"""Atomic storage, verification, and state projection for research contracts and H1/H2 decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from ._validation import (
    canonical_json,
    strict_fields,
    write_json_atomic,
)
from .errors import ProtocolValidationError
from .execution_evidence import EvidenceReceipt
from .reproduction_contract import (
    DecisionPacket,
    H1Approval,
    H2Decision,
    SafeDrugBatchContract,
)

Clock = Callable[[], datetime]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_optional(path: Path, loader: Callable[[str], Any]) -> Any | None:
    if not path.is_file():
        return None
    try:
        return loader(path.read_text(encoding="utf-8"))
    except (ProtocolValidationError, OSError, UnicodeError):
        return None


class ResearchContractStore:
    """Atomic, fail-closed persistence for H1 approvals and H2 decisions."""

    def __init__(self) -> None:
        self._lock = RLock()

    def evidence_receipts(
        self,
        *,
        evidence_dir: Path,
    ) -> tuple[dict[str, EvidenceReceipt], tuple[str, ...]]:
        """Load valid evidence receipts and collect integrity blockers."""
        if not evidence_dir.is_dir():
            return {}, ()
        receipts: dict[str, EvidenceReceipt] = {}
        blockers: list[str] = []
        conflicted: set[str] = set()
        for path in sorted(evidence_dir.glob("*.json")):
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

    def contract_state(
        self,
        *,
        contract_path: Path,
        ai_status: str,
        ai_reason: str,
    ) -> dict[str, object]:
        """Expose only the current contract's public-safe questionnaire fields."""
        contract = _load_optional(contract_path, SafeDrugBatchContract.from_json)
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

    def decision_packet_state(
        self,
        *,
        evidence_dir: Path,
        contract: SafeDrugBatchContract | None,
        packets: list[DecisionPacket],
        record_blockers: tuple[str, ...],
    ) -> dict[str, object]:
        """Expose aggregate packet evidence without paths or restricted artifacts."""
        if contract is None:
            raise ProtocolValidationError("decision packets require a current contract")
        receipts, receipt_blockers = self.evidence_receipts(evidence_dir=evidence_dir)
        records = []
        for packet in packets:
            receipt = receipts.get(packet.packet_sha256)
            evidence_ready = not evidence_dir.is_dir() or (
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

    def create_h1(
        self,
        value: Mapping[str, object],
        *,
        contract_path: Path,
        h1_path: Path,
        clock: Clock,
        on_success: Callable[[], None] | None = None,
    ) -> dict[str, object]:
        """Atomically create and persist an immutable H1 approval record."""
        payload = strict_fields(
            value,
            required=("kind", "schema_version", "owner", "rationale"),
            context="H1 input",
        )
        if payload.pop("kind") != "h1_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("H1 input schema or kind is invalid")
        with self._lock:
            contract = _load_optional(contract_path, SafeDrugBatchContract.from_json)
            if contract is None:
                raise ProtocolValidationError("H1 requires a current production contract")
            existing = _load_optional(h1_path, H1Approval.from_json)
            if h1_path.is_file() and existing is None:
                raise ProtocolValidationError("current H1 record is invalid")
            if existing is not None and existing.is_current(contract):
                if (
                    existing.owner == payload["owner"]
                    and existing.rationale == payload["rationale"]
                ):
                    if on_success:
                        on_success()
                    return existing.to_dict()
                raise ProtocolValidationError("H1 approval for this contract is immutable")
            approval = H1Approval.create(
                contract,
                owner=payload["owner"],
                rationale=payload["rationale"],
                approved_at=_timestamp(clock()),
            )
            write_json_atomic(h1_path, approval.to_dict())
            if on_success:
                on_success()
            return approval.to_dict()

    def create_h2(
        self,
        value: Mapping[str, object],
        *,
        contract_path: Path,
        h1_path: Path,
        packet_dir: Path,
        evidence_dir: Path,
        h2_dir: Path,
        clock: Clock,
        on_success: Callable[[], None] | None = None,
    ) -> dict[str, object]:
        """Atomically create and persist an immutable H2 decision record."""
        payload = strict_fields(
            value,
            required=("kind", "schema_version", "lane_id", "researcher", "action", "rationale"),
            context="H2 input",
        )
        if payload.pop("kind") != "h2_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("H2 input schema or kind is invalid")
        with self._lock:
            contract = _load_optional(contract_path, SafeDrugBatchContract.from_json)
            h1 = _load_optional(h1_path, H1Approval.from_json)
            if contract is None or h1 is None or not h1.is_current(contract):
                raise ProtocolValidationError("H2 requires current H1 authority")
            lane_id = payload.pop("lane_id")
            packets = [
                packet
                for path in sorted(packet_dir.glob("*.json"))
                if (packet := _load_optional(path, DecisionPacket.from_json)) is not None
                and packet.lane_id == lane_id
            ]
            if len(packets) != 1:
                raise ProtocolValidationError("H2 requires exactly one current lane packet")
            receipts, receipt_blockers = self.evidence_receipts(evidence_dir=evidence_dir)
            if evidence_dir.is_dir() and (
                receipt_blockers or receipts.get(packets[0].packet_sha256) is None
            ):
                raise ProtocolValidationError("H2 requires a valid evidence receipt")
            decision = H2Decision.create(
                contract=contract,
                packet=packets[0],
                researcher=payload["researcher"],
                action=payload["action"],
                rationale=payload["rationale"],
                issued_at=_timestamp(clock()),
            )
            existing = [
                item
                for path in sorted(h2_dir.glob("*.json"))
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
                    if on_success:
                        on_success()
                    return current.to_dict()
                raise ProtocolValidationError("H2 decision for this packet is immutable")
            h2_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(h2_dir / f"{decision.packet_sha256}.json", decision.to_dict())
            if on_success:
                on_success()
            return decision.to_dict()


__all__ = ("ResearchContractStore",)
