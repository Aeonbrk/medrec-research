"""Loopback-only HTTP projection for public MedRec research status."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock
from typing import Any

from ._validation import canonical_json, parse_json_object
from .action_gate import ActionIntent, AuthorityBundle, evaluate_action
from .errors import ProtocolValidationError
from .project_status import AuthorityDigest, ProjectStatus, SnapshotCondition, load_status

_BODY_LIMIT = 16 * 1024
_HOST = "127.0.0.1"
_JSON_TYPE = "application/json"
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}
_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
    "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
}

Clock = Callable[[], datetime]


def _error_payload(code: str) -> dict[str, object]:
    return {"error": code, "kind": "harness_error", "schema_version": 1}


class _HarnessServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(
        self,
        address: tuple[str, int],
        *,
        status_path: Path,
        expected_authorities: tuple[AuthorityDigest, ...],
        clock: Clock,
        actions_enabled: bool,
        authority_bundle: AuthorityBundle | None,
    ) -> None:
        self.status_path = status_path
        self.expected_authorities = expected_authorities
        self.clock = clock
        self.actions_enabled = actions_enabled
        self.authority_bundle = authority_bundle
        self._last_known_good: ProjectStatus | None = None
        self._status_lock = Lock()
        super().__init__(address, _HarnessHandler)

    @property
    def expected_host(self) -> str:
        return f"{_HOST}:{self.server_port}"

    def current_status(self) -> ProjectStatus:
        with self._status_lock:
            status = load_status(
                self.status_path,
                clock=self.clock,
                expected_authorities=self.expected_authorities,
                last_known_good=self._last_known_good,
            )
            if status.condition is SnapshotCondition.CURRENT:
                self._last_known_good = status
            return status

    def action_context(self, status: ProjectStatus) -> dict[str, object]:
        unavailable = {
            "enabled": False,
            "intent": None,
            "kind": "action_context",
            "schema_version": 1,
        }
        bundle = self.authority_bundle
        if not self.actions_enabled or bundle is None or status.next_action is None:
            return unavailable

        candidates: list[dict[str, str]] = []
        for authorization in bundle.authorizations:
            for preflight in bundle.preflights:
                try:
                    intent = ActionIntent(
                        request_id="harness-context-probe",
                        action_id=status.next_action.action_id,
                        target_id=bundle.current_remote_profile_id,
                        snapshot_sha256=status.snapshot_sha256,
                        scope_sha256=authorization.scope_sha256,
                        authorization_sha256=authorization.authorization_sha256,
                        preflight_sha256=preflight.preflight_sha256,
                    )
                    decision = evaluate_action(
                        intent=intent,
                        snapshot=status,
                        authority_bundle=bundle,
                        now=self.clock(),
                    )
                except ProtocolValidationError:
                    continue
                if decision.status == "allowed":
                    payload = intent.to_dict()
                    payload.pop("kind")
                    payload.pop("request_id")
                    payload.pop("schema_version")
                    candidates.append(payload)
        if len(candidates) != 1:
            return unavailable
        return {**unavailable, "enabled": True, "intent": candidates[0]}


class _HarnessHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _HarnessServer

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(2)

    def log_message(self, format: str, *args: Any) -> None:
        """Do not copy untrusted request targets or headers into local logs."""

    def _send_bytes(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str,
        *,
        extra_headers: dict[str, str] | None = None,
        include_body: bool = True,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.close_connection = True
        if include_body:
            self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, value: object) -> None:
        body = canonical_json(value).encode("ascii")
        self._send_bytes(status, body, f"{_JSON_TYPE}; charset=utf-8")

    def _reject(self, status: HTTPStatus, code: str) -> bool:
        self._send_json(status, _error_payload(code))
        return False

    def _valid_host(self) -> bool:
        values = self.headers.get_all("Host", failobj=[])
        if len(values) != 1 or values[0] != self.server.expected_host:
            return self._reject(HTTPStatus.MISDIRECTED_REQUEST, "host_rejected")
        return True

    def _valid_origin(self) -> bool:
        values = self.headers.get_all("Origin", failobj=[])
        expected = f"http://{self.server.expected_host}"
        if len(values) != 1 or values[0] != expected:
            return self._reject(HTTPStatus.FORBIDDEN, "origin_rejected")
        return True

    def _post_length(self) -> int | None:
        if not self._valid_host() or not self._valid_origin():
            return None
        if not self.server.actions_enabled:
            self._reject(HTTPStatus.FORBIDDEN, "actions_disabled")
            return None
        if self.path != "/api/action-requests":
            self._reject(HTTPStatus.NOT_FOUND, "route_not_found")
            return None
        if self.headers.get_all("Transfer-Encoding", failobj=[]):
            self._reject(HTTPStatus.BAD_REQUEST, "transfer_encoding_rejected")
            return None
        content_types = self.headers.get_all("Content-Type", failobj=[])
        if len(content_types) != 1 or content_types[0] != _JSON_TYPE:
            self._reject(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type_rejected")
            return None
        lengths = self.headers.get_all("Content-Length", failobj=[])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._reject(HTTPStatus.BAD_REQUEST, "content_length_rejected")
            return None
        length = int(lengths[0])
        if length > _BODY_LIMIT:
            self._reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large")
            return None
        return length

    def handle_expect_100(self) -> bool:
        if self.command != "POST":
            self._method_not_allowed()
            return False
        if self._post_length() is None:
            return False
        self.send_response_only(HTTPStatus.CONTINUE)
        self.end_headers()
        return True

    def do_GET(self) -> None:
        if not self._valid_host():
            return
        asset = _ASSETS.get(self.path)
        if asset is not None:
            name, content_type = asset
            try:
                body = files("medrec_research.web").joinpath(name).read_bytes()
            except (FileNotFoundError, ModuleNotFoundError, OSError):
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    _error_payload("asset_unavailable"),
                )
                return
            self._send_bytes(HTTPStatus.OK, body, content_type)
            return
        if self.path not in {"/api/status", "/api/action-context"}:
            self._send_json(HTTPStatus.NOT_FOUND, _error_payload("route_not_found"))
            return
        try:
            status = self.server.current_status()
        except (OSError, UnicodeError, ProtocolValidationError):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                _error_payload("status_unavailable"),
            )
            return
        if self.path == "/api/status":
            self._send_bytes(
                HTTPStatus.OK,
                status.to_json().encode("ascii"),
                f"{_JSON_TYPE}; charset=utf-8",
            )
            return
        self._send_json(HTTPStatus.OK, self.server.action_context(status))

    def do_POST(self) -> None:
        length = self._post_length()
        if length is None:
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("body_incomplete"))
                return
            payload = parse_json_object(raw.decode("utf-8"), context="action intent")
            intent = ActionIntent.from_dict(payload)
        except (UnicodeError, ProtocolValidationError, TypeError):
            self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("action_intent_invalid"))
            return
        try:
            status = self.server.current_status()
        except (OSError, UnicodeError, ProtocolValidationError):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                _error_payload("status_unavailable"),
            )
            return
        decision = evaluate_action(
            intent=intent,
            snapshot=status,
            authority_bundle=self.server.authority_bundle,
            now=self.server.clock(),
        )
        self._send_json(HTTPStatus.OK, decision.to_dict())

    def _method_not_allowed(self) -> None:
        if not self._valid_host():
            return
        body = canonical_json(_error_payload("method_not_allowed")).encode("ascii")
        self._send_bytes(
            HTTPStatus.METHOD_NOT_ALLOWED,
            body,
            f"{_JSON_TYPE}; charset=utf-8",
            extra_headers={"Allow": "GET, POST"},
            include_body=self.command != "HEAD",
        )

    do_CONNECT = _method_not_allowed
    do_DELETE = _method_not_allowed
    do_HEAD = _method_not_allowed
    do_OPTIONS = _method_not_allowed
    do_PATCH = _method_not_allowed
    do_PUT = _method_not_allowed
    do_TRACE = _method_not_allowed


def create_harness_server(
    *,
    status_path: str | Path,
    expected_authorities: Iterable[AuthorityDigest],
    clock: Clock,
    host: str = _HOST,
    port: int = 0,
    actions_enabled: bool = False,
    authority_bundle: AuthorityBundle | None = None,
) -> ThreadingHTTPServer:
    """Create an unstarted server with explicit status and action authority."""

    if host != _HOST:
        raise ValueError("harness host must be the literal 127.0.0.1 loopback address")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("harness port must be an integer between 0 and 65535")
    if actions_enabled and authority_bundle is None:
        raise ValueError("enabled actions require an explicit authority bundle")
    return _HarnessServer(
        (host, port),
        status_path=Path(status_path),
        expected_authorities=tuple(expected_authorities),
        clock=clock,
        actions_enabled=actions_enabled,
        authority_bundle=authority_bundle,
    )


__all__ = ("create_harness_server",)
