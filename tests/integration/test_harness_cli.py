from __future__ import annotations

import http.client
import json
import signal
import socket
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread

import pytest

from medrec_research.action_gate import (
    ActionAuthorization,
    AuthorityBundle,
    RemotePreflight,
)
from medrec_research.harness import create_harness_server
from medrec_research.project_status import ProjectStatus

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 7, 11, 1, 3, tzinfo=UTC)
TARGET_ID = "319-wild"


def _snapshot() -> ProjectStatus:
    return ProjectStatus.from_json(
        (ROOT / "fixtures/status/discovery-eligible.json").read_text(encoding="utf-8")
    )


def _bundle(snapshot: ProjectStatus) -> AuthorityBundle:
    shared = {
        "project_id": snapshot.project_id,
        "target_id": TARGET_ID,
        "action_id": "begin_discovery",
        "snapshot_sha256": snapshot.snapshot_sha256,
        "scope_sha256": "d" * 64,
        "authorities": snapshot.authorities,
        "issued_at": "2026-07-11T01:01:00Z",
        "expires_at": "2026-07-11T01:05:00Z",
    }
    authorization = ActionAuthorization.create(
        issuer_id="research-steward",
        source_id="steward-approval",
        **shared,
    )
    preflight = RemotePreflight.create(
        issuer_id="aris",
        source_id="remote-preflight",
        remote_revision="e" * 40,
        **shared,
    )
    return AuthorityBundle(
        current_authorities=snapshot.authorities,
        current_remote_profile_id=TARGET_ID,
        current_remote_revision="e" * 40,
        authorization_issuer_id="research-steward",
        authorization_source_id="steward-approval",
        preflight_issuer_id="aris",
        preflight_source_id="remote-preflight",
        authorizations=(authorization,),
        preflights=(preflight,),
    )


@contextmanager
def _running_server(
    status_path: Path,
    *,
    actions_enabled: bool = False,
    bundle: AuthorityBundle | None = None,
    now: datetime = NOW,
) -> Iterator[tuple[object, str]]:
    snapshot = _snapshot()
    server = create_harness_server(
        status_path=status_path,
        expected_authorities=snapshot.authorities,
        clock=lambda: now,
        actions_enabled=actions_enabled,
        authority_bundle=bundle,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    try:
        yield server, host
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(
    host: str,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    address, raw_port = host.split(":")
    connection = http.client.HTTPConnection(address, int(raw_port), timeout=2)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def _raw_request(host: str, request: bytes) -> bytes:
    address, raw_port = host.split(":")
    with socket.create_connection((address, int(raw_port)), timeout=2) as connection:
        connection.sendall(request)
        return connection.recv(4096)


@pytest.fixture
def status_path(tmp_path: Path) -> Path:
    path = tmp_path / "status.json"
    path.write_text(_snapshot().to_json(indent=2), encoding="utf-8")
    return path


def test_root_assets_and_status_are_read_only_package_resources(status_path: Path) -> None:
    before = status_path.read_bytes()
    with _running_server(status_path) as (_, host):
        root = _request(host, "GET", "/")
        css = _request(host, "GET", "/assets/app.css")
        javascript = _request(host, "GET", "/assets/app.js")
        status = _request(host, "GET", "/api/status")

    assert root[0] == css[0] == javascript[0] == status[0] == 200
    assert b"MedRec Research Harness" in root[2]
    assert b"prefers-reduced-motion" in css[2]
    assert b"innerHTML" not in javascript[2]
    assert json.loads(status[2])["snapshot_sha256"] == _snapshot().snapshot_sha256
    assert status_path.read_bytes() == before
    assert "Access-Control-Allow-Origin" not in status[1]
    assert status[1]["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "host_value",
    [
        None,
        "duplicate",
        "127.0.0.1:1,127.0.0.1:2",
        "user@127.0.0.1:1",
        "null",
        "127.0.0.1.example.org:1",
        "127.0.0.1:1",
    ],
)
def test_host_must_be_one_exact_bound_literal(status_path: Path, host_value: str | None) -> None:
    with _running_server(status_path) as (_, host):
        lines = [b"GET /api/status HTTP/1.1"]
        if host_value == "duplicate":
            lines.extend([f"Host: {host}".encode(), f"Host: {host}".encode()])
        elif host_value is not None:
            lines.append(f"Host: {host_value}".encode())
        lines.extend([b"Connection: close", b"", b""])
        response = _raw_request(host, b"\r\n".join(lines))

    assert response.startswith(b"HTTP/1.1 421")


@pytest.mark.parametrize(
    "origin",
    [None, "duplicate", "null", "http://user@127.0.0.1:1", "http://127.0.0.1.example:1"],
)
def test_action_origin_must_be_one_exact_same_origin(status_path: Path, origin: str | None) -> None:
    snapshot = _snapshot()
    with _running_server(status_path, actions_enabled=True, bundle=_bundle(snapshot)) as (_, host):
        lines = [b"POST /api/action-requests HTTP/1.1", f"Host: {host}".encode()]
        if origin == "duplicate":
            lines.extend([f"Origin: http://{host}".encode(), f"Origin: http://{host}".encode()])
        elif origin is not None:
            lines.append(f"Origin: {origin}".encode())
        lines.extend(
            [
                b"Content-Type: application/json",
                b"Content-Length: 16384",
                b"Connection: close",
                b"",
                b"",
            ]
        )
        response = _raw_request(host, b"\r\n".join(lines))

    assert response.startswith(b"HTTP/1.1 403")


def test_expect_100_and_oversized_body_are_rejected_before_body_read(status_path: Path) -> None:
    snapshot = _snapshot()
    with _running_server(status_path, actions_enabled=True, bundle=_bundle(snapshot)) as (_, host):
        request = b"\r\n".join(
            [
                b"POST /api/action-requests HTTP/1.1",
                f"Host: {host}".encode(),
                f"Origin: http://{host}".encode(),
                b"Content-Type: application/json",
                b"Content-Length: 16385",
                b"Expect: 100-continue",
                b"Connection: close",
                b"",
                b"",
            ]
        )
        response = _raw_request(host, request)

    assert response.startswith(b"HTTP/1.1 413")
    assert b"100 Continue" not in response


@pytest.mark.parametrize(
    ("extra_headers", "expected"),
    [
        ({"Content-Type": "text/plain"}, 415),
        ({"Content-Type": "application/json", "Transfer-Encoding": "chunked"}, 400),
    ],
)
def test_action_rejects_wrong_body_framing(
    status_path: Path, extra_headers: dict[str, str], expected: int
) -> None:
    snapshot = _snapshot()
    with _running_server(status_path, actions_enabled=True, bundle=_bundle(snapshot)) as (_, host):
        status, _, _ = _request(
            host,
            "POST",
            "/api/action-requests",
            body=b"{}",
            headers={"Origin": f"http://{host}", **extra_headers},
        )

    assert status == expected


def test_action_context_drives_allowed_request_without_execution(status_path: Path) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    with _running_server(status_path, actions_enabled=True, bundle=bundle) as (_, host):
        context_status, _, context_body = _request(host, "GET", "/api/action-context")
        context = json.loads(context_body)
        intent = {
            "schema_version": 1,
            "kind": "action_intent",
            "request_id": "browser-request-001",
            **context["intent"],
        }
        decision_status, _, decision_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(intent).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    decision = json.loads(decision_body)
    assert context_status == decision_status == 200
    assert context["enabled"] is True
    assert set(context["intent"]) == {
        "action_id",
        "authorization_sha256",
        "preflight_sha256",
        "scope_sha256",
        "snapshot_sha256",
        "target_id",
    }
    assert decision["status"] == "allowed"
    assert decision["request"]["request_sha256"]
    assert "execut" not in json.dumps(decision).lower()


def test_action_gate_returns_blocked_decision_without_mutation(status_path: Path) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    before = status_path.read_bytes()
    with _running_server(status_path, actions_enabled=True, bundle=bundle) as (_, host):
        context = json.loads(_request(host, "GET", "/api/action-context")[2])
        intent = {
            "schema_version": 1,
            "kind": "action_intent",
            "request_id": "browser-request-blocked",
            **context["intent"],
            "authorization_sha256": "f" * 64,
        }
        status, _, body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(intent).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    decision = json.loads(body)
    assert status == 200
    assert decision == {
        "kind": "action_decision",
        "reason_code": "authorization_missing",
        "request": None,
        "schema_version": 1,
        "status": "blocked",
    }
    assert status_path.read_bytes() == before


def test_actions_are_disabled_by_default_before_body_read(status_path: Path) -> None:
    with _running_server(status_path) as (_, host):
        response = _raw_request(
            host,
            b"\r\n".join(
                [
                    b"POST /api/action-requests HTTP/1.1",
                    f"Host: {host}".encode(),
                    f"Origin: http://{host}".encode(),
                    b"Content-Length: 16385",
                    b"Connection: close",
                    b"",
                    b"",
                ]
            ),
        )

    assert response.startswith(b"HTTP/1.1 403")


def test_stale_and_malformed_status_fail_closed(status_path: Path) -> None:
    with _running_server(status_path, now=datetime(2026, 7, 11, 1, 8, tzinfo=UTC)) as (_, host):
        stale = json.loads(_request(host, "GET", "/api/status")[2])
        context = json.loads(_request(host, "GET", "/api/action-context")[2])
    assert stale["condition"] == "stale"
    assert stale["permitted_actions"] == []
    assert context["enabled"] is False

    status_path.write_text("private malformed value", encoding="utf-8")
    with _running_server(status_path) as (_, host):
        status, _, body = _request(host, "GET", "/api/status")
    assert status == 503
    assert json.loads(body) == {
        "error": "status_unavailable",
        "kind": "harness_error",
        "schema_version": 1,
    }
    assert b"private malformed value" not in body


def test_non_loopback_bind_and_unsupported_methods_are_blocked(status_path: Path) -> None:
    snapshot = _snapshot()
    with pytest.raises(ValueError, match=r"127\.0\.0\.1"):
        create_harness_server(
            status_path=status_path,
            expected_authorities=snapshot.authorities,
            clock=lambda: NOW,
            host="0.0.0.0",
        )

    with _running_server(status_path) as (_, host):
        status, headers, _ = _request(host, "PUT", "/api/status", body=b"ignored")
    assert status == 405
    assert headers["Allow"] == "GET, POST"


def test_ui_assets_declare_all_states_and_accessibility_contract(status_path: Path) -> None:
    with _running_server(status_path) as (_, host):
        html = _request(host, "GET", "/")[2].decode()
        css = _request(host, "GET", "/assets/app.css")[2].decode()
        javascript = _request(host, "GET", "/assets/app.js")[2].decode()

    assert html.count("<caption>") == 2
    assert 'aria-live="polite"' in html
    assert 'aria-live="assertive"' in html
    assert 'class="skip-link"' in html
    for state in (
        "loading",
        "no-action",
        "readonly",
        "ready",
        "submitting",
        "allowed",
        "blocked",
        "stale",
        "degraded",
        "malformed",
        "transport",
    ):
        assert f'"{state}"' in javascript
    assert "min-height: 2.75rem" in css
    assert "@media (min-width: 48rem)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "parsed.port" in javascript
    assert '"passwd"' in javascript
    assert '"sig"' in javascript


def test_harness_cli_serves_blocked_decision_and_stops_cleanly(tmp_path: Path) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    bundle_path = tmp_path / "authority-bundle.json"
    bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
    process = subprocess.Popen(
        (
            sys.executable,
            "-m",
            "medrec_research.cli",
            "harness",
            "--status",
            str(ROOT / "fixtures/status/discovery-eligible.json"),
            "--authority-bundle",
            str(bundle_path),
            "--port",
            "0",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    host = process.stdout.readline().strip().removeprefix("http://")
    try:
        assert host.startswith("127.0.0.1:")
        assert _request(host, "GET", "/")[0] == 200
        authorization = bundle.authorizations[0]
        preflight = bundle.preflights[0]
        intent = {
            "action_id": authorization.action_id,
            "authorization_sha256": "f" * 64,
            "kind": "action_intent",
            "preflight_sha256": preflight.preflight_sha256,
            "request_id": "cli-harness-blocked",
            "schema_version": 1,
            "scope_sha256": authorization.scope_sha256,
            "snapshot_sha256": snapshot.snapshot_sha256,
            "target_id": authorization.target_id,
        }
        status, _, body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(intent).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://{host}",
            },
        )
        assert status == 200
        assert json.loads(body)["status"] == "blocked"
    finally:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=5)
    assert process.returncode == 0
