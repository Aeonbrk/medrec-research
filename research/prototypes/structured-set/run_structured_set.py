#!/usr/bin/env python3
"""Run one arm of the bounded MIMIC-III structured-set experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

try:
    from structured_set import (
        DIM,
        FF_DIM,
        HEADS,
        MEDICATIONS,
        SLOTS,
        StructuredSetModel,
        assignment_decode,
        configure_numeric_policy,
        matching_cross_entropy,
        pack_inputs,
        threshold_decode,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from structured_set import (
        DIM,
        FF_DIM,
        HEADS,
        MEDICATIONS,
        SLOTS,
        StructuredSetModel,
        assignment_decode,
        configure_numeric_policy,
        matching_cross_entropy,
        pack_inputs,
        threshold_decode,
    )

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
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
SEED = 20260919
EPOCHS = 60
BATCH_SIZE = 16
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 5.0
NATIVE_BETA = float(np.log(0.35 / 0.65))
BETA_GRID = tuple(
    sorted(
        {
            float(np.log(probability / (1.0 - probability)))
            for probability in np.arange(0.05, 1.0, 0.05)
        }
        | {-6.0, -5.0, -4.0, 4.0, 5.0, 6.0}
    )
)
PROGRESS_SCHEMA = 1


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    configure_numeric_policy()


def _is_dev(patient_id: int) -> bool:
    digest = hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _word(indexed: Any, index: int) -> str:
    try:
        return str(indexed[index])
    except (KeyError, IndexError):
        return str(indexed[str(index)])


def _build_rows(records: Sequence[Any], patients: Iterable[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patient_index in patients:
        history: list[tuple[list[int], list[int], list[int]]] = []
        for visit_index, admission in enumerate(records[int(patient_index)]):
            rows.append(
                {
                    "diagnoses": list(admission[0]),
                    "procedures": list(admission[1]),
                    "history": list(history),
                    "_medications": list(admission[2]),
                    "_patient_id": str(int(patient_index)),
                    "_visit_id": f"{int(patient_index)}:{visit_index}",
                }
            )
            history.append((list(admission[0]), list(admission[1]), list(admission[2])))
    return rows


def _model_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "diagnoses": list(row["diagnoses"]),
            "procedures": list(row["procedures"]),
            "history": list(row["history"]),
        }
        for row in rows
    ]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_profile(snapshot: Path, train_dev_root: Path) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError("committed MIII profile ID does not match the runner")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("committed MIII snapshot ID does not match the runner")
    split = profile.get("split", {})
    if (
        split.get("train", {}).get("patients") != 4233
        or split.get("dev", {}).get("patients") != 1004
    ):
        raise RuntimeError("committed MIII patient split does not match the runner")
    if split.get("train", {}).get("visits") != 10489 or split.get("dev", {}).get("visits") != 2130:
        raise RuntimeError("committed MIII visit split does not match the runner")
    assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = assets.get(name, {})
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("MIII source asset is missing or is a symlink: " + name)
        if path.stat().st_size != expected.get("bytes") or _sha256_file(path) != expected.get(
            "sha256"
        ):
            raise RuntimeError("MIII source asset hash does not match the frozen profile: " + name)
    for name, expected_hash in (
        ("train_targets.npy", split.get("train", {}).get("target_array_sha256")),
        ("dev_targets.npy", split.get("dev", {}).get("target_array_sha256")),
    ):
        path = train_dev_root / name
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected_hash:
            raise RuntimeError("MIII target array hash does not match the frozen profile: " + name)


def _validate_data(
    records: Sequence[Any],
    voc: Mapping[str, Any],
    train_rows: Sequence[Mapping[str, Any]],
    dev_rows: Sequence[Mapping[str, Any]],
    train_targets: np.ndarray,
    dev_targets: np.ndarray,
    ddi: np.ndarray,
) -> tuple[int, int, tuple[str, ...]]:
    if len(records) != 6350:
        raise RuntimeError("canonical snapshot patient count changed")
    medication = voc["med_voc"]
    diagnosis = voc["diag_voc"]
    procedure = voc["pro_voc"]
    if set(int(key) for key in medication.idx2word) != set(range(MEDICATIONS)):
        raise RuntimeError("medication vocabulary IDs are not exact canonical 131 IDs")
    diagnosis_ids = set(int(key) for key in diagnosis.idx2word)
    procedure_ids = set(int(key) for key in procedure.idx2word)
    if diagnosis_ids != set(range(len(diagnosis_ids))) or procedure_ids != set(
        range(len(procedure_ids))
    ):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous")
    for row in tuple(train_rows) + tuple(dev_rows):
        if any(int(code) not in diagnosis_ids for code in row["diagnoses"]):
            raise RuntimeError("current diagnosis ID is outside the frozen vocabulary")
        if any(int(code) not in procedure_ids for code in row["procedures"]):
            raise RuntimeError("current procedure ID is outside the frozen vocabulary")
        if any(int(code) < 0 or int(code) >= MEDICATIONS for code in row["_medications"]):
            raise RuntimeError("current target medication ID is outside canonical 131")
        for event in row["history"]:
            if any(int(code) not in diagnosis_ids for code in event[0]):
                raise RuntimeError("history diagnosis ID is outside the frozen vocabulary")
            if any(int(code) not in procedure_ids for code in event[1]):
                raise RuntimeError("history procedure ID is outside the frozen vocabulary")
            if any(int(code) < 0 or int(code) >= MEDICATIONS for code in event[2]):
                raise RuntimeError("history medication ID is outside canonical 131")
    if train_targets.shape != (len(train_rows), MEDICATIONS) or dev_targets.shape != (
        len(dev_rows),
        MEDICATIONS,
    ):
        raise RuntimeError("target arrays are not aligned with canonical visit rows")
    if not np.isfinite(train_targets).all() or not np.isfinite(dev_targets).all():
        raise RuntimeError("target arrays contain non-finite values")
    if not np.isin(train_targets, (0.0, 1.0)).all() or not np.isin(dev_targets, (0.0, 1.0)).all():
        raise RuntimeError("target arrays are not binary")
    for rows, targets, label in (
        (train_rows, train_targets, "Train"),
        (dev_rows, dev_targets, "Dev"),
    ):
        for index, row in enumerate(rows):
            expected = np.zeros(MEDICATIONS, dtype=np.float32)
            expected[list(set(int(code) for code in row["_medications"]))] = 1.0
            if not np.array_equal(expected, targets[index]):
                raise RuntimeError(label + " target is not aligned with source records")
    if len(train_rows) != 10489 or len(dev_rows) != 2130:
        raise RuntimeError("canonical Train/Dev visit counts changed")
    if (
        ddi.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(ddi).all()
        or not np.isin(ddi, (0.0, 1.0)).all()
    ):
        raise RuntimeError("DDI matrix is not finite binary 131 by 131")
    if not np.array_equal(ddi, ddi.T) or np.any(np.diag(ddi) != 0):
        raise RuntimeError("DDI matrix is not symmetric zero-diagonal")
    return (
        len(diagnosis_ids),
        len(procedure_ids),
        tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS)),
    )


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_source(source_revision: str) -> None:
    if _git_revision() != source_revision:
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


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(str(temporary), str(path))


def _config(
    arm: str, validation_schedule: Sequence[int], numeric_policy: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "arm": arm,
        "architecture": "MICA DrugQuery -> medication representations -> 131 anonymous slots",
        "medications": MEDICATIONS,
        "slots": SLOTS,
        "hidden_dim": DIM,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "gradient_clip": GRADIENT_CLIP,
        "control_objective": "BCEWithLogits(max_s utility, target)",
        "full_objective": "categorical CE after Hungarian matching with cost -u; NULL is class 131",
        "decoder": "threshold for control; exact positive-edge maximum-weight injective assignment for full",
        "beta_grid": list(BETA_GRID),
        "native_beta": NATIVE_BETA,
        "validation_schedule": list(validation_schedule),
        "numeric_policy": dict(numeric_policy),
        "test_accessed": False,
    }


def _targets_from_matrix(targets: np.ndarray) -> list[tuple[int, ...]]:
    return [tuple(int(index) for index in np.flatnonzero(row > 0.5)) for row in targets]


def _utility_batches(
    model: StructuredSetModel,
    rows: Sequence[Mapping[str, Any]],
    dx_count: int,
    proc_count: int,
    device: torch.device,
    batch_size: int = BATCH_SIZE,
) -> np.ndarray:
    model.eval()
    chunks: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch_rows = _model_rows(rows[start : start + batch_size])
            packed = {
                key: value.to(device)
                for key, value in pack_inputs(batch_rows, dx_count, proc_count).items()
            }
            chunks.append(model(packed)["utility"].detach().cpu().numpy())
    values = np.concatenate(chunks, axis=0)
    expected = (len(rows), SLOTS, MEDICATIONS)
    if values.shape != expected or not np.isfinite(values).all():
        raise RuntimeError("cached utility is not finite and visit-aligned")
    return values


def _predictions(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    utility: np.ndarray,
    decoder: str,
    beta: float,
    vocabulary: tuple[str, ...],
) -> tuple[VisitPrediction, ...]:
    target_sets = _targets_from_matrix(targets)
    scores = utility.max(axis=1)
    predictions: list[VisitPrediction] = []
    for index, row in enumerate(rows):
        if decoder == "threshold":
            predicted = threshold_decode(utility[index], beta)
        elif decoder == "assignment":
            predicted = assignment_decode(utility[index], beta)
        else:
            raise ValueError("decoder must be threshold or assignment")
        predictions.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[value] for value in target_sets[index]),
                predicted_medications=tuple(vocabulary[value] for value in predicted),
                medication_scores=tuple(float(value) for value in scores[index]),
            )
        )
    return tuple(predictions)


def _surface(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    utility: np.ndarray,
    decoder: str,
    beta: float,
    vocabulary: tuple[str, ...],
    ddi: np.ndarray,
) -> dict[str, Any]:
    ddi_pairs = tuple(
        (vocabulary[left], vocabulary[right])
        for left, right in zip(  # noqa: B905 - NumPy returns equal-length coordinate arrays
            *np.triu(np.asarray(ddi, dtype=np.float32), 1).nonzero()
        )
    )
    return evaluate(
        _predictions(rows, targets, utility, decoder, beta, vocabulary),
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
    )


def _curve(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    utility: np.ndarray,
    decoder: str,
    vocabulary: tuple[str, ...],
    ddi: np.ndarray,
) -> list[dict[str, Any]]:
    values = []
    for index, beta in enumerate(BETA_GRID):
        metrics = _surface(rows, targets, utility, decoder, beta, vocabulary, ddi)
        values.append(
            {
                "beta": beta,
                "beta_grid_index": index,
                "is_grid_boundary": index in (0, len(BETA_GRID) - 1),
                "metrics": metrics,
            }
        )
    return values


def _control_loss(outputs: dict[str, torch.Tensor], targets: torch.Tensor) -> torch.Tensor:
    values = outputs["utility"].amax(dim=1)
    return torch.nn.functional.binary_cross_entropy_with_logits(values, targets)


def _timing_preflight(
    model: StructuredSetModel,
    train_rows: Sequence[Mapping[str, Any]],
    dev_rows: Sequence[Mapping[str, Any]],
    train_targets: np.ndarray,
    dx_count: int,
    proc_count: int,
    device: torch.device,
    vocabulary: tuple[str, ...],
    ddi: np.ndarray,
) -> dict[str, Any]:
    """Measure the non-scientific costs needed to freeze validation cadence."""

    model.train()
    sample_rows = _model_rows(train_rows[:BATCH_SIZE])
    packed = {
        key: value.to(device)
        for key, value in pack_inputs(sample_rows, dx_count, proc_count).items()
    }
    target = torch.from_numpy(train_targets[: len(sample_rows)]).to(device)
    start = time.perf_counter()
    outputs = model(packed)
    loss = _control_loss(outputs, target)
    loss.backward()
    forward_backward_seconds = time.perf_counter() - start
    model.zero_grad(set_to_none=True)

    start = time.perf_counter()
    cached = _utility_batches(model, dev_rows, dx_count, proc_count, device)
    dev_forward_seconds = time.perf_counter() - start
    start = time.perf_counter()
    copied = torch.from_numpy(cached).to(device)
    _ = copied.cpu()
    transfer_seconds = time.perf_counter() - start
    start = time.perf_counter()
    for beta in BETA_GRID:
        for value in cached:
            assignment_decode(value, beta)
    assignment_grid_seconds = time.perf_counter() - start
    estimated_epoch_seconds = forward_backward_seconds * math.ceil(len(train_rows) / BATCH_SIZE)
    schedule = list(range(1, EPOCHS + 1))
    if assignment_grid_seconds > max(estimated_epoch_seconds, 1e-6) * 0.5:
        schedule = list(range(5, EPOCHS + 1, 5))
    return {
        "forward_backward_batch_seconds": forward_backward_seconds,
        "estimated_train_epoch_seconds": estimated_epoch_seconds,
        "cached_dev_forward_seconds": dev_forward_seconds,
        "gpu_cpu_transfer_seconds": transfer_seconds,
        "full_beta_grid_assignment_seconds": assignment_grid_seconds,
        "assignment_fraction_of_estimated_epoch": assignment_grid_seconds
        / max(estimated_epoch_seconds, 1e-6),
        "validation_schedule": schedule,
        "grid_size": len(BETA_GRID),
        "dev_visits": len(dev_rows),
        "timing_is_execution_check_only": True,
        "test_accessed": False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.arm not in ("control", "full"):
        raise RuntimeError("arm must be control or full")
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev root identity does not match the frozen profile")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if output == REPO_ROOT or REPO_ROOT in output.parents:
        raise RuntimeError("output directory must be outside the run checkout")
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
        records, voc, train_rows, dev_rows, train_targets, dev_targets, ddi
    )
    _seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = StructuredSetModel(dx_count, proc_count).to(device)
    parameter_names = list(model.state_dict())
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    initial_state = {
        name: value.detach().cpu().clone() for name, value in model.state_dict().items()
    }
    initial_digest = _sha256_bytes(
        b"".join(
            name.encode() + b"\0" + tensor.numpy().tobytes()
            for name, tensor in initial_state.items()
        )
    )
    numeric_policy = configure_numeric_policy()

    if args.timing_preflight:
        timing = _timing_preflight(
            model,
            train_rows,
            dev_rows,
            train_targets,
            dx_count,
            proc_count,
            device,
            vocabulary,
            ddi,
        )
        result = {
            "status": "TIMING_PREFLIGHT_PASS",
            "source_revision": args.source_revision,
            "profile_id": PROFILE_ID,
            "arm": args.arm,
            "seed": SEED,
            "parameter_count": parameter_count,
            "parameter_names": parameter_names,
            "initial_state_sha256": initial_digest,
            "timing": timing,
            "config": _config(args.arm, timing["validation_schedule"], numeric_policy),
            "split": {
                "train_patients": len(train_patients),
                "dev_patients": len(dev_patients),
                "train_visits": len(train_rows),
                "dev_visits": len(dev_rows),
            },
            "test_accessed": False,
        }
        _write_json(args.timing_output.resolve(), result)
        return result

    if args.schedule_file is None:
        raise RuntimeError("formal run requires the frozen timing schedule")
    schedule_record = json.loads(args.schedule_file.read_text(encoding="utf-8"))
    validation_schedule = tuple(int(value) for value in schedule_record["validation_schedule"])
    if not validation_schedule or tuple(sorted(set(validation_schedule))) != validation_schedule:
        raise RuntimeError("validation schedule is not deterministic and strictly ordered")
    if validation_schedule[-1] != EPOCHS or any(
        value < 1 or value > EPOCHS for value in validation_schedule
    ):
        raise RuntimeError("validation schedule must end at epoch 60")
    config = _config(args.arm, validation_schedule, numeric_policy)
    output.mkdir(parents=True, exist_ok=True)
    progress: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "preflight_complete",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "arm": args.arm,
        "seed": SEED,
        "initial_state_sha256": initial_digest,
        "parameter_count": parameter_count,
        "config": config,
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "completed_epochs": 0,
        "selected_checkpoint": None,
        "selected_beta": None,
        "evaluations": progress,
        "test_accessed": False,
    }
    _write_json(output / "progress.json", state)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the full-budget experiment")
    device = torch.device("cuda")
    model = StructuredSetModel(dx_count, proc_count).to(device)
    model.load_state_dict(initial_state)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    generator = np.random.RandomState(SEED)
    target_sets = _targets_from_matrix(train_targets)
    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, torch.Tensor] | None = None
    best_utility: np.ndarray | None = None
    start_time = time.time()
    state["status"] = "running"
    _write_json(output / "progress.json", state)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        loss_sum = 0.0
        example_count = 0
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch_rows = _model_rows([train_rows[int(index)] for index in indices])
            packed = {
                key: value.to(device)
                for key, value in pack_inputs(batch_rows, dx_count, proc_count).items()
            }
            target = torch.from_numpy(train_targets[indices]).to(device)
            batch_targets = [target_sets[int(index)] for index in indices]
            optimizer.zero_grad(set_to_none=True)
            outputs = model(packed)
            if args.arm == "control":
                loss = _control_loss(outputs, target)
            else:
                loss, _labels = matching_cross_entropy(outputs, batch_targets, MEDICATIONS, SLOTS)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            loss_sum += float(loss.item()) * size
            example_count += size

        if epoch in validation_schedule:
            dev_utility = _utility_batches(model, dev_rows, dx_count, proc_count, device)
            decoder = "threshold" if args.arm == "control" else "assignment"
            candidate_results: list[dict[str, Any]] = []
            candidates: list[SelectionCandidate] = []
            for beta_index, beta in enumerate(BETA_GRID):
                metrics = _surface(
                    dev_rows, dev_targets, dev_utility, decoder, beta, vocabulary, ddi
                )
                candidates.append(SelectionCandidate(epoch, beta, metrics["jaccard"], beta_index))
                candidate_results.append(
                    {
                        "beta": beta,
                        "beta_grid_index": beta_index,
                        "is_grid_boundary": beta_index in (0, len(BETA_GRID) - 1),
                        "metrics": metrics,
                    }
                )
            checkpoint_best = select_joint(
                candidates, operating_point_order=BETA_GRID, native_default=NATIVE_BETA
            )
            if best_candidate is None or (
                -checkpoint_best.patient_macro_jaccard,
                abs(checkpoint_best.operating_point - NATIVE_BETA),
                checkpoint_best.operating_point_index,
                checkpoint_best.checkpoint,
            ) < (
                -best_candidate.patient_macro_jaccard,
                abs(best_candidate.operating_point - NATIVE_BETA),
                best_candidate.operating_point_index,
                best_candidate.checkpoint,
            ):
                best_candidate = checkpoint_best
                best_state = {
                    name: value.detach().cpu().clone() for name, value in model.state_dict().items()
                }
                best_utility = dev_utility.copy()
                torch.save(best_state, output / "selected_checkpoint.pt")
                np.save(output / "selected_dev_utility.npy", best_utility)
            selected_metrics = next(
                item["metrics"]
                for item in candidate_results
                if item["beta"] == checkpoint_best.operating_point
            )
            progress.append(
                {
                    "epoch": epoch,
                    "train_loss": loss_sum / max(example_count, 1),
                    "decoder": decoder,
                    "selected_beta": checkpoint_best.operating_point,
                    "selected_dev_jaccard": checkpoint_best.patient_macro_jaccard,
                    "candidate_betas": candidate_results,
                    "dev_metrics": selected_metrics,
                    "elapsed_seconds": time.time() - start_time,
                    "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
                }
            )
            state["completed_epochs"] = epoch
            state["selected_checkpoint"] = best_candidate.checkpoint if best_candidate else None
            state["selected_beta"] = best_candidate.operating_point if best_candidate else None
            _write_json(output / "progress.json", state)
        elif epoch == EPOCHS:
            raise RuntimeError("epoch 60 was omitted from validation schedule")

    if best_candidate is None or best_state is None or best_utility is None:
        raise RuntimeError("no complete Dev checkpoint was selected")
    model.load_state_dict(best_state)
    train_utility = _utility_batches(model, train_rows, dx_count, proc_count, device)
    selected_train = _surface(
        train_rows,
        train_targets,
        train_utility,
        "threshold" if args.arm == "control" else "assignment",
        best_candidate.operating_point,
        vocabulary,
        ddi,
    )
    selected_dev = _surface(
        dev_rows,
        dev_targets,
        best_utility,
        "threshold" if args.arm == "control" else "assignment",
        best_candidate.operating_point,
        vocabulary,
        ddi,
    )
    result = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "seed": SEED,
        "arm": args.arm,
        "config": config,
        "parameter_count": parameter_count,
        "parameter_names": parameter_names,
        "initial_state_sha256": initial_digest,
        "split": state["split"],
        "completed_epochs": EPOCHS,
        "validation_schedule": list(validation_schedule),
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_beta": best_candidate.operating_point,
        "selected_beta_is_grid_boundary": best_candidate.operating_point_index
        in (0, len(BETA_GRID) - 1),
        "selected_checkpoint_score": best_candidate.patient_macro_jaccard,
        "metrics": {"Train": selected_train, "Dev": selected_dev},
        "progress": progress,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "test_accessed": False,
        "source_assets": {"snapshot_id": SNAPSHOT_ID, "train_dev_id": TRAIN_DEV_ID},
    }
    state["status"] = "complete"
    state["result"] = {
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_beta": best_candidate.operating_point,
        "selected_beta_is_grid_boundary": result["selected_beta_is_grid_boundary"],
    }
    _write_json(output / "progress.json", state)
    _write_json(output / "results.json", result)
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("control", "full"), required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--timing-preflight", action="store_true")
    parser.add_argument("--timing-output", type=Path)
    parser.add_argument("--schedule-file", type=Path)
    args = parser.parse_args(argv)
    if args.timing_preflight and args.timing_output is None:
        parser.error("--timing-preflight requires --timing-output")
    return args


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
