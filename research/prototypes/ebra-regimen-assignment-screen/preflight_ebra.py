#!/usr/bin/env python3
"""Run the scoped correctness preflight for the frozen EBRA pair."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))

from ebra_model import (  # noqa: E402
    MEDICATIONS,
    SLOTS,
    EBRAModel,
    assignment_decode,
    assignment_loss,
    configure_numeric_policy,
    fixed_multilabel_loss,
    pack_rows,
    parameter_count,
)
from run_ebra import (  # noqa: E402
    BATCH_SIZE,
    PROFILE_ID,
    PROFILE_PATH,
    SNAPSHOT_ID,
    TRAIN_DEV_ID,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _require_clean_source,
    _seed_everything,
    _validate_data,
    _validate_profile_and_test_surface,
)

from research.prototypes.paper_contract.evaluator import VisitPrediction, evaluate  # noqa: E402


def _max_state_diff(left: Mapping[str, torch.Tensor], right: Mapping[str, torch.Tensor]) -> float:
    if left.keys() != right.keys():
        raise RuntimeError("matched pair state_dict keys differ")
    maximum = 0.0
    for key in left:
        first, second = left[key], right[key]
        if first.shape != second.shape or first.dtype != second.dtype:
            raise RuntimeError("matched pair state tensor metadata differs: " + key)
        if first.dtype.is_floating_point:
            maximum = max(maximum, float((first - second).abs().max().item()))
        elif not torch.equal(first, second):
            raise RuntimeError("matched pair nonfloating state differs: " + key)
    return maximum


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(args: argparse.Namespace) -> dict[str, Any]:
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev identity mismatch")
    _validate_profile_and_test_surface(snapshot, train_dev)

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    _assert(profile["profile_id"] == PROFILE_ID, "profile identity changed")
    _assert(profile["split"]["test"]["membership_loaded"] is False, "Test membership was accessed")
    _assert(profile["split"]["test"]["targets_loaded"] is False, "Test targets were accessed")
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
    dx_count, proc_count, vocabulary = _validate_data(
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    leakage_row = copy.deepcopy(train_rows[0])
    altered_row = copy.deepcopy(leakage_row)
    altered_row["_medications"] = [
        int((int(value) + 1) % MEDICATIONS) for value in leakage_row["_medications"]
    ]
    _assert(
        _model_rows([leakage_row]) == _model_rows([altered_row]),
        "target medication leaked into model row",
    )

    history_indices = [index for index, row in enumerate(train_rows) if len(row["history"]) >= 2]
    history_indices = sorted(
        history_indices, key=lambda index: (-len(train_rows[index]["history"]), index)
    )[:BATCH_SIZE]
    if len(history_indices) < 2:
        raise RuntimeError("preflight could not find enough history-bearing Train rows")
    rows = _model_rows([train_rows[index] for index in history_indices])
    packed_cpu = pack_rows(rows, dx_count, proc_count)
    target = torch.from_numpy(train_targets[history_indices])
    target_sets = [
        tuple(np.flatnonzero(train_targets[index] > 0.5).tolist()) for index in history_indices
    ]
    reversed_sets = [tuple(reversed(values)) for values in target_sets]

    device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    packed = {key: value.to(device) for key, value in packed_cpu.items()}
    target = target.to(device)
    configure_numeric_policy()

    _seed_everything()
    control = EBRAModel(dx_count, proc_count).to(device)
    control.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
    control_state = {
        key: value.detach().cpu().clone() for key, value in control.state_dict().items()
    }
    _seed_everything()
    candidate = EBRAModel(dx_count, proc_count).to(device)
    candidate.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
    candidate_state = {
        key: value.detach().cpu().clone() for key, value in candidate.state_dict().items()
    }
    init_diff = _max_state_diff(control_state, candidate_state)
    _assert(init_diff == 0.0, "matched pair initialization differs")
    control_count = parameter_count(control)
    candidate_count = parameter_count(candidate)
    _assert(
        abs(control_count - candidate_count) / float(control_count) <= 0.01,
        "parameter counts differ by more than 1%",
    )
    _assert(control_count == candidate_count, "matched pair parameter counts differ")

    control.train()
    control_output = control(packed)
    control_loss = fixed_multilabel_loss(control_output, target)
    _assert(torch.isfinite(control_loss).item(), "control loss is non-finite")
    control_loss.backward()
    _assert(
        any(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in control.parameters()
        ),
        "control has no finite gradient",
    )

    candidate.train()
    candidate_output = candidate(packed)
    candidate_loss, labels = assignment_loss(candidate_output, target_sets)
    permuted_loss, permuted_labels = assignment_loss(candidate_output, reversed_sets)
    _assert(torch.isfinite(candidate_loss).item(), "candidate loss is non-finite")
    _assert(
        torch.allclose(candidate_loss, permuted_loss, atol=1e-7, rtol=0.0),
        "candidate loss changes under target permutation",
    )
    _assert(
        torch.equal(labels, permuted_labels),
        "candidate assignment changes under target permutation",
    )
    candidate_loss.backward()
    _assert(
        any(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in candidate.parameters()
        ),
        "candidate has no finite gradient",
    )

    medication_logits = candidate_output["medication_logits"].detach().cpu().numpy()
    null_logits = candidate_output["null_logits"].detach().cpu().numpy()
    decoded, scores = assignment_decode(medication_logits[0], null_logits[0])
    _assert(len(decoded) == len(set(decoded)), "assignment decoder emitted duplicate medications")
    _assert(len(decoded) <= MEDICATIONS, "assignment decoder exceeded slot capacity")
    _assert(np.isfinite(scores).all(), "candidate continuous scores are non-finite")
    _assert(
        candidate_output["medication_logits"].shape == (len(rows), SLOTS, MEDICATIONS),
        "full score matrix was not computed",
    )

    sample = VisitPrediction(
        "p", "v", (vocabulary[0],), (vocabulary[0],), tuple([1.0] + [0.0] * (MEDICATIONS - 1))
    )
    evaluated = evaluate((sample,), vocabulary=vocabulary)
    _assert(
        evaluated["jaccard"] == 1.0 and evaluated["f1"] == 1.0,
        "repository-native evaluator pass failed",
    )

    return {
        "status": "PASS",
        "source_revision": args.source_revision,
        "profile_id": PROFILE_ID,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "parameter_count": {"fixed_multilabel": control_count, "ebra_assignment": candidate_count},
        "initialization_max_abs_diff": init_diff,
        "full_score_matrix_shape": list(candidate_output["medication_logits"].shape),
        "target_leakage_check": "PASS",
        "finite_forward_backward": {"fixed_multilabel": "PASS", "ebra_assignment": "PASS"},
        "permutation_invariance": {
            "loss_abs_diff": float((candidate_loss - permuted_loss).abs().item()),
            "labels_equal": True,
        },
        "duplicate_free_assignment_decode": "PASS",
        "repository_native_evaluation": "PASS",
        "test_loaded": False,
        "device": device_name,
    }


def parse_args(argv: Any = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
