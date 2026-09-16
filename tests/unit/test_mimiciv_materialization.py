from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "research"
    / "benchmarks"
    / "mimiciv-medrec"
    / "materialize_mimiciv.py"
)
SPEC = importlib.util.spec_from_file_location("materialize_mimiciv", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ndc_normalization_uses_frozen_542_rule() -> None:
    assert MODULE.normalise_ndc("51079-0073-20") == "51079007320"
    assert MODULE.normalise_ndc("51079007320") == "51079007320"
    assert MODULE.normalise_ndc("0") is None
    assert MODULE.normalise_ndc("") is None


def test_split_role_is_deterministic_and_complete() -> None:
    roles = {MODULE.split_role(str(subject)) for subject in range(1000, 1100)}
    assert roles == {"train", "dev", "test"}
    assert MODULE.split_role("10000032") == MODULE.split_role("10000032")


def test_input_codes_use_explicit_train_vocab_unknown() -> None:
    vocab = {"<UNK>": 0, "ICD9:4019": 1}
    assert MODULE._project_code_tokens(["ICD9:4019", "ICD10:A001"], vocab) == [
        "<UNK>",
        "ICD9:4019",
    ]


def test_serialized_history_audit_rejects_current_visit_history(tmp_path: Path) -> None:
    path = tmp_path / "examples.jsonl"
    valid = {
        "input": {
            "diagnoses": ["ICD9:4019"],
            "procedures": [],
            "history": [
                {
                    "visit_order": 0,
                    "hadm_id": "1",
                    "diagnoses": [],
                    "procedures": [],
                    "medications": ["A01A"],
                }
            ],
        },
        "current_visit_order": 1,
        "provenance": {"current_hadm_id": "2", "history_hadm_ids": ["1"]},
        "target": {"medications": ["A02A"]},
    }
    path.write_text(json.dumps(valid) + "\n", encoding="utf-8")
    audit = MODULE.audit_examples(path)
    assert audit["strict_history_pass"] is True
    assert audit["current_target_not_in_input_pass"] is True

    invalid = dict(valid)
    invalid["provenance"] = {"current_hadm_id": "2", "history_hadm_ids": ["2"]}
    invalid["input"] = dict(valid["input"])
    invalid["input"]["history"] = [dict(valid["input"]["history"][0], hadm_id="2")]
    path.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
    audit = MODULE.audit_examples(path)
    assert audit["strict_history_pass"] is False
