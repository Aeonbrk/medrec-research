#!/usr/bin/env python3
"""Run the one-seed FutureGraphKD Train/Gate01-Dev architecture screen on 319."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

try:
    from hyperedit import backbone_sets, build_visit_contexts, evaluate_sets, set_change_summary
except ModuleNotFoundError:  # Running directly from the prototype directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hyperedit"))
    from hyperedit import backbone_sets, build_visit_contexts, evaluate_sets, set_change_summary

from futuregraphkd import (
    CANDIDATE_COUNT,
    DEFAULT_CODE_HASH_WIDTH,
    DEFAULT_GRAPH_LAYERS,
    DEFAULT_HIDDEN_DIM,
    DEFAULT_HIDDEN_WEIGHT,
    DEFAULT_KD_WEIGHT,
    FutureGraphKDModel,
    build_relation_features,
    build_visit_features,
    future_graph_kd_loss,
)

GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_SOURCE_REVISION = "135929bec17905ad12fbac3f03a4b2430b7fcff7"
DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 6
DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-4


def gate01_dev(patient_id: int) -> bool:
    """Return the existing Gate01-Dev half split for a zero-based patient id."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_id}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _target_sets(target_matrix: np.ndarray) -> tuple[frozenset[int], ...]:
    return tuple(
        frozenset(int(index) for index in np.flatnonzero(row > 0.5)) for row in target_matrix
    )


def _assert_alignment(contexts: tuple[Any, ...], targets: np.ndarray) -> None:
    if len(contexts) != targets.shape[0]:
        raise RuntimeError("record order does not align with the frozen MoleRec target array")
    for row, context in enumerate(contexts):
        expected = set(int(value) for value in context.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"target mismatch at visit row {row}")


def _batch_tensor(array: np.ndarray, rows: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(array[rows])).to(device=device)


def _train(
    student: FutureGraphKDModel,
    teacher: FutureGraphKDModel,
    embeddings: np.ndarray,
    scores: np.ndarray,
    context_features: np.ndarray,
    future_features: np.ndarray,
    supported: np.ndarray,
    targets: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    kd_weight: float,
    hidden_weight: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch size must be positive")
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(
        list(student.parameters()) + list(teacher.parameters()),
        lr=learning_rate,
        weight_decay=weight_decay,
    )
    student.train()
    teacher.train()
    last: dict[str, float] = {}
    for _ in range(epochs):
        order = rng.permutation(len(targets))
        totals = {
            "student_bce": 0.0,
            "teacher_bce": 0.0,
            "logit_kd": 0.0,
            "hidden_mse": 0.0,
            "total": 0.0,
        }
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            embedding_batch = _batch_tensor(embeddings, rows, device)
            score_batch = _batch_tensor(scores, rows, device)
            context_batch = _batch_tensor(context_features, rows, device)
            future_batch = _batch_tensor(future_features, rows, device)
            target_batch = _batch_tensor(targets, rows, device)
            support_batch = torch.from_numpy(supported[rows]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            student_output = student(
                embedding_batch,
                score_batch,
                context_batch,
                future_batch,
            )
            teacher_output = teacher(
                embedding_batch,
                score_batch,
                context_batch,
                future_batch,
            )
            loss, detail = future_graph_kd_loss(
                student_output,
                teacher_output,
                target_batch,
                support_batch,
                kd_weight=kd_weight,
                hidden_weight=hidden_weight,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(student.parameters()) + list(teacher.parameters()), max_norm=5.0
            )
            optimizer.step()
            for key in totals:
                totals[key] += detail[key]
            batches += 1
        last = {key: value / batches for key, value in totals.items()}
    return last


def _predict(
    model: FutureGraphKDModel,
    embeddings: np.ndarray,
    scores: np.ndarray,
    context_features: np.ndarray,
    future_features: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    logits_parts: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(scores), batch_size):
            stop = min(start + batch_size, len(scores))
            rows = np.arange(start, stop, dtype=np.int64)
            output = model(
                _batch_tensor(embeddings, rows, device),
                _batch_tensor(scores, rows, device),
                _batch_tensor(context_features, rows, device),
                _batch_tensor(future_features, rows, device),
            )
            logits_parts.append(output.logits.cpu().numpy())
    return np.concatenate(logits_parts, axis=0)


def _metrics(
    targets: np.ndarray,
    predictions: tuple[frozenset[int], ...],
    scores: np.ndarray,
    ddi: np.ndarray,
) -> dict[str, float]:
    return evaluate_sets(_target_sets(targets), predictions, scores, ddi)


def _load_graph_refine_metrics(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        metrics = payload["diagnostic_same_k"]["GraphRefine-SameK"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("GraphRefine-SameK aggregate result is missing") from error
    required = {"jaccard", "f1", "prauc", "ddi", "mean_medication_count"}
    if not required.issubset(metrics):
        raise RuntimeError("GraphRefine-SameK aggregate result is incomplete")
    return {key: float(metrics[key]) for key in required}


def _load_optional_metrics(path: Path | None) -> dict[str, float] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("GraphRefine-SameK")
    if not isinstance(metrics, dict):
        raise RuntimeError("supported-subset GraphRefine result is missing GraphRefine-SameK")
    required = {"jaccard", "f1", "prauc", "ddi", "mean_medication_count"}
    if not required.issubset(metrics):
        raise RuntimeError("supported-subset GraphRefine aggregate result is incomplete")
    return {key: float(metrics[key]) for key in required}


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    ehr = np.asarray(dill.load((snapshot / "ehr_adj_final.pkl").open("rb")), dtype=np.float32)
    if ddi.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("the canonical DDI matrix is not 131 by 131")
    if ehr.shape != ddi.shape:
        raise RuntimeError("the canonical EHR co-prescription matrix is not 131 by 131")

    split_point = int(len(records) * 2 / 3)
    train_patient_indices = tuple(range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
    train_contexts = build_visit_contexts(records, train_patient_indices)
    dev_contexts = build_visit_contexts(records, dev_patient_indices)
    train_scores = _load_array(train_dev_root, "train_scores.npy")
    train_embeddings = _load_array(train_dev_root, "train_embeddings.npy")
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_scores = _load_array(train_dev_root, "dev_scores.npy")
    dev_embeddings = _load_array(train_dev_root, "dev_embeddings.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    for name, value in (
        ("train_scores", train_scores),
        ("train_targets", train_targets),
        ("dev_scores", dev_scores),
        ("dev_targets", dev_targets),
    ):
        if value.ndim != 2 or value.shape[1] != CANDIDATE_COUNT:
            raise RuntimeError(f"{name} does not have the frozen [visits, 131] shape")
    for name, value, reference in (
        ("train_embeddings", train_embeddings, train_scores),
        ("dev_embeddings", dev_embeddings, dev_scores),
    ):
        if value.ndim != 3 or value.shape[:2] != reference.shape:
            raise RuntimeError(f"{name} is not aligned with its frozen score matrix")
    _assert_alignment(train_contexts, train_targets)
    _assert_alignment(dev_contexts, dev_targets)

    train_context_features, train_future_features, train_supported, train_keys = (
        build_visit_features(
            records,
            train_patient_indices,
            code_hash_width=args.code_hash_width,
        )
    )
    dev_context_features, dev_future_features, dev_supported, dev_keys = build_visit_features(
        records,
        dev_patient_indices,
        code_hash_width=args.code_hash_width,
    )
    if (
        train_context_features.shape[0] != train_scores.shape[0]
        or dev_context_features.shape[0] != dev_scores.shape[0]
    ):
        raise RuntimeError("current/future feature rows are not aligned with MoleRec arrays")

    relation_features = build_relation_features(ehr, ddi)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_kwargs = {
        "embedding_dim": int(train_embeddings.shape[-1]),
        "context_dim": int(train_context_features.shape[-1]),
        "future_dim": int(train_future_features.shape[-1]),
        "relation_features": relation_features,
        "hidden_dim": args.hidden_dim,
    }
    student = FutureGraphKDModel(**model_kwargs, use_future=False).to(device)
    teacher = FutureGraphKDModel(**model_kwargs, use_future=True).to(device)
    train_detail = _train(
        student,
        teacher,
        train_embeddings,
        train_scores,
        train_context_features,
        train_future_features,
        train_supported,
        train_targets,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        kd_weight=args.kd_weight,
        hidden_weight=args.hidden_weight,
        device=device,
    )
    student_logits = _predict(
        student,
        dev_embeddings,
        dev_scores,
        dev_context_features,
        dev_future_features,
        batch_size=args.batch_size,
        device=device,
    )
    teacher_logits = _predict(
        teacher,
        dev_embeddings,
        dev_scores,
        dev_context_features,
        dev_future_features,
        batch_size=args.batch_size,
        device=device,
    )

    base_predictions = backbone_sets(dev_scores)
    student_predictions = tuple(
        frozenset(sorted(np.argsort(-row, kind="stable")[: len(base)]))
        for row, base in zip(student_logits, base_predictions)  # noqa: B905
    )
    teacher_predictions = tuple(
        frozenset(sorted(np.argsort(-row, kind="stable")[: len(base)]))
        for row, base in zip(teacher_logits, base_predictions)  # noqa: B905
    )
    exact_cardinality_preserved = tuple(map(len, base_predictions)) == tuple(
        map(len, student_predictions)
    )
    if not exact_cardinality_preserved:
        raise RuntimeError("Student-SameK decoding changed a frozen MoleRec cardinality")
    graph_refine_metrics = _load_graph_refine_metrics(args.graph_refine_result)
    graph_supported_metrics = _load_optional_metrics(args.graph_refine_supported_result)
    supported_rows = np.flatnonzero(dev_supported)
    if len(supported_rows) == 0:
        raise RuntimeError("Gate01-Dev contains no visits with an immediate next visit")
    supported_targets = dev_targets[supported_rows]
    supported_student_predictions = tuple(student_predictions[index] for index in supported_rows)
    supported_teacher_predictions = tuple(teacher_predictions[index] for index in supported_rows)
    supported_student_metrics = _metrics(
        supported_targets,
        supported_student_predictions,
        student_logits[supported_rows],
        ddi,
    )
    supported_teacher_metrics = _metrics(
        supported_targets,
        supported_teacher_predictions,
        teacher_logits[supported_rows],
        ddi,
    )
    if graph_supported_metrics is None:
        graph_supported_metrics = {
            **graph_refine_metrics,
            "scope_note": "full-Dev aggregate; supported-subset GraphRefine predictions were not persisted",
        }
    supported_jaccard_advantage = (
        supported_teacher_metrics["jaccard"] - supported_student_metrics["jaccard"]
    )
    supported_prauc_advantage = (
        supported_teacher_metrics["prauc"] - supported_student_metrics["prauc"]
    )
    teacher_material = supported_jaccard_advantage >= 0.005 or (
        supported_prauc_advantage >= 0.005 and supported_jaccard_advantage >= -0.002
    )
    student_metrics = _metrics(dev_targets, student_predictions, student_logits, ddi)
    change = set_change_summary(base_predictions, student_predictions)
    student_survives = student_metrics["jaccard"] >= 0.539 or (
        student_metrics["jaccard"] >= 0.536 and student_metrics["ddi"] <= 0.068
    )
    if not teacher_material:
        decision = "STOP_NO_FUTURE_STATE_SIGNAL"
    elif not student_survives:
        decision = "STOP_PRIVILEGED_TRANSFER_FAILURE"
    else:
        decision = "SURVIVE_FUTUREGRAPHKD"
    return {
        "working_name": "FutureGraphKD-v0",
        "source_revision": args.source_revision,
        "device": str(device),
        "seed": args.seed,
        "config": {
            "embedding_dim": int(train_embeddings.shape[-1]),
            "code_hash_width": args.code_hash_width,
            "hidden_dim": args.hidden_dim,
            "graph_layers": DEFAULT_GRAPH_LAYERS,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "kd_weight": args.kd_weight,
            "hidden_alignment_weight": args.hidden_weight,
        },
        "split": {
            "train_patients": split_point,
            "train_visits": len(train_contexts),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_contexts),
            "held_out_resources_read": False,
        },
        "architecture": {
            "student_inputs": "current and historical diagnosis/procedure codes, historical medications, frozen MoleRec score and per-visit medication embedding, EHR/DDI relations",
            "teacher_extra_input": "immediate next recorded visit diagnoses/procedures only",
            "interaction": "shared-width two-layer patient-conditioned medication message passing",
            "distillation": "supported-visit teacher soft-logit BCE plus final hidden-state MSE",
            "decoder": "MoleRec SameK diagnostic; no cardinality model or sequential editor",
        },
        "train_privileged_support": {
            "visits_with_immediate_next": int(train_supported.sum()),
            "total_visits": len(train_supported),
            "fraction": float(train_supported.mean()),
            "patients_with_support": len(
                {
                    patient
                    for (patient, _), has_support in zip(train_keys, train_supported)  # noqa: B905
                    if has_support
                }
            ),
        },
        "dev_privileged_support": {
            "visits_with_immediate_next": int(dev_supported.sum()),
            "total_visits": len(dev_supported),
            "fraction": float(dev_supported.mean()),
            "patients_with_support": len(
                {
                    patient
                    for (patient, _), has_support in zip(dev_keys, dev_supported)  # noqa: B905
                    if has_support
                }
            ),
        },
        "metrics": {
            "MoleRec": _metrics(dev_targets, base_predictions, dev_scores, ddi),
            "GraphRefine-SameK": graph_refine_metrics,
            "FutureGraphKD Student-SameK": student_metrics,
        },
        "exact_molerec_cardinality_preserved": exact_cardinality_preserved,
        "supported_dev_metrics": {
            "GraphRefine-SameK": graph_supported_metrics,
            "FutureGraphKD Student-SameK": supported_student_metrics,
            "FutureGraphKD Teacher-SameK": supported_teacher_metrics,
            "teacher_minus_student_jaccard": supported_jaccard_advantage,
            "teacher_minus_student_prauc": supported_prauc_advantage,
            "supported_visits": len(supported_rows),
            "supported_patients": len({dev_keys[index][0] for index in supported_rows}),
        },
        "set_change_fraction": change["changed_fraction"],
        "mean_symmetric_difference": change["mean_symmetric_difference"],
        "last_train_loss": train_detail,
        "teacher_material_signal": teacher_material,
        "student_survival_signal": student_survives,
        "observed_effect": "strong" if decision == "SURVIVE_FUTUREGRAPHKD" else "weak",
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--graph-refine-result", type=Path, required=True)
    parser.add_argument("--graph-refine-supported-result", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--code-hash-width", type=int, default=DEFAULT_CODE_HASH_WIDTH)
    parser.add_argument("--hidden-dim", type=int, default=DEFAULT_HIDDEN_DIM)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--kd-weight", type=float, default=DEFAULT_KD_WEIGHT)
    parser.add_argument("--hidden-weight", type=float, default=DEFAULT_HIDDEN_WEIGHT)
    args = parser.parse_args()
    result = run(args)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
