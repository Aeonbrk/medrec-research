#!/usr/bin/env python3
"""Contract definitions and profile specifications for MoleRec Table 1 reproduction."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIVED_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"

REPORTED_PAPER_METADATA = {
    "patients": 6350,
    "visits": 14995,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
EXPECTED_COUNTS = {
    "patients": 6350,
    "visits": 15032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
EXPECTED_STATISTICS = {
    "diagnoses": {"numerator": 157_970, "max": 128},
    "procedures": {"numerator": 57_778, "max": 50},
    "medications": {"numerator": 171_900, "max": 65},
}


TEST_DECLARATION = (
    "    parser.add_argument('--Test', action='store_true', default=True, help=\"test mode\")\n"
)
TRAIN_DECLARATION = (
    "    parser.add_argument('--Test', action='store_true', default=False, help=\"test mode\")\n"
)
EPOCH_FORMAL = "    for epoch in range(EPOCH):\n"
EPOCH_SMOKE = "    for epoch in range(1):\n"
ROUND_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([0-9.]+)\s*$")

REGISTRY_IMPORT_MODULES = (
    "torch",
    "torch_geometric",
    "rdkit",
    "pandas",
    "dill",
    "sklearn",
)
PYG_EXTENSION_MODULES = (
    "torch_scatter",
    "torch_sparse",
    "torch_cluster",
    "torch_spline_conv",
)


class ReproductionError(RuntimeError):
    """Raised when the reproduction harness detects contract or execution divergence."""


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
    "ehr_adj_final.pkl",
    "ddi_mask_H.pkl",
    "substructure_smiles.pkl",
    "idx2SMILES.pkl",
    "idx2drug.pkl",
)
GATE_INPUTS = COMMON_INPUTS

PROFILES = {
    "molerec": Profile(
        "molerec",
        "main.py",
        "MoleRec",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
    ),
    "molerec-embedding": Profile(
        "molerec-embedding",
        "main.py",
        "MoleRec",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
    ),
}


def profile_for(baseline_id: str) -> Profile:
    try:
        return PROFILES[baseline_id]
    except KeyError as error:
        raise ReproductionError(f"unknown MoleRec baseline '{baseline_id}'") from error


def _format_lr(lr: float) -> str:
    if lr == 5e-4:
        return "5e-4"
    if lr == 1e-4:
        return "1e-4"
    if lr == 1e-5:
        return "1e-5"
    return f"{lr:g}"


def adapt_learning_rate_source(source: str, target_lr: float, original_lr: float = 5e-4) -> str:
    """Adapt the learning rate in training source code with byte-reversibility check."""
    if target_lr == original_lr:
        return source
    target_lr_str = _format_lr(target_lr)
    orig_lr_str = _format_lr(original_lr)
    pattern = re.compile(rf"lr\s*=\s*(?:{re.escape(orig_lr_str)}|5e-4|{original_lr})")
    match = pattern.search(source)
    if not match:
        raise ReproductionError("learning rate declaration drifted from audited source")
    match_str = match.group(0)
    replaced_str = re.sub(
        r"(?:5e-4|" + re.escape(orig_lr_str) + r"|" + re.escape(str(original_lr)) + r")",
        target_lr_str,
        match_str,
    )
    adapted = source.replace(match_str, replaced_str, 1)
    if match_str in adapted or adapted.replace(replaced_str, match_str, 1) != source:
        raise ReproductionError("learning rate adaptation is not byte-reversible")
    return adapted


def adapt_training_source(source: str, target_lr: float | None = None) -> str:
    """Select training mode and optionally adapt learning rate through audited changes."""
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
    smoke_adapted = adapt_epoch_source(train_adapted)
    reversed_epoch = smoke_adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1)
    if target_lr is not None and target_lr != 5e-4:
        reversed_lr = adapt_learning_rate_source(reversed_epoch, 5e-4)
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
        raise ReproductionError("source does not match exactly one test-mode declaration")
    return matches[0]


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_result(run_root: Path, status: dict[str, Any], payload: dict[str, Any]) -> None:
    write_json(run_root / "status.json", status)
    payload["status"] = status
    write_json(run_root / "result.json", payload)


def training_command(python: str, entrypoint: Path, model_name: str) -> list[str]:
    return [
        python,
        str(entrypoint),
        "--model_name",
        model_name,
    ]


def test_command(
    python: str,
    entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
) -> list[str]:
    resume_target = checkpoint.name if profile.test_uses_basename else str(checkpoint)
    return [
        python,
        str(entrypoint),
        "--Test",
        "--model_name",
        model_name,
        "--resume_path",
        resume_target,
    ]


def verify_upstream_source(upstream_root: Path) -> None:
    source_dir = upstream_root / "src"
    if not source_dir.is_dir():
        raise ReproductionError(f"archived upstream missing src directory: {source_dir}")
    entrypoints = {profile.entrypoint for profile in PROFILES.values()}
    for entrypoint in entrypoints:
        path = source_dir / entrypoint
        if not path.is_file():
            raise ReproductionError(f"archived upstream missing entrypoint: {path}")
