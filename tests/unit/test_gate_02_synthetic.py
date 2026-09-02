from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_gate_02_module():
    gate_02_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "001-tension-guided-verification"
        / "experiments"
        / "run_confidence_sufficiency_gate.py"
    )
    spec = importlib.util.spec_from_file_location("run_confidence_sufficiency_gate", gate_02_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_02_synthetic_critical_paths() -> None:
    module = _load_gate_02_module()
    module.self_test_gate_02()
