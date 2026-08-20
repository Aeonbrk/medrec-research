from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from medrec_research.aris_bridge import ArisBridge, ArisRevisionRecord

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _runner(revision: str, *, dirty: bool = False, branch: str = "main"):
    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if command[-2:] == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, f"{branch}\n", "")
        if command[-2:] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(command, 0, " M file\n" if dirty else "", "")
        if command[-3:] == ["rev-parse", "--verify", "HEAD^{commit}"]:
            return subprocess.CompletedProcess(command, 0, f"{revision}\n", "")
        if command[-3:] == ["rev-parse", "--verify", "origin/main^{commit}"]:
            return subprocess.CompletedProcess(command, 0, f"{revision}\n", "")
        raise AssertionError(command)

    return runner


def test_aris_candidate_activates_atomically(tmp_path: Path) -> None:
    repository = tmp_path / "aris"
    (repository / ".git").mkdir(parents=True)
    manifest = tmp_path / "installed-skills-codex.txt"
    manifest.write_text("repo_root\t" + str(repository) + "\n", encoding="utf-8")
    state_path = tmp_path / "aris-revision.json"
    revision = "a" * 40
    bridge = ArisBridge(
        repository,
        state_path,
        manifest_path=manifest,
        clock=lambda: NOW,
        runner=_runner(revision),
    )

    record = bridge.activate()

    assert record.candidate_valid
    assert not record.fallback_used
    assert record.active_revision == revision
    assert ArisRevisionRecord.from_json(state_path.read_text(encoding="utf-8")) == record


def test_invalid_candidate_keeps_last_known_good_and_blocks_activation(tmp_path: Path) -> None:
    repository = tmp_path / "aris"
    (repository / ".git").mkdir(parents=True)
    manifest = tmp_path / "installed-skills-codex.txt"
    manifest.write_text("repo_root\t" + str(repository) + "\n", encoding="utf-8")
    state_path = tmp_path / "aris-revision.json"
    good = "b" * 40
    bridge = ArisBridge(
        repository,
        state_path,
        manifest_path=manifest,
        clock=lambda: NOW,
        runner=_runner(good),
    )
    first = bridge.activate()

    bridge = ArisBridge(
        repository,
        state_path,
        manifest_path=manifest,
        clock=lambda: NOW,
        runner=_runner("c" * 40, dirty=True),
    )
    second = bridge.activate()

    assert first.active_revision == good
    assert not second.candidate_valid
    assert second.fallback_used
    assert second.active_revision is None
    assert second.last_known_good_revision == good
    assert "aris-checkout-dirty" in second.blockers
    assert "aris-candidate-fallback" in second.blockers
