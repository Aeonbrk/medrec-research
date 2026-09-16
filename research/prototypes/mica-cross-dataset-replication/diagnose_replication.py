#!/usr/bin/env python3
# ruff: noqa: UP006,UP035,UP045,I001
"""No-training Train/Dev diagnostics for the Stage -1F replication screen."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import dill
import numpy as np

REPLICATION_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = REPLICATION_DIR.parents[1] / "benchmarks" / "mimiciv-medrec"
sys.path.insert(0, str(ADAPTER_DIR))

from materialize_mimiciv import (  # noqa: E402
    freeze_formulary_rules,
    iter_selected_rows,
    load_admissions,
    load_atc_mapping,
    load_kgd_mapping,
    load_ndc_rxnorm,
    normalise_ndc,
    normalise_formulary,
    resolve_medication,
    prescription_pass,
)

SPLIT_SNAPSHOT = "molerec-table1-c721-www23"
SPLIT_TRAIN_DEV = "gate01-train-dev-5752596a-20260913a"
IV_PRIVATE_ROOT = "mimiciv-medrec-stage-1e-private-e87411be"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def _histogram(values: Iterable[int]) -> Dict[str, Any]:
    counts = Counter(int(value) for value in values)
    total = sum(counts.values())
    ordered = dict((str(key), counts[key]) for key in sorted(counts))
    return {
        "count": total,
        "histogram": ordered,
        "min": min(counts) if counts else None,
        "max": max(counts) if counts else None,
        "mean": float(sum(key * value for key, value in counts.items()) / total) if total else None,
        "median": float(np.median(np.repeat(list(counts), list(counts.values()))))
        if total
        else None,
    }


def _coverage_summary(cardinalities: Sequence[int], coverage: Sequence[float]) -> Dict[str, Any]:
    if len(cardinalities) != len(coverage):
        raise RuntimeError("normalization diagnostic arrays are misaligned")
    if not cardinalities:
        return {"status": "UNAVAILABLE", "reason": "no eligible target visits"}
    cards = np.asarray(cardinalities, dtype=np.float64)
    cov = np.asarray(coverage, dtype=np.float64)
    if not np.isfinite(cov).all() or np.any(cov < 0.0) or np.any(cov > 1.0):
        raise RuntimeError("normalization coverage is not finite in [0,1]")
    card_stats = _histogram(int(value) for value in cardinalities)
    corr: Optional[float]
    corr_status = "PASS"
    if len(cards) < 2:
        corr = None
        corr_status = "UNDEFINED_TOO_FEW_VISITS"
    elif float(cards.std()) == 0.0 or float(cov.std()) == 0.0:
        corr = None
        corr_status = "UNDEFINED_CONSTANT_INPUT"
    else:
        corr = float(np.corrcoef(cards, cov)[0, 1])
    return {
        "status": "AVAILABLE",
        "visits": len(cardinalities),
        "target_cardinality": card_stats,
        "normalization_coverage": {
            "mean": float(cov.mean()),
            "median": float(np.median(cov)),
            "min": float(cov.min()),
            "max": float(cov.max()),
            "p10": float(np.quantile(cov, 0.10)),
            "p90": float(np.quantile(cov, 0.90)),
        },
        "target_cardinality_vs_normalization_coverage": {
            "pearson_r": corr,
            "status": corr_status,
        },
    }


def _mimic_iii_target_cardinality(
    snapshot: Path, train_dev: Path
) -> Tuple[List[int], List[int], List[List[Any]], List[int], List[int]]:
    if snapshot.name != SPLIT_SNAPSHOT or train_dev.name != SPLIT_TRAIN_DEV:
        raise RuntimeError("MIMIC-III roots do not match the canonical MICA contract")
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    train_targets = np.asarray(np.load(train_dev / "train_targets.npy", mmap_mode="r"))
    dev_targets = np.asarray(np.load(train_dev / "dev_targets.npy", mmap_mode="r"))
    train_cards = [int(value) for value in train_targets.sum(axis=1)]
    dev_cards = [int(value) for value in dev_targets.sum(axis=1)]
    split = int(len(records) * 2 / 3)
    train_patients = list(range(split))
    dev_patients = [index for index in range(split, len(records)) if _gate01_dev(index)]
    return train_cards, dev_cards, records, train_patients, dev_patients


def _gate01_dev(patient_id: int) -> bool:
    import hashlib

    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _mimic_iii_raw_coverage(
    raw_root: Path,
    data_final: Path,
    mapping_dir: Path,
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    train_patients: Sequence[int],
    dev_patients: Sequence[int],
) -> Dict[str, Any]:
    """Compute row coverage for the exact snapshot subjects when raw provenance exists."""

    try:
        data = dill.load(data_final.open("rb"))
        subjects = [int(value) for value in data["SUBJECT_ID"].drop_duplicates().tolist()]
    except (OSError, KeyError, TypeError, AttributeError, ValueError) as exc:
        return {
            "status": "UNAVAILABLE",
            "reason": "cannot load canonical data_final provenance: " + type(exc).__name__,
        }
    if len(subjects) != len(records):
        return {
            "status": "UNAVAILABLE",
            "reason": "data_final subject count does not match records_final; no alignment assumed",
        }
    train_patient_set = set(int(value) for value in train_patients)
    ndc_rxnorm = load_ndc_rxnorm(mapping_dir / "ndc2rxnorm_mapping.txt")
    _ndc_direct, rxnorm_atc, _meta = load_atc_mapping(mapping_dir / "ndc2atc_level4.csv")
    allowed_hadm: Dict[int, str] = {}
    target_cards: Dict[int, int] = {}
    # data_final is sorted by subject/hadm in the canonical MoleRec pipeline.
    for patient_index in (*train_patients, *dev_patients):
        subject = subjects[int(patient_index)]
        role = "train" if int(patient_index) in train_patient_set else "dev"
        patient_data = data[data["SUBJECT_ID"] == subject]
        patient_hadm = [int(value) for value in patient_data["HADM_ID"].tolist()]
        if len(patient_hadm) != len(records[int(patient_index)]):
            return {
                "status": "UNAVAILABLE",
                "reason": "data_final visit order/count does not match records_final",
            }
        for visit_index, hadm in enumerate(patient_hadm):
            allowed_hadm[hadm] = role
            target_cards[hadm] = len(records[int(patient_index)][visit_index][2])
    eligible: Counter[int] = Counter()
    mapped: Counter[int] = Counter()
    with gzip.open(raw_root / "PRESCRIPTIONS.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"SUBJECT_ID", "HADM_ID", "NDC"}
        if not required <= set(reader.fieldnames or []):
            return {
                "status": "UNAVAILABLE",
                "reason": "MIMIC-III prescription schema lacks NDC linkage",
            }
        for row in reader:
            try:
                hadm = int(str(row.get("HADM_ID", "")).strip())
            except ValueError:
                continue
            if hadm not in allowed_hadm:
                continue
            ndc = normalise_ndc(row.get("NDC"))
            if not ndc:
                continue
            eligible[hadm] += 1
            rxnorm = ndc_rxnorm.get(ndc)
            token = rxnorm_atc.get(rxnorm) if rxnorm else None
            if token:
                mapped[hadm] += 1
    by_role: Dict[str, Dict[str, Any]] = {}
    for role in ("train", "dev"):
        cards: List[int] = []
        coverages: List[float] = []
        for hadm, hadm_role in allowed_hadm.items():
            if hadm_role != role:
                continue
            if hadm not in target_cards:
                continue
            if eligible[hadm] <= 0:
                continue
            cards.append(target_cards[hadm])
            coverages.append(mapped[hadm] / float(eligible[hadm]))
        by_role[role] = _coverage_summary(cards, coverages)
        by_role[role]["eligible_rows_on_target_visits"] = int(
            sum(eligible[hadm] for hadm, hadm_role in allowed_hadm.items() if hadm_role == role)
        )
        by_role[role]["mapped_rows_on_target_visits"] = int(
            sum(mapped[hadm] for hadm, hadm_role in allowed_hadm.items() if hadm_role == role)
        )
    return {
        "status": "AVAILABLE",
        "lineage": "MIMIC-III NDC -> RxNorm -> ATC4; no formulary fallback",
        "roles": by_role,
    }


def _iv_index_cardinality(index_dir: Path, role: str) -> List[int]:
    payload = json.loads((index_dir / (role + ".index.json")).read_text(encoding="utf-8"))
    histogram = payload["target_cardinality_histogram"]
    values: List[int] = []
    for key, count in histogram.items():
        values.extend([int(key)] * int(count))
    return values


def _iv_raw_coverage(
    raw_hosp: Path,
    mapping_dir: Path,
    private_root: Path,
) -> Dict[str, Any]:
    """Join raw per-hadm normalization counts to private Train/Dev examples."""

    if private_root.name != IV_PRIVATE_ROOT:
        raise RuntimeError("MIMIC-IV private root identity does not match Stage -1E")
    _visits, hadm_to_subject, roles = load_admissions(raw_hosp / "admissions.csv.gz")
    ndc2atc, rxnorm2atc, _atc_meta = load_atc_mapping(mapping_dir / "ndc2atc_level4.csv")
    ndc_rxnorm = load_ndc_rxnorm(mapping_dir / "ndc2rxnorm_mapping.txt")
    kgd_ndc, kgd_rx, _kgd_meta = load_kgd_mapping(mapping_dir / "drug_codes_mapping.csv")
    maps: Dict[str, Mapping[str, str]] = {
        "ndc_direct": ndc2atc,
        "rxnorm_atc": rxnorm2atc,
        "ndc_rxnorm": ndc_rxnorm,
        "kgd_ndc": kgd_ndc,
        "kgd_rxnorm": kgd_rx,
    }
    # Fit the frozen formulary fallback on Train rows only, exactly as Stage -1E.
    _first, form_counts = prescription_pass(
        raw_hosp / "prescriptions.csv.gz",
        roles,
        hadm_to_subject,
        maps,
        collect_formulary=True,
    )
    formulary_map, _form_meta = freeze_formulary_rules(form_counts)
    eligible: Counter[str] = Counter()
    mapped: Counter[str] = Counter()
    for row in iter_selected_rows(
        raw_hosp / "prescriptions.csv.gz", ("subject_id", "hadm_id", "ndc", "formulary_drug_cd")
    ):
        subject = row["subject_id"].strip()
        role = roles.get(subject)
        if role not in {"train", "dev"}:
            continue
        hadm = row["hadm_id"].strip()
        if not hadm or hadm_to_subject.get(hadm) != subject:
            continue
        if not (normalise_ndc(row.get("ndc")) or normalise_formulary(row.get("formulary_drug_cd"))):
            continue
        eligible[hadm] += 1
        token, _source = resolve_medication(
            row.get("ndc"), row.get("formulary_drug_cd"), maps, formulary_map
        )
        if token:
            mapped[hadm] += 1
    result: Dict[str, Any] = {
        "status": "AVAILABLE",
        "lineage": "Stage -1E frozen deterministic MIMIC-IV mapper",
        "roles": {},
    }
    for role in ("train", "dev"):
        cards: List[int] = []
        coverages: List[float] = []
        target_hadm = set()
        path = private_root / (role + "_examples.private.jsonl")
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                example = json.loads(line)
                hadm = str(example["provenance"]["current_hadm_id"])
                if eligible[hadm] <= 0:
                    continue
                target_hadm.add(hadm)
                cards.append(len(example["target"]["known_medications"]))
                coverages.append(mapped[hadm] / float(eligible[hadm]))
        summary = _coverage_summary(cards, coverages)
        role_hadm = {
            hadm
            for hadm, subject in hadm_to_subject.items()
            if roles.get(subject) == role and hadm in target_hadm
        }
        summary["eligible_rows_on_target_visits"] = int(sum(eligible[hadm] for hadm in role_hadm))
        summary["mapped_rows_on_target_visits"] = int(sum(mapped[hadm] for hadm in role_hadm))
        result["roles"][role] = summary
    return result


def run(args: argparse.Namespace) -> Dict[str, Any]:
    train_cards, dev_cards, records, train_patients, dev_patients = _mimic_iii_target_cardinality(
        args.mimic_iii_snapshot.resolve(), args.mimic_iii_train_dev.resolve()
    )
    result: Dict[str, Any] = {
        "stage": "STAGE -1F",
        "status": "complete",
        "test_loaded": False,
        "target_set_cardinality": {
            "mimic_iii": {"train": _histogram(train_cards), "dev": _histogram(dev_cards)},
            "mimic_iv": {
                "train": _histogram(_iv_index_cardinality(args.iv_index_dir.resolve(), "train")),
                "dev": _histogram(_iv_index_cardinality(args.iv_index_dir.resolve(), "dev")),
            },
        },
        "normalization_coverage": {},
    }
    if args.mimic_iii_raw_root and args.mimic_iii_data_final and args.mapping_dir:
        result["normalization_coverage"]["mimic_iii"] = _mimic_iii_raw_coverage(
            args.mimic_iii_raw_root.resolve(),
            args.mimic_iii_data_final.resolve(),
            args.mapping_dir.resolve(),
            records,
            train_patients,
            dev_patients,
        )
    else:
        result["normalization_coverage"]["mimic_iii"] = {
            "status": "UNAVAILABLE",
            "reason": "canonical raw prescription provenance was not supplied; no 100% assumption made",
        }
    if args.mimic_iv_raw_hosp and args.mapping_dir and args.mimic_iv_root:
        result["normalization_coverage"]["mimic_iv"] = _iv_raw_coverage(
            args.mimic_iv_raw_hosp.resolve(),
            args.mapping_dir.resolve(),
            args.mimic_iv_root.resolve(),
        )
    else:
        result["normalization_coverage"]["mimic_iv"] = {
            "status": "UNAVAILABLE",
            "reason": "raw MIMIC-IV prescription provenance was not supplied",
        }
    result["correlation_policy"] = (
        "Pearson correlation over target visits with at least one eligible prescription row; constant inputs are undefined"
    )
    _write_json(args.output.resolve(), result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mimic-iii-snapshot", type=Path, required=True)
    parser.add_argument("--mimic-iii-train-dev", type=Path, required=True)
    parser.add_argument("--mimic-iii-raw-root", type=Path)
    parser.add_argument("--mimic-iii-data-final", type=Path)
    parser.add_argument("--mimic-iv-root", type=Path)
    parser.add_argument("--mimic-iv-raw-hosp", type=Path)
    parser.add_argument("--iv-index-dir", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True))


if __name__ == "__main__":
    main()
