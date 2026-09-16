from __future__ import annotations

from types import SimpleNamespace

from baselines import armr
from research.prototypes.paper_contract.evaluator import SelectionCandidate


def test_patient_split_matches_frozen_miii_profile() -> None:
    train, dev = armr.patient_split(6350)

    assert len(train) == 4233
    assert len(dev) == 1004
    assert train == tuple(range(4233))
    assert dev[0] >= 4233


def test_model_row_does_not_expose_current_target() -> None:
    row = {
        "diagnoses": [1, 2],
        "procedures": [3],
        "history": [([4], [5], [6])],
        "target": [7, 8],
        "patient_id": "12",
        "visit_id": "12:1",
    }

    assert armr.model_row(row) == {
        "diagnoses": [1, 2],
        "procedures": [3],
        "history": [([4], [5], [6])],
    }


def test_selection_key_prefers_native_threshold_then_earlier_checkpoint() -> None:
    native = SelectionCandidate(4, 0.35, 0.5, 6)
    farther = SelectionCandidate(3, 0.25, 0.5, 4)
    later = SelectionCandidate(5, 0.35, 0.5, 6)

    assert armr._selection_key(native) < armr._selection_key(farther)
    assert armr._selection_key(native) < armr._selection_key(later)


def test_vocabulary_helper_reads_integer_or_string_mapping_keys() -> None:
    values = {index: f"M{index}" for index in range(armr.MEDICATIONS)}
    voc = {"med_voc": SimpleNamespace(idx2word=values)}

    assert armr._vocabulary(voc) == tuple(f"M{index}" for index in range(armr.MEDICATIONS))
