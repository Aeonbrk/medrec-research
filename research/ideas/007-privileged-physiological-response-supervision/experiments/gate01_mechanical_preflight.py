"""Gate 01 P1 mechanical response-support preflight for Idea 007.

This module deliberately stops at frozen linkage/support evidence.  It reuses the
repository's established MIMIC-IV order-time loader for medication normalization,
POE/eMAR linkage, and the non-overlapping ten-minute positive-order burst task,
then adds only the Idea-007 patient split, focal-event administration anchor, and
six-channel physiology tensor/mask support calculation.

The restricted runner keeps patient identifiers and raw measurements in memory on
the execution host.  Its JSON output contains aggregate counts and ratios only.
It never constructs a model, reads recommendation outcomes, or accesses any
quarantined partition.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import tempfile
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SPLIT_SALT = "idea007-gate01-v1"
R0_SALT = "exposure-reset-20260905"
R0_HOLDOUT_THRESHOLD = 0.85
TARGET_BURST_SECONDS = 10 * 60
ADMIN_WINDOW_SECONDS = 6 * 60 * 60
RESPONSE_WINDOW_SECONDS = 24 * 60 * 60
CHANNELS = (
    "heart_rate",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "respiratory_rate",
    "oxygen_saturation",
    "temperature",
)

# Item order is the source-spec precedence order.  Lower rank wins when two
# admitted source IDs report the same patient/admission/chart-time/channel key.
SOURCE_ITEMS: dict[int, tuple[int, str]] = {
    220045: (0, "heart_rate"),
    220050: (0, "systolic_blood_pressure"),
    220179: (1, "systolic_blood_pressure"),
    220051: (0, "diastolic_blood_pressure"),
    220180: (1, "diastolic_blood_pressure"),
    220210: (0, "respiratory_rate"),
    220277: (0, "oxygen_saturation"),
    223762: (0, "temperature"),
    223761: (1, "temperature"),
}
CHANNEL_INDEX = {name: index for index, name in enumerate(CHANNELS)}

CANONICAL_UNITS = {
    "heart_rate": frozenset({"bpm"}),
    "systolic_blood_pressure": frozenset({"mmhg"}),
    "diastolic_blood_pressure": frozenset({"mmhg"}),
    "respiratory_rate": frozenset({"breaths/min"}),
    "oxygen_saturation": frozenset({"%"}),
}
TEMPERATURE_UNITS = {
    223762: frozenset({"degc", "c"}),
    223761: frozenset({"degf", "f"}),
}

SUPPORT_FLOORS = {
    "global": {
        "E_rec": 10_000,
        "N_A": 5_000,
        "coverage": 0.10,
        "distinct_supported_patients": 500,
        "supported_focal_medications": 20,
        "minimum_supported_events_per_counted_medication": 25,
    },
    "partition": {
        "E_rec": 1_000,
        "N_A": 500,
        "coverage": 0.05,
        "distinct_supported_patients": 100,
        "supported_focal_medications": 10,
        "minimum_supported_events_per_counted_medication": 10,
    },
}

CONCENTRATION_FLOORS = {
    "maximum_medication_share": 0.25,
    "top_5_medication_share": 0.60,
    "maximum_patient_share": 0.01,
    "top_20_patient_share": 0.10,
}


class ProtocolFailure(RuntimeError):
    """Raised when the frozen mechanical input contract is unavailable."""


@dataclass
class FocalExample:
    """One public-task focal positive medication example kept in restricted memory."""

    subject_id: int
    hadm_id: int
    decision_time: int
    focal_medication: str
    order_poe_id: str
    order_pharmacy_ids: frozenset[str]
    partition: str
    anchor_time: int | None = None
    supported: bool = False
    observed_timestamps: set[int] = field(default_factory=set)
    cell_values: dict[tuple[int, int], list[float]] = field(default_factory=dict)
    occupied_cells: int = 0
    valid_values: int = 0


def subject_unit_interval(subject_id: int, salt: str) -> float:
    """Return the frozen deterministic hash interval for one subject."""

    token = f"{subject_id}|{salt}".encode()
    digest = hashlib.sha256(token).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF


def is_r0_holdout(subject_id: int) -> bool:
    """Preserve the existing R0 Holdout quarantine before reading clinical rows."""

    return subject_unit_interval(subject_id, R0_SALT) >= R0_HOLDOUT_THRESHOLD


def classify_gate01(subject_id: int) -> str:
    """Assign the frozen Idea-007 partition from subject identity only."""

    value = subject_unit_interval(subject_id, SPLIT_SALT)
    if value < 0.70:
        return "Gate01-Train"
    if value < 0.85:
        return "Gate01-Dev"
    return "Gate01-Audit"


def right_closed_bin(delta_seconds: int) -> int | None:
    """Map ``(a+(j-1)h, a+jh]`` to zero-based bin ``j-1``."""

    if delta_seconds <= 0 or delta_seconds > RESPONSE_WINDOW_SECONDS:
        return None
    return math.ceil(delta_seconds / 3600) - 1


def normalize_unit(value: Any) -> str:
    """Apply the source-spec case/whitespace-only unit normalization."""

    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def convert_value(item_id: int, value: Any, unit: Any) -> float | None:
    """Validate one admitted source row and convert only Fahrenheit temperature."""

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(converted):
        return None
    channel = SOURCE_ITEMS.get(item_id)
    if channel is None:
        return None
    _, channel_name = channel
    observed_unit = normalize_unit(unit)
    if channel_name == "temperature":
        allowed = TEMPERATURE_UNITS[item_id]
        if observed_unit not in allowed:
            return None
        if item_id == 223761:
            converted = (converted - 32.0) * (5.0 / 9.0)
    elif observed_unit not in CANONICAL_UNITS[channel_name]:
        return None
    return converted if math.isfinite(converted) else None


def median_cells(cell_values: dict[tuple[int, int], list[float]]) -> dict[tuple[int, int], float]:
    """Materialize the frozen within-bin medians without filling missing cells."""

    return {cell: statistics.median(values) for cell, values in cell_values.items() if values}


def support_from_tensor(
    *, observed_timestamps: set[int], cell_values: dict[tuple[int, int], list[float]]
) -> tuple[bool, int, int]:
    """Return ``A(e)``, occupied-cell count, and valid-value count."""

    medians = median_cells(cell_values)
    occupied = len(medians)
    valid_values = sum(len(values) for values in cell_values.values())
    supported = len(observed_timestamps) >= 2 and occupied >= 1
    return supported, occupied, valid_values


def _share_summary(counts: collections.Counter[Any], total: int) -> dict[str, float | None]:
    if total <= 0:
        return {
            "maximum_share": 0.0,
            "top_5_share": 0.0,
            "top_20_share": 0.0,
        }
    ordered = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))
    values = [count for _, count in ordered]
    return {
        "maximum_share": values[0] / total if values else 0.0,
        "top_5_share": sum(values[:5]) / total,
        "top_20_share": sum(values[:20]) / total,
    }


def aggregate_partition(examples: Iterable[FocalExample], scope: str) -> dict[str, Any]:
    """Compute only the frozen public-safe support/concentration aggregates."""

    rows = list(examples)
    supported = [example for example in rows if example.supported]
    medication_counts: collections.Counter[str] = collections.Counter(
        example.focal_medication for example in supported
    )
    patient_counts: collections.Counter[int] = collections.Counter(
        example.subject_id for example in supported
    )
    n_a = len(supported)
    e_rec = len(rows)
    medication_floor = SUPPORT_FLOORS["global" if scope == "global" else "partition"][
        "minimum_supported_events_per_counted_medication"
    ]
    minimum_per_med = min(medication_counts.values(), default=0)
    shares = _share_summary(medication_counts, n_a)
    patient_shares = _share_summary(patient_counts, n_a)
    floors = SUPPORT_FLOORS["global" if scope == "global" else "partition"]
    checks = {
        "E_rec": e_rec >= floors["E_rec"],
        "N_A": n_a >= floors["N_A"],
        "coverage": (n_a / e_rec if e_rec else 0.0) >= floors["coverage"],
        "distinct_supported_patients": len(patient_counts) >= floors["distinct_supported_patients"],
        "supported_focal_medications": len(medication_counts)
        >= floors["supported_focal_medications"],
        "minimum_supported_events_per_counted_medication": (
            minimum_per_med >= medication_floor and bool(medication_counts)
        ),
    }
    concentration_checks = {
        "maximum_medication_share": shares["maximum_share"]
        <= CONCENTRATION_FLOORS["maximum_medication_share"],
        "top_5_medication_share": shares["top_5_share"]
        <= CONCENTRATION_FLOORS["top_5_medication_share"],
        "maximum_patient_share": patient_shares["maximum_share"]
        <= CONCENTRATION_FLOORS["maximum_patient_share"],
        "top_20_patient_share": patient_shares["top_20_share"]
        <= CONCENTRATION_FLOORS["top_20_patient_share"],
    }
    return {
        "E_rec": e_rec,
        "N_A": n_a,
        "coverage": n_a / e_rec if e_rec else 0.0,
        "distinct_supported_patients": len(patient_counts),
        "supported_focal_medications": len(medication_counts),
        "minimum_supported_events_per_counted_medication": minimum_per_med,
        "medications_below_per_medication_floor": sum(
            count < medication_floor for count in medication_counts.values()
        ),
        "medication_concentration": {
            "maximum_share": shares["maximum_share"],
            "top_5_share": shares["top_5_share"],
        },
        "patient_concentration": {
            "maximum_share": patient_shares["maximum_share"],
            "top_20_share": patient_shares["top_20_share"],
        },
        "support_floor_checks": checks,
        "concentration_checks": concentration_checks,
        "pass": all(checks.values()) and all(concentration_checks.values()),
    }


def _load_existing_order_time_module(repo_root: Path) -> Any:
    """Load the existing M0 MIMIC order/eMAR implementation without importing it locally."""

    source = (
        repo_root
        / "research/memory/model-reset-20260908-event-sourced-regimen-editing/run_m0_event_edit_admission.py"
    )
    if not source.exists():
        raise ProtocolFailure(f"Missing existing order-time implementation: {source}")
    spec = importlib.util.spec_from_file_location("medrec_existing_order_time", source)
    if spec is None or spec.loader is None:
        raise ProtocolFailure("Unable to load existing order-time implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_focal_examples(
    helper: Any, mimic_dir: Path, mapping_dir: Path, snapshot_dir: Path
) -> tuple[list[FocalExample], dict[int, tuple[int, int]], dict[str, Any]]:
    """Reuse existing normalization/order-time semantics and materialize E_rec."""

    base_patients, _ = helper.load_patients(mimic_dir)
    allowed_subjects = set(base_patients)
    if not allowed_subjects:
        raise ProtocolFailure("Authorized Gate-01 development pool is empty")
    subjects_by_partition: dict[str, set[int]] = {
        "Gate01-Train": set(),
        "Gate01-Dev": set(),
        "Gate01-Audit": set(),
    }
    for subject_id in allowed_subjects:
        subjects_by_partition[classify_gate01(subject_id)].add(subject_id)
    if any(not subjects for subjects in subjects_by_partition.values()):
        raise ProtocolFailure("Frozen Idea-007 split has an empty partition")
    if set.intersection(*subjects_by_partition.values()):
        raise ProtocolFailure("Frozen Idea-007 partitions overlap")

    vocabulary = helper.load_vocabulary(snapshot_dir)
    vocabulary_set = set(vocabulary)
    concept_to_index = {code: index for index, code in enumerate(vocabulary)}
    mapping = helper.build_ndc_mapping(mapping_dir)
    discovery_subjects = {
        subject_id
        for subject_id in allowed_subjects
        if subject_unit_interval(subject_id, R0_SALT) < 0.70
    }
    consensus = helper.build_formulary_consensus(
        mimic_dir, discovery_subjects, mapping, vocabulary_set
    )
    clinical = helper.load_clinical_records(
        mimic_dir, allowed_subjects, mapping, consensus, vocabulary_set
    )
    hadm_to_admit, hadm_to_poe_events, hadm_to_admins, poe_to_atcs, poe_to_pharms = clinical

    examples: list[FocalExample] = []
    for hadm_id in sorted(hadm_to_poe_events):
        admission = hadm_to_admit.get(hadm_id)
        if admission is None:
            continue
        subject_id, _ = admission
        if subject_id not in allowed_subjects:
            continue
        events = sorted(
            hadm_to_poe_events[hadm_id],
            key=lambda event: (event["ordertime"], str(event["poe_id"])),
        )
        positive_orders = [
            (event, helper.event_concepts(event, poe_to_atcs))
            for event in events
            if event["transaction_type"] in ("New", "Change")
            and helper.event_concepts(event, poe_to_atcs)
        ]
        assigned = [False] * len(positive_orders)
        for index, (base_event, _) in enumerate(positive_orders):
            if assigned[index]:
                continue
            decision_time = int(base_event["ordertime"])
            target_end = decision_time + TARGET_BURST_SECONDS
            focal_orders: dict[str, tuple[dict[str, Any], set[str]]] = {}
            for candidate_index in range(index, len(positive_orders)):
                candidate_event, concepts = positive_orders[candidate_index]
                if int(candidate_event["ordertime"]) >= target_end:
                    break
                assigned[candidate_index] = True
                for medication in sorted(concepts):
                    focal_orders.setdefault(medication, (candidate_event, concepts))
            partition = classify_gate01(subject_id)
            for medication, (event, _) in sorted(focal_orders.items()):
                order_id = str(event["poe_id"])
                examples.append(
                    FocalExample(
                        subject_id=subject_id,
                        hadm_id=hadm_id,
                        decision_time=decision_time,
                        focal_medication=medication,
                        order_poe_id=order_id,
                        order_pharmacy_ids=frozenset(poe_to_pharms.get(order_id, set())),
                        partition=partition,
                    )
                )

    admins_by_hadm = {
        hadm_id: sorted(admins, key=lambda row: (int(row[0]), str(row[1]), str(row[2])))
        for hadm_id, admins in hadm_to_admins.items()
    }
    anchor_count = 0
    for example in examples:
        for chart_time, poe_id, pharmacy_id in admins_by_hadm.get(example.hadm_id, []):
            chart_time = int(chart_time)
            if chart_time <= example.decision_time:
                continue
            if chart_time - example.decision_time > ADMIN_WINDOW_SECONDS:
                break
            if (
                str(poe_id) == example.order_poe_id
                or str(pharmacy_id) in example.order_pharmacy_ids
            ):
                example.anchor_time = chart_time
                anchor_count += 1
                break

    # The assignment has completed before any response-linked aggregate is built.
    if any(example.partition not in subjects_by_partition for example in examples):
        raise ProtocolFailure("Example partition assignment is not one of the frozen partitions")
    metadata = {
        "authorized_subjects": len(allowed_subjects),
        "partition_subjects": {
            partition: len(subjects) for partition, subjects in subjects_by_partition.items()
        },
        "examples": len(examples),
        "examples_with_administration_anchor": anchor_count,
        "candidate_universe_size": len(vocabulary),
        "candidate_universe_identity": "frozen 131 ATC-L4 vocabulary",
        "hadm_to_subject": {
            int(hadm_id): int(subject_id) for hadm_id, (subject_id, _) in hadm_to_admit.items()
        },
        "concept_to_index": concept_to_index,
    }
    return examples, hadm_to_admit, metadata


def _scan_future_physiology(
    helper: Any,
    mimic_dir: Path,
    examples: list[FocalExample],
    hadm_to_admit: dict[int, tuple[int, int]],
) -> dict[str, int]:
    """Stream admitted chartevents and construct the frozen [24,6] support tensor."""

    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - only reached on the restricted host
        raise ProtocolFailure(
            "P1 runtime requires pandas in the declared execution environment"
        ) from exc

    item_ids = set(SOURCE_ITEMS)
    d_items_path = helper.table_path(mimic_dir.parent / "icu", "d_items")
    d_items = pd.read_csv(d_items_path, usecols=["itemid"], compression="infer")
    present_items = {int(item_id) for item_id in d_items["itemid"].dropna().tolist()}
    missing_items = sorted(item_ids - present_items)
    if missing_items:
        raise ProtocolFailure(
            f"Frozen physiology item IDs missing from icu.d_items: {missing_items}"
        )

    events_by_hadm: dict[int, list[int]] = collections.defaultdict(list)
    for index, example in enumerate(examples):
        if example.anchor_time is not None:
            events_by_hadm[example.hadm_id].append(index)
    anchors_by_hadm: dict[int, list[int]] = {}
    indices_by_hadm: dict[int, list[int]] = {}
    for hadm_id, indices in events_by_hadm.items():
        ordered = sorted(indices, key=lambda idx: (int(examples[idx].anchor_time), idx))
        indices_by_hadm[hadm_id] = ordered
        anchors_by_hadm[hadm_id] = [int(examples[idx].anchor_time) for idx in ordered]

    canonical_rows: dict[tuple[int, int, int], list[Any]] = {}
    rows_seen = 0
    valid_rows = 0
    rows_in_windows = 0
    chartevents_path = helper.table_path(mimic_dir.parent / "icu", "chartevents")
    columns = ["subject_id", "hadm_id", "charttime", "itemid", "valuenum", "valueuom"]
    dtype = {
        "subject_id": "Int64",
        "hadm_id": "Int64",
        "charttime": "string",
        "itemid": "Int64",
        "valuenum": "float64",
        "valueuom": "string",
    }
    for chunk in pd.read_csv(
        chartevents_path,
        usecols=columns,
        dtype=dtype,
        compression="infer",
        chunksize=250_000,
        low_memory=False,
    ):
        rows_seen += len(chunk)
        chunk = chunk.loc[chunk["itemid"].isin(item_ids)]
        if chunk.empty:
            continue
        chunk = chunk.loc[chunk["hadm_id"].isin(events_by_hadm)]
        if chunk.empty:
            continue
        parsed_time = pd.to_datetime(chunk["charttime"], errors="coerce", utc=True)
        chunk = chunk.assign(chart_epoch=(parsed_time.astype("int64") // 1_000_000_000))
        chunk = chunk.loc[parsed_time.notna() & chunk["valuenum"].notna()]
        if chunk.empty:
            continue
        for subject_id, hadm_id, _, item_id, value, unit, chart_epoch in chunk[
            ["subject_id", "hadm_id", "charttime", "itemid", "valuenum", "valueuom", "chart_epoch"]
        ].itertuples(index=False, name=None):
            if subject_id is None or hadm_id is None or item_id is None:
                continue
            subject_id = int(subject_id)
            hadm_id = int(hadm_id)
            chart_epoch = int(chart_epoch)
            admission = hadm_to_admit.get(hadm_id)
            if admission is None or int(admission[0]) != subject_id:
                continue
            source = SOURCE_ITEMS.get(int(item_id))
            if source is None:
                continue
            _, channel_name = source
            converted = convert_value(int(item_id), value, unit)
            if converted is None:
                continue
            valid_rows += 1
            anchors = anchors_by_hadm.get(hadm_id)
            ordered_indices = indices_by_hadm.get(hadm_id)
            if not anchors or not ordered_indices:
                continue
            right = bisect_right(anchors, chart_epoch)
            matched: list[int] = []
            for position in range(right - 1, -1, -1):
                anchor = anchors[position]
                delta = chart_epoch - anchor
                if delta > RESPONSE_WINDOW_SECONDS:
                    break
                if delta > 0:
                    matched.append(ordered_indices[position])
            if not matched:
                continue
            rows_in_windows += 1
            row_key = (hadm_id, chart_epoch, CHANNEL_INDEX[channel_name])
            rank = SOURCE_ITEMS[int(item_id)][0]
            existing = canonical_rows.get(row_key)
            if existing is None or rank < existing[0]:
                canonical_rows[row_key] = [rank, [converted], matched]
            elif rank == existing[0]:
                existing[1].append(converted)

    for (_hadm_id, chart_epoch, channel_index), (_, values, matched) in canonical_rows.items():
        for example_index in matched:
            example = examples[example_index]
            bin_index = right_closed_bin(chart_epoch - int(example.anchor_time))
            if bin_index is None:
                continue
            cell = (bin_index, channel_index)
            example.cell_values.setdefault(cell, []).extend(values)
            example.observed_timestamps.add(chart_epoch)

    for example in examples:
        example.supported, example.occupied_cells, example.valid_values = support_from_tensor(
            observed_timestamps=example.observed_timestamps,
            cell_values=example.cell_values,
        )
    return {
        "chartevent_rows_seen": rows_seen,
        "valid_admitted_rows": valid_rows,
        "valid_rows_in_response_windows": rows_in_windows,
        "canonical_source_keys": len(canonical_rows),
        "examples_with_observed_timestamp": sum(
            bool(example.observed_timestamps) for example in examples
        ),
        "examples_with_two_or_more_observed_timestamps": sum(
            len(example.observed_timestamps) >= 2 for example in examples
        ),
        "examples_with_valid_tensor_cell": sum(bool(example.cell_values) for example in examples),
        "supported_examples": sum(example.supported for example in examples),
    }


def run_preflight(
    *, repo_root: Path, mimic_dir: Path, mapping_dir: Path, snapshot_dir: Path, output: Path
) -> dict[str, Any]:
    helper = _load_existing_order_time_module(repo_root)
    examples, hadm_to_admit, metadata = _build_focal_examples(
        helper, mimic_dir, mapping_dir, snapshot_dir
    )
    scan_stats = _scan_future_physiology(helper, mimic_dir, examples, hadm_to_admit)
    global_aggregate = aggregate_partition(examples, "global")
    partition_aggregates = {
        partition: aggregate_partition(
            (example for example in examples if example.partition == partition), "partition"
        )
        for partition in ("Gate01-Train", "Gate01-Dev", "Gate01-Audit")
    }
    passed = global_aggregate["pass"] and all(
        aggregate["pass"] for aggregate in partition_aggregates.values()
    )
    report = {
        "schema_version": "1.0",
        "record_type": "IDEA_007_GATE_01_P1_MECHANICAL_PREFLIGHT",
        "protocol_revision": "v1.2",
        "physiology_source_spec_id": "idea007-gate01-physiology-mimiciv-v1",
        "split_salt": SPLIT_SALT,
        "partition_intervals": {
            "Gate01-Train": "[0.00, 0.70)",
            "Gate01-Dev": "[0.70, 0.85)",
            "Gate01-Audit": "[0.85, 1.00)",
        },
        "access_order": [
            "assign patient partitions",
            "construct existing causal order-time E_rec",
            "link positive eMAR administration anchors",
            "tensorize six-channel future windows and compute A(e)",
            "compute aggregate support and concentration",
        ],
        "authorized_pool_metadata": {
            key: value
            for key, value in metadata.items()
            if key not in {"hadm_to_subject", "concept_to_index"}
        },
        "tensorization": {
            "window": "(a(e), a(e)+24 hours]",
            "bins": "24 one-hour right-closed bins",
            "shape": "[24,6]",
            "aggregation": "within-bin median",
            "interpolation": False,
            "forward_fill": False,
            "back_fill": False,
            "channel_order": list(CHANNELS),
            "scan": scan_stats,
        },
        "global": global_aggregate,
        "partitions": partition_aggregates,
        "verdict": (
            "MECHANICAL_PREFLIGHT_PASS"
            if passed
            else "STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT"
        ),
        "training": "NOT_RUN",
        "recommendation_outcomes_accessed": False,
        "G3_G4_R0_holdout_historical_test_accessed": False,
        "quarantine": "intact",
        "next_owner": "ccf-pipeline-orchestrator",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", delete=False
    ) as handle:
        json.dump(report, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(output)
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--mimic-dir", type=Path, required=True)
    parser.add_argument("--mapping-dir", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_preflight(
        repo_root=args.repo_root,
        mimic_dir=args.mimic_dir,
        mapping_dir=args.mapping_dir,
        snapshot_dir=args.snapshot_dir,
        output=args.output,
    )
    print(json.dumps({"verdict": report["verdict"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
