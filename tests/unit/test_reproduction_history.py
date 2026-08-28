from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pytest

from baselines.reproduction_history import (
    load_native_validation_history,
    reconcile_history_checkpoint,
)

HISTORY_KEYS = ("ja", "ddi_rate", "avg_p", "avg_r", "avg_f1", "prauc", "med")


def _history(*, epochs: int = 50) -> dict[str, list[float]]:
    history = {key: [0.1] * epochs for key in HISTORY_KEYS}
    history["ja"] = [0.2] * epochs
    history["ddi_rate"] = [0.08] * epochs
    if epochs == 50:
        history["ja"][17] = 0.512345678901
        history["ja"][31] = 0.512345678901
        history["ddi_rate"][17] = 0.067891234567
    return history


def _write_history(
    path: Path,
    history: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "dill", pickle)
    with path.open("wb") as stream:
        pickle.dump(history, stream)


def test_native_history_preserves_full_precision_and_first_maximum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "history.pkl"
    _write_history(path, _history(), monkeypatch)

    validation = load_native_validation_history(
        path,
        expected_epochs=50,
        error_type=ValueError,
    )

    assert validation == {
        "epochs_observed": 50,
        "best_epoch": 17,
        "validation_jaccard": 0.512345678901,
        "validation_ddi_rate": 0.067891234567,
    }


@pytest.mark.parametrize(
    ("history", "message"),
    [
        (_history(epochs=49), "exactly 50 epochs"),
        ({**_history(), "ja": [float("nan")] * 50}, "finite numeric"),
        ({key: value for key, value in _history().items() if key != "med"}, "exactly"),
    ],
)
def test_native_history_rejects_incomplete_or_malformed_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    history: object,
    message: str,
) -> None:
    path = tmp_path / "history.pkl"
    _write_history(path, history, monkeypatch)

    with pytest.raises(ValueError, match=message):
        load_native_validation_history(path, expected_epochs=50, error_type=ValueError)


def test_checkpoint_cross_check_uses_filename_precision(tmp_path: Path) -> None:
    checkpoint = tmp_path / "Epoch_17_JA_0.5123_DDI_0.0679.model"
    checkpoint.touch()
    validation = {
        "epochs_observed": 50,
        "best_epoch": 17,
        "validation_jaccard": 0.512345678901,
        "validation_ddi_rate": 0.067891234567,
    }

    reconcile_history_checkpoint(checkpoint, validation, error_type=ValueError)

    mismatch = tmp_path / "Epoch_18_JA_0.5123_DDI_0.0679.model"
    mismatch.touch()
    with pytest.raises(ValueError, match="epoch disagrees"):
        reconcile_history_checkpoint(mismatch, validation, error_type=ValueError)

    wrong_metric = tmp_path / "Epoch_17_JA_0.5000_DDI_0.0679.model"
    wrong_metric.touch()
    with pytest.raises(ValueError, match="Jaccard disagrees"):
        reconcile_history_checkpoint(wrong_metric, validation, error_type=ValueError)
