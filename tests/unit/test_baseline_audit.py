from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from medrec_research._validation import content_sha256
from medrec_research.baseline_audit import (
    AuditReview,
    AuditReviewSet,
    AuditSource,
    BaselineAudit,
    BaselineProgram,
    Disposition,
)
from medrec_research.errors import ProtocolValidationError

ROOT = Path(__file__).parents[2]
AUDIT_DIR = ROOT / "baselines" / "audits"
PROGRAM_PATH = ROOT / "baselines" / "programs" / "classic-six.toml"
REVIEWS_PATH = ROOT / "fixtures" / "benchmark" / "audit-reviews.json"
CLASSIC_SIX = (
    "gamenet",
    "safedrug",
    "micron",
    "molerec",
    "retain",
    "leap-safedrug",
)


def load_audits() -> tuple[BaselineAudit, ...]:
    return tuple(
        BaselineAudit.load(AUDIT_DIR / f"{baseline_id}.toml") for baseline_id in CLASSIC_SIX
    )


def test_classic_six_program_and_audits_round_trip_deterministically() -> None:
    program = BaselineProgram.load(PROGRAM_PATH)
    audits = load_audits()

    assert program.candidate_ids == CLASSIC_SIX
    program.validate_audits(audits)
    assert BaselineProgram.from_dict(program.to_dict()) == program
    assert all(BaselineAudit.from_dict(audit.to_dict()) == audit for audit in audits)
    assert program.program_sha256 == BaselineProgram.from_dict(program.to_dict()).program_sha256
    assert all(
        audit.audit_sha256 == BaselineAudit.from_dict(audit.to_dict()).audit_sha256
        for audit in audits
    )


@pytest.mark.parametrize(
    "candidate_ids",
    (
        CLASSIC_SIX[:-1],
        (*CLASSIC_SIX, "reference"),
        (*CLASSIC_SIX[:-1], "gamenet"),
    ),
)
def test_classic_six_rejects_missing_extra_or_duplicate_candidate(
    candidate_ids: tuple[str, ...],
) -> None:
    with pytest.raises(ProtocolValidationError, match="exact classic-six candidates"):
        BaselineProgram(program_id="classic-six", candidate_ids=candidate_ids)


def test_leap_identity_is_derivative_and_never_official() -> None:
    audit = BaselineAudit.load(AUDIT_DIR / "leap-safedrug.toml")
    assert audit.derivative_of == "safedrug"
    assert audit.identity_kind == "derivative"

    payload = audit.to_dict()
    payload["identity_kind"] = "official"
    with pytest.raises(ProtocolValidationError, match="identity_kind"):
        BaselineAudit.from_dict(payload)


def test_audit_completion_requires_all_claims_and_lineage_layers() -> None:
    audit = BaselineAudit.load(AUDIT_DIR / "safedrug.toml")
    assert audit.is_complete
    assert audit.claim("license").disposition is Disposition.UNRESOLVED

    payload = audit.to_dict()
    payload["claims"] = payload["claims"][:-1]
    with pytest.raises(ProtocolValidationError, match="required audit claims"):
        BaselineAudit.from_dict(payload)

    payload = audit.to_dict()
    payload["lineage"] = [
        edge for edge in payload["lineage"] if edge["layer"] != "evaluation_reporting"
    ]
    with pytest.raises(ProtocolValidationError, match="lineage layers"):
        BaselineAudit.from_dict(payload)


def test_hard_gate_pass_requires_matching_accepted_review() -> None:
    gamenet = BaselineAudit.load(AUDIT_DIR / "gamenet.toml")
    reviews = AuditReviewSet.load(REVIEWS_PATH)

    assert AuditReviewSet.from_dict(reviews.to_dict()) == reviews
    assert reviews.matching_review(gamenet, "source").review_sha256
    assert reviews.accepts(gamenet, "source")
    assert reviews.accepts(gamenet, "license")
    assert not AuditReviewSet(()).accepts(gamenet, "source")

    drifted = deepcopy(gamenet.to_dict())
    drifted["claims"][0]["rationale"] += " Drifted."
    assert not reviews.accepts(BaselineAudit.from_dict(drifted), "source")


def test_audit_review_set_is_canonical_and_rejects_conflicting_decisions() -> None:
    gamenet = BaselineAudit.load(AUDIT_DIR / "gamenet.toml")
    reviews = AuditReviewSet.load(REVIEWS_PATH)

    assert AuditReviewSet(tuple(reversed(reviews.reviews))) == reviews
    assert AuditReviewSet(tuple(reversed(reviews.reviews))).to_dict() == reviews.to_dict()

    accepted = reviews.matching_review(gamenet, "source")
    assert accepted is not None
    payload = accepted.to_dict()
    payload.update(
        {
            "decision": "fail",
            "issued_at": "2026-07-12T00:00:00Z",
            "reviewer": "second-steward",
        }
    )
    payload["content_sha256"] = content_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    conflicting = AuditReview.from_dict(payload)

    with pytest.raises(ProtocolValidationError, match="conflicting decisions"):
        AuditReviewSet((*reviews.reviews, conflicting))


def test_immutable_evidence_rejects_mutable_url_digest_or_revision_drift() -> None:
    audit = BaselineAudit.load(AUDIT_DIR / "gamenet.toml")

    credentialed_repository = deepcopy(audit.to_dict()["sources"][0])
    credentialed_repository["repository"] = "https://attacker@github.com/sjy1203/GAMENet"
    with pytest.raises(ProtocolValidationError, match="public GitHub HTTPS URL"):
        AuditSource.from_dict(credentialed_repository)

    mutable = deepcopy(audit.to_dict())
    mutable["evidence"][0]["immutable_url"] = mutable["evidence"][0]["immutable_url"].replace(
        mutable["evidence"][0]["revision"], "main"
    )
    with pytest.raises(ProtocolValidationError, match="immutable revision"):
        BaselineAudit.from_dict(mutable)

    changed_content = deepcopy(audit.to_dict())
    changed_content["evidence"][0]["content"] += " changed"
    with pytest.raises(ProtocolValidationError, match="content_sha256"):
        BaselineAudit.from_dict(changed_content)

    wrong_source_revision = deepcopy(audit.to_dict())
    wrong_source_revision["evidence"][0]["revision"] = "0" * 40
    wrong_source_revision["evidence"][0]["immutable_url"] = wrong_source_revision["evidence"][0][
        "immutable_url"
    ].replace(audit.evidence[0].revision, "0" * 40)
    with pytest.raises(ProtocolValidationError, match="source revision"):
        BaselineAudit.from_dict(wrong_source_revision)


@pytest.mark.parametrize("failure", ["duplicate", "circular", "unknown", "evidence-free"])
def test_lineage_edges_reject_invalid_graphs_per_layer(failure: str) -> None:
    payload = BaselineAudit.load(AUDIT_DIR / "molerec.toml").to_dict()
    first = deepcopy(payload["lineage"][0])
    if failure == "duplicate":
        payload["lineage"].append(first)
    elif failure == "circular":
        first["upstream"] = first["downstream"]
        payload["lineage"][0] = first
    elif failure == "unknown":
        first["upstream"] = "unknown-source"
        payload["lineage"][0] = first
    else:
        first["evidence_ids"] = []
        payload["lineage"][0] = first

    with pytest.raises(ProtocolValidationError, match=failure):
        BaselineAudit.from_dict(payload)


def test_retain_and_shared_pipeline_semantics_remain_explicit() -> None:
    retain = BaselineAudit.load(AUDIT_DIR / "retain.toml")
    molerec = BaselineAudit.load(AUDIT_DIR / "molerec.toml")

    assert {source.role for source in retain.sources} == {
        "canonical_model",
        "medication_comparison",
    }
    assert "sequence classification" in retain.claim("task").rationale.lower()
    assert any("c7218d0" in item.content for item in molerec.evidence)
    assert any(edge.upstream == "safedrug-processing" for edge in molerec.lineage)
