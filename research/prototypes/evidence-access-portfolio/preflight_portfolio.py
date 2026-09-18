#!/usr/bin/env python3
"""Decision-relevant preflight for the 8-lane evidence-access portfolio."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

import dill
import numpy as np
import torch

from portfolio_model import PAIR_MAP, VARIANTS, PortfolioModel, objective, pack_rows, parameter_count
from run_portfolio import (
    BATCH_SIZE,
    MEDICATIONS,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _require_clean_source,
    _seed_everything,
    _validate_data,
    _validate_profile,
)


def _max_state_diff(left: Dict[str, torch.Tensor], right: Dict[str, torch.Tensor]) -> float:
    if left.keys() != right.keys():
        raise RuntimeError("matched-pair state_dict keys differ")
    maximum = 0.0
    for key in left:
        a, b = left[key], right[key]
        if a.shape != b.shape or a.dtype != b.dtype:
            raise RuntimeError("matched-pair state tensor metadata differs: " + key)
        if a.dtype.is_floating_point:
            maximum = max(maximum, float((a - b).abs().max().item()))
        elif not torch.equal(a, b):
            raise RuntimeError("matched-pair nonfloating state differs: " + key)
    return maximum


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
    dx, proc, _vocabulary = _validate_data(
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    leakage_row = copy.deepcopy(train_rows[0])
    altered_row = copy.deepcopy(leakage_row)
    altered_row["_medications"] = [int((int(x) + 1) % MEDICATIONS) for x in leakage_row["_medications"]]
    if _model_rows([leakage_row]) != _model_rows([altered_row]):
        raise RuntimeError("current target medication leaked into model row")

    def evidence_size(row: Mapping[str, Any]) -> int:
        size = len(row["diagnoses"]) + len(row["procedures"])
        for visit in row["history"]:
            size += len(visit[0]) + len(visit[1]) + len(visit[2])
        return size

    history_indices = [
        index for index, row in enumerate(train_rows) if len(row["history"]) >= 2
    ]
    history_indices = sorted(
        history_indices, key=lambda index: (-evidence_size(train_rows[index]), index)
    )[:BATCH_SIZE]
    if len(history_indices) < 2:
        raise RuntimeError("preflight could not find enough history-bearing Train rows")
    history_rows = [train_rows[index] for index in history_indices]
    first_rows = [row for row in train_rows if len(row["history"]) == 0][:BATCH_SIZE]
    payload = _model_rows(history_rows)
    packed_cpu = pack_rows(payload, dx, proc)
    first_packed_cpu = pack_rows(_model_rows(first_rows), dx, proc)
    target = torch.from_numpy(train_targets[history_indices])

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for portfolio preflight")
    device = torch.device("cuda")
    ddi_tensor = torch.from_numpy(ddi).to(device)
    packed = {key: value.to(device) for key, value in packed_cpu.items()}
    first_packed = {key: value.to(device) for key, value in first_packed_cpu.items()}
    target = target.to(device)

    pair_results: Dict[str, Any] = {}
    variant_results: Dict[str, Any] = {}
    initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    logits: Dict[str, torch.Tensor] = {}
    first_logits: Dict[str, torch.Tensor] = {}

    for variant in VARIANTS:
        _seed_everything()
        model = PortfolioModel(dx, proc, variant).to(device)
        model.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
        initialized[variant] = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        model.train()
        output = model(packed)
        loss, bce, ddi_loss = objective(output, target, ddi_tensor)
        if not all(torch.isfinite(value) for value in (output, loss, bce, ddi_loss)):
            raise RuntimeError("non-finite preflight output for " + variant)
        loss.backward()
        grad_count = sum(
            1 for parameter in model.parameters()
            if parameter.grad is not None and torch.isfinite(parameter.grad).all()
        )
        if grad_count == 0:
            raise RuntimeError("no finite parameter gradients for " + variant)
        model.eval()
        with torch.no_grad():
            logits[variant] = model(packed).detach().cpu()
            first_logits[variant] = model(first_packed).detach().cpu()
        variant_results[variant] = {
            "parameter_count": parameter_count(model),
            "finite_gradient_parameter_tensors": grad_count,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        del model
        torch.cuda.empty_cache()

    for pair, (control, candidate) in PAIR_MAP.items():
        init_diff = _max_state_diff(initialized[control], initialized[candidate])
        if init_diff != 0.0:
            raise RuntimeError("matched-pair initialization differs for " + pair)
        if variant_results[control]["parameter_count"] != variant_results[candidate]["parameter_count"]:
            raise RuntimeError("matched-pair parameter counts differ for " + pair)
        behavior_diff = float((logits[control] - logits[candidate]).abs().max().item())
        if behavior_diff <= 1e-8:
            raise RuntimeError("matched-pair mechanism is behaviorally inactive for " + pair)
        result = {
            "control": control,
            "candidate": candidate,
            "parameter_count": variant_results[control]["parameter_count"],
            "initialization_max_abs_diff": init_diff,
            "history_batch_output_max_abs_diff": behavior_diff,
        }
        if pair == "temporal":
            no_history_diff = float(
                (first_logits[control] - first_logits[candidate]).abs().max().item()
            )
            if no_history_diff > 1e-6:
                raise RuntimeError(
                    "temporal pair differs when no history exists; mechanism is not isolated"
                )
            result["no_history_output_max_abs_diff"] = no_history_diff
        pair_results[pair] = result

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
        "matched_pairs": pair_results,
        "variants": variant_results,
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
