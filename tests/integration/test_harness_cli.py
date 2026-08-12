from __future__ import annotations

import http.client
import json
import re
import signal
import socket
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Thread

import pytest

from medrec_research._validation import canonical_json
from medrec_research.action_gate import (
    ActionAuthorization,
    AuthorityBundle,
    RemotePreflight,
)
from medrec_research.cli import main
from medrec_research.harness import create_harness_server
from medrec_research.project_status import AuthorityDigest, ProjectStatus

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 7, 11, 1, 3, tzinfo=UTC)
TARGET_ID = "319-wild"


def _snapshot() -> ProjectStatus:
    return ProjectStatus.from_json(
        (ROOT / "fixtures/status/discovery-eligible.json").read_text(encoding="utf-8")
    )


def _rotated_snapshot(snapshot: ProjectStatus) -> ProjectStatus:
    authorities = tuple(
        AuthorityDigest("scope", "f" * 64) if item.authority_id == "scope" else item
        for item in snapshot.authorities
    )
    return ProjectStatus.create(
        project_id=snapshot.project_id,
        authorities=authorities,
        blockers=snapshot.blockers,
        payload=snapshot.payload,
        clock=lambda: NOW,
    )


def _bundle(
    snapshot: ProjectStatus,
    *,
    issued_at: str = "2026-07-11T01:01:00Z",
    expires_at: str = "2026-07-11T01:05:00Z",
) -> AuthorityBundle:
    scope_sha256 = next(
        item.sha256 for item in snapshot.authorities if item.authority_id == "scope"
    )
    shared = {
        "project_id": snapshot.project_id,
        "target_id": TARGET_ID,
        "action_id": "begin_discovery",
        "snapshot_sha256": snapshot.snapshot_sha256,
        "scope_sha256": scope_sha256,
        "authorities": snapshot.authorities,
        "issued_at": issued_at,
        "expires_at": expires_at,
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
    authority_bundle_path: Path | None = None,
    research_loop_path: Path | None = None,
    now: datetime = NOW,
    clock: Callable[[], datetime] | None = None,
) -> Iterator[tuple[object, str]]:
    snapshot = _snapshot()
    if bundle is not None and authority_bundle_path is None:
        authority_bundle_path = status_path.with_name("authority-bundle.json")
        authority_bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
    server = create_harness_server(
        status_path=status_path,
        expected_authorities=snapshot.authorities,
        clock=clock or (lambda: now),
        actions_enabled=actions_enabled,
        authority_bundle_path=authority_bundle_path,
        research_loop_path=research_loop_path,
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
        html = root[2].decode()
        asset_paths = re.findall(r'(?:href|src)="(/assets/[^"]+)"', html)
        assets = [_request(host, "GET", path) for path in asset_paths]
        status = _request(host, "GET", "/api/status")

    assert root[0] == status[0] == 200
    assert asset_paths
    assert all(asset[0] == 200 for asset in assets)
    assert "MedRec Research · 研究控制台" in html
    assert 'lang="zh-CN"' in html
    assert any(asset[1]["Content-Type"].startswith("text/css") for asset in assets)
    assert any(asset[1]["Content-Type"].startswith("text/javascript") for asset in assets)
    assert json.loads(status[2])["snapshot_sha256"] == _snapshot().snapshot_sha256
    assert status_path.read_bytes() == before
    assert "Access-Control-Allow-Origin" not in status[1]
    assert status[1]["X-Content-Type-Options"] == "nosniff"


def test_hashed_assets_fonts_and_static_path_boundary(status_path: Path) -> None:
    with _running_server(status_path) as (_, host):
        html = _request(host, "GET", "/")[2].decode()
        stylesheet = next(path for path in re.findall(r'href="(/assets/[^"]+\.css)"', html))
        css = _request(host, "GET", stylesheet)
        font_name = re.search(rb"geist-mono-latin[^)]*\.woff2", css[2])
        assert font_name is not None
        font = _request(host, "GET", f"/assets/{font_name.group().decode()}")
        traversal = _request(host, "GET", "/assets/../index.html")
        encoded_traversal = _request(host, "GET", "/assets/%2e%2e/index.html")
        unknown = _request(host, "GET", "/assets/not-built.js")
        api_confusion = _request(host, "GET", "/api/index.js")

    assert css[0] == font[0] == 200
    assert font[1]["Content-Type"] == "font/woff2"
    assert "font-src 'self'" in css[1]["Content-Security-Policy"]
    assert traversal[0] == encoded_traversal[0] == unknown[0] == api_confusion[0] == 404


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
        request = {
            "schema_version": 1,
            "kind": "action_request_input",
            "request_id": context["request_id"],
        }
        decision_status, _, decision_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(request).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    decision = json.loads(decision_body)
    assert context_status == decision_status == 200
    assert context["enabled"] is True
    assert set(context) == {"enabled", "kind", "request_id", "schema_version"}
    assert decision["status"] == "allowed"
    assert decision["request"]["request_sha256"]
    assert "execut" not in json.dumps(decision).lower()


def test_cli_and_harness_emit_the_same_canonical_action_decision(
    status_path: Path, tmp_path: Path
) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    bundle_path = tmp_path / "authority-bundle.json"
    request_path = tmp_path / "request.json"
    cli_output = tmp_path / "cli-decision.json"
    bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")

    with _running_server(
        status_path,
        actions_enabled=True,
        authority_bundle_path=bundle_path,
    ) as (_, host):
        context = json.loads(_request(host, "GET", "/api/action-context")[2])
        request = {
            "kind": "action_request_input",
            "request_id": context["request_id"],
            "schema_version": 1,
        }
        harness_status, _, harness_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(request).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://{host}",
            },
        )
        request_path.write_text(json.dumps(request), encoding="utf-8")
        assert (
            main(
                [
                    "action-evaluate",
                    "--request",
                    str(request_path),
                    "--status",
                    str(status_path),
                    "--authority-bundle",
                    str(bundle_path),
                    "--output",
                    str(cli_output),
                ],
                clock=lambda: NOW,
            )
            == 0
        )

    assert harness_status == 200
    assert (
        canonical_json(json.loads(cli_output.read_text(encoding="utf-8"))).encode("ascii")
        == harness_body
    )


def test_action_context_reloads_rotated_authority_without_mutation(status_path: Path) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    bundle_path = status_path.with_name("authority-bundle.json")
    bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
    before = status_path.read_bytes()
    with _running_server(
        status_path,
        actions_enabled=True,
        authority_bundle_path=bundle_path,
    ) as (_, host):
        context = json.loads(_request(host, "GET", "/api/action-context")[2])
        assert context["enabled"] is True
        bundle_path.write_text("malformed", encoding="utf-8")
        unavailable = json.loads(_request(host, "GET", "/api/action-context")[2])
        request = {
            "schema_version": 1,
            "kind": "action_request_input",
            "request_id": context["request_id"],
        }
        status, _, body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(request).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )
        bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
        recovered = json.loads(_request(host, "GET", "/api/action-context")[2])
        recovered_status, _, recovered_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(
                {
                    "kind": "action_request_input",
                    "request_id": recovered["request_id"],
                    "schema_version": 1,
                }
            ).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    decision = json.loads(body)
    assert status == 200
    assert unavailable["enabled"] is False
    assert recovered["enabled"] is True
    assert recovered_status == 200
    assert json.loads(recovered_body)["status"] == "allowed"
    assert decision == {
        "kind": "action_decision",
        "reason_code": "authority_bundle_missing",
        "request": None,
        "schema_version": 1,
        "status": "blocked",
    }
    assert status_path.read_bytes() == before


def test_action_context_rejects_deeply_nested_authority_bundle(status_path: Path) -> None:
    bundle_path = status_path.with_name("authority-bundle.json")
    bundle_path.write_text("[" * 1_100 + "0" + "]" * 1_100, encoding="utf-8")
    with _running_server(
        status_path,
        actions_enabled=True,
        authority_bundle_path=bundle_path,
    ) as (_, host):
        context_status, _, context_body = _request(host, "GET", "/api/action-context")
        decision_status, _, decision_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(
                {
                    "kind": "action_request_input",
                    "request_id": "deeply-nested-bundle",
                    "schema_version": 1,
                }
            ).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    assert context_status == decision_status == 200
    assert json.loads(context_body)["enabled"] is False
    assert json.loads(decision_body)["reason_code"] == "authority_bundle_missing"


def test_harness_state_rejects_a_context_from_before_valid_rotation(status_path: Path) -> None:
    snapshot = _snapshot()
    bundle = _bundle(snapshot)
    bundle_path = status_path.with_name("authority-bundle.json")
    bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
    with _running_server(
        status_path,
        actions_enabled=True,
        authority_bundle_path=bundle_path,
    ) as (_, host):
        initial = json.loads(_request(host, "GET", "/api/harness-state")[2])
        rotated = _rotated_snapshot(snapshot)
        status_path.write_text(rotated.to_json(indent=2), encoding="utf-8")
        bundle_path.write_text(_bundle(rotated).to_json(indent=2), encoding="utf-8")
        current = json.loads(_request(host, "GET", "/api/harness-state")[2])
        stale_status, _, stale_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(
                {
                    "kind": "action_request_input",
                    "request_id": initial["action_context"]["request_id"],
                    "schema_version": 1,
                }
            ).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )
        current_status, _, current_body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(
                {
                    "kind": "action_request_input",
                    "request_id": current["action_context"]["request_id"],
                    "schema_version": 1,
                }
            ).encode(),
            headers={
                "Origin": f"http://{host}",
                "Content-Type": "application/json",
            },
        )

    assert initial["status"]["snapshot_sha256"] == snapshot.snapshot_sha256
    assert current["status"]["snapshot_sha256"] == rotated.snapshot_sha256
    assert stale_status == current_status == 200
    assert json.loads(stale_body)["reason_code"] == "action_context_stale"
    assert json.loads(current_body)["status"] == "allowed"


def test_harness_state_uses_one_clock_sample(status_path: Path) -> None:
    snapshot = _snapshot()
    timestamps = iter((NOW, datetime(2026, 7, 11, 1, 7, 3, tzinfo=UTC)))
    with _running_server(
        status_path,
        actions_enabled=True,
        bundle=_bundle(snapshot),
        clock=lambda: next(timestamps),
    ) as (_, host):
        state = json.loads(_request(host, "GET", "/api/harness-state")[2])

    assert state["status"]["condition"] == "current"
    assert state["action_context"]["enabled"] is True


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


def test_ui_entrypoint_declares_accessibility_and_runtime_contract(status_path: Path) -> None:
    with _running_server(status_path) as (_, host):
        html = _request(host, "GET", "/")[2].decode()
        assets = re.findall(r'(?:href|src)="(/assets/[^"]+)"', html)

    assert '<div id="root"></div>' in html
    assert assets
    assert all(path.startswith("/assets/") for path in assets)
    assert "http://" not in html
    assert "https://" not in html
    assert "vite.svg" not in html


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
        bundle_path.write_text("malformed", encoding="utf-8")
        request = {
            "kind": "action_request_input",
            "request_id": "cli-harness-blocked",
            "schema_version": 1,
        }
        status, _, body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(request).encode(),
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


def test_harness_cli_recovers_from_initial_invalid_authority_bundle(tmp_path: Path) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    source_snapshot = _snapshot()
    snapshot = ProjectStatus.create(
        project_id=source_snapshot.project_id,
        authorities=source_snapshot.authorities,
        blockers=source_snapshot.blockers,
        payload=source_snapshot.payload,
        clock=lambda: now,
        freshness=timedelta(hours=1),
    )
    status_path = tmp_path / "status.json"
    status_path.write_text(snapshot.to_json(indent=2), encoding="utf-8")
    bundle_path = tmp_path / "authority-bundle.json"
    bundle_path.write_text("malformed", encoding="utf-8")
    process = subprocess.Popen(
        (
            sys.executable,
            "-m",
            "medrec_research.cli",
            "harness",
            "--status",
            str(status_path),
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
        unavailable = json.loads(_request(host, "GET", "/api/action-context")[2])
        assert unavailable["enabled"] is False

        issued_at = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        expires_at = (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        bundle_path.write_text(
            _bundle(snapshot, issued_at=issued_at, expires_at=expires_at).to_json(indent=2),
            encoding="utf-8",
        )
        state = json.loads(_request(host, "GET", "/api/harness-state")[2])
        assert state["action_context"]["enabled"] is True
        status, _, body = _request(
            host,
            "POST",
            "/api/action-requests",
            body=json.dumps(
                {
                    "kind": "action_request_input",
                    "request_id": state["action_context"]["request_id"],
                    "schema_version": 1,
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://{host}",
            },
        )
        assert status == 200
        assert json.loads(body)["status"] == "allowed"
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        process.wait(timeout=5)
    assert process.returncode == 0
