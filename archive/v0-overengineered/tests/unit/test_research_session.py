from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from medrec_research.action_gate import ActionRequest
from medrec_research.errors import ProtocolValidationError
from medrec_research.execution_control import ExecutionState
from medrec_research.reproduction_contract import DecisionPacket, H1Approval, H2Decision
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
    session = ResearchSession(ROOT, clock=lambda: NOW, runtime=tmp_path)
    session.status_path = tmp_path / "project-status.json"
    session.loop_path = tmp_path / "research-loop.json"
    session.preflight_path = tmp_path / "remote-preflight.json"
    session.authority_bundle_path = tmp_path / "authority-bundle.json"
    session.action_request_dir = tmp_path / "action-requests"
    session.execution_dir = tmp_path / "executions"
    session.execution_queue = session.execution_queue.__class__(
        session.execution_dir, clock=session.clock
    )
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.packet_dir = tmp_path / "packets"
    session.h2_dir = tmp_path / "h2"
    session.packet_dir.mkdir()
    session.h2_dir.mkdir()
    session.action_request_dir.mkdir()
    session.execution_dir.mkdir()
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
    assert (
        session.create_h1(
            {
                "kind": "h1_input",
                "schema_version": 1,
                "owner": "oian",
                "rationale": "contract reviewed",
            }
        )
        == approval
    )
    with pytest.raises(ProtocolValidationError, match="H1 approval for this contract is immutable"):
        session.create_h1(
            {
                "kind": "h1_input",
                "schema_version": 1,
                "owner": "another-researcher",
                "rationale": "changed authority",
            }
        )


def test_allowed_request_binds_registered_declaration_and_stays_blocked(
    tmp_path: Path,
) -> None:
    session = ResearchSession(ROOT, clock=lambda: NOW, runtime=tmp_path)
    session.status_path = tmp_path / "project-status.json"
    session.loop_path = tmp_path / "research-loop.json"
    session.preflight_path = tmp_path / "remote-preflight.json"
    session.authority_bundle_path = tmp_path / "authority-bundle.json"
    session.action_request_dir = tmp_path / "action-requests"
    session.execution_dir = tmp_path / "executions"
    session.execution_queue = session.execution_queue.__class__(
        session.execution_dir, clock=session.clock
    )
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.packet_dir = tmp_path / "packets"
    session.h2_dir = tmp_path / "h2"
    session.packet_dir.mkdir()
    session.h2_dir.mkdir()
    session.action_request_dir.mkdir()
    session.execution_dir.mkdir()
    session.contract_path.write_bytes(
        (ROOT / "fixtures/benchmark/safedrug-batch-h1.json").read_bytes()
    )
    (session.packet_dir / "lane.json").write_bytes(
        (ROOT / "fixtures/benchmark/decision-packet-accepted.json").read_bytes()
    )
    session.create_h1(
        {
            "kind": "h1_input",
            "schema_version": 1,
            "owner": "oian",
            "rationale": "contract reviewed",
        }
    )
    request = {
        "action_id": "request_reproduction",
        "authorities": [{"authority_id": "scope", "sha256": "b" * 64}],
        "authorization_sha256": "c" * 64,
        "kind": "action_request",
        "preflight_sha256": "d" * 64,
        "project_id": "medrec-research",
        "remote_revision": "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
        "request_id": "action-context-aaaaaaaaaaaaaaaaaaaa",
        "schema_version": 1,
        "scope_sha256": "b" * 64,
        "snapshot_sha256": "a" * 64,
        "target_id": "319-wild",
    }
    action_request = ActionRequest.create(
        **{key: value for key, value in request.items() if key not in {"kind", "schema_version"}}
    )
    execution = session.queue_action_request(action_request.to_dict())

    assert execution["state"] == ExecutionState.BLOCKED.value
    assert execution["lane_id"] == "gamenet"
    assert execution["h2_decision_sha256"] is None
    assert "license-unresolved" in execution["blockers"]
    assert "preflight-missing" in execution["blockers"]
    assert session.execution_state()["queue"]["records"] == [execution]


def test_h2_non_go_blocks_next_execution_and_go_advances_registered_lane(
    tmp_path: Path,
) -> None:
    session = ResearchSession(ROOT, clock=lambda: NOW, runtime=tmp_path)
    session.action_request_dir = tmp_path / "action-requests"
    session.execution_dir = tmp_path / "executions"
    session.execution_queue = session.execution_queue.__class__(
        session.execution_dir, clock=session.clock
    )
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.packet_dir = tmp_path / "packets"
    session.h2_dir = tmp_path / "h2"
    session.loop_path = tmp_path / "research-loop.json"
    session.packet_dir.mkdir()
    session.h2_dir.mkdir()
    session.action_request_dir.mkdir()
    session.execution_dir.mkdir()
    session.contract_path.write_bytes(
        (ROOT / "fixtures/benchmark/safedrug-batch-h1.json").read_bytes()
    )
    (session.packet_dir / "lane.json").write_bytes(
        (ROOT / "fixtures/benchmark/decision-packet-accepted.json").read_bytes()
    )
    session.create_h1(
        {
            "kind": "h1_input",
            "schema_version": 1,
            "owner": "oian",
            "rationale": "contract reviewed",
        }
    )
    session.create_h2(
        {
            "kind": "h2_input",
            "schema_version": 1,
            "lane_id": "gamenet",
            "researcher": "oian",
            "action": "hold",
            "rationale": "awaiting independent review",
        }
    )
    replay = session.create_h2(
        {
            "kind": "h2_input",
            "schema_version": 1,
            "lane_id": "gamenet",
            "researcher": "oian",
            "action": "hold",
            "rationale": "awaiting independent review",
        }
    )
    assert H2Decision.from_dict(replay).action.value == "hold"

    with pytest.raises(ProtocolValidationError, match="H2 decision for this packet is immutable"):
        session.create_h2(
            {
                "kind": "h2_input",
                "schema_version": 1,
                "lane_id": "gamenet",
                "researcher": "oian",
                "action": "go",
                "rationale": "evidence accepted",
            }
        )

    packet = DecisionPacket.from_json(
        (session.packet_dir / "lane.json").read_text(encoding="utf-8")
    )
    outcomes = {key: value + 0.01 for key, value in packet.to_dict()["outcomes"].items()}
    session.packet_dir.joinpath("lane.json").write_text(
        DecisionPacket(
            packet_id=packet.packet_id,
            contract_sha256=packet.contract_sha256,
            lane_id=packet.lane_id,
            attempts=packet.attempts,
            conclusion=packet.conclusion,
            validity=packet.validity,
            stage=packet.stage,
            required_outcomes=packet.required_outcomes,
            outcomes=outcomes,
            uncertainty=packet.uncertainty,
            limitations=packet.limitations,
            allowed_claims=packet.allowed_claims,
            blockers=packet.blockers,
            action_consequences=packet.action_consequences,
            attempted_lane_ids=packet.attempted_lane_ids,
            completed_lane_ids=packet.completed_lane_ids,
            created_at=packet.created_at,
            notes=packet.notes,
        ).to_json(),
        encoding="utf-8",
    )

    held = ActionRequest.create(
        request_id="action-context-hhhhhhhhhhhhhhhhhhhh",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_next_lane",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "b" * 64},),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="e" * 40,
    )
    with pytest.raises(ProtocolValidationError, match="current H2 GO"):
        session.queue_action_request(held.to_dict())

    session.create_h2(
        {
            "kind": "h2_input",
            "schema_version": 1,
            "lane_id": "gamenet",
            "researcher": "oian",
            "action": "go",
            "rationale": "evidence accepted",
        }
    )
    advanced = ActionRequest.create(
        request_id="action-context-gggggggggggggggggggg",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_next_lane",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "b" * 64},),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="e" * 40,
    )

    execution = session.queue_action_request(advanced.to_dict())
    assert execution["lane_id"] == "safedrug"
    assert execution["h2_decision_sha256"] is not None

    follow_up = ActionRequest.create(
        request_id="action-context-iiiiiiiiiiiiiiiiiiii",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="submit_reproduction_evidence",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "b" * 64},),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="e" * 40,
    )
    evidence = session.queue_action_request(follow_up.to_dict())
    assert evidence["lane_id"] == "safedrug"
    assert evidence["h2_decision_sha256"] == execution["h2_decision_sha256"]
