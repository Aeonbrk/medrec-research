#!/usr/bin/env python3
"""Run one pinned SafeDrug archived Baseline Program lane on 319."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

ARCHIVED_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
TEST_DECLARATION = (
    "parser.add_argument('--Test', action='store_true', default=True, help=\"test mode\")"
)
TRAIN_DECLARATION = TEST_DECLARATION.replace("default=True", "default=False")
EXPECTED_COUNTS = {
    "patients": 6_350,
    "visits": 14_995,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
ROUND_PATTERN = re.compile(
    r"DDI Rate:\s*([0-9.]+),\s*Jaccard:\s*([0-9.]+),\s*PRAUC:\s*([0-9.]+),\s*"
    r"AVG_PRC:\s*([0-9.]+),\s*AVG_RECALL:\s*([0-9.]+),\s*AVG_F1:\s*([0-9.]+),\s*"
    r"AVG_MED:\s*([0-9.]+)"
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


def test_mode_default(source: str) -> bool:
    declarations = {
        TEST_DECLARATION: True,
        TRAIN_DECLARATION: False,
    }
    matches = [value for declaration, value in declarations.items() if declaration in source]
    if len(matches) != 1:
        raise ReproductionError("unable to determine archived --Test default")
    return matches[0]


def count_dataset(records: Any, voc: Any, ddi_adjacency: Any, ddi_mask: Any) -> dict[str, int]:
    """Return paper aggregate counts from already loaded archived values."""
    try:
        ddi_rows, ddi_columns = matrix_shape(ddi_adjacency)
        mask_rows, mask_columns = matrix_shape(ddi_mask)
        medications = len(voc["med_voc"].idx2word)
        counts = {
            "patients": len(records),
            "visits": sum(len(patient) for patient in records),
            "medications": medications,
            "ddi_pairs": sum(
                bool(ddi_adjacency[row][column])
                for row in range(ddi_rows)
                for column in range(row + 1, ddi_columns)
            ),
            "molecular_substructures": mask_columns,
        }
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise ReproductionError("archived dataset values have an invalid structure") from error
    if (ddi_rows, ddi_columns) != (medications, medications):
        raise ReproductionError(
            f"ddi_A_final shape must be {medications} x {medications}, observed "
            f"{ddi_rows} x {ddi_columns}"
        )
    if mask_rows != medications:
        raise ReproductionError(
            f"ddi_mask_H rows must equal medication count {medications}, observed {mask_rows}"
        )
    return counts


def matrix_shape(value: Any) -> tuple[int, int]:
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) == 2:
        return int(shape[0]), int(shape[1])
    rows = len(value)
    columns = len(value[0]) if rows else 0
    if any(len(row) != columns for row in value):
        raise ReproductionError("matrix rows have inconsistent lengths")
    return rows, columns


def require_paper_counts(counts: dict[str, int]) -> None:
    differences = {
        name: {"expected": expected, "observed": counts.get(name)}
        for name, expected in EXPECTED_COUNTS.items()
        if counts.get(name) != expected
    }
    if differences:
        raise ReproductionError(f"archived B0 data gate failed: {json.dumps(differences)}")


def parse_training_log(log_text: str, expected_epochs: int = 50) -> int:
    observed = [int(value) for value in re.findall(r"(?:^|\n)epoch\s+(\d+)\s*-+", log_text)]
    if observed != list(range(1, expected_epochs + 1)):
        raise ReproductionError(
            f"training log must contain exactly epochs 1-{expected_epochs}, observed {observed}"
        )
    best_epochs = [int(value) for value in re.findall(r"best_epoch:\s*(\d+)", log_text)]
    if len(best_epochs) != expected_epochs or not 0 <= best_epochs[-1] < expected_epochs:
        raise ReproductionError("training log has invalid best_epoch evidence")
    return best_epochs[-1]


def select_checkpoint(checkpoint_dir: Path, profile: Profile, best_epoch: int) -> Path:
    matches = [
        path
        for path in checkpoint_dir.iterdir()
        if path.is_file()
        and not path.is_symlink()
        and (match := profile.checkpoint_pattern.fullmatch(path.name))
        and int(match.group(1)) == best_epoch
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"expected one {profile.baseline_id} checkpoint for epoch {best_epoch}, "
            f"observed {[path.name for path in matches]}"
        )
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


def parse_test_log(log_text: str) -> dict[str, Any]:
    rounds = []
    for match in ROUND_PATTERN.finditer(log_text):
        values = [float(value) for value in match.groups()]
        if not all(math.isfinite(value) for value in values):
            raise ReproductionError("test log contains a non-finite metric")
        rounds.append(
            {
                "ddi_rate": values[0],
                "jaccard": values[1],
                "prauc": values[2],
                "avg_precision": values[3],
                "avg_recall": values[4],
                "avg_f1": values[5],
                "avg_medications": values[6],
            }
        )
    if len(rounds) != 10:
        raise ReproductionError(f"expected exactly 10 test rounds, observed {len(rounds)}")
    summary_pairs = re.findall(r"([0-9.]+)\s*\$\\pm\$\s*([0-9.]+)\s*&", log_text)
    if len(summary_pairs) != 5:
        raise ReproductionError(
            f"expected one upstream 5-metric summary, observed {len(summary_pairs)} pairs"
        )
    summary = {}
    for name in ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications"):
        values = [round_data[name] for round_data in rounds]
        mean = sum(values) / len(values)
        summary[name] = {
            "mean": mean,
            "std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
        }
    summary_names = ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications")
    upstream_summary = {
        summary_names[index]: {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(summary_pairs)
    }
    for name, upstream_value in upstream_summary.items():
        harness_value = summary[name]
        maximum_round_value = max(abs(round_data[name]) for round_data in rounds)
        round_precision = (
            5e-5
            if maximum_round_value == 0
            else 0.5 * 10 ** (math.floor(math.log10(maximum_round_value)) - 3)
        )
        tolerance = round_precision + 5e-5 + 1e-12
        if (
            abs(upstream_value["mean"] - harness_value["mean"]) > tolerance
            or abs(upstream_value["std"] - harness_value["std"]) > tolerance
        ):
            raise ReproductionError(f"upstream summary disagrees with parsed rounds for {name}")
    return {
        "test_rounds": rounds,
        "harness_summary": summary,
        "upstream_summary": upstream_summary,
    }


def load_archived_values(data_dir: Path) -> tuple[Any, Any, Any, Any]:
    dill = importlib.import_module("dill")
    values = []
    for name in GATE_INPUTS:
        with (data_dir / name).open("rb") as stream:
            values.append(dill.load(stream))
    return tuple(values)  # type: ignore[return-value]


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def environment_summary() -> dict[str, str]:
    try:
        explicit = subprocess.run(
            ["conda", "list", "--explicit"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to record active Conda environment") from error
    return {
        "conda_explicit_sha256": hashlib.sha256(explicit).hexdigest(),
        "python": sys.version.split()[0],
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize_result(run_root: Path, status: dict[str, Any], result: dict[str, Any]) -> None:
    """Publish terminal status before embedding it in result.json."""
    write_json(run_root / "status.json", status)
    write_json(run_root / "result.json", {**result, "status": status})


def run_logged(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode:
        raise ReproductionError(
            f"command failed with exit code {completed.returncode}: {command[1]}"
        )


def run_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
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

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")
    counts = count_dataset(*load_archived_values(data_dir))
    require_paper_counts(counts)
    environment_identity = environment_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = adapt_training_source(original_source)

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
    adaptation = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "change": {"from": TEST_DECLARATION, "to": TRAIN_DECLARATION},
    }
    write_json(run_root / "adaptation.json", adaptation)
    write_json(
        run_root / "status.json",
        {"state": "running", "stage": "training", "started_at": started_at},
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        run_logged(
            training_command(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_training_log((run_root / "train.log").read_text(errors="replace"))
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch)
        write_json(
            run_root / "status.json",
            {"state": "running", "stage": "testing", "started_at": started_at},
        )
        run_logged(
            test_command(python, original_entrypoint, profile, model_name, checkpoint),
            cwd=work_src,
            env=environment,
            log_path=run_root / "test.log",
        )
        test_data = parse_test_log((run_root / "test.log").read_text(errors="replace"))
        terminal_status = {
            "state": "completed",
            "stage": "terminal",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        finalize_result(
            run_root,
            terminal_status,
            {
                "schema_version": 1,
                "baseline_id": profile.baseline_id,
                "source_revision": ARCHIVED_REVISION,
                "archived_learning_rate": profile.learning_rate,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "checkpoint": {
                    "best_epoch": best_epoch,
                    "sha256": sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                },
                **test_data,
            },
        )
    except Exception:
        write_json(
            run_root / "status.json",
            {
                "state": "failed",
                "stage": "terminal",
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_id", choices=tuple(PROFILES))
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    run_lane(
        profile=profile_for(args.baseline_id),
        upstream_root=args.upstream_root.resolve(),
        data_dir=args.dataset_root.resolve(),
        run_root=args.run_root.resolve(),
        python=args.python,
    )


if __name__ == "__main__":
    main()
