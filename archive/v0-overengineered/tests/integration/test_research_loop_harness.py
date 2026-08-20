from __future__ import annotations

import http.client
import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

from medrec_research.action_gate import ActionRequest
from medrec_research.harness import create_harness_server
from medrec_research.research_loop_status import LaneProgress, ResearchLoopStatus
from medrec_research.research_session import ResearchSession

ROOT = Path(__file__).parents[2]


def _status_path(tmp_path: Path) -> Path:
    path = tmp_path / "status.json"
    path.write_text(
        ResearchLoopStatus(
            contract_sha256=None,
            h1_current=False,
            lanes=(
                LaneProgress(
                    lane_id="gamenet",
                    model_id="gamenet",
                    stage="safedrug",
                    attempt_status="blocked",
                    packet_complete=False,
                    conclusion="inconclusive",
                    h2_action=None,
                    h2_go_eligible=False,
                    current=False,
                    blockers=("h1-stale-or-missing",),
                ),
            ),
            blockers=("h1-stale-or-missing",),
            stale=True,
        ).to_json(),
        encoding="utf-8",
    )
    return path


def _get(host: str, path: str) -> tuple[int, bytes]:
    address, port = host.split(":")
    connection = http.client.HTTPConnection(address, int(port), timeout=2)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    status = response.status
    connection.close()
    return status, body


def _post(host: str, path: str, value: object, *, origin: str | None = None) -> tuple[int, bytes]:
    address, port = host.split(":")
    connection = http.client.HTTPConnection(address, int(port), timeout=2)
    connection.request(
        "POST",
        path,
        body=json.dumps(value).encode(),
        headers={
            "Content-Type": "application/json",
            "Origin": origin or f"http://{host}",
        },
    )
    response = connection.getresponse()
    body = response.read()
    status = response.status
    connection.close()
    return status, body


def _open_sse(
    host: str,
    *,
    last_event_id: str | None = None,
) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
    address, port = host.split(":")
    connection = http.client.HTTPConnection(address, int(port), timeout=2)
    headers = {"Last-Event-ID": last_event_id} if last_event_id is not None else {}
    connection.request("GET", "/api/execution-events", headers=headers)
    return connection, connection.getresponse()


def _read_sse_message(response: http.client.HTTPResponse) -> list[str]:
    lines: list[str] = []
    while True:
        line = response.readline().decode("ascii")
        if not line:
            raise AssertionError("SSE stream closed before a complete message")
        if line == "\n":
            return lines
        lines.append(line.removesuffix("\n"))


def _hitl_session(tmp_path: Path) -> ResearchSession:
    session = ResearchSession(
        ROOT, clock=lambda: datetime(2026, 8, 12, 13, tzinfo=UTC), runtime=tmp_path
    )
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
    return session


def test_research_loop_route_is_read_only_and_fail_closed(tmp_path: Path) -> None:
    loop_path = _status_path(tmp_path)
    server = create_harness_server(
        status_path=tmp_path / "missing-project-status.json",
        expected_authorities=(),
        clock=lambda: datetime(2026, 8, 10, tzinfo=UTC),
        research_loop_path=loop_path,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    try:
        status, body = _get(host, "/api/research-loop")
        assert status == 503
        assert b"research_loop_unavailable" in body
        before = loop_path.read_bytes()
        assert _get(host, "/api/research-loop")[0] == 503
        assert loop_path.read_bytes() == before

        loop_path.write_text("{}", encoding="utf-8")
        unavailable, _ = _get(host, "/api/research-loop")
        assert unavailable == 503

        numeric_digest = json.loads(_status_path(tmp_path).read_text(encoding="utf-8"))
        numeric_digest["contract_sha256"] = 7
        loop_path.write_text(json.dumps(numeric_digest), encoding="utf-8")
        assert _get(host, "/api/research-loop")[0] == 503
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_hitl_http_routes_bind_server_records_and_enforce_same_origin(tmp_path: Path) -> None:
    session = _hitl_session(tmp_path)
    server = create_harness_server(
        status_path=session.status_path,
        expected_authorities=(),
        clock=session.clock,
        research_loop_path=session.loop_path,
        hitl_session=session,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    h1_input = {
        "kind": "h1_input",
        "schema_version": 1,
        "owner": "oian",
        "rationale": "contract reviewed",
    }
    try:
        initial_status, initial_body = _get(host, "/api/hitl-control")
        contract_status, contract_body = _get(host, "/api/contract")
        packet_status, packet_body = _get(host, "/api/decision-packets")
        rejected_status, rejected_body = _post(
            host,
            "/api/h1",
            h1_input,
            origin="https://example.invalid",
        )
        injected_status, injected_body = _post(
            host,
            "/api/h1",
            {**h1_input, "contract_sha256": "f" * 64},
        )
        h1_status, h1_body = _post(host, "/api/h1", h1_input)
        control_status, control_body = _get(host, "/api/hitl-control")
        h2_status, h2_body = _post(
            host,
            "/api/h2",
            {
                "kind": "h2_input",
                "schema_version": 1,
                "lane_id": "gamenet",
                "researcher": "oian",
                "action": "go",
                "rationale": "evidence accepted",
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert initial_status == control_status == 200
    assert contract_status == 200
    contract = json.loads(contract_body)
    assert contract["kind"] == "research_contract"
    assert contract["status"] == "current"
    assert contract["source"]["revision"] == "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a"
    assert {field["id"] for field in contract["questionnaire"]} >= {
        "problem",
        "hypotheses",
        "data_lineage",
        "evidence_duties",
        "stopping_rules",
        "repair_budget",
    }
    assert contract["ai"] == {
        "reason_code": "local-ai-bridge-not-configured",
        "status": "unavailable",
    }
    assert packet_status == 200
    packet_control = json.loads(packet_body)
    assert packet_control["kind"] == "decision_packet_control"
    packet = packet_control["packets"][0]
    assert set(packet["outcomes"]) >= {
        "ddi_rate",
        "jaccard",
        "f1",
        "prauc",
        "average_medication_count",
    }
    assert set(packet["uncertainty"]) >= set(packet["required_outcomes"])
    assert packet["raw_aggregate_table"] is None
    assert packet["raw_artifact_reason"] == "raw-aggregate-table-unavailable"
    assert json.loads(initial_body)["h1"]["current"] is False
    assert rejected_status == 403
    assert json.loads(rejected_body)["error"] == "origin_rejected"
    assert injected_status == 409
    assert json.loads(injected_body)["error"] == "hitl_decision_rejected"
    assert h1_status == h2_status == 201
    assert json.loads(h1_body)["owner"] == "oian"
    assert json.loads(control_body)["h1"]["current"] is True
    assert json.loads(h2_body)["action"] == "go"


def test_contract_ai_route_is_bounded_and_never_writes_h1(tmp_path: Path) -> None:
    session = _hitl_session(tmp_path)
    server = create_harness_server(
        status_path=session.status_path,
        expected_authorities=(),
        clock=session.clock,
        research_loop_path=session.loop_path,
        hitl_session=session,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    payload = {
        "kind": "contract_ai_input",
        "schema_version": 1,
        "operation": "draft",
        "request_id": "request-123",
    }
    try:
        status, body = _post(host, "/api/contract-ai", payload)
        malformed_status, malformed_body = _post(
            host,
            "/api/contract-ai",
            {**payload, "operation": "shell"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    result = json.loads(body)
    assert result["status"] == "unavailable"
    assert result["reason_code"] == "local-ai-bridge-not-configured"
    assert result["h1_written"] is False
    assert not session.h1_path.exists()
    assert malformed_status == 400
    assert json.loads(malformed_body)["error"] == "contract_ai_input_invalid"


def test_transport_control_route_forwards_only_same_origin_opaque_input(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session = _hitl_session(tmp_path)
    calls: list[object] = []

    def control_transport(value: object) -> dict[str, object]:
        calls.append(value)
        return {
            "kind": "transport_control_result",
            "operation": "resume",
            "record": {"request_id": "action-context-recovery"},
            "schema_version": 1,
        }

    monkeypatch.setattr(session, "control_transport", control_transport)
    server = create_harness_server(
        status_path=session.status_path,
        expected_authorities=(),
        clock=session.clock,
        research_loop_path=session.loop_path,
        hitl_session=session,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    payload = {
        "kind": "transport_control_input",
        "operation": "resume",
        "request_id": "action-context-recovery",
        "schema_version": 1,
    }
    try:
        rejected_status, rejected_body = _post(
            host,
            "/api/execution-control",
            payload,
            origin="https://example.invalid",
        )
        status, body = _post(host, "/api/execution-control", payload)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert rejected_status == 403
    assert json.loads(rejected_body)["error"] == "origin_rejected"
    assert status == 200
    assert json.loads(body)["operation"] == "resume"
    assert calls == [payload]


def test_execution_routes_expose_registry_and_replayable_sse(tmp_path: Path) -> None:
    session = _hitl_session(tmp_path)
    declaration = session.execution_registry.get("gamenet", "request_reproduction")
    first_request = ActionRequest.create(
        request_id="action-context-sse-first",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_reproduction",
        snapshot_sha256="1" * 64,
        scope_sha256="2" * 64,
        authorities=({"authority_id": "scope", "sha256": "2" * 64},),
        authorization_sha256="3" * 64,
        preflight_sha256="4" * 64,
        remote_revision="5" * 40,
    )
    session.execution_queue.enqueue(
        request=first_request,
        declaration=declaration,
        contract_sha256="6" * 64,
        h1_approval_sha256="7" * 64,
    )
    server = create_harness_server(
        status_path=session.status_path,
        expected_authorities=(),
        clock=session.clock,
        research_loop_path=session.loop_path,
        hitl_session=session,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    first_connection: http.client.HTTPConnection | None = None
    second_connection: http.client.HTTPConnection | None = None
    try:
        status, body = _get(host, "/api/executions")
        first_connection, first_stream = _open_sse(host)
        assert first_stream.status == 200
        assert first_stream.getheader("Content-Length") is None
        assert first_stream.getheader("Connection") == "keep-alive"
        assert _read_sse_message(first_stream) == ["retry: 1500"]
        first_event_lines = _read_sse_message(first_stream)
        first_event = json.loads(first_event_lines[2].removeprefix("data: "))
        assert first_event_lines[:2] == [
            f"id: {first_event['event_id']}",
            "event: execution",
        ]
        assert first_event["request_sha256"] == first_request.request_sha256
        first_connection.close()
        first_connection = None

        second_connection, second_stream = _open_sse(
            host,
            last_event_id=first_event["event_id"],
        )
        assert second_stream.status == 200
        assert _read_sse_message(second_stream) == ["retry: 1500"]
        second_request = ActionRequest.create(
            request_id="action-context-sse-second",
            project_id="medrec-research",
            target_id="319-wild",
            action_id="request_reproduction",
            snapshot_sha256="8" * 64,
            scope_sha256="9" * 64,
            authorities=({"authority_id": "scope", "sha256": "9" * 64},),
            authorization_sha256="a" * 64,
            preflight_sha256="b" * 64,
            remote_revision="c" * 40,
        )
        session.execution_queue.enqueue(
            request=second_request,
            declaration=declaration,
            contract_sha256="6" * 64,
            h1_approval_sha256="7" * 64,
        )
        second_event_lines = _read_sse_message(second_stream)
        second_event = json.loads(second_event_lines[2].removeprefix("data: "))
        assert second_event_lines[:2] == [
            f"id: {second_event['event_id']}",
            "event: execution",
        ]
        assert int(second_event["event_id"]) > int(first_event["event_id"])
        assert second_event["request_sha256"] == second_request.request_sha256
    finally:
        if first_connection is not None:
            first_connection.close()
        if second_connection is not None:
            second_connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    payload = json.loads(body)
    assert status == 200
    assert payload["registry"]["lane_ids"] == [
        "gamenet",
        "safedrug",
        "molerec",
        "retain",
        "leap-safedrug",
    ]
    assert len(payload["registry"]["declarations"]) == 45


def test_corrupt_execution_record_keeps_public_queue_unavailable(tmp_path: Path) -> None:
    session = _hitl_session(tmp_path)
    (session.execution_dir / "broken.json").write_text("{", encoding="utf-8")
    server = create_harness_server(
        status_path=session.status_path,
        expected_authorities=(),
        clock=session.clock,
        research_loop_path=session.loop_path,
        hitl_session=session,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    try:
        status, body = _get(host, "/api/executions")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 503
    assert json.loads(body)["error"] == "execution_control_unavailable"
