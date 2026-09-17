#!/usr/bin/env python3
"""Run MedLedger or NormalizedLedger on the frozen MIMIC-III canonical-131 Dev profile."""

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
    from medledger import (
        DEFAULT_TAU_INIT,
        DIM,
        DROPOUT,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        MedLedgerModel,
        configure_numeric_policy,
        pack_inputs,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from medledger import (
        DEFAULT_TAU_INIT,
        DIM,
        DROPOUT,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        MedLedgerModel,
        configure_numeric_policy,
        pack_inputs,
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
OPERATING_POINTS = tuple(round(value / 100.0, 2) for value in range(5, 100, 5))
NATIVE_DEFAULT = 0.35
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
        raise RuntimeError("committed MIII profile ID does not match MedLedger")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("committed MIII snapshot ID does not match MedLedger")
    split = profile.get("split", {})
    if (
        split.get("train", {}).get("patients") != 4233
        or split.get("dev", {}).get("patients") != 1004
        or split.get("train", {}).get("visits") != 10489
        or split.get("dev", {}).get("visits") != 2130
    ):
        raise RuntimeError("committed MIII split does not match MedLedger")
    assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = assets.get(name, {})
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"MIII source asset is missing or is a symlink: {name}")
        if path.stat().st_size != expected.get("bytes") or _sha256_file(path) != expected.get(
            "sha256"
        ):
            raise RuntimeError(f"MIII source asset hash does not match the frozen profile: {name}")
    for name, expected_hash in (
        ("train_targets.npy", split.get("train", {}).get("target_array_sha256")),
        ("dev_targets.npy", split.get("dev", {}).get("target_array_sha256")),
    ):
        path = train_dev_root / name
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected_hash:
            raise RuntimeError(f"MIII target array hash does not match the frozen profile: {name}")


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
                raise RuntimeError(f"{name} target mismatch at row {index}")
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
        raise RuntimeError(f"source revision does not match git HEAD: expected {source_revision}")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(f"run checkout is not clean:\n{status}")
    return root


def _scientific_config(variant: str, numeric_policy: dict[str, object]) -> dict[str, Any]:
    return {
        "variant": variant,
        "medications": MEDICATIONS,
        "hidden_dim": DIM,
        "clinical_attention_blocks": LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "dropout": DROPOUT,
        "tau_init": DEFAULT_TAU_INIT,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "loss": "mean BCEWithLogits across 131 medications",
        "nuisance_path": "eta_m = v_m^T [log1p(num_dx), log1p(num_proc), log1p(num_hist)], v_m init 0",
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
        "selection": "joint Dev patient-macro Jaccard over complete epochs with threshold grid",
        "numeric_policy": numeric_policy,
    }


def _write_progress(output: Path, state: dict[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, output / "progress.json")


def _predict_logits(
    model: MedLedgerModel,
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    dx: int,
    proc: int,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    chunks: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = _model_rows(rows[start : start + BATCH_SIZE])
            batch = {
                key: value.to(device) for key, value in pack_inputs(batch_rows, dx, proc).items()
            }
            logits = model(batch)
            chunks.append(logits.detach().cpu().numpy())
    values = np.concatenate(chunks, axis=0)
    if values.shape != targets.shape:
        raise RuntimeError("model logits are not aligned with targets")
    return values


def _evaluate_operating_point(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    samples: list[VisitPrediction] = []
    for index, row in enumerate(rows):
        target = tuple(vocabulary[m] for m in np.flatnonzero(targets[index] > 0.5))
        predicted = tuple(vocabulary[m] for m in np.flatnonzero(probabilities[index] >= threshold))
        samples.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=target,
                predicted_medications=predicted,
                medication_scores=tuple(float(v) for v in probabilities[index]),
            )
        )
    return evaluate(samples, vocabulary=vocabulary, ddi_pairs=ddi_pairs)


def _evaluate_multiplicity(
    model: MedLedgerModel,
    rows: Sequence[Mapping[str, Any]],
    selected_threshold: float,
    dx: int,
    proc: int,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    outside_mass_ratios: list[float] = []
    effective_evidence_counts: list[float] = []
    total_pos_predictions = 0

    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = _model_rows(rows[start : start + BATCH_SIZE])
            batch = {
                key: value.to(device) for key, value in pack_inputs(batch_rows, dx, proc).items()
            }
            logits, diag = model(batch, return_diagnostics=True)
            probs = torch.sigmoid(logits)
            c_pos = diag["c_pos"]  # [B, M, K]
            s_pos = diag["s_pos"]  # [B, M]

            predicted_mask = probs >= selected_threshold  # [B, M]
            for b in range(probs.shape[0]):
                pred_meds = torch.nonzero(predicted_mask[b], as_tuple=False).flatten()
                for m_idx in pred_meds:
                    m = int(m_idx.item())
                    total_pos_predictions += 1
                    s = float(s_pos[b, m].item())
                    c_items = c_pos[b, m]  # [K]
                    if s > 1e-6:
                        max_c = float(c_items.max().item())
                        ratio = max(0.0, (s - max_c) / s)
                        outside_mass_ratios.append(ratio)
                        c_sq_sum = float((c_items**2).sum().item())
                        effective_count = (s**2) / c_sq_sum if c_sq_sum > 1e-8 else 1.0
                        effective_evidence_counts.append(effective_count)
                    else:
                        outside_mass_ratios.append(0.0)
                        effective_evidence_counts.append(1.0)

    outside_arr = np.asarray(outside_mass_ratios, dtype=np.float64)
    eff_arr = np.asarray(effective_evidence_counts, dtype=np.float64)
    return {
        "total_positive_predictions": total_pos_predictions,
        "mean_mass_outside_top1": float(outside_arr.mean()) if len(outside_arr) else 0.0,
        "median_mass_outside_top1": float(np.median(outside_arr)) if len(outside_arr) else 0.0,
        "std_mass_outside_top1": float(outside_arr.std()) if len(outside_arr) else 0.0,
        "fraction_multiplicity_gt_0.10": float((outside_arr > 0.10).mean())
        if len(outside_arr)
        else 0.0,
        "fraction_multiplicity_gt_0.25": float((outside_arr > 0.25).mean())
        if len(outside_arr)
        else 0.0,
        "fraction_multiplicity_gt_0.50": float((outside_arr > 0.50).mean())
        if len(outside_arr)
        else 0.0,
        "mean_effective_evidence_count": float(eff_arr.mean()) if len(eff_arr) else 1.0,
        "median_effective_evidence_count": float(np.median(eff_arr)) if len(eff_arr) else 1.0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    numeric_policy = configure_numeric_policy()
    source_root = _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()

    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev root identity does not match the frozen profile")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if source_root == output or source_root in output.parents:
        raise RuntimeError("output directory must be outside the source checkout")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output directory is not empty: {output}")

    output.mkdir(parents=True, exist_ok=True)
    _validate_profile(snapshot, train_dev_root)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split_border = int(len(records) * 2 / 3)
    train_patients = tuple(range(split_border))
    dev_patients = tuple(index for index in range(split_border, len(records)) if _is_dev(index))
    if (len(train_patients), len(dev_patients)) != (4233, 1004):
        raise RuntimeError(
            f"frozen patient split counts changed: {len(train_patients)}, {len(dev_patients)}"
        )

    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    dx, proc, vocabulary = _validate_data(
        records, voc, train_rows, dev_rows, train_targets, dev_targets, ddi
    )

    ddi_pairs = tuple(
        (vocabulary[left], vocabulary[right])
        for left, right in zip(*np.triu(ddi, 1).nonzero())  # noqa: B905
    )

    config = _scientific_config(args.variant, numeric_policy)
    device = torch.device(
        f"cuda:{args.gpu}"
        if args.gpu is not None and torch.cuda.is_available()
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    _seed_everything(SEED)
    model = MedLedgerModel(dx, proc, variant=args.variant, medication_count=MEDICATIONS).to(device)

    # Initialize prevalence bias from Train targets log-odds
    train_prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)
    model.initialize_prevalence(train_prevalence)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )

    if args.preflight_only:
        return {
            "status": "preflight_only_complete",
            "variant": args.variant,
            "parameter_count": sum(p.numel() for p in model.parameters()),
            "device": str(device),
        }

    progress: list[dict[str, Any]] = []
    progress_state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "running",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "seed": SEED,
        "variant": args.variant,
        "config": config,
        "completed_epochs": 0,
        "selected_epoch": None,
        "selected_operating_point": None,
        "selected_dev_jaccard": None,
    }
    _write_progress(output, progress_state)

    all_candidates: list[SelectionCandidate] = []
    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, torch.Tensor] | None = None
    best_dev_logits: np.ndarray | None = None
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_rng = random.Random(SEED + epoch * 10007)
        indices_list = list(range(len(train_rows)))
        epoch_rng.shuffle(indices_list)

        loss_sum = 0.0
        example_count = 0

        for start in range(0, len(indices_list), BATCH_SIZE):
            batch_indices = indices_list[start : start + BATCH_SIZE]
            batch_data = {
                key: value.to(device)
                for key, value in pack_inputs(
                    _model_rows([train_rows[i] for i in batch_indices]), dx, proc
                ).items()
            }
            targets = torch.from_numpy(train_targets[batch_indices]).to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_data)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite training loss at epoch {epoch}")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()

            size = len(batch_indices)
            loss_sum += float(loss.item()) * size
            example_count += size

        # Dev evaluation at complete epoch:
        dev_logits = _predict_logits(model, dev_rows, dev_targets, dx, proc, device)
        dev_probs = 1.0 / (1.0 + np.exp(-np.asarray(dev_logits, dtype=np.float64)))

        checkpoint_candidates: list[SelectionCandidate] = []
        candidate_metric_map: dict[float, dict[str, Any]] = {}

        for op_idx, threshold in enumerate(OPERATING_POINTS):
            metrics = _evaluate_operating_point(
                dev_rows, dev_targets, dev_probs, threshold, vocabulary, ddi_pairs
            )
            cand = SelectionCandidate(epoch, threshold, float(metrics["jaccard"]), op_idx)
            checkpoint_candidates.append(cand)
            all_candidates.append(cand)
            candidate_metric_map[threshold] = metrics

        best_checkpoint_cand = select_joint(
            checkpoint_candidates,
            operating_point_order=OPERATING_POINTS,
            native_default=NATIVE_DEFAULT,
        )

        overall_best = select_joint(
            all_candidates,
            operating_point_order=OPERATING_POINTS,
            native_default=NATIVE_DEFAULT,
        )

        if best_candidate is None or overall_best == best_checkpoint_cand:
            best_candidate = overall_best
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_logits = dev_logits.copy()
            torch.save(best_state, output / "selected_checkpoint.pt")

        current_metrics = candidate_metric_map[best_checkpoint_cand.operating_point]
        entry = {
            "epoch": epoch,
            "train_loss": loss_sum / example_count,
            "checkpoint_selected_threshold": best_checkpoint_cand.operating_point,
            "checkpoint_selected_jaccard": best_checkpoint_cand.patient_macro_jaccard,
            "overall_best_epoch": overall_best.checkpoint,
            "overall_best_threshold": overall_best.operating_point,
            "overall_best_jaccard": overall_best.patient_macro_jaccard,
            "dev_metrics": current_metrics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": (
                torch.cuda.max_memory_allocated(device) / 1048576.0
                if torch.cuda.is_available()
                else 0.0
            ),
        }
        progress.append(entry)
        progress_state["completed_epochs"] = epoch
        progress_state["selected_epoch"] = overall_best.checkpoint
        progress_state["selected_operating_point"] = overall_best.operating_point
        progress_state["selected_dev_jaccard"] = overall_best.patient_macro_jaccard
        progress_state["epoch_60_dev_metrics"] = current_metrics if epoch == EPOCHS else None
        _write_progress(output, progress_state)

    if best_candidate is None or best_state is None or best_dev_logits is None:
        raise RuntimeError("no complete Dev checkpoint was selected")

    # Load selected checkpoint for final evaluation:
    model.load_state_dict(best_state)
    selected_threshold = float(best_candidate.operating_point)

    train_logits = _predict_logits(model, train_rows, train_targets, dx, proc, device)
    train_probs = 1.0 / (1.0 + np.exp(-np.asarray(train_logits, dtype=np.float64)))
    train_metrics = _evaluate_operating_point(
        train_rows, train_targets, train_probs, selected_threshold, vocabulary, ddi_pairs
    )

    final_dev_probs = 1.0 / (1.0 + np.exp(-np.asarray(best_dev_logits, dtype=np.float64)))
    dev_metrics = _evaluate_operating_point(
        dev_rows, dev_targets, final_dev_probs, selected_threshold, vocabulary, ddi_pairs
    )

    # Multiplicity diagnostic D1 on Dev:
    multiplicity_diag = _evaluate_multiplicity(
        model, dev_rows, selected_threshold, dx, proc, device
    )

    # Save predictions array:
    np.savez_compressed(
        output / "selected_predictions.npz",
        train_logits=train_logits,
        train_targets=train_targets,
        dev_logits=best_dev_logits,
        dev_targets=dev_targets,
        selected_threshold=np.array([selected_threshold], dtype=np.float32),
    )

    result = {
        "schema_version": 1,
        "status": "complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "completed_epochs": len(progress),
        "selected_epoch": best_candidate.checkpoint,
        "selected_threshold": selected_threshold,
        "selected_checkpoint": {"Train": train_metrics, "Dev": dev_metrics},
        "diagnostics": {
            "d1_multiplicity": multiplicity_diag,
        },
        "epoch_60": {"Dev": progress[-1]["dev_metrics"]},
        "progress": progress,
        "cuda_peak_memory_mb": (
            torch.cuda.max_memory_allocated(device) / 1048576.0
            if torch.cuda.is_available()
            else 0.0
        ),
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
    _write_progress(output, progress_state)
    (output / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=MedLedgerModel.VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--gpu", type=int, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
