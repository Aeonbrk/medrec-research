"""One-command coordinator for a real, fail-closed HITL research session."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

from ._validation import content_sha256, strict_fields, write_json_atomic
from .action_gate import ActionRequest, AuthorityBundle
from .baseline_audit import BaselineAudit, BaselineProgram
from .errors import ProtocolValidationError
from .execution_control import DurableExecutionQueue, ExecutionDeclarationRegistry
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

    def __init__(self, root: Path, *, clock: Clock) -> None:
        self.root = root.resolve()
        self.clock = clock
        self.runtime = self.root / "runtime" / "hitl"
        self.status_path = self.runtime / "project-status.json"
        self.loop_path = self.runtime / "research-loop.json"
        self.preflight_path = self.runtime / "remote-preflight.json"
        self.authority_bundle_path = self.runtime / "authority-bundle.json"
        self.action_request_dir = self.runtime / "action-requests"
        self.execution_dir = self.runtime / "executions"
        self.contract_path = self.runtime / "contract.json"
        self.h1_path = self.runtime / "h1.json"
        self.packet_dir = self.runtime / "packets"
        self.h2_dir = self.runtime / "h2"
        self.preflight: RemoteSessionPreflight | None = None
        self.execution_registry = ExecutionDeclarationRegistry.load_package()
        self.execution_queue = DurableExecutionQueue(self.execution_dir, clock=clock)
        self._decision_lock = Lock()

    @property
    def actions_enabled(self) -> bool:
        bundle = self.authority_bundle()
        contract, h1, _, _, _ = self._records()
        return bool(
            bundle is not None
            and self.preflight is not None
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

    def _aris_manifest(self) -> tuple[str | None, tuple[str, ...]]:
        manifest = self.root / ".aris/installed-skills-codex.txt"
        if not manifest.is_file():
            return None, ("aris-install-missing",)
        try:
            lines = manifest.read_text(encoding="utf-8").splitlines()
            rows = [line.split("\t", 1) for line in lines]
            values = {row[0]: row[1] for row in rows if len(row) == 2}
            aris_root = Path(values["repo_root"])
        except (OSError, KeyError, UnicodeError):
            return None, ("aris-install-invalid",)
        blockers: list[str] = []
        if not aris_root.is_dir():
            blockers.append("aris-checkout-missing")
        elif _git_value(aris_root, "branch", "--show-current") != "main":
            blockers.append("aris-not-on-main")
        elif _git_value(aris_root, "status", "--porcelain"):
            blockers.append("aris-checkout-dirty")
        return _sha256_file(manifest), tuple(blockers)

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
        for path in sorted(self.h2_dir.glob("*.json")):
            decision = _load_optional(path, H2Decision.from_json)
            if decision is None:
                blockers.append("h2-invalid")
            else:
                h2_by_packet[decision.packet_sha256] = decision
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
            decision = H2Decision.create(
                contract=contract,
                packet=packets[0],
                researcher=payload["researcher"],
                action=payload["action"],
                rationale=payload["rationale"],
                issued_at=_timestamp(self.clock()),
            )
            write_json_atomic(self.h2_dir / f"{lane_id}.json", decision.to_dict())
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
        return self.execution_queue.enqueue(
            request=request,
            declaration=declaration,
            contract_sha256=contract.contract_sha256,
            h1_approval_sha256=h1.approval_sha256,
            h2_decision_sha256=h2_decision_sha256,
            blockers=(
                self.preflight.blockers if self.preflight is not None else ("preflight-missing",)
            ),
        ).to_public_dict()

    def execution_state(self) -> dict[str, object]:
        return {
            "queue": self.execution_queue.to_public_dict(),
            "registry": self.execution_registry.to_public_dict(),
            "kind": "execution_control",
            "schema_version": 1,
        }


__all__ = ("RemoteSessionPreflight", "ResearchSession", "run_remote_preflight")
