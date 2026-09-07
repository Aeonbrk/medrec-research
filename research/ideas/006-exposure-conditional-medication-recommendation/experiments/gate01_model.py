"""Idea 006 Gate 01: Model architecture, DDI losses, and direct exposure controls.

SSOT: research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class CommonOrderTimeBackbone(nn.Module):
    """Common causal order-time GRU backbone.

    Dimensions frozen by protocol:
    - medication embedding: 64
    - transaction-type embedding: 8
    - elapsed-time projection: 8
    - one-layer GRU: hidden size 128
    - active-regimen input: 131
    - log-hours-since-admission: 1
    - concatenated MLP input: 128 + 131 + 1 = 260
    - MLP: 260 -> 128 -> 131 with ReLU and dropout 0.10
    """

    def __init__(
        self,
        num_medications: int = 131,
        med_emb_dim: int = 64,
        trans_type_emb_dim: int = 8,
        elapsed_proj_dim: int = 8,
        gru_hidden_dim: int = 128,
        mlp_hidden_dim: int = 128,
        dropout: float = 0.10,
    ) -> None:
        super().__init__()
        self.num_medications = num_medications

        # Index 0 is reserved for padding, so vocab size is num_medications + 1
        self.med_embedding = nn.Embedding(
            num_embeddings=num_medications + 1,
            embedding_dim=med_emb_dim,
            padding_idx=0,
        )

        # Transaction types: 0=pad, 1=New, 2=Change, 3=D/C
        self.trans_embedding = nn.Embedding(
            num_embeddings=4,
            embedding_dim=trans_type_emb_dim,
            padding_idx=0,
        )

        self.elapsed_proj = nn.Linear(1, elapsed_proj_dim)

        gru_input_dim = med_emb_dim + trans_type_emb_dim + elapsed_proj_dim
        self.gru = nn.GRU(
            input_size=gru_input_dim,
            hidden_size=gru_hidden_dim,
            num_layers=1,
            batch_first=True,
        )

        # Learned zero-history state when no historical transactions exist
        self.zero_history = nn.Parameter(torch.zeros(gru_hidden_dim))

        mlp_input_dim = gru_hidden_dim + num_medications + 1  # 128 + 131 + 1 = 260
        self.mlp = nn.Sequential(
            nn.Linear(mlp_input_dim, mlp_hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_hidden_dim, num_medications),
        )

    def forward(
        self,
        hist_meds: torch.Tensor,  # (B, L) int64 in [0, 131]
        hist_types: torch.Tensor,  # (B, L) int64 in [0, 3]
        hist_elapsed: torch.Tensor,  # (B, L) float32 (log1p hours)
        active_regimen: torch.Tensor,  # (B, 131) float32
        log_hours_since_admit: torch.Tensor,  # (B, 1) float32
    ) -> torch.Tensor:
        """Forward pass emitting 131 unnormalized logits."""
        # Hist features
        med_emb = self.med_embedding(hist_meds)  # (B, L, 64)
        trans_emb = self.trans_embedding(hist_types)  # (B, L, 8)
        elapsed_feat = self.elapsed_proj(hist_elapsed.unsqueeze(-1))  # (B, L, 8)

        gru_in = torch.cat([med_emb, trans_emb, elapsed_feat], dim=-1)  # (B, L, 80)

        # Sequence lengths: count non-padding elements per sequence
        mask = hist_meds > 0  # (B, L)
        seq_lens = mask.sum(dim=-1)  # (B,)

        gru_out, _ = self.gru(gru_in)  # (B, L, 128)

        # Extract last valid state for each batch item
        batch_size = hist_meds.size(0)
        final_gru = torch.zeros(
            batch_size, self.gru.hidden_size, device=hist_meds.device, dtype=gru_in.dtype
        )

        has_hist = seq_lens > 0
        if has_hist.any():
            valid_indices = torch.where(has_hist)[0]
            last_steps = seq_lens[valid_indices] - 1
            final_gru[valid_indices] = gru_out[valid_indices, last_steps]

        if (~has_hist).any():
            no_hist_indices = torch.where(~has_hist)[0]
            final_gru[no_hist_indices] = self.zero_history

        # Concatenate: final_gru (128) + active_regimen (131) + log_hours (1) = 260
        combined = torch.cat([final_gru, active_regimen, log_hours_since_admit], dim=-1)
        logits = self.mlp(combined)  # (B, 131)
        return logits


def compute_loss_pred(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Full-vocabulary unweighted binary cross-entropy."""
    return F.binary_cross_entropy_with_logits(logits, targets, reduction="mean")


def compute_loss_new(logits: torch.Tensor, ddi_matrix: torch.Tensor) -> torch.Tensor:
    """Conventional predicted-new-set DDI loss term."""
    # p: (B, 131)
    p = torch.sigmoid(logits)
    # D: (131, 131) symmetric, D_ii = 0
    # sum_{i<j} p_i p_j D_ij = 0.5 * p^T D p
    # Factor 2 / (|V|(|V|-1)) * 0.5 = 1 / (|V|(|V|-1)) = 1 / 17030
    p_d = torch.matmul(p, ddi_matrix)  # (B, 131)
    new_term = (p_d * p).sum(dim=-1) / 17030.0  # (B,)
    return new_term.mean()


def compute_loss_active(
    logits: torch.Tensor, active_regimen: torch.Tensor, ddi_matrix: torch.Tensor
) -> torch.Tensor:
    """Exposure-conditioned active-regimen DDI loss term."""
    p = torch.sigmoid(logits)  # (B, 131)
    # A_t: (B, 131)
    a_count = active_regimen.sum(dim=-1)  # (B,)
    a_d = torch.matmul(active_regimen, ddi_matrix)  # (B, 131)
    dot = (p * a_d).sum(dim=-1)  # (B,)

    denom = 131.0 * torch.clamp(a_count, min=1.0)
    active_term = torch.where(a_count > 0, dot / denom, torch.zeros_like(dot))
    return active_term.mean()


def compute_total_loss(
    variant: str,
    logits: torch.Tensor,
    targets: torch.Tensor,
    active_regimen: torch.Tensor,
    ddi_matrix: torch.Tensor,
    lambda_val: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Compute total loss based on method variant.

    Returns:
        (total_loss, l_pred, l_new, l_active)
    """
    l_pred = compute_loss_pred(logits, targets)
    l_new = compute_loss_new(logits, ddi_matrix) if lambda_val > 0.0 else torch.zeros_like(l_pred)
    l_active = (
        compute_loss_active(logits, active_regimen, ddi_matrix)
        if (lambda_val > 0.0 and variant == "ExposureConditional")
        else torch.zeros_like(l_pred)
    )

    if variant == "Base":
        total_loss = l_pred
    elif variant == "StaticLoss":
        total_loss = l_pred + lambda_val * l_new
    elif variant == "ExposureConditional":
        total_loss = l_pred + lambda_val * (l_new + l_active)
    else:
        raise ValueError(f"Unknown variant: {variant}")

    return total_loss, l_pred, l_new, l_active


def direct_exposure_rerank_single(
    base_logits: torch.Tensor | np.ndarray,  # (131,) float
    active_regimen: torch.Tensor | np.ndarray,  # (131,) float/bool
    ddi_matrix: torch.Tensor | np.ndarray,  # (131, 131) float/bool
    concept_codes: list[str],  # 131 concept strings for tie-breaking
    gamma: float,
    k: int = 5,
) -> list[int]:
    """Greedy exposure-aware reranker for a single decision point."""
    logits_np = (
        base_logits.detach().cpu().numpy()
        if isinstance(base_logits, torch.Tensor)
        else np.asarray(base_logits, dtype=np.float32)
    )
    a_vec = (
        active_regimen.detach().cpu().numpy()
        if isinstance(active_regimen, torch.Tensor)
        else np.asarray(active_regimen, dtype=np.float32)
    )
    d_mat = (
        ddi_matrix.detach().cpu().numpy()
        if isinstance(ddi_matrix, torch.Tensor)
        else np.asarray(ddi_matrix, dtype=np.float32)
    )

    a_size = int(a_vec.sum())
    a_edges = d_mat @ a_vec  # (131,)
    selected: list[int] = []
    selected_set: set[int] = set()
    s_edges_acc = np.zeros(len(logits_np), dtype=np.float32)

    for step in range(k):
        denom = max(1, a_size + step)
        cand_scores = logits_np - gamma * ((a_edges + s_edges_acc) / denom)

        best_cand: int | None = None
        best_score = float("-inf")
        best_logit = float("-inf")
        best_code = ""

        for m in range(len(logits_np)):
            if m in selected_set:
                continue
            sc = float(cand_scores[m])
            l_m = float(logits_np[m])
            c_m = concept_codes[m]

            if (
                best_cand is None
                or sc > best_score
                or (
                    sc == best_score
                    and (l_m > best_logit or (l_m == best_logit and c_m < best_code))
                )
            ):
                best_cand = m
                best_score = sc
                best_logit = l_m
                best_code = c_m

        assert best_cand is not None
        selected.append(best_cand)
        selected_set.add(best_cand)
        s_edges_acc += d_mat[best_cand]

    return selected


def exposure_hard_constraint_single(
    base_logits: torch.Tensor | np.ndarray,  # (131,) float
    active_regimen: torch.Tensor | np.ndarray,  # (131,) float/bool
    ddi_matrix: torch.Tensor | np.ndarray,  # (131, 131) float/bool
    concept_codes: list[str],  # 131 concept strings for tie-breaking
    k: int = 5,
) -> list[int]:
    """Deterministic exposure-aware hard constraint selector."""
    logits_np = (
        base_logits.detach().cpu().numpy()
        if isinstance(base_logits, torch.Tensor)
        else np.asarray(base_logits, dtype=np.float32)
    )
    a_vec = (
        active_regimen.detach().cpu().numpy()
        if isinstance(active_regimen, torch.Tensor)
        else np.asarray(active_regimen, dtype=np.float32)
    )
    d_mat = (
        ddi_matrix.detach().cpu().numpy()
        if isinstance(ddi_matrix, torch.Tensor)
        else np.asarray(ddi_matrix, dtype=np.float32)
    )

    a_size = int(a_vec.sum())
    a_edges = d_mat @ a_vec
    selected: list[int] = []
    selected_set: set[int] = set()
    s_edges_acc = np.zeros(len(logits_np), dtype=np.float32)

    for step in range(k):
        denom = max(1, a_size + step)
        inc_edges = a_edges + s_edges_acc

        zero_candidates: list[tuple[int, float, str]] = []
        cand_info: list[tuple[int, float, float, str]] = []

        for m in range(len(logits_np)):
            if m in selected_set:
                continue
            ie = float(inc_edges[m])
            l_m = float(logits_np[m])
            c_m = concept_codes[m]
            r_t = ie / denom

            cand_info.append((m, r_t, l_m, c_m))
            if ie == 0.0:
                zero_candidates.append((m, l_m, c_m))

        if zero_candidates:
            zero_candidates.sort(key=lambda x: (-x[1], x[2]))
            best_cand = zero_candidates[0][0]
        else:
            cand_info.sort(key=lambda x: (x[1], -x[2], x[3]))
            best_cand = cand_info[0][0]

        selected.append(best_cand)
        selected_set.add(best_cand)
        s_edges_acc += d_mat[best_cand]

    return selected
