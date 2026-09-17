from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("numpy")
pytest.importorskip("scipy")

ROOT = Path(__file__).resolve().parents[2] / "research" / "prototypes" / "dcpm"
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402
from dcpm import (  # noqa: E402
    MEDICATIONS,
    DCPMModel,
    build_coarse_peer_pool,
)
from summarize_dcpm import summarize  # noqa: E402


def test_coarse_peer_pool_excludes_same_patient_and_is_train_only() -> None:
    train_rows = [
        {
            "diagnoses": [1, 2],
            "procedures": [0],
            "history": [],
            "_patient_id": "p0",
            "_visit_id": "p0:0",
            "_medications": [10, 20],
        },
        {
            "diagnoses": [1, 3],
            "procedures": [0],
            "history": [([1], [0], [10])],
            "_patient_id": "p0",  # same patient as p0:0
            "_visit_id": "p0:1",
            "_medications": [10, 25],
        },
        {
            "diagnoses": [1, 2],
            "procedures": [1],
            "history": [],
            "_patient_id": "p1",
            "_visit_id": "p1:0",
            "_medications": [5, 12],
        },
        {
            "diagnoses": [0, 2],
            "procedures": [0],
            "history": [],
            "_patient_id": "p2",
            "_visit_id": "p2:0",
            "_medications": [0],
        },
    ]

    dev_rows = [
        {
            "diagnoses": [1, 2],
            "procedures": [0],
            "history": [],
            "_patient_id": "p3",
            "_visit_id": "p3:0",
            "_medications": [10],
        },
    ]

    train_peers, dev_peers = build_coarse_peer_pool(
        train_rows,
        dev_rows,
        diagnosis_count=5,
        procedure_count=4,
        medication_count=MEDICATIONS,
        peer_pool_size=2,
    )

    assert train_peers.shape == (4, 2)
    assert dev_peers.shape == (1, 2)

    # For row 0 (p0:0), peer 1 (p0:1) MUST be excluded because it has same patient p0
    assert 1 not in train_peers[0]
    # For row 1 (p0:1), peer 0 (p0:0) MUST be excluded
    assert 0 not in train_peers[1]

    # All dev peers must be valid train indices
    assert all(0 <= idx < 4 for idx in dev_peers[0])


def test_dcpm_exact_parameter_equality() -> None:
    torch.manual_seed(20260921)
    full_model = DCPMModel(5, 4, variant="dcpm", medication_count=MEDICATIONS)
    torch.manual_seed(20260921)
    ctrl_model = DCPMModel(5, 4, variant="shared_precedent", medication_count=MEDICATIONS)

    full_keys = list(full_model.state_dict().keys())
    ctrl_keys = list(ctrl_model.state_dict().keys())
    assert full_keys == ctrl_keys

    full_count = sum(p.numel() for p in full_model.parameters())
    ctrl_count = sum(p.numel() for p in ctrl_model.parameters())
    assert full_count == ctrl_count

    for k in full_keys:
        assert torch.equal(full_model.state_dict()[k], ctrl_model.state_dict()[k])


def test_summarize_dcpm_decision_rules(tmp_path: Path) -> None:
    import json

    path_dcpm = tmp_path / "dcpm_res.json"
    path_ctrl = tmp_path / "ctrl_res.json"

    # Case 1: Kill (delta <= +0.002)
    base_res = {
        "patient_macro_jaccard": 0.5400,
        "patient_macro_f1": 0.6900,
        "patient_macro_prauc": 0.7800,
        "ddi_rate": 0.0700,
        "average_medication_count": 19.5,
    }
    path_ctrl.write_text(json.dumps(base_res), encoding="utf-8")

    dcpm_kill = dict(base_res)
    dcpm_kill["patient_macro_jaccard"] = 0.5415  # delta = +0.0015 <= 0.002
    path_dcpm.write_text(json.dumps(dcpm_kill), encoding="utf-8")
    s_kill = summarize(path_dcpm, path_ctrl)
    assert s_kill["verdict"] == "KILL_DCPM_MECHANISM"

    # Case 2: Meaningful (delta > +0.004)
    dcpm_meaningful = dict(base_res)
    dcpm_meaningful["patient_macro_jaccard"] = 0.5450  # delta = +0.0050 > 0.004
    path_dcpm.write_text(json.dumps(dcpm_meaningful), encoding="utf-8")
    s_mean = summarize(path_dcpm, path_ctrl)
    assert s_mean["verdict"] == "MEANINGFUL_MECHANISM_SIGNAL"

    # Case 3: Strong (delta >= +0.008)
    dcpm_strong = dict(base_res)
    dcpm_strong["patient_macro_jaccard"] = 0.5500  # delta = +0.0100 >= 0.008
    path_dcpm.write_text(json.dumps(dcpm_strong), encoding="utf-8")
    s_strong = summarize(path_dcpm, path_ctrl)
    assert s_strong["verdict"] == "STRONG_MECHANISM_SIGNAL"
