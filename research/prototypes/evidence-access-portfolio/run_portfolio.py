#!/usr/bin/env python3
"""Run one frozen lane of the evidence-access architecture portfolio."""
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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import dill
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portfolio_model import (
    DIM,
    MEDICATIONS,
    VARIANTS,
    PortfolioModel,
    configure_numeric_policy,
    objective,
    pack_rows,
    parameter_count,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from research.prototypes.paper_contract.evaluator import (
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
EPOCHS = 60
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


def _build_rows(records: Sequence[Any], patients: Iterable[int]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for patient_index in patients:
        history: List[Tuple[List[int], List[int], List[int]]] = []
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


def _model_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "diagnoses": list(row["diagnoses"]),
            "procedures": list(row["procedures"]),
            "history": list(row["history"]),
        }
        for row in rows
    ]


def _sha256(path: Path) -> str:
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
    if split.get("train", {}).get("patients") != 4233 or split.get("dev", {}).get("patients") != 1004:
        raise RuntimeError("committed MIII patient split does not match the runner")
    if split.get("train", {}).get("visits") != 10489 or split.get("dev", {}).get("visits") != 2130:
        raise RuntimeError("committed MIII visit split does not match the runner")
    assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = assets.get(name, {})
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("MIII source asset is missing or symlinked: " + name)
        if path.stat().st_size != expected.get("bytes") or _sha256(path) != expected.get("sha256"):
            raise RuntimeError("MIII source asset hash mismatch: " + name)
    expected_targets = {
        "train_targets.npy": split.get("train", {}).get("target_array_sha256"),
        "dev_targets.npy": split.get("dev", {}).get("target_array_sha256"),
    }
    for name, expected_hash in expected_targets.items():
        path = train_dev_root / name
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected_hash:
            raise RuntimeError("MIII target array hash mismatch: " + name)


def _validate_data(
    records: Sequence[Any],
    voc: Mapping[str, Any],
    ddi: np.ndarray,
    train_rows: Sequence[Mapping[str, Any]],
    dev_rows: Sequence[Mapping[str, Any]],
    train_targets: np.ndarray,
    dev_targets: np.ndarray,
) -> Tuple[int, int, Tuple[str, ...]]:
    if len(records) != 6350:
        raise RuntimeError("canonical snapshot patient count changed")
    medication = voc["med_voc"]
    diagnosis = voc["diag_voc"]
    procedure = voc["pro_voc"]
    vocabulary = tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))
    med_ids = set(range(MEDICATIONS))
    if set(int(key) for key in medication.idx2word) != med_ids:
        raise RuntimeError("medication vocabulary IDs are not exact canonical 131 IDs")
    dx_ids = set(int(key) for key in diagnosis.idx2word)
    proc_ids = set(int(key) for key in procedure.idx2word)
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous")

    for row in tuple(train_rows) + tuple(dev_rows):
        if any(int(code) not in dx_ids for code in row["diagnoses"]):
            raise RuntimeError("current diagnosis ID is outside vocabulary")
        if any(int(code) not in proc_ids for code in row["procedures"]):
            raise RuntimeError("current procedure ID is outside vocabulary")
        if any(int(code) not in med_ids for code in row["_medications"]):
            raise RuntimeError("current medication target outside canonical 131")
        for event in row["history"]:
            if any(int(code) not in dx_ids for code in event[0]):
                raise RuntimeError("history diagnosis ID is outside vocabulary")
            if any(int(code) not in proc_ids for code in event[1]):
                raise RuntimeError("history procedure ID is outside vocabulary")
            if any(int(code) not in med_ids for code in event[2]):
                raise RuntimeError("history medication ID outside canonical 131")

    if train_targets.shape != (len(train_rows), MEDICATIONS) or dev_targets.shape != (len(dev_rows), MEDICATIONS):
        raise RuntimeError("target arrays are not aligned with visit rows")
    if not np.isfinite(train_targets).all() or not np.isfinite(dev_targets).all():
        raise RuntimeError("target arrays contain non-finite values")
    if not np.isin(train_targets, (0.0, 1.0)).all() or not np.isin(dev_targets, (0.0, 1.0)).all():
        raise RuntimeError("target arrays are not binary")

    for rows, targets, label in ((train_rows, train_targets, "Train"), (dev_rows, dev_targets, "Dev")):
        for index, row in enumerate(rows):
            expected = np.zeros(MEDICATIONS, dtype=np.float32)
            expected[list(set(int(code) for code in row["_medications"]))] = 1.0
            if not np.array_equal(expected, targets[index]):
                raise RuntimeError(label + " target mismatch at row " + str(index))

    if len(train_rows) != 10489 or len(dev_rows) != 2130:
        raise RuntimeError("canonical Train/Dev visit counts changed")
    if ddi.shape != (MEDICATIONS, MEDICATIONS):
        raise RuntimeError("DDI matrix shape mismatch")
    if (
        not np.isfinite(ddi).all()
        or not np.isin(ddi, (0.0, 1.0)).all()
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
    ):
        raise RuntimeError("DDI matrix must be finite binary symmetric zero-diagonal")
    return len(dx_ids), len(proc_ids), vocabulary


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_source(source_revision: str) -> Path:
    root = REPO_ROOT.resolve()
    if _git_revision(root) != source_revision:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("run checkout is not clean")
    return root


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def _predictions(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    logits: np.ndarray,
    threshold: float,
    vocabulary: Tuple[str, ...],
) -> Tuple[VisitPrediction, ...]:
    probabilities = 1.0 / (1.0 + np.exp(-np.asarray(logits, dtype=np.float64)))
    if probabilities.shape != targets.shape or not np.isfinite(probabilities).all():
        raise RuntimeError("model probabilities are not finite and visit-aligned")
    predictions: List[VisitPrediction] = []
    for index, row in enumerate(rows):
        target_indices = tuple(int(value) for value in np.flatnonzero(targets[index] > 0.5))
        predicted_indices = tuple(int(value) for value in np.flatnonzero(probabilities[index] >= threshold))
        predictions.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[value] for value in target_indices),
                predicted_medications=tuple(vocabulary[value] for value in predicted_indices),
                medication_scores=tuple(float(value) for value in probabilities[index]),
            )
        )
    return tuple(predictions)


def _surface(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    logits: np.ndarray,
    threshold: float,
    vocabulary: Tuple[str, ...],
    ddi: np.ndarray,
) -> Dict[str, Any]:
    ddi_pairs = tuple(
        (vocabulary[left], vocabulary[right])
        for left, right in zip(*np.triu(np.asarray(ddi, dtype=np.float32), 1).nonzero())
    )
    metrics = evaluate(
        _predictions(rows, targets, logits, threshold, vocabulary),
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
    )
    metrics["nll"] = float(
        torch.nn.functional.binary_cross_entropy_with_logits(
            torch.from_numpy(np.asarray(logits, dtype=np.float32)),
            torch.from_numpy(np.asarray(targets, dtype=np.float32)),
        ).item()
    )
    return metrics


def _best_key(candidate: SelectionCandidate) -> Tuple[float, float, int, int]:
    return (
        -float(candidate.patient_macro_jaccard),
        abs(float(candidate.operating_point) - NATIVE_DEFAULT),
        candidate.operating_point_index,
        candidate.checkpoint,
    )


def _config(variant: str, numeric_policy: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "variant": variant,
        "medications": MEDICATIONS,
        "hidden_dim": DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
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
            "cuda_torch": TORCH_SEED,
            "python_random": PYTHON_SEED,
            "numpy": NUMPY_SEED,
        },
        "numeric_policy": dict(numeric_policy),
    }


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
            batch_rows = _model_rows(rows[start : start + BATCH_SIZE])
            batch = {
                key: value.to(device)
                for key, value in pack_rows(batch_rows, dx_count, proc_count).items()
            }
            chunks.append(model(batch).detach().cpu().numpy())
    values = np.concatenate(chunks, axis=0)
    if values.shape != targets.shape or not np.isfinite(values).all():
        raise RuntimeError("model logits are not finite and aligned with targets")
    return values


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.variant not in VARIANTS:
        raise RuntimeError("unknown portfolio variant")
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
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )

    numeric_policy = configure_numeric_policy()
    config = _config(args.variant, numeric_policy)
    state: Dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "preflight_complete",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "variant": args.variant,
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
        raise RuntimeError("CUDA is required for the full portfolio run")
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "progress.json", state)

    _seed_everything()
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = PortfolioModel(dx_count, proc_count, args.variant).to(device)
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

    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        loss_sum = bce_sum = ddi_sum = 0.0
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
            logits = model(batch)
            loss, bce, ddi_loss = objective(logits, target, ddi_tensor)
            if not torch.isfinite(loss):
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
            candidates, operating_point_order=OPERATING_POINTS, native_default=NATIVE_DEFAULT
        )
        if best_candidate is None or _best_key(checkpoint_best) < _best_key(best_candidate):
            best_candidate = checkpoint_best
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            best_dev_logits = dev_logits.copy()
            torch.save(best_state, output / "selected_checkpoint.pt")
            np.save(output / "selected_dev_logits.npy", best_dev_logits)
        selected_metrics = next(
            item["metrics"] for item in candidate_results if item["operating_point"] == checkpoint_best.operating_point
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
        train_rows, train_targets, train_logits, best_candidate.operating_point, vocabulary, ddi
    )
    selected_dev = _surface(
        dev_rows, dev_targets, best_dev_logits, best_candidate.operating_point, vocabulary, ddi
    )
    result: Dict[str, Any] = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "variant": args.variant,
        "config": config,
        "parameter_count": parameter_count(model),
        "split": state["split"],
        "completed_epochs": EPOCHS,
        "updates_per_epoch": updates_per_epoch,
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_operating_point": best_candidate.operating_point,
        "selected_checkpoint_score": best_candidate.patient_macro_jaccard,
        "metrics": {"Train": selected_train, "Dev": selected_dev},
        "epoch_60_Dev": evaluations[-1]["dev_metrics"],
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
    state["epoch_60_Dev"] = evaluations[-1]["dev_metrics"]
    _write_json(output / "progress.json", state)
    _write_json(output / "results.json", result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
