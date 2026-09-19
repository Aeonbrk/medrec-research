#!/usr/bin/env python3
"""Decision-relevant CUDA preflight for the MHEF normalization-domain screen."""
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

from portfolio_model import MEDICATIONS, PortfolioModel  # noqa: E402
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
from mhef_model import (  # noqa: E402
    MHEFModel,
    objective,
    pack_rows,
    parameter_count,
)
from run_mhef import LANES, _make_model, _seed_everything  # noqa: E402


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
            raise RuntimeError("MHEF dropped a FineCode foundation parameter: " + key)
        other = candidate[key]
        if value.shape != other.shape or value.dtype != other.dtype:
            raise RuntimeError("FineCode foundation parameter metadata drifted: " + key)
        if value.dtype.is_floating_point:
            maximum = max(maximum, float((value - other).abs().max().item()))
        elif not torch.equal(value, other):
            raise RuntimeError("FineCode foundation nonfloating state drifted: " + key)
    return maximum


def _counts(masks: tuple[torch.Tensor, torch.Tensor, torch.Tensor]) -> torch.Tensor:
    return torch.stack([mask.sum(dim=-1) for mask in masks], dim=-1)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    _validate_profile(snapshot, train_dev)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(
        dill.load((snapshot / "ddi_A_final.pkl").open("rb")),
        dtype=np.float32,
    )
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
        raise RuntimeError("CUDA is required for MHEF preflight")
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

    # Verify the stable global FineCode path is unchanged before adding private views.
    _seed_everything()
    foundation = PortfolioModel(dx, proc, "resolution_code").to(device)
    foundation.initialize_prevalence(prevalence)
    foundation_state = _snapshot(foundation)
    foundation.eval()
    with torch.no_grad():
        encoded = foundation._encode(history_batch)
        memory, memory_mask = foundation._flat_evidence(encoded, history_batch)
        foundation_context = foundation._read_memory(memory, memory_mask, foundation._drugs())

    _seed_everything()
    candidate = MHEFModel(dx, proc, "mhef_independent_add").to(device)
    candidate.initialize_prevalence(prevalence)
    candidate_state = _snapshot(candidate)
    candidate.eval()
    with torch.no_grad():
        encoded = candidate._encode(history_batch)
        candidate_context = candidate._contexts(encoded, history_batch, candidate._drugs())[0][0]

    shared_init_diff = _shared_state_diff(foundation_state, candidate_state)
    global_context_diff = float((foundation_context - candidate_context).abs().max().item())
    if shared_init_diff != 0.0 or global_context_diff > 1e-7:
        raise RuntimeError("MHEF global path drifted from the stable FineCode foundation")
    del foundation, candidate
    torch.cuda.empty_cache()

    lane_reports: Dict[str, Any] = {}
    initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    outputs: Dict[str, torch.Tensor] = {}

    for lane, variant in LANES.items():
        _seed_everything()
        model = _make_model(dx, proc, variant).to(device)
        model.initialize_prevalence(prevalence)
        initialized[lane] = _snapshot(model)

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

    parameter_counts = {value["parameter_count"] for value in lane_reports.values()}
    if len(parameter_counts) != 1:
        raise RuntimeError("MHEF screen variants do not share one parameter budget")

    reference_state = initialized["mhef_independent_add"]
    for lane, state in initialized.items():
        if _state_diff(reference_state, state) != 0.0:
            raise RuntimeError("matched initialization differs: " + lane)

    comparisons = {
        "normalization_add": ("coupled_budget_add", "mhef_independent_add"),
        "normalization_concat": ("coupled_budget_concat", "mhef_independent_concat"),
        "capacity_wide_global": ("wide_global_add", "mhef_independent_add"),
        "global_complement": ("private_only_add", "mhef_independent_add"),
        "semantic_partition_a": ("hash_partition_a_add", "mhef_independent_add"),
        "semantic_partition_b": ("hash_partition_b_add", "mhef_independent_add"),
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

    # Hash partitions must preserve per-example bucket sizes and typed-evidence union.
    _seed_everything()
    mask_model = MHEFModel(dx, proc, "mhef_independent_add").to(device)
    semantic = mask_model.debug_view_masks(history_batch, "mhef_independent_add")
    semantic_union = semantic[0] | semantic[1] | semantic[2]
    hash_checks: Dict[str, Any] = {}
    for variant in ("hash_partition_a_add", "hash_partition_b_add"):
        hashed = mask_model.debug_view_masks(history_batch, variant)
        if not torch.equal(_counts(semantic), _counts(hashed)):
            raise RuntimeError("hash partition changed per-example bucket sizes: " + variant)
        hashed_union = hashed[0] | hashed[1] | hashed[2]
        if not torch.equal(semantic_union, hashed_union):
            raise RuntimeError("hash partition changed typed evidence support: " + variant)
        overlap = sum(int((semantic[i] & hashed[i]).sum().item()) for i in range(3))
        total = int(semantic_union.sum().item())
        hash_checks[variant] = {
            "bucket_count_preservation": "PASS",
            "typed_union_preservation": "PASS",
            "same_bucket_fraction": float(overlap) / float(max(total, 1)),
        }
    del mask_model

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
        "finecode_global_path_equivalence": {
            "shared_initialization_max_abs_diff": shared_init_diff,
            "global_context_max_abs_diff": global_context_diff,
        },
        "common_parameter_count": next(iter(parameter_counts)),
        "lanes": lane_reports,
        "behavioral_differences": behavior,
        "hash_partition_checks": hash_checks,
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
