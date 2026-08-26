#!/usr/bin/env python3
"""Contract constants, adaptation logic, and command building for archived SafeDrug."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIVED_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
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
    test_uses_basename: bool = False


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
    ),
    "retain": Profile(
        "retain",
        "Retain.py",
        "Retain",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
        test_uses_basename=True,
    ),
    "leap-safedrug": Profile(
        "leap-safedrug",
        "Leap.py",
        "Leap",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
    ),
}


def profile_for(baseline_id: str) -> Profile:
    try:
        return PROFILES[baseline_id]
    except KeyError as error:
        raise ReproductionError(f"unknown archived baseline '{baseline_id}'") from error


def adapt_training_source(source: str) -> str:
    """Select archived training mode through the only necessary source change."""
    if source.count(TEST_DECLARATION) != 1 or TRAIN_DECLARATION in source:
        raise ReproductionError("archived --Test declaration drifted from audited source")
    adapted = source.replace(TEST_DECLARATION, TRAIN_DECLARATION)
    if adapted.replace(TRAIN_DECLARATION, TEST_DECLARATION) != source:
        raise ReproductionError("training-mode adaptation changed unexpected source bytes")
    return adapted


def adapt_epoch_source(source: str) -> str:
    """Select one training epoch for non-evidence smoke testing."""
    if source.count(EPOCH_FORMAL) != 1 or EPOCH_SMOKE in source:
        raise ReproductionError("archived EPOCH declaration drifted from audited source")
    adapted = source.replace(EPOCH_FORMAL, EPOCH_SMOKE, 1)
    if adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1) != source:
        raise ReproductionError("epoch adaptation changed unexpected source bytes")
    return adapted


def adapt_smoke_source(source: str) -> str:
    """Compose training-mode and 1-epoch adaptations with joint reversibility."""
    train_adapted = adapt_training_source(source)
    smoke_adapted = adapt_epoch_source(train_adapted)
    reversed_source = smoke_adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1).replace(
        TRAIN_DECLARATION, TEST_DECLARATION
    )
    if reversed_source != source:
        raise ReproductionError("smoke adaptation composition is not reversible to original bytes")
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


def test_command(
    python: str,
    original_entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
) -> list[str]:
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
