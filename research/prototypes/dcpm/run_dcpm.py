#!/usr/bin/env python3
"""Run one frozen DCPM or SharedPrecedent Train/Dev experiment arm."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    from dcpm import (
        CLINICAL_LAYERS,
        DIM,
        FF_DIM,
        HEADS,
        MEDICATIONS,
        PEER_POOL_SIZE,
        DCPMModel,
        build_coarse_peer_pool,
        configure_numeric_policy,
        objective,
        pack_inputs,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dcpm import (
        CLINICAL_LAYERS,
        DIM,
        FF_DIM,
        HEADS,
        MEDICATIONS,
        PEER_POOL_SIZE,
        DCPMModel,
        build_coarse_peer_pool,
        configure_numeric_policy,
        objective,
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
SEED = 20260921
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
    medication_codes = tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))
    medication_ids = set(range(MEDICATIONS))
    if set(int(key) for key in medication.idx2word) != medication_ids:
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
        target = tuple(int(code) for code in row["_medications"])
        if any(code not in medication_ids for code in target):
            raise RuntimeError("current target medication ID is outside canonical 131")
        for event in row["history"]:
            if any(int(code) not in diagnosis_ids for code in event[0]):
                raise RuntimeError("history diagnosis ID is outside the frozen vocabulary")
            if any(int(code) not in procedure_ids for code in event[1]):
                raise RuntimeError("history procedure ID is outside the frozen vocabulary")
            if any(int(code) not in medication_ids for code in event[2]):
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
    if ddi.shape != (MEDICATIONS, MEDICATIONS):
        raise RuntimeError("DDI matrix does not match canonical 131 axis")
    if (
        not np.isfinite(ddi).all()
        or not np.isin(ddi, (0.0, 1.0)).all()
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
    ):
        raise RuntimeError("DDI matrix is not finite binary symmetric zero-diagonal")

    return len(diagnosis_ids), len(procedure_ids), medication_codes


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_profile(snapshot: Path, train_dev: Path) -> None:
    if not PROFILE_PATH.exists():
        raise RuntimeError("paper Dev profile JSON is missing")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError("profile ID mismatch")
    source_assets = profile["benchmark"]["source_assets"]
    for filename, record in source_assets.items():
        candidate = snapshot / filename
        if not candidate.exists():
            raise RuntimeError(f"required snapshot file {filename} is missing")
        if candidate.stat().st_size != record["bytes"] or _sha256(candidate) != record["sha256"]:
            raise RuntimeError(f"snapshot file {filename} failed checksum verification")
    split = profile["split"]
    for split_key, target_name in (("train", "train_targets.npy"), ("dev", "dev_targets.npy")):
        candidate = train_dev / target_name
        if not candidate.exists():
            raise RuntimeError(f"required target file {target_name} is missing")
        if _sha256(candidate) != split[split_key]["target_array_sha256"]:
            raise RuntimeError(f"target array {target_name} failed checksum verification")


def _scientific_config(variant: str, numeric_policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": PROFILE_ID,
        "variant": variant,
        "seed": SEED,
        "epochs": EPOCHS,
        "batch_size_visits": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "gradient_clip": GRADIENT_CLIP,
        "optimizer": "AdamW",
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "loss": "existing MICA BCE + 0.05 normalized DDI only",
        "ddi_weight": 0.05,
        "hidden_dim": DIM,
        "clinical_attention_blocks": CLINICAL_LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "dropout": 0.1,
        "peer_pool_size": PEER_POOL_SIZE,
        "medications": MEDICATIONS,
        "numeric_policy": dict(numeric_policy),
        "selection": "joint Dev patient-macro Jaccard over complete epochs with threshold grid",
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
    }


def _write_progress(output_dir: Path, state: Mapping[str, Any]) -> None:
    temp_path = output_dir / "progress.json.tmp"
    final_path = output_dir / "progress.json"
    temp_path.write_text(json.dumps(dict(state), indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(final_path)


def _evaluate_operating_point(
    rows: Sequence[Mapping[str, Any]],
    targets: np.ndarray,
    probs: np.ndarray,
    threshold: float,
    vocabulary: tuple[str, ...],
    ddi_pairs: frozenset[tuple[str, str]],
) -> dict[str, Any]:
    predictions: list[VisitPrediction] = []
    for row_idx, row in enumerate(rows):
        target_indices = np.flatnonzero(targets[row_idx] > 0.5)
        pred_indices = np.flatnonzero(probs[row_idx] >= threshold)
        target_codes = tuple(vocabulary[i] for i in target_indices)
        pred_codes = tuple(vocabulary[i] for i in pred_indices)
        scores = tuple(float(probs[row_idx, col]) for col in range(MEDICATIONS))
        predictions.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=target_codes,
                predicted_medications=pred_codes,
                medication_scores=scores,
            )
        )
    return evaluate(predictions, vocabulary=vocabulary, ddi_pairs=ddi_pairs)


def refresh_train_memory(
    model: DCPMModel,
    train_rows: Sequence[Mapping[str, Any]],
    dx: int,
    proc: int,
    device: torch.device,
    batch_size: int = 64,
) -> torch.Tensor:
    """Encode all Train visits to refresh target-free patient state h_j in memory."""
    model.eval()
    h_chunks: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, len(train_rows), batch_size):
            batch_slice = _model_rows(train_rows[start : start + batch_size])
            packed = {
                key: value.to(device) for key, value in pack_inputs(batch_slice, dx, proc).items()
            }
            h_chunks.append(model.encode_patient_state(packed))
    return torch.cat(h_chunks, dim=0)


def predict_dev_logits(
    model: DCPMModel,
    dev_rows: Sequence[Mapping[str, Any]],
    dev_peer_pool: np.ndarray,
    h_mem: torch.Tensor,
    y_mem: torch.Tensor,
    dx: int,
    proc: int,
    device: torch.device,
    batch_size: int = 64,
) -> np.ndarray:
    """Evaluate Dev logits using Train-only precedent memory."""
    model.eval()
    logits_chunks: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(dev_rows), batch_size):
            end = min(start + batch_size, len(dev_rows))
            batch_slice = _model_rows(dev_rows[start:end])
            packed = {
                key: value.to(device) for key, value in pack_inputs(batch_slice, dx, proc).items()
            }
            peer_idx = dev_peer_pool[start:end]
            peer_h = h_mem[peer_idx]
            peer_y = y_mem[peer_idx]
            logits = model(packed, peer_h, peer_y)
            logits_chunks.append(logits.detach().cpu().numpy())
    return np.concatenate(logits_chunks, axis=0)


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    if args.variant not in DCPMModel.VARIANTS:
        raise RuntimeError(f"variant must be one of {DCPMModel.VARIANTS}")
    source_root = Path(__file__).resolve().parents[3]
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    output = args.output_dir.resolve()

    if snapshot.name != SNAPSHOT_ID or train_dev_root.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot or Train/Dev root identity mismatch")
    if not snapshot.is_dir() or not train_dev_root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if source_root == output or source_root in output.parents:
        raise RuntimeError("output directory must be outside source checkout")
    output.mkdir(parents=True, exist_ok=True)
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

    dx, proc, vocabulary = _validate_data(
        records, voc, train_rows, dev_rows, train_targets, dev_targets, ddi
    )
    ddi_pairs = frozenset(
        tuple(sorted((vocabulary[int(left)], vocabulary[int(right)])))
        for left, right in zip(*np.triu(ddi, 1).nonzero())  # noqa: B905
    )

    numeric_policy = configure_numeric_policy()
    config = _scientific_config(args.variant, numeric_policy)

    device = torch.device(
        f"cuda:{args.gpu}"
        if args.gpu is not None and torch.cuda.is_available()
        else ("cuda" if torch.cuda.is_available() else "cpu")
    )

    # Build or load coarse peer pools
    peer_cache_dir = (
        args.peer_cache_dir.resolve() if args.peer_cache_dir else output.parent / "coarse_peer_pool"
    )
    peer_cache_dir.mkdir(parents=True, exist_ok=True)
    train_peer_file = peer_cache_dir / "train_peer_pool.npy"
    dev_peer_file = peer_cache_dir / "dev_peer_pool.npy"

    if train_peer_file.exists() and dev_peer_file.exists():
        print(f"Loading cached coarse peer pools from {peer_cache_dir}...", flush=True)
        train_peer_pool = np.load(train_peer_file)
        dev_peer_pool = np.load(dev_peer_file)
    else:
        print(
            f"Building coarse peer pools (L={PEER_POOL_SIZE}) from legal target-free clinical inputs...",
            flush=True,
        )
        t0 = time.time()
        train_peer_pool, dev_peer_pool = build_coarse_peer_pool(
            train_rows, dev_rows, dx, proc, MEDICATIONS, PEER_POOL_SIZE
        )
        print(
            f"Peer pools built in {time.time() - t0:.2f}s. Saving to {peer_cache_dir}...",
            flush=True,
        )
        np.save(train_peer_file, train_peer_pool)
        np.save(dev_peer_file, dev_peer_pool)

    # Verify peer pool properties
    if train_peer_pool.shape != (10489, PEER_POOL_SIZE) or dev_peer_pool.shape != (
        2130,
        PEER_POOL_SIZE,
    ):
        raise RuntimeError("peer pool shapes do not match expected dimensions")

    _seed_everything(SEED)
    model = DCPMModel(dx, proc, variant=args.variant, medication_count=MEDICATIONS).to(device)

    # Initialize prevalence bias
    train_prevalence = torch.from_numpy(train_targets.mean(axis=0)).to(device)
    model.initialize_prevalence(train_prevalence)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )

    ddi_tensor = torch.from_numpy(ddi).to(device)
    y_mem = torch.from_numpy(train_targets).to(device)
    train_peer_pool = torch.from_numpy(train_peer_pool).to(device)
    dev_peer_pool = torch.from_numpy(dev_peer_pool).to(device)

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
    start_time = time.time()

    print(
        f"Starting {EPOCHS}-epoch training for variant={args.variant} on {device} (seed={SEED})...",
        flush=True,
    )

    for epoch in range(1, EPOCHS + 1):
        epoch_t0 = time.time()

        # Step A: Refresh Train memory target-free representations h_j at start of epoch
        h_mem = refresh_train_memory(model, train_rows, dx, proc, device)

        # Step B: Train epoch
        model.train()
        epoch_rng = random.Random(SEED + epoch * 10007)
        indices_list = list(range(len(train_rows)))
        epoch_rng.shuffle(indices_list)

        loss_sum = 0.0
        bce_sum = 0.0
        ddi_loss_sum = 0.0
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

            batch_indices_tensor = torch.tensor(batch_indices, dtype=torch.long, device=device)
            batch_peer_idx = train_peer_pool[batch_indices_tensor]
            peer_h = h_mem[batch_peer_idx]
            peer_y = y_mem[batch_peer_idx]

            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_data, peer_h, peer_y)
            loss, bce, ddi_l = objective(logits, targets, ddi_tensor, MEDICATIONS)

            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite training loss at epoch {epoch}")

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()

            size = len(batch_indices)
            loss_sum += float(loss.item()) * size
            bce_sum += float(bce.item()) * size
            ddi_loss_sum += float(ddi_l.item()) * size
            example_count += size

        # Step C: Complete epoch Dev evaluation
        dev_logits = predict_dev_logits(
            model, dev_rows, dev_peer_pool, h_mem, y_mem, dx, proc, device
        )
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
            torch.save(best_state, output / "selected_checkpoint.pt")

        current_metrics = candidate_metric_map[best_checkpoint_cand.operating_point]
        elapsed = time.time() - start_time
        epoch_dur = time.time() - epoch_t0

        progress_state.update(
            {
                "completed_epochs": epoch,
                "selected_epoch": overall_best.checkpoint,
                "selected_operating_point": overall_best.operating_point,
                "selected_dev_jaccard": overall_best.patient_macro_jaccard,
                "latest_train_loss": loss_sum / example_count,
                "latest_checkpoint_jaccard": best_checkpoint_cand.patient_macro_jaccard,
                "latest_checkpoint_metrics": current_metrics,
                "elapsed_seconds": elapsed,
            }
        )
        _write_progress(output, progress_state)

        print(
            f"Epoch {epoch:02d}/{EPOCHS} [{epoch_dur:.1f}s] - Train Loss: {loss_sum / example_count:.4f} "
            f"(BCE {bce_sum / example_count:.4f}, DDI {ddi_loss_sum / example_count:.4f}) | "
            f"Dev Jaccard @ {best_checkpoint_cand.operating_point:.2f}: {best_checkpoint_cand.patient_macro_jaccard:.4f} | "
            f"Best: Ep {overall_best.checkpoint} @ {overall_best.operating_point:.2f} J={overall_best.patient_macro_jaccard:.4f}",
            flush=True,
        )

    # Complete 60-epoch evaluation
    final_selected = select_joint(
        all_candidates,
        operating_point_order=OPERATING_POINTS,
        native_default=NATIVE_DEFAULT,
    )
    selected_checkpoint_path = output / "selected_checkpoint.pt"
    model.load_state_dict(torch.load(selected_checkpoint_path, map_location=device))
    h_mem = refresh_train_memory(model, train_rows, dx, proc, device)
    selected_dev_logits = predict_dev_logits(
        model, dev_rows, dev_peer_pool, h_mem, y_mem, dx, proc, device
    )
    selected_dev_probs = 1.0 / (1.0 + np.exp(-np.asarray(selected_dev_logits, dtype=np.float64)))

    final_metrics = _evaluate_operating_point(
        dev_rows,
        dev_targets,
        selected_dev_probs,
        final_selected.operating_point,
        vocabulary,
        ddi_pairs,
    )

    result_data = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "seed": SEED,
        "variant": args.variant,
        "config": config,
        "status": "COMPLETED",
        "completed_epochs": EPOCHS,
        "selected_epoch": final_selected.checkpoint,
        "selected_operating_point": final_selected.operating_point,
        "patient_macro_jaccard": final_metrics["jaccard"],
        "patient_macro_f1": final_metrics["f1"],
        "patient_macro_prauc": final_metrics["prauc"],
        "ddi_rate": final_metrics["ddi_rate"],
        "average_medication_count": final_metrics["average_medication_count"],
        "target_average_medication_count": final_metrics["target_average_medication_count"],
        "all_metrics": final_metrics,
        "total_elapsed_seconds": time.time() - start_time,
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "test_accessed": False,
    }

    result_path = output / "result.json"
    result_path.write_text(json.dumps(result_data, indent=2, sort_keys=True), encoding="utf-8")
    progress_state["status"] = "COMPLETED"
    _write_progress(output, progress_state)

    print(f"\nCompleted {args.variant} 60-epoch run successfully!", flush=True)
    print(
        f"Selected Checkpoint: Epoch {final_selected.checkpoint}, Threshold {final_selected.operating_point}"
    )
    print(f"Dev Jaccard: {final_metrics['jaccard']:.6f}")
    print(f"Dev F1:      {final_metrics['f1']:.6f}")
    print(f"Dev PRAUC:   {final_metrics['prauc']:.6f}")
    print(f"Dev DDI:     {final_metrics['ddi_rate']:.6f}")
    print(f"Dev AvgMed:  {final_metrics['average_medication_count']:.4f}")

    return result_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DCPM or SharedPrecedent experiment")
    parser.add_argument("--variant", choices=DCPMModel.VARIANTS, required=True)
    parser.add_argument("--gpu", type=int, default=None)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path("/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23"),
    )
    parser.add_argument(
        "--train-dev-root",
        type=Path,
        default=Path("/root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a"),
    )
    parser.add_argument("--peer-cache-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", type=str, default="")
    args = parser.parse_args()

    if not args.source_revision:
        args.source_revision = _git_revision(REPO_ROOT)

    run_experiment(args)


if __name__ == "__main__":
    main()
