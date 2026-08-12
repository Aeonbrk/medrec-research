from __future__ import annotations

import http.client
import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

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


def _hitl_session(tmp_path: Path) -> ResearchSession:
    session = ResearchSession(ROOT, clock=lambda: datetime(2026, 8, 12, 13, tzinfo=UTC))
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
    assert json.loads(initial_body)["h1"]["current"] is False
    assert rejected_status == 403
    assert json.loads(rejected_body)["error"] == "origin_rejected"
    assert injected_status == 409
    assert json.loads(injected_body)["error"] == "hitl_decision_rejected"
    assert h1_status == h2_status == 201
    assert json.loads(h1_body)["owner"] == "oian"
    assert json.loads(control_body)["h1"]["current"] is True
    assert json.loads(h2_body)["action"] == "go"
