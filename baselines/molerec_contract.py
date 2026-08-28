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
    "    parser.add_argument('--Test', action='store_true', help=\"evaluating mode\")\n"
)
TRAIN_DECLARATION = TEST_DECLARATION
EPOCH_FORMAL = "        '--epochs', default=50, type=int,\n"
EPOCH_SMOKE = "        '--epochs', default=1, type=int,\n"
ROUND_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([0-9.]+)\s*$")

REGISTRY_IMPORT_MODULES = (
    "torch",
    "torch_geometric",
    "ogb",
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
    training_args: tuple[str, ...] = ()


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
        training_args=("--embedding",),
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
        raise ReproductionError("learning rate declaration drifted from audited source")
    original_literal = match.group("value")
    adapted = source[: match.start("value")] + target_lr_str + source[match.end("value") :]
    if original_literal in adapted or adapted.replace(target_lr_str, original_literal, 1) != source:
        raise ReproductionError("learning rate adaptation is not byte-reversible")
    return adapted


def adapt_training_source(source: str, target_lr: float | None = None) -> str:
    """Validate MoleRec's source-default training mode and adapt its rate."""
    if source.count(TEST_DECLARATION) != 1:
        raise ReproductionError("archived --Test declaration drifted from audited source")
    adapted = source
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
    if source.count(TEST_DECLARATION) != 1:
        raise ReproductionError("source does not match exactly one test-mode declaration")
    return False


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


def native_history_path(checkpoint_dir: Path, model_name: str) -> Path:
    """Return the frozen MoleRec history written beside checkpoints."""
    del model_name
    return checkpoint_dir / "history.pkl"


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
