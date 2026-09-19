#!/usr/bin/env python3
"""Decision-relevant CUDA preflight for the medication-evidence competition screen."""
from __future__ import annotations

import argparse
import copy
import json
import math
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

from portfolio_model import DIM, MEDICATIONS, PortfolioModel  # noqa: E402
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
from memb_model import MEMB_VARIANTS, MEMBModel, objective, pack_rows, parameter_count  # noqa: E402
from run_memb import LANES, _make_model, _seed_everything  # noqa: E402


def _snapshot(model: torch.nn.Module) -> Dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def _state_diff(left: Dict[str, torch.Tensor], right: Dict[str, torch.Tensor]) -> float:
    if left.keys() != right.keys():
        raise RuntimeError("matched state_dict keys differ")
    maximum = 0.0
    for key in left:
        a, b = left[key], right[key]
        if a.shape != b.shape or a.dtype != b.dtype:
            raise RuntimeError("matched state metadata differs: " + key)
        if a.dtype.is_floating_point:
            maximum = max(maximum, float((a - b).abs().max().item()))
        elif not torch.equal(a, b):
            raise RuntimeError("matched nonfloating state differs: " + key)
    return maximum


def _direct_code_objects(
    model: PortfolioModel, batch: Dict[str, torch.Tensor]
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    encoded = model._encode(batch)
    memory, mask = model._flat_evidence(encoded, batch)
    normalized = model.read_norm(memory)
    keys = model.read_key(normalized)
    values = model.read_value(normalized)
    q = model.read_query(model._drugs())
    raw = torch.einsum("md,bnd->bmn", q, keys) / math.sqrt(DIM)
    return raw, values, mask


def _direct_local_raw(
    model: PortfolioModel, batch: Dict[str, torch.Tensor]
) -> tuple[torch.Tensor, torch.Tensor]:
    encoded = model._encode(batch)
    memory, mask = model._flat_evidence(encoded, batch)
    normalized = model.read_norm(memory)
    keys = model.local_k(normalized)
    drugs = model._drugs()
    chunks = []
    from portfolio_model import CHUNK

    for start in range(0, MEDICATIONS, CHUNK):
        selected = drugs[start : start + CHUNK]
        q = model.local_q(selected)
        interaction = q[None, :, None, :] * keys[:, None, :, :]
        hidden = model.local_hidden(interaction)
        chunks.append(model.local_out(hidden).squeeze(-1))
    return torch.cat(chunks, dim=1), mask


def _max_valid_difference(left: torch.Tensor, right: torch.Tensor, mask: torch.Tensor) -> float:
    expanded = mask[:, None, :].expand_as(left)
    return float((left[expanded] - right[expanded]).abs().max().item())


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
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    leakage_row = copy.deepcopy(train_rows[0])
    altered_row = copy.deepcopy(leakage_row)
    altered_row["_medications"] = [
        int((int(value) + 1) % MEDICATIONS) for value in leakage_row["_medications"]
    ]
    if _model_rows([leakage_row]) != _model_rows([altered_row]):
        raise RuntimeError("current medication target leaked into model payload")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MEMB preflight")
    device = torch.device("cuda")
    ddi_tensor = torch.from_numpy(ddi).to(device)
    prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)

    def evidence_size(row: Dict[str, Any]) -> int:
        total = len(row["diagnoses"]) + len(row["procedures"])
        for visit in row["history"]:
            total += len(visit[0]) + len(visit[1]) + len(visit[2])
        return total

    history_indices = [i for i, row in enumerate(train_rows) if len(row["history"]) >= 2]
    history_indices = sorted(
        history_indices, key=lambda i: (-evidence_size(train_rows[i]), i)
    )[:BATCH_SIZE]
    if len(history_indices) < 2:
        raise RuntimeError("insufficient history-bearing Train rows")
    history_batch = {
        key: value.to(device)
        for key, value in pack_rows(
            _model_rows([train_rows[i] for i in history_indices]), dx, proc
        ).items()
    }
    history_targets = torch.from_numpy(train_targets[history_indices]).to(device)
    first_rows = [row for row in train_rows if len(row["history"]) == 0][:BATCH_SIZE]
    if not first_rows:
        raise RuntimeError("no first-visit rows for no-history check")
    first_batch = {
        key: value.to(device)
        for key, value in pack_rows(_model_rows(first_rows), dx, proc).items()
    }

    _seed_everything()
    foundation = PortfolioModel(dx, proc, "resolution_code").to(device)
    foundation.initialize_prevalence(prevalence)
    foundation.eval()
    foundation_state = _snapshot(foundation)
    with torch.no_grad():
        foundation_raw, _foundation_values, foundation_mask = _direct_code_objects(
            foundation, history_batch
        )
        foundation_output = foundation(history_batch)

    _seed_everything()
    prediction_local = PortfolioModel(dx, proc, "prediction_local").to(device)
    prediction_local.initialize_prevalence(prevalence)
    prediction_local.eval()
    prediction_local_state = _snapshot(prediction_local)
    with torch.no_grad():
        prediction_local_raw, prediction_local_mask = _direct_local_raw(
            prediction_local, history_batch
        )
        prediction_local_output = prediction_local(history_batch)

    if _state_diff(foundation_state, prediction_local_state) != 0.0:
        raise RuntimeError("historical FineCode and PredictionLocal parameter graphs drifted")

    lane_reports: Dict[str, Any] = {}
    initialized: Dict[str, Dict[str, torch.Tensor]] = {}
    outputs: Dict[str, torch.Tensor] = {}
    code_debug: Dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}
    local_debug: Dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}

    for lane, variant in LANES.items():
        _seed_everything()
        model = _make_model(dx, proc, variant).to(device)
        model.initialize_prevalence(prevalence)
        initialized[lane] = _snapshot(model)

        model.train()
        torch.cuda.reset_peak_memory_stats(device)
        logits = model(history_batch)
        loss, bce, ddi_loss = objective(logits, history_targets, ddi_tensor)
        if not (
            bool(torch.isfinite(logits).all().item())
            and bool(torch.isfinite(loss).item())
            and bool(torch.isfinite(bce).item())
            and bool(torch.isfinite(ddi_loss).item())
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
            if isinstance(model, MEMBModel):
                if variant.endswith("_code"):
                    raw, transformed, mask = model.debug_code_objects(history_batch)
                    code_debug[lane] = (
                        raw.detach().cpu(),
                        transformed.detach().cpu(),
                        mask.detach().cpu(),
                    )
                elif variant.endswith("_local"):
                    raw, transformed, mask = model.debug_local_objects(history_batch)
                    local_debug[lane] = (
                        raw.detach().cpu(),
                        transformed.detach().cpu(),
                        mask.detach().cpu(),
                    )
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

    counts = {report["parameter_count"] for report in lane_reports.values()}
    if len(counts) != 1:
        raise RuntimeError("MEMB lanes do not share one parameter budget")
    reference_state = initialized["foundation_code_anchor"]
    for lane, state in initialized.items():
        if _state_diff(reference_state, state) != 0.0:
            raise RuntimeError("matched MEMB initialization differs: " + lane)

    code_raw_diffs: Dict[str, float] = {}
    for lane in ("mutual_code", "scale2_code", "specificity_code"):
        raw, _transformed, mask = code_debug[lane]
        if not torch.equal(mask, foundation_mask.detach().cpu()):
            raise RuntimeError("code evidence support drifted: " + lane)
        code_raw_diffs[lane] = float(
            (raw - foundation_raw.detach().cpu()).abs().max().item()
        )
        if code_raw_diffs[lane] > 1e-7:
            raise RuntimeError("raw FineCode affinity drifted: " + lane)

    local_raw_diffs: Dict[str, float] = {}
    for lane in ("mutual_local", "scale2_local", "specificity_local"):
        raw, _transformed, mask = local_debug[lane]
        if not torch.equal(mask, prediction_local_mask.detach().cpu()):
            raise RuntimeError("local evidence support drifted: " + lane)
        local_raw_diffs[lane] = float(
            (raw - prediction_local_raw.detach().cpu()).abs().max().item()
        )
        if local_raw_diffs[lane] > 1e-7:
            raise RuntimeError("raw PredictionLocal potential drifted: " + lane)

    raw_code, mutual_code_transformed, code_mask = code_debug["mutual_code"]
    _, scale2_code_transformed, _ = code_debug["scale2_code"]
    code_commonness = (
        -torch.logsumexp(raw_code, dim=1, keepdim=True)
        + math.log(float(MEDICATIONS))
    ).expand_as(raw_code)
    code_formula_error = _max_valid_difference(
        mutual_code_transformed - scale2_code_transformed,
        code_commonness,
        code_mask,
    )

    raw_local, mutual_local_transformed, local_mask = local_debug["mutual_local"]
    _, scale2_local_transformed, _ = local_debug["scale2_local"]
    local_commonness = (
        -torch.logsumexp(raw_local, dim=1, keepdim=True)
        + math.log(float(MEDICATIONS))
    ).expand_as(raw_local)
    local_formula_error = _max_valid_difference(
        mutual_local_transformed - scale2_local_transformed,
        local_commonness,
        local_mask,
    )
    if code_formula_error > 1e-6 or local_formula_error > 1e-6:
        raise RuntimeError("commonness attribution formula is not exact")

    anchor_foundation_diff = float(
        (outputs["foundation_code_anchor"] - foundation_output.detach().cpu())
        .abs()
        .max()
        .item()
    )
    anchor_local_diff = float(
        (outputs["prediction_local_anchor"] - prediction_local_output.detach().cpu())
        .abs()
        .max()
        .item()
    )
    if anchor_foundation_diff > 1e-7 or anchor_local_diff > 1e-7:
        raise RuntimeError("historical anchor identity drifted")

    pairs = {
        "code_commonness_scale2": ("scale2_code", "mutual_code"),
        "code_commonness_scale1": ("foundation_code_anchor", "specificity_code"),
        "local_commonness_scale2": ("scale2_local", "mutual_local"),
        "local_commonness_scale1": ("prediction_local_anchor", "specificity_local"),
        "code_sharpening": ("foundation_code_anchor", "scale2_code"),
        "local_sharpening": ("prediction_local_anchor", "scale2_local"),
    }
    behavioral: Dict[str, Any] = {}
    for name, (control, candidate) in pairs.items():
        difference = float((outputs[control] - outputs[candidate]).abs().max().item())
        if difference <= 1e-8:
            raise RuntimeError("mechanism behaviorally inactive: " + name)
        behavioral[name] = {
            "control": control,
            "candidate": candidate,
            "history_batch_output_max_abs_diff": difference,
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
        "target_leakage_check": "PASS",
        "matched_parameter_count": next(iter(counts)),
        "shared_initialization_max_abs_diff": 0.0,
        "raw_code_affinity_max_abs_diff": code_raw_diffs,
        "raw_local_potential_max_abs_diff": local_raw_diffs,
        "commonness_formula_max_abs_error": {
            "code": code_formula_error,
            "local": local_formula_error,
        },
        "anchor_identity": {
            "foundation_code_output_max_abs_diff": anchor_foundation_diff,
            "prediction_local_output_max_abs_diff": anchor_local_diff,
        },
        "lanes": lane_reports,
        "behavioral_differences": behavioral,
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
