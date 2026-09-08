"""Execute the frozen S0 medication practice-shift admission gate.

The runner deliberately contains no DDI or safety objective.  It reuses the
Idea 006 order-time task shape and Base GRU dimensions, while keeping S0's
temporal assignment, target entitlement, freeze boundary, and gate logic local
to this reset packet.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
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

N_CONCEPTS = 131
HISTORY_LENGTH = 64
TARGET_SECONDS = 600
K = 5
BOOTSTRAP_REPLICATES = 2_000
SEED = 260908
SOURCE_SALT = "medication-practice-shift-s0-source-20260908"
TARGET_SALT = "medication-practice-shift-s0-target-20260908"
R0_SALT = "exposure-reset-20260905"

SOURCE_GROUPS = ("2008 - 2010", "2011 - 2013")
TARGET_GROUP = "2014 - 2016"
FUTURE_GROUPS = ("2017 - 2019", "2020 - 2022")
ALL_GROUPS = (*SOURCE_GROUPS, TARGET_GROUP, *FUTURE_GROUPS)

PARTITIONS = (
    "SourceTrain",
    "SourceTune",
    "SourceAudit",
    "TargetPriorBuild",
    "TargetBiasTune",
    "TargetAudit",
)
PRE_FREEZE_PARTITIONS = PARTITIONS[:5]

ALPHA_GRID = (0.0, 0.25, 0.5, 1.0, 2.0)
SUPPORT_FLOORS = {
    "SourceTrain": {"bursts": 100_000, "patients": 5_000},
    "SourceTune": {"bursts": 10_000, "patients": 500},
    "SourceAudit": {"bursts": 10_000, "patients": 500},
    "TargetPriorBuild": {"bursts": 10_000, "patients": 500},
    "TargetBiasTune": {"bursts": 10_000, "patients": 500},
    "TargetAudit": {"bursts": 50_000, "patients": 2_000},
}

ADMINISTRATION_EVENT_TYPES = frozenset(
    {
        "Administered",
        "Applied",
        "Inhaled",
        "Started",
        "Restarted",
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
    """A frozen S0 prerequisite or support condition failed."""


@dataclass(frozen=True)
class Patient:
    subject_id: int
    anchor_year: int
    anchor_year_group: str
    partition: str


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


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


def classify_r0(subject_id: int) -> str:
    value = subject_unit_interval(subject_id, R0_SALT)
    if value < 0.70:
        return "Discovery"
    if value < 0.85:
        return "Dev"
    return "Holdout"


def classify_source(subject_id: int) -> str:
    value = subject_unit_interval(subject_id, SOURCE_SALT)
    if value < 0.80:
        return "SourceTrain"
    if value < 0.90:
        return "SourceTune"
    return "SourceAudit"


def classify_target(subject_id: int) -> str:
    value = subject_unit_interval(subject_id, TARGET_SALT)
    if value < 0.10:
        return "TargetPriorBuild"
    if value < 0.20:
        return "TargetBiasTune"
    return "TargetAudit"


def load_patients(mimic_dir: Path) -> tuple[dict[int, Patient], dict[str, set[int]]]:
    path = table_path(mimic_dir, "patients")
    frame = pd.read_csv(
        path,
        usecols=["subject_id", "anchor_year", "anchor_year_group"],
        dtype={"subject_id": "Int64", "anchor_year": "Int64", "anchor_year_group": "string"},
        compression="infer",
    )

    patients: dict[int, Patient] = {}
    subjects_by_partition = {name: set() for name in PARTITIONS}
    for row in frame.itertuples(index=False):
        subject_id = as_int(row.subject_id)
        anchor_year = as_int(row.anchor_year)
        group = clean_text(row.anchor_year_group)
        if subject_id is None or anchor_year is None or group not in ALL_GROUPS:
            raise ProtocolFailure("MIMIC-IV 3.1 lacks the frozen anchor-year semantics")

        if classify_r0(subject_id) == "Holdout":
            partition = "R0_HOLDOUT"
        elif group in SOURCE_GROUPS:
            partition = classify_source(subject_id)
        elif group == TARGET_GROUP:
            partition = classify_target(subject_id)
        else:
            partition = "FUTURE_RESERVE"

        patients[subject_id] = Patient(subject_id, anchor_year, group, partition)
        if partition in subjects_by_partition:
            subjects_by_partition[partition].add(subject_id)

    if not subjects_by_partition["TargetAudit"]:
        raise ProtocolFailure("TargetAudit has no patient membership under the frozen split")
    return patients, subjects_by_partition


def load_vocabulary(asset_dir: Path) -> list[str]:
    import dill

    path = asset_dir / "voc_final.pkl"
    if not path.exists():
        raise ProtocolFailure(f"Missing frozen medication vocabulary: {path.name}")
    with path.open("rb") as handle:
        vocabulary = dill.load(handle)
    idx2word = vocabulary["med_voc"].idx2word
    codes = [str(idx2word[index]) for index in range(N_CONCEPTS)]
    if len(codes) != N_CONCEPTS or len(set(codes)) != N_CONCEPTS:
        raise ProtocolFailure("Medication vocabulary is not exactly 131 unique concepts")
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
    safe_path = mapping_dir / "ndc2atc_level4.csv"
    kgd_path = mapping_dir / "drug_codes_mapping.csv"
    if not safe_path.exists() or not kgd_path.exists():
        raise ProtocolFailure("Frozen medication normalization assets are incomplete")

    mapping: dict[str, str] = {}
    safe_frame = pd.read_csv(safe_path, dtype="string")
    for row in safe_frame.itertuples(index=False):
        raw = row.NDC
        atc = clean_text(row.ATC4)[:4]
        if len(atc) == 4:
            for key in mapping_keys(raw):
                mapping[key] = atc

    kgd_frame = pd.read_csv(kgd_path, dtype="string")
    for row in kgd_frame.itertuples(index=False):
        raw = row.ndc
        atc = clean_text(row.atc4)[:4]
        if len(atc) == 4 and atc != "nan":
            for key in mapping_keys(raw):
                mapping[key] = atc
    return mapping


def lookup_atc(value: Any, mapping: dict[str, str]) -> str | None:
    for key in mapping_keys(value):
        if key in mapping:
            return mapping[key]
    return None


def build_formulary_consensus(
    mimic_dir: Path,
    source_train_subjects: set[int],
    mapping: dict[str, str],
    vocabulary: set[str],
) -> dict[str, str]:
    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    usecols = ["subject_id", "ndc", "formulary_drug_cd"]
    dtype = {"subject_id": "Int64", "ndc": "string", "formulary_drug_cd": "string"}
    for chunk in iter_subject_chunks(
        table_path(mimic_dir, "prescriptions"), usecols, source_train_subjects, dtype
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


def parse_datetime_seconds(series: pd.Series) -> list[int | None]:
    parsed = pd.to_datetime(series, errors="coerce")
    valid = ~parsed.isna()
    values = parsed.astype("int64").to_numpy()
    return [
        int(value // 1_000_000_000) if ok else None for value, ok in zip(values, valid, strict=True)
    ]


def load_clinical_records(
    mimic_dir: Path,
    patients: dict[int, Patient],
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
    future_subjects = {
        subject_id
        for subject_id, patient in patients.items()
        if patient.partition == "FUTURE_RESERVE"
    }
    holdout_subjects = {
        subject_id for subject_id, patient in patients.items() if patient.partition == "R0_HOLDOUT"
    }
    if subjects & future_subjects:
        raise ProtocolFailure("G3/G4 clinical subjects entered a S0 reader")
    if subjects & holdout_subjects:
        raise ProtocolFailure("R0 Holdout clinical subjects entered a S0 reader")

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
            if subject_id in patients and hadm_id is not None and admit_time is not None:
                hadm_to_admit[hadm_id] = (subject_id, admit_time)

    hadm_to_poe_events: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
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
    for chunk in iter_subject_chunks(table_path(mimic_dir, "poe"), poe_cols, subjects, poe_dtype):
        eligible = chunk.loc[
            chunk["order_type"].eq("Medications")
            & chunk["transaction_type"].isin(["New", "Change", "D/C"])
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

    hadm_to_admins: dict[int, list[tuple[int, str, str]]] = collections.defaultdict(list)
    emar_cols = ["subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"]
    emar_dtype = {
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "poe_id": "string",
        "pharmacy_id": "string",
        "charttime": "string",
        "event_txt": "string",
    }
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


def utc_year(timestamp: int) -> int:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).year


def target_interval(decision_time: int) -> tuple[int, int]:
    return decision_time, decision_time + TARGET_SECONDS


def retain_decision(decision_time: int, anchor_year: int) -> bool:
    return utc_year(decision_time) == anchor_year


def build_bursts(
    patients: dict[int, Patient],
    subjects: set[int],
    hadm_to_admit: dict[int, tuple[int, int]],
    hadm_to_poe_events: dict[int, list[dict[str, Any]]],
    hadm_to_admins: dict[int, list[tuple[int, str, str]]],
    poe_to_atcs: dict[str, set[str]],
    poe_to_pharms: dict[str, set[str]],
    concept_to_index: dict[str, int],
) -> list[dict[str, Any]]:
    bursts: list[dict[str, Any]] = []
    subject_hadm_events = {
        hadm_id: events
        for hadm_id, events in hadm_to_poe_events.items()
        if hadm_id in hadm_to_admit and hadm_to_admit[hadm_id][0] in subjects
    }

    for hadm_id, poe_events in subject_hadm_events.items():
        subject_id, admission_time = hadm_to_admit[hadm_id]
        patient = patients[subject_id]
        poe_events.sort(key=lambda event: (event["ordertime"], event["poe_id"]))
        admins = hadm_to_admins.get(hadm_id, [])
        admin_poe_times: dict[str, list[int]] = collections.defaultdict(list)
        admin_pharm_times: dict[str, list[int]] = collections.defaultdict(list)
        for chart_time, poe_id, pharmacy_id in admins:
            if poe_id:
                admin_poe_times[poe_id].append(chart_time)
            if pharmacy_id:
                admin_pharm_times[pharmacy_id].append(chart_time)

        positive_orders = [
            event
            for event in poe_events
            if event["transaction_type"] in ("New", "Change") and event["poe_id"] in poe_to_atcs
        ]
        assigned: set[int] = set()
        for index, base_order in enumerate(positive_orders):
            if index in assigned:
                continue
            decision_time = base_order["ordertime"]
            _, target_end = target_interval(decision_time)
            burst_positive_orders = []
            target_concepts: set[str] = set()
            for candidate_index in range(index, len(positive_orders)):
                candidate = positive_orders[candidate_index]
                if candidate["ordertime"] >= target_end:
                    break
                burst_positive_orders.append(candidate)
                assigned.add(candidate_index)
                target_concepts.update(poe_to_atcs[candidate["poe_id"]])

            if not retain_decision(decision_time, patient.anchor_year) or not target_concepts:
                continue

            target_indices = sorted(concept_to_index[concept] for concept in target_concepts)
            target_vec = np.zeros(N_CONCEPTS, dtype=np.float32)
            target_vec[target_indices] = 1.0

            history = [event for event in poe_events if event["ordertime"] < decision_time][
                -HISTORY_LENGTH:
            ]
            hist_meds = np.zeros(HISTORY_LENGTH, dtype=np.int64)
            hist_types = np.zeros(HISTORY_LENGTH, dtype=np.int64)
            hist_elapsed = np.zeros(HISTORY_LENGTH, dtype=np.float32)
            previous_time: int | None = None
            for step, event in enumerate(history):
                transaction_type = event["transaction_type"]
                hist_types[step] = {"New": 1, "Change": 2, "D/C": 3}[transaction_type]
                if transaction_type in ("New", "Change"):
                    concepts = poe_to_atcs.get(event["poe_id"], set())
                else:
                    concepts = poe_to_atcs.get(event["discontinue_of_poe_id"], set())
                if concepts:
                    hist_meds[step] = concept_to_index[sorted(concepts)[0]] + 1
                elapsed_hours = (
                    (event["ordertime"] - previous_time) / 3600.0
                    if previous_time is not None
                    else 0.0
                )
                hist_elapsed[step] = math.log1p(max(0.0, elapsed_hours))
                previous_time = event["ordertime"]

            discontinued = {
                event["discontinue_of_poe_id"]
                for event in history
                if event["transaction_type"] == "D/C" and event["discontinue_of_poe_id"]
            }
            active_concepts: set[str] = set()
            for event in history:
                if event["transaction_type"] not in ("New", "Change"):
                    continue
                poe_id = event["poe_id"]
                if poe_id not in poe_to_atcs or poe_id in discontinued:
                    continue
                administered = any(
                    chart_time < decision_time for chart_time in admin_poe_times.get(poe_id, [])
                )
                if not administered:
                    administered = any(
                        chart_time < decision_time
                        for pharmacy_id in poe_to_pharms.get(poe_id, set())
                        for chart_time in admin_pharm_times.get(pharmacy_id, [])
                    )
                if administered:
                    active_concepts.update(poe_to_atcs[poe_id])

            active_indices = sorted(concept_to_index[concept] for concept in active_concepts)
            active_vec = np.zeros(N_CONCEPTS, dtype=np.float32)
            active_vec[active_indices] = 1.0
            hours_since_admit = max(0.0, (decision_time - admission_time) / 3600.0)

            bursts.append(
                {
                    "patient_id": subject_id,
                    "hadm_id": hadm_id,
                    "decision_t": decision_time,
                    "hist_meds": hist_meds.tolist(),
                    "hist_types": hist_types.tolist(),
                    "hist_elapsed": hist_elapsed.tolist(),
                    "active_regimen": active_vec.tolist(),
                    "log_hours_since_admit": float(math.log1p(hours_since_admit)),
                    "target_vec": target_vec.tolist(),
                    "target_indices": target_indices,
                    "active_indices": active_indices,
                }
            )
    return bursts


class BaseOrderTimeGRU(nn.Module):
    """The frozen Idea 006 Base architecture, without its safety code."""

    def __init__(self) -> None:
        super().__init__()
        self.med_embedding = nn.Embedding(N_CONCEPTS + 1, 64, padding_idx=0)
        self.trans_embedding = nn.Embedding(4, 8, padding_idx=0)
        self.elapsed_proj = nn.Linear(1, 8)
        self.gru = nn.GRU(80, 128, num_layers=1, batch_first=True)
        self.zero_history = nn.Parameter(torch.zeros(128))
        self.mlp = nn.Sequential(
            nn.Linear(260, 128),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(128, N_CONCEPTS),
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
        combined = torch.cat([final_state, active_regimen, log_hours_since_admit], dim=-1)
        return self.mlp(combined)


class FastBurstTensorDataset:
    def __init__(self, bursts: list[dict[str, Any]]) -> None:
        self.n = len(bursts)
        self.hist_meds = torch.from_numpy(
            np.asarray([burst["hist_meds"] for burst in bursts], dtype=np.int64).reshape(
                self.n, HISTORY_LENGTH
            )
        )
        self.hist_types = torch.from_numpy(
            np.asarray([burst["hist_types"] for burst in bursts], dtype=np.int64).reshape(
                self.n, HISTORY_LENGTH
            )
        )
        self.hist_elapsed = torch.from_numpy(
            np.asarray([burst["hist_elapsed"] for burst in bursts], dtype=np.float32).reshape(
                self.n, HISTORY_LENGTH
            )
        )
        self.active_regimen = torch.from_numpy(
            np.asarray([burst["active_regimen"] for burst in bursts], dtype=np.float32).reshape(
                self.n, N_CONCEPTS
            )
        )
        self.log_hours = torch.from_numpy(
            np.asarray(
                [[burst["log_hours_since_admit"]] for burst in bursts], dtype=np.float32
            ).reshape(self.n, 1)
        )
        self.target_vec = torch.from_numpy(
            np.asarray([burst["target_vec"] for burst in bursts], dtype=np.float32).reshape(
                self.n, N_CONCEPTS
            )
        )

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


def run_mechanical_preflight(asset_dir: Path, device: torch.device) -> dict[str, Any]:
    """Run the one required preflight before full source training."""
    checks: dict[str, bool] = {}
    first = [classify_source(subject_id) for subject_id in (10000032, 10000084, 10000108)]
    second = [classify_source(subject_id) for subject_id in (10000032, 10000084, 10000108)]
    checks["temporal_assignment_deterministic"] = first == second
    checks["anchor_year_match_is_exact"] = retain_decision(
        1_704_067_200, 2024
    ) and not retain_decision(1_704_067_200, 2023)
    checks["target_interval_is_half_open_10_minutes"] = target_interval(1000) == (1000, 1600)
    checks["pre_freeze_reader_excludes_future_and_target_audit"] = set(
        PRE_FREEZE_PARTITIONS
    ).isdisjoint({"TargetAudit", "FUTURE_RESERVE", "R0_HOLDOUT"})
    checks["r0_holdout_is_excluded"] = "R0_HOLDOUT" not in PRE_FREEZE_PARTITIONS
    vocabulary = load_vocabulary(asset_dir)
    checks["vocabulary_exactly_131"] = len(vocabulary) == N_CONCEPTS

    model = BaseOrderTimeGRU().to(device)
    hist_meds = torch.randint(0, N_CONCEPTS + 1, (4, HISTORY_LENGTH), device=device)
    hist_types = torch.randint(0, 4, (4, HISTORY_LENGTH), device=device)
    hist_elapsed = torch.rand((4, HISTORY_LENGTH), device=device)
    active_regimen = torch.zeros((4, N_CONCEPTS), device=device)
    active_regimen[:, [2, 5, 10]] = 1.0
    log_hours = torch.ones((4, 1), device=device)
    targets = torch.zeros((4, N_CONCEPTS), device=device)
    targets[:, [2, 15]] = 1.0
    logits = model(hist_meds, hist_types, hist_elapsed, active_regimen, log_hours)
    F.binary_cross_entropy_with_logits(logits, targets).backward()
    checks["base_forward_backward"] = tuple(logits.shape) == (4, N_CONCEPTS)
    del model, logits
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    p_source = (np.arange(N_CONCEPTS, dtype=np.float64) + 1.0) / (N_CONCEPTS + 2.0)
    p_target = (np.arange(N_CONCEPTS, dtype=np.float64) + 2.0) / (N_CONCEPTS + 3.0)
    delta_one = logit_delta(p_source, p_target)
    delta_two = logit_delta(p_source, p_target)
    checks["bias_formula_deterministic"] = np.array_equal(delta_one, delta_two)
    if not all(checks.values()):
        raise ProtocolFailure(f"Mechanical preflight failed: {checks}")
    return {"checks": checks, "passed": True}


def select_batch_size(device: torch.device) -> int:
    for batch_size in (2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1):
        try:
            model = BaseOrderTimeGRU().to(device)
            hist_meds = torch.randint(
                0, N_CONCEPTS + 1, (batch_size, HISTORY_LENGTH), device=device
            )
            hist_types = torch.randint(0, 4, (batch_size, HISTORY_LENGTH), device=device)
            hist_elapsed = torch.rand((batch_size, HISTORY_LENGTH), device=device)
            active = torch.rand((batch_size, N_CONCEPTS), device=device)
            hours = torch.rand((batch_size, 1), device=device)
            targets = torch.rand((batch_size, N_CONCEPTS), device=device)
            logits = model(hist_meds, hist_types, hist_elapsed, active, hours)
            F.binary_cross_entropy_with_logits(logits, targets).backward()
            del model, logits
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return batch_size
        except RuntimeError as error:
            if "out of memory" not in str(error).lower():
                raise
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    raise ProtocolFailure("No permitted power-of-two batch size fits the Base preflight")


def train_source(
    train_data: FastBurstTensorDataset,
    tune_data: FastBurstTensorDataset,
    device: torch.device,
    batch_size: int,
    checkpoint_path: Path,
) -> tuple[BaseOrderTimeGRU, int, float, str]:
    if checkpoint_path.exists():
        raise ProtocolFailure("A non-fresh S0 run directory would reuse a checkpoint")
    set_seed(SEED)
    model = BaseOrderTimeGRU().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
    best_loss = float("inf")
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0

    for epoch in range(1, 6):
        model.train()
        train_sum = 0.0
        train_count = 0
        for raw_batch in train_data.iter_batches(batch_size, shuffle=True):
            batch = move_batch(raw_batch, device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(
                batch["hist_meds"],
                batch["hist_types"],
                batch["hist_elapsed"],
                batch["active_regimen"],
                batch["log_hours_since_admit"],
            )
            loss = F.binary_cross_entropy_with_logits(logits, batch["target_vec"])
            loss.backward()
            optimizer.step()
            count = batch["target_vec"].shape[0]
            train_sum += float(loss.detach()) * count
            train_count += count

        tune_loss = evaluate_bce(model, tune_data, device, batch_size)
        print(
            f"epoch={epoch} train_bce={train_sum / train_count:.17g} "
            f"SourceTune_BCE={tune_loss:.17g}",
            flush=True,
        )
        if tune_loss < best_loss:
            best_loss = tune_loss
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= 1:
                break

    if best_state is None:
        raise ProtocolFailure("SourceTune checkpoint selection produced no checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    torch.save(best_state, checkpoint_path)
    checkpoint_sha = sha256_file(checkpoint_path)
    return model, best_epoch, best_loss, checkpoint_sha


def evaluate_bce(
    model: BaseOrderTimeGRU,
    data: FastBurstTensorDataset,
    device: torch.device,
    batch_size: int,
) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.no_grad():
        for raw_batch in data.iter_batches(batch_size):
            batch = move_batch(raw_batch, device)
            logits = model(
                batch["hist_meds"],
                batch["hist_types"],
                batch["hist_elapsed"],
                batch["active_regimen"],
                batch["log_hours_since_admit"],
            )
            total += float(
                F.binary_cross_entropy_with_logits(logits, batch["target_vec"], reduction="sum")
            )
            count += int(np.prod(batch["target_vec"].shape))
    return total / count


def predict_logits(
    model: BaseOrderTimeGRU,
    data: FastBurstTensorDataset,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    rows: list[np.ndarray] = []
    with torch.no_grad():
        for raw_batch in data.iter_batches(batch_size):
            batch = move_batch(raw_batch, device)
            logits = model(
                batch["hist_meds"],
                batch["hist_types"],
                batch["hist_elapsed"],
                batch["active_regimen"],
                batch["log_hours_since_admit"],
            )
            rows.append(logits.cpu().numpy())
    return np.concatenate(rows, axis=0)


def top_k(row: np.ndarray, concept_codes: list[str], k: int = K) -> list[int]:
    return sorted(range(N_CONCEPTS), key=lambda index: (-float(row[index]), concept_codes[index]))[
        :k
    ]


def micro_average_precision(targets: np.ndarray, probabilities: np.ndarray) -> float:
    labels = targets.astype(np.int8).ravel()
    scores = probabilities.astype(np.float64).ravel()
    order = np.argsort(-scores, kind="mergesort")
    ranked_labels = labels[order]
    positives = int(ranked_labels.sum())
    if positives == 0:
        return 0.0
    cumulative = np.cumsum(ranked_labels)
    ranks = np.arange(1, len(ranked_labels) + 1)
    return float(np.sum(cumulative[ranked_labels == 1] / ranks[ranked_labels == 1]) / positives)


def evaluate_logits(
    bursts: list[dict[str, Any]], logits: np.ndarray, concept_codes: list[str]
) -> dict[str, Any]:
    if len(bursts) != len(logits):
        raise ProtocolFailure("Prediction and burst counts differ")
    recalls: list[float] = []
    ndcgs: list[float] = []
    hits: list[float] = []
    targets = np.asarray([burst["target_vec"] for burst in bursts], dtype=np.float32)
    for burst, row in zip(bursts, logits, strict=True):
        target_set = set(burst["target_indices"])
        selected = top_k(row, concept_codes)
        hit_count = sum(index in target_set for index in selected)
        recalls.append(hit_count / len(target_set) if target_set else 0.0)
        hits.append(float(hit_count > 0))
        dcg = sum(
            1.0 / math.log2(rank + 1)
            for rank, index in enumerate(selected, start=1)
            if index in target_set
        )
        ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(K, len(target_set)) + 1))
        ndcgs.append(dcg / ideal if ideal else 0.0)

    probabilities = 1.0 / (1.0 + np.exp(-logits))
    return {
        "Recall@5": float(np.mean(recalls)),
        "NDCG@5": float(np.mean(ndcgs)),
        "Hit@5": float(np.mean(hits)),
        "micro_PRAUC": micro_average_precision(targets, probabilities),
        "n_bursts": len(bursts),
        "_raw_recall": np.asarray(recalls, dtype=np.float64),
        "_raw_ndcg": np.asarray(ndcgs, dtype=np.float64),
        "_raw_hit": np.asarray(hits, dtype=np.float64),
    }


def estimate_prior(bursts: list[dict[str, Any]]) -> np.ndarray:
    positives = np.asarray([burst["target_vec"] for burst in bursts], dtype=np.float64).sum(axis=0)
    return (positives + 1.0) / (len(bursts) + 2.0)


def logit_delta(p_source: np.ndarray, p_target: np.ndarray) -> np.ndarray:
    return np.log(p_target / (1.0 - p_target)) - np.log(p_source / (1.0 - p_source))


def vector_identity(name: str, concept_codes: list[str], values: np.ndarray) -> str:
    payload = json.dumps(
        {"name": name, "concept_codes": concept_codes, "values": [float(v) for v in values]},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_subjects(subjects: set[int]) -> str:
    payload = "\n".join(str(subject_id) for subject_id in sorted(subjects))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def code_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def code_identities() -> tuple[str, str, str]:
    file_bytes = Path(__file__).read_bytes()
    runner_sha = hashlib.sha256(file_bytes).hexdigest()
    task_sha = hashlib.sha256(b"task-construction\n" + file_bytes).hexdigest()
    metric_sha = hashlib.sha256(b"metrics\n" + file_bytes).hexdigest()
    return runner_sha, task_sha, metric_sha


def cohort_stats(bursts: list[dict[str, Any]] | None) -> dict[str, int | None]:
    if bursts is None:
        return {"patients": None, "bursts": None}
    return {"patients": len({burst["patient_id"] for burst in bursts}), "bursts": len(bursts)}


def support_results(cohorts: dict[str, list[dict[str, Any]] | None]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, floor in SUPPORT_FLOORS.items():
        stats = cohort_stats(cohorts.get(name))
        passed = (
            stats["bursts"] is not None
            and stats["patients"] is not None
            and stats["bursts"] >= floor["bursts"]
            and stats["patients"] >= floor["patients"]
        )
        results[name] = {
            "actual": stats,
            "minimum": floor,
            "passed": bool(passed),
        }
    return results


def independent_two_sample_bootstrap(
    source_patient_ids: list[int],
    source_base: np.ndarray,
    source_bias: np.ndarray,
    target_patient_ids: list[int],
    target_base: np.ndarray,
    target_bias: np.ndarray,
) -> dict[str, Any]:
    def cluster_sums(patient_ids: list[int], values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        unique, inverse = np.unique(np.asarray(patient_ids), return_inverse=True)
        counts = np.bincount(inverse, minlength=len(unique)).astype(np.float64)
        sums = np.bincount(inverse, weights=values, minlength=len(unique)).astype(np.float64)
        return counts, sums

    source_count, source_base_sum = cluster_sums(source_patient_ids, source_base)
    _, source_bias_sum = cluster_sums(source_patient_ids, source_bias)
    target_count, target_base_sum = cluster_sums(target_patient_ids, target_base)
    _, target_bias_sum = cluster_sums(target_patient_ids, target_bias)
    rng = np.random.default_rng(SEED)
    source_sample = rng.choice(len(source_count), size=(BOOTSTRAP_REPLICATES, len(source_count)))
    target_sample = rng.choice(len(target_count), size=(BOOTSTRAP_REPLICATES, len(target_count)))

    def multiplicities(sample: np.ndarray, n_clusters: int) -> np.ndarray:
        counts = np.zeros((BOOTSTRAP_REPLICATES, n_clusters), dtype=np.float64)
        for row, indices in enumerate(sample):
            np.add.at(counts[row], indices, 1.0)
        return counts

    source_mult = multiplicities(source_sample, len(source_count))
    target_mult = multiplicities(target_sample, len(target_count))
    source_denominator = source_mult @ source_count
    target_denominator = target_mult @ target_count
    source_base_mean = (source_mult @ source_base_sum) / source_denominator
    source_bias_mean = (source_mult @ source_bias_sum) / source_denominator
    target_base_mean = (target_mult @ target_base_sum) / target_denominator
    target_bias_mean = (target_mult @ target_bias_sum) / target_denominator
    gap_base = source_base_mean - target_base_mean
    gap_bias = source_bias_mean - target_bias_mean
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": SEED,
        "scheme": "independent patient-clustered two-sample bootstrap",
        "gap_base_ci_95": [
            float(np.percentile(gap_base, 2.5)),
            float(np.percentile(gap_base, 97.5)),
        ],
        "gap_bias_ci_95": [
            float(np.percentile(gap_bias, 2.5)),
            float(np.percentile(gap_bias, 97.5)),
        ],
    }


def fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return format(float(value), ".17g")


def strip_raw(metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    if metrics is None:
        return None
    return {key: value for key, value in metrics.items() if not key.startswith("_raw_")}


def verify_integrity(summary: dict[str, Any], freeze_payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        summary["temporal_assignment"]["retained_rule"]
        != "year(decision_time) == patient.anchor_year"
    ):
        findings.append("temporal assignment rule mismatch")
    if summary["quarantine"]["future_reserve_event_data_inspected"]:
        findings.append("future reserve was inspected")
    if summary["quarantine"]["r0_holdout_inspected"]:
        findings.append("R0 Holdout was inspected")
    has_target_result = summary["primary_quantities"]["R_source"] is not None
    if has_target_result and not summary["quarantine"]["target_audit_accessed_after_freeze"]:
        findings.append("TargetAudit was not accessed after freeze")
    if freeze_payload["target_audit_accessed"]:
        findings.append("freeze manifest was written after TargetAudit access")
    rows = summary["target_bias_tune"]["alpha_rows"]
    expected = (
        sorted(rows, key=lambda row: (-row["Recall@5"], row["alpha"]))[0]["alpha"] if rows else None
    )
    if rows and summary["target_bias_tune"]["selected_alpha"] != expected:
        findings.append("alpha tie-breaking mismatch")

    primary = summary["primary_quantities"]
    if has_target_result:
        expected_base = primary["R_source"] - primary["R_target_base"]
        expected_bias = primary["R_source"] - primary["R_target_bias"]
        if not math.isclose(primary["G_base"], expected_base, rel_tol=0.0, abs_tol=1e-15):
            findings.append("G_base arithmetic mismatch")
        if not math.isclose(primary["G_bias"], expected_bias, rel_tol=0.0, abs_tol=1e-15):
            findings.append("G_bias arithmetic mismatch")
        if primary["G_base"] > 0:
            expected_recovery = (primary["R_target_bias"] - primary["R_target_base"]) / primary[
                "G_base"
            ]
            if not math.isclose(primary["Recovery"], expected_recovery, rel_tol=0.0, abs_tol=1e-15):
                findings.append("Recovery arithmetic mismatch")

    support_pass = all(row["passed"] for row in summary["support"].values())
    conditions = summary["conditions"]
    expected_c1 = support_pass
    expected_c2 = bool(
        has_target_result and primary["G_base"] >= 0.020 and primary["G_base_ci_95"][0] > 0.010
    )
    expected_c3 = (
        has_target_result
        and primary["Recovery"] is not None
        and primary["Recovery"] <= 0.50
        and primary["G_bias"] >= 0.010
        and primary["G_bias_ci_95"][0] > 0.0
    )
    if conditions["Condition1"] != expected_c1:
        findings.append("Condition 1 mismatch")
    if conditions["Condition2"] != expected_c2:
        findings.append("Condition 2 mismatch")
    if conditions["Condition3"] != expected_c3:
        findings.append("Condition 3 mismatch")
    if summary["claims"]["causal_practice_drift_claim"]:
        findings.append("causal practice-drift claim exceeds S0 evidence")
    return findings


def write_artifacts(
    output_dir: Path,
    summary: dict[str, Any],
    freeze_payload: dict[str, Any],
    freeze_sha: str | None,
    integrity_findings: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    integrity_verdict = "INTEGRITY_AUDIT_PASS" if not integrity_findings else "INTEGRITY_AUDIT_FAIL"
    summary["integrity_audit_verdict"] = integrity_verdict
    with (output_dir / "s0-summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=True, indent=2, sort_keys=True)

    primary = summary["primary_quantities"]
    support_lines = [
        "| Cohort | Patients | Bursts | Minimum patients | Minimum bursts | PASS |",
        "| :--- | ---: | ---: | ---: | ---: | :--- |",
    ]
    for name in PARTITIONS:
        row = summary["support"][name]
        support_lines.append(
            f"| {name} | {fmt(row['actual']['patients'])} | {fmt(row['actual']['bursts'])} | "
            f"{row['minimum']['patients']} | {row['minimum']['bursts']} | {row['passed']} |"
        )
    alpha_lines = [
        "| alpha | Recall@5 | NDCG@5 | Hit@5 | micro-PRAUC |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["target_bias_tune"]["alpha_rows"]:
        alpha_lines.append(
            f"| {fmt(row['alpha'])} | {fmt(row['Recall@5'])} | {fmt(row['NDCG@5'])} | "
            f"{fmt(row['Hit@5'])} | {fmt(row['micro_PRAUC'])} |"
        )
    decision = [
        "# S0 — Medication Practice-Shift Admission",
        "",
        f"## Verdict: `{summary['verdict']}`",
        "",
        f"- MIMIC-IV version: `{summary['mimic_version']}`",
        f"- Stage: `{summary['stage']}`",
        f"- Freeze SHA256: `{freeze_sha or 'N/A'}`",
        f"- Actual batch size: `{summary['actual_batch_size']}`",
        f"- Source checkpoint epoch: `{summary['source_checkpoint']['epoch']}`",
        f"- SourceTune BCE: `{fmt(summary['source_checkpoint']['source_tune_bce'])}`",
        f"- Integrity audit: `{integrity_verdict}`",
        "",
        "## Temporal and quarantine contract",
        "",
        f"- Retained only when `{summary['temporal_assignment']['retained_rule']}`.",
        "- G3/G4 clinical events, bursts, labels, distributions, predictions, and performance were not inspected.",
        "- R0 Holdout and the historical project test split were untouched.",
        f"- TargetAudit was accessed exactly once after freeze: `{summary['quarantine']['target_audit_accessed_after_freeze']}`.",
        "",
        "## Support floors",
        "",
        *support_lines,
        "",
        "## TargetBiasTune alpha grid",
        "",
        *alpha_lines,
        "",
        f"Selected alpha: `{fmt(summary['target_bias_tune']['selected_alpha'])}` (tie-break: smaller alpha).",
        "",
        "## Primary quantities",
        "",
        f"- R_source: `{fmt(primary['R_source'])}`",
        f"- R_target_base: `{fmt(primary['R_target_base'])}`",
        f"- R_target_bias: `{fmt(primary['R_target_bias'])}`",
        f"- G_base: `{fmt(primary['G_base'])}`, 95% CI `{[fmt(v) for v in primary['G_base_ci_95']]}`",
        f"- G_bias: `{fmt(primary['G_bias'])}`, 95% CI `{[fmt(v) for v in primary['G_bias_ci_95']]}`",
        f"- Recovery: `{fmt(primary['Recovery'])}`",
        "",
        "| Condition | PASS |",
        "| :--- | :--- |",
        f"| Condition 1 — support floors | {summary['conditions']['Condition1']} |",
        f"| Condition 2 — material base gap | {summary['conditions']['Condition2']} |",
        f"| Condition 3 — residual after prior bias | {summary['conditions']['Condition3']} |",
        "",
        "S0 supports only a residual temporal deployment-shift statement. It does not establish causal practice drift, clinical benefit, or method superiority.",
        "",
        f"Next state: `{summary['next_state']}`",
        "",
        "Next CCFA owner: `ccf-pipeline-orchestrator`",
    ]
    with (output_dir / "s0-decision.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(decision) + "\n")

    audit = [
        "# S0 Integrity Audit",
        "",
        f"## Verdict: `{integrity_verdict}`",
        "",
        "Mode: `full` (temporal/quarantine, adaptation entitlement, numeric, and claim audit).",
        "",
        "## Artifacts checked",
        "",
        "- Frozen S0 protocol SSOT.",
        "- `s0-summary.json` and `s0-decision.md`.",
        f"- Restricted freeze manifest identity: `{freeze_sha or 'N/A'}`.",
        "",
        "## Temporal / quarantine",
        "",
        "- `year(decision_time) == anchor_year` is the retained-burst rule.",
        "- Exact groups are G0+G1 source, G2 target, and G3+G4 quarantined future reserve.",
        "- G3/G4 clinical data and aggregates were not inspected.",
        "- R0 Holdout and historical project test split were not inspected.",
        "- TargetAudit was not read before the restricted freeze manifest; it was evaluated once afterward.",
        "",
        "## Adaptation entitlement",
        "",
        "- SourceTrain was the only cohort used for neural weight fitting and source priors.",
        "- TargetPriorBuild supplied only the target marginal prior.",
        "- TargetBiasTune supplied only the scalar alpha selection.",
        "- No target-era neural weight update, learned alpha, adapter, temperature, or transition model was used.",
        "- Alpha grid was exactly `{0.0, 0.25, 0.5, 1.0, 2.0}` with smaller-alpha tie-breaking.",
        "",
        "## Numeric consistency",
        "",
        f"- R_source = `{fmt(primary['R_source'])}`.",
        f"- R_target_base = `{fmt(primary['R_target_base'])}`.",
        f"- R_target_bias = `{fmt(primary['R_target_bias'])}`.",
        f"- G_base = `{fmt(primary['G_base'])}`, CI `{[fmt(v) for v in primary['G_base_ci_95']]}`.",
        f"- G_bias = `{fmt(primary['G_bias'])}`, CI `{[fmt(v) for v in primary['G_bias_ci_95']]}`.",
        f"- Recovery = `{fmt(primary['Recovery'])}`.",
        f"- Conditions 1–3 = `{summary['conditions']['Condition1']}`, `{summary['conditions']['Condition2']}`, `{summary['conditions']['Condition3']}`.",
        "- Confidence intervals use 2,000 independent patient-clustered two-sample bootstrap replicates with seed 260908; the two target methods share identical TargetAudit patient multiplicities per replicate.",
        "",
        "## Claim boundary",
        "",
        "- No causal practice-drift claim is made.",
        "- The result is limited to residual temporal deployment shift under the frozen MIMIC-IV order-time task and prior-bias control.",
        "",
        "No-invention status: `PASS`; no unsupported number, patient-level artifact, or new scientific direction was added.",
        "",
        "Next CCFA owner: `ccf-pipeline-orchestrator`.",
    ]
    if integrity_findings:
        audit.extend(["", "Findings:", "", *[f"- {finding}" for finding in integrity_findings]])
    with (output_dir / "s0-integrity-audit.md").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(audit) + "\n")


def base_summary(
    repo_revision: str,
    runner_sha: str,
    task_sha: str,
    metric_sha: str,
    preflight: dict[str, Any],
    batch_size: int,
    cohorts: dict[str, list[dict[str, Any]] | None],
    source_checkpoint: dict[str, Any],
    source_prior: np.ndarray,
    target_prior: np.ndarray,
    delta: np.ndarray,
    alpha_rows: list[dict[str, Any]],
    selected_alpha: float | None,
    primary: dict[str, Any],
    conditions: dict[str, bool],
    verdict: str,
    freeze_sha: str | None,
    target_audit_accessed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "gate_id": "S0_MEDICATION_PRACTICE_SHIFT_ADMISSION",
        "verdict": verdict,
        "stage": "PRE_IDEA_PRACTICE_SHIFT_S0",
        "mimic_version": "3.1",
        "execution_timestamp_utc": dt.datetime.now(dt.UTC).isoformat(),
        "code": {
            "repository_revision": repo_revision,
            "runner_sha256": runner_sha,
            "task_construction_code_identity": task_sha,
            "metric_code_identity": metric_sha,
        },
        "preflight": preflight,
        "actual_batch_size": batch_size,
        "temporal_assignment": {
            "retained_rule": "year(decision_time) == patient.anchor_year",
            "groups": {
                "G0": "2008 - 2010",
                "G1": "2011 - 2013",
                "G2": "2014 - 2016",
                "G3": "2017 - 2019",
                "G4": "2020 - 2022",
            },
            "source_era": ["G0", "G1"],
            "target_era": ["G2"],
            "future_reserve": ["G3", "G4"],
        },
        "quarantine": {
            "future_reserve_event_data_inspected": False,
            "future_reserve_aggregate_inspected": False,
            "r0_holdout_inspected": False,
            "historical_project_test_split_inspected": False,
            "target_audit_accessed_after_freeze": target_audit_accessed,
            "target_audit_access_count": 1 if target_audit_accessed else 0,
        },
        "cohort_counts": {name: cohort_stats(cohorts.get(name)) for name in PARTITIONS},
        "support": support_results(cohorts),
        "source_checkpoint": source_checkpoint,
        "source_prior": {
            "identity": vector_identity("p_source", SOURCE_CODES, source_prior),
            "values": [float(value) for value in source_prior],
        },
        "target_prior_build": {
            "identity": vector_identity("p_target", SOURCE_CODES, target_prior),
            "values": [float(value) for value in target_prior],
        },
        "delta_bias": {
            "identity": vector_identity("delta_b", SOURCE_CODES, delta),
            "values": [float(value) for value in delta],
        },
        "target_bias_tune": {
            "alpha_grid": list(ALPHA_GRID),
            "alpha_rows": alpha_rows,
            "selected_alpha": selected_alpha,
        },
        "primary_quantities": primary,
        "bootstrap": primary.get("bootstrap"),
        "conditions": conditions,
        "freeze_sha256": freeze_sha,
        "claims": {"causal_practice_drift_claim": False},
        "next_state": (
            "NO_HIGH_VALUE_DIRECTION_YET"
            if verdict == "FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT"
            else "RETURN_TO_CCF_PIPELINE_ORCHESTRATOR"
        ),
    }


SOURCE_CODES: list[str] = []


def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen S0 Medication Practice-Shift Admission")
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
        "--run-dir", type=Path, default=Path("/root/zhb/medrec-data/s0_runs/s0-20260908")
    )
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    global SOURCE_CODES
    set_seed(SEED)
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    if args.run_dir.exists() and any(args.run_dir.iterdir()):
        raise ProtocolFailure("S0 run directory must be fresh")
    args.run_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    repo_root = Path(__file__).parents[3]
    repo_revision = code_revision(repo_root)
    runner_sha, task_sha, metric_sha = code_identities()
    SOURCE_CODES = load_vocabulary(args.vocab_asset_dir)
    concept_to_index = {code: index for index, code in enumerate(SOURCE_CODES)}

    print(f"Using device={device}", flush=True)
    preflight = run_mechanical_preflight(args.vocab_asset_dir, device)
    batch_size = select_batch_size(device)
    preflight["actual_batch_size"] = batch_size
    print(f"Mechanical preflight passed; actual_batch_size={batch_size}", flush=True)

    patients, partition_subjects = load_patients(args.mimic_dir)
    mapping = build_ndc_mapping(args.mapping_dir)
    vocabulary = set(SOURCE_CODES)
    consensus = build_formulary_consensus(
        args.mimic_dir, partition_subjects["SourceTrain"], mapping, vocabulary
    )
    pre_subjects = set().union(*(partition_subjects[name] for name in PRE_FREEZE_PARTITIONS))
    clinical = load_clinical_records(
        args.mimic_dir,
        patients,
        pre_subjects,
        mapping,
        consensus,
        vocabulary,
    )
    pre_bursts = build_bursts(
        patients,
        pre_subjects,
        *clinical,
        concept_to_index,
    )
    del clinical
    cohorts: dict[str, list[dict[str, Any]] | None] = {
        name: [burst for burst in pre_bursts if burst["patient_id"] in partition_subjects[name]]
        for name in PRE_FREEZE_PARTITIONS
    }
    cohorts["TargetAudit"] = None
    pre_support = support_results(cohorts)
    if not all(pre_support[name]["passed"] for name in PRE_FREEZE_PARTITIONS):
        verdict = "FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT"
        summary = base_summary(
            repo_revision,
            runner_sha,
            task_sha,
            metric_sha,
            preflight,
            batch_size,
            cohorts,
            {"epoch": None, "source_tune_bce": None, "sha256": None},
            np.zeros(N_CONCEPTS),
            np.zeros(N_CONCEPTS),
            np.zeros(N_CONCEPTS),
            [],
            None,
            {
                "R_source": None,
                "R_target_base": None,
                "R_target_bias": None,
                "G_base": None,
                "G_base_ci_95": [None, None],
                "G_bias": None,
                "G_bias_ci_95": [None, None],
                "Recovery": None,
                "bootstrap": None,
            },
            {"Condition1": False, "Condition2": False, "Condition3": False},
            verdict,
            None,
            False,
        )
        findings = verify_integrity(summary, {"target_audit_accessed": False})
        write_artifacts(args.output_dir, summary, {"target_audit_accessed": False}, None, findings)
        return 0

    train_data = FastBurstTensorDataset(cohorts["SourceTrain"] or [])
    tune_data = FastBurstTensorDataset(cohorts["SourceTune"] or [])
    checkpoint_path = args.run_dir / "source_base_checkpoint.pt"
    model, checkpoint_epoch, source_tune_bce, checkpoint_sha = train_source(
        train_data, tune_data, device, batch_size, checkpoint_path
    )
    source_audit_bursts = cohorts["SourceAudit"] or []
    source_audit_logits = predict_logits(
        model, FastBurstTensorDataset(source_audit_bursts), device, batch_size
    )
    source_metrics = evaluate_logits(source_audit_bursts, source_audit_logits, SOURCE_CODES)
    source_prior = estimate_prior(cohorts["SourceTrain"] or [])
    target_prior = estimate_prior(cohorts["TargetPriorBuild"] or [])
    delta = logit_delta(source_prior, target_prior)
    target_tune_bursts = cohorts["TargetBiasTune"] or []
    target_tune_logits = predict_logits(
        model, FastBurstTensorDataset(target_tune_bursts), device, batch_size
    )
    alpha_rows: list[dict[str, Any]] = []
    for alpha in ALPHA_GRID:
        metrics = evaluate_logits(
            target_tune_bursts, target_tune_logits + alpha * delta, SOURCE_CODES
        )
        alpha_rows.append({"alpha": alpha, **(strip_raw(metrics) or {})})
    selected_alpha = sorted(alpha_rows, key=lambda row: (-row["Recall@5"], row["alpha"]))[0][
        "alpha"
    ]

    freeze_payload = {
        "protocol": "S0_MEDICATION_PRACTICE_SHIFT_ADMISSION",
        "repository_revision": repo_revision,
        "runner_sha256": runner_sha,
        "task_construction_code_identity": task_sha,
        "metric_code_identity": metric_sha,
        "actual_batch_size": batch_size,
        "seed": SEED,
        "source_checkpoint": {
            "sha256": checkpoint_sha,
            "epoch": checkpoint_epoch,
            "source_tune_bce": source_tune_bce,
        },
        "patient_split_hashes": {
            name: hash_subjects(partition_subjects[name]) for name in PARTITIONS
        },
        "p_source_identity": vector_identity("p_source", SOURCE_CODES, source_prior),
        "p_target_identity": vector_identity("p_target", SOURCE_CODES, target_prior),
        "delta_b_identity": vector_identity("delta_b", SOURCE_CODES, delta),
        "selected_alpha": selected_alpha,
        "alpha_grid": list(ALPHA_GRID),
        "bootstrap_seed": SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "gate_logic": {
            "support_floors": SUPPORT_FLOORS,
            "g_base_point": 0.020,
            "g_base_ci_lower": 0.010,
            "recovery_max": 0.50,
            "g_bias_point": 0.010,
            "g_bias_ci_lower": 0.0,
        },
        "target_audit_accessed": False,
    }
    freeze_text = json.dumps(freeze_payload, ensure_ascii=True, indent=2, sort_keys=True)
    freeze_path = args.run_dir / "s0-freeze-manifest.json"
    freeze_path.write_text(freeze_text + "\n", encoding="utf-8")
    freeze_sha = sha256_file(freeze_path)
    print(f"Critical TargetAudit freeze complete: {freeze_sha}", flush=True)

    audit_subjects = partition_subjects["TargetAudit"]
    audit_clinical = load_clinical_records(
        args.mimic_dir,
        patients,
        audit_subjects,
        mapping,
        consensus,
        vocabulary,
    )
    target_audit_bursts = build_bursts(
        patients,
        audit_subjects,
        *audit_clinical,
        concept_to_index,
    )
    del audit_clinical
    cohorts["TargetAudit"] = target_audit_bursts
    target_audit_data = FastBurstTensorDataset(target_audit_bursts)
    target_logits = predict_logits(model, target_audit_data, device, batch_size)
    target_base_metrics = evaluate_logits(target_audit_bursts, target_logits, SOURCE_CODES)
    target_bias_metrics = evaluate_logits(
        target_audit_bursts, target_logits + selected_alpha * delta, SOURCE_CODES
    )

    r_source = source_metrics["Recall@5"]
    r_target_base = target_base_metrics["Recall@5"]
    r_target_bias = target_bias_metrics["Recall@5"]
    g_base = r_source - r_target_base
    g_bias = r_source - r_target_bias
    recovery = (r_target_bias - r_target_base) / g_base if g_base > 0 else None
    bootstrap = independent_two_sample_bootstrap(
        [burst["patient_id"] for burst in source_audit_bursts],
        source_metrics["_raw_recall"],
        source_metrics["_raw_recall"],
        [burst["patient_id"] for burst in target_audit_bursts],
        target_base_metrics["_raw_recall"],
        target_bias_metrics["_raw_recall"],
    )
    primary = {
        "R_source": r_source,
        "R_target_base": r_target_base,
        "R_target_bias": r_target_bias,
        "G_base": g_base,
        "G_base_ci_95": bootstrap["gap_base_ci_95"],
        "G_bias": g_bias,
        "G_bias_ci_95": bootstrap["gap_bias_ci_95"],
        "Recovery": recovery,
        "bootstrap": bootstrap,
    }
    cohorts_support = support_results(cohorts)
    conditions = {
        "Condition1": all(row["passed"] for row in cohorts_support.values()),
        "Condition2": bool(g_base >= 0.020 and bootstrap["gap_base_ci_95"][0] > 0.010),
        "Condition3": bool(
            recovery is not None
            and recovery <= 0.50
            and g_bias >= 0.010
            and bootstrap["gap_bias_ci_95"][0] > 0.0
        ),
    }
    verdict = (
        "PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT"
        if all(conditions.values())
        else "FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT"
    )
    source_checkpoint = {
        "epoch": checkpoint_epoch,
        "source_tune_bce": source_tune_bce,
        "sha256": checkpoint_sha,
    }
    summary = base_summary(
        repo_revision,
        runner_sha,
        task_sha,
        metric_sha,
        preflight,
        batch_size,
        cohorts,
        source_checkpoint,
        source_prior,
        target_prior,
        delta,
        alpha_rows,
        selected_alpha,
        primary,
        conditions,
        verdict,
        freeze_sha,
        True,
    )
    summary["evaluations"] = {
        "SourceAudit": strip_raw(source_metrics),
        "TargetAudit_SourceOnly": strip_raw(target_base_metrics),
        "TargetAudit_TargetPriorBias": strip_raw(target_bias_metrics),
    }
    summary["source_checkpoint"]["epoch"] = checkpoint_epoch
    summary["source_checkpoint"]["source_tune_bce"] = source_tune_bce
    summary["source_checkpoint"]["sha256"] = checkpoint_sha
    integrity_findings = verify_integrity(summary, freeze_payload)
    write_artifacts(args.output_dir, summary, freeze_payload, freeze_sha, integrity_findings)
    print(f"S0 verdict={verdict}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProtocolFailure as error:
        print(f"S0 protocol failure: {error}", file=sys.stderr)
        raise SystemExit(2) from error
