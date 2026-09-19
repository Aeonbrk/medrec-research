#!/usr/bin/env python3
"""Run one frozen EBRA matched arm on the canonical MIMIC-III Train/Dev profile."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(HERE))
PORTFOLIO_DIR = HERE.parent / "evidence-access-portfolio"
sys.path.insert(0, str(PORTFOLIO_DIR))

from ebra_model import (  # noqa: E402
    MEDICATIONS,
    EBRAModel,
    assignment_decode,
    assignment_loss,
    configure_numeric_policy,
    fixed_multilabel_loss,
    pack_rows,
    parameter_count,
)
from run_portfolio import (  # noqa: E402
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _validate_data,
    _validate_profile,
)

from research.prototypes.paper_contract.evaluator import (  # noqa: E402
    SelectionCandidate,
    VisitPrediction,
    evaluate,
    select_joint,
)

PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"
PROFILE_PATH = REPO_ROOT / "research" / "benchmarks" / "mimiciii-medrec" / "profile.json"

TORCH_SEED = 1203
NUMPY_SEED = 2048
PYTHON_SEED = 1203
DEFAULT_EPOCHS = 15
BATCH_SIZE = 16
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 5.0
OPERATING_POINTS = tuple(round(value / 100.0, 2) for value in range(5, 100, 5))
NATIVE_DEFAULT = 0.35
PROGRESS_SCHEMA = 1


def _seed_everything() -> None:
    random.seed(PYTHON_SEED)
    np.random.seed(NUMPY_SEED)
    torch.manual_seed(TORCH_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(TORCH_SEED)
    configure_numeric_policy()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(str(temporary), str(path))


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_source(source_revision: str) -> None:
    if _git_revision(REPO_ROOT) != source_revision:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("run checkout is not clean")


def _validate_profile_and_test_surface(snapshot: Path, train_dev_root: Path) -> None:
    _validate_profile(snapshot, train_dev_root)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    test_split = profile.get("split", {}).get("test", {})
    if test_split.get("membership_loaded") is not False:
        raise RuntimeError("Test membership is not sealed in the committed profile")
    if test_split.get("targets_loaded") is not False:
        raise RuntimeError("Test targets are not sealed in the committed profile")


def _config(arm: str, epochs: int, numeric_policy: Mapping[str, Any]) -> dict[str, Any]:
    loss = (
        "BCE on fixed diagonal L[m,m]-L[m,NULL]"
        if arm == "fixed_multilabel"
        else ("balanced permutation-invariant matched real/NULL categorical NLL")
    )
    return {
        "profile_id": PROFILE_ID,
        "arm": arm,
        "medications": MEDICATIONS,
        "slots": MEDICATIONS,
        "hidden_dim": 128,
        "proposal": "PortfolioModel resolution_code FineCode proposal bank",
        "decision_block": "131 learned queries, one self-attention, one cross-attention, one FFN",
        "score_matrix": "full medication score matrix plus shared NULL scorer",
        "batch_size_visits": BATCH_SIZE,
        "epochs": epochs,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "loss": loss,
        "operating_points": list(OPERATING_POINTS)
        if arm == "fixed_multilabel"
        else ["native_assignment"],
        "native_default": NATIVE_DEFAULT,
        "rng": {
            "torch": TORCH_SEED,
            "cuda_torch": TORCH_SEED,
            "python_random": PYTHON_SEED,
            "numpy": NUMPY_SEED,
        },
        "numeric_policy": dict(numeric_policy),
        "test_loaded": False,
    }


def _predictions(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    output: Mapping[str, np.ndarray],
    arm: str,
    threshold: float | None,
    vocabulary: tuple[str, ...],
) -> tuple[VisitPrediction, ...]:
    medication_logits = np.asarray(output["medication_logits"], dtype=np.float64)
    null_logits = np.asarray(output["null_logits"], dtype=np.float64)
    if medication_logits.shape != (len(rows), MEDICATIONS, MEDICATIONS):
        raise RuntimeError("medication score matrix is not visit-aligned")
    if null_logits.shape != (len(rows), MEDICATIONS):
        raise RuntimeError("NULL score matrix is not visit-aligned")
    predictions: list[VisitPrediction] = []
    for index, row in enumerate(rows):
        target_indices = tuple(int(value) for value in np.flatnonzero(targets[index] > 0.5))
        if arm == "fixed_multilabel":
            if threshold is None:
                raise RuntimeError("fixed_multilabel requires a threshold")
            diagonal = medication_logits[index, np.arange(MEDICATIONS), np.arange(MEDICATIONS)]
            probabilities = 1.0 / (1.0 + np.exp(-(diagonal - null_logits[index])))
            predicted_indices = tuple(
                int(value) for value in np.flatnonzero(probabilities >= threshold)
            )
            scores = probabilities
        else:
            predicted, scores = assignment_decode(medication_logits[index], null_logits[index])
            predicted_indices = tuple(predicted)
        if not np.isfinite(scores).all():
            raise RuntimeError("medication scores are not finite")
        predictions.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[value] for value in target_indices),
                predicted_medications=tuple(vocabulary[value] for value in predicted_indices),
                medication_scores=tuple(float(value) for value in scores),
            )
        )
    return tuple(predictions)


def _surface(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    output: Mapping[str, np.ndarray],
    arm: str,
    threshold: float | None,
    vocabulary: tuple[str, ...],
    ddi: np.ndarray,
) -> dict[str, Any]:
    ddi_pairs = tuple(
        (vocabulary[left], vocabulary[right])
        for left, right in zip(  # noqa: B905
            *np.triu(np.asarray(ddi, dtype=np.float32), 1).nonzero()
        )
    )
    metrics = evaluate(
        _predictions(rows, targets, output, arm, threshold, vocabulary),
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
    )
    logits = torch.from_numpy(
        np.concatenate(
            (output["medication_logits"], output["null_logits"][..., None]), axis=-1
        ).astype(np.float32)
    )
    target_tensor = torch.from_numpy(np.asarray(targets, dtype=np.float32))
    if arm == "fixed_multilabel":
        diagonal = logits[:, torch.arange(MEDICATIONS), torch.arange(MEDICATIONS)]
        nll = torch.nn.functional.binary_cross_entropy_with_logits(
            diagonal - logits[:, :, MEDICATIONS], target_tensor
        ).item()
    else:
        nll = float("nan")
    metrics["nll"] = float(nll) if math.isfinite(float(nll)) else None
    return metrics


def _predict_outputs(
    model: EBRAModel,
    rows: Sequence[Mapping[str, Any]],
    dx_count: int,
    proc_count: int,
    device: torch.device,
) -> dict[str, np.ndarray]:
    model.eval()
    medication_chunks: list[np.ndarray] = []
    null_chunks: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = _model_rows(rows[start : start + BATCH_SIZE])
            batch = {
                key: value.to(device)
                for key, value in pack_rows(batch_rows, dx_count, proc_count).items()
            }
            output = model(batch)
            medication_chunks.append(output["medication_logits"].detach().cpu().numpy())
            null_chunks.append(output["null_logits"].detach().cpu().numpy())
    medication = np.concatenate(medication_chunks, axis=0)
    null = np.concatenate(null_chunks, axis=0)
    if (
        medication.shape != (len(rows), MEDICATIONS, MEDICATIONS)
        or not np.isfinite(medication).all()
    ):
        raise RuntimeError("model medication scores are not finite and aligned")
    if null.shape != (len(rows), MEDICATIONS) or not np.isfinite(null).all():
        raise RuntimeError("model NULL scores are not finite and aligned")
    return {"medication_logits": medication, "null_logits": null}


def _best_key(candidate: SelectionCandidate) -> tuple[float, float, int, int]:
    return (
        -float(candidate.patient_macro_jaccard),
        abs(float(candidate.operating_point) - NATIVE_DEFAULT),
        candidate.operating_point_index,
        candidate.checkpoint,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.arm not in ("fixed_multilabel", "ebra_assignment"):
        raise RuntimeError("unknown EBRA arm")
    if args.epochs < DEFAULT_EPOCHS:
        raise RuntimeError("EBRA runs require at least the frozen 15-epoch budget")
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev identity mismatch")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    _validate_profile_and_test_surface(snapshot, train_dev_root)

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
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    numeric_policy = configure_numeric_policy()
    config = _config(args.arm, args.epochs, numeric_policy)
    state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "preflight_complete",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "arm": args.arm,
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
        raise RuntimeError("CUDA is required for the full EBRA run")
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "progress.json", state)

    _seed_everything()
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = EBRAModel(dx_count, proc_count).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
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

    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, torch.Tensor] | None = None
    best_dev_output: dict[str, np.ndarray] | None = None
    evaluations: list[dict[str, Any]] = []
    start_time = time.time()
    updates_per_epoch = math.ceil(len(train_rows) / float(BATCH_SIZE))

    for epoch in range(1, args.epochs + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        loss_sum = 0.0
        example_count = 0
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch_rows = _model_rows([train_rows[int(index)] for index in indices])
            batch = {
                key: value.to(device)
                for key, value in pack_rows(batch_rows, dx_count, proc_count).items()
            }
            target = torch.from_numpy(train_targets[indices]).to(device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch)
            if args.arm == "fixed_multilabel":
                loss = fixed_multilabel_loss(outputs, target)
            else:
                target_sets = [
                    tuple(np.flatnonzero(train_targets[int(index)] > 0.5).tolist())
                    for index in indices
                ]
                loss, _labels = assignment_loss(outputs, target_sets)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            loss_sum += float(loss.item()) * size
            example_count += size

        dev_output = _predict_outputs(model, dev_rows, dx_count, proc_count, device)
        candidates: list[SelectionCandidate] = []
        candidate_results: list[dict[str, Any]] = []
        if args.arm == "fixed_multilabel":
            for op_index, operating_point in enumerate(OPERATING_POINTS):
                metrics = _surface(
                    dev_rows, dev_targets, dev_output, args.arm, operating_point, vocabulary, ddi
                )
                candidates.append(
                    SelectionCandidate(epoch, operating_point, metrics["jaccard"], op_index)
                )
                candidate_results.append({"operating_point": operating_point, "metrics": metrics})
        else:
            metrics = _surface(dev_rows, dev_targets, dev_output, args.arm, None, vocabulary, ddi)
            candidates.append(SelectionCandidate(epoch, NATIVE_DEFAULT, metrics["jaccard"], 0))
            candidate_results.append({"operating_point": "native_assignment", "metrics": metrics})
        checkpoint_best = select_joint(
            candidates,
            operating_point_order=(
                OPERATING_POINTS if args.arm == "fixed_multilabel" else (NATIVE_DEFAULT,)
            ),
            native_default=NATIVE_DEFAULT,
        )
        if best_candidate is None or _best_key(checkpoint_best) < _best_key(best_candidate):
            best_candidate = checkpoint_best
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_output = {key: value.copy() for key, value in dev_output.items()}
            torch.save(best_state, output / "selected_checkpoint.pt")
            np.savez_compressed(output / "selected_dev_outputs.npz", **best_dev_output)
        selected_metrics = next(
            item["metrics"]
            for item in candidate_results
            if (item["operating_point"] == "native_assignment" and args.arm == "ebra_assignment")
            or (
                item["operating_point"] == checkpoint_best.operating_point
                and args.arm == "fixed_multilabel"
            )
        )
        entry = {
            "epoch": epoch,
            "train_loss": loss_sum / example_count,
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
        state["selected_operating_point"] = (
            best_candidate.operating_point if best_candidate else None
        )
        _write_json(output / "progress.json", state)

    if best_candidate is None or best_state is None or best_dev_output is None:
        raise RuntimeError("no complete Dev checkpoint selected")
    model.load_state_dict(best_state)
    train_output = _predict_outputs(model, train_rows, dx_count, proc_count, device)
    selected_threshold = best_candidate.operating_point if args.arm == "fixed_multilabel" else None
    selected_train = _surface(
        train_rows, train_targets, train_output, args.arm, selected_threshold, vocabulary, ddi
    )
    selected_dev = _surface(
        dev_rows, dev_targets, best_dev_output, args.arm, selected_threshold, vocabulary, ddi
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "arm": args.arm,
        "config": config,
        "parameter_count": parameter_count(model),
        "split": state["split"],
        "completed_epochs": args.epochs,
        "updates_per_epoch": updates_per_epoch,
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_operating_point": (
            best_candidate.operating_point
            if args.arm == "fixed_multilabel"
            else "native_assignment"
        ),
        "selected_checkpoint_score": best_candidate.patient_macro_jaccard,
        "metrics": {"Train": selected_train, "Dev": selected_dev},
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
    state["final_epoch_Dev"] = evaluations[-1]["dev_metrics"]
    _write_json(output / "progress.json", state)
    _write_json(output / "results.json", result)
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("fixed_multilabel", "ebra_assignment"), required=True)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
