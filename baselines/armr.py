#!/usr/bin/env python3
"""Run the pinned ARMR implementation on the frozen MIMIC-III Train/Dev profile.

The released ARMR model is imported from an immutable external checkout.  This
module owns only the benchmark adapter, the source-informed training loop, and
the public-safe terminal artifacts.  It never loads a MIMIC-IV Test surface.

``formal`` mode is the only mode that can produce development evidence.  The
optional ``smoke`` mode is explicitly marked non-evidence and is limited to one
epoch.  Source-native validation values are retained as diagnostics; checkpoint
and operating-point selection uses the frozen paper evaluator instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from research.prototypes.paper_contract.evaluator import (  # noqa: E402
    SelectionCandidate,
    VisitPrediction,
    evaluate,
    select_joint,
)

UTC = timezone.utc  # noqa: UP017 -- the execution environment includes Python 3.8.

PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"
ARMR_SOURCE_REVISION = "c0de843d43a1f2867d45ede836b918abd11a0fda"
MEDICATIONS = 131
SOURCE_DIM = 256
SOURCE_VISIT_LENGTH = 3
SOURCE_BATCH_SIZE = 32
SOURCE_EVAL_BATCH_SIZE = 256
SOURCE_EPOCHS = 56
SOURCE_THRESHOLD = 0.30
OPERATING_POINTS = tuple(round(value / 100.0, 2) for value in range(5, 100, 5))
NATIVE_DEFAULT = 0.35
PROGRESS_SCHEMA_VERSION = 1
EXPECTED_PARAMETER_COUNT = 9_577_222
PROCEDURE_ZEROING_SOURCE = "procs=torch.zeros_like(procs).to(procs.device)"


class ArmrError(RuntimeError):
    """Raised when ARMR source, profile, or terminal-artifact checks fail."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_git(root: Path, expected_revision: str, label: str) -> str:
    if not (root / ".git").exists():
        raise ArmrError(f"{label} is not a Git checkout")
    actual = _git_output(root, "rev-parse", "HEAD")
    if actual != expected_revision:
        raise ArmrError(f"{label} revision does not match the pinned source")
    status = _git_output(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ArmrError(f"{label} checkout is not clean")
    return actual


def _runtime_modules() -> tuple[Any, Any, Any]:
    """Import execution-plane dependencies lazily so local contract tests stay lightweight."""

    try:
        import dill
        import numpy as np
        import torch
    except ImportError as error:  # pragma: no cover - exercised only on a non-execution plane.
        raise ArmrError("ARMR execution requires dill, NumPy, and PyTorch") from error
    return dill, np, torch


def _is_dev(patient_index: int) -> bool:
    digest = hashlib.sha256(("idea008-gate01-v1:" + str(patient_index)).encode("utf-8")).digest()[
        :8
    ]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


def patient_split(patient_count: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return the frozen patient split without touching any target-bearing surface."""

    split = int(patient_count * 2 / 3)
    train = tuple(range(split))
    dev = tuple(index for index in range(split, patient_count) if _is_dev(index))
    return train, dev


def _word(indexed: Any, index: int) -> str:
    try:
        return str(indexed[index])
    except (KeyError, IndexError):
        return str(indexed[str(index)])


def _vocabulary(voc: Mapping[str, Any]) -> tuple[str, ...]:
    medication = voc["med_voc"]
    ids = {int(key) for key in medication.idx2word}
    if ids != set(range(MEDICATIONS)):
        raise ArmrError("ARMR medication vocabulary is not the exact canonical 131 axis")
    return tuple(_word(medication.idx2word, index) for index in range(MEDICATIONS))


def _sorted_codes(values: Iterable[Any]) -> list[int]:
    return sorted({int(value) for value in values})


def _patient_rows(records: Sequence[Any], patients: Sequence[int]) -> list[dict[str, Any]]:
    """Materialize target-bearing metadata while keeping model inputs target-free."""

    rows: list[dict[str, Any]] = []
    for patient_index in patients:
        history: list[tuple[list[int], list[int], list[int]]] = []
        for visit_index, admission in enumerate(records[int(patient_index)]):
            diagnoses = _sorted_codes(admission[0])
            procedures = _sorted_codes(admission[1])
            medications = _sorted_codes(admission[2])
            rows.append(
                {
                    "diagnoses": diagnoses,
                    "procedures": procedures,
                    "history": [(list(dx), list(proc), list(med)) for dx, proc, med in history],
                    "target": medications,
                    "patient_id": str(int(patient_index)),
                    "visit_id": f"{int(patient_index)}:{visit_index}",
                }
            )
            history.append((diagnoses, procedures, medications))
    return rows


def _model_records(records: Sequence[Any], patients: Sequence[int]) -> list[Any]:
    """Return source-shaped records; current medications are masked by ``create_dataset``."""

    result: list[Any] = []
    for patient_index in patients:
        patient: list[list[list[int]]] = []
        for admission in records[int(patient_index)]:
            patient.append(
                [
                    _sorted_codes(admission[0]),
                    _sorted_codes(admission[1]),
                    _sorted_codes(admission[2]),
                ]
            )
        result.append(patient)
    return result


def model_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Expose exactly the target-free fields consumed by the source batch builder."""

    return {
        "diagnoses": list(row["diagnoses"]),
        "procedures": list(row["procedures"]),
        "history": [(list(dx), list(proc), list(med)) for dx, proc, med in row["history"]],
    }


def _validate_binary_ddi(ddi: Any) -> None:
    import numpy as np

    matrix = np.asarray(ddi, dtype=np.float32)
    if (
        matrix.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(matrix).all()
        or not np.isin(matrix, (0.0, 1.0)).all()
        or not np.array_equal(matrix, matrix.T)
        or np.any(np.diag(matrix) != 0)
    ):
        raise ArmrError("ARMR DDI matrix is not finite binary symmetric zero-diagonal 131 by 131")
    if int(np.triu(matrix, 1).sum()) != 448:
        raise ArmrError("ARMR DDI matrix does not contain the frozen 448 undirected pairs")


def _validate_profile_assets(snapshot: Path, train_dev: Path, profile: Mapping[str, Any]) -> None:
    benchmark = profile.get("benchmark", {})
    if profile.get("profile_id") != PROFILE_ID:
        raise ArmrError("committed MIII profile ID does not match the ARMR runner")
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise ArmrError("committed MIII snapshot ID does not match the ARMR runner")
    expected_assets = benchmark.get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        expected = expected_assets.get(name, {})
        path = snapshot / name
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != expected.get("bytes")
            or _sha256(path) != expected.get("sha256")
        ):
            raise ArmrError("MIII source asset hash does not match the frozen profile: " + name)
    split = profile.get("split", {})
    if split.get("train", {}).get("target_array_sha256") is None:
        raise ArmrError("frozen profile does not bind the Train target hash")
    for name, expected_hash in (
        ("train_targets.npy", split.get("train", {}).get("target_array_sha256")),
        ("dev_targets.npy", split.get("dev", {}).get("target_array_sha256")),
    ):
        path = train_dev / name
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected_hash:
            raise ArmrError("MIII target array hash does not match the frozen profile: " + name)


def _validate_vocabulary_and_records(
    records: Sequence[Any], voc: Mapping[str, Any], ddi: Any, patients: Sequence[int]
) -> tuple[int, int, tuple[str, ...]]:
    diagnosis = voc["diag_voc"]
    procedure = voc["pro_voc"]
    dx_ids = {int(key) for key in diagnosis.idx2word}
    proc_ids = {int(key) for key in procedure.idx2word}
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise ArmrError("ARMR diagnosis/procedure IDs are not contiguous")
    vocabulary = _vocabulary(voc)
    profile_path = (
        Path(__file__).resolve().parents[1]
        / "research"
        / "benchmarks"
        / "mimiciii-medrec"
        / "profile.json"
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    sorted_digest = hashlib.sha256(
        "".join(f"{code}\n" for code in sorted(vocabulary)).encode()
    ).hexdigest()
    expected_digest = profile["benchmark"]["medication_identity"][
        "canonical_sorted_vocabulary_sha256"
    ]
    if sorted_digest != expected_digest:
        raise ArmrError("ARMR medication vocabulary identity does not match the frozen profile")
    for patient_index in patients:
        for admission in records[int(patient_index)]:
            if any(int(code) not in dx_ids for code in admission[0]):
                raise ArmrError("record contains a diagnosis outside the frozen vocabulary")
            if any(int(code) not in proc_ids for code in admission[1]):
                raise ArmrError("record contains a procedure outside the frozen vocabulary")
            if any(int(code) not in range(MEDICATIONS) for code in admission[2]):
                raise ArmrError("record contains a medication outside the frozen 131 axis")
    _validate_binary_ddi(ddi)
    return len(dx_ids), len(proc_ids), vocabulary


def _validate_targets(rows: Sequence[Mapping[str, Any]], targets: Any, label: str) -> None:
    import numpy as np

    matrix = np.asarray(targets, dtype=np.float32)
    if matrix.shape != (len(rows), MEDICATIONS):
        raise ArmrError(f"{label} targets are not aligned with the canonical [visits,131] surface")
    if not np.isfinite(matrix).all() or not np.isin(matrix, (0.0, 1.0)).all():
        raise ArmrError(f"{label} targets are not finite binary values")
    for index, row in enumerate(rows):
        expected = np.zeros(MEDICATIONS, dtype=np.float32)
        expected[row["target"]] = 1.0
        if not np.array_equal(expected, matrix[index]):
            raise ArmrError(f"{label} target mismatch at row {index}")


def _bundle(
    data: Sequence[Any],
    metadata: Sequence[Mapping[str, Any]],
    voc_size: tuple[int, int, int],
    device: Any,
    create_dataset: Any,
    create_batches: Any,
    batch_size: int,
) -> dict[str, Any]:
    """Build source-native near-to-far batches and retain an inverse order map."""

    diags, procs, meds, labels, ids = create_dataset(data, voc_size, device=device)
    order = sorted(range(len(diags)), key=lambda index: int(diags[index].shape[0]))
    batches = create_batches(diags, procs, meds, labels, ids, batch_size=batch_size, sort=True)
    inverse = [0] * len(order)
    for sorted_index, original_index in enumerate(order):
        inverse[original_index] = sorted_index
    return {
        "diag_batches": batches[0],
        "proc_batches": batches[1],
        "med_batches": batches[2],
        "label_batches": batches[3],
        "ids_batches": batches[4],
        "batch_seq_len": batches[5],
        "n_batches": len(batches[0]),
        "order": order,
        "inverse": inverse,
        "metadata": [metadata[index] for index in order],
    }


def _predict(model: Any, bundle: Mapping[str, Any], torch: Any, np: Any) -> Any:
    model.eval()
    values: list[Any] = []
    with torch.no_grad():
        for batch_id in range(bundle["n_batches"]):
            logits = model(
                bundle["diag_batches"][batch_id],
                bundle["proc_batches"][batch_id],
                bundle["med_batches"][batch_id],
            )
            values.append(logits.detach().cpu().numpy())
    if not values:
        raise ArmrError("ARMR prediction bundle is empty")
    sorted_logits = np.concatenate(values, axis=0)
    logits = sorted_logits[np.asarray(bundle["inverse"], dtype=np.int64)]
    if logits.ndim != 2 or logits.shape[1] != MEDICATIONS or not np.isfinite(logits).all():
        raise ArmrError("ARMR model logits are not finite [visits,131] values")
    return logits


def _bundle_targets(bundle: Mapping[str, Any], torch: Any, np: Any) -> Any:
    """Recover labels emitted by the pinned helper in original patient/visit order."""

    values: list[Any] = []
    for batch_id in range(bundle["n_batches"]):
        values.append(bundle["label_batches"][batch_id].detach().cpu().numpy())
    if not values:
        raise ArmrError("ARMR label bundle is empty")
    sorted_targets = np.concatenate(values, axis=0)
    return sorted_targets[np.asarray(bundle["inverse"], dtype=np.int64)]


def _sigmoid(logits: Any, np: Any) -> Any:
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))


def _source_ddi_rate(predictions: Sequence[Sequence[int]], ddi: Any) -> float:
    total = interactions = 0
    for medications in predictions:
        for left_index, left in enumerate(medications):
            for right in medications[left_index + 1 :]:
                total += 1
                interactions += int(bool(ddi[left, right]) or bool(ddi[right, left]))
    return 0.0 if total == 0 else interactions / float(total)


def _source_metrics(
    rows: Sequence[Mapping[str, Any]], targets: Any, logits: Any, ddi: Any, threshold: float
) -> dict[str, float]:
    """Reproduce the released source validation diagnostic, including its fixed threshold."""

    import numpy as np
    from sklearn.metrics import average_precision_score

    probabilities = _sigmoid(logits, np)
    predictions = [list(np.flatnonzero(row >= threshold)) for row in probabilities]
    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        grouped.setdefault(str(row["patient_id"]), []).append(index)
    patient_scores: list[tuple[float, float, float, float, float, float]] = []
    for patient_id in sorted(grouped, key=lambda value: int(value)):
        indexes = grouped[patient_id]
        jaccards: list[float] = []
        precisions: list[float] = []
        recalls: list[float] = []
        f1s: list[float] = []
        aps: list[float] = []
        for index in indexes:
            target = set(int(value) for value in np.flatnonzero(targets[index] > 0.5))
            predicted = set(predictions[index])
            intersection = len(target & predicted)
            union = len(target | predicted)
            jaccards.append(0.0 if union == 0 else intersection / float(union))
            precision = 0.0 if not predicted else intersection / float(len(predicted))
            recall = 0.0 if not target else intersection / float(len(target))
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(
                0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            )
            aps.append(
                float(
                    average_precision_score(targets[index], probabilities[index], average="macro")
                )
            )
        patient_scores.append(
            (
                float(np.mean(jaccards)),
                float(np.mean(aps)),
                float(np.mean(precisions)),
                float(np.mean(recalls)),
                float(np.mean(f1s)),
                _source_ddi_rate([predictions[index] for index in indexes], ddi),
            )
        )
    aggregate = np.asarray(patient_scores, dtype=np.float64).mean(axis=0)
    stable_nll = np.maximum(logits, 0.0) - logits * targets + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": float(aggregate[0]),
        "prauc": float(aggregate[1]),
        "avg_precision": float(aggregate[2]),
        "avg_recall": float(aggregate[3]),
        "avg_f1": float(aggregate[4]),
        "ddi_rate": float(aggregate[5]),
        "mean_medication_count": float(np.mean([len(item) for item in predictions])),
        "loss": float(stable_nll.mean()),
    }


def _ddi_pairs(vocabulary: Sequence[str], ddi: Any) -> tuple[tuple[str, str], ...]:
    import numpy as np

    left, right = np.triu(np.asarray(ddi, dtype=np.float32), 1).nonzero()
    return tuple((vocabulary[int(a)], vocabulary[int(b)]) for a, b in zip(left, right, strict=True))


def _profile_metrics(
    rows: Sequence[Mapping[str, Any]],
    targets: Any,
    logits: Any,
    threshold: float,
    vocabulary: Sequence[str],
    ddi: Any,
) -> dict[str, Any]:
    import numpy as np

    probabilities = _sigmoid(logits, np)
    samples = []
    for index, row in enumerate(rows):
        target_ids = tuple(int(value) for value in np.flatnonzero(targets[index] > 0.5))
        predicted_ids = tuple(
            int(value) for value in np.flatnonzero(probabilities[index] >= threshold)
        )
        samples.append(
            VisitPrediction(
                patient_id=row["patient_id"],
                visit_id=row["visit_id"],
                target_medications=tuple(vocabulary[value] for value in target_ids),
                predicted_medications=tuple(vocabulary[value] for value in predicted_ids),
                medication_scores=tuple(float(value) for value in probabilities[index]),
            )
        )
    return evaluate(samples, vocabulary=tuple(vocabulary), ddi_pairs=_ddi_pairs(vocabulary, ddi))


def _selection_key(candidate: SelectionCandidate) -> tuple[float, float, int, int]:
    return (
        -float(candidate.patient_macro_jaccard),
        abs(float(candidate.operating_point) - NATIVE_DEFAULT),
        candidate.operating_point_index,
        candidate.checkpoint,
    )


def _seed_everything(seed: int, torch: Any, np: Any) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def _numeric_policy(torch: Any) -> dict[str, Any]:
    return {
        "dtype": "float32",
        "cuda_matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
    }


def _load_source(source_root: Path) -> tuple[Any, Any, Any, Any]:
    source_code = source_root / "code"
    if not (source_code / "net_mynet.py").is_file():
        raise ArmrError("pinned ARMR source is missing code/net_mynet.py")
    source_text = (source_code / "net_mynet.py").read_text(encoding="utf-8")
    if PROCEDURE_ZEROING_SOURCE not in source_text:
        raise ArmrError("pinned ARMR source procedure-channel behavior drifted")
    sys.path.insert(0, str(source_code))
    try:
        from net_mynet import MyNet
        from utils_ import create_batches, create_dataset, create_ehr_adj
    except ImportError as error:
        raise ArmrError("pinned ARMR source cannot import its model/batch modules") from error
    return MyNet, create_batches, create_dataset, create_ehr_adj


def _preflight_model(
    model: Any,
    sample_bundle: Mapping[str, Any],
    torch: Any,
    np: Any,
) -> None:
    model.eval()
    with torch.no_grad():
        output = model(
            sample_bundle["diag_batches"][0],
            sample_bundle["proc_batches"][0],
            sample_bundle["med_batches"][0],
        )
    values = output.detach().cpu().numpy()
    if values.shape[1:] != (MEDICATIONS,) or not np.isfinite(values).all():
        raise ArmrError("ARMR preflight produced invalid logits")


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one source-faithful ARMR development lane."""

    dill, np, torch = _runtime_modules()
    sys.dont_write_bytecode = True
    repo_root = Path(__file__).resolve().parents[1]
    harness_revision = _git_output(repo_root, "rev-parse", "HEAD")
    harness_status = _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    if harness_status:
        raise ArmrError("ARMR harness checkout is not clean")
    source_root = args.source_root.resolve()
    _require_clean_git(source_root, ARMR_SOURCE_REVISION, "ARMR source")
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev.name != TRAIN_DEV_ID:
        raise ArmrError("snapshot or Train/Dev root identity does not match the frozen profile")
    if not snapshot.is_dir() or not train_dev.is_dir():
        raise ArmrError("snapshot and Train/Dev roots must exist")
    if source_root == output or source_root in output.parents:
        raise ArmrError("output directory must be outside the ARMR source checkout")
    if repo_root == output or repo_root in output.parents:
        raise ArmrError("output directory must be outside the harness checkout")
    if output.exists() and any(output.iterdir()):
        raise ArmrError("output directory is not empty")

    profile_path = repo_root / "research" / "benchmarks" / "mimiciii-medrec" / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    _validate_profile_assets(snapshot, train_dev, profile)
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    if len(records) != 6350:
        raise ArmrError("canonical snapshot patient count changed")
    train_patients, dev_patients = patient_split(len(records))
    if (len(train_patients), len(dev_patients)) != (4233, 1004):
        raise ArmrError("frozen patient split counts changed")
    dx_count, proc_count, vocabulary = _validate_vocabulary_and_records(
        records, voc, ddi, (*train_patients, *dev_patients)
    )
    train_rows = _patient_rows(records, train_patients)
    dev_rows = _patient_rows(records, dev_patients)
    train_targets = np.asarray(
        np.load(train_dev / "train_targets.npy", allow_pickle=False), dtype=np.float32
    )
    dev_targets = np.asarray(
        np.load(train_dev / "dev_targets.npy", allow_pickle=False), dtype=np.float32
    )
    _validate_targets(train_rows, train_targets, "Train")
    _validate_targets(dev_rows, dev_targets, "Dev")
    if (len(train_rows), len(dev_rows)) != (10489, 2130):
        raise ArmrError("frozen Train/Dev visit counts changed")

    if args.device == "auto":
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if args.mode == "formal" and device.type != "cuda":
        raise ArmrError("formal ARMR training requires CUDA on the 319 execution plane")
    _seed_everything(args.seed, torch, np)
    MyNet, create_batches, create_dataset, create_ehr_adj = _load_source(source_root)
    train_data = _model_records(records, train_patients)
    dev_data = _model_records(records, dev_patients)
    voc_size = (dx_count, proc_count, MEDICATIONS)
    train_bundle = _bundle(
        train_data,
        train_rows,
        voc_size,
        device,
        create_dataset,
        create_batches,
        SOURCE_BATCH_SIZE,
    )
    dev_bundle = _bundle(
        dev_data,
        dev_rows,
        voc_size,
        device,
        create_dataset,
        create_batches,
        SOURCE_EVAL_BATCH_SIZE,
    )
    generated_train_targets = _bundle_targets(train_bundle, torch, np)
    generated_dev_targets = _bundle_targets(dev_bundle, torch, np)
    if not np.array_equal(generated_train_targets, train_targets):
        raise ArmrError("pinned ARMR batch helper changed the Train target alignment")
    if not np.array_equal(generated_dev_targets, dev_targets):
        raise ArmrError("pinned ARMR batch helper changed the Dev target alignment")
    ehr_adj = create_ehr_adj(train_data, MEDICATIONS)
    model = MyNet(
        emb_dim=SOURCE_DIM,
        k=SOURCE_VISIT_LENGTH,
        voc_size=voc_size,
        ehr_adj=torch.as_tensor(ehr_adj, dtype=torch.float32, device=device),
        ddi_adj=torch.as_tensor(ddi, dtype=torch.float32, device=device),
    ).to(device)
    parameter_count = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    if parameter_count != EXPECTED_PARAMETER_COUNT:
        raise ArmrError(f"pinned ARMR parameter count changed: {parameter_count}")
    _preflight_model(model, dev_bundle, torch, np)
    if args.preflight_only:
        return {
            "status": "PASS",
            "preflight_only": True,
            "baseline_id": "armr",
            "profile_id": PROFILE_ID,
            "source_revision": ARMR_SOURCE_REVISION,
            "harness_revision": harness_revision,
            "environment": {
                "python": sys.version.split()[0],
                "torch": torch.__version__,
                "numpy": np.__version__,
                "numeric_policy": _numeric_policy(torch),
            },
            "parameter_count": parameter_count,
            "split": {
                "train_patients": len(train_patients),
                "dev_patients": len(dev_patients),
                "train_visits": len(train_rows),
                "dev_visits": len(dev_rows),
            },
            "test_loaded": False,
        }

    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC).isoformat()
    requested_epochs = 1 if args.mode == "smoke" else SOURCE_EPOCHS
    numeric_policy = _numeric_policy(torch)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=2e-4, betas=(0.9, 0.999), eps=1e-5, weight_decay=1e-6
    )
    config = {
        "profile_id": PROFILE_ID,
        "source_revision": ARMR_SOURCE_REVISION,
        "seed": args.seed,
        "hidden_dim": SOURCE_DIM,
        "history_visit_length": SOURCE_VISIT_LENGTH,
        "batch_size_visits": SOURCE_BATCH_SIZE,
        "eval_batch_size_visits": SOURCE_EVAL_BATCH_SIZE,
        "epochs_requested": requested_epochs,
        "source_maximum_epochs": SOURCE_EPOCHS,
        "optimizer": "Adam(lr=2e-4, betas=(0.9,0.999), eps=1e-5, weight_decay=1e-6)",
        "loss": "BCEWithLogitsLoss",
        "source_validation_threshold": SOURCE_THRESHOLD,
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
        "checkpoint_selection": "joint Dev patient-macro Jaccard and operating point",
        "early_stopping": "source PRAUC decline twice; disabled only by one-epoch smoke cap",
        "ehr_graph": "Train-only medication co-occurrence from pinned source helper",
        "ddi_graph": "frozen canonical 131 DDI matrix",
        "procedure_channel": "pinned MyNet.forward zeroes procedures",
        "numeric_policy": numeric_policy,
    }
    split_info = {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train_rows),
        "dev_visits": len(dev_rows),
    }
    progress: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": "running",
        "non_evidence": args.mode != "formal",
        "baseline_id": "armr",
        "profile_id": PROFILE_ID,
        "source_revision": ARMR_SOURCE_REVISION,
        "harness_revision": harness_revision,
        "mode": args.mode,
        "started_at": started_at,
        "config": config,
        "split": split_info,
        "completed_epochs": 0,
        "selected_checkpoint": None,
        "selected_operating_point": None,
        "evaluations": progress,
        "test_loaded": False,
    }
    _write_json(output / "progress.json", state)
    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, Any] | None = None
    best_dev_logits: Any = None
    source_best_epoch: int | None = None
    source_best_score = -math.inf
    source_best_metrics: dict[str, float] | None = None
    previous_source_prauc = 0.0
    continuous_decline = 0
    start_time = time.time()

    try:
        for epoch in range(1, requested_epochs + 1):
            model.train()
            train_loss_sum = 0.0
            train_count = 0
            for batch_id in range(train_bundle["n_batches"]):
                logits = model(
                    train_bundle["diag_batches"][batch_id],
                    train_bundle["proc_batches"][batch_id],
                    train_bundle["med_batches"][batch_id],
                )
                target = train_bundle["label_batches"][batch_id]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
                if not torch.isfinite(loss):
                    raise ArmrError("ARMR training loss is non-finite")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                size = int(target.shape[0])
                train_loss_sum += float(loss.detach().item()) * size
                train_count += size
            dev_logits = _predict(model, dev_bundle, torch, np)
            source_validation = _source_metrics(
                dev_rows, dev_targets, dev_logits, ddi, SOURCE_THRESHOLD
            )
            candidates: list[SelectionCandidate] = []
            candidate_results: list[dict[str, Any]] = []
            for operating_point_index, operating_point in enumerate(OPERATING_POINTS):
                metrics = _profile_metrics(
                    dev_rows,
                    dev_targets,
                    dev_logits,
                    operating_point,
                    vocabulary,
                    ddi,
                )
                candidates.append(
                    SelectionCandidate(
                        checkpoint=epoch,
                        operating_point=operating_point,
                        patient_macro_jaccard=float(metrics["jaccard"]),
                        operating_point_index=operating_point_index,
                    )
                )
                candidate_results.append(
                    {
                        "operating_point": operating_point,
                        "patient_macro_jaccard": float(metrics["jaccard"]),
                        "metrics": metrics,
                    }
                )
            epoch_best = select_joint(
                candidates,
                operating_point_order=OPERATING_POINTS,
                native_default=NATIVE_DEFAULT,
            )
            if best_candidate is None or _selection_key(epoch_best) < _selection_key(
                best_candidate
            ):
                best_candidate = epoch_best
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                best_dev_logits = dev_logits.copy()
                torch.save(best_state, output / "selected_checkpoint.pt")
                np.save(output / "selected_dev_logits.npy", best_dev_logits.astype(np.float32))
            if source_validation["prauc"] > source_best_score:
                source_best_score = source_validation["prauc"]
                source_best_epoch = epoch
                source_best_metrics = dict(source_validation)
            if args.mode == "formal":
                if source_validation["prauc"] < previous_source_prauc:
                    continuous_decline += 1
                    stopped_early = continuous_decline >= 2
                else:
                    continuous_decline = 0
                    stopped_early = False
            else:
                stopped_early = False
            previous_source_prauc = source_validation["prauc"]
            selected_metrics = next(
                item["metrics"]
                for item in candidate_results
                if item["operating_point"] == epoch_best.operating_point
            )
            entry = {
                "epoch": epoch,
                "train_loss": train_loss_sum / train_count,
                "source_validation": source_validation,
                "selected_operating_point_this_epoch": epoch_best.operating_point,
                "selected_dev_jaccard_this_epoch": epoch_best.patient_macro_jaccard,
                "candidate_operating_points": candidate_results,
                "selected_metrics_this_epoch": selected_metrics,
                "elapsed_seconds": time.time() - start_time,
            }
            progress.append(entry)
            state["completed_epochs"] = epoch
            state["selected_checkpoint"] = best_candidate.checkpoint if best_candidate else None
            state["selected_operating_point"] = (
                best_candidate.operating_point if best_candidate else None
            )
            _write_json(output / "progress.json", state)
            print(
                json.dumps(
                    {
                        "baseline": "armr",
                        "epoch": epoch,
                        "source_prauc": source_validation["prauc"],
                        "selected_dev_jaccard": epoch_best.patient_macro_jaccard,
                        "selected_operating_point": epoch_best.operating_point,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if stopped_early:
                break

        if best_candidate is None or best_state is None or best_dev_logits is None:
            raise ArmrError("ARMR did not produce a complete Dev checkpoint")
        model.load_state_dict(best_state)
        train_logits = _predict(model, train_bundle, torch, np)
        selected_train = _profile_metrics(
            train_rows,
            train_targets,
            train_logits,
            float(best_candidate.operating_point),
            vocabulary,
            ddi,
        )
        selected_dev = _profile_metrics(
            dev_rows,
            dev_targets,
            best_dev_logits,
            float(best_candidate.operating_point),
            vocabulary,
            ddi,
        )
        predicted_count = float(selected_dev["average_medication_count"])
        if not (math.isfinite(predicted_count) and 0.0 < predicted_count < MEDICATIONS):
            raise ArmrError("ARMR selected Dev predictions are collapsed or out of range")
        checkpoint_path = output / "selected_checkpoint.pt"
        result = {
            "schema_version": 1,
            "kind": "armr_result",
            "status": "complete",
            "evidence_role": "DEVELOPMENT" if args.mode == "formal" else "NON_EVIDENCE_SMOKE",
            "non_evidence": args.mode != "formal",
            "baseline_id": "armr",
            "profile_id": PROFILE_ID,
            "snapshot_id": SNAPSHOT_ID,
            "train_dev_id": TRAIN_DEV_ID,
            "source_revision": ARMR_SOURCE_REVISION,
            "harness_revision": harness_revision,
            "seed": args.seed,
            "mode": args.mode,
            "config": config,
            "parameter_count": parameter_count,
            "split": split_info,
            "epochs_requested": requested_epochs,
            "epochs_observed": len(progress),
            "source_early_stop": len(progress) < requested_epochs and args.mode == "formal",
            "source_best": {
                "epoch": source_best_epoch,
                "validation": source_best_metrics,
                "selection_metric": "source patient-macro PRAUC at threshold 0.30",
            },
            "selection": {
                "checkpoint": best_candidate.checkpoint,
                "operating_point": best_candidate.operating_point,
                "metric": "Dev patient-macro Jaccard",
                "score": best_candidate.patient_macro_jaccard,
                "rule": "all declared operating points at every observed checkpoint",
            },
            "metrics": {"Train": selected_train, "Dev": selected_dev},
            "progress": progress,
            "checkpoint": {
                "relative_path": "selected_checkpoint.pt",
                "sha256": _sha256(checkpoint_path),
                "size_bytes": checkpoint_path.stat().st_size,
            },
            "runtime": {
                "python": sys.version.split()[0],
                "torch": torch.__version__,
                "numpy": np.__version__,
                "numeric_policy": numeric_policy,
                "wall_time_seconds": time.time() - start_time,
            },
            "graphs": {
                "ehr_train_only": True,
                "ehr_edge_count": int(np.triu(np.asarray(ehr_adj), 1).sum()),
                "ddi_pair_count": int(np.triu(ddi, 1).sum()),
            },
            "test_loaded": False,
            "test_evaluation": False,
        }
        state["status"] = "complete"
        state["finished_at"] = datetime.now(UTC).isoformat()
        state["source_early_stop"] = result["source_early_stop"]
        _write_json(output / "progress.json", state)
        _write_json(
            output / "status.json",
            {
                "schema_version": 1,
                "kind": "armr_status",
                "state": "complete",
                "mode": args.mode,
                "non_evidence": args.mode != "formal",
                "started_at": started_at,
                "finished_at": state["finished_at"],
                "test_loaded": False,
            },
        )
        _write_json(output / "result.json", result)
        return result
    except Exception as error:
        failure = {
            "schema_version": 1,
            "kind": "armr_status",
            "state": "failed",
            "mode": args.mode,
            "non_evidence": args.mode != "formal",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "failure_code": "armr_run_failed",
            "error": str(error),
            "test_loaded": False,
        }
        _write_json(output / "status.json", failure)
        _write_json(output / "failure.json", failure)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", default=ARMR_SOURCE_REVISION)
    parser.add_argument("--seed", type=int, default=1203)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--mode", choices=("formal", "smoke"), default="formal")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.source_revision != ARMR_SOURCE_REVISION:
        parser.error("--source-revision must equal the pinned ARMR source revision")
    return args


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
