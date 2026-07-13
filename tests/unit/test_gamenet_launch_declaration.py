from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
LAUNCH_DECLARATION = ROOT / "baselines" / "adapters" / "gamenet" / "launch.toml"


def test_gamenet_launch_declaration_is_pinned_and_controlled() -> None:
    with LAUNCH_DECLARATION.open("rb") as stream:
        declaration = tomllib.load(stream)

    assert declaration == {
        "baseline_id": "gamenet",
        "dataset_id": "mimic-iii-v1.4",
        "full_seeds": [7, 19, 31],
        "mode": "reproduction",
        "required_inputs": ["diagnoses", "procedures", "prescriptions", "ddi"],
        "schema_version": 1,
        "smoke_seed": 0,
        "source_revision": "da695b4fc9390882f3a681c82115e81291ae6380",
        "launch": {
            "gpu_memory_used_mib_lt": 500,
            "gpu_utilization_percent": 0,
            "tmux_session": "medrec-gamenet",
        },
    }
