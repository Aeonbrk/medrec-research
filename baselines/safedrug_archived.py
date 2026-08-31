#!/usr/bin/env python3
"""SafeDrug archived Reproduction Program.

This module is the deep owner of SafeDrug-family baseline lifecycle, source adaptation,
validation, and execution on 319.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

if __package__:
    from .reproduction_artifacts import (
        finalize_v2_pair,
        identity_from_environment,
        reopen_recovered_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )
    from .reproduction_history import (
        load_native_validation_history,
        reconcile_history_checkpoint,
    )
    from .reproduction_runner import (
        read_and_validate_adaptation,
        run_logged,
        run_logged_with_progress,
        validate_identity_binding,
        validate_run_layout,
        write_failure_pair,
        write_json_atomic,
    )
    from .safedrug_archived_data import (
        CANONICAL_SIX_INPUTS,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from .safedrug_archived_logs import (
        ROUND_PATTERN,
        parse_test_log,
        parse_training_log,
        parse_validation_metrics,
        select_checkpoint,
    )
    from .safedrug_archived_probe import (
        REGISTRY_IMPORT_MODULES,
        check_cuda_tensor,
        check_dnc_forward,
        check_imports,
        check_rdkit_brics,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from reproduction_artifacts import (
        finalize_v2_pair,
        identity_from_environment,
        reopen_recovered_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )
    from reproduction_history import (
        load_native_validation_history,
        reconcile_history_checkpoint,
    )
    from reproduction_runner import (
        read_and_validate_adaptation,
        run_logged,
        run_logged_with_progress,
        validate_identity_binding,
        validate_run_layout,
        write_failure_pair,
        write_json_atomic,
    )
    from safedrug_archived_data import (
        CANONICAL_SIX_INPUTS,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from safedrug_archived_logs import (
        ROUND_PATTERN,
        parse_test_log,
        parse_training_log,
        parse_validation_metrics,
        select_checkpoint,
    )
    from safedrug_archived_probe import (
        REGISTRY_IMPORT_MODULES,
        check_cuda_tensor,
        check_dnc_forward,
        check_imports,
        check_rdkit_brics,
        environment_summary,
        probe_environment_details,
        run_probe,
    )

ARCHIVED_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
_MISSING_VALIDATION_METRICS = "training log must contain validation Jaccard and DDI metrics"
_RECOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")

__all__ = (
    "ARCHIVED_REVISION",
    "CANONICAL_SIX_INPUTS",
    "COMMON_INPUTS",
    "EPOCH_FORMAL",
    "EPOCH_SMOKE",
    "EXPECTED_COUNTS",
    "EXPECTED_STATISTICS",
    "GATE_INPUTS",
    "PROFILES",
    "REGISTRY_IMPORT_MODULES",
    "REPORTED_PAPER_METADATA",
    "ROUND_PATTERN",
    "SAFE_DRUG_LANE_IDS",
    "SAFE_DRUG_SELECTION_RULE",
    "TEST_DECLARATION",
    "TRAIN_DECLARATION",
    "Profile",
    "ReproductionError",
    "adapt_epoch_source",
    "adapt_learning_rate_source",
    "adapt_smoke_source",
    "adapt_training_source",
    "build_parser",
    "check_cuda_tensor",
    "check_dnc_forward",
    "check_imports",
    "check_rdkit_brics",
    "checkpoint_directory",
    "count_dataset",
    "environment_summary",
    "execute",
    "load_and_validate_canonical_inputs",
    "main",
    "matrix_shape",
    "native_history_path",
    "parse_test_log",
    "parse_training_log",
    "parse_validation_metrics",
    "probe",
    "probe_environment_details",
    "profile_for",
    "recover_formal_lane",
    "require_executable_counts",
    "require_selected_safedrug_selection",
    "run_formal_lane",
    "run_logged",
    "run_probe",
    "run_smoke_lane",
    "run_test_lane",
    "select_checkpoint",
    "sha256",
    "test_command",
    "test_mode_default",
    "training_command",
    "verify_upstream_source",
    "write_json",
)

SAFE_DRUG_LANE_IDS = (
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
)
SAFE_DRUG_SELECTION_RULE = (
    "maximize validation_jaccard",
    "minimize validation_ddi_rate",
    "minimize learning_rate",
    "minimize lane_id",
)
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RECOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SELECTION_CANDIDATE_FIELDS = {
    "lane_id",
    "learning_rate",
    "checkpoint_identity",
    "validation_jaccard",
    "validation_ddi_rate",
    "training_evidence",
}
_SELECTION_EVIDENCE_FIELDS = {
    "state",
    "artifact_type",
    "identity",
    "learning_rate",
    "best_epoch",
    "validation_jaccard",
    "validation_ddi_rate",
    "checkpoint",
    "recovery",
}
_SELECTION_CHECKPOINT_FIELDS = {"best_epoch", "relative_path", "sha256", "size_bytes"}
RECOVERY_FIELDS = (
    "schema_version",
    "kind",
    "recovery_id",
    "finalizer_revision",
    "source_relative_path",
    "source_terminal_state",
    "source_failure_code",
    "parser_classification",
    "selected_epoch",
    "checkpoint_relative_path",
    "validation_jaccard",
    "validation_ddi_rate",
)

TEST_DECLARATION = (
    "parser.add_argument('--Test', action='store_true', default=True, help=\"test mode\")"
)
TRAIN_DECLARATION = TEST_DECLARATION.replace("default=True", "default=False")
EPOCH_FORMAL = "    EPOCH = 50\n"
EPOCH_SMOKE = "    EPOCH = 1\n"

COMMON_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
)
GATE_INPUTS = (*COMMON_INPUTS, "ddi_mask_H.pkl")


@dataclass(frozen=True)
class Profile:
    baseline_id: str
    entrypoint: str
    model_name: str
    learning_rate: float
    required_inputs: tuple[str, ...]
    checkpoint_pattern: re.Pattern[str]
    scientific_baseline_id: str = ""
    test_uses_basename: bool = False

    def __post_init__(self) -> None:
        if not self.scientific_baseline_id:
            object.__setattr__(
                self,
                "scientific_baseline_id",
                "safedrug" if self.baseline_id.startswith("safedrug") else self.baseline_id,
            )


PROFILES = {
    "gamenet": Profile(
        "gamenet",
        "GAMENet.py",
        "GAMENet",
        1e-4,
        (*COMMON_INPUTS, "ehr_adj_final.pkl"),
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="gamenet",
    ),
    "safedrug": Profile(
        "safedrug",
        "SafeDrug.py",
        "SafeDrug",
        5e-4,
        (
            *COMMON_INPUTS,
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "idx2drug.pkl",
        ),
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="safedrug",
    ),
    "safedrug-lr-1e-5": Profile(
        "safedrug-lr-1e-5",
        "SafeDrug.py",
        "SafeDrug",
        1e-5,
        (
            *COMMON_INPUTS,
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "idx2drug.pkl",
        ),
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="safedrug",
    ),
    "safedrug-lr-1e-4": Profile(
        "safedrug-lr-1e-4",
        "SafeDrug.py",
        "SafeDrug",
        1e-4,
        (
            *COMMON_INPUTS,
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "idx2drug.pkl",
        ),
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="safedrug",
    ),
    "safedrug-lr-5e-4": Profile(
        "safedrug-lr-5e-4",
        "SafeDrug.py",
        "SafeDrug",
        5e-4,
        (
            *COMMON_INPUTS,
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "idx2drug.pkl",
        ),
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="safedrug",
    ),
    "retain": Profile(
        "retain",
        "Retain.py",
        "Retain",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="retain",
        test_uses_basename=True,
    ),
    "leap-safedrug": Profile(
        "leap-safedrug",
        "Leap.py",
        "Leap",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="leap-safedrug",
    ),
}


def profile_for(baseline_id: str) -> Profile:
    try:
        return PROFILES[baseline_id]
    except KeyError as error:
        raise ReproductionError(f"unknown archived baseline '{baseline_id}'") from error


def _fail(message: str, error_type: type[Exception]) -> None:
    raise error_type(message)


def _selection_candidate_for_admission(
    candidate: Mapping[str, Any],
    *,
    error_type: type[Exception],
) -> dict[str, Any]:
    if set(candidate) != _SELECTION_CANDIDATE_FIELDS:
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    lane_id = candidate.get("lane_id")
    if lane_id not in SAFE_DRUG_LANE_IDS:
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    expected_learning_rate = {
        SAFE_DRUG_LANE_IDS[0]: 1e-5,
        SAFE_DRUG_LANE_IDS[1]: 1e-4,
        SAFE_DRUG_LANE_IDS[2]: 5e-4,
    }[lane_id]
    learning_rate = candidate["learning_rate"]
    checkpoint_identity = candidate["checkpoint_identity"]
    if (
        not isinstance(learning_rate, (int, float))
        or isinstance(learning_rate, bool)
        or not math.isfinite(float(learning_rate))
        or float(learning_rate) != expected_learning_rate
        or not isinstance(checkpoint_identity, str)
        or not _SHA256.fullmatch(checkpoint_identity)
    ):
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    normalized_metrics: dict[str, float] = {}
    for metric in ("validation_jaccard", "validation_ddi_rate"):
        value = candidate[metric]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 1
        ):
            _fail("SafeDrug selection.json contains invalid validation evidence", error_type)
        normalized_metrics[metric] = float(value)

    evidence = candidate["training_evidence"]
    if not isinstance(evidence, Mapping) or set(evidence) != _SELECTION_EVIDENCE_FIELDS:
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    if evidence["state"] != "completed" or evidence["artifact_type"] != "training":
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    identity = evidence.get("identity")
    if not isinstance(identity, Mapping):
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    if (
        identity.get("lane_id") != lane_id
        or identity.get("scientific_baseline_id") != "safedrug"
        or identity.get("program_id") != "safedrug-archived"
        or identity.get("profile_id") != "safedrug"
        or identity.get("mode") != "formal"
    ):
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    evidence_learning_rate = evidence["learning_rate"]
    if (
        not isinstance(evidence_learning_rate, (int, float))
        or isinstance(evidence_learning_rate, bool)
        or not math.isfinite(float(evidence_learning_rate))
        or float(evidence_learning_rate) != float(learning_rate)
    ):
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    best_epoch = evidence["best_epoch"]
    if type(best_epoch) is not int or best_epoch < 0:
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    checkpoint = evidence["checkpoint"]
    if not isinstance(checkpoint, Mapping) or set(checkpoint) != _SELECTION_CHECKPOINT_FIELDS:
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    checkpoint_relative_path = checkpoint["relative_path"]
    checkpoint_path = (
        Path(checkpoint_relative_path) if isinstance(checkpoint_relative_path, str) else None
    )
    if (
        type(checkpoint["best_epoch"]) is not int
        or checkpoint["best_epoch"] != best_epoch
        or checkpoint_path is None
        or not checkpoint_relative_path
        or checkpoint_path.is_absolute()
        or ".." in checkpoint_path.parts
        or not isinstance(checkpoint["sha256"], str)
        or not _SHA256.fullmatch(checkpoint["sha256"])
        or checkpoint["sha256"] != checkpoint_identity
        or type(checkpoint["size_bytes"]) is not int
        or checkpoint["size_bytes"] < 0
    ):
        _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    for metric in ("validation_jaccard", "validation_ddi_rate"):
        value = evidence[metric]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0 <= float(value) <= 1
            or float(value) != normalized_metrics[metric]
        ):
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    recovery = evidence["recovery"]
    if recovery is not None:
        if not isinstance(recovery, Mapping) or set(recovery) != set(RECOVERY_FIELDS):
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
        recovery_checkpoint_path = recovery["checkpoint_relative_path"]
        recovery_path = (
            Path(recovery_checkpoint_path) if isinstance(recovery_checkpoint_path, str) else None
        )
        if (
            recovery["schema_version"] != 1
            or recovery["kind"] != "training_finalization_recovery"
            or not isinstance(recovery["recovery_id"], str)
            or not _RECOVERY_ID.fullmatch(recovery["recovery_id"])
            or not isinstance(recovery["finalizer_revision"], str)
            or not _IMMUTABLE_REVISION.fullmatch(recovery["finalizer_revision"])
            or recovery["source_terminal_state"] != "failed"
            or recovery["source_failure_code"] != "training_failed"
            or recovery["parser_classification"] != "validation_metrics_unlabeled"
            or not isinstance(recovery["source_relative_path"], str)
            or not recovery["source_relative_path"]
            or type(recovery["selected_epoch"]) is not int
            or recovery["selected_epoch"] != best_epoch
            or recovery_path is None
            or recovery_path.is_absolute()
            or ".." in recovery_path.parts
            or recovery_checkpoint_path != checkpoint_relative_path
            or recovery["validation_jaccard"] != normalized_metrics["validation_jaccard"]
            or recovery["validation_ddi_rate"] != normalized_metrics["validation_ddi_rate"]
        ):
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
    return {
        "lane_id": lane_id,
        "learning_rate": float(learning_rate),
        "validation_jaccard": normalized_metrics["validation_jaccard"],
        "validation_ddi_rate": normalized_metrics["validation_ddi_rate"],
    }


def require_selected_safedrug_selection(
    selection_path: str | Path | None,
    *,
    lane_id: str,
    error_type: type[Exception] = RuntimeError,
) -> dict[str, Any]:
    """Validate the selector artifact before constructing a SafeDrug test command."""
    if selection_path is None:
        _fail("SafeDrug test admission requires selection.json", error_type)
    path = Path(selection_path)
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"SafeDrug selection.json cannot be read: {error}", error_type)
    if not isinstance(selection, Mapping):
        _fail("SafeDrug selection.json must contain an object", error_type)
    required = {
        "schema_version",
        "kind",
        "state",
        "candidate_lane_ids",
        "candidates",
        "selection_rule",
        "comparison_decisions",
        "selected_lane_id",
        "test_metrics_available",
        "errors",
    }
    if set(selection) != required:
        _fail("SafeDrug selection.json has an invalid schema", error_type)
    if (
        selection["schema_version"] != 1
        or selection["kind"] != "safedrug_selection"
        or selection["state"] != "selection_ready"
        or selection["selected_lane_id"] != lane_id
        or selection["test_metrics_available"] is not False
        or selection["errors"] != []
        or selection["candidate_lane_ids"] != list(SAFE_DRUG_LANE_IDS)
        or selection["selection_rule"] != list(SAFE_DRUG_SELECTION_RULE)
    ):
        _fail("SafeDrug selection.json does not authorize this lane", error_type)
    candidates = selection["candidates"]
    if not isinstance(candidates, list) or len(candidates) != len(SAFE_DRUG_LANE_IDS):
        _fail("SafeDrug selection.json has no evidence for the selected lane", error_type)
    normalized_candidates = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
        normalized_candidates.append(
            _selection_candidate_for_admission(candidate, error_type=error_type)
        )
    if [candidate["lane_id"] for candidate in normalized_candidates] != sorted(SAFE_DRUG_LANE_IDS):
        _fail("SafeDrug selection.json has non-canonical candidate order", error_type)
    if len({candidate["lane_id"] for candidate in normalized_candidates}) != len(
        SAFE_DRUG_LANE_IDS
    ):
        _fail("SafeDrug selection.json has duplicate candidate lanes", error_type)
    ranked = sorted(
        normalized_candidates,
        key=lambda candidate: (
            -candidate["validation_jaccard"],
            candidate["validation_ddi_rate"],
            candidate["learning_rate"],
            candidate["lane_id"],
        ),
    )
    expected_comparison = [
        {
            "rank": rank,
            "lane_id": candidate["lane_id"],
            "validation_jaccard": candidate["validation_jaccard"],
            "validation_ddi_rate": candidate["validation_ddi_rate"],
            "learning_rate": candidate["learning_rate"],
        }
        for rank, candidate in enumerate(ranked, start=1)
    ]
    if selection["comparison_decisions"] != expected_comparison:
        _fail("SafeDrug selection.json contains inconsistent comparison decisions", error_type)
    if selection["selected_lane_id"] != expected_comparison[0]["lane_id"]:
        _fail("SafeDrug selection.json contains an inconsistent winner", error_type)
    return dict(selection)


def _format_lr(lr: float) -> str:
    if lr == 5e-4:
        return "5e-4"
    if lr == 1e-4:
        return "1e-4"
    if lr == 1e-5:
        return "1e-5"
    return f"{lr:g}"


def _lr_literals(lr: float) -> tuple[str, ...]:
    return tuple(dict.fromkeys((_format_lr(lr), str(lr))))


def _find_lr_declaration(source: str, literals: tuple[str, ...]) -> re.Match[str] | None:
    value_pattern = "|".join(re.escape(literal) for literal in literals)
    patterns = (
        re.compile(
            rf"(?m)(?P<prefix>parser\.add_argument\(\s*['\"]--lr['\"][^\n]*?"
            rf"\bdefault\s*=\s*)(?P<value>{value_pattern})"
        ),
        re.compile(rf"(?P<prefix>\blr\s*=\s*)(?P<value>{value_pattern})"),
    )
    matches = [match for pattern in patterns for match in pattern.finditer(source)]
    return matches[0] if len(matches) == 1 else None


def adapt_learning_rate_source(source: str, target_lr: float, original_lr: float = 5e-4) -> str:
    """Adapt the learning rate in training source code with byte-reversibility check."""
    if target_lr == original_lr:
        return source
    target_lr_str = _format_lr(target_lr)
    match = _find_lr_declaration(source, _lr_literals(original_lr))
    if not match:
        if _find_lr_declaration(source, _lr_literals(target_lr)) is not None:
            return source
        raise ReproductionError("archived learning rate declaration drifted from audited source")
    original_literal = match.group("value")
    adapted = source[: match.start("value")] + target_lr_str + source[match.end("value") :]
    if original_literal in adapted or adapted.replace(target_lr_str, original_literal, 1) != source:
        raise ReproductionError("learning rate adaptation is not byte-reversible")
    return adapted


def adapt_training_source(source: str, target_lr: float | None = None) -> str:
    """Select archived training mode and optionally adapt learning rate through audited changes."""
    if source.count(TEST_DECLARATION) != 1 or TRAIN_DECLARATION in source:
        raise ReproductionError("archived --Test declaration drifted from audited source")
    adapted = source.replace(TEST_DECLARATION, TRAIN_DECLARATION)
    if adapted.replace(TRAIN_DECLARATION, TEST_DECLARATION) != source:
        raise ReproductionError("training-mode adaptation changed unexpected source bytes")
    if target_lr is not None and target_lr != 5e-4:
        adapted = adapt_learning_rate_source(adapted, target_lr)
    return adapted


def adapt_epoch_source(source: str) -> str:
    """Select one training epoch for non-evidence smoke testing."""
    if source.count(EPOCH_FORMAL) != 1 or EPOCH_SMOKE in source:
        raise ReproductionError("archived EPOCH declaration drifted from audited source")
    adapted = source.replace(EPOCH_FORMAL, EPOCH_SMOKE, 1)
    if adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1) != source:
        raise ReproductionError("epoch adaptation changed unexpected source bytes")
    return adapted


def adapt_smoke_source(source: str, target_lr: float | None = None) -> str:
    """Compose training-mode and 1-epoch adaptations with joint reversibility."""
    train_adapted = adapt_training_source(source, target_lr=target_lr)
    training_only = source.replace(TEST_DECLARATION, TRAIN_DECLARATION, 1)
    rate_was_adapted = train_adapted != training_only
    smoke_adapted = adapt_epoch_source(train_adapted)
    reversed_epoch = smoke_adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1)
    if rate_was_adapted and target_lr is not None:
        reversed_lr = adapt_learning_rate_source(reversed_epoch, 5e-4, original_lr=target_lr)
    else:
        reversed_lr = reversed_epoch
    reversed_source = reversed_lr.replace(TRAIN_DECLARATION, TEST_DECLARATION)
    if reversed_source != source:
        raise ReproductionError("smoke adaptation is not byte-reversible")
    return smoke_adapted


def test_mode_default(source: str) -> bool:
    declarations = {
        TEST_DECLARATION: True,
        TRAIN_DECLARATION: False,
    }
    matches = [value for declaration, value in declarations.items() if declaration in source]
    if len(matches) != 1:
        raise ReproductionError("unable to determine archived --Test default")
    return matches[0]


def checkpoint_directory(work_src: Path, model_name: str) -> Path:
    """Return the checkpoint directory for SafeDrug-family models."""
    return work_src / "saved" / model_name


def native_history_path(checkpoint_dir: Path, model_name: str) -> Path:
    """Return the frozen SafeDrug-family history written beside checkpoints."""
    return checkpoint_dir / f"history_{model_name}.pkl"


def training_command(python: str, adapted_entrypoint: Path, model_name: str) -> list[str]:
    return [python, str(adapted_entrypoint), "--model_name", model_name]


def test_command(
    python: str,
    original_entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
    *,
    lane_id: str | None = None,
    selection_path: Path | None = None,
    **kwargs: Any,
) -> list[str]:
    del kwargs
    if profile.baseline_id.startswith("safedrug"):
        if lane_id is None:
            raise ReproductionError("SafeDrug test command requires an active lane identity")
        require_selected_safedrug_selection(
            selection_path,
            lane_id=lane_id,
            error_type=ReproductionError,
        )
    resume_path = checkpoint.name if profile.test_uses_basename else str(checkpoint.resolve())
    return [
        python,
        str(original_entrypoint),
        "--model_name",
        model_name,
        "--Test",
        "--resume_path",
        resume_path,
    ]


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _publish_legacy_terminal_status(
    run_root: Path,
    status: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Publish terminal status before embedding it in result.json."""
    write_json(run_root / "status.json", status)
    write_json(run_root / "result.json", {**result, "status": status})


def verify_upstream_source(upstream_root: Path) -> None:
    try:
        observed_revision = subprocess.run(
            ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to verify archived upstream source") from error
    if observed_revision != ARCHIVED_REVISION:
        raise ReproductionError(f"upstream source must be archived@{ARCHIVED_REVISION}")
    try:
        tracked_changes = subprocess.run(
            [
                "git",
                "-C",
                str(upstream_root),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to verify archived upstream cleanliness") from error
    if tracked_changes:
        raise ReproductionError("archived upstream source has tracked modifications")


def run_logged(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        raise ReproductionError(
            f"command failed with exit code {completed.returncode}: {command[1]}"
        )


def _run_legacy_smoke_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    runner: Any = None,
) -> None:
    if run_root.exists():
        raise ReproductionError(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise ReproductionError("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise ReproductionError("run root must be outside archived upstream source")

    active_lr = learning_rate if learning_rate is not None else profile.learning_rate
    verify_upstream_source(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")

    _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    environment_identity = environment_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")

    adapted_source = adapt_smoke_source(original_source, target_lr=active_lr)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    data_link = work_src.parent / "data"
    data_link.symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = work_src / "saved" / model_name
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()

    adaptation: dict[str, Any] = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "training_default": {
            "from": TEST_DECLARATION,
            "to": TRAIN_DECLARATION,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
        "epoch_limit": {
            "from": EPOCH_FORMAL,
            "to": EPOCH_SMOKE,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
    }
    write_json(run_root / "adaptation.json", adaptation)
    write_json(
        run_root / "status.json",
        {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "running",
            "stage": "training",
            "learning_rate": active_lr,
            "started_at": started_at,
            "finished_at": None,
            "failure_code": None,
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    environment["SAFEDRUG_ROOT"] = str(upstream_root)
    run_log = runner or run_logged

    try:
        run_log(
            training_command(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_training_log(
            (run_root / "train.log").read_text(errors="replace"), expected_epochs=1
        )
        if best_epoch != 0:
            raise ReproductionError(f"smoke mode requires best_epoch 0, observed {best_epoch}")
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch=0)
        finished_at = datetime.now(UTC).isoformat()
        terminal_status = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "completed",
            "stage": "terminal",
            "learning_rate": active_lr,
            "started_at": started_at,
            "finished_at": finished_at,
            "failure_code": None,
        }
        write_json(run_root / "status.json", terminal_status)
        smoke_record = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke",
            "non_evidence": True,
            "baseline_id": profile.baseline_id,
            "learning_rate": active_lr,
            "source_revision": ARCHIVED_REVISION,
            "environment_sha256": environment_identity["conda_explicit_sha256"],
            "dataset_counts": counts,
            "epochs_requested": 1,
            "epochs_observed": 1,
            "best_epoch": 0,
            "adaptation": {
                "reverse_verification": "byte-identical",
                "training_default": adaptation["training_default"],
                "epoch_limit": adaptation["epoch_limit"],
            },
            "checkpoint": {
                "best_epoch": 0,
                "sha256": sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
            },
            "status": terminal_status,
        }
        write_json(run_root / "smoke.json", smoke_record)
    except Exception:
        write_json(
            run_root / "status.json",
            {
                "schema_version": 1,
                "kind": "safedrug_archived_smoke_status",
                "state": "failed",
                "stage": "terminal",
                "learning_rate": active_lr,
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "smoke_failed",
            },
        )
        raise


def _run_formal_training(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None,
    identity: Mapping[str, str],
    runner: Any = None,
) -> None:
    validate_run_layout(
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        error_type=ReproductionError,
    )
    validate_identity_binding(
        identity,
        program_id="safedrug-archived",
        source_revision=ARCHIVED_REVISION,
        expected_baseline_id=profile.baseline_id,
        error_type=ReproductionError,
    )
    active_lr = learning_rate if learning_rate is not None else profile.learning_rate
    verify_upstream_source(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("dataset inputs must be regular files, not symlinks")

    records, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    del records
    environment_identity = environment_summary()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise ReproductionError("runtime environment identity does not match controller identity")

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = adapt_training_source(original_source, target_lr=active_lr)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = checkpoint_directory(work_src, model_name)
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()
    adaptation = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "phase": "training",
    }
    write_json_atomic(run_root / "adaptation.json", adaptation)
    write_json_atomic(
        run_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "formal",
            "state": "training",
            "stage": "training",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": False,
            "heartbeat": 0,
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    environment["SAFEDRUG_ROOT"] = str(upstream_root)

    try:
        train_log = run_logged_with_progress(
            command=[
                *training_command(python, adapted_entrypoint, model_name),
                *getattr(profile, "training_args", ()),
            ],
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
            runner=runner,
        )
        best_epoch = parse_training_log(train_log, expected_epochs=50)
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch)
        validation = parse_validation_metrics(train_log)
        finished_at = datetime.now(UTC).isoformat()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=False,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=False,
            payload={
                "artifact_type": "training",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "learning_rate": active_lr,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "epochs_requested": 50,
                "epochs_observed": 50,
                "best_epoch": best_epoch,
                "validation_jaccard": validation["validation_jaccard"],
                "validation_ddi_rate": validation["validation_ddi_rate"],
                "checkpoint": {
                    "best_epoch": best_epoch,
                    "sha256": sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                    "relative_path": str(checkpoint.relative_to(run_root)),
                },
            },
        )
        finalize_v2_pair(run_root, status=status, result=result, error_type=ReproductionError)
    except Exception:
        write_failure_pair(
            root=run_root,
            identity=identity,
            started_at=started_at,
            artifact_type="training",
            error_type=ReproductionError,
        )
        raise


def _run_formal_test(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    identity: Mapping[str, str],
    training_source_root: Path | None = None,
    test_root: Path | None = None,
    selection_path: Path | None = None,
    runner: Any = None,
) -> None:
    if not run_root.is_dir():
        raise ReproductionError(f"training run root not found: {run_root}")
    validate_identity_binding(
        identity,
        program_id="safedrug-archived",
        source_revision=ARCHIVED_REVISION,
        expected_baseline_id=profile.baseline_id,
        error_type=ReproductionError,
    )
    if training_source_root is None:
        checkpoint_root = run_root
        training_status, training_result = reopen_v2_pair(
            run_root,
            expected_identity=identity,
            error_type=ReproductionError,
        )
    else:
        checkpoint_root = training_source_root
        training_status, training_result = reopen_recovered_v2_pair(
            training_source_root,
            run_root,
            error_type=ReproductionError,
        )
        training_identity = training_result["identity"]
        validate_identity_binding(
            training_identity,
            program_id="safedrug-archived",
            source_revision=ARCHIVED_REVISION,
            expected_baseline_id=profile.baseline_id,
            error_type=ReproductionError,
        )
        shared_fields = (
            "attempt_id",
            "lane_id",
            "scientific_baseline_id",
            "program_id",
            "profile_id",
            "model_source_revision",
            "preprocessing_revision",
            "snapshot_id",
            "environment_sha256",
            "mode",
        )
        if any(training_identity[field] != identity[field] for field in shared_fields):
            raise ReproductionError("test identity does not continue the recovered training lane")
    if (
        training_status["state"] != "completed"
        or training_result.get("artifact_type") != "training"
    ):
        raise ReproductionError("test admission requires a completed training artifact")

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("dataset inputs must be regular files, not symlinks")
    verify_upstream_source(upstream_root)

    checkpoint_data = training_result.get("checkpoint")
    relative_path = (
        checkpoint_data.get("relative_path") if isinstance(checkpoint_data, Mapping) else None
    )
    if (
        not isinstance(relative_path, str)
        or Path(relative_path).is_absolute()
        or ".." in Path(relative_path).parts
    ):
        raise ReproductionError("training artifact has an invalid checkpoint path")
    checkpoint = checkpoint_root / relative_path
    if not checkpoint.is_file() or checkpoint.is_symlink():
        raise ReproductionError("training checkpoint is missing or is not a regular file")
    if sha256(checkpoint) != checkpoint_data.get("sha256"):
        raise ReproductionError("training checkpoint identity does not match its artifact")

    test_destination = test_root or run_root / "test"
    if test_destination.exists():
        raise ReproductionError(f"test run root already exists: {test_destination}")
    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    model_root = training_source_root or run_root
    model_name = f"{profile.model_name}_{model_root.name}"
    test_destination.mkdir(parents=True)
    work_src = test_destination / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)
    if profile.test_uses_basename:
        staged_checkpoint = work_src / "saved" / model_name / checkpoint.name
        staged_checkpoint.parent.mkdir(parents=True)
        staged_checkpoint.symlink_to(checkpoint.resolve())
    started_at = datetime.now(UTC).isoformat()
    write_json_atomic(
        test_destination / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "formal",
            "state": "testing",
            "stage": "testing",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": False,
        },
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    environment["SAFEDRUG_ROOT"] = str(upstream_root)
    try:
        command = test_command(
            python,
            original_entrypoint,
            profile,
            model_name,
            checkpoint,
            lane_id=identity["lane_id"],
            selection_path=selection_path,
        )
        command = [*command, *getattr(profile, "training_args", ())]
        execute_fn = runner or run_logged
        execute_fn(
            command,
            cwd=work_src,
            env=environment,
            log_path=test_destination / "test.log",
        )
        parsed = parse_test_log((test_destination / "test.log").read_text(errors="replace"))
        rounds = parsed.get("rounds", parsed.get("test_rounds"))
        summary = parsed.get("harness_summary")
        if not isinstance(rounds, list) or len(rounds) != 10:
            raise ReproductionError("formal test parser did not produce exactly ten rounds")
        if not isinstance(summary, Mapping) or len(summary) != 5:
            raise ReproductionError("formal test parser did not produce five summary metrics")
        environment_identity = environment_summary()
        if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
            raise ReproductionError(
                "runtime environment identity does not match controller identity"
            )
        finished_at = datetime.now(UTC).isoformat()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=False,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=False,
            payload={
                "artifact_type": "test",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "dataset_counts": training_result["dataset_counts"],
                "environment": environment_identity,
                "epochs_requested": training_result["epochs_requested"],
                "epochs_observed": training_result["epochs_observed"],
                "checkpoint": checkpoint_data,
                "rounds": rounds,
                "harness_summary": dict(summary),
                "upstream_summary": parsed.get("upstream_summary"),
            },
        )
        finalize_v2_pair(
            test_destination, status=status, result=result, error_type=ReproductionError
        )
    except Exception:
        write_failure_pair(
            root=test_destination,
            identity=identity,
            started_at=started_at,
            artifact_type="test",
            error_type=ReproductionError,
        )
        raise


def _run_recovery(
    *,
    profile: Profile,
    data_dir: Path,
    run_root: Path,
    recovery_id: str,
    finalizer_revision: str,
    identity: Mapping[str, str],
) -> Path:
    if not _RECOVERY_ID.fullmatch(recovery_id) or recovery_id in (".", ".."):
        raise ReproductionError("recovery ID is invalid")
    if not _IMMUTABLE_REVISION.fullmatch(finalizer_revision):
        raise ReproductionError("finalizer revision must be an immutable Git revision")
    validate_identity_binding(
        identity,
        program_id="safedrug-archived",
        source_revision=ARCHIVED_REVISION,
        expected_baseline_id=profile.baseline_id,
        error_type=ReproductionError,
    )
    recovery_root = run_root / "recoveries" / recovery_id
    if recovery_root.exists():
        raise ReproductionError(f"recovery root already exists: {recovery_root}")

    source_status, source_result = reopen_v2_pair(
        run_root,
        expected_identity=identity,
        error_type=ReproductionError,
    )
    if (
        source_status.get("state") != "failed"
        or source_status.get("failure_code") != "training_failed"
        or source_result.get("artifact_type") != "training"
        or source_result.get("failure_code") != "training_failed"
    ):
        raise ReproductionError("source pair is not an eligible terminal training failure")

    try:
        train_log = (run_root / "train.log").read_text(errors="replace")
    except OSError as error:
        raise ReproductionError("source training log cannot be read") from error
    parse_training_log(train_log, expected_epochs=50)
    try:
        parse_validation_metrics(train_log)
    except ReproductionError as error:
        if str(error) != _MISSING_VALIDATION_METRICS:
            raise ReproductionError("source parser failure is not recoverable") from error
    else:
        raise ReproductionError(
            "source validation parser does not reproduce the recoverable failure"
        )

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("dataset inputs must be regular files, not symlinks")
    records, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    del records
    environment_identity = environment_summary()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise ReproductionError("runtime environment identity does not match controller identity")

    adaptation = read_and_validate_adaptation(
        run_root,
        entrypoint=profile.entrypoint,
        source_revision=ARCHIVED_REVISION,
        calc_sha256=sha256,
        error_type=ReproductionError,
    )
    learning_rate = adaptation["learning_rate"]

    model_name = f"{profile.model_name}_{run_root.name}"
    work_src = run_root / "work" / "src"
    checkpoint_dir = checkpoint_directory(work_src, model_name)
    history_path = native_history_path(checkpoint_dir, model_name)
    validation = load_native_validation_history(
        history_path,
        expected_epochs=50,
        error_type=ReproductionError,
    )
    best_epoch = int(validation["best_epoch"])
    checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch)
    reconcile_history_checkpoint(checkpoint, validation, error_type=ReproductionError)
    checkpoint_relative_path = str(checkpoint.relative_to(run_root))
    recovery = {
        "schema_version": 1,
        "kind": "training_finalization_recovery",
        "recovery_id": recovery_id,
        "finalizer_revision": finalizer_revision,
        "source_relative_path": Path(os.path.relpath(run_root, recovery_root)).as_posix(),
        "source_terminal_state": source_status["state"],
        "source_failure_code": source_status["failure_code"],
        "parser_classification": "validation_metrics_unlabeled",
        "selected_epoch": best_epoch,
        "checkpoint_relative_path": checkpoint_relative_path,
        "validation_jaccard": validation["validation_jaccard"],
        "validation_ddi_rate": validation["validation_ddi_rate"],
    }
    started_at = datetime.now(UTC).isoformat()
    status = terminal_status(
        identity,
        state="completed",
        started_at=started_at,
        finished_at=datetime.now(UTC).isoformat(),
        non_evidence=False,
    )
    status["recovery"] = recovery
    result = terminal_result(
        identity,
        state="completed",
        non_evidence=False,
        payload={
            "artifact_type": "training",
            "scientific_baseline_id": identity["scientific_baseline_id"],
            "profile_id": identity["profile_id"],
            "learning_rate": float(learning_rate),
            "dataset_counts": counts,
            "environment": environment_identity,
            "adaptation": adaptation,
            "epochs_requested": 50,
            "epochs_observed": validation["epochs_observed"],
            "best_epoch": best_epoch,
            "validation_jaccard": validation["validation_jaccard"],
            "validation_ddi_rate": validation["validation_ddi_rate"],
            "checkpoint": {
                "best_epoch": best_epoch,
                "sha256": sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
                "relative_path": checkpoint_relative_path,
            },
            "recovery": recovery,
        },
    )
    finalize_v2_pair(recovery_root, status=status, result=result, error_type=ReproductionError)
    reopen_recovered_v2_pair(
        run_root,
        recovery_root,
        expected_identity=identity,
        error_type=ReproductionError,
    )
    return recovery_root


def _run_formal_smoke(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None,
    identity: Mapping[str, str],
    runner: Any = None,
) -> None:
    validate_run_layout(
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        error_type=ReproductionError,
    )
    validate_identity_binding(
        identity,
        program_id="safedrug-archived",
        source_revision=ARCHIVED_REVISION,
        expected_baseline_id=profile.baseline_id,
        error_type=ReproductionError,
    )
    active_lr = learning_rate if learning_rate is not None else profile.learning_rate
    verify_upstream_source(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("dataset inputs must be regular files, not symlinks")

    _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    environment_identity = environment_summary()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise ReproductionError("runtime environment identity does not match controller identity")
    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = adapt_smoke_source(original_source, target_lr=active_lr)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)
    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = checkpoint_directory(work_src, model_name)
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()
    adaptation = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "phase": "smoke",
    }
    write_json_atomic(run_root / "adaptation.json", adaptation)
    write_json_atomic(
        run_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "smoke",
            "state": "training",
            "stage": "training",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": True,
            "heartbeat": 0,
        },
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    environment["SAFEDRUG_ROOT"] = str(upstream_root)
    try:
        train_log = run_logged_with_progress(
            command=[
                *training_command(python, adapted_entrypoint, model_name),
                *getattr(profile, "training_args", ()),
            ],
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
            runner=runner,
        )
        best_epoch = parse_training_log(train_log, expected_epochs=1)
        if best_epoch != 0:
            raise ReproductionError(f"smoke mode requires best_epoch 0, observed {best_epoch}")
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch)
        finished_at = datetime.now(UTC).isoformat()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=True,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=True,
            payload={
                "artifact_type": "smoke",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "learning_rate": active_lr,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "epochs_requested": 1,
                "epochs_observed": 1,
                "best_epoch": 0,
                "checkpoint": {
                    "best_epoch": 0,
                    "sha256": sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                    "relative_path": str(checkpoint.relative_to(run_root)),
                },
            },
        )
        finalize_v2_pair(run_root, status=status, result=result, error_type=ReproductionError)
    except Exception:
        write_failure_pair(
            root=run_root,
            identity=identity,
            started_at=started_at,
            artifact_type="smoke",
            error_type=ReproductionError,
            non_evidence=True,
        )
        raise


def run_formal_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    phase: str = "training",
    selection_path: Path | None = None,
    training_source_root: Path | None = None,
    test_root: Path | None = None,
    runner: Any = None,
) -> None:
    """Run the controller-identified training or serial test phase."""
    if phase not in ("training", "test"):
        raise ReproductionError("formal phase must be 'training' or 'test'")
    identity = identity_from_environment(mode="formal", error_type=ReproductionError)
    if identity is None:
        raise ReproductionError("formal execution requires a controller-issued v2 identity")
    if phase == "training":
        _run_formal_training(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            identity=identity,
            runner=runner,
        )
    else:
        _run_formal_test(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            identity=identity,
            selection_path=selection_path,
            training_source_root=training_source_root,
            test_root=test_root,
            runner=runner,
        )


def run_test_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    selection_path: Path | None = None,
    runner: Any = None,
) -> None:
    """Run the test phase against a finalized training lane."""
    run_formal_lane(
        profile=profile,
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        python=python,
        phase="test",
        selection_path=selection_path,
        runner=runner,
    )


def recover_formal_lane(
    *,
    profile: Profile,
    data_dir: Path,
    run_root: Path,
    recovery_id: str,
    finalizer_revision: str,
) -> Path:
    """Recover one controller-identified terminal training finalization failure."""
    identity = identity_from_environment(mode="formal", error_type=ReproductionError)
    if identity is None:
        raise ReproductionError("recovery requires a controller-issued v2 identity")
    return _run_recovery(
        profile=profile,
        data_dir=data_dir,
        run_root=run_root,
        recovery_id=recovery_id,
        finalizer_revision=finalizer_revision,
        identity=identity,
    )


def run_smoke_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    runner: Any = None,
) -> None:
    """Run a v2 controller-identified smoke or the preserved local legacy smoke."""
    identity = identity_from_environment(mode="smoke", error_type=ReproductionError)
    if identity is None:
        return _run_legacy_smoke_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            runner=runner,
        )
    _run_formal_smoke(
        profile=profile,
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        python=python,
        learning_rate=learning_rate,
        identity=identity,
        runner=runner,
    )


def probe(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute a Program-level probe request."""
    baseline_id = str(request["baseline_id"])
    upstream_root = Path(request["upstream_root"])
    data_dir = Path(request["dataset_root"]) if request.get("dataset_root") else None
    scope = str(request.get("scope", "full"))
    return run_probe(
        baseline_id=baseline_id,
        upstream_root=upstream_root,
        data_dir=data_dir,
        scope=scope,
    )


def execute(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute a Program-level reproduction request (smoke, formal, or recovery)."""
    mode = str(request.get("mode", "formal"))
    baseline_id = str(request["baseline_id"])
    upstream_root = Path(request["upstream_root"]) if request.get("upstream_root") else Path(".")
    data_dir = Path(request["dataset_root"])
    run_root = Path(request["run_root"])
    python = str(request.get("python", sys.executable))
    learning_rate = (
        float(request["learning_rate"]) if request.get("learning_rate") is not None else None
    )
    profile = profile_for(baseline_id)

    if mode == "smoke":
        run_smoke_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
        )
        return {"state": "completed", "mode": "smoke", "run_root": str(run_root)}
    elif mode == "formal":
        phase = str(request.get("phase", "training"))
        selection_path = Path(request["selection_path"]) if request.get("selection_path") else None
        training_source_root = (
            Path(request["training_source_root"]) if request.get("training_source_root") else None
        )
        test_root = Path(request["test_root"]) if request.get("test_root") else None
        run_formal_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            phase=phase,
            selection_path=selection_path,
            training_source_root=training_source_root,
            test_root=test_root,
        )
        return {"state": "completed", "mode": "formal", "phase": phase, "run_root": str(run_root)}
    elif mode == "recovery":
        recovery_id = str(request["recovery_id"])
        finalizer_revision = str(request["finalizer_revision"])
        marker_path = recover_formal_lane(
            profile=profile,
            data_dir=data_dir,
            run_root=run_root,
            recovery_id=recovery_id,
            finalizer_revision=finalizer_revision,
        )
        return {"state": "completed", "mode": "recovery", "marker_path": str(marker_path)}
    else:
        raise ReproductionError(f"unknown execution mode '{mode}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SafeDrug archived reproduction program lanes or probe environment on 319."
    )
    parser.add_argument(
        "baseline_id",
        nargs="?",
        default=None,
        choices=sorted(PROFILES.keys()),
        help="Scientific baseline or hyperparameter profile to run",
    )
    parser.add_argument(
        "--baseline-id",
        dest="baseline_id_opt",
        choices=sorted(PROFILES.keys()),
        help="Scientific baseline or hyperparameter profile to run",
    )
    parser.add_argument(
        "--mode",
        choices=["probe", "smoke", "formal"],
        default="formal",
        help="Execution mode: probe environment/dataset, smoke test (1 epoch), or formal lane",
    )
    parser.add_argument(
        "--upstream-root",
        type=Path,
        required=True,
        help="Path to the archived SafeDrug upstream repository",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Path to the prepared dataset directory containing final pickle inputs",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Path to the directory where run outputs, logs, and markers will be written",
    )
    parser.add_argument(
        "--python",
        default="python",
        help="Python executable to invoke for training/testing",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        help="Override the profile default learning rate",
    )
    parser.add_argument(
        "--scope",
        choices=["environment", "full"],
        default="full",
        help="Probe scope (probe mode only)",
    )
    parser.add_argument(
        "--phase",
        choices=["training", "test"],
        default="training",
        help="Formal reproduction phase (formal mode only)",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        help="Path to selection.json artifact (formal test phase only)",
    )
    parser.add_argument(
        "--training-source-root",
        type=Path,
        help="Path to training run root to copy checkpoint from (formal test phase only)",
    )
    parser.add_argument(
        "--test-root",
        type=Path,
        help="Path to test output directory where artifacts will be finalized (formal test phase only)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    baseline_id = args.baseline_id or args.baseline_id_opt
    if not baseline_id:
        parser.error("baseline_id is required")

    if args.mode == "probe":
        result = run_probe(
            baseline_id=baseline_id,
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve() if args.dataset_root else None,
            scope=args.scope,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if args.dataset_root is None:
        parser.error("--dataset-root is required for smoke and formal modes")
    if args.run_root is None:
        parser.error("--run-root is required for smoke and formal modes")

    if args.mode == "smoke":
        run_smoke_lane(
            profile=profile_for(baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
            learning_rate=args.learning_rate,
        )
    else:
        run_formal_lane(
            profile=profile_for(baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
            learning_rate=args.learning_rate,
            phase=args.phase,
            selection_path=args.selection,
            training_source_root=(
                args.training_source_root.resolve() if args.training_source_root else None
            ),
            test_root=args.test_root.resolve() if args.test_root else None,
        )


if __name__ == "__main__":
    main()
