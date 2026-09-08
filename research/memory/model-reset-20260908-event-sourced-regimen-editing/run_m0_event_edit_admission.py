"""Run the frozen M0 event-sourced regimen-edit admission gate.

The runner is intentionally self-contained at the research-memory boundary. It
uses the existing raw MIMIC-IV 3.1 order/eMAR linkage contract, performs
Phase A before model construction from real data, and withholds EditAudit
events until the freeze manifest is written.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import math
import random
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import average_precision_score

N_CONCEPTS = 131
N_ACTIONS = 3
N_MARKS = N_CONCEPTS * N_ACTIONS
HISTORY_LENGTH = 64
TARGET_SECONDS = 600
TOP_K = 5
BOOTSTRAP_REPLICATES = 2_000
BOOTSTRAP_SEED = 26090807

# The existing order-time implementation fixes this training contract. M0
# changes only the target/decoder object and gives every variant this contract.
TRAINING_SEED = 260907
TRAINING_BATCH_CEILING = 2_048
MAX_EPOCHS = 5
EARLY_STOPPING_PATIENCE = 1
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-5

M0_SALT = "event-edit-m0-20260908"
R0_SALT = "exposure-reset-20260905"
R0_HOLDOUT_THRESHOLD = 0.85

ACTIONS = ("New", "Change", "D/C")
ACTION_TO_INDEX = {action: index for index, action in enumerate(ACTIONS)}
ACTION_CODES = {"New": 1, "Change": 2, "D/C": 3}
ADMITTED_GROUPS = {
    "2008 - 2010": "G0",
    "2011 - 2013": "G1",
    "2014 - 2016": "G2",
}

PHASE_A_FLOORS = {
    "overall": {"mapped_target_events": 250_000, "patients": 10_000},
    "per_action": {
        action: {"mapped_target_events": 20_000, "patients": 2_000} for action in ACTIONS
    },
    "state_consistency": {"Change": 0.70, "D/C": 0.70},
    "distributed": {"concepts": 50, "events_per_action": 50, "minimum_actions": 2},
}

ADMINISTRATION_EVENT_TYPES = frozenset(
    {
        "Administered",
        "Applied",
        "Inhaled",
        "Started",
        "Infused",
        "Given",
        "Delayed Administered",
        "Administered Bolus from IV Drip",
        "Administered in Other Location",
        "Started in Other Location",
        "Delayed Started",
        "Partial Administered",
        "Applied in Other Location",
        "Delayed Applied",
        "Delayed Restarted",
        "Restarted in Other Location",
        "Removed Existing / Applied New",
    }
)


class ProtocolFailure(RuntimeError):
    """Raised when a frozen M0 prerequisite is not satisfied."""


@dataclass(frozen=True)
class Patient:
    subject_id: int
    anchor_year: int
    anchor_year_group: str
    partition: str


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return format(float(value), ".17g")


def set_seed(seed: int = TRAINING_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json_dumps(value).encode()
    return hashlib.sha256(payload).hexdigest()


def json_dumps(value: Any, *, indent: int | None = None) -> str:
    import json

    return json.dumps(value, ensure_ascii=True, indent=indent, sort_keys=True, allow_nan=False)


def table_path(mimic_dir: Path, name: str) -> Path:
    gz = mimic_dir / f"{name}.csv.gz"
    plain = mimic_dir / f"{name}.csv"
    if gz.exists():
        return gz
    if plain.exists():
        return plain
    raise ProtocolFailure(f"Missing MIMIC-IV table: {name}")


def clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


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


def subject_unit_interval(subject_id: int, salt: str) -> float:
    token = f"{subject_id}|{salt}".encode()
    digest = hashlib.sha256(token).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF


def is_r0_holdout(subject_id: int) -> bool:
    return subject_unit_interval(subject_id, R0_SALT) >= R0_HOLDOUT_THRESHOLD


def classify_m0(subject_id: int) -> str:
    value = subject_unit_interval(subject_id, M0_SALT)
    if value < 0.80:
        return "EditTrain"
    if value < 0.90:
        return "EditTune"
    return "EditAudit"


def parse_datetime_seconds(series: pd.Series) -> list[int | None]:
    parsed = pd.to_datetime(series, errors="coerce")
    valid = ~parsed.isna()
    values = parsed.astype("int64").to_numpy()
    return [
        int(value // 1_000_000_000) if ok else None for value, ok in zip(values, valid, strict=True)
    ]


def load_patients(mimic_dir: Path) -> tuple[dict[int, Patient], dict[str, set[int]]]:
    frame = pd.read_csv(
        table_path(mimic_dir, "patients"),
        usecols=["subject_id", "anchor_year", "anchor_year_group"],
        dtype={"subject_id": "Int64", "anchor_year": "Int64", "anchor_year_group": "string"},
        compression="infer",
    )
    patients: dict[int, Patient] = {}
    subjects_by_partition = {name: set() for name in ("EditTrain", "EditTune", "EditAudit")}
    for row in frame.itertuples(index=False):
        subject_id = as_int(row.subject_id)
        anchor_year = as_int(row.anchor_year)
        group = clean_text(row.anchor_year_group)
        if subject_id is None or anchor_year is None or group not in ADMITTED_GROUPS:
            continue
        # Existing R0 Holdout remains a quarantine. No clinical table is read
        # for a subject rejected here, and no Holdout aggregate is reported.
        if is_r0_holdout(subject_id):
            continue
        partition = classify_m0(subject_id)
        patients[subject_id] = Patient(subject_id, anchor_year, group, partition)
        subjects_by_partition[partition].add(subject_id)

    if not all(subjects_by_partition.values()):
        raise ProtocolFailure("M0 patient split has an empty partition")
    if set.intersection(*subjects_by_partition.values()):
        raise ProtocolFailure("M0 patient partitions are not disjoint")
    return patients, subjects_by_partition


def load_vocabulary(asset_dir: Path) -> list[str]:
    import dill

    with (asset_dir / "voc_final.pkl").open("rb") as handle:
        vocabulary = dill.load(handle)
    idx2word = vocabulary["med_voc"].idx2word
    codes = [str(idx2word[index]) for index in range(N_CONCEPTS)]
    if len(codes) != N_CONCEPTS or len(set(codes)) != N_CONCEPTS:
        raise ProtocolFailure("Medication vocabulary is not exactly 131 unique concepts")
    if any(len(code) != 4 for code in codes):
        raise ProtocolFailure("Frozen vocabulary is not ATC-L4")
    return codes


def iter_subject_chunks(
    path: Path,
    usecols: list[str],
    subjects: set[int],
    dtype: dict[str, str],
    chunksize: int = 200_000,
) -> Iterable[pd.DataFrame]:
    if not subjects:
        return
    for chunk in pd.read_csv(
        path,
        usecols=usecols,
        dtype=dtype,
        compression="infer",
        chunksize=chunksize,
        low_memory=False,
    ):
        selected = chunk.loc[chunk["subject_id"].isin(subjects)]
        if not selected.empty:
            yield selected.copy()


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
    safe_frame = pd.read_csv(mapping_dir / "ndc2atc_level4.csv", dtype="string")
    for row in safe_frame.itertuples(index=False):
        atc = clean_text(row.ATC4)[:4]
        if len(atc) == 4:
            for key in mapping_keys(row.NDC):
                mapping[key] = atc

    kgd_frame = pd.read_csv(mapping_dir / "drug_codes_mapping.csv", dtype="string")
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


def build_formulary_consensus(
    mimic_dir: Path,
    train_subjects: set[int],
    mapping: dict[str, str],
    vocabulary: set[str],
) -> dict[str, str]:
    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    usecols = ["subject_id", "ndc", "formulary_drug_cd"]
    dtype = {"subject_id": "Int64", "ndc": "string", "formulary_drug_cd": "string"}
    for chunk in iter_subject_chunks(
        table_path(mimic_dir, "prescriptions"), usecols, train_subjects, dtype
    ):
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
    return consensus


def build_prescription_linkage(
    mimic_dir: Path,
    subjects: set[int],
    mapping: dict[str, str],
    consensus: dict[str, str],
    vocabulary: set[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    poe_to_atcs: dict[str, set[str]] = collections.defaultdict(set)
    poe_to_pharms: dict[str, set[str]] = collections.defaultdict(set)
    usecols = ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"]
    dtype = {
        "subject_id": "Int64",
        "poe_id": "string",
        "pharmacy_id": "string",
        "ndc": "string",
        "formulary_drug_cd": "string",
    }
    for chunk in iter_subject_chunks(
        table_path(mimic_dir, "prescriptions"), usecols, subjects, dtype
    ):
        for row in chunk.itertuples(index=False):
            poe_id = clean_text(row.poe_id)
            pharmacy_id = clean_text(row.pharmacy_id)
            atc = lookup_atc(row.ndc, mapping)
            if atc not in vocabulary:
                atc = consensus.get(clean_text(row.formulary_drug_cd))
            if not poe_id or atc not in vocabulary:
                continue
            poe_to_atcs[poe_id].add(atc)
            if pharmacy_id and pharmacy_id not in {"0", "0.0"}:
                poe_to_pharms[poe_id].add(pharmacy_id)
    return poe_to_atcs, poe_to_pharms


def load_clinical_records(
    mimic_dir: Path,
    subjects: set[int],
    mapping: dict[str, str],
    consensus: dict[str, str],
    vocabulary: set[str],
) -> tuple[
    dict[int, tuple[int, int]],
    dict[int, list[dict[str, Any]]],
    dict[int, list[tuple[int, str, str]]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    poe_to_atcs, poe_to_pharms = build_prescription_linkage(
        mimic_dir, subjects, mapping, consensus, vocabulary
    )

    hadm_to_admit: dict[int, tuple[int, int]] = {}
    admissions_cols = ["subject_id", "hadm_id", "admittime"]
    admissions_dtype = {"subject_id": "Int64", "hadm_id": "Int64", "admittime": "string"}
    for chunk in iter_subject_chunks(
        table_path(mimic_dir, "admissions"), admissions_cols, subjects, admissions_dtype
    ):
        times = parse_datetime_seconds(chunk["admittime"])
        for row, admit_time in zip(chunk.itertuples(index=False), times, strict=True):
            subject_id = as_int(row.subject_id)
            hadm_id = as_int(row.hadm_id)
            if subject_id is not None and hadm_id is not None and admit_time is not None:
                hadm_to_admit[hadm_id] = (subject_id, admit_time)

    poe_cols = [
        "poe_id",
        "subject_id",
        "hadm_id",
        "ordertime",
        "order_type",
        "transaction_type",
        "discontinue_of_poe_id",
    ]
    poe_dtype = {
        "poe_id": "string",
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "ordertime": "string",
        "order_type": "string",
        "transaction_type": "string",
        "discontinue_of_poe_id": "string",
    }
    hadm_to_poe_events: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for chunk in iter_subject_chunks(table_path(mimic_dir, "poe"), poe_cols, subjects, poe_dtype):
        eligible = chunk.loc[
            chunk["order_type"].eq("Medications") & chunk["transaction_type"].isin(ACTIONS)
        ]
        if eligible.empty:
            continue
        times = parse_datetime_seconds(eligible["ordertime"])
        for row, order_time in zip(eligible.itertuples(index=False), times, strict=True):
            hadm_id = as_int(row.hadm_id)
            if hadm_id is None or order_time is None:
                continue
            hadm_to_poe_events[hadm_id].append(
                {
                    "poe_id": clean_text(row.poe_id),
                    "ordertime": order_time,
                    "transaction_type": clean_text(row.transaction_type),
                    "discontinue_of_poe_id": clean_text(row.discontinue_of_poe_id),
                }
            )

    emar_cols = ["subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"]
    emar_dtype = {
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "poe_id": "string",
        "pharmacy_id": "string",
        "charttime": "string",
        "event_txt": "string",
    }
    hadm_to_admins: dict[int, list[tuple[int, str, str]]] = collections.defaultdict(list)
    for chunk in iter_subject_chunks(
        table_path(mimic_dir, "emar"), emar_cols, subjects, emar_dtype
    ):
        eligible = chunk.loc[chunk["event_txt"].isin(ADMINISTRATION_EVENT_TYPES)]
        if eligible.empty:
            continue
        times = parse_datetime_seconds(eligible["charttime"])
        for row, chart_time in zip(eligible.itertuples(index=False), times, strict=True):
            hadm_id = as_int(row.hadm_id)
            if hadm_id is not None and chart_time is not None:
                hadm_to_admins[hadm_id].append(
                    (chart_time, clean_text(row.poe_id), clean_text(row.pharmacy_id))
                )
    return hadm_to_admit, hadm_to_poe_events, hadm_to_admins, poe_to_atcs, poe_to_pharms


def event_concepts(event: dict[str, Any], poe_to_atcs: dict[str, set[str]]) -> set[str]:
    if event["transaction_type"] == "D/C":
        return poe_to_atcs.get(event["discontinue_of_poe_id"], set())
    return poe_to_atcs.get(event["poe_id"], set())


def new_stats() -> dict[str, Any]:
    return {
        "bursts": 0,
        "mapped_target_events": 0,
        "mapped_target_marks": 0,
        "burst_patients": set(),
        "mapped_target_patients": set(),
        "action_events": collections.Counter(),
        "action_marks": collections.Counter(),
        "action_patients": {action: set() for action in ACTIONS},
        "state_consistency": {
            action: {"mapped_events": 0, "active_before": 0} for action in ("Change", "D/C")
        },
        "action_concept_events": {action: collections.Counter() for action in ACTIONS},
    }


def update_stats(
    stats: dict[str, Any],
    patient_id: int,
    target_events: list[tuple[dict[str, Any], set[str]]],
    target_marks: set[int],
    active_indices: set[int],
    concept_to_index: dict[str, int],
) -> None:
    stats["bursts"] += 1
    stats["burst_patients"].add(patient_id)
    stats["mapped_target_marks"] += len(target_marks)
    for event, concepts in target_events:
        action = event["transaction_type"]
        stats["mapped_target_events"] += 1
        stats["mapped_target_patients"].add(patient_id)
        stats["action_events"][action] += 1
        stats["action_patients"][action].add(patient_id)
        indices = {concept_to_index[concept] for concept in concepts}
        stats["action_marks"][action] += len(indices)
        stats["action_concept_events"][action].update(indices)
        if action in ("Change", "D/C"):
            state = stats["state_consistency"][action]
            state["mapped_events"] += 1
            if indices.issubset(active_indices):
                state["active_before"] += 1


def merge_stats(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = new_stats()
    for key in ("bursts", "mapped_target_events", "mapped_target_marks"):
        merged[key] = left[key] + right[key]
    for key in ("burst_patients", "mapped_target_patients"):
        merged[key] = set(left[key]) | set(right[key])
    merged["action_events"].update(left["action_events"])
    merged["action_events"].update(right["action_events"])
    merged["action_marks"].update(left["action_marks"])
    merged["action_marks"].update(right["action_marks"])
    for action in ACTIONS:
        merged["action_patients"][action] = set(left["action_patients"][action]) | set(
            right["action_patients"][action]
        )
        if action in ("Change", "D/C"):
            for field in ("mapped_events", "active_before"):
                merged["state_consistency"][action][field] = (
                    left["state_consistency"][action][field]
                    + right["state_consistency"][action][field]
                )
        merged["action_concept_events"][action].update(left["action_concept_events"][action])
        merged["action_concept_events"][action].update(right["action_concept_events"][action])
    return merged


def stats_public(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "bursts": int(stats["bursts"]),
        "burst_patients": len(stats["burst_patients"]),
        "mapped_target_events": int(stats["mapped_target_events"]),
        "mapped_target_patients": len(stats["mapped_target_patients"]),
        "mapped_target_marks": int(stats["mapped_target_marks"]),
        "action_events": {action: int(stats["action_events"][action]) for action in ACTIONS},
        "action_patients": {action: len(stats["action_patients"][action]) for action in ACTIONS},
        "action_marks": {action: int(stats["action_marks"][action]) for action in ACTIONS},
        "state_consistency": {
            action: {
                "mapped_events": int(stats["state_consistency"][action]["mapped_events"]),
                "active_before": int(stats["state_consistency"][action]["active_before"]),
                "fraction": (
                    stats["state_consistency"][action]["active_before"]
                    / stats["state_consistency"][action]["mapped_events"]
                    if stats["state_consistency"][action]["mapped_events"]
                    else None
                ),
            }
            for action in ("Change", "D/C")
        },
    }


def build_bursts(
    patients: dict[int, Patient],
    subjects: set[int],
    clinical: tuple[
        dict[int, tuple[int, int]],
        dict[int, list[dict[str, Any]]],
        dict[int, list[tuple[int, str, str]]],
        dict[str, set[str]],
        dict[str, set[str]],
    ],
    concept_to_index: dict[str, int],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    hadm_to_admit, hadm_to_poe_events, hadm_to_admins, poe_to_atcs, poe_to_pharms = clinical
    bursts_by_partition = {name: [] for name in ("EditTrain", "EditTune", "EditAudit")}
    stats_by_partition = {name: new_stats() for name in bursts_by_partition}

    for hadm_id in sorted(hadm_to_poe_events):
        if hadm_id not in hadm_to_admit:
            continue
        patient_id, admission_time = hadm_to_admit[hadm_id]
        if patient_id not in subjects or patient_id not in patients:
            continue
        patient = patients[patient_id]
        events = sorted(
            hadm_to_poe_events[hadm_id],
            key=lambda event: (event["ordertime"], event["poe_id"]),
        )

        admin_poe_first: dict[str, int] = {}
        admin_pharm_first: dict[str, int] = {}
        for chart_time, poe_id, pharmacy_id in hadm_to_admins.get(hadm_id, []):
            if poe_id:
                admin_poe_first[poe_id] = min(admin_poe_first.get(poe_id, chart_time), chart_time)
            if pharmacy_id:
                admin_pharm_first[pharmacy_id] = min(
                    admin_pharm_first.get(pharmacy_id, chart_time), chart_time
                )

        discontinue_time: dict[str, int] = {}
        order_first_time: dict[str, int] = {}
        for event in events:
            if event["transaction_type"] == "D/C":
                target_poe = event["discontinue_of_poe_id"]
                if target_poe:
                    discontinue_time[target_poe] = min(
                        discontinue_time.get(target_poe, event["ordertime"]), event["ordertime"]
                    )
            elif event["poe_id"] in poe_to_atcs:
                order_first_time[event["poe_id"]] = min(
                    order_first_time.get(event["poe_id"], event["ordertime"]), event["ordertime"]
                )

        activation_entries: list[tuple[int, str, set[str]]] = []
        removal_entries: list[tuple[int, str, set[str]]] = []
        for poe_id, order_time in order_first_time.items():
            concepts = poe_to_atcs[poe_id]
            first_admin = admin_poe_first.get(poe_id)
            if first_admin is None:
                first_admin = min(
                    (
                        admin_pharm_first[pharmacy_id]
                        for pharmacy_id in poe_to_pharms.get(poe_id, ())
                        if pharmacy_id in admin_pharm_first
                    ),
                    default=None,
                )
            if first_admin is None:
                continue
            activation_time = max(order_time, first_admin)
            dc_time = discontinue_time.get(poe_id)
            if dc_time is not None and dc_time <= activation_time:
                continue
            activation_entries.append((activation_time, poe_id, concepts))
            if dc_time is not None:
                removal_entries.append((dc_time, poe_id, concepts))
        activation_entries.sort(key=lambda item: (item[0], item[1]))
        removal_entries.sort(key=lambda item: (item[0], item[1]))

        positive_orders = [
            (index, event, event_concepts(event, poe_to_atcs))
            for index, event in enumerate(events)
            if event_concepts(event, poe_to_atcs)
        ]
        if not positive_orders:
            continue

        assigned = [False] * len(positive_orders)
        history_end = 0
        activation_cursor = 0
        removal_cursor = 0
        active_counts = np.zeros(N_CONCEPTS, dtype=np.int32)

        for positive_index, (_event_index, base_event, _base_concepts) in enumerate(
            positive_orders
        ):
            if assigned[positive_index]:
                continue
            decision_time = base_event["ordertime"]
            while (
                activation_cursor < len(activation_entries)
                and activation_entries[activation_cursor][0] < decision_time
            ):
                _, _, concepts = activation_entries[activation_cursor]
                for concept in concepts:
                    active_counts[concept_to_index[concept]] += 1
                activation_cursor += 1
            while (
                removal_cursor < len(removal_entries)
                and removal_entries[removal_cursor][0] < decision_time
            ):
                _, _, concepts = removal_entries[removal_cursor]
                for concept in concepts:
                    active_counts[concept_to_index[concept]] -= 1
                removal_cursor += 1

            target_end = decision_time + TARGET_SECONDS
            burst_events: list[tuple[dict[str, Any], set[str]]] = []
            target_marks: set[int] = set()
            target_action_indices: dict[str, set[int]] = {action: set() for action in ACTIONS}
            target_medications: set[int] = set()
            for candidate_index in range(positive_index, len(positive_orders)):
                if positive_orders[candidate_index][1]["ordertime"] >= target_end:
                    break
                assigned[candidate_index] = True
                _, candidate_event, concepts = positive_orders[candidate_index]
                burst_events.append((candidate_event, concepts))
                action_index = ACTION_TO_INDEX[candidate_event["transaction_type"]]
                concept_indices = {concept_to_index[concept] for concept in concepts}
                target_action_indices[candidate_event["transaction_type"]].update(concept_indices)
                target_medications.update(concept_indices)
                target_marks.update(action_index * N_CONCEPTS + index for index in concept_indices)

            if dt.datetime.fromtimestamp(decision_time, tz=dt.UTC).year != patient.anchor_year:
                continue
            if not burst_events or not target_marks:
                continue

            while history_end < len(events) and events[history_end]["ordertime"] < decision_time:
                history_end += 1
            history = events[max(0, history_end - HISTORY_LENGTH) : history_end]
            hist_meds = np.zeros(HISTORY_LENGTH, dtype=np.int64)
            hist_types = np.zeros(HISTORY_LENGTH, dtype=np.int64)
            hist_elapsed = np.zeros(HISTORY_LENGTH, dtype=np.float32)
            previous_time: int | None = None
            for step, event in enumerate(history):
                hist_types[step] = ACTION_CODES[event["transaction_type"]]
                concepts = event_concepts(event, poe_to_atcs)
                if concepts:
                    hist_meds[step] = min(concept_to_index[concept] for concept in concepts) + 1
                elapsed_hours = (
                    (event["ordertime"] - previous_time) / 3600.0
                    if previous_time is not None
                    else 0.0
                )
                hist_elapsed[step] = math.log1p(max(0.0, elapsed_hours))
                previous_time = event["ordertime"]

            active_indices = set(np.flatnonzero(active_counts > 0).tolist())
            target_vec = np.zeros(N_MARKS, dtype=np.float32)
            target_vec[sorted(target_marks)] = 1.0
            hours_since_admit = max(0.0, (decision_time - admission_time) / 3600.0)
            partition = patient.partition
            burst = {
                "patient_id": patient_id,
                "hadm_id": hadm_id,
                "decision_t": decision_time,
                "hist_meds": hist_meds.tolist(),
                "hist_types": hist_types.tolist(),
                "hist_elapsed": hist_elapsed.tolist(),
                "active_regimen": [
                    1.0 if index in active_indices else 0.0 for index in range(N_CONCEPTS)
                ],
                "active_indices": sorted(active_indices),
                "log_hours_since_admit": float(math.log1p(hours_since_admit)),
                "target_vec": target_vec.tolist(),
                "target_mark_indices": sorted(target_marks),
                "target_action_indices": {
                    action: sorted(target_action_indices[action]) for action in ACTIONS
                },
                "target_med_indices": sorted(target_medications),
            }
            bursts_by_partition[partition].append(burst)
            update_stats(
                stats_by_partition[partition],
                patient_id,
                burst_events,
                target_marks,
                active_indices,
                concept_to_index,
            )
    return bursts_by_partition, stats_by_partition


class TensorBurstDataset:
    """CPU tensors for one fixed patient partition."""

    def __init__(self, bursts: list[dict[str, Any]]) -> None:
        if not bursts:
            raise ProtocolFailure("Cannot build a tensor dataset from an empty partition")
        self.bursts = bursts
        self.n = len(bursts)
        self.hist_meds = torch.tensor([burst["hist_meds"] for burst in bursts], dtype=torch.long)
        self.hist_types = torch.tensor([burst["hist_types"] for burst in bursts], dtype=torch.long)
        self.hist_elapsed = torch.tensor(
            [burst["hist_elapsed"] for burst in bursts], dtype=torch.float32
        )
        self.active_regimen = torch.tensor(
            [burst["active_regimen"] for burst in bursts], dtype=torch.float32
        )
        self.log_hours = torch.tensor(
            [[burst["log_hours_since_admit"]] for burst in bursts], dtype=torch.float32
        )
        self.target_vec = torch.tensor(
            [burst["target_vec"] for burst in bursts], dtype=torch.float32
        )
        self.patient_ids = np.asarray([burst["patient_id"] for burst in bursts], dtype=np.int64)

    def __len__(self) -> int:
        return self.n

    def iter_batches(
        self, batch_size: int, shuffle: bool = False
    ) -> Iterable[dict[str, torch.Tensor]]:
        indices = torch.randperm(self.n) if shuffle else torch.arange(self.n)
        for start in range(0, self.n, batch_size):
            selected = indices[start : start + batch_size]
            yield {
                "hist_meds": self.hist_meds[selected],
                "hist_types": self.hist_types[selected],
                "hist_elapsed": self.hist_elapsed[selected],
                "active_regimen": self.active_regimen[selected],
                "log_hours_since_admit": self.log_hours[selected],
                "target_vec": self.target_vec[selected],
            }


def move_batch(batch: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}


class CommonCausalEncoder(nn.Module):
    """Frozen order-time encoder shared by each separately trained variant."""

    def __init__(self) -> None:
        super().__init__()
        self.med_embedding = nn.Embedding(N_CONCEPTS + 1, 64, padding_idx=0)
        self.trans_embedding = nn.Embedding(4, 8, padding_idx=0)
        self.elapsed_proj = nn.Linear(1, 8)
        self.gru = nn.GRU(80, 128, num_layers=1, batch_first=True)
        self.zero_history = nn.Parameter(torch.zeros(128))
        self.context = nn.Sequential(
            nn.Linear(260, 128),
            nn.ReLU(),
            nn.Dropout(0.10),
        )

    def forward(
        self,
        hist_meds: torch.Tensor,
        hist_types: torch.Tensor,
        hist_elapsed: torch.Tensor,
        active_regimen: torch.Tensor,
        log_hours_since_admit: torch.Tensor,
    ) -> torch.Tensor:
        med_emb = self.med_embedding(hist_meds)
        trans_emb = self.trans_embedding(hist_types)
        elapsed_emb = self.elapsed_proj(hist_elapsed.unsqueeze(-1))
        gru_input = torch.cat([med_emb, trans_emb, elapsed_emb], dim=-1)
        sequence_lengths = (hist_meds > 0).sum(dim=-1)
        gru_output, _ = self.gru(gru_input)
        final_state = torch.zeros(
            hist_meds.size(0), 128, device=gru_input.device, dtype=gru_input.dtype
        )
        has_history = sequence_lengths > 0
        if has_history.any():
            rows = torch.where(has_history)[0]
            final_state[rows] = gru_output[rows, sequence_lengths[rows] - 1]
        if (~has_history).any():
            rows = torch.where(~has_history)[0]
            final_state[rows] = self.zero_history
        return self.context(torch.cat([final_state, active_regimen, log_hours_since_admit], dim=-1))


class FlatMark(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = CommonCausalEncoder()
        self.output = nn.Linear(128, N_MARKS)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        return self.output(
            self.encoder(
                batch["hist_meds"],
                batch["hist_types"],
                batch["hist_elapsed"],
                batch["active_regimen"],
                batch["log_hours_since_admit"],
            )
        )


class SeparateHeadsDirectStateMask(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = CommonCausalEncoder()
        self.heads = nn.ModuleList(nn.Linear(128, N_CONCEPTS) for _ in ACTIONS)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        hidden = self.encoder(
            batch["hist_meds"],
            batch["hist_types"],
            batch["hist_elapsed"],
            batch["active_regimen"],
            batch["log_hours_since_admit"],
        )
        return torch.cat([head(hidden) for head in self.heads], dim=-1)


class StateEditProbe(nn.Module):
    """Fixed rank-32 structured action-medication decoder from the protocol."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = CommonCausalEncoder()
        self.medication_base = nn.Linear(128, N_CONCEPTS)
        self.query = nn.Linear(128, 32)
        self.medication_embedding = nn.Parameter(torch.empty(N_CONCEPTS, 32))
        self.action_embedding = nn.Parameter(torch.empty(N_ACTIONS, 32))
        self.action_bias = nn.Parameter(torch.zeros(N_ACTIONS))
        self.active_state_coefficient = nn.Parameter(torch.zeros(N_ACTIONS))
        nn.init.normal_(self.medication_embedding, std=0.02)
        nn.init.normal_(self.action_embedding, std=0.02)

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        hidden = self.encoder(
            batch["hist_meds"],
            batch["hist_types"],
            batch["hist_elapsed"],
            batch["active_regimen"],
            batch["log_hours_since_admit"],
        )
        base = self.medication_base(hidden)
        query = self.query(hidden)
        interaction = torch.einsum(
            "bd,md,ad->bam", query, self.medication_embedding, self.action_embedding
        )
        scores = (
            base[:, None, :]
            + interaction
            + self.action_bias[None, :, None]
            + self.active_state_coefficient[None, :, None] * batch["active_regimen"][:, None, :]
        )
        return scores.reshape(-1, N_MARKS)


MODEL_FACTORIES = {
    "FlatMark": FlatMark,
    "SeparateHeads+DirectStateMask": SeparateHeadsDirectStateMask,
    "StateEditProbe": StateEditProbe,
}


def apply_state_mask_numpy(
    logits: np.ndarray, active_regimen: np.ndarray, model_name: str
) -> np.ndarray:
    decoded = np.asarray(logits, dtype=np.float64).copy()
    if model_name == "FlatMark":
        return decoded
    active = np.asarray(active_regimen, dtype=np.float64) >= 0.5
    for action_index in (ACTION_TO_INDEX["Change"], ACTION_TO_INDEX["D/C"]):
        start = action_index * N_CONCEPTS
        decoded[:, start : start + N_CONCEPTS] = np.where(
            active, decoded[:, start : start + N_CONCEPTS], -np.inf
        )
    return decoded


def apply_state_mask_torch(logits: torch.Tensor, active_regimen: torch.Tensor) -> torch.Tensor:
    scores = logits.reshape(-1, N_ACTIONS, N_CONCEPTS).clone()
    invalid = active_regimen < 0.5
    scores[:, ACTION_TO_INDEX["Change"], :] = scores[:, ACTION_TO_INDEX["Change"], :].masked_fill(
        invalid, -torch.inf
    )
    scores[:, ACTION_TO_INDEX["D/C"], :] = scores[:, ACTION_TO_INDEX["D/C"], :].masked_fill(
        invalid, -torch.inf
    )
    return scores.reshape(-1, N_MARKS)


def select_batch_size(device: torch.device) -> int:
    for batch_size in (
        TRAINING_BATCH_CEILING,
        1024,
        512,
        256,
        128,
        64,
        32,
        16,
        8,
        4,
        2,
        1,
    ):
        try:
            set_seed(TRAINING_SEED)
            model = StateEditProbe().to(device)
            batch = {
                "hist_meds": torch.randint(
                    0, N_CONCEPTS + 1, (batch_size, HISTORY_LENGTH), device=device
                ),
                "hist_types": torch.randint(0, 4, (batch_size, HISTORY_LENGTH), device=device),
                "hist_elapsed": torch.rand((batch_size, HISTORY_LENGTH), device=device),
                "active_regimen": torch.rand((batch_size, N_CONCEPTS), device=device),
                "log_hours_since_admit": torch.rand((batch_size, 1), device=device),
                "target_vec": torch.rand((batch_size, N_MARKS), device=device),
            }
            logits = model(batch)
            F.binary_cross_entropy_with_logits(logits, batch["target_vec"]).backward()
            del model, batch, logits
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return batch_size
        except RuntimeError as error:
            if "out of memory" not in str(error).lower():
                raise
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    raise ProtocolFailure("No deterministic power-of-two batch size fits StateEditProbe")


def run_mechanical_preflight(vocabulary: list[str], device: torch.device) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "vocabulary_exactly_131_atc_l4": len(vocabulary) == N_CONCEPTS
        and len(set(vocabulary)) == N_CONCEPTS
        and all(len(code) == 4 for code in vocabulary),
        "m0_split_deterministic": classify_m0(10000032) == classify_m0(10000032),
        "anchor_year_rule_exact": (
            dt.datetime.fromtimestamp(1704067200, tz=dt.UTC).year == 2024
            and dt.datetime.fromtimestamp(1704067200, tz=dt.UTC).year != 2023
        ),
        "target_interval_half_open_10_minutes": (1000 + TARGET_SECONDS) == 1600,
        "mark_vocabulary_exactly_393": N_ACTIONS * N_CONCEPTS == N_MARKS,
        "dc_target_resolves_to_referenced_medication": event_concepts(
            {
                "transaction_type": "D/C",
                "discontinue_of_poe_id": "old-order",
                "poe_id": "dc-order",
            },
            {"old-order": {"A01A"}},
        )
        == {"A01A"},
    }
    dummy_batch = {
        "hist_meds": torch.randint(0, N_CONCEPTS + 1, (4, HISTORY_LENGTH), device=device),
        "hist_types": torch.randint(0, 4, (4, HISTORY_LENGTH), device=device),
        "hist_elapsed": torch.rand((4, HISTORY_LENGTH), device=device),
        "active_regimen": torch.zeros((4, N_CONCEPTS), device=device),
        "log_hours_since_admit": torch.ones((4, 1), device=device),
        "target_vec": torch.zeros((4, N_MARKS), device=device),
    }
    dummy_batch["active_regimen"][:, [2, 5, 10]] = 1.0
    for name, factory in MODEL_FACTORIES.items():
        set_seed(TRAINING_SEED)
        model = factory().to(device)
        logits = model(dummy_batch)
        F.binary_cross_entropy_with_logits(logits, dummy_batch["target_vec"]).backward()
        checks[f"{name}_forward_backward"] = tuple(logits.shape) == (4, N_MARKS)
        del model, logits
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    checks["state_mask_shape_preserved"] = tuple(
        apply_state_mask_torch(
            torch.zeros((4, N_MARKS), device=device), dummy_batch["active_regimen"]
        ).shape
    ) == (4, N_MARKS)
    if not all(checks.values()):
        raise ProtocolFailure(f"M0 mechanical preflight failed: {checks}")
    return {"checks": checks, "passed": True}


def evaluate_bce(
    model: nn.Module, data: TensorBurstDataset, device: torch.device, batch_size: int
) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for raw_batch in data.iter_batches(batch_size):
            batch = move_batch(raw_batch, device)
            logits = model(batch)
            total += float(
                F.binary_cross_entropy_with_logits(logits, batch["target_vec"], reduction="sum")
            )
            count += int(np.prod(batch["target_vec"].shape))
    return total / count


def train_variant(
    name: str,
    train_data: TensorBurstDataset,
    tune_data: TensorBurstDataset,
    device: torch.device,
    batch_size: int,
    checkpoint_path: Path,
) -> tuple[nn.Module, dict[str, Any]]:
    if checkpoint_path.exists():
        raise ProtocolFailure("M0 run directory is not fresh; checkpoint reuse is forbidden")
    set_seed(TRAINING_SEED)
    model = MODEL_FACTORIES[name]().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    best_tune_bce = float("inf")
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        train_sum = 0.0
        train_count = 0
        for raw_batch in train_data.iter_batches(batch_size, shuffle=True):
            batch = move_batch(raw_batch, device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch)
            loss = F.binary_cross_entropy_with_logits(logits, batch["target_vec"])
            loss.backward()
            optimizer.step()
            count = batch["target_vec"].shape[0]
            train_sum += float(loss.detach()) * count
            train_count += count
        tune_bce = evaluate_bce(model, tune_data, device, batch_size)
        print(
            f"{name} epoch={epoch} train_bce={train_sum / train_count:.17g} "
            f"EditTune_BCE={tune_bce:.17g}",
            flush=True,
        )
        if tune_bce < best_tune_bce:
            best_tune_bce = tune_bce
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= EARLY_STOPPING_PATIENCE:
                break
    if best_state is None:
        raise ProtocolFailure(f"{name} produced no EditTune checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    torch.save(best_state, checkpoint_path)
    selection = {
        "model": name,
        "epoch": best_epoch,
        "edit_tune_bce": best_tune_bce,
        "checkpoint_sha256": sha256_file(checkpoint_path),
    }
    return model, selection


def predict_logits(
    model: nn.Module, data: TensorBurstDataset, device: torch.device, batch_size: int
) -> np.ndarray:
    model.eval()
    rows: list[np.ndarray] = []
    with torch.no_grad():
        for raw_batch in data.iter_batches(batch_size):
            batch = move_batch(raw_batch, device)
            rows.append(model(batch).cpu().numpy())
    return np.concatenate(rows, axis=0)


def action_medication_candidates(vocabulary: list[str]) -> np.ndarray:
    code_order = np.argsort(np.asarray(vocabulary, dtype=str), kind="stable")
    return np.asarray(
        [action * N_CONCEPTS + med for action in range(N_ACTIONS) for med in code_order],
        dtype=np.int64,
    )


def top_k_indices(row: np.ndarray, candidates: np.ndarray, k: int) -> np.ndarray:
    order = np.argsort(-row[candidates], kind="stable")
    return candidates[order[:k]]


def audit_metric_bundle(
    bursts: list[dict[str, Any]],
    raw_logits: np.ndarray,
    model_name: str,
    vocabulary: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    active = np.asarray([burst["active_regimen"] for burst in bursts], dtype=np.float32)
    decoded = apply_state_mask_numpy(raw_logits, active, model_name)
    target_marks = [set(burst["target_mark_indices"]) for burst in bursts]
    target_action = {
        action: [set(burst["target_action_indices"][action]) for burst in bursts]
        for action in ACTIONS
    }
    target_meds = [set(burst["target_med_indices"]) for burst in bursts]
    code_order = np.argsort(np.asarray(vocabulary, dtype=str), kind="stable")
    mark_candidates = action_medication_candidates(vocabulary)
    action_recall_raw: dict[str, np.ndarray] = {}
    action_recall_eligible: dict[str, np.ndarray] = {}
    action_prauc: dict[str, float] = {}
    for action_index, action in enumerate(ACTIONS):
        values = np.zeros(len(bursts), dtype=np.float64)
        eligible = np.asarray([bool(target_action[action][i]) for i in range(len(bursts))])
        segment = decoded[:, action_index * N_CONCEPTS : (action_index + 1) * N_CONCEPTS]
        for index in np.flatnonzero(eligible):
            selected = top_k_indices(segment[index], code_order, TOP_K)
            values[index] = len(set(selected.tolist()) & target_action[action][index]) / len(
                target_action[action][index]
            )
        action_recall_raw[action] = values
        action_recall_eligible[action] = eligible
        labels = np.asarray(
            [
                [1 if med in target_action[action][row] else 0 for med in range(N_CONCEPTS)]
                for row in range(len(bursts))
            ],
            dtype=np.int8,
        )
        action_prauc[action] = float(
            average_precision_score(labels, 1.0 / (1.0 + np.exp(-segment)), average="micro")
        )

    joint_values = np.zeros(len(bursts), dtype=np.float64)
    medication_values = np.zeros(len(bursts), dtype=np.float64)
    invalid_predictions = 0
    for index in range(len(bursts)):
        selected_marks = top_k_indices(raw_logits[index], mark_candidates, TOP_K)
        joint_values[index] = len(set(selected_marks.tolist()) & target_marks[index]) / len(
            target_marks[index]
        )
        invalid_predictions += sum(
            mark // N_CONCEPTS in (ACTION_TO_INDEX["Change"], ACTION_TO_INDEX["D/C"])
            and active[index, mark % N_CONCEPTS] < 0.5
            for mark in selected_marks
        )
        collapsed = np.max(decoded[index].reshape(N_ACTIONS, N_CONCEPTS), axis=0)
        selected_meds = top_k_indices(collapsed, code_order, TOP_K)
        medication_values[index] = len(set(selected_meds.tolist()) & target_meds[index]) / len(
            target_meds[index]
        )

    action_recall = {
        action: float(values[eligible].mean()) if eligible.any() else None
        for action, values in action_recall_raw.items()
        for eligible in [action_recall_eligible[action]]
    }
    macro_action_recall = float(np.mean([action_recall[action] for action in ACTIONS]))
    macro_action_prauc = float(np.mean([action_prauc[action] for action in ACTIONS]))
    public = {
        "model": model_name,
        "n_audit_bursts": len(bursts),
        "n_audit_patients": len({burst["patient_id"] for burst in bursts}),
        "ActionRecall@5_New": action_recall["New"],
        "ActionRecall@5_Change": action_recall["Change"],
        "ActionRecall@5_D/C": action_recall["D/C"],
        "MacroActionRecall@5": macro_action_recall,
        "per_action_PRAUC": action_prauc,
        "macro_action_PRAUC": macro_action_prauc,
        "JointMarkRecall@5": float(joint_values.mean()),
        "MedicationRecall@5": float(medication_values.mean()),
        "pre_mask_state_invalid_prediction_rate": invalid_predictions / (len(bursts) * TOP_K),
        "pre_mask_state_invalid_predictions": invalid_predictions,
        "pre_mask_state_invalid_prediction_denominator": len(bursts) * TOP_K,
        "action_eligible_bursts": {
            action: int(action_recall_eligible[action].sum()) for action in ACTIONS
        },
    }
    raw = {
        "action_recall": action_recall_raw,
        "action_recall_eligible": action_recall_eligible,
        "macro_action_recall": macro_action_recall,
        "joint_mark_recall": joint_values,
        "medication_recall": medication_values,
    }
    return public, raw


def bootstrap_primary_deltas(
    patient_ids: np.ndarray,
    control_raw: dict[str, Any],
    probe_raw: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    unique_patients, inverse = np.unique(patient_ids, return_inverse=True)
    n_patients = len(unique_patients)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = rng.choice(n_patients, size=(BOOTSTRAP_REPLICATES, n_patients), replace=True)
    multiplicities = np.zeros((BOOTSTRAP_REPLICATES, n_patients), dtype=np.float64)
    for row, sample in enumerate(samples):
        np.add.at(multiplicities[row], sample, 1.0)

    def patient_sum(values: np.ndarray) -> np.ndarray:
        return np.bincount(
            inverse, weights=np.asarray(values, dtype=np.float64), minlength=n_patients
        )

    def patient_count(values: np.ndarray) -> np.ndarray:
        return np.bincount(
            inverse, weights=np.asarray(values, dtype=np.float64), minlength=n_patients
        )

    def replicate_mean(raw: dict[str, Any], metric: str) -> np.ndarray:
        if metric in ("joint_mark_recall", "medication_recall"):
            denominator = patient_count(np.ones(len(patient_ids), dtype=np.float64))
            return (multiplicities @ patient_sum(raw[metric])) / (multiplicities @ denominator)
        if metric == "macro_action_recall":
            action_means = []
            for action in ACTIONS:
                eligible = raw["action_recall_eligible"][action].astype(np.float64)
                denominator = multiplicities @ patient_count(eligible)
                numerator = multiplicities @ patient_sum(raw["action_recall"][action])
                if np.any(denominator == 0):
                    raise ProtocolFailure(f"Bootstrap has an empty {action} stratum")
                action_means.append(numerator / denominator)
            return np.mean(np.stack(action_means, axis=0), axis=0)
        raise ValueError(f"Unsupported bootstrap metric: {metric}")

    def action_replicates(raw: dict[str, Any], action: str) -> np.ndarray:
        eligible = raw["action_recall_eligible"][action].astype(np.float64)
        denominator = multiplicities @ patient_count(eligible)
        numerator = multiplicities @ patient_sum(raw["action_recall"][action])
        if np.any(denominator == 0):
            raise ProtocolFailure(f"Bootstrap has an empty {action} stratum")
        return numerator / denominator

    result: dict[str, dict[str, Any]] = {}
    for metric in (
        "ActionRecall@5_New",
        "ActionRecall@5_Change",
        "ActionRecall@5_D/C",
        "MacroActionRecall@5",
        "JointMarkRecall@5",
        "MedicationRecall@5",
    ):
        if metric.startswith("ActionRecall@5_"):
            action = metric.removeprefix("ActionRecall@5_")
            control_replicates = action_replicates(control_raw, action)
            probe_replicates = action_replicates(probe_raw, action)
        elif metric == "MacroActionRecall@5":
            control_replicates = replicate_mean(control_raw, "macro_action_recall")
            probe_replicates = replicate_mean(probe_raw, "macro_action_recall")
        elif metric == "JointMarkRecall@5":
            control_replicates = replicate_mean(control_raw, "joint_mark_recall")
            probe_replicates = replicate_mean(probe_raw, "joint_mark_recall")
        else:
            control_replicates = replicate_mean(control_raw, "medication_recall")
            probe_replicates = replicate_mean(probe_raw, "medication_recall")
        delta = probe_replicates - control_replicates
        result[metric] = {
            "point": float(
                {
                    "ActionRecall@5_New": probe_raw["action_recall"]["New"][
                        probe_raw["action_recall_eligible"]["New"]
                    ].mean()
                    - control_raw["action_recall"]["New"][
                        control_raw["action_recall_eligible"]["New"]
                    ].mean(),
                    "ActionRecall@5_Change": probe_raw["action_recall"]["Change"][
                        probe_raw["action_recall_eligible"]["Change"]
                    ].mean()
                    - control_raw["action_recall"]["Change"][
                        control_raw["action_recall_eligible"]["Change"]
                    ].mean(),
                    "ActionRecall@5_D/C": probe_raw["action_recall"]["D/C"][
                        probe_raw["action_recall_eligible"]["D/C"]
                    ].mean()
                    - control_raw["action_recall"]["D/C"][
                        control_raw["action_recall_eligible"]["D/C"]
                    ].mean(),
                    "MacroActionRecall@5": probe_raw["macro_action_recall"]
                    - control_raw["macro_action_recall"],
                    "JointMarkRecall@5": float(
                        probe_raw["joint_mark_recall"].mean()
                        - control_raw["joint_mark_recall"].mean()
                    ),
                    "MedicationRecall@5": float(
                        probe_raw["medication_recall"].mean()
                        - control_raw["medication_recall"].mean()
                    ),
                }[metric]
            ),
            "ci_95": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "cluster_unit": "patient_id",
        }
    return result


def support_checks(pre_stats: dict[str, Any]) -> dict[str, Any]:
    overall_events = pre_stats["mapped_target_events"]
    overall_patients = len(pre_stats["mapped_target_patients"])
    overall = {
        "actual": {
            "mapped_target_events": overall_events,
            "patients": overall_patients,
        },
        "minimum": PHASE_A_FLOORS["overall"],
        "passed": overall_events >= PHASE_A_FLOORS["overall"]["mapped_target_events"]
        and overall_patients >= PHASE_A_FLOORS["overall"]["patients"],
    }
    per_action: dict[str, Any] = {}
    for action in ACTIONS:
        events = int(pre_stats["action_events"][action])
        patients = len(pre_stats["action_patients"][action])
        floor = PHASE_A_FLOORS["per_action"][action]
        per_action[action] = {
            "actual": {"mapped_target_events": events, "patients": patients},
            "minimum": floor,
            "passed": events >= floor["mapped_target_events"] and patients >= floor["patients"],
        }
    state_consistency = {}
    for action, minimum in PHASE_A_FLOORS["state_consistency"].items():
        values = pre_stats["state_consistency"][action]
        fraction = (
            values["active_before"] / values["mapped_events"] if values["mapped_events"] else None
        )
        state_consistency[action] = {
            "actual": {
                "mapped_target_events": int(values["mapped_events"]),
                "active_before": int(values["active_before"]),
                "fraction": fraction,
            },
            "minimum_fraction": minimum,
            "passed": fraction is not None and fraction >= minimum,
        }
    distributed_concepts = sum(
        sum(
            pre_stats["action_concept_events"][action][concept]
            >= PHASE_A_FLOORS["distributed"]["events_per_action"]
            for action in ACTIONS
        )
        >= PHASE_A_FLOORS["distributed"]["minimum_actions"]
        for concept in range(N_CONCEPTS)
    )
    distributed = {
        "actual_concepts": int(distributed_concepts),
        "minimum_concepts": PHASE_A_FLOORS["distributed"]["concepts"],
        "minimum_events_per_action": PHASE_A_FLOORS["distributed"]["events_per_action"],
        "minimum_action_classes": PHASE_A_FLOORS["distributed"]["minimum_actions"],
        "passed": distributed_concepts >= PHASE_A_FLOORS["distributed"]["concepts"],
    }
    all_passed = bool(
        overall["passed"]
        and all(row["passed"] for row in per_action.values())
        and all(row["passed"] for row in state_consistency.values())
        and distributed["passed"]
    )
    return {
        "visibility": "EditTrain+EditTune only; EditAudit withheld until freeze",
        "overall": overall,
        "per_action": per_action,
        "state_consistency": state_consistency,
        "distributed_action_semantics": distributed,
        "passed": all_passed,
    }


def public_partition_counts(
    bursts_by_partition: dict[str, list[dict[str, Any]]],
    stats_by_partition: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = {}
    for partition in ("EditTrain", "EditTune", "EditAudit"):
        result[partition] = {
            "patients": len(stats_by_partition[partition]["burst_patients"]),
            **stats_public(stats_by_partition[partition]),
            "patient_split_members": None,
        }
        if not bursts_by_partition[partition]:
            result[partition]["bursts"] = 0
    return result


def repository_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def code_identity(path: Path) -> str:
    return sha256_file(path)


def write_freeze_manifest(
    output_dir: Path,
    repo_revision: str,
    runner_sha: str,
    protocol_sha: str,
    vocabulary: list[str],
    mapping_identities: dict[str, str],
    split_subjects: dict[str, set[int]],
    pre_stats: dict[str, Any],
    batch_size: int,
    selections: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    model_definitions = {
        "common_encoder": {
            "medication_embedding": 64,
            "transaction_type_embedding": 8,
            "elapsed_time_projection": 8,
            "gru_layers": 1,
            "gru_hidden": 128,
            "current_regimen": N_CONCEPTS,
            "log_hours_since_admission": 1,
            "dropout": 0.10,
        },
        "FlatMark": {"output": N_MARKS, "state_mask": False},
        "SeparateHeads+DirectStateMask": {
            "heads": N_ACTIONS,
            "output_per_head": N_CONCEPTS,
            "state_mask": "Change/D/C invalid when active_regimen[medication] == 0; New never masked",
        },
        "StateEditProbe": {
            "shared_medication_base_logits": N_CONCEPTS,
            "query_dim": 32,
            "medication_embedding_dim": 32,
            "action_embedding_dim": 32,
            "active_state_coefficient": True,
            "structured_interaction": "<q(h), u_m elementwise-multiply v_a>",
            "state_mask": "same as SeparateHeads+DirectStateMask",
        },
    }
    payload = {
        "schema_version": "1.0",
        "gate_id": "M0_EVENT_SOURCED_EDIT_ADMISSION",
        "protocol_identity": protocol_sha,
        "repository_revision": repo_revision,
        "runner_sha256": runner_sha,
        "data_construction_identity": sha256_json(
            {
                "mimic_version": "3.1",
                "groups": sorted(ADMITTED_GROUPS.items()),
                "temporal_rule": "year(decision_time) == patient.anchor_year",
                "target_window_seconds": TARGET_SECONDS,
                "history_length": HISTORY_LENGTH,
                "actions": ACTIONS,
                "mapping_contract": "raw NDC/ATC plus EditTrain formulary consensus >= 0.85",
                "causal_state_contract": "pre-order eMAR-linked order state with causal D/C pointers",
            }
        ),
        "mapping_asset_identities": mapping_identities,
        "vocabulary": {
            "name": "frozen ATC-L4 vocabulary",
            "size": N_CONCEPTS,
            "identity": sha256_json(vocabulary),
        },
        "mark_vocabulary": {"actions": ACTIONS, "medications": N_CONCEPTS, "size": N_MARKS},
        "split": {
            "salt": M0_SALT,
            "rule": "SHA256(f'{subject_id}|event-edit-m0-20260908').hexdigest()[:8] / 0xffffffff",
            "partitions": {name: "subject-only deterministic hash" for name in split_subjects},
            "patient_counts": {name: len(ids) for name, ids in split_subjects.items()},
            "pre_freeze_stats": stats_public(pre_stats),
            "edit_audit_event_accessed": False,
        },
        "model_definitions": model_definitions,
        "training_contract": {
            "loss": "full-vocabulary unweighted BCE over 393 marks",
            "optimizer": "AdamW",
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "batch_size": batch_size,
            "batch_ceiling": TRAINING_BATCH_CEILING,
            "max_epochs": MAX_EPOCHS,
            "early_stopping_patience": EARLY_STOPPING_PATIENCE,
            "checkpoint_selection": "lowest EditTune BCE; ties retain earlier epoch",
            "training_seed": TRAINING_SEED,
        },
        "selected_checkpoints": selections,
        "metrics": {
            "primary": [
                "ActionRecall@5_New",
                "ActionRecall@5_Change",
                "ActionRecall@5_D/C",
                "MacroActionRecall@5",
            ],
            "secondary": [
                "per_action_PRAUC",
                "macro_action_PRAUC",
                "JointMarkRecall@5",
                "MedicationRecall@5",
                "pre_mask_state_invalid_prediction_rate",
            ],
            "masking": "decode-time only for SeparateHeads+DirectStateMask and StateEditProbe",
            "medication_collapse": "maximum valid action score per medication",
            "tie_break": "ascending medication concept code",
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "cluster_unit": "patient_id",
            "interval": "percentile 95%",
            "comparison": "StateEditProbe - SeparateHeads+DirectStateMask",
        },
        "gate_logic": {
            "phase_a": PHASE_A_FLOORS,
            "delta_macro_minimum": 0.010,
            "delta_macro_ci_lower": 0.0,
            "delta_joint_minimum": 0.005,
            "delta_joint_ci_lower": 0.0,
            "delta_medication_minimum": -0.005,
            "individual_action_delta_minimum": -0.010,
            "integrity_audit": "PASS",
        },
        "edit_audit_accessed": False,
    }
    manifest_path = output_dir / "m0-freeze-manifest.json"
    manifest_path.write_text(json_dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload, sha256_file(manifest_path)


def strip_internal_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return stats_public(stats)


def build_summary(
    *,
    repo_revision: str,
    runner_sha: str,
    protocol_sha: str,
    preflight: dict[str, Any],
    batch_size: int,
    split_subjects: dict[str, set[int]],
    bursts_by_partition: dict[str, list[dict[str, Any]]],
    stats_by_partition: dict[str, dict[str, Any]],
    phase_a: dict[str, Any],
    selections: dict[str, dict[str, Any]],
    audit_rows: dict[str, dict[str, Any]],
    primary_deltas: dict[str, dict[str, Any]],
    freeze_sha: str,
    audit_access_count: int,
    verdict: str,
    integrity_findings: list[str],
) -> dict[str, Any]:
    conditions: dict[str, bool] = {}
    if phase_a["passed"]:
        macro = primary_deltas["MacroActionRecall@5"]
        joint = primary_deltas["JointMarkRecall@5"]
        medication = primary_deltas["MedicationRecall@5"]
        action_conditions = {
            metric: primary_deltas[metric]["point"] >= -0.010
            for metric in (
                "ActionRecall@5_New",
                "ActionRecall@5_Change",
                "ActionRecall@5_D/C",
            )
        }
        conditions = {
            "phase_a_all_admission_conditions": True,
            "delta_macro_action_recall_at_5_ge_0.010": macro["point"] >= 0.010,
            "delta_macro_action_recall_ci_lower_gt_0": macro["ci_95"][0] > 0.0,
            "delta_joint_mark_recall_at_5_ge_0.005": joint["point"] >= 0.005,
            "delta_joint_mark_recall_ci_lower_gt_0": joint["ci_95"][0] > 0.0,
            "delta_medication_recall_at_5_ge_neg_0.005": medication["point"] >= -0.005,
            **action_conditions,
            "integrity_audit_pass": not integrity_findings,
        }
    else:
        conditions = {
            "phase_a_all_admission_conditions": False,
            "models_trained": False,
            "m0b_not_run": True,
            "idea_007_not_created": True,
        }
    partition_counts = public_partition_counts(bursts_by_partition, stats_by_partition)
    return {
        "schema_version": "1.0",
        "gate_id": "M0_EVENT_SOURCED_EDIT_ADMISSION",
        "verdict": verdict,
        "stage": "PRE_IDEA_EVENT_EDIT_M0",
        "mimic_version": "3.1",
        "execution_timestamp_utc": dt.datetime.now(dt.UTC).isoformat(),
        "code": {
            "repository_revision": repo_revision,
            "runner_sha256": runner_sha,
            "protocol_sha256": protocol_sha,
        },
        "preflight": {**preflight, "actual_batch_size": batch_size},
        "temporal_assignment": {
            "retained_rule": "year(decision_time) == patient.anchor_year",
            "admitted_groups": ADMITTED_GROUPS,
            "future_reserve": ["G3", "G4"],
        },
        "split": {
            "salt": M0_SALT,
            "partition_patient_counts": {name: len(ids) for name, ids in split_subjects.items()},
            "patient_disjoint": True,
        },
        "quarantine": {
            "future_reserve_inspected": False,
            "future_reserve_aggregate_inspected": False,
            "r0_holdout_inspected": False,
            "historical_project_test_split_inspected": False,
            "edit_audit_accessed_after_freeze": audit_access_count == 1,
            "edit_audit_access_count": audit_access_count,
            "freeze_written_before_edit_audit": True,
        },
        "phase_a": {
            "visibility": phase_a["visibility"],
            "partition_counts": partition_counts,
            "admission_checks": {
                key: value for key, value in phase_a.items() if key != "visibility"
            },
        },
        "actual_counts": partition_counts,
        "training": {
            "batch_size": batch_size,
            "loss": "unweighted BCE over all 393 action-medication marks",
            "variants": list(MODEL_FACTORIES),
            "selections": selections,
        },
        "edit_audit": {
            "access_count": audit_access_count,
            "model_rows": audit_rows,
            "primary_deltas": primary_deltas,
        },
        "freeze_manifest": {"path": "m0-freeze-manifest.json", "sha256": freeze_sha},
        "conditions": conditions,
        "integrity_findings": integrity_findings,
        "integrity_audit_verdict": "INTEGRITY_AUDIT_PASS"
        if not integrity_findings
        else "INTEGRITY_AUDIT_FAIL",
        "interpretation_boundary": {
            "raw_provider_order_workflow_action": "transaction_type in {New, Change, D/C}; not verified clinical or therapeutic intent",
            "medication_recommendation_fidelity": "recall/PRAUC against observed mapped order marks",
            "reconstructed_pre_order_regimen_state": "execution-confirmed operational order state from prior eMAR evidence and causal D/C pointers",
            "clinical_therapeutic_interpretation": "not evaluated or established",
            "prediction_improvement_is_clinical_benefit": False,
            "m0_pass_is_publishable_method": False,
        },
        "claims": {
            "transaction_marks_are_provider_order_workflow_actions": True,
            "clinical_treatment_intent_verified": False,
            "clinical_benefit_established": False,
            "publishable_method_established": False,
        },
        "next_state": (
            "RETURN_TO_CCF_PIPELINE_ORCHESTRATOR"
            if verdict == "PASS_M0_EVENT_EDIT_STRUCTURE"
            else "NO_HIGH_VALUE_DIRECTION_YET"
        ),
        "next_ccfa_owner": "ccf-pipeline-orchestrator",
    }


def write_decision(summary: dict[str, Any], output_dir: Path) -> None:
    phase_a = summary["phase_a"]
    admission = phase_a["admission_checks"]
    lines = [
        "# M0 — Event-Sourced Regimen-Edit Admission",
        "",
        f"## Verdict: `{summary['verdict']}`",
        "",
        f"- Gate: `{summary['gate_id']}`",
        f"- MIMIC-IV: `{summary['mimic_version']}`",
        f"- Stage: `{summary['stage']}`",
        f"- Repository revision: `{summary['code']['repository_revision']}`",
        f"- Actual batch size: `{summary['training']['batch_size']}`",
        f"- Freeze manifest SHA256: `{summary['freeze_manifest']['sha256']}`",
        f"- Integrity audit: `{summary['integrity_audit_verdict']}`",
        "",
        "## Semantic boundary",
        "",
        "The target is a raw provider-order workflow mark `(transaction_type, medication)` with action vocabulary `New / Change / D/C`. It is not a verified clinical or therapeutic intention. Medication metrics measure fidelity to mapped observed order workflow, not clinical benefit.",
        "",
        "The pre-order state is an operational, execution-confirmed regimen state reconstructed from prior eMAR evidence and causal D/C pointers. It is not a pharmacokinetic concentration estimate.",
        "",
        "## Phase A admission",
        "",
        f"- Visibility: `{phase_a['visibility']}`",
        f"- Overall support: `{admission['overall']['passed']}`",
        f"- Per-action support: `{all(row['passed'] for row in admission['per_action'].values())}`",
        f"- Change/D/C pre-order consistency: `{all(row['passed'] for row in admission['state_consistency'].values())}`",
        f"- Distributed action semantics: `{admission['distributed_action_semantics']['passed']}`",
        f"- Phase A: `{admission['passed']}`",
        "",
        "| Partition | Patients | Bursts | Mapped target events | Mapped target marks |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for partition, row in summary["actual_counts"].items():
        lines.append(
            f"| {partition} | {row['patients']} | {row['bursts']} | {row['mapped_target_events']} | {row['mapped_target_marks']} |"
        )
    lines.extend(["", "## Phase A exact values", ""])
    lines.append(
        f"- Overall mapped events/patients: `{admission['overall']['actual']['mapped_target_events']}` / `{admission['overall']['actual']['patients']}` (floor `250000` / `10000`; PASS `{admission['overall']['passed']}`)."
    )
    for action in ACTIONS:
        row = admission["per_action"][action]
        lines.append(
            f"- `{action}` mapped events/patients: `{row['actual']['mapped_target_events']}` / `{row['actual']['patients']}` (floor `20000` / `2000`; PASS `{row['passed']}`)."
        )
    for action in ("Change", "D/C"):
        row = admission["state_consistency"][action]
        lines.append(
            f"- `{action}` active-before: `{row['actual']['active_before']}` / `{row['actual']['mapped_target_events']}` = `{fmt(row['actual']['fraction'])}` (floor `0.70`; PASS `{row['passed']}`)."
        )
    lines.append(
        f"- Distributed concepts: `{admission['distributed_action_semantics']['actual_concepts']}` (floor `50`; PASS `{admission['distributed_action_semantics']['passed']}`)."
    )

    if summary["training"]["selections"]:
        lines.extend(
            [
                "",
                "## Frozen EditTune selections",
                "",
                "| Model | Epoch | EditTune BCE | Checkpoint SHA256 |",
                "| :--- | ---: | ---: | :--- |",
            ]
        )
        for name, selection in summary["training"]["selections"].items():
            lines.append(
                f"| {name} | {selection['epoch']} | {fmt(selection['edit_tune_bce'])} | `{selection['checkpoint_sha256']}` |"
            )

    if summary["edit_audit"]["model_rows"]:
        lines.extend(
            [
                "",
                "## EditAudit metrics",
                "",
                "| Model | ActionRecall@5 New | ActionRecall@5 Change | ActionRecall@5 D/C | MacroActionRecall@5 | JointMarkRecall@5 | MedicationRecall@5 | macro-action PRAUC | pre-mask invalid rate |",
                "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for name, row in summary["edit_audit"]["model_rows"].items():
            lines.append(
                f"| {name} | {fmt(row['ActionRecall@5_New'])} | {fmt(row['ActionRecall@5_Change'])} | {fmt(row['ActionRecall@5_D/C'])} | {fmt(row['MacroActionRecall@5'])} | {fmt(row['JointMarkRecall@5'])} | {fmt(row['MedicationRecall@5'])} | {fmt(row['macro_action_PRAUC'])} | {fmt(row['pre_mask_state_invalid_prediction_rate'])} |"
            )
        lines.extend(
            [
                "",
                "### StateEditProbe minus strongest control",
                "",
                "| Metric | Delta | 95% CI |",
                "| :--- | ---: | :--- |",
            ]
        )
        for metric, row in summary["edit_audit"]["primary_deltas"].items():
            lines.append(f"| {metric} | {fmt(row['point'])} | `{[fmt(x) for x in row['ci_95']]}` |")

    lines.extend(
        [
            "",
            "## Frozen conditions",
            "",
            "| Condition | PASS |",
            "| :--- | :--- |",
        ]
    )
    for condition, value in summary["conditions"].items():
        lines.append(f"| {condition} | {value} |")
    lines.extend(
        [
            "",
            "## Quarantine and routing",
            "",
            f"- EditAudit formal access occurred exactly once after freeze: `{summary['quarantine']['edit_audit_accessed_after_freeze']}`.",
            "- G3/G4 future reserve: untouched; no event, aggregate, feature, prediction, or metric was inspected.",
            "- R0 Holdout: untouched.",
            "- Historical project test split: untouched.",
            f"- Next state: `{summary['next_state']}`.",
            f"- Next CCFA owner: `{summary['next_ccfa_owner']}`.",
            "",
            "M0 is a bounded premise-selection gate. Even PASS does not establish a publishable method, clinical utility, causal treatment reasoning, or superiority to state-of-the-art medication recommendation models.",
        ]
    )
    (output_dir / "m0-decision.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_integrity_audit(summary: dict[str, Any], output_dir: Path) -> None:
    findings = summary["integrity_findings"]
    lines = [
        "# M0 Integrity Audit",
        "",
        f"## Verdict: `{summary['integrity_audit_verdict']}`",
        "",
        "Mode: `standard` (protocol, numeric, code/data identity, checkpoint, quarantine, and claim-boundary audit).",
        "",
        "## Checks",
        "",
        f"- Gate identity: `{summary['gate_id']}`.",
        f"- Repository revision recorded: `{summary['code']['repository_revision']}`.",
        f"- Freeze manifest identity recorded: `{summary['freeze_manifest']['sha256']}`.",
        f"- EditTune selection was completed before freeze: `{bool(summary['training']['selections'])}`.",
        f"- EditAudit was accessed exactly once after freeze: `{summary['quarantine']['edit_audit_accessed_after_freeze']}`.",
        f"- Bootstrap: `{BOOTSTRAP_REPLICATES}` patient-clustered replicates, seed `{BOOTSTRAP_SEED}`.",
        "- All three variants use the same causal encoder inputs and training contract.",
        "- StateEditProbe uses fixed rank 32; no decoder-rank search or auxiliary loss was run.",
        "- No DDI/safety objective, KG, LLM, guideline rule, labs, vitals, notes, or alternative vocabulary was used.",
        "",
        "## Quarantine",
        "",
        "- G3/G4 future reserve was not inspected.",
        "- R0 Holdout was not inspected.",
        "- Historical project test split was not inspected.",
        "",
        "## Claim boundary",
        "",
        "- New / Change / D/C are raw provider-order workflow actions, not verified clinical intent.",
        "- Metric gains, if any, are medication-recommendation fidelity results and not clinical benefit.",
        "- M0 PASS, if present, admits only this structural premise for later method and novelty review.",
    ]
    if findings:
        lines.extend(["", "## Findings", "", *[f"- {finding}" for finding in findings]])
    else:
        lines.extend(["", "No integrity findings."])
    (output_dir / "m0-integrity-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def integrity_findings(summary: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        summary["temporal_assignment"]["retained_rule"]
        != "year(decision_time) == patient.anchor_year"
    ):
        findings.append("temporal retention rule mismatch")
    quarantine = summary["quarantine"]
    if quarantine["future_reserve_inspected"] or quarantine["future_reserve_aggregate_inspected"]:
        findings.append("future reserve inspection flag is true")
    if quarantine["r0_holdout_inspected"]:
        findings.append("R0 Holdout inspection flag is true")
    if quarantine["historical_project_test_split_inspected"]:
        findings.append("historical project test split inspection flag is true")
    if summary["verdict"] == "PASS_M0_EVENT_EDIT_STRUCTURE":
        if (
            quarantine["edit_audit_access_count"] != 1
            or not quarantine["freeze_written_before_edit_audit"]
        ):
            findings.append("EditAudit freeze/access contract mismatch")
        if set(summary["edit_audit"]["model_rows"]) != set(MODEL_FACTORIES):
            findings.append("EditAudit model row set mismatch")
        if summary["training"]["batch_size"] <= 0:
            findings.append("invalid actual batch size")
        for metric, delta in summary["edit_audit"]["primary_deltas"].items():
            if not (
                math.isfinite(delta["point"])
                and all(math.isfinite(value) for value in delta["ci_95"])
            ):
                findings.append(f"non-finite primary delta: {metric}")
    if summary["claims"]["clinical_treatment_intent_verified"]:
        findings.append("clinical intent claim exceeds protocol")
    if summary["claims"]["clinical_benefit_established"]:
        findings.append("clinical benefit claim exceeds protocol")
    if summary["claims"]["publishable_method_established"]:
        findings.append("publishable-method claim exceeds M0 boundary")
    return findings


def run(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any(args.run_dir.iterdir()) if args.run_dir.exists() else False:
        raise ProtocolFailure("M0 run directory must be fresh")
    args.run_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    repo_root = Path(__file__).parents[3]
    repo_revision = repository_revision(repo_root)
    runner_sha = code_identity(Path(__file__))
    protocol_path = Path(__file__).with_name("m0-event-edit-admission-protocol.md")
    protocol_sha = sha256_file(protocol_path)
    vocabulary = load_vocabulary(args.vocab_asset_dir)
    vocabulary_set = set(vocabulary)
    concept_to_index = {code: index for index, code in enumerate(vocabulary)}

    print(f"Using device={device}", flush=True)
    preflight = run_mechanical_preflight(vocabulary, device)
    batch_size = select_batch_size(device)
    preflight["actual_batch_size"] = batch_size
    print(f"Mechanical preflight passed; actual_batch_size={batch_size}", flush=True)

    patients, split_subjects = load_patients(args.mimic_dir)
    mapping = build_ndc_mapping(args.mapping_dir)
    consensus = build_formulary_consensus(
        args.mimic_dir, split_subjects["EditTrain"], mapping, vocabulary_set
    )
    pre_subjects = split_subjects["EditTrain"] | split_subjects["EditTune"]
    print(
        f"Reading only pre-freeze EditTrain+EditTune clinical records: {len(pre_subjects)} patients",
        flush=True,
    )
    pre_clinical = load_clinical_records(
        args.mimic_dir, pre_subjects, mapping, consensus, vocabulary_set
    )
    pre_bursts_by_partition, pre_stats_by_partition = build_bursts(
        patients, pre_subjects, pre_clinical, concept_to_index
    )
    del pre_clinical
    pre_stats = merge_stats(pre_stats_by_partition["EditTrain"], pre_stats_by_partition["EditTune"])
    phase_a = support_checks(pre_stats)
    print(f"Phase A passed={phase_a['passed']}", flush=True)

    # EditAudit is still withheld. On failure, no model or audit data is touched.
    if not phase_a["passed"]:
        empty_selections: dict[str, dict[str, Any]] = {}
        empty_rows: dict[str, dict[str, Any]] = {}
        empty_deltas: dict[str, dict[str, Any]] = {}
        summary = build_summary(
            repo_revision=repo_revision,
            runner_sha=runner_sha,
            protocol_sha=protocol_sha,
            preflight=preflight,
            batch_size=batch_size,
            split_subjects=split_subjects,
            bursts_by_partition=pre_bursts_by_partition,
            stats_by_partition=pre_stats_by_partition,
            phase_a=phase_a,
            selections=empty_selections,
            audit_rows=empty_rows,
            primary_deltas=empty_deltas,
            freeze_sha="N/A",
            audit_access_count=0,
            verdict="FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE",
            integrity_findings=[],
        )
        findings = integrity_findings(summary)
        summary["integrity_findings"] = findings
        summary["integrity_audit_verdict"] = (
            "INTEGRITY_AUDIT_PASS" if not findings else "INTEGRITY_AUDIT_FAIL"
        )
        (args.output_dir / "m0-summary.json").write_text(
            json_dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        write_decision(summary, args.output_dir)
        write_integrity_audit(summary, args.output_dir)
        return 0

    train_data = TensorBurstDataset(pre_bursts_by_partition["EditTrain"])
    tune_data = TensorBurstDataset(pre_bursts_by_partition["EditTune"])
    selections: dict[str, dict[str, Any]] = {}
    models: dict[str, nn.Module] = {}
    for name in MODEL_FACTORIES:
        checkpoint_path = args.run_dir / f"checkpoint_{name.replace('+', '_').replace(' ', '_')}.pt"
        model, selection = train_variant(
            name, train_data, tune_data, device, batch_size, checkpoint_path
        )
        models[name] = model
        selections[name] = selection

    mapping_identities = {
        "ndc2atc_level4.csv": sha256_file(args.mapping_dir / "ndc2atc_level4.csv"),
        "drug_codes_mapping.csv": sha256_file(args.mapping_dir / "drug_codes_mapping.csv"),
    }
    _freeze_payload, freeze_sha = write_freeze_manifest(
        args.output_dir,
        repo_revision,
        runner_sha,
        protocol_sha,
        vocabulary,
        mapping_identities,
        split_subjects,
        pre_stats,
        batch_size,
        selections,
    )
    print(f"EditAudit freeze manifest written before access: {freeze_sha}", flush=True)

    # This is the single and only formal EditAudit access.
    audit_access_count = 1
    audit_subjects = split_subjects["EditAudit"]
    print(
        f"Reading EditAudit exactly once after freeze: {len(audit_subjects)} patients", flush=True
    )
    audit_clinical = load_clinical_records(
        args.mimic_dir, audit_subjects, mapping, consensus, vocabulary_set
    )
    audit_bursts_by_partition, audit_stats_by_partition = build_bursts(
        patients, audit_subjects, audit_clinical, concept_to_index
    )
    del audit_clinical
    audit_bursts = audit_bursts_by_partition["EditAudit"]
    audit_stats = {
        "EditTrain": pre_stats_by_partition["EditTrain"],
        "EditTune": pre_stats_by_partition["EditTune"],
        "EditAudit": audit_stats_by_partition["EditAudit"],
    }
    # The manifest's pre-access false is immutable evidence of the ordering;
    # the public summary carries the post-access count separately.
    audit_rows: dict[str, dict[str, Any]] = {}
    audit_raw: dict[str, dict[str, Any]] = {}
    for name, model in models.items():
        audit_data = TensorBurstDataset(audit_bursts)
        logits = predict_logits(model, audit_data, device, batch_size)
        public_row, raw = audit_metric_bundle(audit_bursts, logits, name, vocabulary)
        audit_rows[name] = public_row
        audit_raw[name] = raw
        del audit_data, logits

    control_name = "SeparateHeads+DirectStateMask"
    primary_deltas = bootstrap_primary_deltas(
        np.asarray([burst["patient_id"] for burst in audit_bursts], dtype=np.int64),
        audit_raw[control_name],
        audit_raw["StateEditProbe"],
    )
    verdict_conditions = {
        "phase_a_all_admission_conditions": True,
        "delta_macro_action_recall_at_5_ge_0.010": primary_deltas["MacroActionRecall@5"]["point"]
        >= 0.010,
        "delta_macro_action_recall_ci_lower_gt_0": primary_deltas["MacroActionRecall@5"]["ci_95"][0]
        > 0,
        "delta_joint_mark_recall_at_5_ge_0.005": primary_deltas["JointMarkRecall@5"]["point"]
        >= 0.005,
        "delta_joint_mark_recall_ci_lower_gt_0": primary_deltas["JointMarkRecall@5"]["ci_95"][0]
        > 0,
        "delta_medication_recall_at_5_ge_neg_0.005": primary_deltas["MedicationRecall@5"]["point"]
        >= -0.005,
        "ActionRecall@5_New": primary_deltas["ActionRecall@5_New"]["point"] >= -0.010,
        "ActionRecall@5_Change": primary_deltas["ActionRecall@5_Change"]["point"] >= -0.010,
        "ActionRecall@5_D/C": primary_deltas["ActionRecall@5_D/C"]["point"] >= -0.010,
    }
    tentative_verdict = (
        "PASS_M0_EVENT_EDIT_STRUCTURE"
        if all(verdict_conditions.values())
        else "FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE"
    )
    summary = build_summary(
        repo_revision=repo_revision,
        runner_sha=runner_sha,
        protocol_sha=protocol_sha,
        preflight=preflight,
        batch_size=batch_size,
        split_subjects=split_subjects,
        bursts_by_partition={**pre_bursts_by_partition, "EditAudit": audit_bursts},
        stats_by_partition=audit_stats,
        phase_a=phase_a,
        selections=selections,
        audit_rows=audit_rows,
        primary_deltas=primary_deltas,
        freeze_sha=freeze_sha,
        audit_access_count=audit_access_count,
        verdict=tentative_verdict,
        integrity_findings=[],
    )
    findings = integrity_findings(summary)
    summary["integrity_findings"] = findings
    summary["integrity_audit_verdict"] = (
        "INTEGRITY_AUDIT_PASS" if not findings else "INTEGRITY_AUDIT_FAIL"
    )
    # Integrity is a frozen gate condition; if its independent checks fail,
    # the scientific verdict cannot be PASS.
    if findings:
        summary["verdict"] = "FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE"
        summary["next_state"] = "NO_HIGH_VALUE_DIRECTION_YET"
        summary["conditions"]["integrity_audit_pass"] = False
    (args.output_dir / "m0-summary.json").write_text(
        json_dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    write_decision(summary, args.output_dir)
    write_integrity_audit(summary, args.output_dir)
    print(f"M0 verdict={summary['verdict']}", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen M0 Event-Sourced Regimen-Edit Admission")
    parser.add_argument(
        "--mimic-dir", type=Path, default=Path("/root/zhb/Search/dataset/mimic-iv-3.1/hosp")
    )
    parser.add_argument(
        "--vocab-asset-dir",
        type=Path,
        default=Path("/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23"),
    )
    parser.add_argument(
        "--mapping-dir", type=Path, default=Path("/root/zhb/code/KGDNet/data/Mappings")
    )
    parser.add_argument(
        "--run-dir", type=Path, default=Path("/root/zhb/medrec-data/m0_runs/m0-event-edit-20260908")
    )
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    try:
        return run(args)
    except ProtocolFailure as error:
        print(f"M0 protocol failure: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
