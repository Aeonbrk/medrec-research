"""One-command coordinator for a real, fail-closed HITL research session."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock, RLock
from typing import Any, ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    require_identifier,
    strict_fields,
    write_json_atomic,
)
from .action_gate import ActionRequest, AuthorityBundle
from .aris_bridge import ArisBridge, ArisRevisionRecord
from .aris_transport import (
    ArisTransportManifest,
    ArisTransportReceipt,
    ArisTransportStatus,
    FixedArisTransport,
    transport_package_sha256,
)
from .baseline_audit import BaselineAudit, BaselineProgram
from .errors import ProtocolValidationError
from .execution_control import (
    DurableExecutionQueue,
    ExecutionDeclaration,
    ExecutionDeclarationRegistry,
    ExecutionRecord,
    ExecutionState,
)
from .execution_evidence import (
    EvidenceReceipt,
    MonitorObservation,
    RestrictedEvidenceInput,
    assemble_decision_packet,
)
from .execution_worker import DeclarationBoundWorker, ExecutionSubmission
from .local_ai_bridge import LocalAIBridge
from .project_status import (
    AuthorityDigest,
    BlockerCategory,
    CandidateStatus,
    EvidenceLink,
    LineageStatus,
    MedRecStatus,
    ProjectStage,
    ProjectStatus,
    StatusBlocker,
)
from .registry import BaselineRegistry
from .reproduction_contract import DecisionPacket, H1Approval, H2Decision, SafeDrugBatchContract
from .research_loop_status import ResearchLoopStatus

Clock = Callable[[], datetime]
RunCommand = Callable[..., subprocess.CompletedProcess[str]]

_REMOTE_PROBE = r"""set -eu
printf 'identity=%s\n' "$(id -un)"
if test -d /root/zhb/medrec-research/.git; then
  printf 'checkout_exists=1\n'
  revision=$(git -C /root/zhb/medrec-research rev-parse HEAD 2>/dev/null || true)
  printf 'revision=%s\n' "$revision"
  if test -z "$(git -C /root/zhb/medrec-research status --porcelain 2>/dev/null)"; then
    printf 'checkout_clean=1\n'
  else
    printf 'checkout_clean=0\n'
  fi
else
  printf 'checkout_exists=0\nrevision=\ncheckout_clean=0\n'
fi
if test -n "${MEDREC_DATA_ROOT:-}" && test -d "$MEDREC_DATA_ROOT"; then
  printf 'data_root_ready=1\n'
else
  printf 'data_root_ready=0\n'
fi
if test -x /root/anaconda3/bin/conda; then
  printf 'conda_available=1\n'
else
  printf 'conda_available=0\n'
fi
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_rows=$(nvidia-smi \
    --query-gpu=memory.free,utilization.gpu \
    --format=csv,noheader,nounits 2>/dev/null || true)
  gpu_count=$(printf '%s\n' "$gpu_rows" | awk 'NF{count++} END{print count+0}')
  gpu_available=$(printf '%s\n' "$gpu_rows" | \
    awk -F',' '($1+0)>=20000 && ($2+0)<=10{count++} END{print count+0}')
  printf 'gpu_count=%s\ngpu_available=%s\n' "$gpu_count" "$gpu_available"
else
  printf 'gpu_count=0\ngpu_available=0\n'
fi
disk_free_kib=$(df -Pk /root/zhb 2>/dev/null | awk 'NR==2{printf "%.0f", $4}')
printf 'disk_free_kib=%s\n' "${disk_free_kib:-0}"
"""


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    from hashlib import sha256

    return sha256(path.read_bytes()).hexdigest()


def _immutable_revision(value: str | None) -> str | None:
    if (
        value is None
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        return None
    return value


def _parse_probe(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in values:
            raise ProtocolValidationError("remote preflight returned an invalid public-safe record")
        values[key] = value
    expected = {
        "checkout_clean",
        "checkout_exists",
        "conda_available",
        "data_root_ready",
        "disk_free_kib",
        "gpu_available",
        "gpu_count",
        "identity",
        "revision",
    }
    if set(values) != expected:
        raise ProtocolValidationError("remote preflight returned an incomplete public-safe record")
    return values


def _probe_integer(value: str) -> int:
    if not value.isascii() or not value.isdigit() or len(value) > 20:
        raise ProtocolValidationError("remote preflight capacity is invalid")
    return int(value)


@dataclass(frozen=True, slots=True)
class RemoteSessionPreflight:
    """Public-safe observation of the real 319 execution plane."""

    observed_at: str
    reachable: bool
    fallback_used: bool
    identity_ok: bool
    checkout_exists: bool
    checkout_clean: bool
    local_revision: str | None
    remote_revision: str | None
    revision_matches: bool
    data_root_ready: bool
    conda_available: bool
    environment_verified: bool
    gpu_count: int
    gpu_available: int
    disk_free_gib: int
    blockers: tuple[str, ...]
    preflight_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if self.local_revision is not None and _immutable_revision(self.local_revision) is None:
            raise ProtocolValidationError("local_revision must be an immutable Git revision")
        if self.remote_revision is not None and _immutable_revision(self.remote_revision) is None:
            raise ProtocolValidationError("remote_revision must be an immutable Git revision")
        for value in (
            self.reachable,
            self.fallback_used,
            self.identity_ok,
            self.checkout_exists,
            self.checkout_clean,
            self.revision_matches,
            self.data_root_ready,
            self.conda_available,
            self.environment_verified,
        ):
            if type(value) is not bool:
                raise ProtocolValidationError("remote preflight flags must be booleans")
        capacity = (self.gpu_count, self.gpu_available, self.disk_free_gib)
        if any(type(value) is not int or value < 0 for value in capacity):
            raise ProtocolValidationError("remote preflight capacity must be nonnegative integers")
        blockers = tuple(dict.fromkeys(self.blockers))
        object.__setattr__(self, "blockers", blockers)
        expected = content_sha256(self._content())
        if self.preflight_sha256 and self.preflight_sha256 != expected:
            raise ProtocolValidationError("remote preflight digest does not match content")
        object.__setattr__(self, "preflight_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "blockers": list(self.blockers),
            "checkout_clean": self.checkout_clean,
            "checkout_exists": self.checkout_exists,
            "conda_available": self.conda_available,
            "data_root_ready": self.data_root_ready,
            "disk_free_gib": self.disk_free_gib,
            "environment_verified": self.environment_verified,
            "fallback_used": self.fallback_used,
            "gpu_available": self.gpu_available,
            "gpu_count": self.gpu_count,
            "identity_ok": self.identity_ok,
            "local_revision": self.local_revision,
            "observed_at": self.observed_at,
            "reachable": self.reachable,
            "remote_revision": self.remote_revision,
            "revision_matches": self.revision_matches,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._content(),
            "kind": "remote_session_preflight",
            "preflight_sha256": self.preflight_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }


def run_remote_preflight(
    *,
    local_revision: str | None,
    clock: Clock,
    runner: RunCommand = subprocess.run,
    timeout_seconds: int = 12,
) -> RemoteSessionPreflight:
    """Try the documented 319 aliases and run one fixed read-only probe."""

    values: dict[str, str] | None = None
    fallback_used = False
    for index, profile in enumerate(("319-lab", "319-lab-via-server")):
        try:
            result = runner(
                [
                    "rtk",
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    f"ConnectTimeout={timeout_seconds}",
                    profile,
                    "sh",
                    "-s",
                ],
                input=_REMOTE_PROBE,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue
        try:
            candidate = _parse_probe(result.stdout)
        except ProtocolValidationError:
            continue
        if candidate["identity"] != "root":
            continue
        values = candidate
        fallback_used = index == 1
        break

    local = _immutable_revision(local_revision)
    if values is None:
        return RemoteSessionPreflight(
            observed_at=_timestamp(clock()),
            reachable=False,
            fallback_used=False,
            identity_ok=False,
            checkout_exists=False,
            checkout_clean=False,
            local_revision=local,
            remote_revision=None,
            revision_matches=False,
            data_root_ready=False,
            conda_available=False,
            environment_verified=False,
            gpu_count=0,
            gpu_available=0,
            disk_free_gib=0,
            blockers=("remote-unreachable",),
        )

    remote = _immutable_revision(values["revision"])
    checkout_exists = values["checkout_exists"] == "1"
    checkout_clean = values["checkout_clean"] == "1"
    data_root_ready = values["data_root_ready"] == "1"
    conda_available = values["conda_available"] == "1"
    try:
        gpu_count = _probe_integer(values["gpu_count"])
        gpu_available = _probe_integer(values["gpu_available"])
        disk_free_kib = _probe_integer(values["disk_free_kib"])
    except ProtocolValidationError:
        return RemoteSessionPreflight(
            observed_at=_timestamp(clock()),
            reachable=False,
            fallback_used=fallback_used,
            identity_ok=True,
            checkout_exists=checkout_exists,
            checkout_clean=checkout_clean,
            local_revision=local,
            remote_revision=remote,
            revision_matches=False,
            data_root_ready=False,
            conda_available=False,
            environment_verified=False,
            gpu_count=0,
            gpu_available=0,
            disk_free_gib=0,
            blockers=("remote-preflight-invalid",),
        )
    revision_matches = local is not None and remote == local
    blockers: list[str] = []
    if not checkout_exists:
        blockers.append("remote-checkout-missing")
    elif not checkout_clean:
        blockers.append("remote-checkout-dirty")
    if not revision_matches:
        blockers.append("remote-revision-mismatch")
    if not data_root_ready:
        blockers.append("remote-data-root-missing")
    if not conda_available:
        blockers.append("remote-conda-unavailable")
    blockers.append("remote-environment-unverified")
    if gpu_available < 1:
        blockers.append("remote-gpu-unavailable")
    if disk_free_kib < 100 * 1024 * 1024:
        blockers.append("remote-disk-headroom-low")
    return RemoteSessionPreflight(
        observed_at=_timestamp(clock()),
        reachable=True,
        fallback_used=fallback_used,
        identity_ok=True,
        checkout_exists=checkout_exists,
        checkout_clean=checkout_clean,
        local_revision=local,
        remote_revision=remote,
        revision_matches=revision_matches,
        data_root_ready=data_root_ready,
        conda_available=conda_available,
        environment_verified=False,
        gpu_count=gpu_count,
        gpu_available=gpu_available,
        disk_free_gib=disk_free_kib // (1024 * 1024),
        blockers=tuple(blockers),
    )


def _git_value(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _lineage(
    program: BaselineProgram, audits: tuple[BaselineAudit, ...]
) -> tuple[LineageStatus, ...]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for audit in audits:
        sources = {item.source_id: item.repository for item in audit.sources}
        evidence = {item.evidence_id: item for item in audit.evidence}
        for edge in audit.lineage:
            repository = sources.get(edge.upstream, audit.sources[0].repository)
            group = grouped.setdefault((edge.layer, repository), {"candidate_ids": [], "links": {}})
            if audit.baseline_id not in group["candidate_ids"]:
                group["candidate_ids"].append(audit.baseline_id)
            for evidence_id in edge.evidence_ids:
                item = evidence[evidence_id]
                group["links"][evidence_id] = EvidenceLink(evidence_id, item.immutable_url)
    order = {candidate_id: index for index, candidate_id in enumerate(program.candidate_ids)}
    return tuple(
        sorted(
            (
                LineageStatus(
                    layer=layer,
                    upstream_repository=repository,
                    candidate_ids=tuple(sorted(group["candidate_ids"], key=order.__getitem__)),
                    evidence=tuple(group["links"][key] for key in sorted(group["links"])),
                )
                for (layer, repository), group in grouped.items()
            ),
            key=lambda item: (item.layer, item.upstream_repository),
        )
    )


def _load_optional(path: Path, loader: Callable[[str], Any]) -> Any | None:
    if not path.is_file():
        return None
    try:
        return loader(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ProtocolValidationError):
        return None


class ResearchSession:
    """Own ignored session records and expose only bounded human decisions."""

    def __init__(self, root: Path, *, clock: Clock, runtime: Path | None = None) -> None:
        self.root = root.resolve()
        self.clock = clock
        self.runtime = (self.root / "runtime" / "hitl") if runtime is None else runtime.resolve()
        self.status_path = self.runtime / "project-status.json"
        self.loop_path = self.runtime / "research-loop.json"
        self.preflight_path = self.runtime / "remote-preflight.json"
        self.aris_revision_path = self.runtime / "aris-revision.json"
        self.authority_bundle_path = self.runtime / "authority-bundle.json"
        self.action_request_dir = self.runtime / "action-requests"
        self.execution_dir = self.runtime / "executions"
        self.submission_dir = self.runtime / "submissions"
        self.transport_manifest_dir = self.runtime / "transport-manifests"
        self.transport_receipt_dir = self.runtime / "transport-receipts"
        self.monitor_dir = self.runtime / "monitor"
        self.evidence_dir = self.runtime / "evidence"
        self.contract_path = self.runtime / "contract.json"
        self.h1_path = self.runtime / "h1.json"
        self.packet_dir = self.runtime / "packets"
        self.h2_dir = self.runtime / "h2"
        self.preflight: RemoteSessionPreflight | None = None
        self.aris_revision: ArisRevisionRecord | None = None
        manifest_path = self.root / ".aris" / "installed-skills-codex.txt"
        self.aris_bridge = ArisBridge(
            self._aris_repository_from_manifest(),
            self.aris_revision_path,
            clock=clock,
            manifest_path=manifest_path,
        )
        self.execution_registry = ExecutionDeclarationRegistry.load_package()
        self.execution_queue = DurableExecutionQueue(self.execution_dir, clock=clock)
        self.aris_transport = FixedArisTransport(self.transport_receipt_dir, clock=clock)
        self.ai_bridge = LocalAIBridge(self.root)
        self._decision_lock = Lock()
        self._transport_lock = RLock()
        self._last_transport_poll: datetime | None = None

    @property
    def actions_enabled(self) -> bool:
        bundle = self.authority_bundle()
        contract, h1, _, _, _ = self._records()
        return bool(
            bundle is not None
            and self.preflight is not None
            and self.aris_revision is not None
            and self.aris_revision.candidate_valid
            and not self.aris_revision.fallback_used
            and contract is not None
            and h1 is not None
            and h1.is_current(contract)
        )

    def prepare(self, *, timeout_seconds: int = 12) -> tuple[ProjectStatus, ResearchLoopStatus]:
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.packet_dir.mkdir(exist_ok=True)
        self.h2_dir.mkdir(exist_ok=True)
        self.action_request_dir.mkdir(exist_ok=True)
        self.execution_dir.mkdir(exist_ok=True)
        self.monitor_dir.mkdir(exist_ok=True)
        self.evidence_dir.mkdir(exist_ok=True)
        self.submission_dir.mkdir(exist_ok=True)
        self.transport_manifest_dir.mkdir(exist_ok=True)
        self.transport_receipt_dir.mkdir(exist_ok=True)
        self.aris_revision = self.aris_bridge.activate()
        if not self.aris_revision.candidate_valid:
            raise ProtocolValidationError(
                "ARIS candidate validation failed; last-known-good was retained without startup"
            )
        local_revision = _git_value(self.root, "rev-parse", "HEAD")
        self.preflight = run_remote_preflight(
            local_revision=local_revision,
            clock=self.clock,
            timeout_seconds=timeout_seconds,
        )
        write_json_atomic(self.preflight_path, self.preflight.to_dict())
        status = self._publish_status(local_revision)
        loop = self.refresh_loop()
        return status, loop

    def _authoritative_inputs(
        self,
    ) -> tuple[BaselineProgram, tuple[BaselineAudit, ...], BaselineRegistry]:
        program = BaselineProgram.load(self.root / "baselines/programs/final-five.toml")
        audits = tuple(
            BaselineAudit.load(self.root / "baselines/audits" / f"{candidate_id}.toml")
            for candidate_id in program.candidate_ids
        )
        program.validate_audits(audits)
        return program, audits, BaselineRegistry.load(self.root / "baselines/registry.toml")

    def _aris_repository_from_manifest(self) -> Path:
        manifest = self.root / ".aris" / "installed-skills-codex.txt"
        if not manifest.is_file():
            return self.root / ".aris" / "missing-repository"
        try:
            rows = [
                line.split("\t", 1) for line in manifest.read_text(encoding="utf-8").splitlines()
            ]
            values = {row[0]: row[1] for row in rows if len(row) == 2}
            return Path(values["repo_root"])
        except (OSError, KeyError, UnicodeError):
            return self.root / ".aris" / "invalid-repository"

    def _aris_manifest(self) -> tuple[str | None, tuple[str, ...]]:
        manifest = self.root / ".aris/installed-skills-codex.txt"
        if not manifest.is_file():
            return None, ("aris-install-missing",)
        try:
            digest = _sha256_file(manifest)
        except (OSError, UnicodeError):
            return None, ("aris-install-invalid",)
        if self.aris_revision is None:
            try:
                self.aris_revision = self.aris_bridge.activate()
            except ProtocolValidationError:
                return digest, ("aris-revision-invalid",)
        blockers = tuple(self.aris_revision.blockers)
        if self.aris_revision.manifest_sha256 != digest:
            blockers = (*blockers, "aris-manifest-digest-mismatch")
        return digest, tuple(dict.fromkeys(blockers))

    def _publish_status(self, local_revision: str | None) -> ProjectStatus:
        if self.preflight is None:
            raise RuntimeError("session preflight must run before status publication")
        program, audits, registry = self._authoritative_inputs()
        audit_by_id = {audit.baseline_id: audit for audit in audits}
        candidates = tuple(
            CandidateStatus(
                candidate_id=candidate_id,
                display_name=audit_by_id[candidate_id].display_name,
                readiness=registry.get(candidate_id).readiness.value,
                source_gate=audit_by_id[candidate_id].claim("source").disposition.value,
                license_gate=audit_by_id[candidate_id].claim("license").disposition.value,
                evidence=tuple(
                    EvidenceLink(item.evidence_id, item.immutable_url)
                    for item in audit_by_id[candidate_id].evidence
                ),
            )
            for candidate_id in program.candidate_ids
        )
        blockers: list[StatusBlocker] = []
        for candidate in candidates:
            if candidate.source_gate != "pass":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.SOURCE_LICENSE,
                        "source-gate-unresolved",
                        candidate.candidate_id,
                    )
                )
            if candidate.license_gate != "pass":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.SOURCE_LICENSE,
                        "license-gate-unresolved",
                        candidate.candidate_id,
                    )
                )
            if candidate.readiness == "registered":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.READINESS,
                        "baseline-not-smoke-ready",
                        candidate.candidate_id,
                    )
                )
        blockers.extend(
            StatusBlocker(BlockerCategory.REMOTE_PREFLIGHT, reason)
            for reason in self.preflight.blockers
        )
        aris_digest, aris_blockers = self._aris_manifest()
        blockers.extend(
            StatusBlocker(BlockerCategory.STATUS_INTEGRITY, reason) for reason in aris_blockers
        )
        if local_revision is None or _immutable_revision(local_revision) is None:
            blockers.append(
                StatusBlocker(BlockerCategory.STATUS_INTEGRITY, "local-source-uncommitted")
            )
        if _git_value(self.root, "status", "--porcelain"):
            blockers.append(StatusBlocker(BlockerCategory.STATUS_INTEGRITY, "local-worktree-dirty"))
        if not self.actions_enabled:
            blockers.append(
                StatusBlocker(BlockerCategory.AUTHORIZATION, "action-authority-missing")
            )
        if not self.contract_path.is_file():
            blockers.append(
                StatusBlocker(BlockerCategory.READINESS, "reproduction-contract-missing")
            )

        payload = MedRecStatus.create(
            stage=ProjectStage.AUDIT_BLOCKED,
            qualified_count=sum(
                candidate.readiness == "comparison_ready" for candidate in candidates
            ),
            review_state="pending",
            discovery_eligible=False,
            candidates=candidates,
            shared_lineage=_lineage(program, audits),
        )
        authorities = [
            AuthorityDigest("program", program.program_sha256),
            AuthorityDigest(
                "audit-set",
                content_sha256({"audits": [item.audit_sha256 for item in audits]}),
            ),
            AuthorityDigest("registry", content_sha256(registry.to_dict())),
            AuthorityDigest("remote-preflight", self.preflight.preflight_sha256),
        ]
        if aris_digest is not None:
            authorities.append(AuthorityDigest("aris-install", aris_digest))
        if self.aris_revision is not None:
            authorities.append(AuthorityDigest("aris-revision", self.aris_revision.revision_sha256))
        if local_revision is not None:
            authorities.append(
                AuthorityDigest("local-source", content_sha256({"revision": local_revision}))
            )
        snapshot = ProjectStatus.create(
            project_id="medrec-research",
            authorities=authorities,
            blockers=blockers,
            payload=payload,
            clock=self.clock,
            freshness=timedelta(minutes=30),
        )
        snapshot.write_atomic(self.status_path)
        return snapshot

    def _records(
        self,
    ) -> tuple[
        SafeDrugBatchContract | None,
        H1Approval | None,
        tuple[DecisionPacket, ...],
        dict[str, H2Decision],
        tuple[str, ...],
    ]:
        blockers: list[str] = []
        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None:
            blockers.append("contract-missing-or-invalid")
        h1 = _load_optional(self.h1_path, H1Approval.from_json)
        packets: list[DecisionPacket] = []
        for path in sorted(self.packet_dir.glob("*.json")):
            packet = _load_optional(path, DecisionPacket.from_json)
            if packet is None:
                blockers.append("packet-invalid")
            else:
                packets.append(packet)
        h2_by_packet: dict[str, H2Decision] = {}
        conflicted_packets: set[str] = set()
        for path in sorted(self.h2_dir.glob("*.json")):
            decision = _load_optional(path, H2Decision.from_json)
            if decision is None:
                blockers.append("h2-invalid")
            else:
                existing = h2_by_packet.get(decision.packet_sha256)
                if existing is not None and existing.to_dict() != decision.to_dict():
                    conflicted_packets.add(decision.packet_sha256)
                    blockers.append("h2-conflict")
                else:
                    h2_by_packet[decision.packet_sha256] = decision
        for packet_sha256 in conflicted_packets:
            h2_by_packet.pop(packet_sha256, None)
        decisions = {
            packet.lane_id: h2_by_packet[packet.packet_sha256]
            for packet in packets
            if packet.packet_sha256 in h2_by_packet
        }
        if not packets:
            blockers.append("decision-packets-missing")
        return contract, h1, tuple(packets), decisions, tuple(dict.fromkeys(blockers))

    def refresh_loop(self) -> ResearchLoopStatus:
        contract, h1, packets, decisions, record_blockers = self._records()
        loop = ResearchLoopStatus.create(
            contract=contract,
            h1=h1,
            packets=packets,
            h2_decisions=decisions,
        )
        remote_blockers = (
            self.preflight.blockers if self.preflight is not None else ("preflight-missing",)
        )
        blockers = tuple(dict.fromkeys((*loop.blockers, *record_blockers, *remote_blockers)))
        loop = ResearchLoopStatus(
            contract_sha256=loop.contract_sha256,
            h1_current=loop.h1_current,
            lanes=loop.lanes,
            blockers=blockers,
            stale=loop.stale or bool(blockers),
        )
        write_json_atomic(self.loop_path, loop.to_dict())
        return loop

    def control_state(self) -> dict[str, object]:
        contract, h1, packets, decisions, record_blockers = self._records()
        h1_current = bool(contract is not None and h1 is not None and h1.is_current(contract))
        lanes = []
        for packet in packets:
            decision = decisions.get(packet.lane_id)
            matches_contract = bool(
                contract is not None and packet.contract_sha256 == contract.contract_sha256
            )
            lanes.append(
                {
                    "current_action": decision.action.value if decision is not None else None,
                    "enabled": h1_current and packet.is_current and matches_contract,
                    "go_eligible": packet.go_eligible,
                    "lane_id": packet.lane_id,
                }
            )
        return {
            "blockers": list(record_blockers),
            "h1": {
                "current": h1_current,
                "enabled": contract is not None and contract.is_current(),
                "owner": h1.owner if h1_current and h1 is not None else None,
            },
            "h2": lanes,
            "kind": "hitl_control",
            "schema_version": 1,
        }

    def contract_state(self) -> dict[str, object]:
        """Expose only the current contract's public-safe questionnaire fields."""

        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None or not contract.is_current():
            raise ProtocolValidationError("research contract is unavailable or stale")
        models = [
            {
                "model_id": annex.model_id,
                "mode": annex.mode.value if hasattr(annex.mode, "value") else str(annex.mode),
                "required_outcomes": list(annex.required_outcomes),
            }
            for annex in contract.model_annexes
        ]
        metric_intervals = {
            annex.model_id: annex.metric_intervals for annex in contract.model_annexes
        }
        sections = (
            {
                "id": "problem",
                "label": "研究问题",
                "provenance": "derived",
                "value": (
                    "在 SafeDrug main 固定来源上进行 source-native reproduction, "
                    "并分别审阅四条模型 lane。"
                ),
            },
            {
                "id": "hypotheses",
                "label": "竞争性假设",
                "provenance": "derived",
                "value": canonical_json(models),
            },
            {
                "id": "data_lineage",
                "label": "数据 lineage",
                "provenance": "protected",
                "value": canonical_json(contract.dataset_lineage),
            },
            {
                "id": "mode",
                "label": "执行模式",
                "provenance": "protected",
                "value": canonical_json(sorted({item["mode"] for item in models})),
            },
            {
                "id": "evidence_duties",
                "label": "证据职责",
                "provenance": "protected",
                "value": canonical_json(
                    {
                        "required_outcomes": sorted(
                            {outcome for item in models for outcome in item["required_outcomes"]}
                        ),
                        "public_evidence_urls": list(contract.evidence_urls),
                    }
                ),
            },
            {
                "id": "acceptance",
                "label": "验收边界",
                "provenance": "protected",
                "value": canonical_json(metric_intervals),
            },
            {
                "id": "stopping_rules",
                "label": "停止条件",
                "provenance": "protected",
                "value": canonical_json(contract.stopping_rules),
            },
            {
                "id": "resource_ceiling",
                "label": "资源上限",
                "provenance": "protected",
                "value": canonical_json(contract.resource_ceiling),
            },
            {
                "id": "repair_budget",
                "label": "契约内修复预算",
                "provenance": "protected",
                "value": canonical_json(contract.repair_budget),
            },
            {
                "id": "non_waivable_boundaries",
                "label": "不可豁免边界",
                "provenance": "protected",
                "value": canonical_json(list(contract.non_waivable_boundaries)),
            },
        )
        ai_status, ai_reason = self.ai_bridge.availability()
        return {
            "ai": {
                "reason_code": ai_reason,
                "status": ai_status,
            },
            "contract_sha256": contract.contract_sha256,
            "kind": "research_contract",
            "questionnaire": list(sections),
            "schema_version": 1,
            "source": {
                "branch": contract.source_branch,
                "repository": contract.source_repository,
                "revision": contract.source_revision,
            },
            "status": "current",
        }

    def contract_ai(self, value: Mapping[str, object]) -> dict[str, object]:
        """Run a bounded local draft/challenge without changing any research record."""

        payload = strict_fields(
            value,
            required=("kind", "schema_version", "operation", "request_id"),
            context="contract AI input",
        )
        if payload.pop("kind") != "contract_ai_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("contract AI input schema or kind is invalid")
        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None or not contract.is_current():
            raise ProtocolValidationError("contract AI requires a current contract")
        state = self.contract_state()
        result = self.ai_bridge.run(
            operation=payload["operation"],
            request_id=payload["request_id"],
            questionnaire=state["questionnaire"],
        )
        return {
            **result.to_dict(),
            "contract_sha256": contract.contract_sha256,
        }

    def decision_packet_state(self) -> dict[str, object]:
        """Expose aggregate packet evidence without paths or restricted artifacts."""

        contract, _, packets, _, record_blockers = self._records()
        if contract is None:
            raise ProtocolValidationError("decision packets require a current contract")
        receipts, receipt_blockers = self._evidence_receipts()
        records = []
        for packet in packets:
            receipt = receipts.get(packet.packet_sha256)
            evidence_ready = not self.evidence_dir.is_dir() or (
                receipt is not None and not receipt_blockers
            )
            attempts = [
                {
                    "attempt_id": item.attempt_id,
                    "artifact_digests": dict(item.artifact_digests),
                    "deviations": list(item.deviations),
                    "lane_id": item.lane_id,
                    "outcomes": item.to_dict()["outcomes"],
                    "status": item.status.value,
                    "uncertainty": item.to_dict()["uncertainty"],
                    "validity": item.validity.value,
                }
                for item in packet.attempts
            ]
            records.append(
                {
                    "attempts": attempts,
                    "blockers": list(packet.blockers),
                    "conclusion": packet.conclusion.value,
                    "current": (
                        packet.is_current and packet.contract_sha256 == contract.contract_sha256
                    ),
                    "go_eligible": packet.go_eligible and evidence_ready,
                    "lane_id": packet.lane_id,
                    "limitations": list(packet.limitations),
                    "packet_id": packet.packet_id,
                    "packet_sha256": packet.packet_sha256,
                    "raw_aggregate_table": (
                        list(receipt.aggregate_table)
                        if receipt is not None and not receipt_blockers
                        else None
                    ),
                    "raw_artifact_reason": (
                        "raw-aggregate-table-available"
                        if receipt is not None and not receipt_blockers
                        else "raw-aggregate-table-unavailable"
                    ),
                    "required_outcomes": list(packet.required_outcomes),
                    "uncertainty": packet.to_dict()["uncertainty"],
                    "validity": packet.validity.value,
                    "outcomes": packet.to_dict()["outcomes"],
                }
            )
        return {
            "blockers": list(dict.fromkeys((*record_blockers, *receipt_blockers))),
            "contract_sha256": contract.contract_sha256,
            "kind": "decision_packet_control",
            "packets": records,
            "schema_version": 1,
        }

    def _evidence_receipts(self) -> tuple[dict[str, EvidenceReceipt], tuple[str, ...]]:
        if not self.evidence_dir.is_dir():
            return {}, ()
        receipts: dict[str, EvidenceReceipt] = {}
        blockers: list[str] = []
        conflicted: set[str] = set()
        for path in sorted(self.evidence_dir.glob("*.json")):
            receipt = _load_optional(path, EvidenceReceipt.from_json)
            if receipt is None:
                blockers.append("evidence-receipt-invalid")
                continue
            if receipt.packet_sha256 in conflicted:
                continue
            existing = receipts.get(receipt.packet_sha256)
            if existing is not None and existing.to_dict() != receipt.to_dict():
                blockers.append("evidence-receipt-conflict")
                receipts.pop(receipt.packet_sha256, None)
                conflicted.add(receipt.packet_sha256)
                continue
            receipts[receipt.packet_sha256] = receipt
        return receipts, tuple(dict.fromkeys(blockers))

    def create_h1(self, value: Mapping[str, object]) -> dict[str, object]:
        payload = strict_fields(
            value,
            required=("kind", "schema_version", "owner", "rationale"),
            context="H1 input",
        )
        if payload.pop("kind") != "h1_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("H1 input schema or kind is invalid")
        with self._decision_lock:
            contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
            if contract is None:
                raise ProtocolValidationError("H1 requires a current production contract")
            existing = _load_optional(self.h1_path, H1Approval.from_json)
            if self.h1_path.is_file() and existing is None:
                raise ProtocolValidationError("current H1 record is invalid")
            if existing is not None and existing.is_current(contract):
                if (
                    existing.owner == payload["owner"]
                    and existing.rationale == payload["rationale"]
                ):
                    self.refresh_loop()
                    return existing.to_dict()
                raise ProtocolValidationError("H1 approval for this contract is immutable")
            approval = H1Approval.create(
                contract,
                owner=payload["owner"],
                rationale=payload["rationale"],
                approved_at=_timestamp(self.clock()),
            )
            write_json_atomic(self.h1_path, approval.to_dict())
            self.refresh_loop()
            return approval.to_dict()

    def create_h2(self, value: Mapping[str, object]) -> dict[str, object]:
        payload = strict_fields(
            value,
            required=("kind", "schema_version", "lane_id", "researcher", "action", "rationale"),
            context="H2 input",
        )
        if payload.pop("kind") != "h2_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("H2 input schema or kind is invalid")
        with self._decision_lock:
            contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
            h1 = _load_optional(self.h1_path, H1Approval.from_json)
            if contract is None or h1 is None or not h1.is_current(contract):
                raise ProtocolValidationError("H2 requires current H1 authority")
            lane_id = payload.pop("lane_id")
            packets = [
                packet
                for path in sorted(self.packet_dir.glob("*.json"))
                if (packet := _load_optional(path, DecisionPacket.from_json)) is not None
                and packet.lane_id == lane_id
            ]
            if len(packets) != 1:
                raise ProtocolValidationError("H2 requires exactly one current lane packet")
            receipts, receipt_blockers = self._evidence_receipts()
            if self.evidence_dir.is_dir() and (
                receipt_blockers or receipts.get(packets[0].packet_sha256) is None
            ):
                raise ProtocolValidationError("H2 requires a valid evidence receipt")
            decision = H2Decision.create(
                contract=contract,
                packet=packets[0],
                researcher=payload["researcher"],
                action=payload["action"],
                rationale=payload["rationale"],
                issued_at=_timestamp(self.clock()),
            )
            existing = [
                item
                for path in sorted(self.h2_dir.glob("*.json"))
                if (item := _load_optional(path, H2Decision.from_json)) is not None
                and item.packet_sha256 == decision.packet_sha256
            ]
            if existing:
                if any(item.to_dict() != existing[0].to_dict() for item in existing[1:]):
                    raise ProtocolValidationError("H2 records for this packet conflict")
                current = existing[0]
                same_input = (
                    current.contract_sha256 == decision.contract_sha256
                    and current.packet_sha256 == decision.packet_sha256
                    and current.researcher == decision.researcher
                    and current.action == decision.action
                    and current.rationale == decision.rationale
                )
                if same_input:
                    self.refresh_loop()
                    return current.to_dict()
                raise ProtocolValidationError("H2 decision for this packet is immutable")
            write_json_atomic(self.h2_dir / f"{decision.packet_sha256}.json", decision.to_dict())
            self.refresh_loop()
            return decision.to_dict()

    def authority_bundle(self) -> AuthorityBundle | None:
        if not self.authority_bundle_path.is_file():
            return None
        try:
            return AuthorityBundle.load(self.authority_bundle_path)
        except (OSError, UnicodeError, ProtocolValidationError):
            return None

    def _execution_binding(
        self, action_id: str
    ) -> tuple[SafeDrugBatchContract, H1Approval, str | None, str]:
        contract, h1, packets, decisions, _ = self._records()
        if contract is None or h1 is None or not h1.is_current(contract):
            raise ProtocolValidationError("execution requires current H1 authority")
        current_records = [
            record
            for record in self.execution_queue.records()
            if record.contract_sha256 == contract.contract_sha256
            and record.h1_approval_sha256 == h1.approval_sha256
        ]
        current_record = (
            max(current_records, key=lambda record: record.events[-1].journal_sequence)
            if current_records
            else None
        )
        current_lane_id = (
            current_record.lane_id
            if current_record is not None
            else self.execution_registry.initial_lane_id
        )
        packets_by_lane = {packet.lane_id: packet for packet in packets}
        packet = packets_by_lane.get(current_lane_id)
        decision = decisions.get(current_lane_id)
        if decision is not None and (
            packet is None or not decision.is_current(contract=contract, packet=packet)
        ):
            decision = None
        if action_id != "request_next_lane":
            if decision is not None:
                raise ProtocolValidationError("decided lane cannot continue execution")
            return (
                contract,
                h1,
                current_record.h2_decision_sha256 if current_record is not None else None,
                current_lane_id,
            )
        if decision is None or not decision.go_eligible:
            raise ProtocolValidationError("next lane requires current H2 GO")
        lane_ids = self.execution_registry.lane_ids
        try:
            lane_id = lane_ids[lane_ids.index(current_lane_id) + 1]
        except (ValueError, IndexError) as error:
            raise ProtocolValidationError("no next registered execution lane") from error
        return contract, h1, decision.decision_sha256, lane_id

    def queue_action_request(self, value: Mapping[str, object]) -> dict[str, object]:
        request = ActionRequest.from_dict(value)
        contract, h1, h2_decision_sha256, lane_id = self._execution_binding(request.action_id)
        declaration = self.execution_registry.get(lane_id, request.action_id)
        write_json_atomic(
            self.action_request_dir / f"{request.request_sha256}.json",
            request.to_dict(),
        )
        record = self.execution_queue.enqueue(
            request=request,
            declaration=declaration,
            contract_sha256=contract.contract_sha256,
            h1_approval_sha256=h1.approval_sha256,
            h2_decision_sha256=h2_decision_sha256,
            blockers=(
                self.preflight.blockers if self.preflight is not None else ("preflight-missing",)
            ),
        )
        self._dispatch_pending()
        return self.execution_queue.load(record.request_sha256).to_public_dict()

    def _dispatch_pending(self) -> tuple[ExecutionSubmission, ...]:
        with self._transport_lock:
            worker = DeclarationBoundWorker(
                self.execution_queue,
                self.action_request_dir,
                self.submission_dir,
                clock=self.clock,
            )
            prepared = []
            for record in self.execution_queue.records():
                if record.state is not ExecutionState.QUEUED:
                    continue
                try:
                    declaration = self.execution_registry.get(record.lane_id, record.action_id)
                    submission = worker.prepare(
                        record,
                        declaration,
                        aris_revision=self.aris_revision,
                    )
                    prepared.append(submission)
                    if submission.status != "awaiting-aris-bridge":
                        continue
                    manifest = self._transport_manifest(record, submission, declaration)
                    receipt = self.aris_transport.submit(
                        manifest,
                        fallback_used=self._transport_fallback_used(),
                    )
                    self._apply_transport_receipt(record, receipt)
                except ProtocolValidationError:
                    current = self.execution_queue.load(record.request_sha256)
                    if current.state is ExecutionState.QUEUED:
                        self.execution_queue.transition(
                            record.request_sha256,
                            state=ExecutionState.REVIEW_PENDING,
                            reason_code="execution-dispatch-invalid",
                        )
            return tuple(prepared)

    def _transport_fallback_used(self) -> bool:
        if self.preflight is None:
            raise ProtocolValidationError("ARIS transport requires remote preflight")
        return self.preflight.fallback_used

    def _transport_manifest(
        self,
        record: ExecutionRecord,
        submission: ExecutionSubmission,
        declaration: ExecutionDeclaration,
    ) -> ArisTransportManifest:
        if self.preflight is None or self.preflight.blockers:
            raise ProtocolValidationError("ARIS transport requires a clear remote preflight")
        if not self.preflight.environment_verified:
            raise ProtocolValidationError("ARIS transport requires a verified remote environment")
        if self.aris_revision is None or not self.aris_revision.candidate_valid:
            raise ProtocolValidationError("ARIS transport requires a valid ARIS revision")
        if self.aris_revision.active_revision is None:
            raise ProtocolValidationError("ARIS transport requires an active ARIS revision")
        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None or contract.contract_sha256 != record.contract_sha256:
            raise ProtocolValidationError("ARIS transport contract binding changed")
        contract_values = contract.to_dict()
        stopping_rules = contract_values["stopping_rules"]
        resource_ceiling = contract_values["resource_ceiling"]
        if not isinstance(stopping_rules, Mapping) or not isinstance(resource_ceiling, Mapping):
            raise ProtocolValidationError("ARIS transport resource authority is invalid")
        max_attempts = stopping_rules.get("max_attempts")
        gpu_count = resource_ceiling.get("gpu_count")
        if type(max_attempts) is not int or max_attempts < 1:
            raise ProtocolValidationError("ARIS transport max_attempts is invalid")
        if type(gpu_count) is not int or gpu_count < 1:
            raise ProtocolValidationError("ARIS transport gpu_count is invalid")
        manifest = ArisTransportManifest(
            request_sha256=record.request_sha256,
            submission_sha256=submission.submission_sha256,
            declaration_sha256=declaration.declaration_sha256,
            contract_sha256=record.contract_sha256,
            h1_approval_sha256=record.h1_approval_sha256,
            preflight_sha256=self.preflight.preflight_sha256,
            transport_policy_sha256=self.aris_transport.registry.policy_sha256,
            transport_package_sha256=transport_package_sha256(),
            queue_manager_sha256=_sha256_file(
                self.aris_bridge.repository / self.aris_transport.registry.queue_manager_relative
            ),
            aris_revision=self.aris_revision.active_revision,
            project_id=declaration.project_id,
            target_id=declaration.target_id,
            lane_id=declaration.lane_id,
            action_id=declaration.action_id,
            source_revision=declaration.source_revision,
            environment_id=declaration.environment_id,
            resource_profile_id=declaration.resource_profile_id,
            command_template_id=declaration.command_template_id,
            launch_template_id=declaration.launch_template_id,
            evidence_schema_id=declaration.evidence_schema_id,
            source_path_id=declaration.source_path_id,
            data_path_id=declaration.data_path_id,
            output_path_id=declaration.output_path_id,
            max_attempts=max_attempts,
            gpu_count=gpu_count,
        )
        self.transport_manifest_dir.mkdir(parents=True, exist_ok=True)
        path = self.transport_manifest_dir / f"{record.request_sha256}.json"
        if path.is_file():
            existing = ArisTransportManifest.from_json(path.read_text(encoding="utf-8"))
            if existing.to_dict() != manifest.to_dict():
                raise ProtocolValidationError("ARIS transport manifest conflicts with history")
            return existing
        write_json_atomic(path, manifest.to_dict())
        return manifest

    def _load_transport_manifest(self, request_sha256: str) -> ArisTransportManifest:
        try:
            return ArisTransportManifest.from_json(
                (self.transport_manifest_dir / f"{request_sha256}.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("ARIS transport manifest is unavailable") from error

    def _apply_transport_receipt(
        self,
        record: ExecutionRecord,
        receipt: ArisTransportReceipt,
        *,
        recovering: bool = False,
    ) -> ExecutionRecord:
        if receipt.request_sha256 != record.request_sha256:
            raise ProtocolValidationError("ARIS transport receipt request binding changed")
        paths = {
            ArisTransportStatus.ACCEPTED: (ExecutionState.SUBMITTING,),
            ArisTransportStatus.PENDING: (ExecutionState.SUBMITTING,),
            ArisTransportStatus.RUNNING: (
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
            ),
            ArisTransportStatus.COMPLETED: (
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
                ExecutionState.INTAKE,
            ),
            ArisTransportStatus.FAILED: (ExecutionState.REVIEW_PENDING,),
            ArisTransportStatus.TRANSPORT_FAILURE: (ExecutionState.REVIEW_PENDING,),
            ArisTransportStatus.STUCK: (ExecutionState.STUCK,),
            ArisTransportStatus.CANCELLED: (ExecutionState.CANCELLED,),
        }
        target_path = paths[receipt.status]
        current = self.execution_queue.load(record.request_sha256)
        if current.state in {
            ExecutionState.COMPLETED,
            ExecutionState.CANCELLED,
            ExecutionState.FAILED,
            ExecutionState.STUCK,
        }:
            return current
        for target in target_path:
            current = self.execution_queue.load(record.request_sha256)
            if current.state is target:
                continue
            if target is ExecutionState.SUBMITTING:
                allowed = {ExecutionState.QUEUED}
                if recovering:
                    allowed.add(ExecutionState.REVIEW_PENDING)
                if current.state not in allowed:
                    continue
            if target is ExecutionState.RUNNING and current.state is not ExecutionState.SUBMITTING:
                continue
            if target is ExecutionState.MONITORING and current.state is not ExecutionState.RUNNING:
                continue
            if target is ExecutionState.INTAKE and current.state is not ExecutionState.MONITORING:
                continue
            current = self.execution_queue.transition(
                record.request_sha256,
                state=target,
                reason_code=(
                    receipt.reason_code if target is target_path[-1] else "aris-state-observed"
                ),
            )
        return current

    def advance_transport(self, *, force: bool = False) -> tuple[dict[str, object], ...]:
        """Submit queued declarations and poll active ARIS receipts on a bounded cadence."""

        with self._transport_lock:
            now = self.clock()
            if now.tzinfo is None:
                raise ProtocolValidationError("ARIS transport clock must be aware")
            if (
                not force
                and self._last_transport_poll is not None
                and (now - self._last_transport_poll).total_seconds()
                < self.aris_transport.registry.poll_seconds
            ):
                return ()
            self._last_transport_poll = now
            self._dispatch_pending()
            updated = []
            for receipt in self.aris_transport.records():
                record = self.execution_queue.load(receipt.request_sha256)
                if record.state not in {
                    ExecutionState.SUBMITTING,
                    ExecutionState.RUNNING,
                    ExecutionState.MONITORING,
                }:
                    continue
                try:
                    manifest = self._load_transport_manifest(receipt.request_sha256)
                    observed = self.aris_transport.monitor(
                        manifest,
                        fallback_used=self._transport_fallback_used(),
                    )
                    current = self._apply_transport_receipt(record, observed)
                except ProtocolValidationError:
                    current = self.execution_queue.load(record.request_sha256)
                    if current.state in {
                        ExecutionState.SUBMITTING,
                        ExecutionState.RUNNING,
                        ExecutionState.MONITORING,
                    }:
                        current = self.execution_queue.transition(
                            record.request_sha256,
                            state=ExecutionState.REVIEW_PENDING,
                            reason_code="execution-monitor-invalid",
                        )
                updated.append(current.to_public_dict())
            return tuple(updated)

    def cancel_transport(self, request_sha256: str) -> dict[str, object]:
        """Apply the declaration-owned fixed cancellation path."""

        with self._transport_lock:
            manifest = self._load_transport_manifest(request_sha256)
            existing = self.aris_transport.load(request_sha256)
            recovering = bool(
                existing is not None and existing.status is ArisTransportStatus.TRANSPORT_FAILURE
            )
            receipt = self.aris_transport.cancel(
                manifest,
                fallback_used=self._transport_fallback_used(),
            )
            record = self.execution_queue.load(request_sha256)
            return self._apply_transport_receipt(
                record,
                receipt,
                recovering=recovering,
            ).to_public_dict()

    def resume_transport(self, request_sha256: str) -> dict[str, object]:
        """Perform one explicit, manifest-bound recovery attempt."""

        with self._transport_lock:
            manifest = self._load_transport_manifest(request_sha256)
            receipt = self.aris_transport.resume(
                manifest,
                fallback_used=self._transport_fallback_used(),
            )
            record = self.execution_queue.load(request_sha256)
            return self._apply_transport_receipt(
                record,
                receipt,
                recovering=True,
            ).to_public_dict()

    def control_transport(self, value: Mapping[str, object]) -> dict[str, object]:
        """Resolve one opaque browser request to a fixed transport operation."""

        payload = strict_fields(
            value,
            required=("kind", "operation", "request_id", "schema_version"),
            context="transport control input",
        )
        if payload.pop("kind") != "transport_control_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("transport control input schema is invalid")
        request_id = require_identifier(
            payload.pop("request_id"),
            field="transport_control.request_id",
        )
        operation = payload.pop("operation")
        if operation not in {"cancel", "resume"}:
            raise ProtocolValidationError("transport control operation is not fixed")
        records = [
            record for record in self.execution_queue.records() if record.request_id == request_id
        ]
        if len(records) != 1:
            raise ProtocolValidationError("transport control request is unavailable")
        record = records[0]
        receipt = self.aris_transport.load(record.request_sha256)
        if receipt is None:
            raise ProtocolValidationError("transport control receipt is unavailable")
        if operation == "resume":
            recovery_ready = (
                record.state is ExecutionState.REVIEW_PENDING
                and receipt.status is ArisTransportStatus.TRANSPORT_FAILURE
            )
            recovery_replayed = receipt.status is not ArisTransportStatus.TRANSPORT_FAILURE and any(
                event.state is ExecutionState.REVIEW_PENDING
                and event.reason_code.startswith("aris-transport-")
                for event in record.events[:-1]
            )
            if not recovery_ready and not recovery_replayed:
                raise ProtocolValidationError("transport recovery is not permitted")
            updated = (
                record.to_public_dict()
                if recovery_replayed
                else self.resume_transport(record.request_sha256)
            )
        else:
            active_states = {
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
            }
            terminal_receipt = receipt.status in {
                ArisTransportStatus.COMPLETED,
                ArisTransportStatus.FAILED,
                ArisTransportStatus.STUCK,
                ArisTransportStatus.CANCELLED,
            }
            if (
                record.state not in active_states
                and not (
                    record.state is ExecutionState.REVIEW_PENDING
                    and receipt.status is ArisTransportStatus.TRANSPORT_FAILURE
                )
                and not terminal_receipt
            ):
                raise ProtocolValidationError("transport cancellation is not permitted")
            updated = self.cancel_transport(record.request_sha256)
        return {
            "kind": "transport_control_result",
            "operation": operation,
            "record": updated,
            "schema_version": 1,
        }

    def execution_dispatch_state(self) -> dict[str, object]:
        """Expose declaration-derived envelopes without command or path details."""

        worker = DeclarationBoundWorker(
            self.execution_queue,
            self.action_request_dir,
            self.submission_dir,
            clock=self.clock,
        )
        records = {item.request_sha256: item for item in worker.records()}
        return {
            "kind": "execution_dispatch",
            "records": [records[key].to_dict() for key in sorted(records)],
            "schema_version": 1,
            "transport": {
                "records": [item.to_dict() for item in self.aris_transport.records()],
                "schema_version": 1,
            },
        }

    def _bound_execution(self, request_sha256: str, declaration_sha256: str, remote_revision: str):
        record = self.execution_queue.load(request_sha256)
        declaration = self.execution_registry.get(record.lane_id, record.action_id)
        if (
            record.declaration_sha256 != declaration_sha256
            or declaration.declaration_sha256 != declaration_sha256
        ):
            raise ProtocolValidationError("execution declaration binding changed")
        request_path = self.action_request_dir / f"{request_sha256}.json"
        try:
            request = ActionRequest.from_json(request_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("bound Action Request is unavailable") from error
        if (
            request.request_sha256 != record.request_sha256
            or request.action_id != record.action_id
            or request.project_id != declaration.project_id
            or request.target_id != declaration.target_id
            or request.remote_revision != remote_revision
        ):
            raise ProtocolValidationError("execution authority binding changed")
        return record, declaration

    def apply_monitor_observation(self, value: Mapping[str, object]) -> dict[str, object]:
        """Persist one public-safe bridge observation and advance the durable queue."""

        observation = MonitorObservation.from_dict(value)
        with self._decision_lock:
            record, _ = self._bound_execution(
                observation.request_sha256,
                observation.declaration_sha256,
                observation.remote_revision,
            )
            self.monitor_dir.mkdir(parents=True, exist_ok=True)
            path = self.monitor_dir / (
                f"{observation.request_sha256}-{observation.observation_id}.json"
            )
            if path.is_file():
                existing = _load_optional(path, MonitorObservation.from_json)
                if existing is None or existing.to_dict() != observation.to_dict():
                    raise ProtocolValidationError("monitor observation conflicts with history")
            if record.state is observation.state:
                if not path.is_file():
                    write_json_atomic(path, observation.to_dict())
                return record.to_public_dict()
            updated = self.execution_queue.transition(
                observation.request_sha256,
                state=observation.state,
                reason_code=observation.reason_code,
            )
            if not path.is_file():
                write_json_atomic(path, observation.to_dict())
            return updated.to_public_dict()

    def intake_reproduction_evidence(self, value: Mapping[str, object]) -> dict[str, object]:
        """Accept one aggregate-only record and assemble a core-owned Decision Packet."""

        evidence = RestrictedEvidenceInput.from_dict(value)
        with self._decision_lock:
            record, declaration = self._bound_execution(
                evidence.request_sha256,
                evidence.declaration_sha256,
                evidence.remote_revision,
            )
            contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
            h1 = _load_optional(self.h1_path, H1Approval.from_json)
            if contract is None or h1 is None or not h1.is_current(contract):
                raise ProtocolValidationError("evidence intake requires current H1 authority")
            if (
                record.contract_sha256 != contract.contract_sha256
                or record.h1_approval_sha256 != h1.approval_sha256
            ):
                raise ProtocolValidationError("evidence intake authority binding changed")
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            receipt_path = self.evidence_dir / f"{evidence.request_sha256}.json"
            if receipt_path.is_file():
                receipt = _load_optional(receipt_path, EvidenceReceipt.from_json)
                if (
                    receipt is None
                    or receipt.request_sha256 != evidence.request_sha256
                    or receipt.evidence_sha256 != evidence.evidence_sha256
                ):
                    raise ProtocolValidationError("evidence intake conflicts with history")
                packet = _load_optional(
                    self.packet_dir / f"{record.lane_id}.json",
                    DecisionPacket.from_json,
                )
                if packet is None or packet.packet_sha256 != receipt.packet_sha256:
                    raise ProtocolValidationError("evidence receipt packet is unavailable")
                if record.state is ExecutionState.INTAKE:
                    self.execution_queue.transition(
                        record.request_sha256,
                        state=ExecutionState.REVIEW_PENDING,
                        reason_code="decision-packet-ready",
                    )
                    self.refresh_loop()
                elif record.state is not ExecutionState.REVIEW_PENDING:
                    raise ProtocolValidationError("evidence intake replay state is invalid")
                return packet.to_dict()
            if record.state is not ExecutionState.INTAKE:
                raise ProtocolValidationError("evidence intake requires intake execution state")
            packet_path = self.packet_dir / f"{record.lane_id}.json"
            if packet_path.is_file():
                raise ProtocolValidationError("execution lane already has a Decision Packet")
            accepted_at = _timestamp(self.clock())
            packet, receipt = assemble_decision_packet(
                evidence=evidence,
                contract=contract,
                declaration=declaration,
                accepted_at=accepted_at,
            )
            self.packet_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(packet_path, packet.to_dict())
            write_json_atomic(receipt_path, receipt.to_dict())
            self.execution_queue.transition(
                record.request_sha256,
                state=ExecutionState.REVIEW_PENDING,
                reason_code="decision-packet-ready",
            )
            self.refresh_loop()
            return packet.to_dict()

    def execution_state(self) -> dict[str, object]:
        return {
            "queue": self.execution_queue.to_public_dict(),
            "registry": self.execution_registry.to_public_dict(),
            "kind": "execution_control",
            "schema_version": 1,
        }

    def aris_revision_state(self) -> dict[str, object]:
        if self.aris_revision is None:
            raise ProtocolValidationError("ARIS revision validation has not run")
        return self.aris_revision.to_dict()


__all__ = ("RemoteSessionPreflight", "ResearchSession", "run_remote_preflight")
