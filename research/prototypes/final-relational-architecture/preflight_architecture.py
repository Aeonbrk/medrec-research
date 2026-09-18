#!/usr/bin/env python3
"""Decision-relevant CUDA preflight for the final relational architecture search."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

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
from final_relational_model import (  # noqa: E402
    FinalRelationalModel,
    objective,
    pack_rows,
    parameter_count,
)
from run_architecture import LANES, _make_model, _seed_everything  # noqa: E402


def _snapshot(model: torch.nn.Module) -> Dict[str, torch.Tensor]:
    return {
        key: value.detach().cpu().clone()
        for key, value in model.state_dict().items()
    }


def _state_diff(
    left: Dict[str, torch.Tensor],
    right: Dict[str, torch.Tensor],
) -> float:
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
    dev_patients = tuple(
        index for index in range(split, len(records)) if _is_dev(index)
    )
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
        int((int(value) + 1) % MEDICATIONS)
        for value in leakage_row["_medications"]
    ]
    if _model_rows([leakage_row]) != _model_rows([altered_row]):
        raise RuntimeError("current medication target leaked into model payload")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for architecture preflight")
    device = torch.device("cuda")
    ddi_tensor = torch.from_numpy(ddi).to(device)
    prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)

    def evidence_size(row: Dict[str, Any]) -> int:
        total = len(row["diagnoses"]) + len(row["procedures"])
        for visit in row["history"]:
            total += len(visit[0]) + len(visit[1]) + len(visit[2])
        return total

    history_indices = [
        index for index, row in enumerate(train_rows) if len(row["history"]) >= 2
    ]
    history_indices = sorted(
        history_indices,
        key=lambda index: (-evidence_size(train_rows[index]), index),
    )[:BATCH_SIZE]
    if len(history_indices) < 2:
        raise RuntimeError("insufficient history-bearing Train rows")

    history_batch = {
        key: value.to(device)
        for key, value in pack_rows(
            _model_rows([train_rows[index] for index in history_indices]),
            dx,
            proc,
        ).items()
    }
    history_targets = torch.from_numpy(train_targets[history_indices]).to(device)

    first_rows = [row for row in train_rows if len(row["history"]) == 0][
        :BATCH_SIZE
    ]
    first_batch = {
        key: value.to(device)
        for key, value in pack_rows(_model_rows(first_rows), dx, proc).items()
    }

    # The new foundation anchor must be the exact prior resolution_code model.
    _seed_everything()
    direct = PortfolioModel(dx, proc, "resolution_code").to(device)
    direct.initialize_prevalence(prevalence)
    direct_state = _snapshot(direct)
    direct.eval()
    with torch.no_grad():
        direct_logits = direct(history_batch).detach().cpu()

    _seed_everything()
    wrapped = _make_model(dx, proc, "foundation", "resolution_code").to(device)
    wrapped.initialize_prevalence(prevalence)
    wrapped_state = _snapshot(wrapped)
    wrapped.eval()
    with torch.no_grad():
        wrapped_logits = wrapped(history_batch).detach().cpu()

    foundation_state_diff = _state_diff(direct_state, wrapped_state)
    foundation_output_diff = float(
        (direct_logits - wrapped_logits).abs().max().item()
    )
    if foundation_state_diff != 0.0 or foundation_output_diff > 1e-7:
        raise RuntimeError("foundation_code drifted from prior resolution_code")
    del direct, wrapped
    torch.cuda.empty_cache()

    lane_reports: Dict[str, Any] = {}
    initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    outputs: Dict[str, torch.Tensor] = {}

    for lane, spec in LANES.items():
        _seed_everything()
        model = _make_model(dx, proc, spec["family"], spec["variant"]).to(device)
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
            if parameter.grad is not None
            and bool(torch.isfinite(parameter.grad).all().item())
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
            "family": spec["family"],
            "variant": spec["variant"],
            "parameter_count": parameter_count(model),
            "finite_gradient_parameter_tensors": finite_gradients,
            "cuda_peak_memory_mb": (
                torch.cuda.max_memory_allocated(device) / 1048576.0
            ),
            "no_history_forward_finite": True,
        }
        del model
        torch.cuda.empty_cache()

    matched_pairs: Dict[str, Tuple[str, str]] = {
        "summary_operator": ("summary_add", "summary_mul"),
        "pair_granularity": ("factorized_pair", "nonseparable_pair"),
        "relation_competition": ("nonseparable_pair", "joint_competition_pair"),
        "temporal_edge": ("untyped_edge_pair", "temporal_edge_pair"),
    }
    pair_reports: Dict[str, Any] = {}

    for name, (control, candidate) in matched_pairs.items():
        if (
            lane_reports[control]["parameter_count"]
            != lane_reports[candidate]["parameter_count"]
        ):
            raise RuntimeError("matched parameter count differs: " + name)
        init_diff = _state_diff(initialized[control], initialized[candidate])
        if init_diff != 0.0:
            raise RuntimeError("matched initialization differs: " + name)
        behavior_diff = float(
            (outputs[control] - outputs[candidate]).abs().max().item()
        )
        if behavior_diff <= 1e-8:
            raise RuntimeError("mechanism behaviorally inactive: " + name)
        pair_reports[name] = {
            "control": control,
            "candidate": candidate,
            "parameter_count": lane_reports[control]["parameter_count"],
            "initialization_max_abs_diff": init_diff,
            "history_batch_output_max_abs_diff": behavior_diff,
        }

    relational_counts = {
        lane_reports[lane]["parameter_count"]
        for lane in LANES
        if lane != "foundation_code"
    }
    if len(relational_counts) != 1:
        raise RuntimeError("relational architecture variants do not share one budget")

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
        "foundation_equivalence": {
            "state_max_abs_diff": foundation_state_diff,
            "output_max_abs_diff": foundation_output_diff,
        },
        "relational_parameter_count": next(iter(relational_counts)),
        "lanes": lane_reports,
        "pairs": pair_reports,
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
