#!/usr/bin/env python3
# ruff: noqa: UP006,UP035,UP045
"""Run one frozen RouteAux/RouteFact Train/Dev arm on canonical MIMIC-III."""

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

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
from routefact import (  # noqa: E402
    DDI_WEIGHT,
    MEDICATIONS,
    ROUTE_AUX_WEIGHT,
    RouteFactModel,
    objective,
)

MICA_DIR = THIS_DIR.parents[0] / "mica"
if str(MICA_DIR) not in sys.path:
    sys.path.insert(0, str(MICA_DIR))
from mica import DIM, FF_DIM, HEADS, LAYERS, configure_numeric_policy, pack_inputs  # noqa: E402

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
SEED = 20260922
EPOCHS = 60
BATCH_SIZE = 16
LEARNING_RATE = 1e-4
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_source(revision: str) -> None:
    if _git_revision(REPO_ROOT) != revision:
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
                    "_visit_id": "%d:%d" % (int(patient_index), visit_index),
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


def _validate_profile(snapshot: Path, train_dev: Path) -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError("committed profile ID does not match RouteFact")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("snapshot ID does not match RouteFact")
    split = profile.get("split", {})
    if (
        split.get("train", {}).get("patients") != 4233
        or split.get("dev", {}).get("patients") != 1004
        or split.get("train", {}).get("visits") != 10489
        or split.get("dev", {}).get("visits") != 2130
    ):
        raise RuntimeError("frozen Train/Dev counts changed")
    assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = assets.get(name, {})
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("source asset is missing or symlinked: " + name)
        if path.stat().st_size != expected.get("bytes") or _sha256(path) != expected.get("sha256"):
            raise RuntimeError("source asset hash changed: " + name)
    for name, expected in (
        ("train_targets.npy", split.get("train", {}).get("target_array_sha256")),
        ("dev_targets.npy", split.get("dev", {}).get("target_array_sha256")),
    ):
        path = train_dev / name
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise RuntimeError("medication target array hash changed: " + name)


def _validate_route_assets(
    route_root: Path, source_revision: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[str, ...], Dict[str, Any]]:
    metadata = json.loads((route_root / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "complete" or metadata.get("profile_id") != PROFILE_ID:
        raise RuntimeError("route target metadata does not match RouteFact profile")
    if metadata.get("source_revision") != source_revision:
        raise RuntimeError("route targets were not built from the run source revision")
    if metadata.get("route_vocabulary_source") != "Train only" or metadata.get(
        "medication_route_support_mask_source"
    ) != "Train only":
        raise RuntimeError("route vocabulary/support mask are not Train-only frozen")
    for name, expected in metadata.get("assets", {}).items():
        path = route_root / name
        if (
            not path.is_file()
            or path.stat().st_size != expected.get("bytes")
            or _sha256(path) != expected.get("sha256")
        ):
            raise RuntimeError("route asset integrity failed: " + name)
    train_route = np.load(route_root / "train_route_targets.npy", mmap_mode="r")
    dev_route = np.load(route_root / "dev_route_targets.npy", mmap_mode="r")
    allowed = np.asarray(
        np.load(route_root / "allowed_route_mask.npy", mmap_mode="r"), dtype=np.uint8
    )
    route_payload = json.loads(
        (route_root / "route_vocabulary.json").read_text(encoding="utf-8")
    )
    routes = tuple(str(value) for value in route_payload["routes"])
    if train_route.shape != (10489, MEDICATIONS, len(routes)):
        raise RuntimeError("Train route target shape mismatch")
    if dev_route.shape != (2130, MEDICATIONS, len(routes)):
        raise RuntimeError("Dev route target shape mismatch")
    if allowed.shape != (MEDICATIONS, len(routes)) or np.any(allowed.sum(axis=1) < 1):
        raise RuntimeError("allowed route mask is malformed")
    return train_route, dev_route, allowed, routes, metadata


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
        raise RuntimeError("canonical patient count changed")
    medication = voc["med_voc"]
    diagnosis = voc["diag_voc"]
    procedure = voc["pro_voc"]
    med_codes = tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))
    dx_ids = set(int(key) for key in diagnosis.idx2word)
    proc_ids = set(int(key) for key in procedure.idx2word)
    if set(int(key) for key in medication.idx2word) != set(range(MEDICATIONS)):
        raise RuntimeError("medication vocabulary IDs changed")
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous")
    if train_targets.shape != (len(train_rows), MEDICATIONS) or dev_targets.shape != (
        len(dev_rows),
        MEDICATIONS,
    ):
        raise RuntimeError("medication targets are not visit-aligned")
    for rows, targets in ((train_rows, train_targets), (dev_rows, dev_targets)):
        for index, row in enumerate(rows):
            expected = np.zeros(MEDICATIONS, dtype=np.uint8)
            expected[list(set(int(value) for value in row["_medications"]))] = 1
            if not np.array_equal(expected, np.asarray(targets[index] > 0.5, dtype=np.uint8)):
                raise RuntimeError("medication target mismatch")
    if (
        ddi.shape != (MEDICATIONS, MEDICATIONS)
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
    ):
        raise RuntimeError("DDI matrix is malformed")
    return len(dx_ids), len(proc_ids), med_codes


def _predictions(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    logits: np.ndarray,
    threshold: float,
    vocabulary: Tuple[str, ...],
) -> Tuple[VisitPrediction, ...]:
    probabilities = 1.0 / (1.0 + np.exp(-np.asarray(logits, dtype=np.float64)))
    result: List[VisitPrediction] = []
    for index, row in enumerate(rows):
        target_ids = tuple(int(v) for v in np.flatnonzero(targets[index] > 0.5))
        pred_ids = tuple(int(v) for v in np.flatnonzero(probabilities[index] >= threshold))
        result.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[v] for v in target_ids),
                predicted_medications=tuple(vocabulary[v] for v in pred_ids),
                medication_scores=tuple(float(v) for v in probabilities[index]),
            )
        )
    return tuple(result)


def _surface(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    logits: np.ndarray,
    threshold: float,
    vocabulary: Tuple[str, ...],
    ddi: np.ndarray,
) -> Dict[str, Any]:
    coordinates = np.triu(np.asarray(ddi, dtype=np.float32), 1).nonzero()
    ddi_pairs = tuple((vocabulary[l], vocabulary[r]) for l, r in zip(*coordinates))
    return evaluate(
        _predictions(rows, targets, logits, threshold, vocabulary),
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
    )


def _best_key(candidate: SelectionCandidate) -> Tuple[float, float, int, int]:
    return (
        -float(candidate.patient_macro_jaccard),
        abs(float(candidate.operating_point) - NATIVE_DEFAULT),
        candidate.operating_point_index,
        candidate.checkpoint,
    )


def _predict_logits(
    model: RouteFactModel,
    rows: Sequence[Mapping[str, Any]],
    dx_count: int,
    proc_count: int,
    allowed: torch.Tensor,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    chunks: List[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = _model_rows(rows[start : start + BATCH_SIZE])
            packed = {
                key: value.to(device)
                for key, value in pack_inputs(batch_rows, dx_count, proc_count).items()
            }
            chunks.append(model(packed, allowed).detach().cpu().numpy())
    return np.concatenate(chunks, axis=0)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, path)


def _config(variant: str, route_count: int, numeric_policy: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "variant": variant,
        "medications": MEDICATIONS,
        "route_count": route_count,
        "intermediate_object": "multi-hot medication-route set",
        "route_factorization": (
            "noisy-OR over Train-supported routes per medication"
            if variant == "route_fact"
            else "auxiliary only; direct medication head is decision path"
        ),
        "hidden_dim": DIM,
        "clinical_attention_blocks": LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "gradient_clip": GRADIENT_CLIP,
        "loss": "medication BCE + %.2f route BCE + %.2f normalized DDI"
        % (ROUTE_AUX_WEIGHT, DDI_WEIGHT),
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
        "numeric_policy": dict(numeric_policy),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.seed != SEED:
        raise RuntimeError("RouteFact screen seed is frozen to %d" % SEED)
    _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    route_root = args.route_target_root.resolve()
    output = args.output_dir.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot/TrainDev identities do not match the frozen profile")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory must be empty")
    _validate_profile(snapshot, train_dev)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(i for i in range(split, len(records)) if _is_dev(i))
    train_rows = _build_rows(records, train_patients)
    dev_rows = _build_rows(records, dev_patients)
    train_targets = np.asarray(
        np.load(train_dev / "train_targets.npy", mmap_mode="r"), dtype=np.float32
    )
    dev_targets = np.asarray(
        np.load(train_dev / "dev_targets.npy", mmap_mode="r"), dtype=np.float32
    )
    dx_count, proc_count, vocabulary = _validate_data(
        records, voc, ddi, train_rows, dev_rows, train_targets, dev_targets
    )
    train_route, _dev_route, allowed_np, route_vocabulary, route_metadata = _validate_route_assets(
        route_root, args.source_revision
    )
    route_count = len(route_vocabulary)
    numeric_policy = configure_numeric_policy()
    _seed_everything(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteFactModel(dx_count, proc_count, route_count, args.variant).to(device)
    med_prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)
    route_prevalence = torch.from_numpy(
        np.asarray(train_route.mean(axis=0), dtype=np.float32)
    ).to(device)
    allowed = torch.from_numpy(allowed_np.astype(np.bool_)).to(device)
    model.initialize_prevalence(med_prevalence)
    model.initialize_route_prevalence(route_prevalence, med_prevalence, allowed)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())

    sample_indices = np.arange(min(BATCH_SIZE, len(train_rows)))
    packed = {
        key: value.to(device)
        for key, value in pack_inputs(
            _model_rows(train_rows[: len(sample_indices)]), dx_count, proc_count
        ).items()
    }
    med_logits, route_logits, _direct = model(packed, allowed, return_all=True)
    sample_route = torch.from_numpy(
        np.asarray(train_route[sample_indices], dtype=np.float32)
    ).to(device)
    sample_med = torch.from_numpy(train_targets[sample_indices]).to(device)
    route_mask = torch.ones(sample_med.shape, dtype=torch.bool, device=device)
    ddi_tensor = torch.from_numpy(ddi).to(device)
    loss, med_bce, route_bce, ddi_loss = objective(
        med_logits, sample_med, route_logits, sample_route, route_mask, allowed, ddi_tensor
    )
    if not all(torch.isfinite(value) for value in (loss, med_bce, route_bce, ddi_loss)):
        raise RuntimeError("RouteFact preflight produced a non-finite loss")
    loss.backward()
    if args.preflight_only:
        return {
            "status": "PASS",
            "preflight_only": True,
            "profile_id": PROFILE_ID,
            "source_revision": args.source_revision,
            "variant": args.variant,
            "seed": args.seed,
            "parameter_count": parameter_count,
            "route_count": route_count,
            "route_target_metadata_sha256": _sha256(route_root / "metadata.json"),
            "split": {
                "train_patients": len(train_patients),
                "dev_patients": len(dev_patients),
                "train_visits": len(train_rows),
                "dev_visits": len(dev_rows),
            },
            "test_loaded": False,
        }
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the full RouteFact screen")

    output.mkdir(parents=True, exist_ok=True)
    progress: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "running",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "variant": args.variant,
        "seed": args.seed,
        "parameter_count": parameter_count,
        "route_target_metadata_sha256": _sha256(route_root / "metadata.json"),
        "completed_epochs": 0,
        "selected_checkpoint": None,
        "selected_operating_point": None,
        "test_loaded": False,
    }
    _write_json(output / "progress.json", state)

    _seed_everything(args.seed)
    model = RouteFactModel(dx_count, proc_count, route_count, args.variant).to(device)
    model.initialize_prevalence(med_prevalence)
    model.initialize_route_prevalence(route_prevalence, med_prevalence, allowed)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    generator = np.random.RandomState(args.seed)
    best_candidate: Optional[SelectionCandidate] = None
    best_state: Optional[Dict[str, torch.Tensor]] = None
    best_dev_logits: Optional[np.ndarray] = None
    start_time = time.time()
    torch.cuda.reset_peak_memory_stats(device)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train_rows))
        sums = {"loss": 0.0, "med_bce": 0.0, "route_bce": 0.0, "ddi": 0.0}
        seen = 0
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch_rows = _model_rows([train_rows[int(index)] for index in indices])
            packed = {
                key: value.to(device)
                for key, value in pack_inputs(batch_rows, dx_count, proc_count).items()
            }
            med_target = torch.from_numpy(train_targets[indices]).to(device)
            route_target = torch.from_numpy(
                np.asarray(train_route[indices], dtype=np.float32)
            ).to(device)
            route_mask = torch.ones(med_target.shape, dtype=torch.bool, device=device)
            optimizer.zero_grad(set_to_none=True)
            med_logits, route_logits, _direct = model(packed, allowed, return_all=True)
            loss, med_bce, route_bce, ddi_loss = objective(
                med_logits,
                med_target,
                route_logits,
                route_target,
                route_mask,
                allowed,
                ddi_tensor,
            )
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite RouteFact training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            sums["loss"] += float(loss.item()) * size
            sums["med_bce"] += float(med_bce.item()) * size
            sums["route_bce"] += float(route_bce.item()) * size
            sums["ddi"] += float(ddi_loss.item()) * size
            seen += size

        dev_logits = _predict_logits(model, dev_rows, dx_count, proc_count, allowed, device)
        candidates: List[SelectionCandidate] = []
        candidate_metrics: List[Dict[str, Any]] = []
        for op_index, op in enumerate(OPERATING_POINTS):
            metrics = _surface(dev_rows, dev_targets, dev_logits, op, vocabulary, ddi)
            candidates.append(SelectionCandidate(epoch, op, metrics["jaccard"], op_index))
            candidate_metrics.append({"operating_point": op, "metrics": metrics})
        checkpoint_best = select_joint(
            candidates, operating_point_order=OPERATING_POINTS, native_default=NATIVE_DEFAULT
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
            for item in candidate_metrics
            if item["operating_point"] == checkpoint_best.operating_point
        )
        progress.append(
            {
                "epoch": epoch,
                "train_loss": sums["loss"] / seen,
                "train_med_bce": sums["med_bce"] / seen,
                "train_route_bce": sums["route_bce"] / seen,
                "train_ddi": sums["ddi"] / seen,
                "selected_operating_point": checkpoint_best.operating_point,
                "selected_dev_jaccard": checkpoint_best.patient_macro_jaccard,
                "dev_metrics": selected_metrics,
                "elapsed_seconds": time.time() - start_time,
                "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
            }
        )
        state["completed_epochs"] = epoch
        state["selected_checkpoint"] = best_candidate.checkpoint if best_candidate else None
        state["selected_operating_point"] = (
            best_candidate.operating_point if best_candidate else None
        )
        _write_json(output / "progress.json", state)

    if best_candidate is None or best_state is None or best_dev_logits is None:
        raise RuntimeError("no complete Dev checkpoint selected")
    model.load_state_dict(best_state)
    train_logits = _predict_logits(model, train_rows, dx_count, proc_count, allowed, device)
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
        "seed": args.seed,
        "variant": args.variant,
        "config": _config(args.variant, route_count, numeric_policy),
        "parameter_count": parameter_count,
        "route_target_metadata_sha256": _sha256(route_root / "metadata.json"),
        "route_target_summary": {
            "route_count": route_count,
            "fallback_positive_pairs": route_metadata.get("fallback_positive_pairs"),
            "unseen_dev_route_values": route_metadata.get("unseen_dev_route_values"),
        },
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
        },
        "completed_epochs": EPOCHS,
        "updates_per_epoch": int(math.ceil(len(train_rows) / float(BATCH_SIZE))),
        "selected_checkpoint": best_candidate.checkpoint,
        "selected_operating_point": best_candidate.operating_point,
        "selected_checkpoint_score": best_candidate.patient_macro_jaccard,
        "metrics": {"Train": selected_train, "Dev": selected_dev},
        "epoch_60_Dev": progress[-1]["dev_metrics"],
        "progress": progress,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "test_loaded": False,
    }
    state["status"] = "complete"
    _write_json(output / "progress.json", state)
    _write_json(output / "results.json", result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("route_aux", "route_fact"), required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--route-target-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
