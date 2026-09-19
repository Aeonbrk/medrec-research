#!/usr/bin/env python3
"""Run one 30-epoch lane of the MSED evidence-distribution screen."""
from __future__ import annotations

import argparse
import json
import math
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

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
    GRADIENT_CLIP,
    LEARNING_RATE,
    NATIVE_DEFAULT,
    OPERATING_POINTS,
    PROFILE_ID,
    SNAPSHOT_ID,
    TRAIN_DEV_ID,
    WEIGHT_DECAY,
    _best_key,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _require_clean_source,
    _surface,
    _validate_data,
    _validate_profile,
    _write_json,
)
from research.prototypes.paper_contract.evaluator import (  # noqa: E402
    SelectionCandidate,
    select_joint,
)
from msed_model import (  # noqa: E402
    ALL_VARIANTS,
    MSED_VARIANTS,
    MSEDModel,
    configure_numeric_policy,
    objective,
    pack_rows,
    parameter_count,
)

DEFAULT_EPOCHS = 30
HORIZON_SAFE_MAX_EPOCH = 25

TORCH_SEED = 1203
CUDA_SEED = 1203
PYTHON_SEED = 1203
NUMPY_SEED = 2048

LANES: Dict[str, str] = {
    "msed_ecf_global": "msed_ecf_global",
    "point_lme_global": "point_lme_global",
    "point_mean_global": "point_mean_global",
    "point_max_global": "point_max_global",
    "msed_ecf_only": "msed_ecf_only",
    "point_lme_only": "point_lme_only",
    "prediction_local_anchor": "prediction_local_anchor",
    "foundation_code_anchor": "foundation_code_anchor",
}


def _seed_everything() -> None:
    random.seed(PYTHON_SEED)
    np.random.seed(NUMPY_SEED)
    torch.manual_seed(TORCH_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(CUDA_SEED)
    configure_numeric_policy()


def _make_model(diagnosis_count: int, procedure_count: int, variant: str) -> torch.nn.Module:
    if variant in MSED_VARIANTS:
        return MSEDModel(diagnosis_count, procedure_count, variant)
    if variant == "prediction_local_anchor":
        return PortfolioModel(diagnosis_count, procedure_count, "prediction_local")
    if variant == "foundation_code_anchor":
        return PortfolioModel(diagnosis_count, procedure_count, "resolution_code")
    raise RuntimeError("unknown MSED screen variant: " + variant)


def _predict_logits(
    model: torch.nn.Module,
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    dx_count: int,
    proc_count: int,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    chunks: List[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = {
                key: value.to(device)
                for key, value in pack_rows(
                    _model_rows(rows[start : start + BATCH_SIZE]),
                    dx_count,
                    proc_count,
                ).items()
            }
            chunks.append(model(batch).detach().cpu().numpy())
    values = np.concatenate(chunks, axis=0)
    if values.shape != targets.shape or not np.isfinite(values).all():
        raise RuntimeError("model logits are not finite and target-aligned")
    return values


def _config(
    lane: str,
    variant: str,
    numeric_policy: Mapping[str, Any],
    epochs: int,
) -> Dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "architecture_family": "MSED",
        "lane": lane,
        "variant": variant,
        "epochs": epochs,
        "horizon_safe_max_selected_epoch": HORIZON_SAFE_MAX_EPOCH,
        "batch_size_visits": BATCH_SIZE,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "loss": "BCE + 0.05 * normalized DDI penalty",
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
        "rng": {
            "torch": TORCH_SEED,
            "cuda_torch": CUDA_SEED,
            "python_random": PYTHON_SEED,
            "numpy": NUMPY_SEED,
        },
        "numeric_policy": dict(numeric_policy),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.lane not in LANES:
        raise RuntimeError("unknown MSED lane")
    variant = LANES[args.lane]
    if variant not in ALL_VARIANTS:
        raise RuntimeError("lane maps to unknown MSED screen variant")

    source_root = _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()

    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev identity mismatch")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if source_root == output or source_root in output.parents:
        raise RuntimeError("output directory must be outside source checkout")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    _validate_profile(snapshot, train_dev_root)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(index for index in range(split, len(records)) if _is_dev(index))
    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    dx_count, proc_count, vocabulary = _validate_data(
        records,
        voc,
        ddi,
        train_rows,
        dev_rows,
        train_targets,
        dev_targets,
    )

    epochs = int(args.epochs)
    if epochs not in {30, 60}:
        raise RuntimeError("MSED runner supports only 30 epochs or the exact 60-epoch censoring extension")

    numeric_policy = configure_numeric_policy()
    config = _config(args.lane, variant, numeric_policy, epochs)
    state: Dict[str, Any] = {
        "schema_version": 1,
        "status": "preflight_complete",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "lane": args.lane,
        "variant": variant,
        "config": config,
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "completed_epochs": 0,
        "selected_checkpoint": None,
        "selected_operating_point": None,
        "evaluations": [],
        "test_loaded": False,
    }

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the full MSED screen")
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "progress.json", state)

    _seed_everything()
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = _make_model(dx_count, proc_count, variant).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    generator = np.random.RandomState(NUMPY_SEED)
    state["status"] = "running"
    _write_json(output / "progress.json", state)

    best_candidate: Optional[SelectionCandidate] = None
    best_state: Optional[Dict[str, torch.Tensor]] = None
    best_dev_logits: Optional[np.ndarray] = None
    evaluations: List[Dict[str, Any]] = []
    start_time = time.time()
    updates_per_epoch = math.ceil(len(train_rows) / float(BATCH_SIZE))

    for epoch in range(1, epochs + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        loss_sum = 0.0
        bce_sum = 0.0
        ddi_sum = 0.0
        example_count = 0

        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch = {
                key: value.to(device)
                for key, value in pack_rows(
                    _model_rows([train_rows[int(index)] for index in indices]),
                    dx_count,
                    proc_count,
                ).items()
            }
            target = torch.from_numpy(train_targets[indices]).to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(batch)
            loss, bce, ddi_loss = objective(logits, target, ddi_tensor)
            if not bool(torch.isfinite(loss).item()):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()

            size = len(indices)
            loss_sum += float(loss.item()) * size
            bce_sum += float(bce.item()) * size
            ddi_sum += float(ddi_loss.item()) * size
            example_count += size

        dev_logits = _predict_logits(model, dev_rows, dev_targets, dx_count, proc_count, device)
        candidates: List[SelectionCandidate] = []
        candidate_results: List[Dict[str, Any]] = []
        for op_index, op in enumerate(OPERATING_POINTS):
            metrics = _surface(dev_rows, dev_targets, dev_logits, op, vocabulary, ddi)
            candidates.append(SelectionCandidate(epoch, op, metrics["jaccard"], op_index))
            candidate_results.append({"operating_point": op, "metrics": metrics})

        checkpoint_best = select_joint(
            candidates,
            operating_point_order=OPERATING_POINTS,
            native_default=NATIVE_DEFAULT,
        )
        if best_candidate is None or _best_key(checkpoint_best) < _best_key(best_candidate):
            best_candidate = checkpoint_best
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_logits = dev_logits.copy()
            torch.save(best_state, output / "selected_checkpoint.pt")
            np.save(output / "selected_dev_logits.npy", best_dev_logits)

        selected_metrics = next(
            item["metrics"]
            for item in candidate_results
            if item["operating_point"] == checkpoint_best.operating_point
        )
        entry = {
            "epoch": epoch,
            "train_loss": loss_sum / example_count,
            "train_bce": bce_sum / example_count,
            "train_ddi": ddi_sum / example_count,
            "selected_operating_point": checkpoint_best.operating_point,
            "selected_dev_jaccard": checkpoint_best.patient_macro_jaccard,
            "dev_metrics": selected_metrics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        evaluations.append(entry)
        state["evaluations"] = evaluations
        state["completed_epochs"] = epoch
        state["selected_checkpoint"] = best_candidate.checkpoint if best_candidate else None
        state["selected_operating_point"] = best_candidate.operating_point if best_candidate else None
        _write_json(output / "progress.json", state)

    if best_candidate is None or best_state is None or best_dev_logits is None:
        raise RuntimeError("no complete Dev checkpoint selected")

    model.load_state_dict(best_state)
    train_logits = _predict_logits(model, train_rows, train_targets, dx_count, proc_count, device)
    selected_train = _surface(
        train_rows,
        train_targets,
        train_logits,
        best_candidate.operating_point,
        vocabulary,
        ddi,
    )
    selected_dev = _surface(
        dev_rows,
        dev_targets,
        best_dev_logits,
        best_candidate.operating_point,
        vocabulary,
        ddi,
    )

    horizon_censored = (
        epochs == DEFAULT_EPOCHS and best_candidate.checkpoint > HORIZON_SAFE_MAX_EPOCH
    )
    result: Dict[str, Any] = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "lane": args.lane,
        "variant": variant,
        "architecture_family": "MSED",
        "config": config,
        "parameter_count": parameter_count(model),
        "split": state["split"],
        "completed_epochs": epochs,
        "updates_per_epoch": updates_per_epoch,
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_operating_point": best_candidate.operating_point,
        "selected_checkpoint_score": best_candidate.patient_macro_jaccard,
        "horizon_censored": horizon_censored,
        "metrics": {"Train": selected_train, "Dev": selected_dev},
        "epoch_30_Dev": evaluations[29]["dev_metrics"],
        "final_epoch_Dev": evaluations[-1]["dev_metrics"],
        "progress": evaluations,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "test_loaded": False,
    }

    state["status"] = "complete"
    state["horizon_censored"] = horizon_censored
    state["epoch_30_Dev"] = evaluations[29]["dev_metrics"]
    state["final_epoch_Dev"] = evaluations[-1]["dev_metrics"]
    _write_json(output / "progress.json", state)
    _write_json(output / "results.json", result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", choices=tuple(LANES), required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, choices=(30, 60), default=DEFAULT_EPOCHS)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
