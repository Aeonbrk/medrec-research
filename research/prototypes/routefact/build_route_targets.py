#!/usr/bin/env python3
"""Build Train-only-frozen multi-hot medication-route targets for RouteFact.

The route vocabulary, medication-route support mask, and route supervision are
derived from Train prescription rows only. Dev raw route labels are not read as
training/evaluation inputs; Dev uses only the frozen canonical medication targets.
No Test resource is read. Outputs are private run assets and must remain outside Git.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Set, Tuple

import dill
import numpy as np
import pandas as pd

MEDICATIONS = 131
PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"
UNSPECIFIED_ROUTE = "<UNSPECIFIED_ROUTE>"
PRESCRIPTION_COLUMNS = ("SUBJECT_ID", "HADM_ID", "NDC", "ROUTE")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text in {"", "nan", "NaN", "<NA>", "None"} else text


def _as_int(value: Any) -> Optional[int]:
    text = _clean(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return None


def _normalize_route(value: Any) -> str:
    text = _clean(value).upper()
    return re.sub(r"\s+", " ", text) if text else UNSPECIFIED_ROUTE


def _normalize_ndc(value: Any) -> str:
    text = _clean(value)
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"[^0-9]", "", text)
    if not digits or set(digits) == {"0"}:
        return ""
    return digits


def _ndc_keys(value: Any) -> Tuple[str, ...]:
    token = _normalize_ndc(value)
    return () if not token else (token, token.zfill(11))


def _rxnorm_key(value: Any) -> str:
    return re.sub(r"[^0-9]", "", _clean(value))


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


def _require_clean_source(root: Path, revision: str) -> None:
    if _git_revision(root) != revision:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("source checkout is not clean")


def _is_dev(patient_id: int) -> bool:
    digest = hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


def _table_path(root: Path) -> Path:
    for name in ("PRESCRIPTIONS.csv.gz", "PRESCRIPTIONS.csv"):
        path = root / name
        if path.is_file():
            return path
    raise RuntimeError("MIMIC-III PRESCRIPTIONS table not found")


def _word(indexed: Any, index: int) -> str:
    try:
        return str(indexed[index])
    except (KeyError, IndexError):
        return str(indexed[str(index)])


def _build_ndc_to_atc4(mapping_dir: Path) -> Tuple[Dict[str, str], int]:
    atc_path = mapping_dir / "ndc2atc_level4.csv"
    rx_path = mapping_dir / "ndc2rxnorm_mapping.txt"
    if not atc_path.is_file() or not rx_path.is_file():
        raise RuntimeError("required SafeDrug NDC mapping assets are missing")
    rxnorm_to_atc: Dict[str, str] = {}
    frame = pd.read_csv(atc_path, dtype="string", usecols=["RXCUI", "ATC5"])
    for row in frame.itertuples(index=False):
        rxnorm = _rxnorm_key(row.RXCUI)
        atc = _clean(row.ATC5).upper()[:4]
        if rxnorm and len(atc) == 4:
            rxnorm_to_atc.setdefault(rxnorm, atc)
    raw = ast.literal_eval(rx_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("ndc2rxnorm_mapping.txt is not a mapping")
    candidates: Dict[str, Set[str]] = collections.defaultdict(set)
    for ndc, rxnorm in raw.items():
        atc = rxnorm_to_atc.get(_rxnorm_key(rxnorm))
        if atc:
            for key in _ndc_keys(ndc):
                candidates[key].add(atc)
    mapping = {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}
    ambiguous = sum(len(values) > 1 for values in candidates.values())
    return mapping, int(ambiguous)


@dataclass(frozen=True)
class VisitRef:
    split: str
    index: int
    medication_ids: frozenset[int]


def _build_visit_index(
    records: Sequence[Any],
    data_final: pd.DataFrame,
    train_targets: np.ndarray,
    dev_targets: np.ndarray,
) -> Tuple[Dict[Tuple[int, int], VisitRef], Tuple[int, ...], Tuple[int, ...]]:
    subjects = tuple(int(value) for value in data_final["SUBJECT_ID"].drop_duplicates().tolist())
    if len(subjects) != len(records):
        raise RuntimeError("data_final subject order does not match records_final")
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(i for i in range(split, len(records)) if _is_dev(i))
    if (len(train_patients), len(dev_patients)) != (4233, 1004):
        raise RuntimeError("frozen Train/Dev patient counts changed")
    visit_index: Dict[Tuple[int, int], VisitRef] = {}
    counters = {"train": 0, "dev": 0}
    train_set = set(train_patients)
    dev_set = set(dev_patients)
    for patient_index in (*train_patients, *dev_patients):
        subject = subjects[patient_index]
        hadms = [
            int(value)
            for value in data_final.loc[data_final["SUBJECT_ID"] == subject, "HADM_ID"].tolist()
        ]
        if len(hadms) != len(records[patient_index]):
            raise RuntimeError("data_final visit order/count does not match records_final")
        role = "train" if patient_index in train_set else "dev"
        if patient_index not in train_set and patient_index not in dev_set:
            continue
        for visit_order, hadm in enumerate(hadms):
            meds = frozenset(int(value) for value in records[patient_index][visit_order][2])
            row_index = counters[role]
            counters[role] += 1
            visit_index[(subject, hadm)] = VisitRef(role, row_index, meds)
            target = train_targets[row_index] if role == "train" else dev_targets[row_index]
            expected = np.zeros(MEDICATIONS, dtype=np.uint8)
            expected[list(meds)] = 1
            if not np.array_equal(expected, np.asarray(target > 0.5, dtype=np.uint8)):
                raise RuntimeError("canonical medication target alignment failed")
    if counters["train"] != len(train_targets) or counters["dev"] != len(dev_targets):
        raise RuntimeError("visit index does not cover Train/Dev target arrays")
    return visit_index, train_patients, dev_patients


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, path)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    _require_clean_source(repo_root, args.source_revision)
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    if snapshot.name != SNAPSHOT_ID or train_dev.name != TRAIN_DEV_ID:
        raise RuntimeError("snapshot/TrainDev identities do not match the frozen profile")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    train_targets = np.asarray(np.load(train_dev / "train_targets.npy", mmap_mode="r"))
    dev_targets = np.asarray(np.load(train_dev / "dev_targets.npy", mmap_mode="r"))
    if train_targets.shape != (10489, MEDICATIONS) or dev_targets.shape != (2130, MEDICATIONS):
        raise RuntimeError("frozen medication target shapes changed")
    data_final = dill.load(args.canonical_data.open("rb"))
    if not isinstance(data_final, pd.DataFrame) or not {"SUBJECT_ID", "HADM_ID"} <= set(data_final.columns):
        raise RuntimeError("canonical data_final provenance is malformed")
    visit_index, train_patients, dev_patients = _build_visit_index(
        records, data_final, train_targets, dev_targets
    )

    med_voc = voc["med_voc"]
    medication_codes = tuple(_word(med_voc.idx2word, i) for i in range(MEDICATIONS))
    if len(set(medication_codes)) != MEDICATIONS:
        raise RuntimeError("canonical medication vocabulary is malformed")
    medication_index = {code: i for i, code in enumerate(medication_codes)}
    ndc_to_atc, ambiguous_mapping_keys = _build_ndc_to_atc4(args.mapping_dir)

    route_sets: Dict[Tuple[int, int], Set[str]] = collections.defaultdict(set)
    route_row_counts: collections.Counter[str] = collections.Counter()
    stats = collections.Counter()
    prescriptions = _table_path(args.mimic_root)
    dtype = {column: "string" for column in PRESCRIPTION_COLUMNS}
    for chunk in pd.read_csv(
        prescriptions,
        usecols=list(PRESCRIPTION_COLUMNS),
        dtype=dtype,
        compression="infer",
        chunksize=args.chunk_size,
        low_memory=False,
    ):
        for row in chunk.itertuples(index=False):
            subject = _as_int(row.SUBJECT_ID)
            hadm = _as_int(row.HADM_ID)
            if subject is None or hadm is None:
                continue
            ref = visit_index.get((subject, hadm))
            if ref is None:
                continue
            if ref.split != "train":
                continue
            stats["train_selected_rows"] += 1
            ndc = _normalize_ndc(row.NDC)
            atc = ndc_to_atc.get(ndc) or ndc_to_atc.get(ndc.zfill(11) if ndc else "")
            med = medication_index.get(atc or "")
            if med is None:
                continue
            stats["train_canonical_rows"] += 1
            if med not in ref.medication_ids:
                stats["train_mapped_rows_not_in_target"] += 1
                continue
            route = _normalize_route(row.ROUTE)
            route_sets[(ref.index, med)].add(route)
            route_row_counts[route] += 1

    train_real_routes = sorted(
        route
        for route, count in route_row_counts.items()
        if count > 0 and route != UNSPECIFIED_ROUTE
    )
    route_vocabulary = (UNSPECIFIED_ROUTE, *train_real_routes)
    route_to_index = {route: i for i, route in enumerate(route_vocabulary)}
    route_count = len(route_vocabulary)
    allowed = np.zeros((MEDICATIONS, route_count), dtype=np.uint8)
    for (_visit_index_value, med), routes in route_sets.items():
        for route in routes:
            route_idx = route_to_index.get(route)
            if route_idx is not None and route_idx != 0:
                allowed[med, route_idx] = 1

    # The unspecified coordinate is not a universal shortcut. It is enabled
    # only for medications with at least one positive Train pair that cannot be
    # expressed by a real Train-observed route, or for a medication with no
    # real Train route coordinate at all.
    for row_index in range(len(train_targets)):
        for med_value in np.flatnonzero(train_targets[row_index] > 0.5):
            med = int(med_value)
            routes = route_sets.get((row_index, med), set())
            has_real_supported = any(route_to_index.get(route, 0) > 0 for route in routes)
            if not has_real_supported:
                allowed[med, 0] = 1
    for med in range(MEDICATIONS):
        if not allowed[med].any():
            allowed[med, 0] = 1

    train_route_targets = np.zeros(
        (len(train_targets), MEDICATIONS, route_count), dtype=np.uint8
    )
    fallback_count = 0
    for row_index in range(len(train_targets)):
        positive_meds = np.flatnonzero(train_targets[row_index] > 0.5)
        for med_value in positive_meds:
            med = int(med_value)
            routes = route_sets.get((row_index, med), set())
            emitted = False
            for route in routes:
                route_idx = route_to_index.get(route)
                if route_idx is not None and allowed[med, route_idx]:
                    train_route_targets[row_index, med, route_idx] = 1
                    emitted = True
            if not emitted:
                if not allowed[med, 0]:
                    raise RuntimeError("Train positive medication has no legal route target")
                train_route_targets[row_index, med, 0] = 1
                fallback_count += 1
    medication_presence = np.asarray(train_targets > 0.5, dtype=np.uint8)
    if np.any(train_route_targets > medication_presence[..., None]):
        raise RuntimeError("route target implies an absent medication")
    positive_route_counts = train_route_targets.sum(axis=2)
    if np.any((medication_presence > 0) & (positive_route_counts == 0)):
        raise RuntimeError("a Train positive medication has no route target")
    if np.any((medication_presence == 0) & (positive_route_counts != 0)):
        raise RuntimeError("an absent medication has a positive route target")

    np.save(output / "train_route_targets.npy", train_route_targets, allow_pickle=False)
    np.save(output / "allowed_route_mask.npy", allowed, allow_pickle=False)
    route_vocabulary_path = output / "route_vocabulary.json"
    _write_json(route_vocabulary_path, {"routes": list(route_vocabulary)})
    assets = {}
    for name in (
        "train_route_targets.npy",
        "allowed_route_mask.npy",
        "route_vocabulary.json",
    ):
        path = output / name
        assets[name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}

    train_positive_pairs = int(np.asarray(train_targets > 0.5, dtype=np.uint8).sum())
    result: Dict[str, Any] = {
        "schema_version": 1,
        "status": "complete",
        "profile_id": PROFILE_ID,
        "source_revision": args.source_revision,
        "route_semantics": "multi-hot admission-level route set conditional on canonical medication target",
        "route_vocabulary_source": "Train only",
        "medication_route_support_mask_source": "Train only",
        "raw_route_scope": "Train admissions only; Dev raw route labels not read",
        "route_count": route_count,
        "train_real_route_count": len(train_real_routes),
        "split": {
            "train_patients": len(train_patients),
            "dev_patients": len(dev_patients),
            "train_visits": len(train_targets),
            "dev_visits": len(dev_targets),
        },
        "positive_medication_pairs": {"train": train_positive_pairs},
        "fallback_positive_pairs": {"train": int(fallback_count)},
        "medications_with_unspecified_route_enabled": int(allowed[:, 0].sum()),
        "allowed_route_coordinates": int(allowed.sum()),
        "ambiguous_mapping_keys_excluded": ambiguous_mapping_keys,
        "raw_alignment_counts": dict(stats),
        "assets": assets,
        "test_loaded": False,
    }
    _write_json(output / "metadata.json", result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--canonical-data", type=Path, required=True)
    parser.add_argument("--mimic-root", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--chunk-size", type=int, default=250000)
    return parser.parse_args(argv)


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
