#!/usr/bin/env python3
"""Run the pinned MoleRec model on the frozen MIMIC-III paper profile.

The released MoleRec model and visit-level optimizer are imported from an
immutable external checkout.  This adapter owns only profile-bound patient
selection, terminal metrics, and public-safe run artifacts.  It never loads a
MIMIC-IV Test surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from baselines.reproduction_artifacts import (  # noqa: E402
    finalize_v2_pair,
    identity_from_environment,
    terminal_result,
    terminal_status,
)
from baselines.reproduction_runner import write_failure_pair, write_json_atomic  # noqa: E402
from research.prototypes.paper_contract.evaluator import (  # noqa: E402
    SelectionCandidate,
    VisitPrediction,
    evaluate,
    select_joint,
)

UTC = timezone.utc  # noqa: UP017 -- the execution plane includes Python 3.8.

PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"
SOURCE_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
PREPROCESSING_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"
PROGRAM_ID = "molerec-profile"
ENVIRONMENT_SHA256 = "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
MEDICATIONS = 131
EPOCHS = 50
SOURCE_THRESHOLD = 0.5
NATIVE_DEFAULT = 0.35
OPERATING_POINTS = tuple(round(value / 100.0, 2) for value in range(5, 100, 5))
EXPECTED_PARAMETER_COUNT = 506932
SNAPSHOT_FILES = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ehr_adj_final.pkl",
    "ddi_mask_H.pkl",
    "substructure_smiles.pkl",
    "idx2SMILES.pkl",
    "idx2drug.pkl",
)
SNAPSHOT_ASSET_HASHES = {
    "ddi_mask_H.pkl": "44d3abd5da6239fe84a55cbd2e1c7d94a1380115730a241f618834a3ee7be461",
    "substructure_smiles.pkl": "0009032d316a17d0162472a28ef1309e757477ba71d325476c798ff493dc484f",
    "idx2SMILES.pkl": "b1eaaba3a8bdcb2c7d51b7edaa53ed4357a76d5f8f4b9fa3bdcc4c4dc8a21ce6",
    "idx2drug.pkl": "b1eaaba3a8bdcb2c7d51b7edaa53ed4357a76d5f8f4b9fa3bdcc4c4dc8a21ce6",
    "ehr_adj_final.pkl": "4d8fde44926babbde741b10d52a1a7d0106f7a7d7c4a15f1df1a42ad94e140a8",
}


class MoleRecProfileError(RuntimeError):
    """Raised when source, profile, or terminal-artifact checks fail."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _require_clean_git(root: Path, expected_revision: str, label: str) -> str:
    if not (root / ".git").exists():
        raise MoleRecProfileError(f"{label} is not a Git checkout")
    revision = _git_output(root, "rev-parse", "HEAD")
    if revision != expected_revision:
        raise MoleRecProfileError(f"{label} revision does not match the pinned source")
    if _git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MoleRecProfileError(f"{label} checkout is not clean")
    return revision


def _runtime_modules() -> tuple[Any, Any, Any]:
    try:
        import dill
        import numpy as np
        import torch
    except ImportError as error:  # pragma: no cover - execution-plane only.
        raise MoleRecProfileError("MoleRec execution requires dill, NumPy, and PyTorch") from error
    return dill, np, torch


def _is_dev(patient_index: int) -> bool:
    digest = hashlib.sha256(("idea008-gate01-v1:" + str(patient_index)).encode("utf-8")).digest()[
        :8
    ]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


def patient_split(patient_count: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    split = int(patient_count * 2 / 3)
    return tuple(range(split)), tuple(
        index for index in range(split, patient_count) if _is_dev(index)
    )


def _profile_path() -> Path:
    return _REPO_ROOT / "research" / "benchmarks" / "mimiciii-medrec" / "profile.json"


def _validate_asset(path: Path, expected: Mapping[str, Any], name: str) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != expected.get("bytes")
        or _sha256(path) != expected.get("sha256")
    ):
        raise MoleRecProfileError(
            f"MIII source asset hash does not match the frozen profile: {name}"
        )


def _validate_snapshot_layout(snapshot: Path) -> None:
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise MoleRecProfileError("MoleRec snapshot root must be a regular directory")
    observed = tuple(
        sorted(path.name for path in snapshot.iterdir() if path.is_file() or path.is_symlink())
    )
    if observed != tuple(sorted(SNAPSHOT_FILES)):
        raise MoleRecProfileError(
            "MoleRec snapshot must contain exactly the frozen eight consumer files"
        )
    for name in SNAPSHOT_FILES:
        path = snapshot / name
        if not path.is_file() or path.is_symlink():
            raise MoleRecProfileError(f"MoleRec snapshot input is not a regular file: {name}")


def _validate_binary_symmetric_ddi(ddi: Any, np: Any) -> None:
    if (
        ddi.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(ddi).all()
        or not np.isin(ddi, (0.0, 1.0)).all()
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
        or int(np.triu(ddi, 1).sum()) != 448
    ):
        raise MoleRecProfileError(
            "MoleRec DDI matrix is not finite binary symmetric zero-diagonal 131 by 131"
        )


def _validate_molecular_assets(
    snapshot: Path, voc: Mapping[str, Any], ddi: Any, dill: Any, np: Any
) -> None:
    mask = np.asarray(dill.load((snapshot / "ddi_mask_H.pkl").open("rb")))
    substructures = dill.load((snapshot / "substructure_smiles.pkl").open("rb"))
    molecule = dill.load((snapshot / "idx2SMILES.pkl").open("rb"))
    alias = snapshot / "idx2drug.pkl"
    if (
        mask.shape != (MEDICATIONS, 491)
        or not np.isfinite(mask).all()
        or not np.isin(mask, (0.0, 1.0)).all()
        or not isinstance(substructures, (list, tuple))
        or len(substructures) != 491
        or not isinstance(molecule, Mapping)
    ):
        raise MoleRecProfileError(
            "MoleRec molecular assets do not match the frozen 131 x 491 contract"
        )
    medication_codes = set(_vocabulary(voc))
    if not medication_codes.issubset({str(key) for key in molecule}):
        raise MoleRecProfileError("MoleRec idx2SMILES keys do not cover the frozen medication axis")
    if alias.read_bytes() != (snapshot / "idx2SMILES.pkl").read_bytes():
        raise MoleRecProfileError("MoleRec idx2drug.pkl is not byte-identical to idx2SMILES.pkl")
    _validate_binary_symmetric_ddi(ddi, np)
    ehr_adj = np.asarray(dill.load((snapshot / "ehr_adj_final.pkl").open("rb")))
    if (
        ehr_adj.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(ehr_adj).all()
        or not np.array_equal(ehr_adj, ehr_adj.T)
        or np.any(np.diag(ehr_adj) != 0)
    ):
        raise MoleRecProfileError(
            "MoleRec EHR adjacency is not a finite symmetric 131 by 131 matrix"
        )
    for name, expected_hash in SNAPSHOT_ASSET_HASHES.items():
        if _sha256(snapshot / name) != expected_hash:
            raise MoleRecProfileError(
                f"MoleRec snapshot asset hash does not match the frozen snapshot: {name}"
            )


def _membership_digest(indices: Sequence[int]) -> str:
    return hashlib.sha256(
        "".join(f"{int(index)}\n" for index in indices).encode("utf-8")
    ).hexdigest()


def _validate_selection_profile(profile: Mapping[str, Any]) -> None:
    selection = profile.get("selection", {})
    declared_points = tuple(float(value) for value in selection.get("operating_points", ()))
    if (
        declared_points != OPERATING_POINTS
        or float(selection.get("native_default", -1.0)) != NATIVE_DEFAULT
    ):
        raise MoleRecProfileError("MoleRec selection constants do not match the frozen profile")


def _load_inputs(snapshot: Path, train_dev: Path, dill: Any, np: Any) -> tuple[Any, ...]:
    if snapshot.name != SNAPSHOT_ID or train_dev.name != TRAIN_DEV_ID:
        raise MoleRecProfileError(
            "snapshot or Train/Dev root identity does not match the frozen profile"
        )
    _validate_snapshot_layout(snapshot)
    profile = json.loads(_profile_path().read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise MoleRecProfileError("MIII profile ID does not match the MoleRec adapter")
    if profile.get("benchmark", {}).get("source_snapshot_id") != SNAPSHOT_ID:
        raise MoleRecProfileError("MIII profile snapshot ID does not match the MoleRec adapter")
    _validate_selection_profile(profile)
    assets = profile.get("benchmark", {}).get("source_assets", {})
    for name in ("records_final.pkl", "voc_final.pkl", "ddi_A_final.pkl"):
        _validate_asset(snapshot / name, assets.get(name, {}), name)
    split = profile.get("split", {})
    target_paths = {
        "train": train_dev / "train_targets.npy",
        "dev": train_dev / "dev_targets.npy",
    }
    for role, path in target_paths.items():
        expected = split.get(role, {}).get("target_array_sha256")
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise MoleRecProfileError(f"{role} target array hash does not match the frozen profile")
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    vocabulary = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")))
    train_targets = np.asarray(np.load(target_paths["train"], allow_pickle=False), dtype=np.float32)
    dev_targets = np.asarray(np.load(target_paths["dev"], allow_pickle=False), dtype=np.float32)
    if len(records) != 6350 or ddi.shape != (MEDICATIONS, MEDICATIONS):
        raise MoleRecProfileError("canonical MIII snapshot shape changed")
    _validate_molecular_assets(snapshot, vocabulary, ddi, dill, np)
    return records, vocabulary, ddi, train_targets, dev_targets, profile


def _rows(records: Sequence[Any], patients: Sequence[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patient_index in patients:
        for visit_index, admission in enumerate(records[int(patient_index)]):
            target = sorted({int(value) for value in admission[2]})
            rows.append(
                {
                    "patient_id": str(int(patient_index)),
                    "visit_id": f"{int(patient_index)}:{visit_index}",
                    "target": target,
                }
            )
    return rows


def _target_free_prefix(patient: Sequence[Any], end: int) -> list[Any]:
    """Keep legal history while clearing the current visit's target channel."""
    prefix = list(patient[:end])
    if not prefix:
        return prefix
    current = prefix[-1]
    return [*prefix[:-1], [current[0], current[1], []]]


def _validate_targets(rows: Sequence[Mapping[str, Any]], targets: Any, label: str, np: Any) -> None:
    if targets.shape != (len(rows), MEDICATIONS):
        raise MoleRecProfileError(
            f"{label} targets are not aligned with the canonical [visits,131] surface"
        )
    if not np.isfinite(targets).all() or not np.isin(targets, (0.0, 1.0)).all():
        raise MoleRecProfileError(f"{label} targets are not finite binary values")
    for index, row in enumerate(rows):
        expected = np.zeros(MEDICATIONS, dtype=np.float32)
        expected[row["target"]] = 1.0
        if not np.array_equal(expected, targets[index]):
            raise MoleRecProfileError(f"{label} target mismatch at row {index}")


def _vocabulary(voc: Mapping[str, Any]) -> tuple[str, ...]:
    medication = voc["med_voc"]
    ids = {int(key) for key in medication.idx2word}
    if ids != set(range(MEDICATIONS)):
        raise MoleRecProfileError("MoleRec medication vocabulary is not the canonical 131 axis")
    return tuple(str(medication.idx2word[index]) for index in range(MEDICATIONS))


def _validate_vocabulary_and_records(
    records: Sequence[Any], voc: Mapping[str, Any], profile: Mapping[str, Any]
) -> tuple[int, int, tuple[str, ...]]:
    diagnosis = voc["diag_voc"]
    procedure = voc["pro_voc"]
    dx_ids = {int(key) for key in diagnosis.idx2word}
    procedure_ids = {int(key) for key in procedure.idx2word}
    if dx_ids != set(range(len(dx_ids))) or procedure_ids != set(range(len(procedure_ids))):
        raise MoleRecProfileError("MoleRec diagnosis/procedure IDs are not contiguous")
    vocabulary = _vocabulary(voc)
    sorted_digest = hashlib.sha256(
        "".join(f"{code}\n" for code in sorted(vocabulary)).encode("utf-8")
    ).hexdigest()
    expected_digest = profile["benchmark"]["medication_identity"][
        "canonical_sorted_vocabulary_sha256"
    ]
    if sorted_digest != expected_digest:
        raise MoleRecProfileError(
            "MoleRec medication vocabulary identity does not match the frozen profile"
        )
    if not isinstance(records, list) or len(records) != 6350:
        raise MoleRecProfileError("MoleRec records are not the canonical patient list")
    for patient_index, patient in enumerate(records):
        if not isinstance(patient, list) or not patient:
            raise MoleRecProfileError(f"MoleRec patient {patient_index} has no valid admissions")
        for visit_index, admission in enumerate(patient):
            if not isinstance(admission, list) or len(admission) != 3:
                raise MoleRecProfileError(
                    f"MoleRec visit {patient_index}:{visit_index} is malformed"
                )
            if any(int(code) not in dx_ids for code in admission[0]):
                raise MoleRecProfileError(
                    "MoleRec record contains a diagnosis outside its vocabulary"
                )
            if any(int(code) not in procedure_ids for code in admission[1]):
                raise MoleRecProfileError(
                    "MoleRec record contains a procedure outside its vocabulary"
                )
            if any(int(code) not in range(MEDICATIONS) for code in admission[2]):
                raise MoleRecProfileError(
                    "MoleRec record contains a medication outside the 131 axis"
                )
    return len(dx_ids), len(procedure_ids), vocabulary


def _ddi_pairs(vocabulary: Sequence[str], ddi: Any, np: Any) -> tuple[tuple[str, str], ...]:
    left, right = np.triu(ddi, 1).nonzero()
    return tuple(
        (vocabulary[int(a)], vocabulary[int(b)])
        for a, b in zip(left, right)  # noqa: B905
    )


def _profile_metrics(
    rows: Sequence[Mapping[str, Any]],
    targets: Any,
    logits: Any,
    threshold: float,
    vocabulary: Sequence[str],
    ddi: Any,
    np: Any,
) -> dict[str, Any]:
    probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))
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
    return evaluate(
        samples, vocabulary=tuple(vocabulary), ddi_pairs=_ddi_pairs(vocabulary, ddi, np)
    )


def _source_metrics(
    rows: Sequence[Mapping[str, Any]],
    targets: Any,
    logits: Any,
    ddi_path: Path,
    source_ddi_rate: Any,
    np: Any,
) -> dict[str, float]:
    probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))
    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        grouped.setdefault(str(row["patient_id"]), []).append(index)
    patient_scores = []
    patient_predictions: list[list[list[int]]] = []
    from sklearn.metrics import average_precision_score

    for patient_id in sorted(grouped, key=lambda value: int(value)):
        indices = grouped[patient_id]
        visit_scores = []
        predictions = []
        for index in indices:
            target = set(int(value) for value in np.flatnonzero(targets[index] > 0.5))
            predicted = list(
                int(value) for value in np.flatnonzero(probabilities[index] >= SOURCE_THRESHOLD)
            )
            predictions.append(predicted)
            intersection = len(target & set(predicted))
            union = len(target | set(predicted))
            precision = 0.0 if not predicted else intersection / float(len(predicted))
            recall = 0.0 if not target else intersection / float(len(target))
            f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            ap = float(
                average_precision_score(targets[index], probabilities[index], average="macro")
            )
            visit_scores.append(
                (0.0 if union == 0 else intersection / float(union), ap, precision, recall, f1)
            )
        patient_scores.append(tuple(np.asarray(visit_scores, dtype=np.float64).mean(axis=0)))
        patient_predictions.append(predictions)
    aggregate = np.asarray(patient_scores, dtype=np.float64).mean(axis=0)
    pooled_ddi_rate = source_ddi_rate(patient_predictions, path=str(ddi_path))
    stable_nll = np.maximum(logits, 0.0) - logits * targets + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": float(aggregate[0]),
        "prauc": float(aggregate[1]),
        "avg_precision": float(aggregate[2]),
        "avg_recall": float(aggregate[3]),
        "avg_f1": float(aggregate[4]),
        "ddi_rate": float(pooled_ddi_rate),
        "mean_medication_count": float(np.mean((probabilities >= SOURCE_THRESHOLD).sum(axis=1))),
        "loss": float(stable_nll.mean()),
    }


def _predict(
    model: Any, patients: Sequence[Any], drug_data: Mapping[str, Any], torch: Any, np: Any
) -> Any:
    values = []
    model.eval()
    with torch.no_grad():
        for patient in patients:
            for visit_index in range(len(patient)):
                score, _ = model(
                    patient_data=_target_free_prefix(patient, visit_index + 1), **drug_data
                )
                values.append(score.detach().cpu().numpy()[0])
    logits = np.asarray(values, dtype=np.float32)
    if (
        logits.shape != (sum(len(patient) for patient in patients), MEDICATIONS)
        or not np.isfinite(logits).all()
    ):
        raise MoleRecProfileError("MoleRec logits are not finite [visits,131] values")
    return logits


def _seed(seed: int, torch: Any, np: Any) -> None:
    if seed != 1203:
        raise MoleRecProfileError("the pinned MoleRec profile permits only source seed 1203")
    torch.manual_seed(seed)
    np.random.seed(2048)
    random.seed(seed)
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


def _preflight_model(
    model: Any, patient: Sequence[Any], drug_data: Mapping[str, Any], torch: Any, np: Any
) -> None:
    if not patient:
        raise MoleRecProfileError("MoleRec preflight patient is empty")
    model.eval()
    with torch.no_grad():
        output, _ = model(patient_data=_target_free_prefix(patient, 1), **drug_data)
    values = output.detach().cpu().numpy()
    if values.shape != (1, MEDICATIONS) or not np.isfinite(values).all():
        raise MoleRecProfileError("MoleRec preflight produced invalid logits")


def run(args: argparse.Namespace) -> dict[str, Any]:
    dill, np, torch = _runtime_modules()
    repo_root = Path(__file__).resolve().parents[1]
    harness_revision = _git_output(repo_root, "rev-parse", "HEAD")
    if _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise MoleRecProfileError("MoleRec harness checkout is not clean")
    source_root = args.source_root.resolve()
    _require_clean_git(source_root, SOURCE_REVISION, "MoleRec source")
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise MoleRecProfileError("output directory is not empty")
    identity = identity_from_environment(mode=args.mode, error_type=MoleRecProfileError)
    if identity is None:
        raise MoleRecProfileError("profile execution requires a controller-issued v2 identity")
    expected_identity = {
        "scientific_baseline_id": "molerec",
        "program_id": PROGRAM_ID,
        "profile_id": PROFILE_ID,
        "harness_revision": harness_revision,
        "model_source_revision": SOURCE_REVISION,
        "preprocessing_revision": PREPROCESSING_REVISION,
        "snapshot_id": SNAPSHOT_ID,
        "environment_sha256": ENVIRONMENT_SHA256,
    }
    for field, expected in expected_identity.items():
        if identity[field] != expected:
            raise MoleRecProfileError(
                f"controller identity {field} does not match the MoleRec profile"
            )
    records, voc, ddi, train_targets, dev_targets, profile = _load_inputs(
        snapshot, train_dev, dill, np
    )
    train_patients, dev_patients = patient_split(len(records))
    split = profile["split"]
    if (
        _membership_digest(train_patients) != split["train"]["membership_digest"]
        or _membership_digest(dev_patients) != split["dev"]["membership_digest"]
    ):
        raise MoleRecProfileError("MoleRec patient split does not match the frozen profile")
    train_data = [records[index] for index in train_patients]
    dev_data = [records[index] for index in dev_patients]
    train_rows = _rows(records, train_patients)
    dev_rows = _rows(records, dev_patients)
    diagnosis_count, procedure_count, vocabulary = _validate_vocabulary_and_records(
        records, voc, profile
    )
    _validate_targets(train_rows, train_targets, "Train", np)
    _validate_targets(dev_rows, dev_targets, "Dev", np)
    if (len(train_rows), len(dev_rows)) != (10489, 2130):
        raise MoleRecProfileError("frozen Train/Dev visit counts changed")
    if args.device == "auto":
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if args.mode == "formal" and device.type != "cuda":
        raise MoleRecProfileError("formal MoleRec profile training requires CUDA")
    _seed(args.seed, torch, np)
    source_code = source_root / "src"
    sys.path.insert(0, str(source_code))
    try:
        from modules import MoleRecModel
        from modules.gnn import graph_batch_from_smile
        from util import buildPrjSmiles, ddi_rate_score
    except ImportError as error:
        raise MoleRecProfileError("pinned MoleRec source cannot import model modules") from error
    ddi_mask = np.asarray(dill.load((snapshot / "ddi_mask_H.pkl").open("rb")))
    molecule = dill.load((snapshot / "idx2SMILES.pkl").open("rb"))
    substructure_smiles = dill.load((snapshot / "substructure_smiles.pkl").open("rb"))
    average_projection, smiles_list = buildPrjSmiles(molecule, voc["med_voc"].idx2word)
    molecule_graphs = graph_batch_from_smile(smiles_list)
    substructure_graphs = graph_batch_from_smile(substructure_smiles)
    molecule_para = {
        "num_layer": 4,
        "emb_dim": 64,
        "graph_pooling": "mean",
        "drop_ratio": 0.7,
        "gnn_type": "gin",
        "virtual_node": False,
    }
    substructure_para = dict(molecule_para)
    drug_data = {
        "substruct_data": {"batched_data": substructure_graphs.to(device)},
        "mol_data": {"batched_data": molecule_graphs.to(device)},
        "ddi_mask_H": torch.as_tensor(ddi_mask, device=device),
        "tensor_ddi_adj": torch.as_tensor(ddi, device=device),
        "average_projection": average_projection.to(device),
    }
    model = MoleRecModel(
        global_para=molecule_para,
        substruct_para=substructure_para,
        emb_dim=64,
        global_dim=64,
        substruct_dim=64,
        substruct_num=int(ddi_mask.shape[1]),
        voc_size=(diagnosis_count, procedure_count, MEDICATIONS),
        use_embedding=False,
        device=device,
        dropout=0.7,
    ).to(device)
    parameter_count = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    if parameter_count != EXPECTED_PARAMETER_COUNT:
        raise MoleRecProfileError(f"pinned MoleRec parameter count changed: {parameter_count}")
    _preflight_model(model, dev_data[0], drug_data, torch, np)
    numeric_policy = _numeric_policy(torch)
    if args.preflight_only:
        return {
            "status": "PASS",
            "preflight_only": True,
            "baseline_id": "molerec",
            "program_id": PROGRAM_ID,
            "profile_id": PROFILE_ID,
            "source_revision": SOURCE_REVISION,
            "preprocessing_revision": PREPROCESSING_REVISION,
            "harness_revision": harness_revision,
            "environment_sha256": ENVIRONMENT_SHA256,
            "diagnosis_count": diagnosis_count,
            "procedure_count": procedure_count,
            "parameter_count": parameter_count,
            "split": {
                "train_patients": len(train_patients),
                "dev_patients": len(dev_patients),
                "train_visits": len(train_rows),
                "dev_visits": len(dev_rows),
            },
            "numeric_policy": numeric_policy,
            "test_loaded": False,
        }
    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4)
    output.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC).isoformat()
    requested_epochs = 1 if args.mode == "smoke" else EPOCHS
    config = {
        "profile_id": PROFILE_ID,
        "source_revision": SOURCE_REVISION,
        "seed": args.seed,
        "torch_seed": args.seed,
        "numpy_seed": 2048,
        "hidden_dim": 64,
        "dropout": 0.7,
        "learning_rate": 5e-4,
        "coef": 2.5,
        "target_ddi": 0.06,
        "loss": "official BCE + multi-label-margin + DDI annealing",
        "optimizer": "Adam(lr=5e-4)",
        "update_granularity": "one optimizer update per admission/visit",
        "target_free_forward": "current admission medication channel cleared; prior channel retained",
        "source_validation_threshold": SOURCE_THRESHOLD,
        "operating_points": list(OPERATING_POINTS),
        "native_default": NATIVE_DEFAULT,
        "checkpoint_selection": "joint Dev patient-macro Jaccard and operating point",
        "model_medication_history_consumed": False,
        "substructure_representation": "released GNN path (use_embedding=False)",
        "source_default_operating_point": SOURCE_THRESHOLD,
        "profile_native_default": NATIVE_DEFAULT,
        "molecular_assets": [
            "idx2SMILES.pkl",
            "substructure_smiles.pkl",
            "ddi_mask_H.pkl",
            "ddi_A_final.pkl",
        ],
        "ehr_adj_consumed_by_pinned_forward": False,
        "numeric_policy": numeric_policy,
        "snapshot_asset_hashes": {name: _sha256(snapshot / name) for name in SNAPSHOT_FILES},
    }
    state = {
        "schema_version": 2,
        "kind": "molerec_profile_progress",
        "identity": dict(identity),
        "mode": args.mode,
        "state": "training",
        "non_evidence": args.mode != "formal",
        "started_at": started_at,
        "config": config,
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_rows),
            "dev_visits": len(dev_rows),
            "train_membership_digest": _membership_digest(train_patients),
            "dev_membership_digest": _membership_digest(dev_patients),
            "train_target_array_sha256": _sha256(train_dev / "train_targets.npy"),
            "dev_target_array_sha256": _sha256(train_dev / "dev_targets.npy"),
        },
        "test_loaded": False,
        "evaluations": [],
    }
    write_json_atomic(output / "progress.json", state)
    best_candidate: SelectionCandidate | None = None
    best_state: dict[str, Any] | None = None
    best_dev_logits = None
    start_time = time.time()
    try:
        for epoch in range(1, requested_epochs + 1):
            model.train()
            train_loss_sum = 0.0
            update_count = 0
            for patient in train_data:
                for adm_idx, admission in enumerate(patient):
                    bce_target = torch.zeros((1, MEDICATIONS), device=device)
                    bce_target[:, admission[2]] = 1
                    multi_target = -torch.ones((1, MEDICATIONS), dtype=torch.long, device=device)
                    for index, item in enumerate(admission[2]):
                        multi_target[0][index] = item
                    result, loss_ddi = model(
                        patient_data=_target_free_prefix(patient, adm_idx + 1), **drug_data
                    )
                    sigmoid_result = torch.sigmoid(result)
                    loss_bce = torch.nn.functional.binary_cross_entropy_with_logits(
                        result, bce_target
                    )
                    loss_multi = torch.nn.functional.multilabel_margin_loss(
                        sigmoid_result, multi_target
                    )
                    labels = np.flatnonzero(
                        sigmoid_result.detach().cpu().numpy()[0] >= SOURCE_THRESHOLD
                    ).tolist()
                    current_ddi = ddi_rate_score([[labels]], path=str(snapshot / "ddi_A_final.pkl"))
                    if current_ddi <= 0.06:
                        loss = 0.95 * loss_bce + 0.05 * loss_multi
                    else:
                        beta = min(math.exp(2.5 * (1 - (current_ddi / 0.06))), 1)
                        loss = beta * (0.95 * loss_bce + 0.05 * loss_multi) + (1 - beta) * loss_ddi
                    if not torch.isfinite(loss):
                        raise MoleRecProfileError("MoleRec training loss is non-finite")
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    train_loss_sum += float(loss.detach().item())
                    update_count += 1
            dev_logits = _predict(model, dev_data, drug_data, torch, np)
            source_validation = _source_metrics(
                dev_rows,
                dev_targets,
                dev_logits,
                snapshot / "ddi_A_final.pkl",
                ddi_rate_score,
                np,
            )
            candidates = []
            candidate_results = []
            for op_index, operating_point in enumerate(OPERATING_POINTS):
                metrics = _profile_metrics(
                    dev_rows, dev_targets, dev_logits, operating_point, vocabulary, ddi, np
                )
                candidates.append(
                    SelectionCandidate(
                        checkpoint=epoch,
                        operating_point=operating_point,
                        patient_macro_jaccard=float(metrics["jaccard"]),
                        operating_point_index=op_index,
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
                candidates, operating_point_order=OPERATING_POINTS, native_default=NATIVE_DEFAULT
            )
            if best_candidate is None or (
                -epoch_best.patient_macro_jaccard,
                abs(epoch_best.operating_point - NATIVE_DEFAULT),
                epoch_best.operating_point_index,
                epoch_best.checkpoint,
            ) < (
                -best_candidate.patient_macro_jaccard,
                abs(best_candidate.operating_point - NATIVE_DEFAULT),
                best_candidate.operating_point_index,
                best_candidate.checkpoint,
            ):
                best_candidate = epoch_best
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                best_dev_logits = dev_logits.copy()
                torch.save(best_state, output / "selected_checkpoint.pt")
                np.save(output / "selected_dev_logits.npy", best_dev_logits.astype(np.float32))
            entry = {
                "epoch": epoch,
                "train_loss": train_loss_sum / update_count,
                "updates": update_count,
                "source_validation": source_validation,
                "selected_operating_point_this_epoch": epoch_best.operating_point,
                "selected_dev_jaccard_this_epoch": epoch_best.patient_macro_jaccard,
                "candidate_operating_points": candidate_results,
                "elapsed_seconds": time.time() - start_time,
            }
            state["evaluations"].append(entry)
            state["completed_epochs"] = epoch
            state["selected_checkpoint"] = best_candidate.checkpoint
            state["selected_operating_point"] = best_candidate.operating_point
            write_json_atomic(output / "progress.json", state)
            print(
                json.dumps(
                    {
                        "baseline": "molerec-profile",
                        "epoch": epoch,
                        "source_prauc": source_validation["prauc"],
                        "selected_dev_jaccard": epoch_best.patient_macro_jaccard,
                        "selected_operating_point": epoch_best.operating_point,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        if best_candidate is None or best_state is None or best_dev_logits is None:
            raise MoleRecProfileError("MoleRec did not produce a complete Dev checkpoint")
        model.load_state_dict(best_state)
        train_logits = _predict(model, train_data, drug_data, torch, np)
        selected_train = _profile_metrics(
            train_rows,
            train_targets,
            train_logits,
            float(best_candidate.operating_point),
            vocabulary,
            ddi,
            np,
        )
        selected_dev = _profile_metrics(
            dev_rows,
            dev_targets,
            best_dev_logits,
            float(best_candidate.operating_point),
            vocabulary,
            ddi,
            np,
        )
        predicted_count = float(selected_dev["average_medication_count"])
        if not math.isfinite(predicted_count) or not 0.0 < predicted_count < MEDICATIONS:
            raise MoleRecProfileError(
                "MoleRec selected Dev predictions are collapsed or out of range"
            )
        checkpoint = output / "selected_checkpoint.pt"
        payload = {
            "artifact_type": "training",
            "scientific_baseline_id": "molerec",
            "profile_id": PROFILE_ID,
            "snapshot_id": SNAPSHOT_ID,
            "train_dev_id": TRAIN_DEV_ID,
            "source_revision": SOURCE_REVISION,
            "preprocessing_revision": PREPROCESSING_REVISION,
            "harness_revision": harness_revision,
            "environment_sha256": ENVIRONMENT_SHA256,
            "program_id": PROGRAM_ID,
            "seed": args.seed,
            "mode": args.mode,
            "config": config,
            "parameter_count": parameter_count,
            "split": state["split"],
            "epochs_requested": requested_epochs,
            "epochs_observed": len(state["evaluations"]),
            "source_early_stop": False,
            "selection": {
                "checkpoint": best_candidate.checkpoint,
                "operating_point": best_candidate.operating_point,
                "metric": "Dev patient-macro Jaccard",
                "score": best_candidate.patient_macro_jaccard,
                "rule": "all declared operating points at every observed checkpoint",
            },
            "metrics": {"Train": selected_train, "Dev": selected_dev},
            "runtime": {
                "python": sys.version.split()[0],
                "torch": torch.__version__,
                "numpy": np.__version__,
                "wall_time_seconds": time.time() - start_time,
            },
            "checkpoint": {
                "relative_path": "selected_checkpoint.pt",
                "sha256": _sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
            },
            "test_loaded": False,
            "test_evaluation": False,
        }
        state.update({"state": "complete", "finished_at": datetime.now(UTC).isoformat()})
        write_json_atomic(output / "progress.json", state)
        finalize_v2_pair(
            output,
            status=terminal_status(
                identity,
                state="completed",
                started_at=started_at,
                finished_at=state["finished_at"],
                non_evidence=args.mode != "formal",
            ),
            result=terminal_result(
                identity, state="completed", non_evidence=args.mode != "formal", payload=payload
            ),
            error_type=MoleRecProfileError,
        )
        return payload
    except Exception:
        write_failure_pair(
            root=output,
            identity=identity,
            started_at=started_at,
            artifact_type="training",
            error_type=MoleRecProfileError,
            non_evidence=args.mode != "formal",
        )
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1203)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--mode", choices=("formal", "smoke"), default="formal")
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
