from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_baseline_establish_dry_run():
    cmd = [
        sys.executable,
        "-m",
        "medrec_research.cli",
        "--non-interactive",
        "baseline",
        "establish",
        "safedrug",
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "✓ Team spawned (3 agents)" in res.stdout
    assert "✓ Baseline config validated" in res.stdout
    assert "✓ Execution plan generated" in res.stdout
    assert "→ Would run on 319, but dry-run mode" in res.stdout


def test_cli_idea_discover(tmp_path: Path):
    cmd = [
        sys.executable,
        "-m",
        "medrec_research.cli",
        "--non-interactive",
        "--root",
        str(tmp_path),
        "idea",
        "discover",
        "safedrug",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Phase 2: Discovering Ideas" in res.stdout
    assert "✓ Research Team spawned" in res.stdout


def test_cli_loop_dry_run(tmp_path: Path):
    cmd = [
        sys.executable,
        "-m",
        "medrec_research.cli",
        "--non-interactive",
        "--root",
        str(tmp_path),
        "loop",
        "start",
        "safedrug",
        "--dry-run",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Phase 1: Establishing Baseline" in res.stdout
    assert "[Dry-Run] Phase 1 验收通过" in res.stdout
