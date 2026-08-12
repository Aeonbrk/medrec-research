"""Read-only public projection of reproduction packets and H1/H2 state."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError
from .reproduction_contract import (
    AttemptStatus,
    DecisionPacket,
    H1Approval,
    H2Decision,
    SafeDrugBatchContract,
    Stage,
)


def _strings(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ProtocolValidationError(f"{field} must be a list")
    result = tuple(require_single_line_public_string(item, field=field) for item in value)
    if len(result) != len(set(result)):
        raise ProtocolValidationError(f"{field} entries must be unique")
    return result


@dataclass(frozen=True, slots=True)
class LaneProgress:
    lane_id: str
    model_id: str
    stage: str
    attempt_status: str
    packet_complete: bool
    conclusion: str
    h2_action: str | None
    h2_go_eligible: bool
    current: bool
    blockers: tuple[str, ...] = ()
    evidence_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, field="lane.lane_id")
        require_identifier(self.model_id, field="lane.model_id")
        require_identifier(self.stage, field="lane.stage")
        require_identifier(self.attempt_status, field="lane.attempt_status")
        require_identifier(self.conclusion, field="lane.conclusion")
        if self.h2_action is not None:
            require_identifier(self.h2_action, field="lane.h2_action")
        if (
            type(self.packet_complete) is not bool
            or type(self.h2_go_eligible) is not bool
            or type(self.current) is not bool
        ):
            raise ProtocolValidationError("lane status flags must be boolean")
        object.__setattr__(self, "blockers", _strings(self.blockers, field="lane.blockers"))
        object.__setattr__(
            self, "evidence_urls", _strings(self.evidence_urls, field="lane.evidence_urls")
        )

    @classmethod
    def from_packet(
        cls,
        packet: DecisionPacket,
        *,
        model_id: str | None = None,
        h2: H2Decision | None = None,
        evidence_urls: Iterable[str] = (),
    ) -> LaneProgress:
        if not isinstance(packet, DecisionPacket):
            raise ProtocolValidationError("lane packet must be a DecisionPacket")
        statuses = {item.status for item in packet.attempts}
        if AttemptStatus.RUNNING in statuses:
            attempt_status = AttemptStatus.RUNNING.value
        elif AttemptStatus.BLOCKED in statuses:
            attempt_status = AttemptStatus.BLOCKED.value
        elif AttemptStatus.INVALID in statuses:
            attempt_status = AttemptStatus.INVALID.value
        elif AttemptStatus.FAILED in statuses:
            attempt_status = AttemptStatus.FAILED.value
        else:
            attempt_status = AttemptStatus.COMPLETED.value
        outcome_keys = set(dict(packet.outcomes).keys()) if packet.outcomes else set()
        uncertainty_keys = set(dict(packet.uncertainty).keys()) if packet.uncertainty else set()
        packet_complete = (
            bool(packet.attempts)
            and set(packet.required_outcomes) <= outcome_keys
            and set(packet.required_outcomes) <= uncertainty_keys
        )
        blockers = list(packet.blockers)
        if not packet.is_current:
            blockers.append("packet-stale")
        if not packet_complete:
            blockers.append("packet-incomplete")
        h2_current = h2 is not None and h2.is_current(
            contract=packet.contract_sha256, packet=packet
        )
        stage = packet.stage.value if isinstance(packet.stage, Stage) else "safedrug"
        return cls(
            lane_id=packet.lane_id,
            model_id=model_id or packet.lane_id,
            stage=stage,
            attempt_status=attempt_status,
            packet_complete=packet_complete,
            conclusion=packet.conclusion.value,
            h2_action=h2.action.value if h2_current else None,
            h2_go_eligible=packet.go_eligible and (h2 is None or h2_current),
            current=packet.is_current and (h2 is None or h2_current),
            blockers=tuple(dict.fromkeys(blockers)),
            evidence_urls=tuple(evidence_urls),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "attempt_status": self.attempt_status,
            "blockers": list(self.blockers),
            "conclusion": self.conclusion,
            "current": self.current,
            "evidence_urls": list(self.evidence_urls),
            "h2_action": self.h2_action,
            "h2_go_eligible": self.h2_go_eligible,
            "lane_id": self.lane_id,
            "model_id": self.model_id,
            "packet_complete": self.packet_complete,
            "stage": self.stage,
        }

    @classmethod
    def from_dict(cls, value: object) -> LaneProgress:
        return cls(
            **strict_fields(
                value,
                required=(
                    "attempt_status",
                    "blockers",
                    "conclusion",
                    "current",
                    "evidence_urls",
                    "h2_action",
                    "h2_go_eligible",
                    "lane_id",
                    "model_id",
                    "packet_complete",
                    "stage",
                ),
                context="LaneProgress",
            )
        )


@dataclass(frozen=True, slots=True)
class ResearchLoopStatus:
    """Content-addressed, read-only loop snapshot."""

    contract_sha256: str | None
    h1_current: bool
    lanes: tuple[LaneProgress, ...]
    blockers: tuple[str, ...] = ()
    stale: bool = False
    status_sha256: str = ""

    SCHEMA_VERSION = 1

    def __post_init__(self) -> None:
        if self.contract_sha256 is not None:
            require_sha256(self.contract_sha256, field="loop.contract_sha256")
        if type(self.h1_current) is not bool or type(self.stale) is not bool:
            raise ProtocolValidationError("loop h1_current and stale must be boolean")
        lanes = tuple(
            item if isinstance(item, LaneProgress) else LaneProgress.from_dict(item)
            for item in self.lanes
        )
        if len({item.lane_id for item in lanes}) != len(lanes):
            raise ProtocolValidationError("loop lane IDs must be unique")
        object.__setattr__(self, "lanes", tuple(sorted(lanes, key=lambda item: item.lane_id)))
        object.__setattr__(self, "blockers", _strings(self.blockers, field="loop.blockers"))
        expected = content_sha256(self._protected_payload())
        if self.status_sha256:
            require_sha256(self.status_sha256, field="loop.status_sha256")
            if self.status_sha256 != expected:
                raise ProtocolValidationError("loop status_sha256 does not match snapshot content")
        else:
            object.__setattr__(self, "status_sha256", expected)

    @classmethod
    def create(
        cls,
        *,
        contract: SafeDrugBatchContract | None,
        h1: H1Approval | None,
        packets: Iterable[DecisionPacket],
        h2_decisions: Mapping[str, H2Decision] | None = None,
        model_ids: Mapping[str, str] | None = None,
    ) -> ResearchLoopStatus:
        decisions = h2_decisions or {}
        packet_values = tuple(packets)
        lanes = tuple(
            LaneProgress.from_packet(
                packet,
                model_id=(model_ids or {}).get(packet.lane_id),
                h2=decisions.get(packet.lane_id),
            )
            for packet in packet_values
        )
        if contract is not None:
            lanes = tuple(
                replace(
                    lane,
                    current=False,
                    h2_action=None,
                    h2_go_eligible=False,
                    blockers=(*lane.blockers, "contract-mismatch"),
                )
                if packet.contract_sha256 != contract.contract_sha256
                else lane
                for packet, lane in zip(packet_values, lanes, strict=True)
            )
        h1_current = bool(contract is not None and h1 is not None and h1.is_current(contract))
        if not h1_current:
            lanes = tuple(
                replace(
                    lane,
                    current=False,
                    h2_go_eligible=False,
                    blockers=(*lane.blockers, "h1-stale-or-missing"),
                )
                for lane in lanes
            )
        blockers: list[str] = []
        if not h1_current:
            blockers.append("h1-stale-or-missing")
        for lane in lanes:
            blockers.extend(f"{lane.lane_id}:{item}" for item in lane.blockers)
        stale = not h1_current or any(not lane.current for lane in lanes)
        return cls(
            contract_sha256=contract.contract_sha256 if contract is not None else None,
            h1_current=h1_current,
            lanes=lanes,
            blockers=tuple(dict.fromkeys(blockers)),
            stale=stale,
        )

    @property
    def is_current(self) -> bool:
        return self.status_sha256 == content_sha256(self._protected_payload())

    @property
    def h2_eligible_lane_ids(self) -> tuple[str, ...]:
        return tuple(item.lane_id for item in self.lanes if item.h2_go_eligible)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "blockers": list(self.blockers),
            "contract_sha256": self.contract_sha256,
            "h1_current": self.h1_current,
            "lanes": [item.to_dict() for item in self.lanes],
            "stale": self.stale,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "kind": "research_loop_status",
            "schema_version": self.SCHEMA_VERSION,
            "status_sha256": self.status_sha256,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> ResearchLoopStatus:
        payload = strict_fields(
            value,
            required=(
                "blockers",
                "contract_sha256",
                "h1_current",
                "kind",
                "lanes",
                "schema_version",
                "stale",
                "status_sha256",
            ),
            context="ResearchLoopStatus",
        )
        if (
            payload.pop("kind") != "research_loop_status"
            or payload.pop("schema_version") != cls.SCHEMA_VERSION
        ):
            raise ProtocolValidationError("ResearchLoopStatus schema or kind is invalid")
        lanes = payload.pop("lanes")
        if not isinstance(lanes, list):
            raise ProtocolValidationError("ResearchLoopStatus lanes must be a list")
        payload["lanes"] = tuple(LaneProgress.from_dict(item) for item in lanes)
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ResearchLoopStatus:
        return cls.from_dict(parse_json_object(text, context="ResearchLoopStatus"))


def load_research_loop(path: str | Path) -> ResearchLoopStatus:
    try:
        return ResearchLoopStatus.from_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ProtocolValidationError) as error:
        if isinstance(error, ProtocolValidationError):
            raise
        raise ProtocolValidationError("research loop status is unavailable") from error


__all__ = ("LaneProgress", "ResearchLoopStatus", "load_research_loop")
