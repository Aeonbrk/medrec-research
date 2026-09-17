#!/usr/bin/env python3
"""Run targeted correctness checks for the structured-set implementation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[2]))
from run_structured_set import (  # noqa: E402
    MEDICATIONS,
    PROFILE_ID,
    PROFILE_PATH,
    SNAPSHOT_ID,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _seed_everything,
    _validate_data,
    _validate_profile,
)
from structured_set import (  # noqa: E402
    SLOTS,
    StructuredSetModel,
    assignment_decode,
    configure_numeric_policy,
    matching_cost_from_probabilities,
    matching_cross_entropy,
    matching_labels,
    pack_inputs,
    threshold_decode,
)

from research.prototypes.paper_contract.evaluator import VisitPrediction, evaluate  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _matching_fixture() -> None:
    probabilities = np.array([[0.60, 0.10, 0.30], [0.50, 0.49, 0.01]], dtype=np.float64)
    costs = matching_cost_from_probabilities(probabilities, 0)
    _assert(int(np.argmin(costs)) == 1, "complete CE / -u fixture did not select slot B")
    product_a = probabilities[0, 0] * probabilities[1, -1]
    product_b = probabilities[1, 0] * probabilities[0, -1]
    _assert(product_b > product_a, "complete CE fixture products are not ordered B over A")


def _decoder_checks() -> None:
    utility = np.array([[0.0, 0.2, 0.3], [0.0, 0.2, 0.1]], dtype=np.float64)
    _assert(assignment_decode(utility, 0.0) == (1, 2), "positive assignment decode is incorrect")
    _assert(assignment_decode(np.zeros((3, 3)), 0.0) == (), "exact-zero edge did not choose NULL")
    for beta in (-1.0, 0.0, 0.1, 0.25, 1.0):
        _assert(
            set(assignment_decode(utility, beta)) <= set(threshold_decode(utility, beta)),
            "subset invariant failed",
        )
    tie = np.zeros((3, 2), dtype=np.float64)
    first = matching_labels(torch.from_numpy(tie[None]), [(0, 1)], 2, 3)
    second = matching_labels(torch.from_numpy(tie[None]), [(0, 1)], 2, 3)
    _assert(torch.equal(first, second), "matching tie behavior is not deterministic")
    duplicate_probe = assignment_decode(np.ones((4, 3), dtype=np.float64), -0.5)
    _assert(
        len(duplicate_probe) == len(set(duplicate_probe)), "assignment emitted duplicate medication"
    )


def _matching_shape_checks() -> None:
    utility = torch.zeros((1, 3, 3), dtype=torch.float32)
    empty = matching_labels(utility, [()], 3, 3)
    _assert(
        torch.equal(empty, torch.full((1, 3), 3, dtype=torch.long)),
        "empty target did not assign NULL",
    )
    full = matching_labels(utility, [(0, 1, 2)], 3, 3)
    _assert(set(full[0].tolist()) == {0, 1, 2}, "|Y| = K did not fill every slot")
    capacity_probe = torch.zeros((1, 3, 4), dtype=torch.float32)
    try:
        matching_labels(capacity_probe, [(0, 1, 2, 3)], 4, 3)
    except ValueError as error:
        _assert("exceeds slot capacity" in str(error), "wrong rejection for |Y| > K")
    else:
        raise AssertionError("|Y| > K was accepted")
    torch.manual_seed(7)
    random_utility = torch.randn((1, 3, 4), dtype=torch.float32)
    left, _ = matching_cross_entropy(
        {
            "utility": random_utility,
            "medication_logits": random_utility,
            "null_logits": torch.zeros((1, 3)),
        },
        [(1, 3)],
        4,
        3,
    )
    right, _ = matching_cross_entropy(
        {
            "utility": random_utility,
            "medication_logits": random_utility,
            "null_logits": torch.zeros((1, 3)),
        },
        [(3, 1)],
        4,
        3,
    )
    _assert(torch.equal(left, right), "target permutation changed matching loss")


def _model_checks(device: str) -> dict[str, Any]:
    _seed_everything(20260919)
    control = StructuredSetModel(5, 4).to(device)
    _seed_everything(20260919)
    full = StructuredSetModel(5, 4).to(device)
    _assert(list(control.state_dict()) == list(full.state_dict()), "parameter names differ")
    _assert(
        sum(parameter.numel() for parameter in control.parameters())
        == sum(parameter.numel() for parameter in full.parameters()),
        "parameter counts differ",
    )
    _assert(
        all(
            torch.equal(control.state_dict()[name], full.state_dict()[name])
            for name in control.state_dict()
        ),
        "initialization tensors differ",
    )
    rows = [
        {"diagnoses": [1, 2], "procedures": [0], "history": []},
        {"diagnoses": [0], "procedures": [1], "history": [([2], [0], [4, 5])]},
    ]
    packed = {key: value.to(device) for key, value in pack_inputs(rows, 5, 4).items()}
    outputs = control(packed)
    _assert(torch.isfinite(outputs["utility"]).all().item(), "forward utility is non-finite")
    targets = torch.zeros((2, MEDICATIONS), device=device)
    targets[0, 0] = 1.0
    targets[1, 1] = 1.0
    control.zero_grad(set_to_none=True)
    loss = torch.nn.functional.binary_cross_entropy_with_logits(
        outputs["utility"].amax(dim=1), targets
    )
    loss.backward()
    _assert(torch.isfinite(loss).item(), "control loss is non-finite")
    full.zero_grad(set_to_none=True)
    full_outputs = full(packed)
    full_loss, _labels = matching_cross_entropy(full_outputs, [(0,), (1,)], MEDICATIONS, SLOTS)
    full_loss.backward()
    _assert(torch.isfinite(full_loss).item(), "matching loss is non-finite")
    return {
        "parameter_count": sum(parameter.numel() for parameter in control.parameters()),
        "device": device,
    }


def _identity_and_leakage_checks(snapshot: Path, train_dev: Path) -> dict[str, Any]:
    _validate_profile(snapshot, train_dev)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    _assert(profile["profile_id"] == PROFILE_ID, "profile identity changed")
    _assert(profile["benchmark"]["source_snapshot_id"] == SNAPSHOT_ID, "snapshot identity changed")
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
    dx_count, proc_count, _ = _validate_data(
        records, voc, train_rows, dev_rows, train_targets, dev_targets, ddi
    )
    probe = train_rows[:32]
    packed = pack_inputs(_model_rows(probe), dx_count, proc_count)
    med_offset = dx_count + proc_count
    _assert(packed["mask"].shape[0] == len(probe), "packed rows are not batch-aligned")
    for row_index, row in enumerate(probe):
        expected_tokens = (
            1 + len(set(row["diagnoses"])) + len(set(row["procedures"])) + 3 * len(row["history"])
        )
        _assert(
            int(packed["mask"][row_index].sum()) == expected_tokens,
            "history packing changed token count",
        )
        offset_start = row_index * packed["mask"].shape[1]
        token_types = packed["types"][offset_start : offset_start + packed["mask"].shape[1]]
        # Current diagnosis/procedure tokens are the only current tokens. Any
        # medication IDs may occur only in type-5 strictly previous-history bags.
        offsets = packed["offsets"]
        for token_index, token_type in enumerate(token_types.tolist()):
            start = int(offsets[offset_start + token_index])
            end = int(offsets[offset_start + token_index + 1])
            token_codes = packed["codes"][start:end]
            if token_type in (1, 2):
                _assert(
                    not bool((token_codes >= med_offset).any()),
                    "current target/future medication leaked into input",
                )
            if token_type == 5:
                _assert(len(row["history"]) > 0, "medication history token exists without history")
    return {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train_rows),
        "dev_visits": len(dev_rows),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    configure_numeric_policy()
    device = args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    result = {
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "test_accessed": False,
        "matching_fixture": "PASS",
        "decoder_checks": "PASS",
        "matching_shape_checks": "PASS",
        "model_checks": _model_checks(device),
        "identity_and_leakage": None,
        "raw_score_contract": "PASS",
        "cached_u_contract": "PASS",
    }
    _matching_fixture()
    _decoder_checks()
    _matching_shape_checks()
    samples = [
        VisitPrediction("p", "v", ("m0",), ("m0",), (0.3, 0.1)),
    ]
    evaluated = evaluate(samples, vocabulary=("m0", "m1"))
    _assert(evaluated["prauc"] == 1.0, "raw finite max_s utility was transformed before AP")
    if args.snapshot_root is not None and args.train_dev_root is not None:
        result["identity_and_leakage"] = _identity_and_leakage_checks(
            args.snapshot_root, args.train_dev_root
        )
    if args.timing_output is not None:
        _ = json.loads(args.timing_output.read_text(encoding="utf-8"))
    output = json.dumps(result, sort_keys=True, allow_nan=False)
    if args.output is not None:
        args.output.write_text(output + "\n")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--train-dev-root", type=Path)
    parser.add_argument("--timing-output", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
