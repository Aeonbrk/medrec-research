"""Run the frozen Strict Drug-Changing Supportability audit.

The runner is deliberately bounded.  It reconstructs the previously admitted
directional POE relation, verifies its 1,040-event identity, and then computes
only the eleven frozen supportability aggregates.  Patient/order identifiers
remain in restricted process memory and never enter the output artifacts.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from bisect import bisect_right
from pathlib import Path
from typing import Any

import pandas as pd

TARGET_REVISION = "15b3cffe42dd08cbfc9e2d8bf34ee766520a67a2"
EXPECTED_STRICT_EVENTS = 1040
WINDOW_SECONDS = 600
R0_SALT = "exposure-reset-20260905"
R0_HOLDOUT_THRESHOLD = 0.85
DISCOVERY_THRESHOLD = 0.70
CHUNKSIZE = 250_000
ALLOWED_GROUPS = {
    "2008 - 2010": "G0",
    "2011 - 2013": "G1",
    "2014 - 2016": "G2",
}

REQUIRED_COLUMNS = {
    "patients": {"subject_id", "anchor_year", "anchor_year_group"},
    "poe": {
        "poe_id",
        "poe_seq",
        "subject_id",
        "hadm_id",
        "ordertime",
        "order_type",
        "transaction_type",
        "discontinue_of_poe_id",
        "order_provider_id",
    },
    "prescriptions": {
        "subject_id",
        "poe_id",
        "pharmacy_id",
        "ndc",
        "formulary_drug_cd",
    },
}

EXPECTED_CRITERIA = {
    "C1_total_support": {"op": ">=", "value": 500},
    "C2_patient_breadth": {"op": ">=", "value": 200},
    "C3_patient_concentration": {"op": ">=", "value": 150},
    "C4_admission_contexts": {"op": ">=", "value": 250},
    "C5_source_breadth": {"op": ">=", "value": 20},
    "C6_source_recurrence": {"op": ">=", "value": 15},
    "C7_source_concentration": {"op": ">=", "value": 10},
    "C8_destination_breadth": {"op": ">=", "value": 20},
    "C9_destination_concentration": {"op": ">=", "value": 10},
    "C10_temporal_event_width": {"op": ">=", "value": 0.20},
    "C11_temporal_patient_width": {"op": ">=", "value": 0.20},
}


class ImplementationMismatch(RuntimeError):
    """Raised when re-materialization is not the frozen semantic object."""


def zip_strict(*iterables: Any) -> Any:
    """Python 3.8-compatible equivalent of ``zip(..., strict=True)``."""
    sentinel = object()
    for values in itertools.zip_longest(*iterables, fillvalue=sentinel):
        if any(value is sentinel for value in values):
            raise ImplementationMismatch("internal iterable length mismatch")
        yield values


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text in {"", "nan", "NaN", "<NA>", "None"}:
        return ""
    return text


def as_int(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return None


def table_path(mimic_dir: Path, name: str) -> Path:
    gz = mimic_dir / f"{name}.csv.gz"
    plain = mimic_dir / f"{name}.csv"
    if gz.exists():
        return gz
    if plain.exists():
        return plain
    raise ImplementationMismatch(f"missing required MIMIC table: {name}")


def subject_unit_interval(subject_id: int, salt: str = R0_SALT) -> float:
    token = f"{subject_id}|{salt}".encode()
    digest = hashlib.sha256(token).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF


def verify_execution_checkout(repo_root: Path) -> None:
    head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1"], text=True
    )
    if head != TARGET_REVISION or status:
        raise ImplementationMismatch(
            f"execution checkout must be clean at {TARGET_REVISION}; observed {head!r}"
        )


def read_frozen_protocol(protocol_path: Path) -> dict[str, Any]:
    text = protocol_path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match is None:
        raise ImplementationMismatch("protocol machine-readable block is missing")
    try:
        spec = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ImplementationMismatch("protocol machine-readable block is invalid") from exc
    if spec.get("protocol") != "STRICT_DRUG_CHANGING_SUPPORTABILITY":
        raise ImplementationMismatch("protocol identity mismatch")
    if spec.get("expected_strict_events") != EXPECTED_STRICT_EVENTS:
        raise ImplementationMismatch("protocol semantic identity mismatch")
    if spec.get("criteria") != EXPECTED_CRITERIA:
        raise ImplementationMismatch("protocol criteria differ from frozen runner contract")
    return spec


def check_schema(mimic_dir: Path) -> None:
    for table, required in REQUIRED_COLUMNS.items():
        columns = set(pd.read_csv(table_path(mimic_dir, table), nrows=0).columns)
        missing = sorted(required - columns)
        if missing:
            raise ImplementationMismatch(f"missing fields in {table}: {missing}")


def normalize_ndc(value: Any) -> str:
    text = clean_text(value)
    if text in {"0", "0.0", "<NA>", "nan"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return re.sub(r"[^0-9]", "", text)


def mapping_keys(value: Any) -> tuple[str, ...]:
    text = normalize_ndc(value)
    return (text, text.zfill(11)) if text else ()


def build_ndc_mapping(mapping_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    safe_frame = pd.read_csv(mapping_dir / "ndc2atc_level4.csv")
    for row in safe_frame.itertuples(index=False):
        atc = clean_text(row.ATC4)[:4]
        if len(atc) == 4:
            for key in mapping_keys(row.NDC):
                mapping[key] = atc

    kgd_frame = pd.read_csv(mapping_dir / "drug_codes_mapping.csv")
    for row in kgd_frame.itertuples(index=False):
        atc = clean_text(row.atc4)[:4]
        if len(atc) == 4 and atc != "nan":
            for key in mapping_keys(row.ndc):
                mapping[key] = atc
    return mapping


def lookup_atc(value: Any, mapping: dict[str, str]) -> str | None:
    for key in mapping_keys(value):
        if key in mapping:
            return mapping[key]
    return None


def load_vocabulary(vocab_dir: Path) -> set[str]:
    import dill

    with (vocab_dir / "voc_final.pkl").open("rb") as handle:
        vocabulary = dill.load(handle)
    idx2word = vocabulary["med_voc"].idx2word
    codes = [str(idx2word[index]) for index in range(131)]
    if len(codes) != 131 or len(set(codes)) != 131 or any(len(code) != 4 for code in codes):
        raise ImplementationMismatch("frozen medication vocabulary is not 131 unique ATC-L4 codes")
    return set(codes)


def load_population(mimic_dir: Path) -> tuple[dict[int, tuple[int, str]], set[int], set[int]]:
    """Load only admitted patient metadata and derive the existing R0 split."""

    patients: dict[int, tuple[int, str]] = {}
    allowed: set[int] = set()
    discovery: set[int] = set()
    dtype = {"subject_id": "Int64", "anchor_year": "Int64", "anchor_year_group": "string"}
    for chunk in pd.read_csv(
        table_path(mimic_dir, "patients"),
        usecols=sorted(REQUIRED_COLUMNS["patients"]),
        dtype=dtype,
        compression="infer",
        chunksize=CHUNKSIZE,
        low_memory=False,
    ):
        for row in chunk.itertuples(index=False):
            subject_id = as_int(row.subject_id)
            anchor_year = as_int(row.anchor_year)
            group = clean_text(row.anchor_year_group)
            if subject_id is None or anchor_year is None or group not in ALLOWED_GROUPS:
                continue
            u = subject_unit_interval(subject_id)
            if u >= R0_HOLDOUT_THRESHOLD:
                continue
            patients[subject_id] = (anchor_year, ALLOWED_GROUPS[group])
            allowed.add(subject_id)
            if u < DISCOVERY_THRESHOLD:
                discovery.add(subject_id)
    if not patients or not discovery:
        raise ImplementationMismatch("admitted G0-G2/R0 population is empty")
    return patients, allowed, discovery


def iter_prescription_chunks(mimic_dir: Path, subjects: set[int], usecols: list[str]) -> Any:
    dtype = {
        "subject_id": "Int64",
        "poe_id": "string",
        "pharmacy_id": "string",
        "ndc": "string",
        "formulary_drug_cd": "string",
    }
    for chunk in pd.read_csv(
        table_path(mimic_dir, "prescriptions"),
        usecols=usecols,
        dtype={key: dtype[key] for key in usecols},
        compression="infer",
        chunksize=CHUNKSIZE,
        low_memory=False,
    ):
        selected = chunk.loc[chunk["subject_id"].isin(subjects)]
        if not selected.empty:
            yield selected


def build_poe_identity_map(
    mimic_dir: Path,
    allowed_subjects: set[int],
    discovery_subjects: set[int],
    mapping: dict[str, str],
    vocabulary: set[str],
) -> dict[str, set[str]]:
    """Reuse gate01_data's direct-NDC then 85% Discovery formulary lineage."""

    usecols = ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"]
    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for chunk in iter_prescription_chunks(mimic_dir, discovery_subjects, usecols):
        for row in chunk.itertuples(index=False):
            atc = lookup_atc(row.ndc, mapping)
            formulary = clean_text(row.formulary_drug_cd)
            if atc in vocabulary and formulary:
                counts[formulary][atc] += 1

    consensus: dict[str, str] = {}
    for formulary, counter in counts.items():
        atc, top_count = counter.most_common(1)[0]
        if top_count / sum(counter.values()) >= 0.85:
            consensus[formulary] = atc

    poe_to_atcs: dict[str, set[str]] = collections.defaultdict(set)
    for chunk in iter_prescription_chunks(mimic_dir, allowed_subjects, usecols):
        for row in chunk.itertuples(index=False):
            poe_id = clean_text(row.poe_id)
            if not poe_id:
                continue
            atc = lookup_atc(row.ndc, mapping)
            if atc not in vocabulary:
                atc = consensus.get(clean_text(row.formulary_drug_cd))
            if atc in vocabulary:
                poe_to_atcs[poe_id].add(atc)
    return poe_to_atcs


def parse_time_series(series: pd.Series) -> list[int | None]:
    parsed = pd.to_datetime(series, errors="coerce")
    valid = (~parsed.isna()).to_numpy()
    values = parsed.astype("int64").to_numpy()
    return [int(value // 1_000_000_000) if ok else None for value, ok in zip_strict(values, valid)]


def read_poe_orders(
    mimic_dir: Path,
    patients: dict[int, tuple[int, str]],
    allowed_subjects: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    usecols = sorted(REQUIRED_COLUMNS["poe"])
    dtype = {
        "poe_id": "string",
        "poe_seq": "string",
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "ordertime": "string",
        "order_type": "string",
        "transaction_type": "string",
        "discontinue_of_poe_id": "string",
        "order_provider_id": "string",
    }
    source_dc: list[dict[str, Any]] = []
    new_orders: list[dict[str, Any]] = []
    old_refs: set[str] = set()
    row_index = 0
    for chunk in pd.read_csv(
        table_path(mimic_dir, "poe"),
        usecols=usecols,
        dtype=dtype,
        compression="infer",
        chunksize=CHUNKSIZE,
        low_memory=False,
    ):
        selected = chunk.loc[chunk["subject_id"].isin(allowed_subjects)]
        if selected.empty:
            continue
        epochs = parse_time_series(selected["ordertime"])
        for row, order_time in zip_strict(selected.itertuples(index=False), epochs):
            order_type = clean_text(row.order_type)
            transaction_type = clean_text(row.transaction_type)
            record_index = row_index
            row_index += 1
            if order_type != "Medications" or transaction_type not in {"D/C", "New"}:
                continue
            subject_id = as_int(row.subject_id)
            if subject_id is None or subject_id not in patients:
                continue
            record = {
                "row_index": record_index,
                "poe_id": clean_text(row.poe_id),
                "poe_seq": as_int(row.poe_seq),
                "subject_id": subject_id,
                "hadm_id": as_int(row.hadm_id),
                "ordertime": order_time,
                "order_type": order_type,
                "transaction_type": transaction_type,
                "discontinue_of_poe_id": clean_text(row.discontinue_of_poe_id),
                "order_provider_id": clean_text(row.order_provider_id),
            }
            if transaction_type == "D/C":
                source_dc.append(record)
                if record["discontinue_of_poe_id"]:
                    old_refs.add(record["discontinue_of_poe_id"])
            else:
                new_orders.append(record)
    return source_dc, new_orders, old_refs


def read_referenced_old_rows(
    mimic_dir: Path, allowed_subjects: set[int], old_refs: set[str]
) -> dict[str, list[dict[str, Any]]]:
    old_rows: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    if not old_refs:
        return old_rows
    usecols = sorted(REQUIRED_COLUMNS["poe"])
    dtype = {
        "poe_id": "string",
        "poe_seq": "string",
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "ordertime": "string",
        "order_type": "string",
        "transaction_type": "string",
        "discontinue_of_poe_id": "string",
        "order_provider_id": "string",
    }
    for chunk in pd.read_csv(
        table_path(mimic_dir, "poe"),
        usecols=usecols,
        dtype=dtype,
        compression="infer",
        chunksize=CHUNKSIZE,
        low_memory=False,
    ):
        selected = chunk.loc[chunk["subject_id"].isin(allowed_subjects)]
        if selected.empty:
            continue
        ids = selected["poe_id"].map(clean_text)
        selected = selected.loc[ids.isin(old_refs)]
        if selected.empty:
            continue
        epochs = parse_time_series(selected["ordertime"])
        for row, order_time in zip_strict(selected.itertuples(index=False), epochs):
            poe_id = clean_text(row.poe_id)
            old_rows[poe_id].append(
                {
                    "poe_id": poe_id,
                    "poe_seq": as_int(row.poe_seq),
                    "subject_id": as_int(row.subject_id),
                    "hadm_id": as_int(row.hadm_id),
                    "ordertime": order_time,
                    "order_type": clean_text(row.order_type),
                    "transaction_type": clean_text(row.transaction_type),
                    "order_provider_id": clean_text(row.order_provider_id),
                }
            )
    return old_rows


def construct_strict_events(
    source_dc: list[dict[str, Any]],
    new_orders: list[dict[str, Any]],
    old_refs: set[str],
    old_rows: dict[str, list[dict[str, Any]]],
    poe_to_atcs: dict[str, set[str]],
    patients: dict[int, tuple[int, str]],
) -> tuple[list[dict[str, Any]], collections.Counter[str], collections.Counter[str]]:
    """Construct complete candidate relations, then apply one-to-one rules."""

    flow: collections.Counter[str] = collections.Counter()
    flow["medication_dc_rows"] = len(source_dc)
    eligible_sources: list[dict[str, Any]] = []
    for source in source_dc:
        ref = source["discontinue_of_poe_id"]
        referenced = old_rows.get(ref, []) if ref else []
        if not ref or len(referenced) != 1 or referenced[0]["order_type"] != "Medications":
            flow["invalid_or_missing_explicit_old_link"] += 1
            continue
        old = referenced[0]
        same_subject = old["subject_id"] == source["subject_id"]
        same_hadm = (
            old["hadm_id"] is not None
            and source["hadm_id"] is not None
            and old["hadm_id"] == source["hadm_id"]
        )
        same_provider = (
            bool(old["order_provider_id"])
            and bool(source["order_provider_id"])
            and (old["order_provider_id"] == source["order_provider_id"])
        )
        if not (same_subject and same_hadm and same_provider):
            flow["patient_hadm_provider_mismatch_or_missing"] += 1
            continue
        delta = (
            source["ordertime"] - old["ordertime"]
            if source["ordertime"] is not None and old["ordertime"] is not None
            else None
        )
        if (
            delta is None
            or delta < 0
            or delta > WINDOW_SECONDS
            or old["poe_seq"] is None
            or source["poe_seq"] is None
            or old["poe_seq"] >= source["poe_seq"]
        ):
            flow["timing_or_poe_seq_failure"] += 1
            continue
        old_identity = poe_to_atcs.get(old["poe_id"], set())
        if len(old_identity) != 1:
            flow["old_identity_unresolved"] += 1
            continue
        eligible_sources.append(
            {
                "source": source,
                "old": old,
                "old_key": (old["subject_id"], old["hadm_id"], old["poe_id"]),
                "old_identity": next(iter(old_identity)),
            }
        )

    flow["eligible_explicit_source_dc"] = len(eligible_sources)

    indexed_new: list[dict[str, Any]] = []
    new_by_context: dict[tuple[int, int, str], list[int]] = collections.defaultdict(list)
    for new in new_orders:
        if (
            new["subject_id"] is None
            or new["hadm_id"] is None
            or not new["order_provider_id"]
            or new["ordertime"] is None
            or new["poe_seq"] is None
            or not new["poe_id"]
        ):
            continue
        identity = poe_to_atcs.get(new["poe_id"], set())
        if len(identity) != 1:
            continue
        index = len(indexed_new)
        indexed_new.append({"record": new, "identity": next(iter(identity))})
        new_by_context[(new["subject_id"], new["hadm_id"], new["order_provider_id"])].append(index)

    context_times: dict[tuple[int, int, str], list[int]] = {}
    for context, indices in new_by_context.items():
        indices.sort(
            key=lambda idx: (
                indexed_new[idx]["record"]["ordertime"],
                indexed_new[idx]["record"]["poe_seq"],
                indexed_new[idx]["record"]["poe_id"],
            )
        )
        context_times[context] = [indexed_new[idx]["record"]["ordertime"] for idx in indices]

    old_degree: collections.Counter[Any] = collections.Counter(
        item["old_key"] for item in eligible_sources
    )
    candidate_sets: list[list[int]] = []
    reverse_degree: collections.Counter[int] = collections.Counter()
    for item in eligible_sources:
        source = item["source"]
        context = (source["subject_id"], source["hadm_id"], source["order_provider_id"])
        indices = new_by_context.get(context, [])
        times = context_times.get(context, [])
        left = bisect_right(times, source["ordertime"])
        right = bisect_right(times, source["ordertime"] + WINDOW_SECONDS)
        candidates = [
            new_index
            for new_index in indices[left:right]
            if indexed_new[new_index]["record"]["poe_seq"] > source["poe_seq"]
        ]
        candidate_sets.append(candidates)
        reverse_degree.update(candidates)

    flow["zero_eligible_post_dc_new"] = sum(len(candidates) == 0 for candidates in candidate_sets)
    flow["dc_out_degree_gt_1"] = sum(len(candidates) > 1 for candidates in candidate_sets)
    flow["old_order_source_degree_gt_1"] = sum(
        old_degree[item["old_key"]] > 1 for item in eligible_sources
    )
    flow["old_orders_with_source_degree_gt_1"] = sum(degree > 1 for degree in old_degree.values())
    flow["new_reverse_in_degree_gt_1"] = sum(degree > 1 for degree in reverse_degree.values())
    flow["singleton_sources_affected_by_new_reverse_in_degree_gt_1"] = sum(
        len(candidates) == 1 and reverse_degree[candidates[0]] > 1 for candidates in candidate_sets
    )

    relation_candidates: list[dict[str, Any]] = []
    for index, item in enumerate(eligible_sources):
        candidates = candidate_sets[index]
        if old_degree[item["old_key"]] != 1 or len(candidates) != 1:
            continue
        new_index = candidates[0]
        if reverse_degree[new_index] != 1:
            continue
        new_item = indexed_new[new_index]
        relation_candidates.append(
            {
                "source": item["source"],
                "old": item["old"],
                "new": new_item["record"],
                "old_identity": item["old_identity"],
                "new_identity": new_item["identity"],
                "candidate_set": candidates,
                "old_key": item["old_key"],
            }
        )

    flow["same_medrec_action_identity"] = sum(
        item["old_identity"] == item["new_identity"] for item in relation_candidates
    )
    strict = [item for item in relation_candidates if item["old_identity"] != item["new_identity"]]

    violations: collections.Counter[str] = collections.Counter()
    for item in strict:
        source = item["source"]
        old = item["old"]
        new = item["new"]
        if source["discontinue_of_poe_id"] != old["poe_id"]:
            violations["explicit_old_link"] += 1
        if source["transaction_type"] != "D/C" or source["order_type"] != "Medications":
            violations["source_medication_dc"] += 1
        if old["order_type"] != "Medications":
            violations["old_order_type_medications"] += 1
        if new["order_type"] != "Medications" or new["transaction_type"] != "New":
            violations["new_medication_order"] += 1
        if old["subject_id"] != source["subject_id"] or new["subject_id"] != source["subject_id"]:
            violations["same_subject"] += 1
        if (
            old["hadm_id"] is None
            or source["hadm_id"] is None
            or new["hadm_id"] is None
            or old["hadm_id"] != source["hadm_id"]
            or new["hadm_id"] != source["hadm_id"]
        ):
            violations["same_nonnull_hadm"] += 1
        if (
            not source["order_provider_id"]
            or old["order_provider_id"] != source["order_provider_id"]
            or new["order_provider_id"] != source["order_provider_id"]
        ):
            violations["same_nonnull_provider"] += 1
        if (
            old["ordertime"] is None
            or source["ordertime"] is None
            or source["ordertime"] - old["ordertime"] < 0
            or source["ordertime"] - old["ordertime"] > WINDOW_SECONDS
        ):
            violations["old_to_dc_timing"] += 1
        if (
            new["ordertime"] is None
            or source["ordertime"] is None
            or new["ordertime"] - source["ordertime"] <= 0
            or new["ordertime"] - source["ordertime"] > WINDOW_SECONDS
        ):
            violations["dc_to_new_timing"] += 1
        if (
            old["poe_seq"] is None
            or source["poe_seq"] is None
            or new["poe_seq"] is None
            or old["poe_seq"] >= source["poe_seq"]
        ):
            violations["old_to_dc_poe_seq"] += 1
        if source["poe_seq"] is None or new["poe_seq"] <= source["poe_seq"]:
            violations["dc_to_new_poe_seq"] += 1
        if len(poe_to_atcs.get(old["poe_id"], set())) != 1:
            violations["old_identity_singleton"] += 1
        if len(poe_to_atcs.get(new["poe_id"], set())) != 1:
            violations["new_identity_singleton"] += 1
        if old_degree[item["old_key"]] != 1:
            violations["old_source_degree"] += 1
        if len(item["candidate_set"]) != 1:
            violations["dc_out_degree"] += 1
        if reverse_degree[item["candidate_set"][0]] != 1:
            violations["new_reverse_in_degree"] += 1
        if item["old_identity"] == item["new_identity"]:
            violations["different_medrec_identity"] += 1

    if violations:
        raise ImplementationMismatch(
            f"frozen invariant violations: {dict(sorted(violations.items()))}"
        )
    return strict, flow, violations


def effective_count(counts: collections.Counter[Any]) -> float:
    if not counts:
        return 0.0
    total = sum(counts.values())
    denominator = sum(value * value for value in counts.values())
    return (total * total) / denominator if denominator else 0.0


def evaluate_supportability(
    strict: list[dict[str, Any]], patients: dict[int, tuple[int, str]]
) -> dict[str, Any]:
    n = len(strict)
    patient_counts: collections.Counter[int] = collections.Counter(
        item["source"]["subject_id"] for item in strict
    )
    admission_ids = {item["source"]["hadm_id"] for item in strict}
    source_counts: collections.Counter[str] = collections.Counter(
        item["old_identity"] for item in strict
    )
    destination_counts: collections.Counter[str] = collections.Counter(
        item["new_identity"] for item in strict
    )
    source_patients: dict[str, set[int]] = collections.defaultdict(set)
    for item in strict:
        source_patients[item["old_identity"]].add(item["source"]["subject_id"])

    group_events: collections.Counter[str] = collections.Counter()
    group_patients: dict[str, set[int]] = {group: set() for group in ("G0", "G1", "G2")}
    for item in strict:
        subject_id = item["source"]["subject_id"]
        group = patients[subject_id][1]
        group_events[group] += 1
        group_patients[group].add(subject_id)

    event_shares = [group_events[group] / n if n else 0.0 for group in ("G0", "G1", "G2")]
    patient_total = len(patient_counts)
    patient_shares = [
        len(group_patients[group]) / patient_total if patient_total else 0.0
        for group in ("G0", "G1", "G2")
    ]
    second_event_share = sorted(event_shares, reverse=True)[1]
    second_patient_share = sorted(patient_shares, reverse=True)[1]

    support = {
        "strict_events": n,
        "unique_patients": patient_total,
        "effective_patients": effective_count(patient_counts),
        "unique_admissions": len(admission_ids),
        "unique_source_actions": len(source_counts),
        "recurrent_source_actions_ge_10_patients": sum(
            len(subjects) >= 10 for subjects in source_patients.values()
        ),
        "effective_source_actions": effective_count(source_counts),
        "unique_destination_actions": len(destination_counts),
        "effective_destination_actions": effective_count(destination_counts),
    }
    temporal_support: dict[str, Any] = {}
    for group in ("G0", "G1", "G2"):
        temporal_support[group] = {
            "strict_events": group_events[group],
            "unique_patients": len(group_patients[group]),
            "event_share": group_events[group] / n if n else 0.0,
            "patient_share": len(group_patients[group]) / patient_total if patient_total else 0.0,
        }
    temporal_support["second_largest_event_share"] = second_event_share
    temporal_support["second_largest_patient_share"] = second_patient_share

    criteria = {
        "C1_total_support": n >= 500,
        "C2_patient_breadth": patient_total >= 200,
        "C3_patient_concentration": support["effective_patients"] >= 150,
        "C4_admission_contexts": support["unique_admissions"] >= 250,
        "C5_source_breadth": support["unique_source_actions"] >= 20,
        "C6_source_recurrence": support["recurrent_source_actions_ge_10_patients"] >= 15,
        "C7_source_concentration": support["effective_source_actions"] >= 10,
        "C8_destination_breadth": support["unique_destination_actions"] >= 20,
        "C9_destination_concentration": support["effective_destination_actions"] >= 10,
        "C10_temporal_event_width": second_event_share >= 0.20,
        "C11_temporal_patient_width": second_patient_share >= 0.20,
    }
    verdict = (
        "PASS_STRICT_DRUG_CHANGING_SUPPORTABILITY"
        if all(criteria.values())
        else "ABANDON_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_STRICT_TRACE_SUPPORT"
    )
    return {
        "protocol": "STRICT_DRUG_CHANGING_SUPPORTABILITY",
        "starting_revision": TARGET_REVISION,
        "semantic_admission": "PASS_SEMANTIC_ADMISSION",
        "semantic_object_integrity": {
            "strict_events_expected": EXPECTED_STRICT_EVENTS,
            "strict_events_observed": n,
            "frozen_invariant_violations": 0,
        },
        "support": support,
        "temporal_support": temporal_support,
        "criteria": criteria,
        "verdict": verdict,
        "quarantine": {
            "G3_G4_accessed": False,
            "R0_holdout_accessed": False,
            "historical_project_test_accessed": False,
        },
    }


def decision_markdown(summary: dict[str, Any]) -> str:
    question = (
        "Under the already frozen strict drug-changing order-revision semantics, "
        "is the admitted supervision sufficiently large, patient-distributed, "
        "recurrent on the source side, medication-diverse, and non-concentrated "
        "to justify one subsequent bounded test of incremental learning value?"
    )
    lines = [
        "# Strict Drug-Changing Supportability Decision",
        "",
        "## Scientific question",
        "",
        question,
        "",
        "## Semantic-object integrity",
        "",
        (
            f"`PASS_SEMANTIC_ADMISSION` was re-materialized at the frozen revision: "
            f"{summary['semantic_object_integrity']['strict_events_observed']} strict "
            "events observed (expected 1,040), with zero frozen-invariant violations. "
            "Candidate New sets were complete before identity-difference filtering; no "
            "nearest/first matching or tie-breaking was used."
        ),
        "",
        "## Frozen criteria",
        "",
        "| Criterion | Value | Status |",
        "| --- | ---: | :---: |",
    ]
    values = {
        "C1_total_support": summary["support"]["strict_events"],
        "C2_patient_breadth": summary["support"]["unique_patients"],
        "C3_patient_concentration": summary["support"]["effective_patients"],
        "C4_admission_contexts": summary["support"]["unique_admissions"],
        "C5_source_breadth": summary["support"]["unique_source_actions"],
        "C6_source_recurrence": summary["support"]["recurrent_source_actions_ge_10_patients"],
        "C7_source_concentration": summary["support"]["effective_source_actions"],
        "C8_destination_breadth": summary["support"]["unique_destination_actions"],
        "C9_destination_concentration": summary["support"]["effective_destination_actions"],
        "C10_temporal_event_width": summary["temporal_support"]["second_largest_event_share"],
        "C11_temporal_patient_width": summary["temporal_support"]["second_largest_patient_share"],
    }
    for key, value in values.items():
        lines.append(f"| `{key}` | `{value}` | {'PASS' if summary['criteria'][key] else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"`{summary['verdict']}`",
            "",
            "No predictive value, treatment effect, replacement/correction meaning, "
            "clinical correctness, or causal superiority is inferred.",
            "",
            "## Quarantine",
            "",
            "G3/G4, R0 Holdout, and the historical project test were not accessed; "
            "no model, prediction, outcome, or pair-specific statistic was computed.",
            "",
            "## Next-stage boundary",
            "",
            (
                "If this pass stands, the only authorized next scientific stage is "
                "`Pair/Context Incremental Value`; it requires a fresh frozen design "
                "and is not executed in this round."
                if summary["verdict"] == "PASS_STRICT_DRUG_CHANGING_SUPPORTABILITY"
                else "The candidate is terminated under the present frozen definition; no rescue is authorized."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def run(args: argparse.Namespace) -> dict[str, Any]:
    # This is intentionally the first operation touching the execution checkout.
    verify_execution_checkout(args.repo_root)
    read_frozen_protocol(args.protocol)
    # The schema check opens headers only and occurs before any data row is read.
    verify_execution_checkout(args.repo_root)
    check_schema(args.mimic_dir)

    patients, allowed_subjects, discovery_subjects = load_population(args.mimic_dir)
    mapping = build_ndc_mapping(args.mapping_dir)
    vocabulary = load_vocabulary(args.vocab_dir)
    source_dc, new_orders, old_refs = read_poe_orders(args.mimic_dir, patients, allowed_subjects)
    poe_to_atcs = build_poe_identity_map(
        args.mimic_dir, allowed_subjects, discovery_subjects, mapping, vocabulary
    )
    old_rows = read_referenced_old_rows(args.mimic_dir, allowed_subjects, old_refs)
    strict, _flow, _violations = construct_strict_events(
        source_dc, new_orders, old_refs, old_rows, poe_to_atcs, patients
    )
    if len(strict) != EXPECTED_STRICT_EVENTS:
        raise ImplementationMismatch(
            f"strict semantic identity mismatch: expected {EXPECTED_STRICT_EVENTS}, observed {len(strict)}"
        )
    summary = evaluate_supportability(strict, patients)
    verify_execution_checkout(args.repo_root)
    write_atomic(
        args.summary, json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    )
    write_atomic(args.decision, decision_markdown(summary))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--mimic-dir", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--vocab-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    try:
        result = run(arguments)
    except ImplementationMismatch as exc:
        print(f"IMPLEMENTATION_MISMATCH: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "strict_events": result["support"]["strict_events"],
                "criteria": result["criteria"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
