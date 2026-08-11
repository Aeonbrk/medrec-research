from __future__ import annotations

import http.client
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

from medrec_research.harness import create_harness_server
from medrec_research.research_loop_status import LaneProgress, ResearchLoopStatus


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
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
