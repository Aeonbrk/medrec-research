"""MedLedger: independent evidence accumulation vs normalized competition.

Both arms share identical evidence construction, 2-layer clinical Transformer,
interaction tensor u_mk, signed latent model contributions a_mk, count nuisance
path eta_m = v_m^T q(X), log1p positive/negative aggregation, and tau scale.
They differ only in how relevance is aggregated across evidence units:
MedLedger uses independent sigmoid gates g_mk = sigmoid(r_mk), whereas
NormalizedLedger uses softmax competition alpha_mk = softmax_k(r_mk).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import torch
from torch import nn

MEDICATIONS = 131
DIM = 128
HEADS = 4
FF_DIM = 256
LAYERS = 2
DROPOUT = 0.1
DEFAULT_TAU_INIT = 0.5413248547  # softplus(0.5413248547) == 1.0


def configure_numeric_policy() -> dict[str, object]:
    """Freeze the float32 CUDA policy shared by both MedLedger arms."""
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    return {
        "dtype": "float32",
        "cuda_matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
    }


def pack_inputs(
    rows: Sequence[dict[str, Any]], diagnosis_count: int, procedure_count: int
) -> dict[str, torch.Tensor]:
    """Pack target-free current D/P, history D/P/M tokens, and count features.

    Tokens:
      - Type 0, Lag 0: NULL token (empty bag)
      - Type 1, Lag 0: Current diagnosis (singleton code)
      - Type 2, Lag 0: Current procedure (singleton code + diagnosis_count)
      - Type 3, Lag > 0: Historical diagnosis summary bag
      - Type 4, Lag > 0: Historical procedure summary bag
      - Type 5, Lag > 0: Historical medication summary bag

    Nuisance features q(X):
      [log1p(num_current_dx), log1p(num_current_proc), log1p(num_history_visits)]
    """
    packed: list[list[tuple[list[int], int, int]]] = []
    q_counts: list[list[float]] = []
    med_offset = diagnosis_count + procedure_count

    for row in rows:
        tokens: list[tuple[list[int], int, int]] = [([], 0, 0)]
        tokens.extend(([int(c)], 1, 0) for c in sorted(set(row["diagnoses"])))
        tokens.extend(([diagnosis_count + int(c)], 2, 0) for c in sorted(set(row["procedures"])))
        history = row["history"]
        for index, visit in enumerate(history):
            lag = len(history) - index
            tokens.append((sorted(set(map(int, visit[0]))), 3, lag))
            tokens.append(([diagnosis_count + int(c) for c in sorted(set(visit[1]))], 4, lag))
            tokens.append(([med_offset + int(c) for c in sorted(set(visit[2]))], 5, lag))
        packed.append(tokens)

        num_dx = len(set(row["diagnoses"]))
        num_proc = len(set(row["procedures"]))
        num_hist = len(history)
        q_counts.append(
            [
                math.log1p(float(num_dx)),
                math.log1p(float(num_proc)),
                math.log1p(float(num_hist)),
            ]
        )

    width = max(map(len, packed))
    ids: list[int] = []
    offsets = [0]
    types: list[int] = []
    lags: list[float] = []
    masks: list[list[bool]] = []
    for tokens in packed:
        mask: list[bool] = []
        for index in range(width):
            codes, kind, lag = tokens[index] if index < len(tokens) else ([], 0, 0)
            ids.extend(codes)
            offsets.append(len(ids))
            types.append(kind)
            lags.append(float(lag))
            mask.append(index < len(tokens))
        masks.append(mask)

    return {
        "codes": torch.tensor(ids, dtype=torch.long),
        "offsets": torch.tensor(offsets, dtype=torch.long),
        "types": torch.tensor(types, dtype=torch.long),
        "lags": torch.tensor(lags, dtype=torch.float32),
        "mask": torch.tensor(masks, dtype=torch.bool),
        "q_counts": torch.tensor(q_counts, dtype=torch.float32),
    }


class ClinicalBlock(nn.Module):
    """One shared-parameter clinical-token interaction block."""

    def __init__(self) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.attention = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        normalized = self.norm1(x)
        x = (
            x
            + self.attention(
                normalized, normalized, normalized, key_padding_mask=~mask, need_weights=False
            )[0]
        )
        return x + self.ff(self.norm2(x))


class MedLedgerModel(nn.Module):
    """MedLedger full arm or NormalizedLedger matched control."""

    VARIANTS = ("medledger", "normalized")

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        variant: str = "medledger",
        medication_count: int = MEDICATIONS,
    ) -> None:
        super().__init__()
        if variant not in self.VARIANTS:
            raise ValueError(f"variant must be one of {self.VARIANTS}")
        if medication_count <= 0:
            raise ValueError("medication_count must be positive")

        self.variant = variant
        self.medication_count = int(medication_count)
        self.med_offset = int(diagnosis_count + procedure_count)

        self.codes = nn.EmbeddingBag(
            self.med_offset + self.medication_count, DIM, mode="mean", include_last_offset=True
        )
        self.types = nn.Embedding(6, DIM)
        self.token_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.input_dropout = nn.Dropout(DROPOUT)
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.drug_norm = nn.LayerNorm(DIM, eps=1e-5)

        # Medication-token interaction projections:
        # u_mk = GELU(W_h h_k + W_e e_m + W_x (h_k ⊙ e_m) + b)
        self.w_h = nn.Linear(DIM, DIM, bias=False)
        self.w_e = nn.Linear(DIM, DIM, bias=False)
        self.w_x = nn.Linear(DIM, DIM, bias=False)
        self.u_bias = nn.Parameter(torch.zeros(DIM))

        # Signed relevance and contribution heads:
        # r_mk = w_r^T u_mk
        # a_mk = tanh(w_a^T u_mk)
        self.w_r = nn.Linear(DIM, 1, bias=False)
        self.w_a = nn.Linear(DIM, 1, bias=False)

        # Explicit count nuisance path: eta_m = v_m^T q(X), initialized to 0
        self.v = nn.Parameter(torch.zeros(self.medication_count, 3))

        # Scale parameter tau, initialized so softplus(tau) == 1.0
        self.tau = nn.Parameter(torch.tensor([DEFAULT_TAU_INIT]))

        # Output bias per medication (initialized from Train log-odds)
        self.drug_bias = nn.Parameter(torch.zeros(self.medication_count))

        self.register_buffer(
            "lag_frequency", torch.exp(torch.arange(0, DIM, 2) * (-math.log(10000.0) / DIM))
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, (nn.Embedding, nn.EmbeddingBag)):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
        for block in self.blocks:
            nn.init.xavier_uniform_(block.attention.in_proj_weight)
            nn.init.zeros_(block.attention.in_proj_bias)
        nn.init.xavier_uniform_(self.w_h.weight)
        nn.init.xavier_uniform_(self.w_e.weight)
        nn.init.xavier_uniform_(self.w_x.weight)
        nn.init.zeros_(self.u_bias)
        nn.init.xavier_uniform_(self.w_r.weight)
        nn.init.xavier_uniform_(self.w_a.weight)
        nn.init.zeros_(self.v)
        nn.init.zeros_(self.drug_bias)
        with torch.no_grad():
            self.tau.copy_(torch.tensor([DEFAULT_TAU_INIT]))

    def initialize_prevalence(self, prevalence: torch.Tensor) -> None:
        with torch.no_grad():
            p = prevalence.clamp(1e-4, 1.0 - 1e-4)
            self.drug_bias.copy_(torch.log(p / (1.0 - p)))

    def encode_tokens(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        lag_angle = batch["lags"].unsqueeze(-1) * self.lag_frequency
        positions = torch.stack((lag_angle.sin(), lag_angle.cos()), dim=-1).flatten(-2)
        x = (
            self.token_norm(
                self.codes(batch["codes"], batch["offsets"]) + self.types(batch["types"])
            )
            + positions
        )
        return self.input_dropout(x.reshape(*batch["mask"].shape, DIM))

    def assemble(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x, mask)
        return self.final_norm(x)

    def forward(
        self, batch: dict[str, torch.Tensor], return_diagnostics: bool = False
    ) -> torch.Tensor | tuple[torch.Tensor, dict[str, Any]]:
        x = self.encode_tokens(batch)
        mask = batch["mask"]  # [B, K]
        h = self.assemble(x, mask)  # [B, K, D]
        e = self.drug_norm(
            self.codes.weight[self.med_offset : self.med_offset + self.medication_count]
        )  # [M, D]

        # Contextualizer projections:
        wh_h = self.w_h(h).unsqueeze(1)  # [B, 1, K, D]
        we_e = self.w_e(e).unsqueeze(0).unsqueeze(2)  # [1, M, 1, D]
        h_exp = h.unsqueeze(1)  # [B, 1, K, D]
        e_exp = e.unsqueeze(0).unsqueeze(2)  # [1, M, 1, D]
        wx_inter = self.w_x(h_exp * e_exp)  # [B, M, K, D]

        u = nn.functional.gelu(wh_h + we_e + wx_inter + self.u_bias)  # [B, M, K, D]
        r = self.w_r(u).squeeze(-1)  # [B, M, K]
        a = torch.tanh(self.w_a(u).squeeze(-1))  # [B, M, K]

        mask_expanded = mask.unsqueeze(1)  # [B, 1, K]

        if self.variant == "medledger":
            g = torch.sigmoid(r)
            g = g.masked_fill(~mask_expanded, 0.0)
            c = g * a
            relevance_weights = g
        else:
            r_masked = r.masked_fill(~mask_expanded, float("-inf"))
            alpha = torch.softmax(r_masked, dim=-1)
            alpha = torch.nan_to_num(alpha, nan=0.0)
            c = alpha * a
            relevance_weights = alpha

        c = c.masked_fill(~mask_expanded, 0.0)
        c_pos = nn.functional.relu(c)
        c_neg = nn.functional.relu(-c)
        s_pos = c_pos.sum(dim=-1)  # [B, M]
        s_neg = c_neg.sum(dim=-1)  # [B, M]
        a_agg = torch.log1p(s_pos) - torch.log1p(s_neg)  # [B, M]

        q = batch["q_counts"]  # [B, 3]
        eta = nn.functional.linear(q, self.v)  # [B, M]
        tau_scale = nn.functional.softplus(self.tau)  # scalar
        logits = self.drug_bias + eta + tau_scale * a_agg  # [B, M]

        if return_diagnostics:
            return logits, {
                "r": r,
                "a": a,
                "relevance_weights": relevance_weights,
                "c": c,
                "c_pos": c_pos,
                "c_neg": c_neg,
                "s_pos": s_pos,
                "s_neg": s_neg,
                "a_agg": a_agg,
                "eta": eta,
                "tau_scale": tau_scale,
            }
        return logits
