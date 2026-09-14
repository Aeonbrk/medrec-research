#!/usr/bin/env python3
"""Bounded RxUnitSet target-supportability analysis.

This script reads only the authorized MIMIC-III PRESCRIPTIONS table and the
canonical SafeDrug c721 data product needed to identify Train and Gate01-Dev
admission identities.  It does not train a model and never writes row-level
prescription, patient, or split identifiers to the aggregate result.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import dill
import pandas as pd

N_CONCEPTS = 131
EXPECTED_CANONICAL_PATIENTS = 6_350
EXPECTED_CANONICAL_ADMISSIONS = 15_032
GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_CHUNK_SIZE = 250_000
DEFAULT_SOURCE_REVISION = ""
ROUTE_MISSING = "<MISSING_ROUTE>"
DOSE_MISSING = "<MISSING_DOSE>"
DOSE_UNIT_MISSING = "<MISSING_UNIT>"

PRESCRIPTION_COLUMNS = (
    "ROW_ID",
    "SUBJECT_ID",
    "HADM_ID",
    "STARTDATE",
    "ENDDATE",
    "DRUG",
    "DRUG_NAME_GENERIC",
    "FORMULARY_DRUG_CD",
    "GSN",
    "NDC",
    "PROD_STRENGTH",
    "DOSE_VAL_RX",
    "DOSE_UNIT_RX",
    "ROUTE",
)


class SupportabilityError(RuntimeError):
    """Raised when an input or semantic contract cannot be established."""


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text in {"", "nan", "NaN", "<NA>", "None", "NaT"}:
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


def table_path(root: Path) -> Path:
    for name in ("PRESCRIPTIONS.csv.gz", "PRESCRIPTIONS.csv"):
        candidate = root / name
        if candidate.is_file():
            return candidate
    raise SupportabilityError(f"missing MIMIC-III prescriptions table under {root}")


def gate01_dev(patient_index: int) -> bool:
    digest = hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_index}".encode()).digest()[:8]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


@dataclass(frozen=True)
class CanonicalScope:
    train_subjects: frozenset[int]
    dev_subjects: frozenset[int]
    train_pairs: frozenset[tuple[int, int]]
    dev_pairs: frozenset[tuple[int, int]]

    @property
    def selected_subjects(self) -> frozenset[int]:
        return self.train_subjects | self.dev_subjects

    @property
    def selected_pairs(self) -> frozenset[tuple[int, int]]:
        return self.train_pairs | self.dev_pairs


def load_canonical_scope(path: Path) -> CanonicalScope:
    """Derive the existing Train/Gate01-Dev identity split from data_final."""

    if not path.is_file():
        raise SupportabilityError(f"canonical data product not found: {path}")
    with path.open("rb") as handle:
        data = dill.load(handle)
    if not isinstance(data, pd.DataFrame) or not {"SUBJECT_ID", "HADM_ID"}.issubset(data.columns):
        raise SupportabilityError("canonical data_final must contain SUBJECT_ID and HADM_ID")

    if len(data) != EXPECTED_CANONICAL_ADMISSIONS:
        raise SupportabilityError("canonical data_final admission count drifted")
    ordered_subjects = [as_int(value) for value in data["SUBJECT_ID"].drop_duplicates()]
    if (
        any(value is None for value in ordered_subjects)
        or len(ordered_subjects) != EXPECTED_CANONICAL_PATIENTS
    ):
        raise SupportabilityError("canonical subject ordering is malformed")
    subjects = [int(value) for value in ordered_subjects]
    split_point = int(len(subjects) * 2 / 3)
    train_subjects = frozenset(subjects[:split_point])
    dev_subjects = frozenset(
        subject
        for index, subject in enumerate(subjects[split_point:], split_point)
        if gate01_dev(index)
    )

    train_pairs: set[tuple[int, int]] = set()
    dev_pairs: set[tuple[int, int]] = set()
    for row in data[["SUBJECT_ID", "HADM_ID"]].itertuples(index=False):
        subject = as_int(row.SUBJECT_ID)
        hadm = as_int(row.HADM_ID)
        if subject is None or hadm is None:
            continue
        pair = (subject, hadm)
        if subject in train_subjects:
            train_pairs.add(pair)
        elif subject in dev_subjects:
            dev_pairs.add(pair)
    if not train_pairs or not dev_pairs:
        raise SupportabilityError("canonical Train/Gate01-Dev admission identity is empty")
    return CanonicalScope(
        train_subjects, dev_subjects, frozenset(train_pairs), frozenset(dev_pairs)
    )


def normalize_ndc(value: Any) -> str:
    text = clean_text(value)
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"[^0-9]", "", text)
    if not digits or set(digits) == {"0"}:
        return ""
    return digits


def ndc_keys(value: Any) -> tuple[str, ...]:
    normalized = normalize_ndc(value)
    if not normalized:
        return ()
    return (normalized, normalized.zfill(11))


def rxnorm_key(value: Any) -> str:
    text = clean_text(value)
    digits = re.sub(r"[^0-9]", "", text)
    return digits


def build_ndc_to_atc4(mapping_dir: Path) -> tuple[dict[str, str], int]:
    """Reuse SafeDrug's NDC -> RxNorm -> ATC4 mapping lineage."""

    atc_path = mapping_dir / "ndc2atc_level4.csv"
    rx_path = mapping_dir / "ndc2rxnorm_mapping.txt"
    if not atc_path.is_file() or not rx_path.is_file():
        raise SupportabilityError("required NDC/RxNorm mapping asset is missing")

    rxnorm_to_atc: dict[str, str] = {}
    frame = pd.read_csv(atc_path, dtype="string", usecols=["RXCUI", "ATC5"])
    for row in frame.itertuples(index=False):
        rxnorm = rxnorm_key(row.RXCUI)
        atc = clean_text(row.ATC5).upper()[:4]
        if rxnorm and len(atc) == 4:
            # SafeDrug drops duplicate RXCUI rows and keeps the first table row.
            rxnorm_to_atc.setdefault(rxnorm, atc)

    try:
        raw_mapping = ast.literal_eval(rx_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as error:
        raise SupportabilityError(
            "ndc2rxnorm_mapping.txt is not a valid literal mapping"
        ) from error
    if not isinstance(raw_mapping, dict):
        raise SupportabilityError("ndc2rxnorm_mapping.txt must contain a mapping")

    candidates: dict[str, set[str]] = collections.defaultdict(set)
    for ndc, rxnorm in raw_mapping.items():
        atc = rxnorm_to_atc.get(rxnorm_key(rxnorm))
        if atc:
            for key in ndc_keys(ndc):
                candidates[key].add(atc)
    mapping = {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}
    ambiguous = sum(1 for values in candidates.values() if len(values) > 1)
    return mapping, ambiguous


def load_vocabulary(path: Path) -> tuple[str, ...]:
    if not path.is_file():
        raise SupportabilityError(f"canonical vocabulary not found: {path}")
    with path.open("rb") as handle:
        vocabulary = dill.load(handle)
    try:
        idx2word = vocabulary["med_voc"].idx2word
        values = tuple(str(idx2word[index]) for index in range(N_CONCEPTS))
    except (KeyError, IndexError, TypeError) as error:
        raise SupportabilityError(
            "canonical vocabulary has no ordered 131-medication map"
        ) from error
    if len(set(values)) != N_CONCEPTS or any(len(value) != 4 for value in values):
        raise SupportabilityError("canonical vocabulary is not 131 unique ATC4 concepts")
    return values


def normalize_route(value: Any) -> str:
    text = clean_text(value).upper()
    return re.sub(r"\s+", " ", text) if text else ROUTE_MISSING


_NUMERIC = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_RANGE = re.compile(rf"^{_NUMERIC}\s*(?:-|–|—|to)\s*{_NUMERIC}$", re.IGNORECASE)
_SINGLE = re.compile(rf"^{_NUMERIC}$", re.IGNORECASE)


def canonical_number(text: str) -> str:
    try:
        value = Decimal(text)
    except InvalidOperation:
        return text
    if not value.is_finite():
        return text
    if value == 0:
        return "0"
    normalized = format(value.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def classify_dose(value: Any, unit: Any) -> tuple[str, str, bool]:
    raw = clean_text(value)
    normalized_unit = re.sub(r"\s+", " ", clean_text(unit).upper()) or DOSE_UNIT_MISSING
    if not raw:
        return "missing", DOSE_MISSING, False
    if _SINGLE.fullmatch(raw):
        token = f"{canonical_number(raw)}|{normalized_unit}"
        return "single_numeric", token, normalized_unit != DOSE_UNIT_MISSING
    if _RANGE.fullmatch(raw):
        compact_range = re.sub(r"\s+", "", raw.upper())
        return "numeric_range", f"RANGE:{compact_range}|{normalized_unit}", False
    if re.search(r"[A-Za-z]", raw):
        return "textual", f"TEXT:{raw.upper()}|{normalized_unit}", False
    return "otherwise_unparsable", f"UNPARSEABLE:{raw.upper()}|{normalized_unit}", False


def parse_timestamp(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed.value // 1_000_000_000)


@dataclass
class PairAccumulator:
    split: str
    row_count: int = 0
    route_counts: collections.Counter[str] = field(default_factory=collections.Counter)
    dose_token_counts: collections.Counter[str] = field(default_factory=collections.Counter)
    route_classes: set[str] = field(default_factory=set)
    dose_tokens: set[str] = field(default_factory=set)
    dose_kinds: set[str] = field(default_factory=set)
    complete_configs: set[tuple[str, str]] = field(default_factory=set)
    configs: set[tuple[str, str]] = field(default_factory=set)
    signatures: collections.Counter[tuple[tuple[str, str], int | None, int | None]] = field(
        default_factory=collections.Counter
    )
    events: list[tuple[int, int | None, tuple[str, str]]] = field(default_factory=list)


@dataclass
class ScopeAccumulator:
    split: str
    raw_rows: int = 0
    valid_ndc_rows: int = 0
    mapped_any_rows: int = 0
    canonical_rows: int = 0
    outside_rows: int = 0
    unmapped_rows: int = 0
    med_rows: collections.Counter[str] = field(default_factory=collections.Counter)
    med_patients: dict[str, set[int]] = field(default_factory=lambda: collections.defaultdict(set))
    med_route_rows: collections.Counter[str] = field(default_factory=collections.Counter)
    med_dose_rows: collections.Counter[str] = field(default_factory=collections.Counter)
    route_rows: collections.Counter[str] = field(default_factory=collections.Counter)
    dose_kinds: collections.Counter[str] = field(default_factory=collections.Counter)
    dose_pairs: collections.Counter[str] = field(default_factory=collections.Counter)
    prod_strength_rows: int = 0
    pairs: set[tuple[int, int, str]] = field(default_factory=set)


def _split_for_pair(pair: tuple[int, int], scope: CanonicalScope) -> str | None:
    if pair in scope.train_pairs:
        return "Train"
    if pair in scope.dev_pairs:
        return "Gate01-Dev"
    return None


def _selected_frame(chunk: pd.DataFrame, scope: CanonicalScope) -> pd.DataFrame:
    if chunk.empty:
        return chunk
    selected = chunk.loc[
        chunk["SUBJECT_ID"].isin({str(value) for value in scope.selected_subjects})
    ].copy()
    if selected.empty:
        return selected
    pair_keys = selected["SUBJECT_ID"].astype("string") + "|" + selected["HADM_ID"].astype("string")
    allowed_keys = {f"{subject}|{hadm}" for subject, hadm in scope.selected_pairs}
    return selected.loc[pair_keys.isin(allowed_keys)]


def _new_scope_accumulator(split: str) -> ScopeAccumulator:
    return ScopeAccumulator(split=split)


def analyze_rows(
    prescriptions: Path,
    scope: CanonicalScope,
    ndc_to_atc: dict[str, str],
    vocabulary: tuple[str, ...],
    chunk_size: int,
) -> tuple[
    dict[str, ScopeAccumulator], dict[tuple[int, int, str], PairAccumulator], dict[str, Any]
]:
    vocab_set = set(vocabulary)
    accumulators = {name: _new_scope_accumulator(name) for name in ("Train", "Gate01-Dev")}
    pair_stats: dict[tuple[int, int, str], PairAccumulator] = {}
    total = collections.Counter()
    raw_route_strings: collections.Counter[str] = collections.Counter()
    normalized_route_classes: collections.Counter[str] = collections.Counter()
    dose_kind_counts: collections.Counter[str] = collections.Counter()
    dose_pair_counts: collections.Counter[str] = collections.Counter()
    prod_strength_rows = 0

    dtype = {column: "string" for column in PRESCRIPTION_COLUMNS}
    for chunk in pd.read_csv(
        prescriptions,
        usecols=list(PRESCRIPTION_COLUMNS),
        dtype=dtype,
        compression="infer",
        chunksize=chunk_size,
        low_memory=False,
    ):
        selected = _selected_frame(chunk, scope)
        if selected.empty:
            continue
        total["raw_rows"] += len(selected)
        normalized_ndc = selected["NDC"].map(normalize_ndc)
        atc_values = normalized_ndc.map(ndc_to_atc)
        total["valid_ndc_rows"] += int((normalized_ndc != "").sum())
        total["mapped_any_rows"] += int(atc_values.notna().sum())
        canonical_mask = atc_values.isin(vocab_set)
        total["canonical_rows"] += int(canonical_mask.sum())
        total["outside_rows"] += int((atc_values.notna() & ~canonical_mask).sum())
        total["unmapped_rows"] += int(atc_values.isna().sum())

        for row_index in selected.index[canonical_mask]:
            row = selected.loc[row_index]
            subject = as_int(row["SUBJECT_ID"])
            hadm = as_int(row["HADM_ID"])
            med = str(atc_values.loc[row_index])
            if subject is None or hadm is None:
                continue
            split = _split_for_pair((subject, hadm), scope)
            if split is None:
                raise SupportabilityError("selected prescription row is outside Train/Gate01-Dev")
            acc = accumulators[split]
            route_raw = clean_text(row["ROUTE"])
            route = normalize_route(row["ROUTE"])
            dose_kind, dose_token, dose_usable = classify_dose(
                row["DOSE_VAL_RX"], row["DOSE_UNIT_RX"]
            )
            start = parse_timestamp(row["STARTDATE"])
            end = parse_timestamp(row["ENDDATE"])
            config = (dose_token, route)
            pair = (subject, hadm, med)
            state = pair_stats.setdefault(pair, PairAccumulator(split=split))
            state.row_count += 1
            state.route_counts[route] += 1
            state.dose_token_counts[dose_token] += 1
            state.route_classes.add(route)
            state.dose_tokens.add(dose_token)
            state.dose_kinds.add(dose_kind)
            state.configs.add(config)
            if dose_usable and route != ROUTE_MISSING:
                state.complete_configs.add(config)
            state.signatures[(config, start, end)] += 1
            if start is not None:
                state.events.append((start, end, config))

            acc.canonical_rows += 1
            acc.med_rows[med] += 1
            acc.med_patients[med].add(subject)
            acc.route_rows[route] += 1
            acc.dose_kinds[dose_kind] += 1
            if route != ROUTE_MISSING:
                acc.med_route_rows[med] += 1
            if dose_usable:
                acc.med_dose_rows[med] += 1
                acc.dose_pairs[f"{med}|{dose_token}"] += 1
                dose_pair_counts[f"{med}|{dose_token}"] += 1
            if clean_text(row["PROD_STRENGTH"]):
                acc.prod_strength_rows += 1
                prod_strength_rows += 1
            acc.pairs.add(pair)
            raw_route_strings[route_raw or ROUTE_MISSING] += 1
            normalized_route_classes[route] += 1
            dose_kind_counts[dose_kind] += 1

        for split, acc in accumulators.items():
            # Raw/mapping totals are split by the same admission identity.
            # Recounting from the selected frame avoids retaining row IDs.
            split_subjects = scope.train_subjects if split == "Train" else scope.dev_subjects
            split_mask = selected["SUBJECT_ID"].map(as_int).isin(split_subjects)
            if bool(split_mask.any()):
                split_atc = atc_values.loc[split_mask]
                split_ndc = normalized_ndc.loc[split_mask]
                split_canonical = split_atc.isin(vocab_set)
                acc.raw_rows += int(split_mask.sum())
                acc.valid_ndc_rows += int((split_ndc != "").sum())
                acc.mapped_any_rows += int(split_atc.notna().sum())
                acc.outside_rows += int((split_atc.notna() & ~split_canonical).sum())
                acc.unmapped_rows += int(split_atc.isna().sum())
    # The loop above intentionally keeps pair-level canonical rows authoritative.
    # Replace split row counters with exact mapped totals from pair states below.
    for split, acc in accumulators.items():
        split_pairs = [state for state in pair_stats.values() if state.split == split]
        acc.canonical_rows = sum(state.row_count for state in split_pairs)
        acc.pairs = {pair for pair, state in pair_stats.items() if state.split == split}
    total["canonical_rows"] = sum(state.row_count for state in pair_stats.values())
    return (
        accumulators,
        pair_stats,
        {
            "total": dict(total),
            "raw_route_strings": raw_route_strings,
            "normalized_route_classes": normalized_route_classes,
            "dose_kind_counts": dose_kind_counts,
            "dose_pair_counts": dose_pair_counts,
            "prod_strength_rows": prod_strength_rows,
        },
    )


def entropy_from_counts(counts: Iterable[int]) -> float:
    values = [int(value) for value in counts if value]
    total = sum(values)
    if total == 0:
        return 0.0
    return float(-sum((value / total) * math.log2(value / total) for value in values))


def top_share(counter: collections.Counter[str], count: int) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return float(sum(value for _, value in counter.most_common(count)) / total)


def classify_pair(state: PairAccumulator) -> str:
    doses = {config[0] for config in state.configs}
    routes = {config[1] for config in state.configs}
    if len(state.configs) == 1:
        return "one_unique_dose_route"
    if len(doses) > 1 and len(routes) == 1:
        return "multiple_doses_same_route"
    if len(doses) == 1 and len(routes) > 1:
        return "same_dose_multiple_routes"
    return "multiple_doses_and_routes"


def temporal_summary(state: PairAccumulator) -> dict[str, Any]:
    unique_signatures = list(state.signatures)
    ambiguous = any(start is None for _, start, _ in unique_signatures)
    events = sorted(state.events, key=lambda value: (value[0], value[1] or value[0], value[2]))
    for index, (start, end, config) in enumerate(events):
        for next_start, _next_end, next_config in events[index + 1 :]:
            if next_config == config:
                continue
            if start == next_start:
                ambiguous = True
            if end is None or end > next_start:
                ambiguous = True
    temporal_change = False
    route_temporal_change = False
    for index, (_, end, config) in enumerate(events[:-1]):
        next_start, _, next_config = events[index + 1]
        if config != next_config and end is not None and end <= next_start:
            temporal_change = True
            if config[1] != next_config[1]:
                route_temporal_change = True
            if route_temporal_change:
                break
    duplicate_rows = sum(count - 1 for count in state.signatures.values() if count > 1)
    nonmissing_routes = {route for route in state.route_classes if route != ROUTE_MISSING}
    nonmissing_doses = {dose for dose in state.dose_tokens if dose != DOSE_MISSING}
    complete_episode_count = sum(
        1
        for (config, start, _), count in state.signatures.items()
        if start is not None and config in state.complete_configs and count > 0
    )
    return {
        "episode_count": len(unique_signatures),
        "complete_episode_count": complete_episode_count,
        "duplicate_rows": duplicate_rows,
        "has_duplicate_order_records": duplicate_rows > 0,
        "multiple_routes": len(nonmissing_routes) > 1,
        "multiple_doses": len(nonmissing_doses) > 1,
        "temporal_change_supported": temporal_change,
        "route_temporal_change_supported": route_temporal_change,
        "temporal_ordering_ambiguous": ambiguous,
    }


def per_medication_diagnostics(
    vocabulary: tuple[str, ...],
    pair_stats: dict[tuple[int, int, str], PairAccumulator],
) -> dict[str, dict[str, float | int]]:
    med_route_counts: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    med_dose_counts: dict[str, collections.Counter[str]] = collections.defaultdict(
        collections.Counter
    )
    med_pair_count: collections.Counter[str] = collections.Counter()
    med_multi_route_pairs: collections.Counter[str] = collections.Counter()
    for (__, ___, med), state in pair_stats.items():
        med_pair_count[med] += 1
        med_route_counts[med].update(state.route_counts)
        med_dose_counts[med].update(state.dose_token_counts)
        if len({route for route in state.route_classes if route != ROUTE_MISSING}) > 1:
            med_multi_route_pairs[med] += 1

    diagnostics: dict[str, dict[str, float | int]] = {}
    for med in vocabulary:
        route_counter = med_route_counts[med]
        dose_counter = med_dose_counts[med]
        route_observed = sum(value for key, value in route_counter.items() if key != ROUTE_MISSING)
        route_entropy = entropy_from_counts(
            value for key, value in route_counter.items() if key != ROUTE_MISSING
        )
        dose_entropy = entropy_from_counts(
            value for key, value in dose_counter.items() if not key.startswith("<MISSING")
        )
        diagnostics[med] = {
            "row_count": int(sum(route_counter.values())),
            "route_class_count": len([key for key in route_counter if key != ROUTE_MISSING]),
            "route_entropy_bits": route_entropy,
            "route_max_share": (
                max(
                    (value for key, value in route_counter.items() if key != ROUTE_MISSING),
                    default=0,
                )
                / route_observed
                if route_observed
                else 0.0
            ),
            "route_ambiguity_pair_fraction": (
                med_multi_route_pairs[med] / med_pair_count[med] if med_pair_count[med] else 0.0
            ),
            "dose_unique_value_count": len(
                [key for key in dose_counter if not key.startswith("<MISSING")]
            ),
            "dose_entropy_bits": dose_entropy,
            "dose_max_share": (
                max(
                    (
                        value
                        for key, value in dose_counter.items()
                        if not key.startswith("<MISSING")
                    ),
                    default=0,
                )
                / sum(
                    value for key, value in dose_counter.items() if not key.startswith("<MISSING")
                )
                if any(not key.startswith("<MISSING") for key in dose_counter)
                else 0.0
            ),
        }
    return diagnostics


def concentration(
    counter: collections.Counter[str], vocabulary: tuple[str, ...]
) -> dict[str, float | int]:
    counts = {med: int(counter.get(med, 0)) for med in vocabulary}
    ordered = sorted(counts.values(), reverse=True)
    total = sum(ordered)
    bottom_half = sum(ordered[len(ordered) // 2 :])
    return {
        "total_units": total,
        "top10_share": sum(ordered[:10]) / total if total else 0.0,
        "top25_share": sum(ordered[:25]) / total if total else 0.0,
        "bottom_half_share": bottom_half / total if total else 0.0,
        "medications_ge_50_units": sum(value >= 50 for value in ordered),
        "medications_ge_100_units": sum(value >= 100 for value in ordered),
    }


def case_count_summary(
    pair_stats: dict[tuple[int, int, str], PairAccumulator],
    split: str,
    vocabulary: tuple[str, ...],
) -> dict[str, Any]:
    states = [state for state in pair_stats.values() if state.split == split]
    admission_pairs = len(states)
    pair_categories = collections.Counter(classify_pair(state) for state in states)
    temporal = [temporal_summary(state) for state in states]
    episode_counts = [item["episode_count"] for item in temporal]
    stable_units = collections.Counter()
    complete_episode_units = collections.Counter()
    stable_meds: set[str] = set()
    episode_meds: set[str] = set()
    admissions: dict[int, int] = collections.Counter()
    episode_admissions: dict[int, int] = collections.Counter()
    patients: dict[int, int] = collections.Counter()
    patient_episode_counts: dict[int, int] = collections.Counter()
    for (subject, hadm, med), state in pair_stats.items():
        if state.split != split:
            continue
        stable = len(state.configs) == 1 and len(state.complete_configs) == 1
        if stable:
            stable_units[med] += 1
            stable_meds.add(med)
            admissions[hadm] += 1
            patients[subject] += 1
        episode = temporal_summary(state)
        patient_episode_counts[subject] += int(episode["episode_count"])
        complete_episode_units[med] += int(episode["complete_episode_count"])
        if episode["complete_episode_count"]:
            episode_meds.add(med)
            episode_admissions[hadm] += int(episode["complete_episode_count"])

    pair_counter = collections.Counter(pair_categories)
    multi_config = admission_pairs - pair_counter["one_unique_dose_route"]
    temporal_change = sum(item["temporal_change_supported"] for item in temporal)
    route_multi = sum(item["multiple_routes"] for item in temporal)
    route_temporal_change = sum(item["route_temporal_change_supported"] for item in temporal)
    duplicate_rows = sum(item["duplicate_rows"] for item in temporal)
    duplicate_pairs = sum(item["has_duplicate_order_records"] for item in temporal)
    temporal_ambiguous = sum(
        item["temporal_ordering_ambiguous"] for item in temporal if item["episode_count"] > 1
    )
    episode_hist = collections.Counter(
        "6+" if count >= 6 else str(count) for count in episode_counts
    )
    admission_target_counts = list(admissions.values())
    episode_target_counts = list(episode_admissions.values())
    return {
        "patients": len(
            {subject for (subject, _, _), state in pair_stats.items() if state.split == split}
        ),
        "canonical_admission_medication_pairs": admission_pairs,
        "pair_categories": dict(pair_counter),
        "pairs_with_multiple_configs": multi_config,
        "pairs_with_temporally_supported_change": temporal_change,
        "temporally_supported_change_fraction_of_multi_config": (
            temporal_change / multi_config if multi_config else 0.0
        ),
        "pairs_with_multiple_routes": route_multi,
        "pairs_with_routes_temporally_distinct": route_temporal_change,
        "route_temporal_distinct_fraction_of_multiple_route_pairs": (
            route_temporal_change / route_multi if route_multi else 0.0
        ),
        "duplicate_order_rows": duplicate_rows,
        "pairs_with_duplicate_order_records": duplicate_pairs,
        "duplicate_row_fraction": duplicate_rows / max(1, sum(state.row_count for state in states)),
        "episode_ordering_ambiguity_rate": temporal_ambiguous
        / max(1, sum(item["episode_count"] > 1 for item in temporal)),
        "episode_count_distribution": dict(sorted(episode_hist.items(), key=lambda item: item[0])),
        "admission_target_events_stable_complete": int(sum(stable_units.values())),
        "admission_target_medications_represented": len(stable_meds),
        "admission_target_cases": len(admission_target_counts),
        "admission_target_count_mean_per_supported_case": (
            sum(admission_target_counts) / len(admission_target_counts)
            if admission_target_counts
            else 0.0
        ),
        "admission_target_count_median_per_supported_case": (
            float(pd.Series(admission_target_counts).median()) if admission_target_counts else 0.0
        ),
        "episode_target_events_complete": int(sum(complete_episode_units.values())),
        "episode_target_medications_represented": len(episode_meds),
        "episode_target_cases": len(episode_target_counts),
        "episode_target_count_mean_per_supported_case": (
            sum(episode_target_counts) / len(episode_target_counts)
            if episode_target_counts
            else 0.0
        ),
        "episode_target_count_median_per_supported_case": (
            float(pd.Series(episode_target_counts).median()) if episode_target_counts else 0.0
        ),
        "patients_with_at_least_two_prescription_decision_points": sum(
            count >= 2 for count in patient_episode_counts.values()
        ),
        # The canonical diagnosis/procedure inputs are admission-level and have
        # no event timestamps.  Thus no within-admission episode has a proven
        # strictly preceding clinical context under the causal contract.
        "episodes_with_causally_aligned_preceding_clinical_context": 0,
        "episode_context_alignment_status": "unsupported_admission_level_codes_have_no_timestamps",
        "concentration_admission_units": concentration(stable_units, vocabulary),
        "concentration_episode_units": concentration(complete_episode_units, vocabulary),
        "pair_category_fractions": {
            key: value / admission_pairs if admission_pairs else 0.0
            for key, value in pair_counter.items()
        },
    }


def apply_decision(
    total: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Apply predeclared semantic floors; no rescue or tuning is performed."""

    episode_context = sum(
        int(summary["episodes_with_causally_aligned_preceding_clinical_context"])
        for summary in summaries.values()
    )
    episode_support = episode_context > 0
    admission_pairs = sum(
        summary["canonical_admission_medication_pairs"] for summary in summaries.values()
    )
    stable_pairs = sum(
        summary["admission_target_events_stable_complete"] for summary in summaries.values()
    )
    stable_fraction = stable_pairs / admission_pairs if admission_pairs else 0.0
    route_usable = total["canonical_rows"] - total["route_rows_missing"]
    dose_usable = total["usable_numeric_dose_rows"]
    route_fraction = route_usable / total["canonical_rows"] if total["canonical_rows"] else 0.0
    dose_fraction = dose_usable / total["canonical_rows"] if total["canonical_rows"] else 0.0

    # Episode targets require causal context.  Admission targets require an
    # overwhelmingly stable complete unit and majority route/dose observability.
    if episode_support:
        decision = "SUPPORT_RXUNIT_EPISODE_PROTOTYPE"
    elif stable_fraction >= 0.90 and route_fraction >= 0.90 and dose_fraction >= 0.80:
        decision = "SUPPORT_RXUNIT_ADMISSION_PROTOTYPE"
    else:
        decision = "KILL_RXUNIT_UNSUPPORTABLE_TARGET"
    return decision, {
        "episode_support": episode_support,
        "stable_admission_pair_fraction": stable_fraction,
        "route_observed_fraction": route_fraction,
        "usable_numeric_dose_fraction": dose_fraction,
        "criteria": {
            "episode_causal_context_required": True,
            "admission_stable_pair_floor": 0.90,
            "admission_route_fraction_floor": 0.90,
            "admission_numeric_dose_fraction_floor": 0.80,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    vocabulary = load_vocabulary(args.vocabulary)
    scope = load_canonical_scope(args.canonical_data)
    ndc_to_atc, ambiguous_mapping_keys = build_ndc_to_atc4(args.mapping_dir)
    prescriptions = table_path(args.mimic_root)
    accumulators, pair_stats, raw = analyze_rows(
        prescriptions,
        scope,
        ndc_to_atc,
        vocabulary,
        args.chunk_size,
    )

    route_rows = raw["normalized_route_classes"]
    dose_kinds = raw["dose_kind_counts"]
    total = raw["total"]
    total["route_rows_missing"] = int(route_rows.get(ROUTE_MISSING, 0))
    total["usable_numeric_dose_rows"] = int(
        sum(
            value
            for key, value in raw["dose_pair_counts"].items()
            if not key.endswith(f"|{DOSE_UNIT_MISSING}")
        )
    )
    total["prod_strength_rows"] = raw["prod_strength_rows"]
    total["ambiguous_mapping_keys"] = ambiguous_mapping_keys
    total["route_missing_fraction"] = (
        total["route_rows_missing"] / total["canonical_rows"] if total["canonical_rows"] else 0.0
    )
    total["usable_numeric_dose_fraction"] = (
        total["usable_numeric_dose_rows"] / total["canonical_rows"]
        if total["canonical_rows"]
        else 0.0
    )

    summaries = {
        split: case_count_summary(pair_stats, split, vocabulary)
        for split in ("Train", "Gate01-Dev")
    }
    for split, acc in accumulators.items():
        summary = summaries[split]
        summary["raw_rows"] = acc.raw_rows
        summary["valid_ndc_rows"] = acc.valid_ndc_rows
        summary["mapped_any_rows"] = acc.mapped_any_rows
        summary["canonical_rows"] = acc.canonical_rows
        summary["outside_rows"] = acc.outside_rows
        summary["unmapped_rows"] = acc.unmapped_rows
        summary["medications_represented_in_canonical_rows"] = len(acc.med_rows)
        summary["route_classes_represented"] = len(
            {route for route in acc.route_rows if route != ROUTE_MISSING}
        )
        summary["usable_dose_coverage"] = (
            sum(acc.med_dose_rows.values()) / acc.canonical_rows if acc.canonical_rows else 0.0
        )
        summary["route_coverage"] = (
            sum(value for route, value in acc.route_rows.items() if route != ROUTE_MISSING)
            / acc.canonical_rows
            if acc.canonical_rows
            else 0.0
        )
        summary["prod_strength_fraction"] = (
            acc.prod_strength_rows / acc.canonical_rows if acc.canonical_rows else 0.0
        )
        summary["medication_row_counts"] = dict(sorted(acc.med_rows.items()))
        summary["medication_patient_counts"] = {
            med: len(subjects) for med, subjects in sorted(acc.med_patients.items())
        }
        summary["concentration_route_rows"] = concentration(
            collections.Counter({med: count for med, count in acc.med_route_rows.items()}),
            vocabulary,
        )
        summary["concentration_numeric_dose_rows"] = concentration(
            collections.Counter({med: count for med, count in acc.med_dose_rows.items()}),
            vocabulary,
        )

    decision, decision_detail = apply_decision(total, summaries)
    per_med = per_medication_diagnostics(vocabulary, pair_stats)
    top_routes = [
        {"route": route, "count": int(count), "fraction": count / sum(route_rows.values())}
        for route, count in route_rows.most_common(20)
    ]
    top_doses = [
        {
            "dose_unit": token,
            "count": int(count),
            "fraction": count / sum(raw["dose_pair_counts"].values()),
        }
        for token, count in raw["dose_pair_counts"].most_common(20)
    ]

    result = {
        "working_name": "RxUnitSet — Structured Prescription-Unit Set Prediction",
        "prototype_status": "throwaway_pre_idea_supportability_only",
        "source_revision": args.source_revision or "unknown",
        "seed": 20260914,
        "decision": decision,
        "decision_detail": decision_detail,
        "scope": {
            "canonical_split": "existing SafeDrug c721 data_final patient order; first two-thirds Train; idea008-gate01-v1 hash Dev half",
            "train_patients": len(scope.train_subjects),
            "dev_patients": len(scope.dev_subjects),
            "train_admissions": len(scope.train_pairs),
            "dev_admissions": len(scope.dev_pairs),
            "heldout_resources_read": False,
            "audit_resources_read": False,
            "g3_resources_read": False,
            "g4_resources_read": False,
            "historical_test_resources_read": False,
            "model_training": False,
        },
        "inputs": {
            "raw_source": "MIMIC-III 1.4 PRESCRIPTIONS.csv(.gz)",
            "canonical_vocabulary_count": N_CONCEPTS,
            "mapping_lineage": "SafeDrug c721 NDC -> RxNorm -> ATC4",
            "diagnoses_procedures": "canonical admission-level identity only; no episode-time labels",
        },
        "alignment": {
            **total,
            "raw_route_string_count": len(raw["raw_route_strings"]),
            "normalized_route_class_count": len(raw["normalized_route_classes"]),
            "dose_kind_counts": dict(dose_kinds),
            "route_top_frequencies": top_routes,
            "route_tail_mass_outside_top10": 1.0 - top_share(route_rows, 10),
            "normalized_dose_unit_pair_top_frequencies": top_doses,
            "dose_unique_pair_count": len(raw["dose_pair_counts"]),
            "prod_strength_present_fraction": (
                raw["prod_strength_rows"] / total["canonical_rows"]
                if total["canonical_rows"]
                else 0.0
            ),
        },
        "train_dev": summaries,
        "per_medication_route_dose_diagnostics": per_med,
        "raw_route_class_counts": dict(sorted(raw["normalized_route_classes"].items())),
        "dose_kind_counts": dict(dose_kinds),
        "concentration": {
            "Train_admission_units": summaries["Train"]["concentration_admission_units"],
            "Train_episode_units": summaries["Train"]["concentration_episode_units"],
            "Train_route_rows": summaries["Train"]["concentration_route_rows"],
            "Train_numeric_dose_rows": summaries["Train"]["concentration_numeric_dose_rows"],
        },
        "no_model_training": True,
        "no_idea_009": True,
        "no_formal_gate": True,
        "no_push": True,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mimic-root", type=Path, required=True)
    parser.add_argument("--canonical-data", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    args = parser.parse_args()
    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be positive")
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps({"decision": result["decision"], "source_revision": result["source_revision"]})
    )


if __name__ == "__main__":
    main()
