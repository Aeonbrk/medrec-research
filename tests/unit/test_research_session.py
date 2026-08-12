from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from medrec_research.reproduction_contract import H1Approval, H2Decision
from medrec_research.research_session import ResearchSession, run_remote_preflight

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)


def _probe(*, revision: str, data_root_ready: bool = True) -> str:
    return "\n".join(
        (
            "identity=root",
            "checkout_exists=1",
            f"revision={revision}",
            "checkout_clean=1",
            f"data_root_ready={int(data_root_ready)}",
            "conda_available=1",
            "gpu_count=8",
            "gpu_available=6",
            "disk_free_kib=2147483648",
        )
    )


def test_remote_preflight_falls_back_and_reports_real_blockers() -> None:
    revision = "a" * 40
    calls: list[list[str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 255, "", "private details")
        return subprocess.CompletedProcess(
            command,
            0,
            _probe(revision="b" * 40, data_root_ready=False),
            "",
        )

    preflight = run_remote_preflight(
        local_revision=revision,
        clock=lambda: NOW,
        runner=runner,
    )

    assert preflight.reachable
    assert preflight.fallback_used
    assert preflight.remote_revision == "b" * 40
    assert preflight.blockers == (
        "remote-revision-mismatch",
        "remote-data-root-missing",
        "remote-environment-unverified",
    )
    assert calls[0][-3] == "319-lab"
    assert calls[1][-3] == "319-lab-via-server"
    assert "private" not in json.dumps(preflight.to_dict())


def test_remote_preflight_never_uses_ambient_host_or_command() -> None:
    commands: list[list[str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, "", "")

    preflight = run_remote_preflight(
        local_revision="a" * 40,
        clock=lambda: NOW,
        runner=runner,
        timeout_seconds=1,
    )

    assert preflight.blockers == ("remote-unreachable",)
    assert [command[-3] for command in commands] == ["319-lab", "319-lab-via-server"]
    assert all(command[-2:] == ["sh", "-s"] for command in commands)


def test_remote_preflight_fails_closed_on_malformed_capacity() -> None:
    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        output = _probe(revision="a" * 40).replace("gpu_count=8", f"gpu_count={'9' * 100}")
        return subprocess.CompletedProcess(command, 0, output, "")

    preflight = run_remote_preflight(
        local_revision="a" * 40,
        clock=lambda: NOW,
        runner=runner,
    )

    assert not preflight.reachable
    assert preflight.blockers == ("remote-preflight-invalid",)


def test_h1_and_h2_bind_server_loaded_records(tmp_path: Path) -> None:
    session = ResearchSession(ROOT, clock=lambda: NOW)
    session.runtime = tmp_path
    session.status_path = tmp_path / "project-status.json"
    session.loop_path = tmp_path / "research-loop.json"
    session.preflight_path = tmp_path / "remote-preflight.json"
    session.authority_bundle_path = tmp_path / "authority-bundle.json"
    session.action_request_dir = tmp_path / "action-requests"
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.packet_dir = tmp_path / "packets"
    session.h2_dir = tmp_path / "h2"
    session.packet_dir.mkdir()
    session.h2_dir.mkdir()
    session.action_request_dir.mkdir()
    session.contract_path.write_bytes(
        (ROOT / "fixtures/benchmark/safedrug-batch-h1.json").read_bytes()
    )
    (session.packet_dir / "lane.json").write_bytes(
        (ROOT / "fixtures/benchmark/decision-packet-accepted.json").read_bytes()
    )

    approval = session.create_h1(
        {
            "kind": "h1_input",
            "schema_version": 1,
            "owner": "oian",
            "rationale": "contract reviewed",
        }
    )
    decision = session.create_h2(
        {
            "kind": "h2_input",
            "schema_version": 1,
            "lane_id": "gamenet",
            "researcher": "oian",
            "action": "go",
            "rationale": "evidence accepted",
        }
    )

    assert H1Approval.from_dict(approval).owner == "oian"
    assert H2Decision.from_dict(decision).go_eligible
    assert session.control_state()["h1"]["current"]
