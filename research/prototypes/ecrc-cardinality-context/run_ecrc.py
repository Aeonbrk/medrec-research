#!/usr/bin/env python3
"""Run one ECRC arm on the frozen MIMIC-III canonical-131 Train/Dev profile."""

from __future__ import annotations

import argparse
import hashlib
import json
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

try:
    from ecrc import (
        ECRC,
        MEDICATIONS,
        RANK,
        VARIANTS,
        configure_numeric_policy,
        joint_objective,
        pack_inputs,
        topk_indices,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ecrc import (
        ECRC,
        MEDICATIONS,
        RANK,
        VARIANTS,
        configure_numeric_policy,
        joint_objective,
        pack_inputs,
        topk_indices,
    )

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from research.prototypes.paper_contract.evaluator import VisitPrediction, evaluate  # noqa: E402

PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"
PROFILE_PATH = REPO_ROOT / "research" / "benchmarks" / "mimiciii-medrec" / "profile.json"
EPOCHS = 60
BATCH_SIZE = 16
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 5.0
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


def _build_rows(records: Sequence[Any], patients: Sequence[int]) -> list[dict[str, Any]]:
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_profile(snapshot: Path, train_dev_root: Path) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError("committed MIII profile ID does not match ECRC")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("committed MIII snapshot ID does not match ECRC")
    split = profile.get("split", {})
    if (
        split.get("train", {}).get("patients") != 4233
        or split.get("dev", {}).get("patients") != 1004
        or split.get("train", {}).get("visits") != 10489
        or split.get("dev", {}).get("visits") != 2130
    ):
        raise RuntimeError("committed MIII split does not match ECRC")
    assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = assets.get(name, {})
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("MIII source asset is missing or is a symlink: " + name)
        if path.stat().st_size != expected.get("bytes") or _sha256_file(path) != expected.get(
            "sha256"
        ):
            raise RuntimeError("MIII source asset hash does not match frozen profile: " + name)
    for name, expected_hash in (
        ("train_targets.npy", split.get("train", {}).get("target_array_sha256")),
        ("dev_targets.npy", split.get("dev", {}).get("target_array_sha256")),
    ):
        path = train_dev_root / name
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected_hash:
            raise RuntimeError("MIII target array hash does not match frozen profile: " + name)


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
            raise RuntimeError("current diagnosis ID is outside frozen vocabulary")
        if any(int(code) not in procedure_ids for code in row["procedures"]):
            raise RuntimeError("current procedure ID is outside frozen vocabulary")
        if any(int(code) < 0 or int(code) >= MEDICATIONS for code in row["_medications"]):
            raise RuntimeError("current target medication ID is outside canonical 131")
        for event in row["history"]:
            if any(int(code) not in diagnosis_ids for code in event[0]):
                raise RuntimeError("history diagnosis ID is outside frozen vocabulary")
            if any(int(code) not in procedure_ids for code in event[1]):
                raise RuntimeError("history procedure ID is outside frozen vocabulary")
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
    for rows, targets, name in (
        (train_rows, train_targets, "Train"),
        (dev_rows, dev_targets, "Dev"),
    ):
        for index, row in enumerate(rows):
            expected = np.zeros(MEDICATIONS, dtype=np.float32)
            expected[np.asarray(row["_medications"], dtype=np.int64)] = 1.0
            if not np.array_equal(expected, targets[index]):
                raise RuntimeError(name + " target mismatch at row " + str(index))
    ddi = np.asarray(ddi, dtype=np.float32)
    if (
        ddi.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(ddi).all()
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
    ):
        raise RuntimeError("DDI must be finite, symmetric, zero-diagonal 131 by 131")
    vocabulary = tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))
    if len(set(vocabulary)) != MEDICATIONS:
        raise RuntimeError("medication vocabulary words are not unique")
    return len(diagnosis_ids), len(procedure_ids), vocabulary


def _ddi_pairs(ddi: np.ndarray, vocabulary: Sequence[str]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for left in range(MEDICATIONS):
        for right in range(left + 1, MEDICATIONS):
            if float(ddi[left, right]) > 0.0:
                pairs.append(tuple(sorted((str(vocabulary[left]), str(vocabulary[right])))))
    return tuple(pairs)


def _git_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean_source(source_revision: str) -> Path:
    root = _git_root()
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


def _to_device(batch: Any, device: torch.device) -> Any:
    if isinstance(batch, dict):
        return {key: _to_device(value, device) for key, value in batch.items()}
    if isinstance(batch, torch.Tensor):
        return batch.to(device)
    return batch


def _evaluate_scores(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    scores: np.ndarray,
    counts: np.ndarray,
    *,
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
    eligible_patient_ids: Sequence[str],
) -> dict[str, Any]:
    if scores.shape != targets.shape or counts.shape != (targets.shape[0],):
        raise RuntimeError("evaluation score/count shape mismatch")
    score_tensor = torch.from_numpy(scores)
    count_tensor = torch.from_numpy(counts.astype(np.int64, copy=False))
    decoded = topk_indices(score_tensor, count_tensor)
    samples: list[VisitPrediction] = []
    for index, (row, selected) in enumerate(zip(rows, decoded)):
        target_ids = np.flatnonzero(targets[index])
        samples.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[int(i)] for i in target_ids),
                predicted_medications=tuple(vocabulary[int(i)] for i in selected),
                medication_scores=tuple(float(x) for x in scores[index]),
            )
        )
    metrics = evaluate(
        samples,
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
        eligible_patient_ids=eligible_patient_ids,
    )
    target_counts = targets.sum(axis=1)
    metrics["count_mae_visit"] = float(np.abs(counts - target_counts).mean())
    metrics["count_bias_visit"] = float((counts - target_counts).mean())
    metrics["count_exact_visit"] = float((counts == target_counts).mean())
    metrics["predicted_count_mean_visit"] = float(counts.mean())
    metrics["target_count_mean_visit"] = float(target_counts.mean())
    return metrics


def _predict(
    model: ECRC,
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    dx: int,
    proc: int,
    device: torch.device,
    *,
    oracle_k: bool,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    all_scores: list[np.ndarray] = []
    all_counts: list[np.ndarray] = []
    model_rows = _model_rows(rows)
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = model_rows[start : start + BATCH_SIZE]
            batch = _to_device(pack_inputs(batch_rows, dx, proc), device)
            if oracle_k:
                count = torch.from_numpy(
                    targets[start : start + len(batch_rows)].sum(axis=1).astype(np.int64)
                ).to(device)
                if torch.any(count > model.k_max):
                    count = count.clamp_max(model.k_max)
                output = model(batch, k=count)
                selected_count = count
            else:
                output = model(batch, k=None)
                selected_count = output["predicted_k"]
            scores = output["medication_logits"]
            if not torch.isfinite(scores).all() or not torch.isfinite(output["size_logits"]).all():
                raise RuntimeError("non-finite ECRC inference output")
            all_scores.append(scores.cpu().numpy())
            all_counts.append(selected_count.cpu().numpy())
    return np.concatenate(all_scores), np.concatenate(all_counts)


def _scientific_config(
    variant: str, seed: int, k_max: int, numeric_policy: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "variant": variant,
        "conditioned_medication_choice": variant.startswith("kcond_"),
        "medication_likelihood": "fixed_cardinality_exact"
        if variant.endswith("_exact")
        else "bernoulli",
        "rank": RANK,
        "k_max_train": k_max,
        "seed": seed,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "gradient_clip": GRADIENT_CLIP,
        "decoder": "argmax predicted K, then canonical Top-K medication utilities",
        "checkpoint_selection": "best complete-Dev patient-macro Jaccard under native decoder",
        "loss": "(medication NLL + cardinality CE) / 131",
        "ddi_training_weight": 0.0,
        "numeric_policy": dict(numeric_policy),
    }


def _write_progress(output: Path, state: Mapping[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, output / "progress.json")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.variant not in VARIANTS:
        raise RuntimeError("unknown ECRC variant")
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    git_root = _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if git_root == output or git_root in output.parents:
        raise RuntimeError("output directory must be outside the run checkout")
    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot/train-dev identity does not match frozen ECRC profile")
    _validate_profile(snapshot, train_dev_root)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(i for i in range(split, len(records)) if _is_dev(i))
    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    dx, proc, vocabulary = _validate_data(
        records,
        voc,
        train_rows,
        dev_rows,
        train_targets,
        dev_targets,
        ddi,
    )
    if (len(train_rows), len(dev_rows)) != (10489, 2130):
        raise RuntimeError("canonical visit counts are not 10489/2130")
    k_max = int(train_targets.sum(axis=1).max())
    if k_max < 1 or k_max > MEDICATIONS:
        raise RuntimeError("invalid Train maximum medication cardinality")
    dev_max = int(dev_targets.sum(axis=1).max())
    dev_oracle_k_clipped = int((dev_targets.sum(axis=1) > k_max).sum())
    frozen_ddi_pairs = _ddi_pairs(ddi, vocabulary)
    eligible_train = tuple(str(int(i)) for i in train_patients)
    eligible_dev = tuple(str(int(i)) for i in dev_patients)

    numeric_policy = configure_numeric_policy()
    config = _scientific_config(args.variant, args.seed, k_max, numeric_policy)
    if args.preflight_only:
        return {
            "preflight_only": True,
            "source_revision": args.source_revision,
            "config": config,
            "split": {
                "train_patients": len(train_patients),
                "dev_patients": len(dev_patients),
                "train_visits": len(train_rows),
                "dev_visits": len(dev_rows),
            },
            "k_max_train": k_max,
            "k_max_dev": dev_max,
            "dev_oracle_k_clipped_visits": dev_oracle_k_clipped,
        }
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")

    _seed_everything(args.seed)
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = ECRC(dx, proc, k_max, args.variant).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(axis=0)).to(device))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    generator = np.random.RandomState(args.seed)
    train_model_rows = _model_rows(train_rows)

    progress: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "running",
        "source_revision": args.source_revision,
        "variant": args.variant,
        "seed": args.seed,
        "config": config,
        "completed_epochs": 0,
        "selected_epoch": None,
        "selected_dev_jaccard": None,
        "epochs": progress,
    }
    _write_progress(output, state)

    best_j = float("-inf")
    best_epoch = None
    best_state = None
    best_dev_scores = None
    best_dev_counts = None
    best_dev_metrics = None
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        total_loss = 0.0
        total_med_nll = 0.0
        total_size_nll = 0.0
        total_items = 0
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            rows = [train_model_rows[int(i)] for i in indices]
            batch = _to_device(pack_inputs(rows, dx, proc), device)
            target = torch.from_numpy(train_targets[indices]).to(device)
            target_k = target.sum(dim=-1).to(torch.long)
            optimizer.zero_grad(set_to_none=True)
            output_values = model(batch, k=target_k)
            loss, pieces = joint_objective(
                output_values,
                target,
                target_k,
                exact=model.exact,
            )
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite ECRC training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            total_loss += float(loss.item()) * size
            total_med_nll += float(pieces["medication_nll"].item()) * size
            total_size_nll += float(pieces["size_nll"].item()) * size
            total_items += size

        dev_scores, dev_counts = _predict(
            model, dev_rows, dev_targets, dx, proc, device, oracle_k=False
        )
        dev_metrics = _evaluate_scores(
            dev_rows,
            dev_targets,
            dev_scores,
            dev_counts,
            vocabulary=vocabulary,
            ddi_pairs=frozen_ddi_pairs,
            eligible_patient_ids=eligible_dev,
        )
        jaccard = float(dev_metrics["jaccard"])
        entry = {
            "epoch": epoch,
            "train_loss": total_loss / total_items,
            "train_medication_nll": total_med_nll / total_items,
            "train_size_nll": total_size_nll / total_items,
            "dev_metrics": dev_metrics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        progress.append(entry)
        if jaccard > best_j:
            best_j = jaccard
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_scores = dev_scores.copy()
            best_dev_counts = dev_counts.copy()
            best_dev_metrics = dict(dev_metrics)
            torch.save(best_state, output / "selected_checkpoint.pt")
        state["completed_epochs"] = epoch
        state["selected_epoch"] = best_epoch
        state["selected_dev_jaccard"] = best_j
        _write_progress(output, state)

    if (
        best_state is None
        or best_epoch is None
        or best_dev_scores is None
        or best_dev_counts is None
        or best_dev_metrics is None
    ):
        raise RuntimeError("no complete Dev checkpoint was selected")

    model.load_state_dict(best_state)
    train_scores, train_counts = _predict(
        model, train_rows, train_targets, dx, proc, device, oracle_k=False
    )
    train_metrics = _evaluate_scores(
        train_rows,
        train_targets,
        train_scores,
        train_counts,
        vocabulary=vocabulary,
        ddi_pairs=frozen_ddi_pairs,
        eligible_patient_ids=eligible_train,
    )
    oracle_scores, oracle_counts = _predict(
        model, dev_rows, dev_targets, dx, proc, device, oracle_k=True
    )
    oracle_metrics = _evaluate_scores(
        dev_rows,
        dev_targets,
        oracle_scores,
        oracle_counts,
        vocabulary=vocabulary,
        ddi_pairs=frozen_ddi_pairs,
        eligible_patient_ids=eligible_dev,
    )
    np.savez_compressed(
        output / "selected_predictions.npz",
        train_scores=train_scores,
        train_counts=train_counts,
        train_targets=train_targets,
        dev_scores=best_dev_scores,
        dev_counts=best_dev_counts,
        dev_targets=dev_targets,
        dev_oracle_scores=oracle_scores,
        dev_oracle_counts=oracle_counts,
    )

    result = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": PROFILE_ID,
        "variant": args.variant,
        "seed": args.seed,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "cardinality_support": {
            "k_max_train": k_max,
            "k_max_dev": dev_max,
            "dev_oracle_k_clipped_visits": dev_oracle_k_clipped,
        },
        "selected_epoch": best_epoch,
        "selected_checkpoint": {
            "Train_predicted_k": train_metrics,
            "Dev_predicted_k": best_dev_metrics,
            "Dev_oracle_k_diagnostic": oracle_metrics,
        },
        "epoch_60_dev_predicted_k": progress[-1]["dev_metrics"],
        "progress": progress,
        "wall_time_seconds": time.time() - start_time,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "test_accessed": False,
        "oracle_k_is_privileged_diagnostic_only": True,
    }
    state["status"] = "complete"
    _write_progress(output, state)
    (output / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
