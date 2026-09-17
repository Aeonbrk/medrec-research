#!/usr/bin/env python3
"""Run targeted correctness checks for the RIME implementation."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[2]))
from rime import (  # noqa: E402
    FLIP_CAP,
    MEDICATIONS,
    RIMEModel,
    configure_numeric_policy,
    greedy_decode,
    pack_inputs,
    sample_contexts,
    scores_for_set,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _model_inputs(device: str) -> dict[str, torch.Tensor]:
    rows = [
        {"diagnoses": [1, 2], "procedures": [0], "history": []},
        {"diagnoses": [0], "procedures": [1], "history": [([2], [0], [4, 5])]},
    ]
    return {key: value.to(device) for key, value in pack_inputs(rows, 5, 4).items()}


def _parameter_checks(device: str) -> dict[str, Any]:
    torch.manual_seed(20260920)
    composition = RIMEModel(5, 4, "composition", medication_count=MEDICATIONS).to(device)
    torch.manual_seed(20260920)
    control = RIMEModel(5, 4, "count_only", medication_count=MEDICATIONS).to(device)
    _assert(list(composition.state_dict()) == list(control.state_dict()), "state keys differ")
    _assert(
        sum(parameter.numel() for parameter in composition.parameters())
        == sum(parameter.numel() for parameter in control.parameters()),
        "parameter counts differ",
    )
    _assert(
        all(
            torch.equal(composition.state_dict()[name], control.state_dict()[name])
            for name in composition.state_dict()
        ),
        "matched initialization differs",
    )
    return {
        "parameter_count": sum(parameter.numel() for parameter in composition.parameters()),
        "device": device,
    }


def _context_checks() -> None:
    targets = torch.zeros((3, MEDICATIONS), dtype=torch.float32)
    targets[0, [1, 4, 8]] = 1.0
    targets[1, [2]] = 1.0
    targets[2, :] = 1.0
    # The all-medication row must be rejected because C_err needs M\Y.
    try:
        sample_contexts(targets, random.Random(3))
    except ValueError as error:
        _assert("negative medication" in str(error), "wrong full-target rejection")
    else:
        raise AssertionError("target equal to the full vocabulary was accepted")
    targets = targets[:2]
    positive, erroneous = sample_contexts(targets, random.Random(3))
    _assert(bool((positive <= targets.bool()).all()), "C_pos is not a subset of Y")
    _assert(bool((erroneous >= positive).all()), "C_err dropped C_pos")
    _assert(
        bool((erroneous.sum(dim=1) - positive.sum(dim=1) == 1).all()),
        "C_err did not add exactly one negative medication",
    )


def _utility_identity_checks(device: str) -> dict[str, Any]:
    inputs = _model_inputs(device)
    torch.manual_seed(20260920)
    model = RIMEModel(5, 4, "composition", medication_count=MEDICATIONS).to(device).eval()
    with torch.no_grad():
        encoded = model(inputs)
        contexts = torch.zeros((2, MEDICATIONS), dtype=torch.bool, device=device)
        contexts[0, [1, 4, 8]] = True
        contexts[1, [2, 6]] = True
        for row in range(contexts.shape[0]):
            encoded_row = {key: value[row : row + 1] for key, value in encoded.items()}
            for medication in range(MEDICATIONS):
                base = contexts[row : row + 1].clone()
                base[0, medication] = False
                augmented = base.clone()
                augmented[0, medication] = True
                expected = (
                    model.utility(encoded_row, augmented)[0] - model.utility(encoded_row, base)[0]
                )
                marginal = model.marginal_logits(encoded_row, base)[0, medication]
                _assert(
                    torch.allclose(marginal, expected, atol=2e-3, rtol=2e-3),
                    "marginal utility identity failed",
                )
        selected, adds, removes, cap_hits = greedy_decode(model, encoded, flip_cap=FLIP_CAP)
        if not bool(cap_hits.any()):
            add, remove = model.flip_gains(encoded, selected)
            valid_add = add[~selected]
            valid_remove = remove[selected]
            if valid_add.numel():
                _assert(bool((valid_add <= 1e-6).all()), "decoder stopped with a positive add gain")
            if valid_remove.numel():
                _assert(
                    bool((valid_remove <= 1e-6).all()),
                    "decoder stopped with a positive remove gain",
                )
        score = scores_for_set(model, encoded, selected)
        for row in range(selected.shape[0]):
            encoded_row = {key: value[row : row + 1] for key, value in encoded.items()}
            for medication in range(MEDICATIONS):
                context = selected[row : row + 1].clone()
                context[0, medication] = False
                expected = model.marginal_logits(encoded_row, context)[0, medication]
                _assert(
                    torch.allclose(score[row, medication], expected, atol=2e-2, rtol=2e-2),
                    "PRAUC score identity failed",
                )
    return {
        "decoder_adds": adds.tolist(),
        "decoder_removes": removes.tolist(),
        "decoder_cap_hits": cap_hits.tolist(),
    }


def _control_invariance_check(device: str) -> None:
    inputs = _model_inputs(device)
    torch.manual_seed(20260920)
    model = RIMEModel(5, 4, "count_only", medication_count=MEDICATIONS).to(device).eval()
    with torch.no_grad():
        encoded = model(inputs)
        left = torch.zeros((2, MEDICATIONS), dtype=torch.bool, device=device)
        right = torch.zeros((2, MEDICATIONS), dtype=torch.bool, device=device)
        left[0, [1, 4, 8]] = True
        right[0, [2, 6, 12]] = True
        left[1, [0, 9]] = True
        right[1, [5, 10]] = True
        left_scores = model.marginal_logits(encoded, left)
        right_scores = model.marginal_logits(encoded, right)
        # Compare a candidate absent from both contexts.  The declared
        # marginal removes the candidate before adding it back, so a candidate
        # present in only one context would intentionally have a different
        # cardinality base.
        _assert(
            torch.allclose(left_scores[:, 20], right_scores[:, 20], atol=1e-6, rtol=1e-6),
            "count-only control responds to same-cardinality composition",
        )


def run(args: argparse.Namespace) -> dict[str, Any]:
    configure_numeric_policy()
    device = args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    _context_checks()
    parameters = _parameter_checks(device)
    identity = _utility_identity_checks(device)
    _control_invariance_check(device)
    result = {
        "status": "PASS",
        "seed": 20260920,
        "test_accessed": False,
        "context_sampling": "PASS",
        "parameter_matching": parameters,
        "utility_and_decoder_identities": identity,
        "count_only_composition_invariance": "PASS",
    }
    output = json.dumps(result, sort_keys=True, allow_nan=False)
    if args.output is not None:
        args.output.write_text(output + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
