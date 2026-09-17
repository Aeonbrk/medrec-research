#!/usr/bin/env python3
"""Run one RIME arm on the frozen MIMIC-III canonical-131 Dev profile."""

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
    from rime import (
        CLINICAL_LAYERS,
        DIM,
        FF_DIM,
        FLIP_CAP,
        HEADS,
        MEDICATIONS,
        RIMEModel,
        configure_numeric_policy,
        context_loss,
        greedy_decode,
        pack_inputs,
        scores_for_set,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from rime import (
        CLINICAL_LAYERS,
        DIM,
        FF_DIM,
        FLIP_CAP,
        HEADS,
        MEDICATIONS,
        RIMEModel,
        configure_numeric_policy,
        context_loss,
        greedy_decode,
        pack_inputs,
        scores_for_set,
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
SEED = 20260920
EPOCHS = 60
BATCH_SIZE = 16
LEARNING_RATE = 3e-4
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
        raise RuntimeError("committed MIII profile ID does not match RIME")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("committed MIII snapshot ID does not match RIME")
    split = profile.get("split", {})
    if (
        split.get("train", {}).get("patients") != 4233
        or split.get("dev", {}).get("patients") != 1004
        or split.get("train", {}).get("visits") != 10489
        or split.get("dev", {}).get("visits") != 2130
    ):
        raise RuntimeError("committed MIII split does not match RIME")
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
        raise RuntimeError("DDI must be finite, symmetric, and zero-diagonal 131 by 131")
    vocabulary = tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))
    if len(set(vocabulary)) != MEDICATIONS:
        raise RuntimeError("medication vocabulary words are not unique")
    return len(diagnosis_ids), len(procedure_ids), vocabulary


def _git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


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


def _scientific_config(variant: str, numeric_policy: dict[str, object]) -> dict[str, Any]:
    return {
        "variant": variant,
        "medications": MEDICATIONS,
        "hidden_dim": DIM,
        "set_hidden_dim": 128,
        "clinical_attention_blocks": CLINICAL_LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "dropout": 0.1,
        "loss": "0.5 * BCE(C_pos) + 0.5 * BCE(C_err)",
        "context_sampling": "uniform k in [0, |Y|], uniform k-subset, one uniform n from M\\Y",
        "p_x": "masked mean of target-free assembled MICA clinical tokens",
        "decoder": "positive-gain deterministic single-medication flips from empty set",
        "flip_cap": FLIP_CAP,
        "decoder_operating_point": "native only; no threshold or beta",
        "selection": "joint Dev patient-macro Jaccard over complete epochs with native decoder",
        "numeric_policy": numeric_policy,
    }


def _write_progress(output: Path, state: dict[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, output / "progress.json")


def _ddi_pairs(vocabulary: tuple[str, ...], ddi: np.ndarray) -> tuple[tuple[str, str], ...]:
    return tuple(
        (vocabulary[left], vocabulary[right])
        for left in range(MEDICATIONS)
        for right in range(left + 1, MEDICATIONS)
        if ddi[left, right] != 0
    )


def _samples(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    selected: np.ndarray,
    scores: np.ndarray,
    vocabulary: tuple[str, ...],
) -> list[VisitPrediction]:
    result: list[VisitPrediction] = []
    for index, row in enumerate(rows):
        target = tuple(vocabulary[medication] for medication in np.flatnonzero(targets[index]))
        predicted = tuple(vocabulary[medication] for medication in np.flatnonzero(selected[index]))
        result.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=target,
                predicted_medications=predicted,
                medication_scores=tuple(float(value) for value in scores[index]),
            )
        )
    return result


def _count_diagnostics(targets: np.ndarray, selected: np.ndarray) -> dict[str, float]:
    target_count = targets.sum(axis=1).astype(np.float64)
    predicted_count = selected.sum(axis=1).astype(np.float64)
    error = predicted_count - target_count
    return {
        "count_mae_visit": float(np.abs(error).mean()),
        "count_bias_visit": float(error.mean()),
        "target_count_mean_visit": float(target_count.mean()),
        "predicted_count_mean_visit": float(predicted_count.mean()),
    }


def _predict(
    model: RIMEModel,
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
    dx: int,
    proc: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, Any]]:
    model.eval()
    score_rows: list[np.ndarray] = []
    selected_rows: list[np.ndarray] = []
    add_rows: list[np.ndarray] = []
    remove_rows: list[np.ndarray] = []
    cap_rows: list[np.ndarray] = []
    composition_differences: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(
                    _model_rows(rows[start : start + BATCH_SIZE]), dx, proc
                ).items()
            }
            encoded = model(batch)
            selected, adds, removes, caps = greedy_decode(model, encoded)
            scores = scores_for_set(model, encoded, selected)
            alternate = selected.clone()
            valid_rows: list[int] = []
            for row_index in range(alternate.shape[0]):
                present = torch.nonzero(selected[row_index], as_tuple=False).flatten()
                absent = torch.nonzero(~selected[row_index], as_tuple=False).flatten()
                if len(present) == 0 or len(absent) == 0:
                    continue
                alternate[row_index, int(present[0])] = False
                alternate[row_index, int(absent[0])] = True
                valid_rows.append(row_index)
            if valid_rows:
                alternate_scores = scores_for_set(model, encoded, alternate)
                for row_index in valid_rows:
                    common_absent = (~selected[row_index]) & (~alternate[row_index])
                    if bool(common_absent.any()):
                        composition_differences.append(
                            (
                                scores[row_index, common_absent]
                                - alternate_scores[row_index, common_absent]
                            )
                            .abs()
                            .cpu()
                            .numpy()
                        )
            score_rows.append(scores.cpu().numpy())
            selected_rows.append(selected.cpu().numpy())
            add_rows.append(adds.cpu().numpy())
            remove_rows.append(removes.cpu().numpy())
            cap_rows.append(caps.cpu().numpy())
    scores_array = np.concatenate(score_rows, axis=0)
    selected_array = np.concatenate(selected_rows, axis=0).astype(bool, copy=False)
    adds = np.concatenate(add_rows, axis=0)
    removes = np.concatenate(remove_rows, axis=0)
    caps = np.concatenate(cap_rows, axis=0).astype(bool, copy=False)
    if not np.isfinite(scores_array).all():
        raise RuntimeError("non-finite RIME marginal scores")
    metrics = evaluate(
        _samples(rows, targets, selected_array, scores_array, vocabulary),
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
    )
    metrics.update(_count_diagnostics(targets, selected_array))
    diagnostics = {
        "adds": int(adds.sum()),
        "removes": int(removes.sum()),
        "total_flips": int(adds.sum() + removes.sum()),
        "cap_hits": int(caps.sum()),
        "cap_hit_rate": float(caps.mean()),
        "composition_sensitivity": {
            "same_cardinality_pairs": len(composition_differences),
            "mean_abs_marginal_delta": float(
                np.concatenate(composition_differences).mean() if composition_differences else 0.0
            ),
            "max_abs_marginal_delta": float(
                np.concatenate(composition_differences).max() if composition_differences else 0.0
            ),
            "fraction_nonzero": float(
                (np.concatenate(composition_differences) > 1e-7).mean()
                if composition_differences
                else 0.0
            ),
            "construction": "replace the lowest selected medication with the lowest unselected medication and compare candidates absent from both contexts",
        },
    }
    return scores_array, selected_array, metrics, diagnostics


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    git_root = _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if git_root == output or git_root in output.parents:
        raise RuntimeError("output directory must be outside the run checkout")
    if snapshot.name != SNAPSHOT_ID:
        raise RuntimeError("snapshot root identity does not match RIME")
    if train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("Train/Dev root identity does not match RIME")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    _validate_profile(snapshot, train_dev_root)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(index for index in range(split, len(records)) if _is_dev(index))
    if (len(records), len(train_patients), len(dev_patients)) != (6350, 4233, 1004):
        raise RuntimeError("canonical patient split counts are not 6350/4233/1004")
    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    dx, proc, vocabulary = _validate_data(
        records, voc, train_rows, dev_rows, train_targets, dev_targets, ddi
    )
    if (len(train_rows), len(dev_rows)) != (10489, 2130):
        raise RuntimeError("canonical visit counts are not 10489/2130")
    ddi_pairs = _ddi_pairs(vocabulary, ddi)
    split_info = {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train_rows),
        "dev_visits": len(dev_rows),
    }
    numeric_policy = configure_numeric_policy()
    config = _scientific_config(args.variant, numeric_policy)
    progress: list[dict[str, Any]] = []
    progress_state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "preflight_complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "split": split_info,
        "completed_epochs": 0,
        "selected_epoch": None,
        "selected_dev_jaccard": None,
        "epoch_60_dev_metrics": None,
        "epochs": progress,
    }
    if args.preflight_only:
        return {
            "preflight_only": True,
            "source_revision": args.source_revision,
            "config": config,
            "split": split_info,
        }
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    _write_progress(output, progress_state)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for RIME experiment execution")

    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    _seed_everything(SEED)
    model = RIMEModel(dx, proc, args.variant).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, torch.Tensor] | None = None
    context_rng = random.Random(SEED)
    visit_rng = np.random.RandomState(SEED)
    start_time = time.time()
    progress_state["status"] = "running"
    _write_progress(output, progress_state)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = visit_rng.permutation(len(train_rows))
        totals = [0.0, 0.0, 0.0, 0]
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(
                    _model_rows([train_rows[int(i)] for i in indices]), dx, proc
                ).items()
            }
            targets = torch.from_numpy(train_targets[indices]).to(device)
            optimizer.zero_grad(set_to_none=True)
            encoded = model(batch)
            loss, positive_loss, erroneous_loss = context_loss(model, encoded, targets, context_rng)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite RIME training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            totals[0] += float(loss.item()) * size
            totals[1] += float(positive_loss.item()) * size
            totals[2] += float(erroneous_loss.item()) * size
            totals[3] += size
        dev_scores, dev_selected, dev_metrics, dev_diagnostics = _predict(
            model, dev_rows, dev_targets, vocabulary, ddi_pairs, dx, proc, device
        )
        candidate = SelectionCandidate(epoch, 0.0, float(dev_metrics["jaccard"]), 0)
        if best_candidate is None:
            best_candidate = candidate
        else:
            best_candidate = select_joint(
                (best_candidate, candidate), operating_point_order=(0.0,), native_default=0.0
            )
        if best_candidate == candidate:
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            torch.save(best_state, output / "selected_checkpoint.pt")
        entry = {
            "epoch": epoch,
            "train_loss": totals[0] / totals[3],
            "train_positive_context_bce": totals[1] / totals[3],
            "train_error_context_bce": totals[2] / totals[3],
            "dev_metrics": dev_metrics,
            "dev_inference": dev_diagnostics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        progress.append(entry)
        progress_state["completed_epochs"] = epoch
        progress_state["selected_epoch"] = best_candidate.checkpoint
        progress_state["selected_dev_jaccard"] = best_candidate.patient_macro_jaccard
        progress_state["epoch_60_dev_metrics"] = dev_metrics if epoch == EPOCHS else None
        _write_progress(output, progress_state)

    if best_candidate is None or best_state is None:
        raise RuntimeError("no complete Dev checkpoint was selected")
    model.load_state_dict(best_state)
    train_scores, train_selected, train_metrics, train_diagnostics = _predict(
        model, train_rows, train_targets, vocabulary, ddi_pairs, dx, proc, device
    )
    dev_scores, dev_selected, dev_metrics, dev_diagnostics = _predict(
        model, dev_rows, dev_targets, vocabulary, ddi_pairs, dx, proc, device
    )
    np.savez_compressed(
        output / "selected_predictions.npz",
        train_scores=train_scores,
        train_selected=train_selected,
        train_targets=train_targets,
        dev_scores=dev_scores,
        dev_selected=dev_selected,
        dev_targets=dev_targets,
    )
    result = {
        "schema_version": 1,
        "status": "complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "split": split_info,
        "completed_epochs": len(progress),
        "selected_epoch": best_candidate.checkpoint,
        "selected_checkpoint": {"Train": train_metrics, "Dev": dev_metrics},
        "selected_inference": {"Train": train_diagnostics, "Dev": dev_diagnostics},
        "epoch_60": {"Dev": progress[-1]["dev_metrics"]},
        "metrics": {"Train": train_metrics, "Dev": dev_metrics},
        "progress": progress,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "source_bound_references": {
            "profile": PROFILE_ID,
            "snapshot": SNAPSHOT_ID,
            "train_dev": TRAIN_DEV_ID,
            "test_accessed": False,
        },
    }
    progress_state["status"] = "complete"
    progress_state["epoch_60_dev_metrics"] = progress[-1]["dev_metrics"]
    _write_progress(output, progress_state)
    (output / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=RIMEModel.VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
