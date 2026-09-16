#!/usr/bin/env python3
# ruff: noqa: UP006,UP035,UP045
"""Run the frozen Stage -1F MICA Train/Dev replication arms.

The runner intentionally keeps the historical MICA computation unchanged
apart from its optional medication-axis length.  Real data and all
patient-aligned artifacts must remain outside the repository on 319.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import dill
import numpy as np
import torch

MICA_DIR = Path(__file__).resolve().parents[1] / "mica"
sys.path.insert(0, str(MICA_DIR))

from mica import (  # noqa: E402
    DIM,
    FF_DIM,
    HEADS,
    LAYERS,
    MEDICATIONS,
    MICA,
    THRESHOLD,
    configure_numeric_policy,
    objective,
    pack_inputs,
)
from run_mica import (  # noqa: E402
    _align,
    _load,
    _require_clean_source,
    _rows,
    _validate_vocab,
)

SEED = 20260914
BATCH_SIZE = 16
LR = 1e-4
WEIGHT_DECAY = 1e-4
DDI_WEIGHT = 0.05
GRADIENT_CLIP = 5.0
MIMIC_III_EPOCHS = 60
MIMIC_IV_UPDATES = 39_360
MIMIC_IV_EVAL_EVERY = 3_280
MIMIC_III_SNAPSHOT = "molerec-table1-c721-www23"
MIMIC_III_TRAIN_DEV = "gate01-train-dev-5752596a-20260913a"
MIMIC_IV_ROOT = "mimiciv-medrec-stage-1e-private-e87411be"
MIMIC_IV_EXPECTED = {"train_examples": 308_824, "dev_examples": 76_529}
IV_INDEX_SCHEMA = 1
PROGRESS_SCHEMA = 1
TERMINAL_IMPROVEMENT_THRESHOLD = 0.002
LOGIT_THRESHOLD = float(np.log(THRESHOLD / (1.0 - THRESHOLD)))


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    configure_numeric_policy()


def _gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"
    )
    os.replace(str(temporary), str(path))


def _average_precision(target: Iterable[int], scores: Sequence[float]) -> float:
    target_set = {int(item) for item in target}
    if not target_set:
        return 0.0
    ranked = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_set:
            found += 1
            total += found / rank
    return total / len(target_set)


def surface_metrics(targets: np.ndarray, logits: np.ndarray, ddi: np.ndarray) -> Dict[str, float]:
    """Match the visit-macro NeedCover surface for an arbitrary med count."""

    values = np.asarray(logits, dtype=np.float32)
    target_values = np.asarray(targets, dtype=np.float32)
    ddi_values = np.asarray(ddi, dtype=np.float32)
    if values.ndim != 2 or target_values.shape != values.shape:
        raise RuntimeError("targets and logits are not visit-aligned")
    if ddi_values.shape != (values.shape[1], values.shape[1]):
        raise RuntimeError("DDI matrix shape does not match medication axis")
    if not np.isfinite(values).all() or not np.isfinite(target_values).all():
        raise RuntimeError("non-finite evaluation values")
    jaccard = precision = recall = f1 = prauc = 0.0
    ddi_count = pair_count = 0
    medication_counts: List[int] = []
    for target_row, score_row in zip(target_values, values):  # noqa: B905 (Python 3.8 remote)
        target = set(int(index) for index in np.flatnonzero(target_row > 0.5))
        prediction = set(int(index) for index in np.flatnonzero(score_row >= LOGIT_THRESHOLD))
        intersection = len(target & prediction)
        union = len(target | prediction)
        visit_precision = (
            1.0
            if not prediction and not target
            else intersection / len(prediction)
            if prediction
            else 0.0
        )
        visit_recall = (
            1.0 if not prediction and not target else intersection / len(target) if target else 0.0
        )
        visit_f1 = (
            0.0
            if visit_precision + visit_recall == 0.0
            else 2.0 * visit_precision * visit_recall / (visit_precision + visit_recall)
        )
        jaccard += 1.0 if not union else intersection / union
        precision += visit_precision
        recall += visit_recall
        f1 += visit_f1
        prauc += _average_precision(target, score_row)
        medication_counts.append(len(prediction))
        ordered = sorted(prediction)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi_values[left, right]))
    count = len(target_values)
    if count <= 0:
        raise RuntimeError("cannot evaluate an empty visit collection")
    stable_nll = (
        np.maximum(values, 0.0) - values * target_values + np.logaddexp(0.0, -np.abs(values))
    )
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "precision": precision / count,
        "recall": recall / count,
        "ddi_rate": 0.0 if pair_count == 0 else ddi_count / pair_count,
        "mean_medication_count": float(sum(medication_counts) / count),
        "std_medication_count": float(np.asarray(medication_counts, dtype=np.float32).std()),
        "nll": float(stable_nll.mean()),
        "visit_count": float(count),
    }


class InMemoryDataset:
    """Small canonical MIMIC-III rows plus their aligned labels."""

    def __init__(self, rows: Sequence[Mapping[str, Any]], targets: np.ndarray) -> None:
        self.rows = list(rows)
        self.targets = np.asarray(targets, dtype=np.float32)

    def __len__(self) -> int:
        return len(self.rows)

    def get_batch(self, indices: Sequence[int]) -> Tuple[List[Mapping[str, Any]], np.ndarray]:
        values = [self.rows[int(index)] for index in indices]
        return values, self.targets[np.asarray(indices, dtype=np.int64)]


def _validate_iv_object(
    example: Mapping[str, Any],
    dx_vocab: Mapping[str, int],
    proc_vocab: Mapping[str, int],
    med_vocab: Mapping[str, int],
) -> Tuple[Dict[str, Any], np.ndarray]:
    """Parse one private JSONL record and fail closed on leakage or OOV labels."""

    required = {
        "schema_version",
        "subject_id",
        "current_visit_order",
        "input",
        "target",
        "provenance",
    }
    if set(example) != required or int(example["schema_version"]) != 1:
        raise RuntimeError("MIMIC-IV example schema mismatch")
    input_part = example["input"]
    if set(input_part) != {"diagnoses", "procedures", "history"}:
        raise RuntimeError("MIMIC-IV input contains an unexpected medication-bearing field")
    target_part = example["target"]
    if set(target_part) != {"medications", "known_medications", "oov_medications"}:
        raise RuntimeError("MIMIC-IV target schema mismatch")
    provenance = example["provenance"]
    current_order = int(example["current_visit_order"])
    current_hadm = str(provenance["current_hadm_id"])
    history_ids = [str(value) for value in provenance["history_hadm_ids"]]
    history = input_part["history"]
    if len(history_ids) != len(history) or current_hadm in history_ids:
        raise RuntimeError("current admission appears in MIMIC-IV history")

    def project_codes(values: Iterable[str], vocab: Mapping[str, int]) -> List[int]:
        return sorted({int(vocab.get(str(value), 0)) for value in values})

    history_rows: List[Tuple[List[int], List[int], List[int]]] = []
    for entry, history_hadm in zip(history, history_ids):  # noqa: B905 (Python 3.8 remote)
        if str(entry["hadm_id"]) != history_hadm:
            raise RuntimeError("history provenance mismatch")
        visit_order = int(entry["visit_order"])
        if visit_order >= current_order or str(entry["hadm_id"]) == current_hadm:
            raise RuntimeError("strict previous-visit history invariant failed")
        history_meds: List[int] = []
        for token in entry["medications"]:
            if str(token) not in med_vocab:
                raise RuntimeError("history medication is outside the frozen Train vocabulary")
            history_meds.append(int(med_vocab[str(token)]))
        history_rows.append(
            (
                project_codes(entry["diagnoses"], dx_vocab),
                project_codes(entry["procedures"], proc_vocab),
                sorted(set(history_meds)),
            )
        )

    target_tokens = [str(value) for value in target_part["medications"]]
    known_tokens = [str(value) for value in target_part["known_medications"]]
    oov_tokens = [str(value) for value in target_part["oov_medications"]]
    if oov_tokens or set(target_tokens) != set(known_tokens):
        raise RuntimeError("MIMIC-IV target contains an OOV medication")
    target_indices = sorted({int(med_vocab[token]) for token in known_tokens})
    target = np.zeros(len(med_vocab), dtype=np.float32)
    target[target_indices] = 1.0
    row = {
        "diagnoses": project_codes(input_part["diagnoses"], dx_vocab),
        "procedures": project_codes(input_part["procedures"], proc_vocab),
        "history": history_rows,
    }
    return row, target


class JsonlDataset:
    """Random-access private JSONL dataset backed by a prebuilt offset index."""

    def __init__(
        self,
        path: Path,
        index_path: Path,
        dx_vocab: Mapping[str, int],
        proc_vocab: Mapping[str, int],
        med_vocab: Mapping[str, int],
    ) -> None:
        self.path = path
        self.offsets = np.asarray(np.load(str(index_path), mmap_mode="r"), dtype=np.int64)
        self.dx_vocab = dx_vocab
        self.proc_vocab = proc_vocab
        self.med_vocab = med_vocab
        self.handle = path.open("rb")

    def __len__(self) -> int:
        return int(self.offsets.shape[0])

    def get_batch(self, indices: Sequence[int]) -> Tuple[List[Mapping[str, Any]], np.ndarray]:
        rows: List[Mapping[str, Any]] = []
        targets = np.zeros((len(indices), len(self.med_vocab)), dtype=np.float32)
        for output_index, index in enumerate(indices):
            self.handle.seek(int(self.offsets[int(index)]))
            line = self.handle.readline()
            if not line:
                raise RuntimeError("MIMIC-IV JSONL offset points past EOF")
            try:
                example = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError("invalid MIMIC-IV JSONL record") from exc
            row, target = _validate_iv_object(
                example, self.dx_vocab, self.proc_vocab, self.med_vocab
            )
            rows.append(row)
            targets[output_index] = target
        return rows, targets

    def close(self) -> None:
        self.handle.close()


def _build_iv_index(
    path: Path,
    index_path: Path,
    manifest_path: Path,
    dx_vocab: Mapping[str, int],
    proc_vocab: Mapping[str, int],
    med_vocab: Mapping[str, int],
) -> Dict[str, Any]:
    """Build private offsets and Train/Dev aggregate target metadata once."""

    offsets: List[int] = []
    target_sum = np.zeros(len(med_vocab), dtype=np.uint64)
    cardinality: Counter[str] = Counter()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            try:
                example = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError("invalid MIMIC-IV JSONL record while indexing") from exc
            _row, target = _validate_iv_object(example, dx_vocab, proc_vocab, med_vocab)
            offsets.append(offset)
            target_sum += target.astype(np.uint64)
            cardinality[str(int(target.sum()))] += 1
            digest.update(_canonical_json(example))
    if not offsets:
        raise RuntimeError("MIMIC-IV JSONL contains no eligible examples")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_name(index_path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, np.asarray(offsets, dtype=np.int64), allow_pickle=False)
    os.replace(str(temporary), str(index_path))
    metadata = {
        "schema_version": IV_INDEX_SCHEMA,
        "filename": path.name,
        "line_count": len(offsets),
        "serialization_sha256": digest.hexdigest(),
        "target_sum": [int(value) for value in target_sum],
        "target_cardinality_histogram": dict(
            sorted(cardinality.items(), key=lambda item: int(item[0]))
        ),
    }
    _write_json(manifest_path, metadata)
    return metadata


def _load_iv_vocab(root: Path) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int], np.ndarray]:
    try:
        vocabularies = json.loads((root / "vocabularies.private.json").read_text(encoding="utf-8"))
        ddi_payload = json.loads((root / "ddi_matrix.private.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "cannot load the frozen private MIMIC-IV vocabulary/DDI artifacts"
        ) from exc
    dx_vocab = {str(key): int(value) for key, value in vocabularies["diagnosis"].items()}
    proc_vocab = {str(key): int(value) for key, value in vocabularies["procedure"].items()}
    med_vocab = {str(key): int(value) for key, value in vocabularies["medication"].items()}
    if dx_vocab.get("<UNK>") != 0 or proc_vocab.get("<UNK>") != 0:
        raise RuntimeError("MIMIC-IV diagnosis/procedure UNK IDs are not zero")
    if set(med_vocab.values()) != set(range(len(med_vocab))):
        raise RuntimeError("MIMIC-IV medication vocabulary IDs are not contiguous")
    ddi = np.asarray(ddi_payload["matrix"], dtype=np.float32)
    if ddi.shape != (len(med_vocab), len(med_vocab)):
        raise RuntimeError("MIMIC-IV DDI matrix does not match the medication vocabulary")
    if not np.isfinite(ddi).all() or not np.isin(ddi, (0.0, 1.0)).all():
        raise RuntimeError("MIMIC-IV DDI matrix is not finite binary")
    if not np.array_equal(ddi, ddi.T) or np.any(np.diag(ddi) != 0):
        raise RuntimeError("MIMIC-IV DDI matrix is not symmetric zero-diagonal")
    if ddi_payload.get("vocabulary") != med_vocab:
        raise RuntimeError("MIMIC-IV DDI vocabulary identity mismatch")
    return dx_vocab, proc_vocab, med_vocab, ddi


def prepare_iv_indexes(root: Path, index_dir: Path) -> Dict[str, Any]:
    if root.name != MIMIC_IV_ROOT:
        raise RuntimeError("MIMIC-IV private root identity does not match Stage -1E")
    dx_vocab, proc_vocab, med_vocab, _ddi = _load_iv_vocab(root)
    index_dir.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for role in ("train", "dev"):
        path = root / (role + "_examples.private.jsonl")
        if not path.is_file():
            raise RuntimeError("missing MIMIC-IV Train/Dev JSONL: " + str(path))
        metadata[role] = _build_iv_index(
            path,
            index_dir / (role + ".offsets.npy"),
            index_dir / (role + ".index.json"),
            dx_vocab,
            proc_vocab,
            med_vocab,
        )
    if metadata["train"]["line_count"] != MIMIC_IV_EXPECTED["train_examples"]:
        raise RuntimeError("MIMIC-IV Train example count does not match frozen Stage -1E")
    if metadata["dev"]["line_count"] != MIMIC_IV_EXPECTED["dev_examples"]:
        raise RuntimeError("MIMIC-IV Dev example count does not match frozen Stage -1E")
    result = {
        "schema_version": IV_INDEX_SCHEMA,
        "benchmark_root": root.name,
        "medication_vocab_size": len(med_vocab),
        "diagnosis_vocab_size": len(dx_vocab),
        "procedure_vocab_size": len(proc_vocab),
        "roles": metadata,
        "test_loaded": False,
    }
    _write_json(index_dir / "index-manifest.json", result)
    return result


def _load_mimic_iii(
    snapshot: Path, train_dev: Path
) -> Tuple[InMemoryDataset, InMemoryDataset, np.ndarray, int, int, Dict[str, int]]:
    if snapshot.name != MIMIC_III_SNAPSHOT or train_dev.name != MIMIC_III_TRAIN_DEV:
        raise RuntimeError("MIMIC-III roots do not match the canonical MICA contract")
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(index for index in range(split, len(records)) if _gate01_dev(index))
    if (len(records), len(train_patients), len(dev_patients)) != (6350, 4233, 1004):
        raise RuntimeError("canonical MIMIC-III patient split counts changed")
    dx, proc = _validate_vocab(records, voc, ddi, (*train_patients, *dev_patients))
    train_rows = _rows(records, train_patients)
    dev_rows = _rows(records, dev_patients)
    train_targets = _load(train_dev, "train_targets.npy")
    dev_targets = _load(train_dev, "dev_targets.npy")
    _align(train_rows, train_targets, "MIMIC-III Train")
    _align(dev_rows, dev_targets, "MIMIC-III Dev")
    if (len(train_rows), len(dev_rows)) != (10_489, 2_130):
        raise RuntimeError("canonical MIMIC-III visit counts changed")
    for row in train_rows + dev_rows:
        row.pop("_medications", None)
    split_info = {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train_rows),
        "dev_visits": len(dev_rows),
    }
    return (
        InMemoryDataset(train_rows, train_targets),
        InMemoryDataset(dev_rows, dev_targets),
        ddi,
        dx,
        proc,
        split_info,
    )


def _load_mimic_iv(
    root: Path, index_dir: Path
) -> Tuple[JsonlDataset, JsonlDataset, np.ndarray, int, int, Dict[str, int]]:
    if root.name != MIMIC_IV_ROOT:
        raise RuntimeError("MIMIC-IV private root identity does not match Stage -1E")
    dx_vocab, proc_vocab, med_vocab, ddi = _load_iv_vocab(root)
    train_index = index_dir / "train.offsets.npy"
    dev_index = index_dir / "dev.offsets.npy"
    if not train_index.is_file() or not dev_index.is_file():
        raise RuntimeError("MIMIC-IV private JSONL indexes are missing; prepare them first")
    train = JsonlDataset(
        root / "train_examples.private.jsonl", train_index, dx_vocab, proc_vocab, med_vocab
    )
    dev = JsonlDataset(
        root / "dev_examples.private.jsonl", dev_index, dx_vocab, proc_vocab, med_vocab
    )
    if (
        len(train) != MIMIC_IV_EXPECTED["train_examples"]
        or len(dev) != MIMIC_IV_EXPECTED["dev_examples"]
    ):
        raise RuntimeError("MIMIC-IV indexed example counts changed")
    index_manifest_path = index_dir / "index-manifest.json"
    if not index_manifest_path.is_file():
        raise RuntimeError("MIMIC-IV index manifest is missing")
    try:
        public_manifest = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "benchmarks"
                / "mimiciv-medrec"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        patient_counts = public_manifest["split"]["patient_counts"]
        if public_manifest["benchmark_id"] != "mimiciv-visit-medrec-stage-minus-1e":
            raise ValueError("benchmark identity mismatch")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("MIMIC-IV public manifest cannot be loaded") from exc
    split_info = {
        "train_patients": int(patient_counts["train"]),
        "dev_patients": int(patient_counts["dev"]),
        "train_visits": len(train),
        "dev_visits": len(dev),
        "train_examples": len(train),
        "dev_examples": len(dev),
        "medication_vocab_size": len(med_vocab),
        "diagnosis_vocab_size": len(dx_vocab),
        "procedure_vocab_size": len(proc_vocab),
    }
    return train, dev, ddi, len(dx_vocab), len(proc_vocab), split_info


def _predict(
    model: torch.nn.Module,
    dataset: Any,
    device: torch.device,
    dx_count: int,
    proc_count: int,
    medication_count: int,
) -> Tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_chunks: List[np.ndarray] = []
    target_chunks: List[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(dataset), BATCH_SIZE):
            indices = list(range(start, min(start + BATCH_SIZE, len(dataset))))
            rows, targets = dataset.get_batch(indices)
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(rows, dx_count, proc_count).items()
            }
            output = model(batch).detach().cpu().numpy()
            logits_chunks.append(output)
            target_chunks.append(targets)
    return np.concatenate(logits_chunks, axis=0), np.concatenate(target_chunks, axis=0)


def _config(dataset: str, variant: str, medication_count: int) -> Dict[str, Any]:
    return {
        "stage": "STAGE -1F",
        "dataset": dataset,
        "variant": variant,
        "medications": medication_count,
        "hidden_dim": DIM,
        "clinical_attention_blocks": LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LR,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "decoder": "sigmoid probability >= 0.35",
        "decoder_threshold": THRESHOLD,
        "loss": "BCE + 0.05 * normalized DDI penalty",
        "ddi_weight": DDI_WEIGHT,
        "mimic_iii_epochs": MIMIC_III_EPOCHS if dataset == "mimic_iii" else None,
        "mimic_iv_update_cap": MIMIC_IV_UPDATES if dataset == "mimic_iv" else None,
        "mimic_iv_eval_every_updates": MIMIC_IV_EVAL_EVERY if dataset == "mimic_iv" else None,
    }


def _write_progress(output: Path, state: Mapping[str, Any]) -> None:
    _write_json(output / "progress.json", state)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    _require_clean_source(args.source_revision)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MICA replication")
    if args.dataset == "mimic_iii":
        if args.snapshot_root is None or args.train_dev_root is None:
            raise RuntimeError("MIMIC-III requires --snapshot-root and --train-dev-root")
        train, dev, ddi, dx_count, proc_count, split_info = _load_mimic_iii(
            args.snapshot_root.resolve(), args.train_dev_root.resolve()
        )
        medication_count = MEDICATIONS
    else:
        if args.iv_root is None or args.iv_index_dir is None:
            raise RuntimeError("MIMIC-IV requires --iv-root and --iv-index-dir")
        train, dev, ddi, dx_count, proc_count, split_info = _load_mimic_iv(
            args.iv_root.resolve(), args.iv_index_dir.resolve()
        )
        medication_count = int(ddi.shape[0])

    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    numeric_policy = configure_numeric_policy()
    config = _config(args.dataset, args.variant, medication_count)
    config["numeric_policy"] = numeric_policy
    state: Dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA,
        "status": "preflight_complete",
        "dataset": args.dataset,
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "split": split_info,
        "completed_updates": 0,
        "selected_update": None,
        "selected_dev_jaccard": None,
        "evaluations": [],
        "test_loaded": False,
    }
    if args.preflight_only:
        _seed(SEED)
        model = MICA(dx_count, proc_count, args.variant, medication_count=medication_count).cuda()
        if args.dataset == "mimic_iii":
            prevalence = train.targets.mean(0)
        else:
            index_meta = json.loads(
                (args.iv_index_dir / "train.index.json").read_text(encoding="utf-8")
            )
            prevalence = np.asarray(index_meta["target_sum"], dtype=np.float32) / float(len(train))
        model.initialize_prevalence(torch.from_numpy(prevalence).cuda())
        rows, targets = train.get_batch(list(range(min(BATCH_SIZE, len(train)))))
        batch = {
            key: value.cuda() for key, value in pack_inputs(rows, dx_count, proc_count).items()
        }
        target_tensor = torch.from_numpy(targets).cuda()
        loss, _bce, _ddi_loss = objective(
            model(batch),
            target_tensor,
            torch.from_numpy(ddi).cuda(),
            medication_count=medication_count,
        )
        if not torch.isfinite(loss):
            raise RuntimeError("replication preflight produced a non-finite loss")
        loss.backward()
        return {
            "preflight_only": True,
            "source_revision": args.source_revision,
            "dataset": args.dataset,
            "variant": args.variant,
            "config": config,
            "split": split_info,
            "parameter_count": sum(param.numel() for param in model.parameters()),
            "test_loaded": False,
        }

    _seed(SEED)
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = MICA(dx_count, proc_count, args.variant, medication_count=medication_count).to(device)
    if args.dataset == "mimic_iii":
        prevalence = train.targets.mean(0)
    else:
        index_meta = json.loads(
            (args.iv_index_dir / "train.index.json").read_text(encoding="utf-8")
        )
        prevalence = np.asarray(index_meta["target_sum"], dtype=np.float32) / float(len(train))
    model.initialize_prevalence(torch.from_numpy(prevalence).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY, betas=(0.9, 0.999), eps=1e-8
    )
    state["status"] = "running"
    _write_progress(output, state)
    best_j = float("-inf")
    best_update: Optional[int] = None
    best_epoch: Optional[int] = None
    best_state: Optional[Dict[str, torch.Tensor]] = None
    best_dev_logits: Optional[np.ndarray] = None
    best_dev_metrics: Optional[Dict[str, float]] = None
    generator = np.random.RandomState(SEED)
    updates_per_epoch = math.ceil(len(train) / float(BATCH_SIZE))
    total_updates = (
        MIMIC_III_EPOCHS * updates_per_epoch if args.dataset == "mimic_iii" else MIMIC_IV_UPDATES
    )
    next_eval = updates_per_epoch if args.dataset == "mimic_iii" else MIMIC_IV_EVAL_EVERY
    update = 0
    epoch = 0
    interval_loss = interval_bce = interval_ddi = 0.0
    interval_examples = 0
    start_time = time.time()
    while update < total_updates:
        epoch += 1
        order = generator.permutation(len(train))
        for start in range(0, len(order), BATCH_SIZE):
            if update >= total_updates:
                break
            indices = order[start : start + BATCH_SIZE]
            rows, targets = train.get_batch(indices)
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(rows, dx_count, proc_count).items()
            }
            target_tensor = torch.from_numpy(targets).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss, bce, ddi_loss = objective(
                model(batch), target_tensor, ddi_tensor, medication_count=medication_count
            )
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            batch_size = len(indices)
            interval_loss += float(loss.item()) * batch_size
            interval_bce += float(bce.item()) * batch_size
            interval_ddi += float(ddi_loss.item()) * batch_size
            interval_examples += batch_size
            update += 1
            if update != next_eval and update < total_updates:
                continue
            dev_logits, dev_targets = _predict(
                model, dev, device, dx_count, proc_count, medication_count
            )
            dev_metrics = surface_metrics(dev_targets, dev_logits, ddi)
            entry: Dict[str, Any] = {
                "update": update,
                "epoch": epoch if args.dataset == "mimic_iii" else None,
                "epoch_equivalent": update / float(updates_per_epoch),
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
                "train_loss": 0.0,
                "train_bce": 0.0,
                "train_ddi": 0.0,
                "dev_metrics": dev_metrics,
                "elapsed_seconds": time.time() - start_time,
                "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
            }
            # Keep exact weighted averages in the aggregate progress row.
            if interval_examples:
                entry["train_loss"] = interval_loss / interval_examples
                entry["train_bce"] = interval_bce / interval_examples
                entry["train_ddi"] = interval_ddi / interval_examples
            state["evaluations"].append(entry)
            jaccard = float(dev_metrics["jaccard"])
            if jaccard > best_j:
                best_j = jaccard
                best_update = update
                best_epoch = epoch if args.dataset == "mimic_iii" else None
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                best_dev_logits = dev_logits.copy()
                best_dev_metrics = dict(dev_metrics)
                torch.save(best_state, output / "selected_checkpoint.pt")
                np.save(output / "selected_dev_logits.npy", best_dev_logits)
            state["completed_updates"] = update
            state["selected_update"] = best_update
            state["selected_dev_jaccard"] = best_j
            _write_progress(output, state)
            interval_loss = interval_bce = interval_ddi = 0.0
            interval_examples = 0
            if args.dataset == "mimic_iii":
                next_eval += updates_per_epoch
            else:
                next_eval += MIMIC_IV_EVAL_EVERY
    if (
        best_state is None
        or best_update is None
        or best_dev_logits is None
        or best_dev_metrics is None
    ):
        raise RuntimeError("no complete Dev checkpoint was selected")
    model.load_state_dict(best_state)
    train_logits, train_targets = _predict(
        model, train, device, dx_count, proc_count, medication_count
    )
    train_metrics = surface_metrics(train_targets, train_logits, ddi)
    terminal_entry = state["evaluations"][-1]
    result: Dict[str, Any] = {
        "schema_version": 1,
        "status": "complete",
        "stage": "STAGE -1F",
        "dataset": args.dataset,
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(param.numel() for param in model.parameters()),
        "split": split_info,
        "updates_per_epoch": updates_per_epoch,
        "completed_updates": update,
        "completed_epochs": MIMIC_III_EPOCHS if args.dataset == "mimic_iii" else None,
        "selected_update": best_update,
        "selected_epoch": best_epoch,
        "selected_epoch_equivalent": best_update / float(updates_per_epoch),
        "selected_checkpoint": {"Train": train_metrics, "Dev": best_dev_metrics},
        "terminal": terminal_entry,
        "evaluations": state["evaluations"],
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
    state["terminal"] = terminal_entry
    _write_progress(output, state)
    _write_json(output / "results.json", result)
    if hasattr(train, "close"):
        train.close()
    if hasattr(dev, "close"):
        dev.close()
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("mimic_iii", "mimic_iv"), required=True)
    parser.add_argument("--variant", choices=MICA.VARIANTS[:2], required=True)
    parser.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--train-dev-root", type=Path)
    parser.add_argument("--iv-root", type=Path)
    parser.add_argument("--iv-index-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--prepare-iv-index", action="store_true")
    args = parser.parse_args(argv)
    if args.prepare_iv_index and (
        args.dataset != "mimic_iv" or args.iv_root is None or args.iv_index_dir is None
    ):
        parser.error(
            "--prepare-iv-index requires --dataset mimic_iv, --iv-root, and --iv-index-dir"
        )
    return args


def main() -> None:
    args = parse_args()
    if args.prepare_iv_index:
        _require_clean_source(args.source_revision)
        print(
            json.dumps(
                prepare_iv_indexes(args.iv_root.resolve(), args.iv_index_dir.resolve()),
                sort_keys=True,
            )
        )
        return
    result = run(args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
