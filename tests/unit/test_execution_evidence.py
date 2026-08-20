from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from medrec_research.action_gate import ActionRequest
from medrec_research.errors import ProtocolValidationError
from medrec_research.execution_control import (
    ExecutionDeclarationRegistry,
    ExecutionState,
)
from medrec_research.execution_evidence import MonitorObservation, RestrictedEvidenceInput
from medrec_research.project_status import AuthorityDigest
from medrec_research.reproduction_contract import SafeDrugBatchContract
from medrec_research.reproduction_evaluation import (
    OutcomeObservation,
    SourceAcceptanceProfile,
    classify_reproduction,
)
from medrec_research.research_session import RemoteSessionPreflight, ResearchSession

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 8, 16, 7, tzinfo=UTC)
REMOTE_REVISION = "e" * 40


def _session(tmp_path: Path) -> ResearchSession:
    moments = iter(NOW + timedelta(seconds=index) for index in range(40))
    session = ResearchSession(ROOT, clock=lambda: next(moments))
    session.runtime = tmp_path
    session.status_path = tmp_path / "project-status.json"
    session.loop_path = tmp_path / "research-loop.json"
    session.preflight_path = tmp_path / "remote-preflight.json"
    session.authority_bundle_path = tmp_path / "authority-bundle.json"
    session.action_request_dir = tmp_path / "action-requests"
    session.execution_dir = tmp_path / "executions"
    session.monitor_dir = tmp_path / "monitor"
    session.evidence_dir = tmp_path / "evidence"
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.packet_dir = tmp_path / "packets"
    session.h2_dir = tmp_path / "h2"
    for directory in (
        session.action_request_dir,
        session.execution_dir,
        session.monitor_dir,
        session.evidence_dir,
        session.packet_dir,
        session.h2_dir,
    ):
        directory.mkdir(parents=True)
    session.execution_queue = session.execution_queue.__class__(
        session.execution_dir, clock=session.clock
    )
    packaged = ExecutionDeclarationRegistry.load_package()
    session.execution_registry = ExecutionDeclarationRegistry(
        tuple(replace(item, blockers=(), declaration_sha256="") for item in packaged.declarations),
        initial_lane_id=packaged.initial_lane_id,
    )
    session.preflight = RemoteSessionPreflight(
        observed_at="2026-08-16T07:00:00Z",
        reachable=True,
        fallback_used=False,
        identity_ok=True,
        checkout_exists=True,
        checkout_clean=True,
        local_revision=REMOTE_REVISION,
        remote_revision=REMOTE_REVISION,
        revision_matches=True,
        data_root_ready=True,
        conda_available=True,
        environment_verified=True,
        gpu_count=1,
        gpu_available=1,
        disk_free_gib=100,
        blockers=(),
    )
    session.contract_path.write_bytes(
        (ROOT / "fixtures/benchmark/safedrug-batch-h1.json").read_bytes()
    )
    session.create_h1(
        {
            "kind": "h1_input",
            "schema_version": 1,
            "owner": "oian",
            "rationale": "synthetic control-plane contract",
        }
    )
    return session


def _request(action_id: str, suffix: str) -> ActionRequest:
    return ActionRequest.create(
        request_id=f"action-context-{suffix * 20}",
        project_id="medrec-research",
        target_id="319-wild",
        action_id=action_id,
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=(AuthorityDigest("synthetic-authority", "1" * 64),),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision=REMOTE_REVISION,
    )


def _monitor(
    session: ResearchSession,
    request: ActionRequest,
    declaration_sha256: str,
    state: ExecutionState,
    sequence: int,
) -> None:
    observation = MonitorObservation(
        observation_id=f"poll-{sequence}",
        request_sha256=request.request_sha256,
        declaration_sha256=declaration_sha256,
        remote_revision=REMOTE_REVISION,
        state=state,
        reason_code=f"bridge-{state.value}",
        observed_at=f"2026-08-16T07:00:{sequence:02d}Z",
        authority_ok=True,
        privacy_ok=True,
        integrity_ok=True,
        resource_ok=True,
    )
    session.apply_monitor_observation(observation.to_dict())


def _evidence(session: ResearchSession, request: ActionRequest) -> RestrictedEvidenceInput:
    contract = SafeDrugBatchContract.from_json(session.contract_path.read_text(encoding="utf-8"))
    annex = next(item for item in contract.model_annexes if item.model_id == "gamenet")
    profile = SourceAcceptanceProfile(
        model_id="gamenet",
        acceptance_intervals=annex.acceptance_intervals,
        source_revision=annex.source_revision,
        source_reference="source-native-contract",
    )
    observations = tuple(
        OutcomeObservation(
            observation_id=f"aggregate-{index}",
            metric_values={
                "ddi_rate": 0.2,
                "jaccard": 0.5,
                "f1": 0.5,
                "prauc": 0.5,
                "average_medication_count": 0.5,
            },
        )
        for index in range(5)
    )
    evaluation = classify_reproduction(observations, profile, model_id="gamenet")
    declaration = session.execution_registry.get("gamenet", "request_reproduction")
    return RestrictedEvidenceInput(
        evidence_id="gamenet-aggregate-1",
        request_sha256=request.request_sha256,
        declaration_sha256=declaration.declaration_sha256,
        remote_revision=REMOTE_REVISION,
        evidence_schema_id=declaration.evidence_schema_id,
        attempt_id="gamenet-attempt-1",
        evaluation=evaluation,
        qa_qc={"coverage_complete": True, "patient_rows_exported": False},
        artifact_digests=(("aggregate-record", "f" * 64),),
        repair_evidence=(),
        deviations=(),
        authority_ok=True,
        privacy_ok=True,
        resource_ok=True,
        started_at="2026-08-16T07:00:00Z",
        finished_at="2026-08-16T07:10:00Z",
        reason="source-native aggregate evidence accepted",
    )


def test_monitor_intake_packet_h2_and_next_lane_form_one_replayable_chain(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    request = _request("request_reproduction", "a")
    queued = session.queue_action_request(request.to_dict())
    assert queued["state"] == "queued"
    declaration_sha256 = session.execution_registry.get(
        "gamenet", "request_reproduction"
    ).declaration_sha256
    for sequence, state in enumerate(
        (
            ExecutionState.SUBMITTING,
            ExecutionState.RUNNING,
            ExecutionState.MONITORING,
            ExecutionState.INTAKE,
        ),
        start=1,
    ):
        _monitor(session, request, declaration_sha256, state, sequence)

    evidence = _evidence(session, request)
    packet = session.intake_reproduction_evidence(evidence.to_dict())
    replay = session.intake_reproduction_evidence(evidence.to_dict())
    assert replay == packet
    assert packet["conclusion"] == "accepted"
    assert (
        session.execution_queue.load(request.request_sha256).state is ExecutionState.REVIEW_PENDING
    )
    projected = session.decision_packet_state()["packets"][0]
    assert len(projected["raw_aggregate_table"]) == 5
    assert projected["raw_artifact_reason"] == "raw-aggregate-table-available"

    receipt_path = next(session.evidence_dir.glob("*.json"))
    receipt_text = receipt_path.read_text(encoding="utf-8")
    tampered = json.loads(receipt_text)
    tampered["aggregate_table"][0]["metric"] = "tampered"
    receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
    blocked = session.decision_packet_state()["packets"][0]
    assert not blocked["go_eligible"]
    assert "evidence-receipt-invalid" in session.decision_packet_state()["blockers"]
    with pytest.raises(ProtocolValidationError, match="valid evidence receipt"):
        session.create_h2(
            {
                "kind": "h2_input",
                "schema_version": 1,
                "lane_id": "gamenet",
                "researcher": "oian",
                "action": "go",
                "rationale": "aggregate evidence accepted",
            }
        )
    receipt_path.write_text(receipt_text, encoding="utf-8")

    decision = session.create_h2(
        {
            "kind": "h2_input",
            "schema_version": 1,
            "lane_id": "gamenet",
            "researcher": "oian",
            "action": "go",
            "rationale": "aggregate evidence accepted",
        }
    )
    assert decision["action"] == "go"
    next_request = _request("request_next_lane", "b")
    next_record = session.queue_action_request(next_request.to_dict())
    assert next_record["lane_id"] == "safedrug"
    assert next_record["state"] == "queued"


def test_second_request_cannot_replace_a_lane_decision_packet(tmp_path: Path) -> None:
    session = _session(tmp_path)
    first = _request("request_reproduction", "a")
    session.queue_action_request(first.to_dict())
    declaration = session.execution_registry.get("gamenet", "request_reproduction")
    for sequence, state in enumerate(
        (
            ExecutionState.SUBMITTING,
            ExecutionState.RUNNING,
            ExecutionState.MONITORING,
            ExecutionState.INTAKE,
        ),
        start=1,
    ):
        _monitor(session, first, declaration.declaration_sha256, state, sequence)
    session.intake_reproduction_evidence(_evidence(session, first).to_dict())

    second = _request("request_reproduction", "b")
    session.queue_action_request(second.to_dict())
    for sequence, state in enumerate(
        (
            ExecutionState.SUBMITTING,
            ExecutionState.RUNNING,
            ExecutionState.MONITORING,
            ExecutionState.INTAKE,
        ),
        start=5,
    ):
        _monitor(session, second, declaration.declaration_sha256, state, sequence)

    with pytest.raises(ProtocolValidationError, match="already has a Decision Packet"):
        session.intake_reproduction_evidence(_evidence(session, second).to_dict())


def test_monitor_and_evidence_fail_closed_on_hard_gate_or_private_path(tmp_path: Path) -> None:
    session = _session(tmp_path)
    request = _request("request_reproduction", "a")
    session.queue_action_request(request.to_dict())
    declaration = session.execution_registry.get("gamenet", "request_reproduction")
    with pytest.raises(ProtocolValidationError, match="must cancel"):
        MonitorObservation(
            observation_id="poll-1",
            request_sha256=request.request_sha256,
            declaration_sha256=declaration.declaration_sha256,
            remote_revision=REMOTE_REVISION,
            state="running",
            reason_code="privacy-failed",
            observed_at="2026-08-16T07:00:01Z",
            authority_ok=True,
            privacy_ok=False,
            integrity_ok=True,
            resource_ok=True,
        )
    evidence = _evidence(session, request).to_dict()
    evidence["qa_qc"] = {"artifact": "/root/private/predictions.json"}
    evidence["evidence_sha256"] = ""
    with pytest.raises(ProtocolValidationError, match="local path"):
        RestrictedEvidenceInput.from_dict(evidence)

    malformed = _evidence(session, request).to_dict()
    malformed["deviations"] = "not-a-list"
    malformed["evidence_sha256"] = ""
    with pytest.raises(ProtocolValidationError, match="deviations must be a list"):
        RestrictedEvidenceInput.from_dict(malformed)
