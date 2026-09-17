"""Drug-Conditioned Precedent Memory (DCPM) and SharedPrecedent control.

This module implements the bounded two-arm Train/Dev mechanism screen for
Drug-Conditioned Precedent Memory on the MIMIC-III canonical-131 surface.
Both arms share the MICA/DrugQuery legal target-free clinical encoder, local
readouts, identical memory cases and peer labels from Train memory, identical
parameter counts, and identical optimization.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import scipy.sparse as sp
import torch
from torch import nn

MEDICATIONS = 131
DIM = 128
HEADS = 4
FF_DIM = 256
CLINICAL_LAYERS = 2
CHUNK = 16
PEER_POOL_SIZE = 256
DROPOUT = 0.1


def configure_numeric_policy() -> dict[str, object]:
    """Freeze the float32 CUDA policy shared by both arms."""
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
    """Pack target-free current D/P and strictly earlier D/P/M visit tuples.

    Each current code is a singleton bag; each earlier modality is one mean
    bag. Empty historical bags remain explicit. No clinical-code positions or
    patient identifier is encoded, and no input is truncated or hashed.
    """
    packed: list[list[tuple[list[int], int, int]]] = []
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
    width = max(map(len, packed))
    ids: list[int] = []
    offsets = [0]
    types, lags, masks = [], [], []
    for tokens in packed:
        mask = []
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


def build_coarse_peer_pool(
    train_rows: Sequence[Mapping[str, Any]],
    dev_rows: Sequence[Mapping[str, Any]],
    diagnosis_count: int,
    procedure_count: int,
    medication_count: int = MEDICATIONS,
    peer_pool_size: int = PEER_POOL_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct common coarse peer pools C_i of size L=256 for Train and Dev.

    Constructed strictly from legal target-free clinical inputs:
    - Current diagnoses
    - Current procedures
    - History diagnoses
    - History procedures
    - History medications
    Current target medications are strictly excluded.
    For Train visits, all same-patient visits are strictly excluded.
    For Dev visits, candidate memory visits are strictly Train visits.
    """
    total_vocab = diagnosis_count + procedure_count + medication_count
    med_offset = diagnosis_count + procedure_count

    def extract_codes(row: Mapping[str, Any]) -> set[int]:
        codes = set()
        codes.update(int(c) for c in row["diagnoses"])
        codes.update(diagnosis_count + int(c) for c in row["procedures"])
        for hist in row["history"]:
            codes.update(int(c) for c in hist[0])
            codes.update(diagnosis_count + int(c) for c in hist[1])
            codes.update(med_offset + int(c) for c in hist[2])
        return codes

    n_train = len(train_rows)
    train_code_sets = [extract_codes(r) for r in train_rows]
    dev_code_sets = [extract_codes(r) for r in dev_rows]

    # Compute Train-only document frequency
    df = np.zeros(total_vocab, dtype=np.int32)
    for cset in train_code_sets:
        for c in cset:
            df[c] += 1

    # IDF weights computed strictly on Train
    idf = np.log((float(n_train) + 1.0) / (df.astype(np.float32) + 1.0)) + 1.0

    def build_matrix(code_sets: list[set[int]]) -> sp.csr_matrix:
        rows_idx, cols_idx, data = [], [], []
        for i, cset in enumerate(code_sets):
            for c in cset:
                rows_idx.append(i)
                cols_idx.append(c)
                data.append(idf[c])
        mat = sp.csr_matrix(
            (data, (rows_idx, cols_idx)), shape=(len(code_sets), total_vocab), dtype=np.float32
        )
        # Row-normalize to unit Euclidean length
        norms = sp.linalg.norm(mat, axis=1)
        norms[norms == 0.0] = 1.0
        mat = sp.diags(1.0 / np.array(norms).flatten()).dot(mat)
        return mat.tocsr()

    train_mat = build_matrix(train_code_sets)
    dev_mat = build_matrix(dev_code_sets)

    # Precompute patient groupings to exclude same-patient visits during Train
    train_patient_ids = [str(r["_patient_id"]) for r in train_rows]
    patient_to_train_indices = defaultdict(list)
    for idx, pid in enumerate(train_patient_ids):
        patient_to_train_indices[pid].append(idx)

    # Train peer pool
    train_peers = np.zeros((n_train, peer_pool_size), dtype=np.int64)
    chunk_size = 512
    for start in range(0, n_train, chunk_size):
        end = min(start + chunk_size, n_train)
        chunk_sim = train_mat[start:end].dot(train_mat.T).toarray()
        for i in range(start, end):
            row_idx = i - start
            same_patient_indices = patient_to_train_indices[train_patient_ids[i]]
            chunk_sim[row_idx, same_patient_indices] = -1e9
            # Select top L peers with deterministic tie-break
            sims = chunk_sim[row_idx]
            # Partition top L
            top_k_indices = np.argpartition(-sims, peer_pool_size)[:peer_pool_size]
            # Sort top L descending by score, tie-break by index
            top_k_sorted = sorted(top_k_indices, key=lambda idx: (-sims[idx], idx))
            train_peers[i] = top_k_sorted

    # Dev peer pool (Train-only candidates)
    n_dev = len(dev_rows)
    dev_peers = np.zeros((n_dev, peer_pool_size), dtype=np.int64)
    for start in range(0, n_dev, chunk_size):
        end = min(start + chunk_size, n_dev)
        chunk_sim = dev_mat[start:end].dot(train_mat.T).toarray()
        for i in range(start, end):
            row_idx = i - start
            sims = chunk_sim[row_idx]
            top_k_indices = np.argpartition(-sims, peer_pool_size)[:peer_pool_size]
            top_k_sorted = sorted(top_k_indices, key=lambda idx: (-sims[idx], idx))
            dev_peers[i] = top_k_sorted

    return train_peers, dev_peers


class DCPMModel(nn.Module):
    """Parameter-matched Drug-Conditioned Precedent Memory (DCPM) or SharedPrecedent.

    Both arms share:
    - Target-free clinical encoder (2 ClinicalBlocks, d=128)
    - Patient state h_i and DrugQuery local read l_im
    - Parameters W_h, W_l, W_d, LN_q, W_k, LN_k, W_v, precedent MLP, head
    - Output prediction head [l_im, d_m, r_im, l_im * d_m] -> z_im
    - Exact parameter-count equality.
    """

    VARIANTS = ("dcpm", "shared_precedent")

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        variant: str = "dcpm",
        medication_count: int = MEDICATIONS,
    ) -> None:
        super().__init__()
        if variant not in self.VARIANTS:
            raise ValueError("variant must be dcpm or shared_precedent")
        if medication_count <= 0:
            raise ValueError("medication_count must be positive")

        self.variant = variant
        self.medication_count = int(medication_count)
        self.med_offset = int(diagnosis_count + procedure_count)

        # 1. Target-free clinical encoder
        self.codes = nn.EmbeddingBag(
            self.med_offset + self.medication_count,
            DIM,
            mode="mean",
            include_last_offset=True,
        )
        self.types = nn.Embedding(6, DIM)
        self.token_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.input_dropout = nn.Dropout(DROPOUT)
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(CLINICAL_LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)

        # 2. DrugQuery local readout
        self.drug_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.query = nn.Linear(DIM, DIM, bias=False)
        self.key = nn.Linear(DIM, DIM, bias=False)
        self.value = nn.Linear(DIM, DIM, bias=False)
        self.conditioner = nn.Linear(DIM, 2 * DIM)

        # 3. Query projection components
        self.w_h = nn.Linear(DIM, DIM, bias=False)
        self.w_l = nn.Linear(DIM, DIM, bias=False)
        self.w_d = nn.Linear(DIM, DIM, bias=False)
        self.ln_q = nn.LayerNorm(DIM, eps=1e-5)

        # 4. Precedent Memory key/value projections
        self.w_k = nn.Linear(DIM, DIM, bias=False)
        self.ln_k = nn.LayerNorm(DIM, eps=1e-5)
        self.w_v = nn.Linear(DIM, DIM, bias=False)

        # 5. Precedent MLP: [mu+, mu-, mu+ - mu-, pi+] -> r_im
        # Input dim: 3 * DIM + 1 = 385 -> 256 -> 128
        self.mlp = nn.Sequential(
            nn.Linear(3 * DIM + 1, 2 * DIM),
            nn.GELU(),
            nn.Dropout(DROPOUT),
            nn.Linear(2 * DIM, DIM),
        )

        # 6. Prediction Head: [l_im, d_m, r_im, l_im * d_m] -> z_im
        # Input dim: 4 * DIM = 512 -> 128 -> 1
        self.head = nn.Sequential(
            nn.Linear(4 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(DROPOUT),
            nn.Linear(DIM, 1),
        )
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
        nn.init.zeros_(self.conditioner.weight)
        nn.init.zeros_(self.conditioner.bias)

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

    def patient_state(self, assembled: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Target-free shared patient state h_i via masked mean pooling."""
        mask_f = mask.unsqueeze(-1).to(assembled.dtype)
        return (assembled * mask_f).sum(dim=1) / mask_f.sum(dim=1).clamp_min(1.0)

    def read(self, views: torch.Tensor, drugs: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Medication-specific attention pooling over [B, M, K, D] views."""
        normalized = self.read_norm(views)
        scores = torch.einsum("md,bmkd->bmk", self.query(drugs), self.key(normalized)) / math.sqrt(
            DIM
        )
        weights = scores.masked_fill(~mask[:, None], float("-inf")).softmax(dim=-1)
        return torch.einsum("bmk,bmkd->bmd", weights, self.value(normalized))

    def condition_context(self, context: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        scale, shift = (0.5 * self.conditioner(drugs).tanh()).chunk(2, dim=-1)
        return context * (1.0 + scale[None]) + shift[None]

    def medication_readout(
        self, assembled: torch.Tensor, mask: torch.Tensor, drugs: torch.Tensor
    ) -> torch.Tensor:
        """DrugQuery local read l_im for each candidate medication."""
        contexts = []
        for start in range(0, self.medication_count, CHUNK):
            selected = drugs[start : start + CHUNK]
            expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
            pooled = self.read(expanded, selected, mask)
            contexts.append(self.condition_context(pooled, selected))
        return torch.cat(contexts, dim=1)

    def encode_patient_state(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Encode target-free patient state h_i for Train memory caching."""
        x = self.encode_tokens(batch)
        assembled = self.assemble(x, batch["mask"])
        return self.patient_state(assembled, batch["mask"])

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        peer_h: torch.Tensor,
        peer_y: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass for DCPM or SharedPrecedent control.

        Args:
            batch: packed clinical input dictionary.
            peer_h: target-free memory embeddings for peers [B, L, DIM].
            peer_y: target medication labels for peers [B, L, M].

        Returns:
            z_im: logits for all medications [B, M].
        """
        x = self.encode_tokens(batch)
        mask = batch["mask"]
        assembled = self.assemble(x, mask)
        h_i = self.patient_state(assembled, mask)  # [B, DIM]
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])  # [M, DIM] (d_m)
        l_im = self.medication_readout(assembled, mask, drugs)  # [B, M, DIM]

        w_h_i = self.w_h(h_i)  # [B, DIM]
        w_l_im = self.w_l(l_im)  # [B, M, DIM]
        w_d_m = self.w_d(drugs)  # [M, DIM]

        if self.variant == "dcpm":
            # q_im = LN(W_h h_i + W_l l_im + W_d d_m)
            q = self.ln_q(w_h_i.unsqueeze(1) + w_l_im + w_d_m.unsqueeze(0))  # [B, M, DIM]
        else:
            # SharedPrecedent control:
            # l_bar_i = mean_m(l_im)
            # d_bar = mean_m(d_m)
            # q_i = LN(W_h h_i + W_l l_bar_i + W_d d_bar)
            l_bar_i = l_im.mean(dim=1)  # [B, DIM]
            d_bar = drugs.mean(dim=0)  # [DIM]
            q_i = self.ln_q(w_h_i + self.w_l(l_bar_i) + self.w_d(d_bar).unsqueeze(0))  # [B, DIM]
            q = q_i.unsqueeze(1).expand(-1, self.medication_count, -1)  # [B, M, DIM]

        # s_ijm = q_im^T LN(W_k h_j) / sqrt(128)
        k_j = self.ln_k(self.w_k(peer_h))  # [B, L, DIM]
        s_ijm = torch.einsum("bmd,bld->bml", q, k_j) / math.sqrt(DIM)  # [B, M, L]

        # beta_ijm = softmax_j(s_ijm), j in C_i
        beta = torch.softmax(s_ijm, dim=-1)  # [B, M, L]

        # Value vectors and peer labels
        v_j = self.w_v(peer_h)  # [B, L, DIM]
        y_jm = peer_y.transpose(1, 2)  # [B, M, L]

        # pi+_im = sum_j beta_ijm y_jm
        pi_pos = (beta * y_jm).sum(dim=-1, keepdim=True)  # [B, M, 1]

        # mu+_im = weighted mean W_v h_j over y_jm=1
        weighted_pos_v = torch.einsum("bml,bld->bmd", beta * y_jm, v_j)  # [B, M, DIM]
        mu_pos = torch.where(
            pi_pos > 1e-6,
            weighted_pos_v / pi_pos.clamp_min(1e-8),
            torch.zeros_like(weighted_pos_v),
        )

        # mu-_im = weighted mean W_v h_j over y_jm=0
        pi_neg = 1.0 - pi_pos  # [B, M, 1]
        weighted_neg_v = torch.einsum("bml,bld->bmd", beta * (1.0 - y_jm), v_j)  # [B, M, DIM]
        mu_neg = torch.where(
            pi_neg > 1e-6,
            weighted_neg_v / pi_neg.clamp_min(1e-8),
            torch.zeros_like(weighted_neg_v),
        )

        # r_im = MLP([mu+, mu-, mu+-mu-, pi+])
        r_input = torch.cat([mu_pos, mu_neg, mu_pos - mu_neg, pi_pos], dim=-1)  # [B, M, 3*DIM+1]
        r_im = self.mlp(r_input)  # [B, M, DIM]

        # Head: [l_im, d_m, r_im, l_im*d_m] -> z_im
        broadcast_drugs = drugs.unsqueeze(0).expand(l_im.shape[0], -1, -1)  # [B, M, DIM]
        head_features = torch.cat(
            [l_im, broadcast_drugs, r_im, l_im * broadcast_drugs], dim=-1
        )  # [B, M, 4*DIM]
        z_im = self.head(head_features).squeeze(-1) + self.drug_bias  # [B, M]

        return z_im


def objective(
    logits: torch.Tensor,
    targets: torch.Tensor,
    ddi: torch.Tensor,
    medication_count: int = MEDICATIONS,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Existing MICA BCE + 0.05 normalized DDI loss."""
    if medication_count <= 0 or logits.shape[-1] != medication_count:
        raise ValueError("medication_count must match the logits medication dimension")
    bce = nn.functional.binary_cross_entropy_with_logits(logits, targets)
    probabilities = logits.sigmoid()
    ddi_loss = (
        torch.einsum(
            "bi,ij,bj->b", probabilities, torch.triu(ddi, diagonal=1), probabilities
        ).mean()
        / medication_count
    )
    return bce + 0.05 * ddi_loss, bce, ddi_loss
