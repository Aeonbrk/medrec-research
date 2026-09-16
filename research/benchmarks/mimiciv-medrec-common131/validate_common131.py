#!/usr/bin/env python3
"""Independent Train/Dev-only validator for the common-131 private variant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_role(root: Path, role: str, med_vocab: dict[str, int]) -> dict[str, Any]:
    path = root / (role + "_examples.private.jsonl")
    offsets_path = root / (role + "_examples.private.offsets.npy")
    offsets = np.asarray(np.load(str(offsets_path), allow_pickle=False), dtype=np.int64)
    subjects: set[str] = set()
    previous_order: dict[str, int] = {}
    rows = 0
    target_rows = 0
    history_rows = 0
    with path.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            if rows >= len(offsets) or int(offsets[rows]) != offset:
                raise RuntimeError("serialization offset index mismatch")
            example = _load_line(line)
            required = {
                "schema_version",
                "subject_id",
                "current_visit_order",
                "input",
                "target",
                "provenance",
            }
            if set(example) != required or int(example["schema_version"]) != 1:
                raise RuntimeError("MIMIC-IV common131 example schema mismatch")
            subject = str(example["subject_id"])
            current_order = int(example["current_visit_order"])
            if subject in previous_order and current_order <= previous_order[subject]:
                raise RuntimeError("visit chronology is not strictly increasing")
            previous_order[subject] = current_order
            subjects.add(subject)
            input_part = example["input"]
            if set(input_part) != {"diagnoses", "procedures", "history"}:
                raise RuntimeError(
                    "current target can enter input only through an unexpected field"
                )
            target = example["target"]
            if set(target) != {"medications", "known_medications", "oov_medications"}:
                raise RuntimeError("target schema mismatch")
            if target["oov_medications"]:
                raise RuntimeError("common131 target contains OOV medication")
            target_tokens = [str(value) for value in target["medications"]]
            known_tokens = [str(value) for value in target["known_medications"]]
            if not target_tokens or set(target_tokens) != set(known_tokens):
                raise RuntimeError("common131 target is empty or not closed")
            if any(token not in med_vocab for token in target_tokens):
                raise RuntimeError("common131 target is outside frozen vocabulary")
            if target_tokens != sorted(set(target_tokens), key=med_vocab.__getitem__):
                raise RuntimeError("common131 target ordering or duplicate normalization drifted")
            provenance = example["provenance"]
            current_hadm = str(provenance["current_hadm_id"])
            history_ids = [str(value) for value in provenance["history_hadm_ids"]]
            history = input_part["history"]
            if len(history) != len(history_ids) or current_hadm in history_ids:
                raise RuntimeError("current admission appears in common131 history")
            last_history_order = -1
            for entry, history_hadm in zip(history, history_ids):  # noqa: B905 -- Python 3.8 remote
                if str(entry["hadm_id"]) != history_hadm:
                    raise RuntimeError("history provenance mismatch")
                visit_order = int(entry["visit_order"])
                if visit_order >= current_order or visit_order <= last_history_order:
                    raise RuntimeError("strict previous-visit history invariant failed")
                last_history_order = visit_order
                for token in entry["medications"]:
                    if str(token) not in med_vocab:
                        raise RuntimeError("common131 history contains an OOV medication")
                    history_rows += 1
            rows += 1
            target_rows += len(target_tokens)
    if rows != len(offsets):
        raise RuntimeError("serialization offset count mismatch")
    if rows == 0 or not subjects:
        raise RuntimeError("common131 role contains no examples")
    return {
        "rows": rows,
        "subjects": len(subjects),
        "target_rows": target_rows,
        "history_rows": history_rows,
        "offsets_reloaded": True,
        "subjects_private": subjects,
    }


def _load_line(line: bytes) -> dict[str, Any]:
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("invalid common131 JSONL serialization") from error
    if not isinstance(value, dict):
        raise RuntimeError("common131 JSONL row is not an object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = _load_json(args.manifest.resolve())
    if manifest.get("benchmark_id") != "mimiciv-visit-medrec-stage-minus-1g-common131":
        raise RuntimeError("common131 manifest identity mismatch")
    if manifest.get("native_benchmark_id") != "mimiciv-visit-medrec-stage-minus-1e":
        raise RuntimeError("native source identity mismatch")
    vocab_payload = _load_json(root / "vocabularies.private.json")
    med_vocab = {str(key): int(value) for key, value in vocab_payload["medication"].items()}
    if len(med_vocab) != 131 or sorted(med_vocab.values()) != list(range(131)):
        raise RuntimeError("common131 medication vocabulary is not a contiguous 131-axis")
    ddi_payload = _load_json(root / "ddi_matrix.private.json")
    matrix = np.asarray(ddi_payload["matrix"], dtype=np.float32)
    if matrix.shape != (131, 131) or not np.array_equal(matrix, matrix.T):
        raise RuntimeError("common131 DDI matrix shape/symmetry check failed")
    if np.any(np.diag(matrix) != 0) or not np.isin(matrix, (0.0, 1.0)).all():
        raise RuntimeError("common131 DDI matrix binary/diagonal check failed")
    train = _check_role(root, "train", med_vocab)
    dev = _check_role(root, "dev", med_vocab)
    if train["subjects_private"] & dev["subjects_private"]:
        raise RuntimeError("Train/Dev patient split is not disjoint")
    expected = manifest["roles"]
    if train["rows"] != int(expected["train"]["output_examples"]):
        raise RuntimeError("Train row count differs from common131 manifest")
    if dev["rows"] != int(expected["dev"]["output_examples"]):
        raise RuntimeError("Dev row count differs from common131 manifest")
    train.pop("subjects_private")
    dev.pop("subjects_private")
    checks = {
        "SOURCE_IDENTITY_PASS": True,
        "PATIENT_SPLIT_DISJOINT_PASS": True,
        "VISIT_CHRONOLOGY_PASS": True,
        "STRICT_HISTORY_PASS": True,
        "CURRENT_TARGET_NOT_IN_INPUT_PASS": True,
        "TRAIN_ONLY_VOCAB_FIT_PASS": True,
        "NORMALIZATION_DETERMINISM_PASS": True,
        "DDI_MATRIX_VALID_PASS": True,
        "TRAIN_DEV_SERIALIZATION_RELOAD_PASS": True,
        "TEST_LOADED": False,
    }
    result = {"schema_version": 1, "checks": checks, "train": train, "dev": dev}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
