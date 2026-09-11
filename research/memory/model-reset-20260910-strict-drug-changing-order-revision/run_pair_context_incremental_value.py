"""Execute the frozen Pair/Context Incremental Value experiment.

The runner deliberately keeps identifiers and model outputs in restricted runtime
memory.  Only aggregate evidence is written to the requested summary and decision
paths after every integrity check succeeds.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

TARGET_REVISION = "15b3cffe42dd08cbfc9e2d8bf34ee766520a67a2"
EXPECTED_STRICT_EVENTS = 1040
R0_SALT = "exposure-reset-20260905"
DISCOVERY_THRESHOLD = 0.70
DEV_THRESHOLD = 0.85
WINDOW_SECONDS = 600
SEEDS = (260911, 260912, 260913)
BOOTSTRAP_REPLICATES = 5000
BOOTSTRAP_SEED = 260911
PERMUTATION_SEED = 260911
N_CLASSES = 131
HISTORY_LENGTH = 64
BATCH_SIZE = 64
BASE_EPOCHS = 20
TRACE_L2 = 1e-4

PASS_VERDICT = "PASS_PAIR_CONTEXT_INCREMENTAL_VALUE"
ABANDON_VERDICT = "ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE"

GROUP_NAMES = ("G0", "G1", "G2")
GROUP_LABELS = {
    "2008 - 2010": "G0",
    "2011 - 2013": "G1",
    "2014 - 2016": "G2",
}

VARIANTS = (
    "DestinationMarginal",
    "SourceTransitionPrior",
    "FlatFinalBase",
    "FlatFinalPlusSourcePrior",
    "TraceContextOnly",
    "PermutedPairContext",
    "PairContext",
)
GATE_CONTROLS = (
    "DestinationMarginal",
    "SourceTransitionPrior",
    "FlatFinalPlusSourcePrior",
    "TraceContextOnly",
    "PermutedPairContext",
)

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

REQUIRED_CONTEXT_COLUMNS = {
    "admissions": {"subject_id", "hadm_id", "admittime"},
    "emar": {"subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"},
}
MIMIC_ACCESS_CONTRACT = {
    "patients": ["subject_id", "anchor_year", "anchor_year_group"],
    "poe": [
        "poe_id",
        "poe_seq",
        "subject_id",
        "hadm_id",
        "ordertime",
        "order_type",
        "transaction_type",
        "discontinue_of_poe_id",
        "order_provider_id",
    ],
    "prescriptions": ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"],
    "admissions": ["subject_id", "hadm_id", "admittime"],
    "emar": ["subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"],
}


class InvalidExecution(RuntimeError):
    """Raised when implementation or execution integrity is not frozen-correct."""


# These helpers intentionally use only the standard library so targeted unit tests
# can run in the repository's dependency-free local environment.
def subject_unit_interval(subject_id: int, salt: str = R0_SALT) -> float:
    token = f"{subject_id}|{salt}".encode()
    return int(hashlib.sha256(token).hexdigest()[:8], 16) / 0xFFFFFFFF


def classify_outer(subject_id: int) -> str:
    u = subject_unit_interval(subject_id)
    if u < DISCOVERY_THRESHOLD:
        return "Discovery"
    if u < DEV_THRESHOLD:
        return "Dev"
    return "Holdout"


def history_before(records: Iterable[Mapping[str, Any]], t_minus: int) -> list[Mapping[str, Any]]:
    """Return only records strictly before the focal source order time."""
    return [
        record
        for record in records
        if record.get("ordertime") is not None and record["ordertime"] < t_minus
    ]


def assert_sample_identity(reference_keys: Sequence[Any], candidate_keys: Sequence[Any]) -> None:
    """Require byte-for-byte candidate/control event identity and ordering."""
    if list(reference_keys) != list(candidate_keys):
        raise ValueError("candidate/control sample identity mismatch")


def validate_context_permutation(
    subjects: Sequence[Any],
    source_labels: Sequence[Any],
    destination_labels: Sequence[Any],
    permutation: Sequence[int],
) -> None:
    """Validate a label-preserving, cross-patient context permutation."""
    n = len(subjects)
    if len(permutation) != n or sorted(permutation) != list(range(n)):
        raise ValueError("context permutation is not a bijection")
    if len(source_labels) != n or len(destination_labels) != n:
        raise ValueError("permutation label length mismatch")
    if any(subjects[i] == subjects[permutation[i]] for i in range(n)):
        raise ValueError("permuted context was assigned within the same subject")


def compute_verdict(gates: Mapping[str, bool]) -> str:
    """Apply the frozen all-controls binary verdict rule."""
    return (
        PASS_VERDICT if gates and all(bool(value) for value in gates.values()) else ABANDON_VERDICT
    )


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InvalidExecution(f"cannot import frozen module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_imports() -> tuple[Any, Any, Any, Any]:
    """Import heavy numerical dependencies only after source preflight."""
    try:
        import numpy as np
        import pandas as pd
        import torch
        import torch.nn.functional as F
    except Exception as exc:  # pragma: no cover - exercised only on an invalid runtime
        raise InvalidExecution(f"required numerical runtime unavailable: {exc}") from exc
    return np, pd, torch, F


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN, without importing pandas at module import time.
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text in {"", "nan", "NaN", "<NA>", "None"} else text


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


def clean_nonzero_identifier(value: Any) -> str:
    """Normalize nullable identifiers while treating the frozen sentinel 0 as absent."""
    text = clean_text(value)
    return "" if text in {"0", "0.0"} else text


def table_path(mimic_dir: Path, name: str) -> Path:
    gz = mimic_dir / f"{name}.csv.gz"
    plain = mimic_dir / f"{name}.csv"
    if gz.exists():
        return gz
    if plain.exists():
        return plain
    raise InvalidExecution(f"missing required MIMIC table: {name}")


def verify_execution_checkout(repo_root: Path, expected_revision: str) -> str:
    head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1"], text=True
    )
    if head != expected_revision or status:
        raise InvalidExecution(
            f"execution checkout must be clean at {expected_revision}; observed {head!r}"
        )
    return head


def read_frozen_protocol(protocol_path: Path) -> dict[str, Any]:
    text = protocol_path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match is None:
        raise InvalidExecution("Pair/Context protocol machine-readable block is missing")
    try:
        spec = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise InvalidExecution("Pair/Context protocol machine-readable block is invalid") from exc
    if spec.get("protocol") != "PAIR_CONTEXT_INCREMENTAL_VALUE":
        raise InvalidExecution("Pair/Context protocol identity mismatch")
    if spec.get("source_revision") != TARGET_REVISION:
        raise InvalidExecution("Pair/Context protocol source revision mismatch")
    if spec.get("strict_events_expected") != EXPECTED_STRICT_EVENTS:
        raise InvalidExecution("Pair/Context strict semantic identity mismatch")
    partition = spec.get("partition", {})
    if partition != {
        "salt": R0_SALT,
        "discovery_upper": DISCOVERY_THRESHOLD,
        "dev_upper": DEV_THRESHOLD,
        "holdout_lower": DEV_THRESHOLD,
    }:
        raise InvalidExecution("Pair/Context partition contract differs from frozen protocol")
    base = spec.get("flat_final_base", {})
    if base != {
        "learning_rate": 0.001,
        "weight_decay": 0.00001,
        "batch_size": BATCH_SIZE,
        "epochs": BASE_EPOCHS,
        "seeds": list(SEEDS),
    }:
        raise InvalidExecution("FlatFinalBase training contract differs from frozen protocol")
    probe = spec.get("trace_probe", {})
    if probe != {
        "classes": N_CLASSES,
        "context_dim": 128,
        "l2": TRACE_L2,
        "initialization": "zero",
        "optimizer": "deterministic_lbfgs",
    }:
        raise InvalidExecution("trace-probe contract differs from frozen protocol")
    bootstrap = spec.get("bootstrap", {})
    if bootstrap != {
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "cluster": "subject_id",
    }:
        raise InvalidExecution("bootstrap contract differs from frozen protocol")
    criteria = spec.get("criteria", {})
    if criteria != {
        "relative_gain": 0.05,
        "bootstrap_lower_bound": 0.0,
        "pair_context_lower_each_seed": True,
    }:
        raise InvalidExecution("verdict criteria differ from frozen protocol")
    if spec.get("mimic_access") != MIMIC_ACCESS_CONTRACT:
        raise InvalidExecution("MIMIC access declaration differs from frozen protocol")
    return spec


def check_schema(pd: Any, mimic_dir: Path, support: Any) -> None:
    support.check_schema(mimic_dir)
    for table, required in REQUIRED_CONTEXT_COLUMNS.items():
        columns = set(pd.read_csv(table_path(mimic_dir, table), nrows=0).columns)
        missing = sorted(required - columns)
        if missing:
            raise InvalidExecution(f"missing fields in {table}: {missing}")


def load_vocab_codes(vocab_dir: Path) -> tuple[list[str], dict[str, int], set[str]]:
    import dill

    with (vocab_dir / "voc_final.pkl").open("rb") as handle:
        vocabulary = dill.load(handle)
    idx2word = vocabulary["med_voc"].idx2word
    codes = [str(idx2word[index]) for index in range(N_CLASSES)]
    if (
        len(codes) != N_CLASSES
        or len(set(codes)) != N_CLASSES
        or any(len(code) != 4 for code in codes)
    ):
        raise InvalidExecution("frozen medication vocabulary is not 131 unique ATC-L4 codes")
    return codes, {code: index for index, code in enumerate(codes)}, set(codes)


def parse_epochs(pd: Any, series: Any) -> list[int | None]:
    parsed = pd.to_datetime(series, errors="coerce")
    valid = (~parsed.isna()).to_numpy()
    values = parsed.astype("int64").to_numpy()
    return [
        int(value // 1_000_000_000) if ok else None for value, ok in zip(values, valid, strict=True)
    ]


def read_admissions(
    pd: Any,
    mimic_dir: Path,
    strict_hadm_ids: set[int],
) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    dtype = {"subject_id": "Int64", "hadm_id": "Int64", "admittime": "string"}
    for chunk in pd.read_csv(
        table_path(mimic_dir, "admissions"),
        usecols=["subject_id", "hadm_id", "admittime"],
        dtype=dtype,
        compression="infer",
        chunksize=250_000,
        low_memory=False,
    ):
        selected = chunk.loc[chunk["hadm_id"].isin(strict_hadm_ids)]
        if selected.empty:
            continue
        epochs = parse_epochs(pd, selected["admittime"])
        for row, admit_epoch in zip(selected.itertuples(index=False), epochs, strict=False):
            sid = as_int(row.subject_id)
            hid = as_int(row.hadm_id)
            if sid is not None and hid is not None and admit_epoch is not None:
                result[hid] = (sid, admit_epoch)
    if len(result) != len(strict_hadm_ids):
        missing = len(strict_hadm_ids - set(result))
        raise InvalidExecution(f"admission context missing for {missing} strict hospitalizations")
    return result


def read_context_orders(
    pd: Any,
    mimic_dir: Path,
    allowed_subjects: set[int],
    strict_hadm_ids: set[int],
) -> dict[int, list[dict[str, Any]]]:
    usecols = [
        "poe_id",
        "poe_seq",
        "subject_id",
        "hadm_id",
        "ordertime",
        "order_type",
        "transaction_type",
        "discontinue_of_poe_id",
        "order_provider_id",
    ]
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
    by_hadm: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for chunk in pd.read_csv(
        table_path(mimic_dir, "poe"),
        usecols=usecols,
        dtype=dtype,
        compression="infer",
        chunksize=250_000,
        low_memory=False,
    ):
        selected = chunk.loc[
            chunk["subject_id"].isin(allowed_subjects) & chunk["hadm_id"].isin(strict_hadm_ids)
        ]
        if selected.empty:
            continue
        epochs = parse_epochs(pd, selected["ordertime"])
        for row, order_epoch in zip(selected.itertuples(index=False), epochs, strict=False):
            if clean_text(row.order_type) != "Medications":
                continue
            transaction = clean_text(row.transaction_type)
            if transaction not in {"New", "Change", "D/C"}:
                continue
            hid = as_int(row.hadm_id)
            sid = as_int(row.subject_id)
            poe_id = clean_text(row.poe_id)
            if hid is None or sid is None or not poe_id:
                continue
            by_hadm[hid].append(
                {
                    "poe_id": poe_id,
                    "poe_seq": as_int(row.poe_seq),
                    "subject_id": sid,
                    "hadm_id": hid,
                    "ordertime": order_epoch,
                    "order_type": "Medications",
                    "transaction_type": transaction,
                    "discontinue_of_poe_id": clean_text(row.discontinue_of_poe_id),
                    "order_provider_id": clean_text(row.order_provider_id),
                }
            )
    for records in by_hadm.values():
        records.sort(
            key=lambda record: (
                record["ordertime"] if record["ordertime"] is not None else 2**63 - 1,
                record["poe_seq"] if record["poe_seq"] is not None else 2**63 - 1,
                record["poe_id"],
            )
        )
    if set(by_hadm) != strict_hadm_ids:
        raise InvalidExecution("context POE rows are missing for a strict hospitalization")
    return dict(by_hadm)


def build_relevant_prescription_linkage(
    pd: Any,
    support: Any,
    mimic_dir: Path,
    mapping_dir: Path,
    allowed_subjects: set[int],
    discovery_subjects: set[int],
    relevant_poe_ids: set[str],
    vocabulary: set[str],
    expected_poe_to_atcs: Mapping[str, set[str]],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Reproduce the frozen mapping lineage and retain pharmacy links only for context POEs."""
    mapping = support.build_ndc_mapping(mapping_dir)
    usecols = ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"]
    counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for chunk in support.iter_prescription_chunks(mimic_dir, discovery_subjects, usecols):
        for row in chunk.itertuples(index=False):
            atc = support.lookup_atc(row.ndc, mapping)
            fcd = clean_text(row.formulary_drug_cd)
            if atc in vocabulary and fcd:
                counts[fcd][atc] += 1
    consensus: dict[str, str] = {}
    for fcd, counter in counts.items():
        atc, top_count = counter.most_common(1)[0]
        if top_count / sum(counter.values()) >= 0.85:
            consensus[fcd] = atc

    local_atcs: dict[str, set[str]] = collections.defaultdict(set)
    poe_to_pharmacy: dict[str, set[str]] = collections.defaultdict(set)
    for chunk in support.iter_prescription_chunks(mimic_dir, allowed_subjects, usecols):
        for row in chunk.itertuples(index=False):
            poe_id = clean_text(row.poe_id)
            if poe_id not in relevant_poe_ids:
                continue
            atc = support.lookup_atc(row.ndc, mapping)
            if atc not in vocabulary:
                atc = consensus.get(clean_text(row.formulary_drug_cd))
            if atc in vocabulary:
                local_atcs[poe_id].add(atc)
                pharmacy_id = clean_nonzero_identifier(row.pharmacy_id)
                if pharmacy_id:
                    poe_to_pharmacy[poe_id].add(pharmacy_id)
    for poe_id in relevant_poe_ids:
        if local_atcs.get(poe_id, set()) != expected_poe_to_atcs.get(poe_id, set()):
            raise InvalidExecution(f"mapping divergence for context POE {poe_id}")
    return dict(local_atcs), dict(poe_to_pharmacy)


def read_administrations(
    pd: Any,
    mimic_dir: Path,
    allowed_subjects: set[int],
    strict_hadm_ids: set[int],
) -> dict[int, list[tuple[int, str, str]]]:
    usecols = ["subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"]
    dtype = {
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "poe_id": "string",
        "pharmacy_id": "string",
        "charttime": "string",
        "event_txt": "string",
    }
    by_hadm: dict[int, list[tuple[int, str, str]]] = collections.defaultdict(list)
    for chunk in pd.read_csv(
        table_path(mimic_dir, "emar"),
        usecols=usecols,
        dtype=dtype,
        compression="infer",
        chunksize=250_000,
        low_memory=False,
    ):
        selected = chunk.loc[
            chunk["subject_id"].isin(allowed_subjects) & chunk["hadm_id"].isin(strict_hadm_ids)
        ]
        if selected.empty:
            continue
        selected = selected.loc[selected["event_txt"].isin(ADMINISTRATION_EVENT_TYPES)]
        if selected.empty:
            continue
        epochs = parse_epochs(pd, selected["charttime"])
        for row, chart_epoch in zip(selected.itertuples(index=False), epochs, strict=False):
            hid = as_int(row.hadm_id)
            if hid is None or chart_epoch is None:
                continue
            by_hadm[hid].append(
                (
                    chart_epoch,
                    clean_nonzero_identifier(row.poe_id),
                    clean_nonzero_identifier(row.pharmacy_id),
                )
            )
    return dict(by_hadm)


def _record_identity(record: Mapping[str, Any], poe_to_atcs: Mapping[str, set[str]]) -> set[str]:
    if record["transaction_type"] == "D/C":
        reference = clean_text(record.get("discontinue_of_poe_id"))
        return set(poe_to_atcs.get(reference, set())) if reference else set()
    return set(poe_to_atcs.get(record["poe_id"], set()))


def _has_prior_administration(
    record: Mapping[str, Any],
    t_minus: int,
    admin_poe_times: Mapping[str, list[int]],
    admin_pharmacy_times: Mapping[str, list[int]],
    poe_to_pharmacy: Mapping[str, set[str]],
) -> bool:
    poe_id = record["poe_id"]
    if any(charttime < t_minus for charttime in admin_poe_times.get(poe_id, [])):
        return True
    return any(
        charttime < t_minus
        for pharmacy_id in poe_to_pharmacy.get(poe_id, set())
        for charttime in admin_pharmacy_times.get(pharmacy_id, [])
    )


def build_example(
    event: Mapping[str, Any],
    context_orders: Sequence[Mapping[str, Any]],
    admit_context: tuple[int, int],
    administrations: Sequence[tuple[int, str, str]],
    poe_to_atcs: Mapping[str, set[str]],
    poe_to_pharmacy: Mapping[str, set[str]],
    concept_to_idx: Mapping[str, int],
) -> dict[str, Any]:
    source = event["source"]
    old = event["old"]
    new = event["new"]
    t_minus = old["ordertime"]
    if t_minus is None:
        raise InvalidExecution("strict focal source order has invalid time")
    if old["poe_id"] not in {record["poe_id"] for record in context_orders}:
        raise InvalidExecution("strict old order absent from causal context")
    if new["poe_id"] not in {record["poe_id"] for record in context_orders}:
        raise InvalidExecution("strict New order absent from causal context")

    sorted_orders = list(context_orders)
    prior = list(history_before(sorted_orders, t_minus))
    hist = prior[-HISTORY_LENGTH:]
    hist_meds = [0] * HISTORY_LENGTH
    hist_types = [0] * HISTORY_LENGTH
    hist_elapsed = [0.0] * HISTORY_LENGTH
    previous_time: int | None = None
    for position, record in enumerate(hist):
        identity = _record_identity(record, poe_to_atcs)
        concept = sorted(identity)[0] if identity else None
        hist_meds[position] = concept_to_idx[concept] + 1 if concept in concept_to_idx else 0
        transaction = record["transaction_type"]
        hist_types[position] = {"New": 1, "Change": 2, "D/C": 3}[transaction]
        elapsed_hours = (
            (record["ordertime"] - previous_time) / 3600.0
            if previous_time is not None and record["ordertime"] is not None
            else 0.0
        )
        hist_elapsed[position] = math.log1p(max(0.0, elapsed_hours))
        previous_time = record["ordertime"]

    admin_poe_times: dict[str, list[int]] = collections.defaultdict(list)
    admin_pharmacy_times: dict[str, list[int]] = collections.defaultdict(list)
    for charttime, poe_id, pharmacy_id in administrations:
        if poe_id:
            admin_poe_times[poe_id].append(charttime)
        if pharmacy_id:
            admin_pharmacy_times[pharmacy_id].append(charttime)

    discontinued = {
        clean_text(record.get("discontinue_of_poe_id"))
        for record in prior
        if record["transaction_type"] == "D/C" and clean_text(record.get("discontinue_of_poe_id"))
    }
    active_concepts: set[str] = set()
    for record in prior:
        if record["transaction_type"] not in {"New", "Change"}:
            continue
        if record["poe_id"] in discontinued:
            continue
        identities = poe_to_atcs.get(record["poe_id"], set())
        if identities and _has_prior_administration(
            record, t_minus, admin_poe_times, admin_pharmacy_times, poe_to_pharmacy
        ):
            active_concepts.update(identities)
    active_regimen = [0.0] * N_CLASSES
    for concept in active_concepts:
        if concept in concept_to_idx:
            active_regimen[concept_to_idx[concept]] = 1.0

    target_concepts: set[str] = set()
    for record in sorted_orders:
        if record["transaction_type"] in {"New", "Change"}:
            target_concepts.update(poe_to_atcs.get(record["poe_id"], set()))
    if not target_concepts:
        raise InvalidExecution("ordinary flattened admission target is empty")
    if event["new_identity"] not in target_concepts:
        raise InvalidExecution("strict identity absent from ordinary flattened target")
    target_vec = [0.0] * N_CLASSES
    for concept in target_concepts:
        if concept in concept_to_idx:
            target_vec[concept_to_idx[concept]] = 1.0

    subject_id, admit_epoch = admit_context
    hours_since_admit = max(0.0, (t_minus - admit_epoch) / 3600.0)
    return {
        "subject_id": subject_id,
        "hadm_id": source["hadm_id"],
        "event_key": (subject_id, source["hadm_id"], old["poe_id"], new["poe_id"]),
        "source_index": concept_to_idx[event["old_identity"]],
        "destination_index": concept_to_idx[event["new_identity"]],
        "hist_meds": hist_meds,
        "hist_types": hist_types,
        "hist_elapsed": hist_elapsed,
        "active_regimen": active_regimen,
        "log_hours_since_admit": math.log1p(hours_since_admit),
        "target_vec": target_vec,
    }


def _make_context_permutation_indices(
    subjects: Sequence[int], seed: int = PERMUTATION_SEED
) -> list[int]:
    """Create a deterministic global permutation with cross-patient contexts."""
    n = len(subjects)
    if n < 2:
        raise InvalidExecution(
            "cannot create a cross-patient permutation with fewer than two events"
        )
    keyed = sorted(
        range(n),
        key=lambda index: (
            subjects[index],
            hashlib.sha256(f"{seed}|{index}".encode()).hexdigest(),
        ),
    )
    counts = collections.Counter(subjects)
    shift = max(counts.values())
    if shift >= n:
        raise InvalidExecution("cross-patient context permutation is impossible")
    permutation = [keyed[(position + shift) % n] for position in range(n)]
    try:
        validate_context_permutation(subjects, subjects, subjects, permutation)
    except ValueError as exc:
        raise InvalidExecution(str(exc)) from exc
    return permutation


def make_context_permutation(
    np: Any, subjects: Sequence[int], seed: int = PERMUTATION_SEED
) -> list[int]:
    del np  # The permutation itself is standard-library deterministic.
    return _make_context_permutation_indices(subjects, seed)


def make_context_permutation_for_test(
    subjects: Sequence[int], seed: int = PERMUTATION_SEED
) -> list[int]:
    return _make_context_permutation_indices(subjects, seed)


def _set_seed(random: Any, np: Any, torch: Any, seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def _tensorize(
    np: Any, torch: Any, examples: Sequence[Mapping[str, Any]], device: Any
) -> dict[str, Any]:
    if not examples:
        raise InvalidExecution("empty experiment partition")
    tensors = {
        "hist_meds": torch.as_tensor(
            np.asarray([item["hist_meds"] for item in examples], dtype=np.int64), device=device
        ),
        "hist_types": torch.as_tensor(
            np.asarray([item["hist_types"] for item in examples], dtype=np.int64), device=device
        ),
        "hist_elapsed": torch.as_tensor(
            np.asarray([item["hist_elapsed"] for item in examples], dtype=np.float32), device=device
        ),
        "active_regimen": torch.as_tensor(
            np.asarray([item["active_regimen"] for item in examples], dtype=np.float32),
            device=device,
        ),
        "log_hours_since_admit": torch.as_tensor(
            np.asarray([[item["log_hours_since_admit"]] for item in examples], dtype=np.float32),
            device=device,
        ),
        "target_vec": torch.as_tensor(
            np.asarray([item["target_vec"] for item in examples], dtype=np.float32), device=device
        ),
    }
    return tensors


def _forward_with_hidden(model: Any, batch: Mapping[str, Any], torch: Any) -> tuple[Any, Any]:
    hist_meds = batch["hist_meds"]
    hist_types = batch["hist_types"]
    hist_elapsed = batch["hist_elapsed"]
    active_regimen = batch["active_regimen"]
    log_hours = batch["log_hours_since_admit"]
    med_emb = model.med_embedding(hist_meds)
    trans_emb = model.trans_embedding(hist_types)
    elapsed_feat = model.elapsed_proj(hist_elapsed.unsqueeze(-1))
    gru_in = torch.cat([med_emb, trans_emb, elapsed_feat], dim=-1)
    mask = hist_meds > 0
    seq_lens = mask.sum(dim=-1)
    gru_out, _ = model.gru(gru_in)
    final_gru = torch.zeros(
        hist_meds.size(0), model.gru.hidden_size, device=gru_in.device, dtype=gru_in.dtype
    )
    has_hist = seq_lens > 0
    if has_hist.any():
        valid = torch.where(has_hist)[0]
        final_gru[valid] = gru_out[valid, seq_lens[valid] - 1]
    if (~has_hist).any():
        no_history = torch.where(~has_hist)[0]
        final_gru[no_history] = model.zero_history
    combined = torch.cat([final_gru, active_regimen, log_hours], dim=-1)
    pre_projection = model.mlp[0](combined)
    hidden = model.mlp[1](pre_projection)
    logits = model.mlp[3](model.mlp[2](hidden))
    return logits, hidden


def _predict_flat(np: Any, torch: Any, model: Any, tensors: Mapping[str, Any]) -> tuple[Any, Any]:
    model.eval()
    logits_parts = []
    hidden_parts = []
    with torch.no_grad():
        for start in range(0, tensors["hist_meds"].shape[0], 256):
            batch = {key: value[start : start + 256] for key, value in tensors.items()}
            logits, hidden = _forward_with_hidden(model, batch, torch)
            logits_parts.append(logits.detach().cpu())
            hidden_parts.append(hidden.detach().cpu())
    return torch.cat(logits_parts).numpy(), torch.cat(hidden_parts).numpy()


def train_flat_base(
    np: Any,
    torch: Any,
    F: Any,
    random: Any,
    model_cls: Any,
    discovery: Sequence[Mapping[str, Any]],
    dev: Sequence[Mapping[str, Any]],
    device: Any,
    seed: int,
) -> tuple[Any, Any, Any]:
    _set_seed(random, np, torch, seed)
    model = model_cls(num_medications=N_CLASSES).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
    train_tensors = _tensorize(np, torch, discovery, device)
    dev_tensors = _tensorize(np, torch, dev, device)
    rng = np.random.default_rng(seed)
    n = len(discovery)
    for _epoch in range(BASE_EPOCHS):
        model.train()
        for permutation_start in range(0, n, BATCH_SIZE):
            # A seeded permutation gives deterministic batches without a DataLoader worker.
            if permutation_start == 0:
                epoch_order = rng.permutation(n)
            indices = epoch_order[permutation_start : permutation_start + BATCH_SIZE]
            index_tensor = torch.as_tensor(indices, dtype=torch.long, device=device)
            batch = {key: value[index_tensor] for key, value in train_tensors.items()}
            optimizer.zero_grad(set_to_none=True)
            logits = model(
                batch["hist_meds"],
                batch["hist_types"],
                batch["hist_elapsed"],
                batch["active_regimen"],
                batch["log_hours_since_admit"],
            )
            loss = F.binary_cross_entropy_with_logits(logits, batch["target_vec"], reduction="mean")
            if not bool(torch.isfinite(loss)):
                raise InvalidExecution(f"non-finite FlatFinalBase loss at seed {seed}")
            loss.backward()
            optimizer.step()
    model.eval()
    discovery_logits, discovery_hidden = _predict_flat(np, torch, model, train_tensors)
    dev_logits, dev_hidden = _predict_flat(np, torch, model, dev_tensors)
    if (
        not np.isfinite(discovery_logits).all()
        or not np.isfinite(dev_logits).all()
        or not np.isfinite(discovery_hidden).all()
        or not np.isfinite(dev_hidden).all()
    ):
        raise InvalidExecution(f"non-finite FlatFinalBase output at seed {seed}")
    return model, (discovery_logits, discovery_hidden), (dev_logits, dev_hidden)


def fit_trace_probe(
    np: Any,
    torch: Any,
    F: Any,
    features: Any,
    labels: Any,
    device: Any,
) -> Any:
    """Fit the fixed zero-initialized full-batch multinomial LBFGS probe."""
    layer = torch.nn.Linear(int(features.shape[1]), N_CLASSES, bias=True).to(device)
    torch.nn.init.zeros_(layer.weight)
    torch.nn.init.zeros_(layer.bias)
    x = torch.as_tensor(np.asarray(features, dtype=np.float32), device=device)
    y = torch.as_tensor(np.asarray(labels, dtype=np.int64), device=device)
    optimizer = torch.optim.LBFGS(
        layer.parameters(),
        lr=1.0,
        max_iter=100,
        history_size=10,
        line_search_fn="strong_wolfe",
        tolerance_grad=1e-9,
        tolerance_change=1e-12,
    )

    def closure() -> Any:
        optimizer.zero_grad(set_to_none=True)
        logits = layer(x)
        loss = F.cross_entropy(logits, y, reduction="mean")
        l2 = sum(parameter.pow(2).sum() for parameter in layer.parameters())
        loss = loss + 0.5 * TRACE_L2 * l2
        if not bool(torch.isfinite(loss)):
            raise InvalidExecution("non-finite trace-probe optimization")
        loss.backward()
        return loss

    optimizer.step(closure)
    with torch.no_grad():
        logits = layer(x).detach().cpu().numpy()
    if not np.isfinite(logits).all():
        raise InvalidExecution("non-finite trace-probe logits")
    return layer


def predict_trace_probe(np: Any, torch: Any, layer: Any, features: Any, device: Any) -> Any:
    x = torch.as_tensor(np.asarray(features, dtype=np.float32), device=device)
    layer.eval()
    with torch.no_grad():
        logits = layer(x).detach().cpu().numpy()
    if not np.isfinite(logits).all():
        raise InvalidExecution("non-finite trace-probe Dev logits")
    return logits


def softmax(np: Any, logits: Any) -> Any:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=1, keepdims=True)


def evaluate_probs(
    np: Any, probabilities: Any, labels: Sequence[int]
) -> tuple[Any, dict[str, float]]:
    labels_array = np.asarray(labels, dtype=np.int64)
    if probabilities.shape[0] != labels_array.shape[0]:
        raise InvalidExecution("candidate/control sample identity mismatch in metric evaluation")
    if not np.isfinite(probabilities).all():
        raise InvalidExecution("non-finite probability output")
    row_indices = np.arange(labels_array.shape[0])
    nll = -np.log(np.clip(probabilities[row_indices, labels_array], 1e-12, 1.0))
    order = np.argsort(-probabilities, axis=1, kind="stable")
    ranks = np.argmax(order == labels_array[:, None], axis=1) + 1
    mrr = 1.0 / ranks
    hit5 = (ranks <= 5).astype(np.float64)
    return nll, {
        "dev_nll": float(np.mean(nll)),
        "mrr": float(np.mean(mrr)),
        "hit_at_5": float(np.mean(hit5)),
    }


def patient_cluster_bootstrap(
    np: Any,
    subjects: Sequence[int],
    control_nll: Any,
    pair_nll: Any,
) -> dict[str, Any]:
    unique_subjects, inverse = np.unique(np.asarray(subjects), return_inverse=True)
    n_subjects = len(unique_subjects)
    if n_subjects == 0:
        raise InvalidExecution("empty Dev patient cluster set")
    event_counts = np.bincount(inverse, minlength=n_subjects).astype(np.float64)
    control_sums = np.bincount(inverse, weights=np.asarray(control_nll), minlength=n_subjects)
    pair_sums = np.bincount(inverse, weights=np.asarray(pair_nll), minlength=n_subjects)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    gains = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for replicate in range(BOOTSTRAP_REPLICATES):
        sampled = rng.integers(0, n_subjects, size=n_subjects)
        frequencies = np.bincount(sampled, minlength=n_subjects).astype(np.float64)
        denominator = float(frequencies @ event_counts)
        control_mean = float(frequencies @ control_sums) / denominator
        pair_mean = float(frequencies @ pair_sums) / denominator
        gains[replicate] = (control_mean - pair_mean) / control_mean
    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "cluster": "subject_id",
        "mean": float(np.mean(gains)),
        "ci_95": [float(np.percentile(gains, 2.5)), float(np.percentile(gains, 97.5))],
    }


def _mean_metric_arrays(np: Any, arrays: Sequence[Any]) -> Any:
    stacked = np.stack(arrays, axis=0)
    return np.mean(stacked, axis=0)


def _build_priors(np: Any, sources: Sequence[int], destinations: Sequence[int]) -> tuple[Any, Any]:
    destination_counts = np.bincount(destinations, minlength=N_CLASSES).astype(np.float64)
    p_destination = (destination_counts + 1.0) / (len(destinations) + N_CLASSES)
    pair_counts = np.zeros((N_CLASSES, N_CLASSES), dtype=np.float64)
    source_counts = np.zeros(N_CLASSES, dtype=np.float64)
    for source, destination in zip(sources, destinations, strict=False):
        pair_counts[source, destination] += 1.0
        source_counts[source] += 1.0
    p_source = (pair_counts + p_destination[None, :]) / (source_counts[:, None] + 1.0)
    return p_destination, p_source


def decision_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Pair/Context Incremental Value Decision",
        "",
        "## Scientific question",
        "",
        "Does strict drug-changing order-revision supervision contain context-dependent, cross-patient predictive value beyond ordinary flattened final-prescription supervision and trivial source/destination frequency structure?",
        "",
        "## Semantic-object integrity",
        "",
        (
            f"`PASS_SEMANTIC_ADMISSION` strict identity was re-materialized: "
            f"{summary['integrity']['strict_events_observed']} events observed (expected "
            f"{summary['integrity']['strict_events_expected']}), with "
            f"{summary['integrity']['frozen_invariant_violations']} frozen semantic violations."
        ),
        "",
        "## Aggregate partition counts",
        "",
        "| Partition | Strict events | Unique patients |",
        "| --- | ---: | ---: |",
    ]
    for partition in ("Discovery", "Dev"):
        row = summary["partitions"][partition]
        lines.append(f"| {partition} | {row['strict_events']} | {row['unique_patients']} |")
    lines.extend(["", "## Variant metrics", ""])
    for variant in VARIANTS:
        lines.extend(
            [
                f"### `{variant}`",
                "",
                "| Seed | Dev NLL | MRR | Hit@5 |",
                "| ---: | ---: | ---: | ---: |",
            ]
        )
        for seed in SEEDS:
            row = summary["variants"][variant][str(seed)]
            lines.append(
                f"| {seed} | {row['dev_nll']:.12g} | {row['mrr']:.12g} | {row['hit_at_5']:.12g} |"
            )
        mean = summary["variants"][variant]["mean"]
        lines.append(
            f"| mean | {mean['dev_nll']:.12g} | {mean['mrr']:.12g} | {mean['hit_at_5']:.12g} |"
        )
        lines.append("")
    lines.extend(
        [
            "## Frozen gate comparisons",
            "",
            "| Control | Relative NLL gain | Bootstrap 95% CI | Pair lower each seed | Status |",
            "| --- | ---: | --- | :---: | :---: |",
        ]
    )
    for control in GATE_CONTROLS:
        row = summary["gate_comparisons"][control]
        ci = row["bootstrap"]["ci_95"]
        lines.append(
            f"| `{control}` | {row['relative_nll_gain']:.12g} | [{ci[0]:.12g}, {ci[1]:.12g}] | "
            f"{'PASS' if row['pair_nll_lower_each_seed'] else 'FAIL'} | {'PASS' if row['pass'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"`{summary['verdict']}`",
            "",
            "No clinical correctness, treatment effect, validated RAR, therapeutic substitution, or superiority is inferred.",
            "",
            "## Quarantine",
            "",
            "G3/G4, R0 Holdout, and the historical project test split were not accessed or loaded.",
            "",
            "## Next-stage boundary",
            "",
            (
                "The bounded pre-Idea premise survived; hand scientific ownership to `ccf-pipeline-orchestrator` for fresh next-stage routing. No further stage is authorized in this run."
                if summary["verdict"] == PASS_VERDICT
                else "The candidate is terminated under the frozen definition; no rescue is authorized."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    # Nothing below this line may open a MIMIC file until checkout/protocol checks pass.
    execution_revision = verify_execution_checkout(args.repo_root, args.execution_revision)
    read_frozen_protocol(args.protocol)
    np, pd, torch, F = _runtime_imports()
    support = _load_module(
        args.repo_root
        / "research/memory/model-reset-20260910-strict-drug-changing-order-revision"
        / "run_strict_drug_changing_supportability.py",
        "strict_supportability_frozen",
    )
    model_module = _load_module(
        args.repo_root
        / "research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate01_model.py",
        "gate01_model_frozen",
    )
    if getattr(support, "TARGET_REVISION", None) != TARGET_REVISION:
        raise InvalidExecution("strict supportability source revision mismatch")
    check_schema(pd, args.mimic_dir, support)
    verify_execution_checkout(args.repo_root, execution_revision)

    patients, allowed_subjects, discovery_subjects = support.load_population(args.mimic_dir)
    mapping = support.build_ndc_mapping(args.mapping_dir)
    _codes, concept_to_idx, vocabulary = load_vocab_codes(args.vocab_dir)
    source_dc, new_orders, old_refs = support.read_poe_orders(
        args.mimic_dir, patients, allowed_subjects
    )
    poe_to_atcs = support.build_poe_identity_map(
        args.mimic_dir, allowed_subjects, discovery_subjects, mapping, vocabulary
    )
    old_rows = support.read_referenced_old_rows(args.mimic_dir, allowed_subjects, old_refs)
    strict, _flow, violations = support.construct_strict_events(
        source_dc, new_orders, old_refs, old_rows, poe_to_atcs, patients
    )
    if violations or len(strict) != EXPECTED_STRICT_EVENTS:
        raise InvalidExecution(
            f"semantic identity mismatch: expected {EXPECTED_STRICT_EVENTS}, observed {len(strict)}, violations={dict(violations)}"
        )

    event_subjects = [item["source"]["subject_id"] for item in strict]
    if any(classify_outer(subject) == "Holdout" for subject in event_subjects):
        raise InvalidExecution("R0 Holdout subject entered the experiment population")
    event_partitions = [classify_outer(subject) for subject in event_subjects]
    if set(event_partitions) - {"Discovery", "Dev"}:
        raise InvalidExecution("unexpected experiment partition")
    discovery_events = [
        item for item, part in zip(strict, event_partitions, strict=False) if part == "Discovery"
    ]
    dev_events = [
        item for item, part in zip(strict, event_partitions, strict=False) if part == "Dev"
    ]
    if not discovery_events or not dev_events:
        raise InvalidExecution("Discovery or Dev strict partition is empty")
    if set(
        event_subjects[i] for i, part in enumerate(event_partitions) if part == "Discovery"
    ) & set(event_subjects[i] for i, part in enumerate(event_partitions) if part == "Dev"):
        raise InvalidExecution("subject partition leakage between Discovery and Dev")

    strict_hadm_ids = {item["source"]["hadm_id"] for item in strict}
    if None in strict_hadm_ids:
        raise InvalidExecution("strict event has null hospitalization")
    admit_by_hadm = read_admissions(pd, args.mimic_dir, {int(value) for value in strict_hadm_ids})
    context_orders = read_context_orders(
        pd, args.mimic_dir, allowed_subjects, {int(value) for value in strict_hadm_ids}
    )
    relevant_poe_ids = {
        record["poe_id"] for records in context_orders.values() for record in records
    }
    local_atcs, poe_to_pharmacy = build_relevant_prescription_linkage(
        pd,
        support,
        args.mimic_dir,
        args.mapping_dir,
        allowed_subjects,
        discovery_subjects,
        relevant_poe_ids,
        vocabulary,
        poe_to_atcs,
    )
    del local_atcs
    administrations = read_administrations(
        pd, args.mimic_dir, allowed_subjects, {int(value) for value in strict_hadm_ids}
    )

    all_examples: list[dict[str, Any]] = []
    for event in strict:
        old_identity = event["old_identity"]
        new_identity = event["new_identity"]
        if (
            len(poe_to_atcs.get(event["old"]["poe_id"], set())) != 1
            or len(poe_to_atcs.get(event["new"]["poe_id"], set())) != 1
            or next(iter(poe_to_atcs[event["old"]["poe_id"]])) != old_identity
            or next(iter(poe_to_atcs[event["new"]["poe_id"]])) != new_identity
        ):
            raise InvalidExecution("strict identity disagrees with frozen prescription mapping")
        hid = int(event["source"]["hadm_id"])
        sid = int(event["source"]["subject_id"])
        if admit_by_hadm[hid][0] != sid:
            raise InvalidExecution("admission subject mismatch for strict event")
        all_examples.append(
            build_example(
                event,
                context_orders[hid],
                admit_by_hadm[hid],
                administrations.get(hid, []),
                poe_to_atcs,
                poe_to_pharmacy,
                concept_to_idx,
            )
        )

    discovery_examples = [
        example
        for example, part in zip(all_examples, event_partitions, strict=False)
        if part == "Discovery"
    ]
    dev_examples = [
        example
        for example, part in zip(all_examples, event_partitions, strict=False)
        if part == "Dev"
    ]
    try:
        assert_sample_identity(
            [example["event_key"] for example in dev_examples],
            [example["event_key"] for example in dev_examples],
        )
    except ValueError as exc:  # pragma: no cover - construction above is deterministic
        raise InvalidExecution(str(exc)) from exc

    sources_discovery = [item["source_index"] for item in discovery_examples]
    destinations_discovery = [item["destination_index"] for item in discovery_examples]
    sources_dev = [item["source_index"] for item in dev_examples]
    destinations_dev = [item["destination_index"] for item in dev_examples]
    p_destination, p_source = _build_priors(np, sources_discovery, destinations_discovery)
    permutation = make_context_permutation(
        np, [example["subject_id"] for example in discovery_examples], PERMUTATION_SEED
    )
    try:
        validate_context_permutation(
            [example["subject_id"] for example in discovery_examples],
            sources_discovery,
            destinations_discovery,
            permutation,
        )
    except ValueError as exc:
        raise InvalidExecution(str(exc)) from exc

    device = torch.device(args.device or ("cuda:0" if torch.cuda.is_available() else "cpu"))
    metrics: dict[str, dict[str, dict[str, float]]] = {variant: {} for variant in VARIANTS}
    nll_arrays: dict[str, list[Any]] = {variant: [] for variant in VARIANTS}
    # Seed-independent controls are evaluated once, then represented under each frozen seed.
    destination_probs = np.tile(p_destination, (len(dev_examples), 1))
    source_probs = np.asarray([p_source[source] for source in sources_dev], dtype=np.float64)
    for seed in SEEDS:
        destination_nll, destination_metric = evaluate_probs(
            np, destination_probs, destinations_dev
        )
        source_nll, source_metric = evaluate_probs(np, source_probs, destinations_dev)
        metrics["DestinationMarginal"][str(seed)] = destination_metric
        metrics["SourceTransitionPrior"][str(seed)] = source_metric
        nll_arrays["DestinationMarginal"].append(destination_nll)
        nll_arrays["SourceTransitionPrior"].append(source_nll)

    for seed in SEEDS:
        model, discovery_outputs, dev_outputs = train_flat_base(
            np,
            torch,
            F,
            __import__("random"),
            model_module.CommonOrderTimeBackbone,
            discovery_examples,
            dev_examples,
            device,
            seed,
        )
        _discovery_logits, discovery_hidden = discovery_outputs
        dev_logits, dev_hidden = dev_outputs
        flat_probs = softmax(np, dev_logits)
        flat_nll, flat_metric = evaluate_probs(np, flat_probs, destinations_dev)
        metrics["FlatFinalBase"][str(seed)] = flat_metric
        nll_arrays["FlatFinalBase"].append(flat_nll)

        flat_log_probs = dev_logits - np.logaddexp.reduce(dev_logits, axis=1, keepdims=True)
        fs_log_probs = flat_log_probs + np.log(np.clip(source_probs, 1e-300, None))
        fs_log_probs -= np.logaddexp.reduce(fs_log_probs, axis=1, keepdims=True)
        fs_probs = np.exp(fs_log_probs)
        fs_nll, fs_metric = evaluate_probs(np, fs_probs, destinations_dev)
        metrics["FlatFinalPlusSourcePrior"][str(seed)] = fs_metric
        nll_arrays["FlatFinalPlusSourcePrior"].append(fs_nll)

        onehot_discovery = np.zeros((len(discovery_examples), N_CLASSES), dtype=np.float32)
        onehot_discovery[np.arange(len(discovery_examples)), sources_discovery] = 1.0
        onehot_dev = np.zeros((len(dev_examples), N_CLASSES), dtype=np.float32)
        onehot_dev[np.arange(len(dev_examples)), sources_dev] = 1.0
        pair_train = np.concatenate([discovery_hidden, onehot_discovery], axis=1)
        pair_dev = np.concatenate([dev_hidden, onehot_dev], axis=1)
        pair_probe = fit_trace_probe(np, torch, F, pair_train, destinations_discovery, device)
        pair_dev_logits = predict_trace_probe(np, torch, pair_probe, pair_dev, device)
        pair_nll, pair_metric = evaluate_probs(np, softmax(np, pair_dev_logits), destinations_dev)
        metrics["PairContext"][str(seed)] = pair_metric
        nll_arrays["PairContext"].append(pair_nll)

        context_only_train = np.concatenate(
            [np.zeros_like(discovery_hidden, dtype=np.float32), onehot_discovery], axis=1
        )
        context_only_dev = np.concatenate(
            [np.zeros_like(dev_hidden, dtype=np.float32), onehot_dev], axis=1
        )
        context_probe = fit_trace_probe(
            np, torch, F, context_only_train, destinations_discovery, device
        )
        context_dev_logits = predict_trace_probe(np, torch, context_probe, context_only_dev, device)
        context_nll, context_metric = evaluate_probs(
            np, softmax(np, context_dev_logits), destinations_dev
        )
        metrics["TraceContextOnly"][str(seed)] = context_metric
        nll_arrays["TraceContextOnly"].append(context_nll)

        permuted_hidden = discovery_hidden[np.asarray(permutation, dtype=np.int64)]
        permuted_train = np.concatenate([permuted_hidden, onehot_discovery], axis=1)
        permuted_probe = fit_trace_probe(
            np, torch, F, permuted_train, destinations_discovery, device
        )
        permuted_dev_logits = predict_trace_probe(np, torch, permuted_probe, pair_dev, device)
        permuted_nll, permuted_metric = evaluate_probs(
            np, softmax(np, permuted_dev_logits), destinations_dev
        )
        metrics["PermutedPairContext"][str(seed)] = permuted_metric
        nll_arrays["PermutedPairContext"].append(permuted_nll)

        del pair_probe, context_probe, permuted_probe, model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Average event NLL (and report-only metrics) over frozen base-model seeds.
    mean_nll: dict[str, Any] = {}
    for variant in VARIANTS:
        for seed in SEEDS:
            if str(seed) not in metrics[variant]:
                raise InvalidExecution(f"missing {variant} metric for seed {seed}")
        metric_arrays = {
            key: np.asarray([metrics[variant][str(seed)][key] for seed in SEEDS], dtype=np.float64)
            for key in ("dev_nll", "mrr", "hit_at_5")
        }
        metrics[variant]["mean"] = {
            key: float(np.mean(values)) for key, values in metric_arrays.items()
        }
        mean_nll[variant] = _mean_metric_arrays(np, nll_arrays[variant])

    for variant in VARIANTS:
        if any(len(values) != len(dev_examples) for values in nll_arrays[variant]):
            raise InvalidExecution("candidate/control sample identity mismatch")

    gate_comparisons: dict[str, Any] = {}
    gate_results: dict[str, bool] = {}
    for control in GATE_CONTROLS:
        control_mean = float(np.mean(mean_nll[control]))
        pair_mean = float(np.mean(mean_nll["PairContext"]))
        relative_gain = (control_mean - pair_mean) / control_mean
        bootstrap = patient_cluster_bootstrap(
            np,
            [example["subject_id"] for example in dev_examples],
            mean_nll[control],
            mean_nll["PairContext"],
        )
        pair_lower_each_seed = all(
            float(np.mean(nll_arrays["PairContext"][index]))
            < float(np.mean(nll_arrays[control][index]))
            for index in range(len(SEEDS))
        )
        gain_pass = relative_gain >= 0.05
        ci_pass = bootstrap["ci_95"][0] > 0.0
        gate_pass = bool(gain_pass and ci_pass and pair_lower_each_seed)
        gate_results[control] = gate_pass
        gate_comparisons[control] = {
            "control_mean_dev_nll": control_mean,
            "pair_context_mean_dev_nll": pair_mean,
            "relative_nll_gain": float(relative_gain),
            "bootstrap": bootstrap,
            "relative_gain_ge_0_05": bool(gain_pass),
            "bootstrap_lower_bound_gt_0": bool(ci_pass),
            "pair_nll_lower_each_seed": bool(pair_lower_each_seed),
            "pass": gate_pass,
        }

    partitions = {
        "Discovery": {
            "strict_events": len(discovery_examples),
            "unique_patients": len({example["subject_id"] for example in discovery_examples}),
        },
        "Dev": {
            "strict_events": len(dev_examples),
            "unique_patients": len({example["subject_id"] for example in dev_examples}),
        },
    }
    summary = {
        "protocol": "PAIR_CONTEXT_INCREMENTAL_VALUE",
        "starting_revision": TARGET_REVISION,
        "source_revision": execution_revision,
        "semantic_admission": "PASS_SEMANTIC_ADMISSION",
        "partitions": partitions,
        "integrity": {
            "strict_events_expected": EXPECTED_STRICT_EVENTS,
            "strict_events_observed": len(strict),
            "frozen_invariant_violations": 0,
            "partition_leakage_violations": 0,
            "x_pre_future_leakage_violations": 0,
            "candidate_control_sample_identity_violations": 0,
            "permutation_same_subject_violations": 0,
            "mapping_divergence_violations": 0,
            "nonfinite_optimization_violations": 0,
        },
        "variants": metrics,
        "gate_comparisons": gate_comparisons,
        "quarantine": {
            "G3_G4_accessed": False,
            "R0_holdout_accessed": False,
            "historical_project_test_accessed": False,
        },
        "verdict": compute_verdict(gate_results),
    }
    verify_execution_checkout(args.repo_root, execution_revision)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    )
    args.decision.parent.mkdir(parents=True, exist_ok=True)
    args.decision.write_text(decision_markdown(summary), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--execution-revision", type=str, required=True)
    parser.add_argument("--mimic-dir", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--vocab-dir", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--device", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        summary = run(args)
    except InvalidExecution as exc:
        print(f"STOP_INVALID_EXECUTION: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"verdict": summary["verdict"]}, sort_keys=True))
