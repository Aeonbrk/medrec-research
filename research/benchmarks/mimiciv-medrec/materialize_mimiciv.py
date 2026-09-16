#!/usr/bin/env python3
"""Materialize the frozen MIMIC-IV visit-level MICA Train/Dev contract.

The adapter is deliberately independent of the old MIMIC-IV order-time and
admission-set exporters.  It reads only admissions, diagnoses, procedures and
prescriptions, builds a patient-level split before any medication-derived
statistic, and writes restricted examples outside the repository.  Only
aggregate/public-safe JSON is written to ``--public-output-dir``.

The script is intended to run on the approved 319 execution plane.  It uses
the Python standard library for CSV processing; NumPy and dill are optional
only for loading and validating the frozen SafeDrug/MoleRec DDI matrix.
"""

from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import gzip
import hashlib
import json
import pickle
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

STAGE = "STAGE -1E"
BENCHMARK_ID = "mimiciv-visit-medrec-stage-minus-1e"
SOURCE_RELEASE = "MIMIC-IV v3.1"
SPLIT_SALT = "mimiciv-mica-stage-minus-1e-20260916"
SPLIT_BUCKETS = 6
MAPPING_FORMULARY_MIN_CONSENSUS = 0.85
REQUIRED_TABLES: dict[str, tuple[str, ...]] = {
    "admissions": ("subject_id", "hadm_id", "admittime"),
    "diagnoses_icd": ("subject_id", "hadm_id", "icd_code", "icd_version"),
    "procedures_icd": ("subject_id", "hadm_id", "icd_code", "icd_version"),
    "prescriptions": ("subject_id", "hadm_id", "ndc", "formulary_drug_cd"),
}
CODE_VERSIONS = {"9", "10"}


class AdapterError(RuntimeError):
    """A fail-closed adapter or source-contract error."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_lines(lines: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _header(path: Path) -> list[str]:
    with open_text(path) as handle:
        try:
            return next(csv.reader(handle))
        except StopIteration as exc:
            raise AdapterError(f"empty source table: {path.name}") from exc


def inspect_table(path: Path, required: Sequence[str]) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"missing source table: {path}")
    header = _header(path)
    missing = sorted(set(required) - set(header))
    if missing:
        raise AdapterError(f"{path.name} missing required columns: {missing}")
    stat = path.stat()
    modified = dt.datetime.fromtimestamp(stat.st_mtime, dt.UTC).isoformat()
    return {
        "filename": path.name,
        "bytes": stat.st_size,
        "modified_utc": modified,
        "sha256": sha256_file(path),
        "header": header,
        "required_columns": list(required),
    }


def iter_selected_rows(path: Path, columns: Sequence[str]) -> Iterator[dict[str, str]]:
    """Yield selected CSV columns without materializing a restricted table."""

    with open_text(path) as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise AdapterError(f"empty source table: {path.name}") from exc
        positions = []
        for column in columns:
            if column not in header:
                raise AdapterError(f"{path.name} missing required column {column!r}")
            positions.append(header.index(column))
        width = len(header)
        for line_number, row in enumerate(reader, start=2):
            if len(row) != width:
                raise AdapterError(
                    f"{path.name} malformed row {line_number}: expected {width} columns, got {len(row)}"
                )
            yield {
                column: row[position] for column, position in zip(columns, positions, strict=True)
            }


def normalise_ndc(raw: str | None) -> str | None:
    """Apply the frozen 5-4-2 NDC normalisation used by the 319 mappings."""

    value = (raw or "").strip()
    if not value or value == "0":
        return None
    parts = value.split("-")
    if len(parts) == 3 and all(re.fullmatch(r"\d+", part or "") for part in parts):
        return parts[0].zfill(5) + parts[1].zfill(4) + parts[2].zfill(2)
    digits = re.sub(r"[^0-9]", "", value)
    if not digits or len(digits) > 11:
        return None
    return digits.zfill(11)


def normalise_rxnorm(raw: str | None) -> str | None:
    value = (raw or "").strip()
    if not value or value.lower() in {"nan", "none", "null"}:
        return None
    value = value[:-2] if value.endswith(".0") else value
    return value if value.isdigit() else None


def normalise_formulary(raw: str | None) -> str | None:
    value = (raw or "").strip().upper()
    return value or None


def normalise_atc4(raw: str | None) -> str | None:
    """Return the SafeDrug/MoleRec four-character ATC4 identity.

    The upstream mapping column is named ``ATC4`` and contains five-character
    entries such as ``A10BJ``.  The frozen MICA/SafeDrug vocabulary and DDI
    authority use the four-character identity (for example ``A10B``); the
    deterministic prefix is therefore part of this benchmark's lineage.
    """

    value = (raw or "").strip().upper()
    if value.startswith("ATC4:"):
        value = value[5:]
    if len(value) < 4 or not re.fullmatch(r"[A-Z][0-9]{2}[A-Z].*", value):
        return None
    return value[:4]


def split_role(subject_id: str) -> str:
    digest = hashlib.sha256(f"{SPLIT_SALT}|{subject_id}".encode()).digest()
    bucket = int.from_bytes(digest[:8], "big") % SPLIT_BUCKETS
    if bucket < 4:
        return "train"
    if bucket == 4:
        return "dev"
    return "test"


def _hadm_sort_key(admittime: str, hadm_id: str) -> tuple[str, int | str]:
    if hadm_id.isdigit():
        return (admittime, int(hadm_id))
    return (admittime, hadm_id)


def load_admissions(
    path: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str], dict[str, str]]:
    visits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    hadm_to_subject: dict[str, str] = {}
    roles: dict[str, str] = {}
    for row in iter_selected_rows(path, REQUIRED_TABLES["admissions"]):
        subject = row["subject_id"].strip()
        hadm = row["hadm_id"].strip()
        admittime = row["admittime"].strip()
        if not subject or not hadm or not admittime:
            raise AdapterError("admissions contains a blank subject_id, hadm_id, or admittime")
        if hadm in hadm_to_subject:
            raise AdapterError(f"duplicate hadm_id in admissions: {hadm}")
        role = roles.setdefault(subject, split_role(subject))
        hadm_to_subject[hadm] = subject
        visits[subject].append({"hadm_id": hadm, "admittime": admittime, "role": role})
    for subject, rows in visits.items():
        rows.sort(key=lambda item: _hadm_sort_key(item["admittime"], item["hadm_id"]))
        previous: tuple[str, int | str] | None = None
        for order, row in enumerate(rows):
            key = _hadm_sort_key(row["admittime"], row["hadm_id"])
            if previous is not None and key <= previous:
                raise AdapterError(f"non-deterministic visit chronology for subject {subject}")
            row["visit_order"] = order
            previous = key
    return visits, hadm_to_subject, roles


def _code_token(code: str, version: str) -> str:
    code = code.strip().upper()
    version = version.strip()
    if not code or version not in CODE_VERSIONS:
        raise AdapterError(f"invalid ICD code/version pair: {code!r}/{version!r}")
    return f"ICD{version}:{code}"


def load_code_sets(
    path: Path,
    table_name: str,
    roles: Mapping[str, str],
    hadm_to_subject: Mapping[str, str],
) -> tuple[dict[str, set[str]], dict[str, int]]:
    code_sets: dict[str, set[str]] = defaultdict(set)
    stats = Counter()
    for row in iter_selected_rows(path, REQUIRED_TABLES[table_name]):
        subject = row["subject_id"].strip()
        role = roles.get(subject)
        if role not in {"train", "dev"}:
            stats["rows_skipped_test_or_unknown"] += 1
            continue
        stats[f"rows_{role}"] += 1
        hadm = row["hadm_id"].strip()
        if not hadm or hadm not in hadm_to_subject:
            stats["orphan_rows"] += 1
            continue
        if hadm_to_subject[hadm] != subject:
            raise AdapterError(f"{table_name} subject/hadm linkage mismatch")
        token = _code_token(row["icd_code"], row["icd_version"])
        code_sets[hadm].add(token)
    for role in ("train", "dev"):
        stats[f"unique_hadm_{role}"] = sum(
            1
            for hadm, values in code_sets.items()
            if values and roles.get(hadm_to_subject.get(hadm, "")) == role
        )
    return code_sets, dict(stats)


def _choose_mapping(
    current: tuple[tuple[int, int, str], str] | None,
    candidate: tuple[tuple[int, int, str], str],
) -> tuple[tuple[int, int, str], str]:
    if current is None:
        return candidate
    if candidate[0] > current[0]:
        return candidate
    if candidate[0] < current[0]:
        return current
    return candidate if candidate[1] < current[1] else current


def load_atc_mapping(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    ndc_candidates: dict[str, tuple[tuple[int, int, str], str]] = {}
    rx_candidates: dict[str, tuple[tuple[int, int, str], str]] = {}
    rows = 0
    invalid = 0
    for row in iter_selected_rows(path, ("YEAR", "MONTH", "NDC", "RXCUI", "ATC4")):
        rows += 1
        token = normalise_atc4(row["ATC4"])
        ndc = normalise_ndc(row["NDC"])
        rxnorm = normalise_rxnorm(row["RXCUI"])
        if token is None:
            invalid += 1
            continue
        try:
            year = int(row["YEAR"])
            month = int(row["MONTH"])
        except ValueError:
            year, month = -1, -1
        rank = (year, month, token)
        if ndc:
            ndc_candidates[ndc] = _choose_mapping(ndc_candidates.get(ndc), (rank, token))
        if rxnorm:
            rx_candidates[rxnorm] = _choose_mapping(rx_candidates.get(rxnorm), (rank, token))
    return (
        {key: value[1] for key, value in ndc_candidates.items()},
        {key: value[1] for key, value in rx_candidates.items()},
        {
            "rows": rows,
            "invalid_atc_rows": invalid,
            "distinct_ndc": len(ndc_candidates),
            "distinct_rxnorm": len(rx_candidates),
            "selection": "latest YEAR/MONTH, lexicographically smallest token on exact tie",
        },
    )


def load_ndc_rxnorm(path: Path) -> dict[str, str]:
    try:
        value = ast.literal_eval(path.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError) as exc:
        raise AdapterError(f"cannot parse NDC/RxNorm mapping: {path.name}") from exc
    if not isinstance(value, dict):
        raise AdapterError("NDC/RxNorm mapping is not a dictionary")
    result: dict[str, str] = {}
    for raw_ndc, raw_rxnorm in value.items():
        ndc, rxnorm = normalise_ndc(str(raw_ndc)), normalise_rxnorm(str(raw_rxnorm))
        if ndc and rxnorm:
            result[ndc] = rxnorm
    return result


def load_kgd_mapping(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    with open_text(path) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AdapterError(f"empty mapping file: {path.name}")
        required = {"ndc", "rxcui", "atc4"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise AdapterError(f"{path.name} missing mapping columns: {sorted(missing)}")
        ndc_map: dict[str, str] = {}
        rx_map: dict[str, str] = {}
        rows = 0
        for row in reader:
            rows += 1
            token = normalise_atc4(row.get("atc4"))
            if token is None:
                continue
            ndc = normalise_ndc(row.get("ndc"))
            rxnorm = normalise_rxnorm(row.get("rxcui"))
            if ndc:
                ndc_map.setdefault(ndc, token)
            if rxnorm:
                rx_map.setdefault(rxnorm, token)
        return (
            ndc_map,
            rx_map,
            {"rows": rows, "distinct_ndc": len(ndc_map), "distinct_rxnorm": len(rx_map)},
        )


def resolve_without_formulary(
    ndc_raw: str | None,
    maps: Mapping[str, Mapping[str, str]],
) -> tuple[str | None, str | None]:
    ndc = normalise_ndc(ndc_raw)
    if ndc and ndc in maps["ndc_direct"]:
        return maps["ndc_direct"][ndc], "ndc_direct"
    rxnorm = maps["ndc_rxnorm"].get(ndc) if ndc else None
    if rxnorm and rxnorm in maps["rxnorm_atc"]:
        return maps["rxnorm_atc"][rxnorm], "ndc_rxnorm_atc"
    if ndc and ndc in maps["kgd_ndc"]:
        return maps["kgd_ndc"][ndc], "kgd_ndc"
    if rxnorm and rxnorm in maps["kgd_rxnorm"]:
        return maps["kgd_rxnorm"][rxnorm], "kgd_rxnorm_atc"
    return None, None


def resolve_medication(
    ndc_raw: str | None,
    formulary_raw: str | None,
    maps: Mapping[str, Mapping[str, str]],
    formulary_map: Mapping[str, str],
) -> tuple[str | None, str | None]:
    token, source = resolve_without_formulary(ndc_raw, maps)
    if token:
        return token, source
    formulary = normalise_formulary(formulary_raw)
    if formulary and formulary in formulary_map:
        return formulary_map[formulary], "formulary_consensus_train"
    return None, None


def _prescription_row_eligible(row: Mapping[str, str]) -> bool:
    return bool(row["hadm_id"].strip()) and bool(
        normalise_ndc(row.get("ndc")) or normalise_formulary(row.get("formulary_drug_cd"))
    )


def prescription_pass(
    path: Path,
    roles: Mapping[str, str],
    hadm_to_subject: Mapping[str, str],
    maps: Mapping[str, Mapping[str, str]],
    *,
    formulary_map: Mapping[str, str] | None = None,
    collect_formulary: bool = False,
    meds_by_hadm: dict[str, set[str]] | None = None,
    samples: list[tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Counter[str]]]:
    stats: dict[str, Counter[str]] = {"train": Counter(), "dev": Counter()}
    form_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in iter_selected_rows(path, ("subject_id", "hadm_id", "ndc", "formulary_drug_cd")):
        subject = row["subject_id"].strip()
        role = roles.get(subject)
        if role not in {"train", "dev"}:
            continue  # Test rows are never loaded into target statistics.
        counter = stats[role]
        counter["rows_seen"] += 1
        hadm = row["hadm_id"].strip()
        if not hadm or hadm not in hadm_to_subject:
            counter["orphan_rows"] += 1
            continue
        if hadm_to_subject[hadm] != subject:
            raise AdapterError("prescriptions subject/hadm linkage mismatch")
        if not _prescription_row_eligible(row):
            counter["ineligible_rows"] += 1
            continue
        counter["eligible_rows"] += 1
        if samples is not None and len(samples) < 512:
            samples.append((row.get("ndc", ""), row.get("formulary_drug_cd", "")))
        token, source = resolve_without_formulary(row.get("ndc"), maps)
        if collect_formulary and role == "train" and token:
            formulary = normalise_formulary(row.get("formulary_drug_cd"))
            if formulary:
                form_counts[formulary][token] += 1
        if formulary_map is None:
            if token:
                counter["mapped_without_formulary"] += 1
                counter[f"path_{source}"] += 1
            else:
                counter["unmapped_without_formulary"] += 1
            continue
        token, source = resolve_medication(
            row.get("ndc"), row.get("formulary_drug_cd"), maps, formulary_map
        )
        if token is None:
            counter["unmapped_rows"] += 1
            if not normalise_ndc(row.get("ndc")):
                counter["unmapped_no_ndc"] += 1
            else:
                counter["unmapped_ndc_and_formulary"] += 1
        else:
            counter["mapped_rows"] += 1
            counter[f"path_{source}"] += 1
            if meds_by_hadm is not None:
                meds_by_hadm.setdefault(hadm, set()).add(token)
    return {role: dict(counter) for role, counter in stats.items()}, form_counts


def freeze_formulary_rules(
    form_counts: Mapping[str, Counter[str]],
) -> tuple[dict[str, str], dict[str, Any]]:
    rules: dict[str, str] = {}
    ambiguous = 0
    for formulary, counts in sorted(form_counts.items()):
        total = sum(counts.values())
        top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
        if total and top[1] / total >= MAPPING_FORMULARY_MIN_CONSENSUS:
            rules[formulary] = top[0]
        if len(counts) > 1:
            ambiguous += 1
    return rules, {
        "rules": len(rules),
        "observed_formulary_codes": len(form_counts),
        "ambiguous_formulary_codes": ambiguous,
        "consensus_fraction": MAPPING_FORMULARY_MIN_CONSENSUS,
        "fit_role": "train_only",
        "tie_break": "highest count, lexicographically smallest ATC4 token",
    }


def fit_vocab(
    visits_by_subject: Mapping[str, Sequence[Mapping[str, Any]]],
    roles: Mapping[str, str],
    dx_by_hadm: Mapping[str, set[str]],
    proc_by_hadm: Mapping[str, set[str]],
    meds_by_hadm: Mapping[str, set[str]],
) -> dict[str, Any]:
    dx: set[str] = set()
    proc: set[str] = set()
    med: set[str] = set()
    for subject, visits in visits_by_subject.items():
        if roles[subject] != "train":
            continue
        for visit in visits:
            hadm = visit["hadm_id"]
            dx.update(dx_by_hadm.get(hadm, set()))
            proc.update(proc_by_hadm.get(hadm, set()))
            med.update(meds_by_hadm.get(hadm, set()))
    return {
        "diagnosis": {"<UNK>": 0, **{token: index + 1 for index, token in enumerate(sorted(dx))}},
        "procedure": {"<UNK>": 0, **{token: index + 1 for index, token in enumerate(sorted(proc))}},
        "medication": {token: index for index, token in enumerate(sorted(med))},
    }


def _history_entry(
    visit: Mapping[str, Any],
    dx_by_hadm: Mapping[str, set[str]],
    proc_by_hadm: Mapping[str, set[str]],
    meds_by_hadm: Mapping[str, set[str]],
) -> dict[str, Any]:
    hadm = visit["hadm_id"]
    return {
        "visit_order": visit["visit_order"],
        "hadm_id": hadm,
        "diagnoses": sorted(dx_by_hadm.get(hadm, set())),
        "procedures": sorted(proc_by_hadm.get(hadm, set())),
        "medications": sorted(meds_by_hadm.get(hadm, set())),
    }


def write_examples(
    path: Path,
    role: str,
    visits_by_subject: Mapping[str, Sequence[Mapping[str, Any]]],
    roles: Mapping[str, str],
    dx_by_hadm: Mapping[str, set[str]],
    proc_by_hadm: Mapping[str, set[str]],
    meds_by_hadm: Mapping[str, set[str]],
    med_vocab: Mapping[str, int],
    dx_vocab: Mapping[str, int],
    proc_vocab: Mapping[str, int],
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats: Counter[str] = Counter()
    digest = hashlib.sha256()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for subject in sorted(visits_by_subject):
            if roles[subject] != role:
                continue
            visits = visits_by_subject[subject]
            stats["patients"] += 1
            history: list[dict[str, Any]] = []
            for visit in visits:
                stats["visits_total"] += 1
                hadm = visit["hadm_id"]
                target = sorted(meds_by_hadm.get(hadm, set()))
                if not target:
                    stats["visits_without_mapped_target"] += 1
                    history.append(_history_entry(visit, dx_by_hadm, proc_by_hadm, meds_by_hadm))
                    continue
                current_dx = sorted(dx_by_hadm.get(hadm, set()))
                current_proc = sorted(proc_by_hadm.get(hadm, set()))
                history_copy = [dict(entry) for entry in history]
                known_target = sorted(token for token in target if token in med_vocab)
                oov_target = sorted(token for token in target if token not in med_vocab)
                example = {
                    "schema_version": 1,
                    "subject_id": subject,
                    "current_visit_order": visit["visit_order"],
                    "input": {
                        "diagnoses": current_dx,
                        "procedures": current_proc,
                        "history": history_copy,
                    },
                    "target": {
                        "medications": target,
                        "known_medications": known_target,
                        "oov_medications": oov_target,
                    },
                    "provenance": {
                        "current_hadm_id": hadm,
                        "history_hadm_ids": [entry["hadm_id"] for entry in history_copy],
                    },
                }
                encoded = canonical_json(example)
                handle.write(encoded.decode("utf-8"))
                digest.update(encoded)
                stats["examples"] += 1
                stats["target_medication_tokens"] += len(target)
                stats["target_medication_oov_tokens"] += len(oov_target)
                if oov_target:
                    stats["examples_with_target_oov"] += 1
                if not known_target:
                    stats["examples_all_target_oov"] += 1
                input_dx = current_dx + [
                    token for entry in history_copy for token in entry["diagnoses"]
                ]
                input_proc = current_proc + [
                    token for entry in history_copy for token in entry["procedures"]
                ]
                input_hist_med = [token for entry in history_copy for token in entry["medications"]]
                stats["dx_input_tokens"] += len(input_dx)
                stats["dx_input_oov_tokens"] += sum(token not in dx_vocab for token in input_dx)
                stats["proc_input_tokens"] += len(input_proc)
                stats["proc_input_oov_tokens"] += sum(
                    token not in proc_vocab for token in input_proc
                )
                stats["history_medication_tokens"] += len(input_hist_med)
                stats["history_medication_oov_tokens"] += sum(
                    token not in med_vocab for token in input_hist_med
                )
                history.append(_history_entry(visit, dx_by_hadm, proc_by_hadm, meds_by_hadm))
            # A target-empty visit is still part of the strict history prefix.
            # The branch above appends it before continuing.
    stats["sha256"] = digest.hexdigest()
    return dict(stats)


def reload_digest(path: Path) -> tuple[int, str]:
    count = 0
    digest = hashlib.sha256()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AdapterError(f"cannot reload {path.name} line {line_number}") from exc
            digest.update(canonical_json(obj))
            count += 1
    return count, digest.hexdigest()


def audit_examples(path: Path) -> dict[str, Any]:
    count = 0
    max_history = -1
    current_target_input_hits = 0
    current_hadm_history_hits = 0
    invalid_input_keys = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                example = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AdapterError(f"invalid serialized example {path.name}:{line_number}") from exc
            count += 1
            current_order = example["current_visit_order"]
            current_hadm = example["provenance"]["current_hadm_id"]
            input_part = example["input"]
            history = input_part["history"]
            if set(input_part) != {"diagnoses", "procedures", "history"}:
                invalid_input_keys += 1
            if "medications" in input_part or "current_medications" in input_part:
                current_target_input_hits += 1
            history_ids = example["provenance"]["history_hadm_ids"]
            if current_hadm in history_ids:
                current_hadm_history_hits += 1
            for entry in history:
                max_history = max(max_history, entry["visit_order"])
                if entry["visit_order"] >= current_order or entry["hadm_id"] == current_hadm:
                    current_hadm_history_hits += 1
            if history_ids != [entry["hadm_id"] for entry in history]:
                current_hadm_history_hits += 1
    return {
        "examples": count,
        "max_history_visit_order_observed": max_history,
        "current_target_input_hits": current_target_input_hits,
        "current_hadm_history_hits": current_hadm_history_hits,
        "invalid_input_keys": invalid_input_keys,
        "strict_history_pass": current_hadm_history_hits == 0,
        "current_target_not_in_input_pass": current_target_input_hits == 0,
    }


def load_ddi_projection(
    snapshot_dir: Path,
    medication_vocab: Mapping[str, int],
) -> tuple[dict[str, Any], list[list[int]]]:
    try:
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover - only remote execution has DDI assets
        raise AdapterError("NumPy is required to validate the frozen DDI asset") from exc
    voc_path = snapshot_dir / "voc_final.pkl"
    ddi_path = snapshot_dir / "ddi_A_final.pkl"
    if not voc_path.is_file() or not ddi_path.is_file():
        raise AdapterError(f"DDI snapshot missing voc_final.pkl or ddi_A_final.pkl: {snapshot_dir}")
    loader = pickle
    try:
        import dill  # type: ignore

        loader = dill
    except ImportError:
        pass
    with voc_path.open("rb") as handle:
        voc = loader.load(handle)
    with ddi_path.open("rb") as handle:
        matrix = np.asarray(loader.load(handle))
    med_idx2word = voc["med_voc"].idx2word
    source_codes = [normalise_atc4(str(med_idx2word[index])) for index in range(len(med_idx2word))]
    if any(code is None for code in source_codes):
        raise AdapterError("frozen DDI vocabulary contains an invalid medication code")
    source_codes = [code for code in source_codes if code is not None]
    if matrix.shape != (len(source_codes), len(source_codes)):
        raise AdapterError("frozen DDI matrix shape does not match its medication vocabulary")
    if not np.isfinite(matrix).all() or not np.isin(matrix, (0, 1)).all():
        raise AdapterError("frozen DDI matrix is not finite binary")
    symmetric = bool(np.array_equal(matrix, matrix.T))
    zero_diagonal = bool(np.all(np.diag(matrix) == 0))
    if not symmetric or not zero_diagonal:
        raise AdapterError("frozen DDI matrix is not symmetric zero-diagonal")
    source_pairs = {
        tuple(sorted((source_codes[left], source_codes[right])))
        for left in range(len(source_codes))
        for right in range(left + 1, len(source_codes))
        if matrix[left, right] == 1
    }
    vocab_codes = set(medication_vocab)
    represented = sorted(set(source_codes) & vocab_codes)
    unmapped_endpoints = sorted(set(source_codes) - vocab_codes)
    projected_pairs = sorted(
        pair for pair in source_pairs if pair[0] in vocab_codes and pair[1] in vocab_codes
    )
    projected = [[0 for _ in medication_vocab] for _ in medication_vocab]
    for left, right in projected_pairs:
        i, j = medication_vocab[left], medication_vocab[right]
        projected[i][j] = projected[j][i] = 1
    projected_np = np.asarray(projected, dtype=np.int8)
    projection_checks = {
        "matrix_shape": [len(medication_vocab), len(medication_vocab)],
        "matrix_finite_binary": bool(
            np.isfinite(projected_np).all() and np.isin(projected_np, (0, 1)).all()
        ),
        "matrix_symmetric": bool(np.array_equal(projected_np, projected_np.T)),
        "matrix_zero_diagonal": bool(np.all(np.diag(projected_np) == 0)),
    }
    return (
        {
            "authority": "SafeDrug/MoleRec canonical DDI snapshot",
            "snapshot_id": snapshot_dir.name,
            "voc_file": {
                "filename": voc_path.name,
                "bytes": voc_path.stat().st_size,
                "sha256": sha256_file(voc_path),
            },
            "ddi_file": {
                "filename": ddi_path.name,
                "bytes": ddi_path.stat().st_size,
                "sha256": sha256_file(ddi_path),
            },
            "source_medication_vocab_size": len(source_codes),
            "source_ddi_pair_count": len(source_pairs),
            "source_supported_concept_count": len({x for pair in source_pairs for x in pair}),
            "projected_medication_vocab_size": len(medication_vocab),
            "projected_supported_concept_count": len(represented),
            "projected_concept_coverage": (len(represented) / len(set(source_codes)))
            if source_codes
            else 0.0,
            "unmapped_source_endpoint_count": len(unmapped_endpoints),
            "projected_ddi_pair_count": len(projected_pairs),
            "unmapped_ddi_pair_count": len(source_pairs) - len(projected_pairs),
            "source_checks": {
                "finite_binary": True,
                "symmetric": symmetric,
                "zero_diagonal": zero_diagonal,
            },
            "projection_checks": projection_checks,
            "coverage_policy": "report only; no new DDI pairs or arbitrary PASS threshold",
        },
        projected,
    )


def artifact_meta(path: Path) -> dict[str, Any]:
    return {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def materialize(args: argparse.Namespace) -> dict[str, Any]:
    mimic_hosp = args.mimic_hosp.resolve()
    mapping_dir = args.mapping_dir.resolve()
    output_dir = args.output_dir.resolve()
    public_dir = args.public_output_dir.resolve()
    script_root: Path | None = None
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            script_root = parent
            break
    if script_root is not None:
        if script_root == output_dir or script_root in output_dir.parents:
            raise AdapterError("restricted output must be outside the repository")
        if script_root == public_dir or script_root in public_dir.parents:
            raise AdapterError("public output staging must be outside the repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)

    source_meta: dict[str, Any] = {}
    for table_name, required in REQUIRED_TABLES.items():
        source_meta[table_name] = inspect_table(mimic_hosp / f"{table_name}.csv.gz", required)

    visits, hadm_to_subject, roles = load_admissions(mimic_hosp / "admissions.csv.gz")
    role_subjects = {
        role: sorted(subject for subject, value in roles.items() if value == role)
        for role in {"train", "dev", "test"}
    }
    test_membership_sha256 = sha256_text_lines(
        f"test\t{subject}\n" for subject in role_subjects["test"]
    )
    (output_dir / "split_membership.private.json").write_text(
        json.dumps({"roles": role_subjects}, sort_keys=True) + "\n", encoding="utf-8"
    )

    dx_by_hadm, dx_stats = load_code_sets(
        mimic_hosp / "diagnoses_icd.csv.gz", "diagnoses_icd", roles, hadm_to_subject
    )
    proc_by_hadm, proc_stats = load_code_sets(
        mimic_hosp / "procedures_icd.csv.gz", "procedures_icd", roles, hadm_to_subject
    )

    ndc2atc, rxnorm2atc, atc_meta = load_atc_mapping(mapping_dir / "ndc2atc_level4.csv")
    ndc_rxnorm = load_ndc_rxnorm(mapping_dir / "ndc2rxnorm_mapping.txt")
    kgd_file = mapping_dir / "drug_codes_mapping.csv"
    if not kgd_file.is_file():
        kgd_file = mapping_dir / "drug_codes_mapping_atc.csv"
    kgd_ndc, kgd_rx, kgd_meta = load_kgd_mapping(kgd_file)
    maps: dict[str, Mapping[str, str]] = {
        "ndc_direct": ndc2atc,
        "rxnorm_atc": rxnorm2atc,
        "ndc_rxnorm": ndc_rxnorm,
        "kgd_ndc": kgd_ndc,
        "kgd_rxnorm": kgd_rx,
    }
    samples: list[tuple[str, str]] = []
    first_stats, form_counts = prescription_pass(
        mimic_hosp / "prescriptions.csv.gz",
        roles,
        hadm_to_subject,
        maps,
        collect_formulary=True,
        samples=samples,
    )
    formulary_map, formulary_meta = freeze_formulary_rules(form_counts)
    meds_by_hadm: dict[str, set[str]] = {}
    final_stats, _ = prescription_pass(
        mimic_hosp / "prescriptions.csv.gz",
        roles,
        hadm_to_subject,
        maps,
        formulary_map=formulary_map,
        meds_by_hadm=meds_by_hadm,
    )
    for role in ("train", "dev"):
        if first_stats[role]["eligible_rows"] != final_stats[role]["eligible_rows"]:
            raise AdapterError("normalization passes disagree on eligible prescription rows")
        final_stats[role]["coverage"] = _ratio(
            final_stats[role].get("mapped_rows", 0), final_stats[role].get("eligible_rows", 0)
        )
        final_stats[role]["unique_normalized_concepts"] = len(
            {
                token
                for hadm, tokens in meds_by_hadm.items()
                if roles.get(hadm_to_subject.get(hadm, "")) == role
                for token in tokens
            }
        )

    # Make normalization determinism explicit on a fixed, role-safe sample.
    determinism_digest = hashlib.sha256()
    for ndc, formulary in samples:
        first = resolve_medication(ndc, formulary, maps, formulary_map)
        second = resolve_medication(ndc, formulary, maps, formulary_map)
        if first != second:
            raise AdapterError("normalization is not deterministic")
        determinism_digest.update(
            canonical_json(
                {
                    "ndc": normalise_ndc(ndc),
                    "formulary": normalise_formulary(formulary),
                    "result": first,
                }
            )
        )

    vocabs = fit_vocab(visits, roles, dx_by_hadm, proc_by_hadm, meds_by_hadm)
    (output_dir / "vocabularies.private.json").write_text(
        json.dumps(vocabs, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "mapping_manifest.private.json").write_text(
        json.dumps(
            {
                "mapping_files": {
                    "ndc2atc_level4.csv": artifact_meta(mapping_dir / "ndc2atc_level4.csv"),
                    "ndc2rxnorm_mapping.txt": artifact_meta(mapping_dir / "ndc2rxnorm_mapping.txt"),
                    kgd_file.name: artifact_meta(kgd_file),
                },
                "atc_mapping_stats": atc_meta,
                "kgd_mapping_stats": kgd_meta,
                "formulary_fallback": formulary_meta,
                "normalization_precedence": [
                    "NDC direct ATC4 mapping",
                    "NDC to RxNorm to ATC4",
                    "KGDNet NDC/RxNorm ATC4 mapping",
                    "Train-only formulary consensus fallback",
                ],
                "normalization_rule_digest": determinism_digest.hexdigest(),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    med_vocab = vocabs["medication"]
    train_examples = output_dir / "train_examples.private.jsonl"
    dev_examples = output_dir / "dev_examples.private.jsonl"
    train_example_stats = write_examples(
        train_examples,
        "train",
        visits,
        roles,
        dx_by_hadm,
        proc_by_hadm,
        meds_by_hadm,
        med_vocab,
        vocabs["diagnosis"],
        vocabs["procedure"],
    )
    dev_example_stats = write_examples(
        dev_examples,
        "dev",
        visits,
        roles,
        dx_by_hadm,
        proc_by_hadm,
        meds_by_hadm,
        med_vocab,
        vocabs["diagnosis"],
        vocabs["procedure"],
    )
    train_reload = reload_digest(train_examples)
    dev_reload = reload_digest(dev_examples)
    if train_reload != (train_example_stats["examples"], train_example_stats["sha256"]):
        raise AdapterError("Train serialization reload digest mismatch")
    if dev_reload != (dev_example_stats["examples"], dev_example_stats["sha256"]):
        raise AdapterError("Dev serialization reload digest mismatch")
    train_audit = audit_examples(train_examples)
    dev_audit = audit_examples(dev_examples)

    ddi, projected_ddi = load_ddi_projection(args.ddi_snapshot.resolve(), med_vocab)
    (output_dir / "ddi_matrix.private.json").write_text(
        json.dumps({"vocabulary": med_vocab, "matrix": projected_ddi}, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    def role_summary(
        role: str, examples: Mapping[str, Any], audit: Mapping[str, Any]
    ) -> dict[str, Any]:
        target_total = examples.get("target_medication_tokens", 0)
        return {
            "patients": len(role_subjects[role]),
            "visits_total": examples.get("visits_total", 0),
            "eligible_target_visits": examples.get("examples", 0),
            "visits_without_mapped_target": examples.get("visits_without_mapped_target", 0),
            "examples": examples.get("examples", 0),
            "serialization_sha256": examples["sha256"],
            "diagnosis_input_tokens": examples.get("dx_input_tokens", 0),
            "diagnosis_input_oov_tokens": examples.get("dx_input_oov_tokens", 0),
            "diagnosis_input_oov_rate": _ratio(
                examples.get("dx_input_oov_tokens", 0), examples.get("dx_input_tokens", 0)
            ),
            "procedure_input_tokens": examples.get("proc_input_tokens", 0),
            "procedure_input_oov_tokens": examples.get("proc_input_oov_tokens", 0),
            "procedure_input_oov_rate": _ratio(
                examples.get("proc_input_oov_tokens", 0), examples.get("proc_input_tokens", 0)
            ),
            "target_medication_tokens": target_total,
            "target_medication_oov_tokens": examples.get("target_medication_oov_tokens", 0),
            "target_medication_oov_rate": _ratio(
                examples.get("target_medication_oov_tokens", 0), target_total
            ),
            "examples_with_target_oov": examples.get("examples_with_target_oov", 0),
            "examples_all_target_oov": examples.get("examples_all_target_oov", 0),
            "history_medication_oov_rate": _ratio(
                examples.get("history_medication_oov_tokens", 0),
                examples.get("history_medication_tokens", 0),
            ),
            "audit": dict(audit),
        }

    train_summary = role_summary("train", train_example_stats, train_audit)
    dev_summary = role_summary("dev", dev_example_stats, dev_audit)
    source_meta_for_public = {
        table: {key: value for key, value in meta.items() if key != "header"}
        | {"header_columns": meta["header"]}
        for table, meta in source_meta.items()
    }
    public_manifest: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": BENCHMARK_ID,
        "stage": STAGE,
        "source_revision": args.source_revision,
        "source_release": SOURCE_RELEASE,
        "raw_source_identity": source_meta_for_public,
        "split": {
            "algorithm": "SHA256(SPLIT_SALT|subject_id) first 8 bytes interpreted big-endian modulo 6",
            "salt": SPLIT_SALT,
            "bucket_roles": {"0-3": "train", "4": "dev", "5": "test"},
            "patient_counts": {role: len(role_subjects[role]) for role in ("train", "dev", "test")},
            "test_membership": {
                "count": len(role_subjects["test"]),
                "sha256": test_membership_sha256,
                "targets_loaded": False,
                "materialized": False,
            },
        },
        "normalization_lineage": {
            "representation": "ATC4 SafeDrug/MoleRec four-character identity (upstream ATC4 field prefix [:4])",
            "mapping_precedence": [
                "NDC direct mapping",
                "NDC to RxNorm to ATC4",
                "KGDNet NDC/RxNorm mapping",
                "Train-only formulary consensus fallback",
            ],
            "ndc_rule": "hyphenated 5-4-2 components padded to 11 digits; otherwise digits-only left-padded to 11",
            "duplicate_resolution": "latest YEAR/MONTH then lexicographically smallest projected ATC4",
            "unmapped_handling": "count and exclude from current target; no artificial UNK medication",
            "formulary_fallback": formulary_meta,
            "mapping_files": {
                "ndc2atc_level4.csv": artifact_meta(mapping_dir / "ndc2atc_level4.csv"),
                "ndc2rxnorm_mapping.txt": artifact_meta(mapping_dir / "ndc2rxnorm_mapping.txt"),
                kgd_file.name: artifact_meta(kgd_file),
            },
            "determinism_sample_count": len(samples),
            "determinism_sample_digest": determinism_digest.hexdigest(),
        },
        "normalization": {
            role: {
                "eligible_prescription_rows": final_stats[role].get("eligible_rows", 0),
                "mapped_prescription_rows": final_stats[role].get("mapped_rows", 0),
                "unmapped_prescription_rows": final_stats[role].get("unmapped_rows", 0),
                "coverage": final_stats[role]["coverage"],
                "unique_normalized_atc4_concepts": final_stats[role].get(
                    "unique_normalized_concepts", 0
                ),
                "path_counts": {
                    key[5:]: value
                    for key, value in final_stats[role].items()
                    if key.startswith("path_")
                },
            }
            for role in ("train", "dev")
        },
        "vocabulary": {
            "fit_role": "train_only",
            "diagnosis_vocab_size": len(vocabs["diagnosis"]),
            "procedure_vocab_size": len(vocabs["procedure"]),
            "medication_vocab_size": len(vocabs["medication"]),
            "unknown_policy": {
                "diagnosis": "Dev/Test input codes map to <UNK> and never extend Train vocab",
                "procedure": "Dev/Test input codes map to <UNK> and never extend Train vocab",
                "medication_target": "Dev/Test target concepts absent from Train are reported OOV and never extend Train vocab",
                "medication_history": "history concepts absent from Train target vocab map to an input-side unknown at model consumption",
            },
        },
        "train": train_summary,
        "dev": dev_summary,
        "ddi": ddi,
        "private_artifacts": [
            artifact_meta(train_examples),
            artifact_meta(dev_examples),
            artifact_meta(output_dir / "vocabularies.private.json"),
            artifact_meta(output_dir / "mapping_manifest.private.json"),
            artifact_meta(output_dir / "ddi_matrix.private.json"),
            artifact_meta(output_dir / "split_membership.private.json"),
        ],
        "test_policy": "Test membership is sealed by count/digest only; no Test medications, target frequencies, vocab fit, DDI fit, threshold tuning, or evaluation was performed.",
        "next_screen_contract": {
            "status": "prepared_not_run",
            "arms": ["SharedPool", "MICA-Core/DrugQuery"],
            "recipe": "AdamW constant learning rate 1e-4, same seed first screen, full budget, strict best-Dev-Jaccard checkpoint",
            "threshold": 0.35,
            "primary_delta": "DrugQuery - SharedPool",
        },
    }
    core = {
        "SOURCE_IDENTITY_PASS": True,
        "PATIENT_SPLIT_DISJOINT_PASS": len(set(roles.values())) == 3
        and sum(len(role_subjects[role]) for role in ("train", "dev", "test")) == len(roles),
        "VISIT_CHRONOLOGY_PASS": True,
        "STRICT_HISTORY_PASS": bool(
            train_audit["strict_history_pass"] and dev_audit["strict_history_pass"]
        ),
        "CURRENT_TARGET_NOT_IN_INPUT_PASS": bool(
            train_audit["current_target_not_in_input_pass"]
            and dev_audit["current_target_not_in_input_pass"]
        ),
        "TRAIN_ONLY_VOCAB_FIT_PASS": True,
        "NORMALIZATION_DETERMINISM_PASS": bool(samples) and bool(determinism_digest.hexdigest()),
        "DDI_MATRIX_VALID_PASS": all(ddi["projection_checks"].values())
        and all(ddi["source_checks"].values()),
        "TRAIN_DEV_SERIALIZATION_RELOAD_PASS": train_reload
        == (train_example_stats["examples"], train_example_stats["sha256"])
        and dev_reload == (dev_example_stats["examples"], dev_example_stats["sha256"]),
    }
    checks: dict[str, Any] = {
        "schema_version": 1,
        "stage": STAGE,
        "checks": {name: {"status": "PASS" if value else "FAIL"} for name, value in core.items()},
        "NORMALIZATION_COVERAGE_REPORTED": {
            "status": "REPORTED",
            "train": public_manifest["normalization"]["train"],
            "dev": public_manifest["normalization"]["dev"],
        },
        "MEDICATION_TARGET_OOV_REPORTED": {
            "status": "REPORTED",
            "dev_target_oov_rate": dev_summary["target_medication_oov_rate"],
            "dev_examples_with_target_oov": dev_summary["examples_with_target_oov"],
        },
        "DDI_PROJECTION_COVERAGE_REPORTED": {
            "status": "REPORTED",
            "concept_coverage": ddi["projected_concept_coverage"],
            "source_pairs": ddi["source_ddi_pair_count"],
            "projected_pairs": ddi["projected_ddi_pair_count"],
            "unmapped_endpoints": ddi["unmapped_source_endpoint_count"],
        },
        "source_stats": {"diagnoses": dx_stats, "procedures": proc_stats},
        "test_targets_loaded": False,
        "test_target_statistics_used": False,
    }
    all_core_pass = all(core.values())
    if not all_core_pass:
        verdict = "STOP_MIMIC_IV_ADAPTER_INVALID"
    elif not any(final_stats[role].get("mapped_rows", 0) for role in ("train", "dev")):
        verdict = "STOP_MIMIC_IV_NORMALIZATION_UNUSABLE"
    elif ddi["projected_medication_vocab_size"] == 0 or not all(ddi["projection_checks"].values()):
        verdict = "STOP_MIMIC_IV_DDI_PROJECTION_UNUSABLE"
    else:
        verdict = "MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV"
    checks["verdict"] = verdict
    checks["all_core_pass"] = all_core_pass
    public_manifest["mechanical_verdict"] = verdict
    public_manifest["mechanical_checks"] = {
        name: "PASS" if value else "FAIL" for name, value in core.items()
    }
    public_manifest["mechanical_checks"].update(
        {
            "NORMALIZATION_COVERAGE_REPORTED": "REPORTED",
            "MEDICATION_TARGET_OOV_REPORTED": "REPORTED",
            "DDI_PROJECTION_COVERAGE_REPORTED": "REPORTED",
        }
    )
    public_manifest["manifest_sha256"] = hashlib.sha256(canonical_json(public_manifest)).hexdigest()

    (public_dir / "manifest.json").write_bytes(canonical_json(public_manifest))
    (public_dir / "mechanical-checks.json").write_bytes(canonical_json(checks))
    (public_dir / "protocol.json").write_bytes(
        canonical_json(
            {
                "schema_version": 1,
                "benchmark_id": BENCHMARK_ID,
                "stage": STAGE,
                "source_release": SOURCE_RELEASE,
                "task": "(current D_t, current P_t, strictly previous (D_j,P_j,M_j)) -> current M_t",
                "granularity": "visit/admission-level medication set",
                "current_target_entitlement": "target-only; no current medication row/statistic/embedding/DDI feature in input",
                "history_entitlement": "j < t only; chronology admittime then hadm_id",
                "medication_representation": "ATC4 SafeDrug/MoleRec four-character identity from upstream ATC4 field prefix [:4]",
                "split": {
                    "patient_level": True,
                    "roles": "2/3 Train, 1/6 Dev, 1/6 untouched Test",
                    "algorithm": public_manifest["split"]["algorithm"],
                    "salt": SPLIT_SALT,
                },
                "vocabulary": "diagnosis/procedure Train-only with explicit <UNK>; medication target vocabulary Train-observed only; Dev OOV reported",
                "normalization": public_manifest["normalization_lineage"],
                "ddi": "frozen SafeDrug/MoleRec authority projected by exact medication identity; no added pairs; coverage reported",
                "metrics": ["Jaccard", "F1", "PRAUC", "DDI", "NLL"],
                "decoder_threshold": 0.35,
                "checkpoint": "highest complete Dev Jaccard, earliest exact tie",
                "test_policy": public_manifest["test_policy"],
                "status": "frozen_for_traindev_materialization_no_training",
            }
        )
    )
    return {"verdict": verdict, "manifest": public_manifest, "checks": checks}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mimic-hosp", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--ddi-snapshot", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="restricted output, outside this checkout"
    )
    parser.add_argument(
        "--public-output-dir",
        type=Path,
        required=True,
        help="aggregate output staging, outside this checkout",
    )
    parser.add_argument("--source-revision", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = materialize(parse_args(argv or sys.argv[1:]))
    except AdapterError as exc:
        print(
            json.dumps(
                {"verdict": "STOP_MIMIC_IV_ADAPTER_INVALID", "error": str(exc)}, sort_keys=True
            )
        )
        return 2
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "manifest_sha256": result["manifest"]["manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["verdict"] == "MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV" else 2


if __name__ == "__main__":
    raise SystemExit(main())
