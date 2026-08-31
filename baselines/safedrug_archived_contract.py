#!/usr/bin/env python3
"""Contract constants, adaptation logic, and command building for archived SafeDrug."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIVED_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
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


def checkpoint_directory(work_src: Path, model_name: str) -> Path:
    """Return the checkpoint directory for SafeDrug-family models."""
    return work_src / "saved" / model_name


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


TEST_DECLARATION = (
    "parser.add_argument('--Test', action='store_true', default=True, help=\"test mode\")"
)
TRAIN_DECLARATION = TEST_DECLARATION.replace("default=True", "default=False")
EPOCH_FORMAL = "    EPOCH = 50\n"
EPOCH_SMOKE = "    EPOCH = 1\n"

EXPECTED_COUNTS = {
    "patients": 6_350,
    "visits": 15_032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
REPORTED_PAPER_METADATA = {
    "paper_reported_visits": 14_995,
    "executable_visits": 15_032,
    "difference": 37,
}
EXPECTED_STATISTICS = {
    "diagnoses": {"numerator": 157_970, "max": 128},
    "procedures": {"numerator": 57_778, "max": 50},
    "medications": {"numerator": 171_900, "max": 65},
}
ROUND_PATTERN = re.compile(
    r"DDI Rate:\s*([0-9.]+),\s*Jaccard:\s*([0-9.]+),\s*PRAUC:\s*([0-9.]+),\s*"
    r"AVG_PRC:\s*([0-9.]+),\s*AVG_RECALL:\s*([0-9.]+),\s*AVG_F1:\s*([0-9.]+),\s*"
    r"AVG_MED:\s*([0-9.]+)"
)

CANONICAL_SIX_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ddi_mask_H.pkl",
    "ehr_adj_final.pkl",
    "idx2drug.pkl",
)
REGISTRY_IMPORT_MODULES = (
    "torch",
    "dnc",
    "rdkit",
    "pandas",
    "dill",
    "sklearn",
    "models",
    "util",
)


class ReproductionError(RuntimeError):
    """Raised when an archived reproduction contract is not satisfied."""


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


COMMON_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
)
GATE_INPUTS = (*COMMON_INPUTS, "ddi_mask_H.pkl")
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


def training_command(python: str, adapted_entrypoint: Path, model_name: str) -> list[str]:
    return [python, str(adapted_entrypoint), "--model_name", model_name]


def native_history_path(checkpoint_dir: Path, model_name: str) -> Path:
    """Return the frozen SafeDrug-family history written beside checkpoints."""
    return checkpoint_dir / f"history_{model_name}.pkl"


def test_command(
    python: str,
    original_entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
    *,
    lane_id: str | None = None,
    selection_path: Path | None = None,
) -> list[str]:
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


def finalize_result(
    run_root: Path,
    status: dict[str, Any],
    result: dict[str, Any],
    dispatch_module: Any = None,
) -> None:
    """Publish terminal status before embedding it in result.json."""
    import sys

    mod = (
        dispatch_module
        or sys.modules.get("safedrug_archived_program")
        or sys.modules.get("baselines.safedrug_archived")
        or sys.modules.get("safedrug_archived")
        or sys.modules[__name__]
    )
    do_write_json = getattr(mod, "write_json", write_json)
    do_write_json(run_root / "status.json", status)
    do_write_json(run_root / "result.json", {**result, "status": status})


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
