"""Loopback-only HTTP projection for public MedRec research status."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from ._validation import canonical_json, parse_json_object
from .action_gate import (
    ActionContext,
    ActionRequestInput,
    AuthorityBundle,
    evaluate_action,
    resolve_action_context,
)
from .errors import ProtocolValidationError
from .project_status import AuthorityDigest, ProjectStatus, SnapshotCondition, load_status
from .research_loop_status import load_research_loop

if TYPE_CHECKING:
    from .research_session import ResearchSession

_BODY_LIMIT = 16 * 1024
_HOST = "127.0.0.1"
_JSON_TYPE = "application/json"
_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}
_ASSET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_ASSET_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".woff2": "font/woff2",
}

Clock = Callable[[], datetime]


def _error_payload(code: str) -> dict[str, object]:
    return {"error": code, "kind": "harness_error", "schema_version": 1}


def _static_asset(target: str) -> tuple[tuple[str, ...], str] | None:
    """Resolve only the Vite entrypoint and one-level hashed build assets."""

    path = urlsplit(target).path
    if path == "/":
        return ("index.html",), "text/html; charset=utf-8"
    prefix = "/assets/"
    if not path.startswith(prefix):
        return None
    name = path.removeprefix(prefix)
    if not _ASSET_NAME.fullmatch(name):
        return None
    content_type = _ASSET_TYPES.get(Path(name).suffix)
    if content_type is None:
        return None
    return ("assets", name), content_type


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
        authority_bundle_path: Path | None,
        research_loop_path: Path | None,
        hitl_session: ResearchSession | None,
    ) -> None:
        self.status_path = status_path
        self.expected_authorities = expected_authorities
        self.clock = clock
        self._actions_enabled = actions_enabled
        self.authority_bundle_path = authority_bundle_path
        self.research_loop_path = research_loop_path
        self.hitl_session = hitl_session
        self._last_known_good: ProjectStatus | None = None
        self._status_lock = Lock()
        super().__init__(address, _HarnessHandler)

    @property
    def expected_host(self) -> str:
        return f"{_HOST}:{self.server_port}"

    @property
    def actions_enabled(self) -> bool:
        if self.hitl_session is not None:
            return self.hitl_session.actions_enabled
        return self._actions_enabled

    def current_status(
        self,
        authority_bundle: AuthorityBundle | None = None,
        *,
        clock: Clock | None = None,
    ) -> ProjectStatus:
        expected_authorities = (
            authority_bundle.current_authorities
            if authority_bundle is not None
            else self.expected_authorities
        )
        with self._status_lock:
            status = load_status(
                self.status_path,
                clock=clock or self.clock,
                expected_authorities=expected_authorities,
                last_known_good=self._last_known_good,
            )
            if status.condition is SnapshotCondition.CURRENT:
                self._last_known_good = status
            return status

    def current_authority_bundle(self) -> AuthorityBundle | None:
        if self.authority_bundle_path is None:
            return None
        try:
            return AuthorityBundle.load(self.authority_bundle_path)
        except (OSError, UnicodeError, ProtocolValidationError):
            return None

    def action_context(
        self,
        status: ProjectStatus,
        authority_bundle: AuthorityBundle | None,
        *,
        clock: Clock,
    ) -> dict[str, object]:
        if not self.actions_enabled:
            return ActionContext.unavailable("actions_disabled").to_public_dict()
        return resolve_action_context(
            snapshot=status,
            authority_bundle=authority_bundle,
            now=clock(),
        ).to_public_dict()

    def service_actions(self) -> None:
        """Advance the server-owned transport without coupling it to browser reads."""

        super().service_actions()
        if self.hitl_session is None:
            return
        try:
            self.hitl_session.advance_transport()
        except (OSError, UnicodeError, ProtocolValidationError):
            # Bound transport failures are persisted by the wrapper. A malformed
            # local control record must not take down the loopback review server.
            return


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

    def _send_execution_events(self) -> None:
        if self.server.hitl_session is None:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                _error_payload("execution_control_unavailable"),
            )
            return
        cursor = self.headers.get("Last-Event-ID")
        try:
            events = self.server.hitl_session.execution_queue.events_after(cursor)
        except ProtocolValidationError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                _error_payload("execution_event_cursor_invalid"),
            )
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Connection", "keep-alive")
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.close_connection = False
        current_cursor = cursor
        heartbeat_at = time.monotonic() + 15
        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            while True:
                if not events:
                    events = self.server.hitl_session.execution_queue.events_after(current_cursor)
                for item in events:
                    self.wfile.write(
                        (
                            f"id: {item['event_id']}\n"
                            "event: execution\n"
                            f"data: {canonical_json(item)}\n\n"
                        ).encode("ascii")
                    )
                    current_cursor = item["event_id"]
                if events:
                    self.wfile.flush()
                    events = ()
                    heartbeat_at = time.monotonic() + 15
                elif time.monotonic() >= heartbeat_at:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    heartbeat_at = time.monotonic() + 15
                time.sleep(0.25)
        except (BrokenPipeError, ConnectionResetError, OSError, ProtocolValidationError):
            self.close_connection = True

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
        routes = {
            "/api/action-requests",
            "/api/contract-ai",
            "/api/execution-control",
            "/api/h1",
            "/api/h2",
        }
        if self.path not in routes:
            self._reject(HTTPStatus.NOT_FOUND, "route_not_found")
            return None
        if self.path == "/api/action-requests" and not self.server.actions_enabled:
            self._reject(HTTPStatus.FORBIDDEN, "actions_disabled")
            return None
        if (
            self.path in {"/api/contract-ai", "/api/execution-control", "/api/h1", "/api/h2"}
            and self.server.hitl_session is None
        ):
            self._reject(HTTPStatus.FORBIDDEN, "hitl_control_disabled")
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
        asset = _static_asset(self.path)
        if asset is not None:
            parts, content_type = asset
            try:
                body = files("medrec_research.web").joinpath(*parts).read_bytes()
            except FileNotFoundError:
                self._send_json(HTTPStatus.NOT_FOUND, _error_payload("route_not_found"))
                return
            except (ModuleNotFoundError, OSError):
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    _error_payload("asset_unavailable"),
                )
                return
            self._send_bytes(HTTPStatus.OK, body, content_type)
            return
        if self.path == "/api/research-loop":
            if self.server.research_loop_path is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("research_loop_unavailable"),
                )
                return
            try:
                loop = load_research_loop(self.server.research_loop_path)
            except ProtocolValidationError:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("research_loop_unavailable"),
                )
                return
            if not loop.is_current or (
                self.server.hitl_session is None and (loop.stale or not loop.h1_current)
            ):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("research_loop_unavailable"),
                )
                return
            self._send_bytes(
                HTTPStatus.OK,
                loop.to_json().encode("ascii"),
                f"{_JSON_TYPE}; charset=utf-8",
            )
            return
        if self.path == "/api/hitl-control":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("hitl_control_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, self.server.hitl_session.control_state())
            return
        if self.path == "/api/contract":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("contract_unavailable"),
                )
                return
            try:
                contract = self.server.hitl_session.contract_state()
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("contract_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, contract)
            return
        if self.path == "/api/decision-packets":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("decision_packets_unavailable"),
                )
                return
            try:
                packets = self.server.hitl_session.decision_packet_state()
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("decision_packets_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, packets)
            return
        if self.path == "/api/executions":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("execution_control_unavailable"),
                )
                return
            try:
                state = self.server.hitl_session.execution_state()
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("execution_control_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, state)
            return
        if self.path == "/api/execution-dispatch":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("execution_control_unavailable"),
                )
                return
            try:
                dispatch = self.server.hitl_session.execution_dispatch_state()
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("execution_dispatch_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, dispatch)
            return
        if self.path == "/api/aris-revision":
            if self.server.hitl_session is None:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("aris_revision_unavailable"),
                )
                return
            try:
                revision = self.server.hitl_session.aris_revision_state()
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("aris_revision_unavailable"),
                )
                return
            self._send_json(HTTPStatus.OK, revision)
            return
        if self.path == "/api/execution-events":
            self._send_execution_events()
            return
        if self.path not in {"/api/status", "/api/action-context", "/api/harness-state"}:
            self._send_json(HTTPStatus.NOT_FOUND, _error_payload("route_not_found"))
            return
        authority_bundle = (
            self.server.current_authority_bundle() if self.server.actions_enabled else None
        )
        now: datetime | None = None

        def request_clock() -> datetime:
            nonlocal now
            if now is None:
                now = self.server.clock()
            return now

        try:
            status = self.server.current_status(authority_bundle, clock=request_clock)
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
        context = self.server.action_context(status, authority_bundle, clock=request_clock)
        if self.path == "/api/action-context":
            self._send_json(HTTPStatus.OK, context)
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "action_context": context,
                "kind": "harness_state",
                "schema_version": 1,
                "status": status.to_dict(),
            },
        )

    def do_POST(self) -> None:
        length = self._post_length()
        if length is None:
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("body_incomplete"))
                return
            payload = parse_json_object(raw.decode("utf-8"), context="HITL input")
        except (UnicodeError, ProtocolValidationError, TypeError):
            self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("request_input_invalid"))
            return
        if self.path == "/api/contract-ai":
            assert self.server.hitl_session is not None
            try:
                result = self.server.hitl_session.contract_ai(payload)
            except ProtocolValidationError:
                self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("contract_ai_input_invalid"))
                return
            self._send_json(HTTPStatus.OK, result)
            return
        if self.path in {"/api/h1", "/api/h2"}:
            assert self.server.hitl_session is not None
            try:
                record = (
                    self.server.hitl_session.create_h1(payload)
                    if self.path == "/api/h1"
                    else self.server.hitl_session.create_h2(payload)
                )
            except ProtocolValidationError:
                self._send_json(HTTPStatus.CONFLICT, _error_payload("hitl_decision_rejected"))
                return
            self._send_json(HTTPStatus.CREATED, record)
            return
        if self.path == "/api/execution-control":
            assert self.server.hitl_session is not None
            try:
                result = self.server.hitl_session.control_transport(payload)
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.CONFLICT,
                    _error_payload("transport_control_rejected"),
                )
                return
            self._send_json(HTTPStatus.OK, result)
            return
        try:
            request = ActionRequestInput.from_dict(payload)
        except (ProtocolValidationError, TypeError):
            self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("action_request_input_invalid"))
            return
        authority_bundle = self.server.current_authority_bundle()
        now: datetime | None = None

        def request_clock() -> datetime:
            nonlocal now
            if now is None:
                now = self.server.clock()
            return now

        try:
            status = self.server.current_status(authority_bundle, clock=request_clock)
        except (OSError, UnicodeError, ProtocolValidationError):
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                _error_payload("status_unavailable"),
            )
            return
        decision = evaluate_action(
            request=request,
            snapshot=status,
            authority_bundle=authority_bundle,
            now=request_clock(),
        )
        if decision.request is not None and self.server.hitl_session is not None:
            try:
                self.server.hitl_session.queue_action_request(decision.request.to_dict())
            except (OSError, UnicodeError, ProtocolValidationError):
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    _error_payload("action_queue_unavailable"),
                )
                return
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
    authority_bundle_path: str | Path | None = None,
    research_loop_path: str | Path | None = None,
    hitl_session: ResearchSession | None = None,
) -> ThreadingHTTPServer:
    """Create an unstarted server with explicit status and action authority."""

    if host != _HOST:
        raise ValueError("harness host must be the literal 127.0.0.1 loopback address")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("harness port must be an integer between 0 and 65535")
    if actions_enabled and authority_bundle_path is None:
        raise ValueError("enabled actions require an explicit authority bundle path")
    return _HarnessServer(
        (host, port),
        status_path=Path(status_path),
        expected_authorities=tuple(expected_authorities),
        clock=clock,
        actions_enabled=actions_enabled,
        authority_bundle_path=(
            Path(authority_bundle_path) if authority_bundle_path is not None else None
        ),
        research_loop_path=Path(research_loop_path) if research_loop_path is not None else None,
        hitl_session=hitl_session,
    )


__all__ = ("create_harness_server",)
