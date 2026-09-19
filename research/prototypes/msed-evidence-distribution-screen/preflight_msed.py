#!/usr/bin/env python3
"""Decision-relevant CUDA preflight for the MSED evidence-distribution screen."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict

import dill
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
PORTFOLIO_DIR = HERE.parents[0] / "evidence-access-portfolio"
if str(PORTFOLIO_DIR) not in sys.path:
    sys.path.insert(0, str(PORTFOLIO_DIR))

from portfolio_model import CHUNK, MEDICATIONS, PortfolioModel  # noqa: E402
from run_portfolio import (  # noqa: E402
    BATCH_SIZE,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _require_clean_source,
    _validate_data,
    _validate_profile,
)
from msed_model import MSED_VARIANTS, MSEDModel, objective, pack_rows, parameter_count  # noqa: E402
from run_msed import LANES, _make_model, _seed_everything  # noqa: E402


def _snapshot(model: torch.nn.Module) -> Dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def _state_diff(left: Dict[str, torch.Tensor], right: Dict[str, torch.Tensor]) -> float:
    if left.keys() != right.keys():
        raise RuntimeError("matched state_dict keys differ")
    maximum = 0.0
    for key in left:
        a = left[key]
        b = right[key]
        if a.shape != b.shape or a.dtype != b.dtype:
            raise RuntimeError("matched state metadata differs: " + key)
        if a.dtype.is_floating_point:
            maximum = max(maximum, float((a - b).abs().max().item()))
        elif not torch.equal(a, b):
            raise RuntimeError("matched nonfloating state differs: " + key)
    return maximum


def _shared_state_diff(
    base: Dict[str, torch.Tensor], candidate: Dict[str, torch.Tensor]
) -> float:
    maximum = 0.0
    for key, value in base.items():
        if key not in candidate:
            raise RuntimeError("MSED dropped a FineCode/PredictionLocal parameter: " + key)
        other = candidate[key]
        if value.shape != other.shape or value.dtype != other.dtype:
            raise RuntimeError("shared parameter metadata drifted: " + key)
        if value.dtype.is_floating_point:
            maximum = max(maximum, float((value - other).abs().max().item()))
        elif not torch.equal(value, other):
            raise RuntimeError("shared nonfloating state drifted: " + key)
    return maximum


def _direct_local_scores(
    model: PortfolioModel,
    batch: Dict[str, torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    encoded = model._encode(batch)
    memory, mask = model._flat_evidence(encoded, batch)
    normalized = model.read_norm(memory)
    keys = model.local_k(normalized)
    drugs = model._drugs()
    chunks = []
    for start in range(0, MEDICATIONS, CHUNK):
        selected = drugs[start : start + CHUNK]
        q = model.local_q(selected)
        interaction = q[None, :, None, :] * keys[:, None, :, :]
        hidden = model.local_hidden(interaction)
        chunks.append(model.local_out(hidden).squeeze(-1))
    raw = torch.cat(chunks, dim=1)
    masked = raw.masked_fill(~mask[:, None, :], float("-inf"))
    valid_count = mask.sum(dim=-1).clamp_min(1).to(raw.dtype)
    lme = torch.logsumexp(masked, dim=-1) - valid_count.log()[:, None]
    return raw, lme, mask


def run(args: argparse.Namespace) -> Dict[str, Any]:
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    _validate_profile(snapshot, train_dev)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(index for index in range(split, len(records)) if _is_dev(index))
    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = _load_array(train_dev, "train_targets.npy")
    dev_targets = _load_array(train_dev, "dev_targets.npy")
    dx, proc, _vocab = _validate_data(
        records,
        voc,
        ddi,
        train_rows,
        dev_rows,
        train_targets,
        dev_targets,
    )

    leakage_row = copy.deepcopy(train_rows[0])
    altered_row = copy.deepcopy(leakage_row)
    altered_row["_medications"] = [
        int((int(value) + 1) % MEDICATIONS) for value in leakage_row["_medications"]
    ]
    if _model_rows([leakage_row]) != _model_rows([altered_row]):
        raise RuntimeError("current medication target leaked into model payload")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MSED preflight")
    device = torch.device("cuda")
    ddi_tensor = torch.from_numpy(ddi).to(device)
    prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)

    def evidence_size(row: Dict[str, Any]) -> int:
        total = len(row["diagnoses"]) + len(row["procedures"])
        for visit in row["history"]:
            total += len(visit[0]) + len(visit[1]) + len(visit[2])
        return total

    history_indices = [index for index, row in enumerate(train_rows) if len(row["history"]) >= 2]
    history_indices = sorted(
        history_indices,
        key=lambda index: (-evidence_size(train_rows[index]), index),
    )[:BATCH_SIZE]
    if len(history_indices) < 2:
        raise RuntimeError("insufficient history-bearing Train rows")

    history_batch = {
        key: value.to(device)
        for key, value in pack_rows(
            _model_rows([train_rows[index] for index in history_indices]), dx, proc
        ).items()
    }
    history_targets = torch.from_numpy(train_targets[history_indices]).to(device)
    first_rows = [row for row in train_rows if len(row["history"]) == 0][:BATCH_SIZE]
    first_batch = {
        key: value.to(device)
        for key, value in pack_rows(_model_rows(first_rows), dx, proc).items()
    }

    # Verify both stable ingredients inherited by MSED: global FineCode read and the
    # PredictionLocal medication-token scalar potentials/LME statistic.
    _seed_everything()
    foundation = PortfolioModel(dx, proc, "resolution_code").to(device)
    foundation.initialize_prevalence(prevalence)
    foundation.eval()
    foundation_state = _snapshot(foundation)
    with torch.no_grad():
        encoded = foundation._encode(history_batch)
        memory, memory_mask = foundation._flat_evidence(encoded, history_batch)
        foundation_context = foundation._read_memory(memory, memory_mask, foundation._drugs())

    _seed_everything()
    direct_local = PortfolioModel(dx, proc, "prediction_local").to(device)
    direct_local.initialize_prevalence(prevalence)
    direct_local.eval()
    direct_local_state = _snapshot(direct_local)
    with torch.no_grad():
        direct_raw, direct_lme, direct_mask = _direct_local_scores(direct_local, history_batch)
        direct_output = direct_local(history_batch)

    _seed_everything()
    candidate = MSEDModel(dx, proc, "msed_ecf_global").to(device)
    candidate.initialize_prevalence(prevalence)
    candidate.eval()
    candidate_state = _snapshot(candidate)
    with torch.no_grad():
        candidate_context, candidate_raw, candidate_lme, _candidate_vector = candidate.debug_local_objects(
            history_batch
        )

    foundation_shared_diff = _shared_state_diff(foundation_state, candidate_state)
    local_shared_diff = _shared_state_diff(direct_local_state, candidate_state)
    global_context_diff = float((foundation_context - candidate_context).abs().max().item())
    raw_score_diff = float((direct_raw - candidate_raw).abs().max().item())
    lme_diff = float((direct_lme - candidate_lme).abs().max().item())
    if not torch.equal(direct_mask, memory_mask):
        raise RuntimeError("MSED local evidence support drifted from PredictionLocal")
    if (
        foundation_shared_diff != 0.0
        or local_shared_diff != 0.0
        or global_context_diff > 1e-5
        or raw_score_diff > 1e-6
        or lme_diff > 1e-6
    ):
        raise RuntimeError("MSED drifted from the frozen FineCode/PredictionLocal primitives")
    del foundation, candidate
    torch.cuda.empty_cache()

    lane_reports: Dict[str, Any] = {}
    matched_initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    outputs: Dict[str, torch.Tensor] = {}
    debug: Dict[str, Dict[str, torch.Tensor]] = {}

    for lane, variant in LANES.items():
        _seed_everything()
        model = _make_model(dx, proc, variant).to(device)
        model.initialize_prevalence(prevalence)
        if variant in MSED_VARIANTS:
            matched_initialized[lane] = _snapshot(model)

        model.train()
        torch.cuda.reset_peak_memory_stats(device)
        logits = model(history_batch)
        loss, bce, ddi_loss = objective(logits, history_targets, ddi_tensor)
        if (
            not bool(torch.isfinite(logits).all().item())
            or not bool(torch.isfinite(loss).item())
            or not bool(torch.isfinite(bce).item())
            or not bool(torch.isfinite(ddi_loss).item())
        ):
            raise RuntimeError("non-finite preflight computation: " + lane)
        loss.backward()
        finite_gradients = sum(
            1
            for parameter in model.parameters()
            if parameter.grad is not None and bool(torch.isfinite(parameter.grad).all().item())
        )
        if finite_gradients == 0:
            raise RuntimeError("no finite gradients: " + lane)

        model.eval()
        with torch.no_grad():
            outputs[lane] = model(history_batch).detach().cpu()
            first_logits = model(first_batch)
            if isinstance(model, MSEDModel):
                gc, raw, lme, vec = model.debug_local_objects(history_batch)
                debug[lane] = {
                    "global": gc.detach().cpu(),
                    "raw": raw.detach().cpu(),
                    "lme": lme.detach().cpu(),
                    "vector": vec.detach().cpu(),
                }
        if not bool(torch.isfinite(first_logits).all().item()):
            raise RuntimeError("non-finite no-history forward: " + lane)

        lane_reports[lane] = {
            "variant": variant,
            "parameter_count": parameter_count(model),
            "finite_gradient_parameter_tensors": finite_gradients,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
            "no_history_forward_finite": True,
        }
        del model
        torch.cuda.empty_cache()

    matched_counts = {
        lane_reports[lane]["parameter_count"] for lane in LANES if LANES[lane] in MSED_VARIANTS
    }
    if len(matched_counts) != 1:
        raise RuntimeError("six MSED variants do not share one parameter budget")
    reference_state = matched_initialized["msed_ecf_global"]
    for lane, state in matched_initialized.items():
        if _state_diff(reference_state, state) != 0.0:
            raise RuntimeError("matched MSED initialization differs: " + lane)

    # The primary pair must differ only after identical local scores/LME and identical
    # global context have been formed.
    primary_candidate = debug["msed_ecf_global"]
    primary_control = debug["point_lme_global"]
    primary_invariants = {
        "global_context_max_abs_diff": float(
            (primary_candidate["global"] - primary_control["global"]).abs().max().item()
        ),
        "raw_local_score_max_abs_diff": float(
            (primary_candidate["raw"] - primary_control["raw"]).abs().max().item()
        ),
        "raw_lme_max_abs_diff": float(
            (primary_candidate["lme"] - primary_control["lme"]).abs().max().item()
        ),
        "local_vector_max_abs_diff": float(
            (primary_candidate["vector"] - primary_control["vector"]).abs().max().item()
        ),
    }
    if (
        primary_invariants["global_context_max_abs_diff"] > 1e-7
        or primary_invariants["raw_local_score_max_abs_diff"] > 1e-7
        or primary_invariants["raw_lme_max_abs_diff"] > 1e-7
        or primary_invariants["local_vector_max_abs_diff"] <= 1e-8
    ):
        raise RuntimeError("primary MSED/control attribution is not isolated")

    comparisons = {
        "distribution_beyond_lme_global": ("point_lme_global", "msed_ecf_global"),
        "distribution_vs_mean_global": ("point_mean_global", "msed_ecf_global"),
        "distribution_vs_max_global": ("point_max_global", "msed_ecf_global"),
        "distribution_beyond_lme_only": ("point_lme_only", "msed_ecf_only"),
        "global_complement": ("msed_ecf_only", "msed_ecf_global"),
    }
    behavior: Dict[str, Any] = {}
    for name, (control, candidate_lane) in comparisons.items():
        difference = float((outputs[control] - outputs[candidate_lane]).abs().max().item())
        if difference <= 1e-8:
            raise RuntimeError("mechanism behaviorally inactive: " + name)
        behavior[name] = {
            "control": control,
            "candidate": candidate_lane,
            "history_batch_output_max_abs_diff": difference,
        }

    # Anchor identities are direct prior models, not matched-capacity MSED controls.
    _seed_everything()
    anchor_local_direct = PortfolioModel(dx, proc, "prediction_local").to(device)
    anchor_local_direct.initialize_prevalence(prevalence)
    anchor_local_direct.eval()
    _seed_everything()
    anchor_local_lane = _make_model(dx, proc, "prediction_local_anchor").to(device)
    anchor_local_lane.initialize_prevalence(prevalence)
    anchor_local_lane.eval()
    with torch.no_grad():
        anchor_local_diff = float(
            (anchor_local_direct(history_batch) - anchor_local_lane(history_batch)).abs().max().item()
        )

    _seed_everything()
    anchor_foundation_direct = PortfolioModel(dx, proc, "resolution_code").to(device)
    anchor_foundation_direct.initialize_prevalence(prevalence)
    anchor_foundation_direct.eval()
    _seed_everything()
    anchor_foundation_lane = _make_model(dx, proc, "foundation_code_anchor").to(device)
    anchor_foundation_lane.initialize_prevalence(prevalence)
    anchor_foundation_lane.eval()
    with torch.no_grad():
        anchor_foundation_diff = float(
            (anchor_foundation_direct(history_batch) - anchor_foundation_lane(history_batch)).abs().max().item()
        )
    if anchor_local_diff > 1e-7 or anchor_foundation_diff > 1e-7:
        raise RuntimeError("anchor model identity drifted")

    return {
        "status": "PASS",
        "source_revision": args.source_revision,
        "profile_id": "mimic-iii-canonical-131-paper-dev-v1",
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "target_leakage_check": "PASS",
        "primitive_equivalence": {
            "foundation_shared_initialization_max_abs_diff": foundation_shared_diff,
            "prediction_local_shared_initialization_max_abs_diff": local_shared_diff,
            "global_context_max_abs_diff": global_context_diff,
            "raw_local_score_max_abs_diff": raw_score_diff,
            "raw_lme_max_abs_diff": lme_diff,
        },
        "primary_pair_attribution": primary_invariants,
        "matched_msed_parameter_count": next(iter(matched_counts)),
        "lanes": lane_reports,
        "behavioral_differences": behavior,
        "anchor_identity": {
            "prediction_local_output_max_abs_diff": anchor_local_diff,
            "foundation_code_output_max_abs_diff": anchor_foundation_diff,
            "direct_prediction_local_preflight_output_is_finite": bool(
                torch.isfinite(direct_output).all().item()
            ),
        },
        "test_loaded": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
