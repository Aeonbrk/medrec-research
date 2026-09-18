#!/usr/bin/env python3
"""Decision-relevant preflight for iterative-evidence survivor discrimination."""
from __future__ import annotations

import argparse
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

from portfolio_model import PortfolioModel  # noqa: E402
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
from run_survivor import LANES, SEED_CONDITIONS, _seed_everything  # noqa: E402
from survivor_model import SurvivorModel, objective, pack_rows, parameter_count  # noqa: E402


def _state_diff(
    left: Dict[str, torch.Tensor], right: Dict[str, torch.Tensor]
) -> float:
    if left.keys() != right.keys():
        raise RuntimeError("state_dict keys differ")
    maximum = 0.0
    for key in left:
        a = left[key]
        b = right[key]
        if a.shape != b.shape or a.dtype != b.dtype:
            raise RuntimeError("state tensor metadata differs: " + key)
        if a.dtype.is_floating_point:
            maximum = max(maximum, float((a - b).abs().max().item()))
        elif not torch.equal(a, b):
            raise RuntimeError("nonfloating state differs: " + key)
    return maximum


def _snapshot(model: torch.nn.Module) -> Dict[str, torch.Tensor]:
    return {
        key: value.detach().cpu().clone()
        for key, value in model.state_dict().items()
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    _validate_profile(snapshot, train_dev)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(
        dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32
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
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for survivor preflight")
    device = torch.device("cuda")
    ddi_tensor = torch.from_numpy(ddi).to(device)

    def evidence_size(row: Dict[str, Any]) -> int:
        total = len(row["diagnoses"]) + len(row["procedures"])
        for visit in row["history"]:
            total += len(visit[0]) + len(visit[1]) + len(visit[2])
        return total

    indices = [
        i for i, row in enumerate(train_rows) if len(row["history"]) >= 2
    ]
    indices = sorted(
        indices, key=lambda i: (-evidence_size(train_rows[i]), i)
    )[:BATCH_SIZE]
    if len(indices) < 2:
        raise RuntimeError("not enough history-bearing rows for preflight")
    batch_cpu = pack_rows(
        _model_rows([train_rows[i] for i in indices]), dx, proc
    )
    batch = {key: value.to(device) for key, value in batch_cpu.items()}
    targets = torch.from_numpy(train_targets[indices]).to(device)
    prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)

    # Canonical reread_code must preserve the preceding depth_reread computation.
    _seed_everything("canonical")
    original = PortfolioModel(dx, proc, "depth_reread").to(device)
    original.initialize_prevalence(prevalence)
    original_state = _snapshot(original)
    original.eval()
    with torch.no_grad():
        original_logits = original(batch).detach().cpu()

    _seed_everything("canonical")
    replacement = SurvivorModel(dx, proc, "reread_code").to(device)
    replacement.initialize_prevalence(prevalence)
    replacement_state = _snapshot(replacement)
    exact_state_diff = _state_diff(original_state, replacement_state)
    replacement.eval()
    with torch.no_grad():
        replacement_logits = replacement(batch).detach().cpu()
    exact_output_diff = float(
        (original_logits - replacement_logits).abs().max().item()
    )
    if exact_state_diff != 0.0 or exact_output_diff > 1e-7:
        raise RuntimeError(
            "reread_code is not exact-equivalent to prior depth_reread"
        )
    del original, replacement
    torch.cuda.empty_cache()

    lane_reports: Dict[str, Any] = {}
    initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    outputs: Dict[str, torch.Tensor] = {}
    for lane, spec in LANES.items():
        _seed_everything(spec["condition"])
        model = SurvivorModel(dx, proc, spec["variant"]).to(device)
        model.initialize_prevalence(prevalence)
        initialized[lane] = _snapshot(model)
        model.train()
        logits = model(batch)
        loss, bce, ddi_loss = objective(logits, targets, ddi_tensor)
        if not bool(torch.isfinite(logits).all().item()) or not all(
            bool(torch.isfinite(value).item())
            for value in (loss, bce, ddi_loss)
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
            outputs[lane] = model(batch).detach().cpu()
        lane_reports[lane] = {
            "variant": spec["variant"],
            "condition": spec["condition"],
            "rng": dict(SEED_CONDITIONS[spec["condition"]]),
            "parameter_count": parameter_count(model),
            "finite_gradient_parameter_tensors": finite_gradients,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device)
            / 1048576.0,
        }
        del model
        torch.cuda.empty_cache()

    pairs = {
        "resolution_canonical": (
            "resolution_visit_canonical",
            "resolution_code_canonical",
        ),
        "depth_stability_1": ("depth_state_s1", "depth_reread_s1"),
        "depth_stability_2": ("depth_state_s2", "depth_reread_s2"),
        "depth_stability_3": ("depth_state_s3", "depth_reread_s3"),
    }
    pair_reports: Dict[str, Any] = {}
    for name, (control, candidate) in pairs.items():
        if (
            lane_reports[control]["parameter_count"]
            != lane_reports[candidate]["parameter_count"]
        ):
            raise RuntimeError("parameter mismatch: " + name)
        init_diff = _state_diff(
            initialized[control], initialized[candidate]
        )
        if init_diff != 0.0:
            raise RuntimeError("matched initialization differs: " + name)
        behavior_diff = float(
            (outputs[control] - outputs[candidate]).abs().max().item()
        )
        if behavior_diff <= 1e-8:
            raise RuntimeError("mechanism is behaviorally inactive: " + name)
        pair_reports[name] = {
            "control": control,
            "candidate": candidate,
            "parameter_count": lane_reports[control]["parameter_count"],
            "initialization_max_abs_diff": init_diff,
            "history_batch_output_max_abs_diff": behavior_diff,
        }

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
        "prior_depth_reread_equivalence": {
            "state_max_abs_diff": exact_state_diff,
            "output_max_abs_diff": exact_output_diff,
        },
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
