#!/usr/bin/env python3
"""Train-only supportability audit for concept-trajectory patient evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import dill
import numpy as np

PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_PATIENTS = 4233
TRAIN_VISITS = 10489
MODALITIES = ("diag", "proc", "med")

THRESHOLDS = {
    "all_recurrent_occurrence_coverage": 0.30,
    "nonmed_recurrent_occurrence_coverage": 0.20,
    "events_ge3_recurrent_nonmed": 0.50,
    "events_ge5_recurrent_all": 0.50,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean_revision(expected: str) -> None:
    root = _repo_root()
    if _git_revision(root) != expected:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("audit checkout is not clean")


def _validate_snapshot(snapshot: Path) -> Mapping[str, Any]:
    profile_path = _repo_root() / "research" / "benchmarks" / "mimiciii-medrec" / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("profile_id") != PROFILE_ID:
        raise RuntimeError("unexpected MIMIC-III profile")
    benchmark = profile.get("benchmark", {})
    if benchmark.get("source_snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError("unexpected source snapshot identity")
    if snapshot.name != SNAPSHOT_ID:
        raise RuntimeError("snapshot directory name does not match frozen identity")
    records_meta = benchmark.get("source_assets", {}).get("records_final.pkl", {})
    records_path = snapshot / "records_final.pkl"
    if not records_path.is_file() or records_path.is_symlink():
        raise RuntimeError("records_final.pkl missing or symlinked")
    if records_path.stat().st_size != records_meta.get("bytes"):
        raise RuntimeError("records_final.pkl byte size mismatch")
    if _sha256_file(records_path) != records_meta.get("sha256"):
        raise RuntimeError("records_final.pkl sha256 mismatch")
    split = profile.get("split", {}).get("train", {})
    if split.get("patients") != TRAIN_PATIENTS or split.get("visits") != TRAIN_VISITS:
        raise RuntimeError("frozen Train split identity changed")
    return profile


def _dedup(values: Iterable[Any]) -> Tuple[int, ...]:
    return tuple(sorted(set(int(value) for value in values)))


def _visit_codes(admission: Sequence[Any]) -> Dict[str, Tuple[int, ...]]:
    return {
        "diag": _dedup(admission[0]),
        "proc": _dedup(admission[1]),
        "med": _dedup(admission[2]),
    }


def _safe_ratio(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _quantiles(values: Sequence[int]) -> Dict[str, float]:
    if not values:
        return {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "max": 0.0}
    array = np.asarray(values, dtype=np.float64)
    return {
        "p25": float(np.quantile(array, 0.25)),
        "p50": float(np.quantile(array, 0.50)),
        "p75": float(np.quantile(array, 0.75)),
        "p90": float(np.quantile(array, 0.90)),
        "max": float(array.max()),
    }


def audit(records: Sequence[Any]) -> Dict[str, Any]:
    if len(records) != 6350:
        raise RuntimeError("canonical patient count changed")

    visit_total = sum(len(records[index]) for index in range(TRAIN_PATIENTS))
    if visit_total != TRAIN_VISITS:
        raise RuntimeError("canonical Train visit count changed")

    history_events = 0
    patients_with_history_event = 0

    per_modality = {
        modality: {
            "history_occurrences": 0,
            "recurrent_history_occurrences": 0,
            "history_unique_concepts": 0,
            "recurrent_unique_concepts": 0,
            "trajectory_lengths": [],
        }
        for modality in MODALITIES
    }

    all_history_occurrences = 0
    all_recurrent_occurrences = 0
    nonmed_history_occurrences = 0
    nonmed_recurrent_occurrences = 0

    recurrent_all_counts: List[int] = []
    recurrent_nonmed_counts: List[int] = []
    events_ge1_recurrent_all = 0
    events_ge3_recurrent_nonmed = 0
    events_ge5_recurrent_all = 0

    current_nonmed_codes = 0
    current_nonmed_seen_before = 0
    current_diag_codes = 0
    current_diag_seen_before = 0
    current_proc_codes = 0
    current_proc_seen_before = 0

    for patient_index in range(TRAIN_PATIENTS):
        patient = records[patient_index]
        counts = {modality: Counter() for modality in MODALITIES}
        patient_has_history_event = False

        for visit_index, admission in enumerate(patient):
            current = _visit_codes(admission)

            if visit_index > 0:
                patient_has_history_event = True
                history_events += 1

                event_recurrent_all = 0
                event_recurrent_nonmed = 0

                for modality in MODALITIES:
                    counter = counts[modality]
                    occurrence_count = int(sum(counter.values()))
                    recurrent_occurrence_count = int(
                        sum(value for value in counter.values() if value >= 2)
                    )
                    unique_count = len(counter)
                    recurrent_unique_count = sum(1 for value in counter.values() if value >= 2)
                    lengths = [int(value) for value in counter.values() if value >= 2]

                    stats = per_modality[modality]
                    stats["history_occurrences"] += occurrence_count
                    stats["recurrent_history_occurrences"] += recurrent_occurrence_count
                    stats["history_unique_concepts"] += unique_count
                    stats["recurrent_unique_concepts"] += recurrent_unique_count
                    stats["trajectory_lengths"].extend(lengths)

                    all_history_occurrences += occurrence_count
                    all_recurrent_occurrences += recurrent_occurrence_count
                    event_recurrent_all += recurrent_unique_count

                    if modality != "med":
                        nonmed_history_occurrences += occurrence_count
                        nonmed_recurrent_occurrences += recurrent_occurrence_count
                        event_recurrent_nonmed += recurrent_unique_count

                recurrent_all_counts.append(event_recurrent_all)
                recurrent_nonmed_counts.append(event_recurrent_nonmed)
                if event_recurrent_all >= 1:
                    events_ge1_recurrent_all += 1
                if event_recurrent_nonmed >= 3:
                    events_ge3_recurrent_nonmed += 1
                if event_recurrent_all >= 5:
                    events_ge5_recurrent_all += 1

                for code in current["diag"]:
                    current_diag_codes += 1
                    current_nonmed_codes += 1
                    if counts["diag"].get(code, 0) > 0:
                        current_diag_seen_before += 1
                        current_nonmed_seen_before += 1
                for code in current["proc"]:
                    current_proc_codes += 1
                    current_nonmed_codes += 1
                    if counts["proc"].get(code, 0) > 0:
                        current_proc_seen_before += 1
                        current_nonmed_seen_before += 1

            # Only after the current event is audited do current codes become legal history
            # for later visits. Current medication is never inspected as evidence for itself.
            for modality in MODALITIES:
                for code in current[modality]:
                    counts[modality][code] += 1

        if patient_has_history_event:
            patients_with_history_event += 1

    all_cov = _safe_ratio(all_recurrent_occurrences, all_history_occurrences)
    nonmed_cov = _safe_ratio(nonmed_recurrent_occurrences, nonmed_history_occurrences)
    event_nonmed_cov = _safe_ratio(events_ge3_recurrent_nonmed, history_events)
    event_all_cov = _safe_ratio(events_ge5_recurrent_all, history_events)

    conditions = {
        "all_recurrent_occurrence_coverage": all_cov >= THRESHOLDS[
            "all_recurrent_occurrence_coverage"
        ],
        "nonmed_recurrent_occurrence_coverage": nonmed_cov >= THRESHOLDS[
            "nonmed_recurrent_occurrence_coverage"
        ],
        "events_ge3_recurrent_nonmed": event_nonmed_cov >= THRESHOLDS[
            "events_ge3_recurrent_nonmed"
        ],
        "events_ge5_recurrent_all": event_all_cov >= THRESHOLDS[
            "events_ge5_recurrent_all"
        ],
    }
    decision = "SUPPORT_CCTM_PREMISE" if all(conditions.values()) else "KILL_CCTM_SUPPORTABILITY"

    modality_output = {}
    for modality in MODALITIES:
        stats = per_modality[modality]
        modality_output[modality] = {
            "history_occurrences": int(stats["history_occurrences"]),
            "recurrent_history_occurrences": int(stats["recurrent_history_occurrences"]),
            "recurrent_occurrence_coverage": _safe_ratio(
                stats["recurrent_history_occurrences"], stats["history_occurrences"]
            ),
            "history_unique_concepts_event_sum": int(stats["history_unique_concepts"]),
            "recurrent_unique_concepts_event_sum": int(stats["recurrent_unique_concepts"]),
            "recurrent_unique_fraction": _safe_ratio(
                stats["recurrent_unique_concepts"], stats["history_unique_concepts"]
            ),
            "recurrent_trajectory_length_quantiles": _quantiles(stats["trajectory_lengths"]),
        }

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "TRAIN_ONLY_SUPPORTABILITY",
        "profile_id": PROFILE_ID,
        "decision": decision,
        "frozen_thresholds": THRESHOLDS,
        "conditions": conditions,
        "population": {
            "train_patients": TRAIN_PATIENTS,
            "train_visits": TRAIN_VISITS,
            "history_bearing_prediction_events": history_events,
            "patients_with_history_bearing_event": patients_with_history_event,
        },
        "primary": {
            "all_history_occurrences": all_history_occurrences,
            "all_recurrent_occurrences": all_recurrent_occurrences,
            "all_recurrent_occurrence_coverage": all_cov,
            "nonmed_history_occurrences": nonmed_history_occurrences,
            "nonmed_recurrent_occurrences": nonmed_recurrent_occurrences,
            "nonmed_recurrent_occurrence_coverage": nonmed_cov,
            "events_ge3_recurrent_nonmed": events_ge3_recurrent_nonmed,
            "events_ge3_recurrent_nonmed_fraction": event_nonmed_cov,
            "events_ge5_recurrent_all": events_ge5_recurrent_all,
            "events_ge5_recurrent_all_fraction": event_all_cov,
        },
        "supporting": {
            "events_ge1_recurrent_all_fraction": _safe_ratio(
                events_ge1_recurrent_all, history_events
            ),
            "recurrent_all_trajectory_count_quantiles": _quantiles(recurrent_all_counts),
            "recurrent_nonmed_trajectory_count_quantiles": _quantiles(recurrent_nonmed_counts),
            "current_diag_prior_identity_overlap": _safe_ratio(
                current_diag_seen_before, current_diag_codes
            ),
            "current_proc_prior_identity_overlap": _safe_ratio(
                current_proc_seen_before, current_proc_codes
            ),
            "current_nonmed_prior_identity_overlap": _safe_ratio(
                current_nonmed_seen_before, current_nonmed_codes
            ),
            "per_modality": modality_output,
        },
        "privacy": {
            "patient_level_output": False,
            "dev_loaded": False,
            "test_loaded": False,
            "current_medication_used_as_same_event_evidence": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    _require_clean_revision(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    _validate_snapshot(snapshot)
    records = dill.load((snapshot / "records_final.pkl").open("rb"))

    result = audit(records)
    result["source_revision"] = args.source_revision
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
