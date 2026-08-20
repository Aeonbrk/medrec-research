from __future__ import annotations

import itertools
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from medrec_research.baseline_audit import AuditReviewSet, BaselineAudit, BaselineProgram
from medrec_research.benchmark_program import (
    ReproductionAttempt,
    ReproductionCharacterization,
    ReproductionStabilityPolicy,
    SelectionAcceptance,
    SelectionDiagnostic,
    SelectionResult,
    SelectionSpecification,
    VarianceCheck,
)
from medrec_research.benchmark_state import (
    ComparisonScope,
    HumanReviewRecord,
    HumanReviewState,
    LiveBenchmarkAuthority,
    derive_benchmark_state,
    program_registry_authority_sha256,
)
from medrec_research.errors import ProtocolValidationError
from medrec_research.project_status import (
    AuthorityDigest,
    BlockerCategory,
    CandidateStatus,
    EvidenceLink,
    LineageStatus,
    MedRecStatus,
    ProjectStage,
    ProjectStatus,
    SnapshotCondition,
    StatusBlocker,
    load_status,
    publish_medrec_status,
    validate_evidence_url,
)
from medrec_research.registry import BaselineRegistry

from .test_benchmark_state import _registry_with_qualified

NOW = datetime(2026, 7, 11, 1, 2, 3, tzinfo=UTC)
FINAL_FIVE = (
    "gamenet",
    "safedrug",
    "molerec",
    "retain",
    "leap-safedrug",
)
LAYERS = (
    "model_core",
    "data_processing",
    "split_selection",
    "evaluation_reporting",
)
ROOT = Path(__file__).parents[2]


def _clock() -> datetime:
    return NOW


def _authorities(digit: str = "a") -> tuple[AuthorityDigest, ...]:
    return (
        AuthorityDigest("audit-set", digit * 64),
        AuthorityDigest("program", "b" * 64),
        AuthorityDigest("registry", "c" * 64),
        AuthorityDigest("scope", "d" * 64),
    )


def _payload(
    *,
    qualified_count: int = 0,
    review_state: HumanReviewState = HumanReviewState.NOT_REQUIRED,
    discovery_eligible: bool = False,
) -> MedRecStatus:
    candidates = tuple(
        CandidateStatus(
            candidate_id=candidate_id,
            display_name=candidate_id,
            readiness="comparison_ready" if ordinal < qualified_count else "registered",
            source_gate="pass",
            license_gate="pass" if candidate_id != "safedrug" else "unresolved",
            evidence=(
                EvidenceLink(
                    label=f"{candidate_id}-source",
                    url=f"https://github.com/example/{candidate_id}",
                ),
            ),
        )
        for ordinal, candidate_id in enumerate(FINAL_FIVE)
    )
    lineage = tuple(
        LineageStatus(
            layer=layer,
            upstream_repository="https://github.com/example/shared-pipeline",
            candidate_ids=("safedrug", "molerec"),
            evidence=(
                EvidenceLink(
                    label=f"{layer}-lineage",
                    url="https://raw.githubusercontent.com/example/shared-pipeline/"
                    "0123456789abcdef0123456789abcdef01234567/README.md",
                ),
            ),
        )
        for layer in LAYERS
    )
    return MedRecStatus.create(
        qualified_count=qualified_count,
        review_state=review_state,
        discovery_eligible=discovery_eligible,
        candidates=candidates,
        shared_lineage=lineage,
    )


def _status(
    *,
    payload: MedRecStatus | None = None,
    blockers: tuple[StatusBlocker, ...] = (),
    authorities: tuple[AuthorityDigest, ...] | None = None,
) -> ProjectStatus:
    return ProjectStatus.create(
        project_id="medrec-research",
        authorities=authorities or _authorities(),
        blockers=blockers,
        payload=payload or _payload(),
        clock=_clock,
    )


def test_snapshot_is_deterministic_content_addressed_and_round_trips() -> None:
    first = _status()
    second = _status()

    assert first.to_json() == second.to_json()
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert ProjectStatus.from_json(first.to_json()) == first
    assert first.generated_at == "2026-07-11T01:02:03Z"
    assert first.valid_until == "2026-07-11T01:07:03Z"

    drifted = _status(authorities=_authorities("e"))
    assert drifted.snapshot_sha256 != first.snapshot_sha256


def test_publisher_projects_existing_authorities_without_advancing_them() -> None:
    program = BaselineProgram.load(ROOT / "baselines" / "programs" / "final-five.toml")
    audits = tuple(
        BaselineAudit.load(ROOT / "baselines" / "audits" / f"{candidate_id}.toml")
        for candidate_id in FINAL_FIVE
    )
    registry = BaselineRegistry.load(ROOT / "baselines" / "registry.toml")
    reviews = AuditReviewSet.load(ROOT / "fixtures" / "benchmark" / "audit-reviews.json")
    selection = SelectionResult.load(ROOT / "fixtures" / "benchmark" / "selection-result.json")
    authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=reviews,
        registry=registry,
        scope=ComparisonScope(
            protocol_version="1.0",
            dataset_manifest_sha256="d" * 64,
            adaptation_budget_sha256="a" * 64,
        ),
        selection=selection,
    )

    snapshot = publish_medrec_status(
        authority=authority,
        clock=_clock,
    )

    assert snapshot.payload.stage is ProjectStage.LANE_PROPOSED
    assert snapshot.payload.candidates[1].license_gate == "unresolved"
    assert {item.layer for item in snapshot.payload.shared_lineage} == set(LAYERS)
    assert {item.authority_id for item in snapshot.authorities} == {
        "audit-set",
        "program",
        "registry",
        "review-set",
        "scope",
        "selection",
    }
    assert registry.get("gamenet").readiness.value == "registered"


def test_live_benchmark_authority_rejects_drifted_selection_authorities() -> None:
    program = BaselineProgram.load(ROOT / "baselines" / "programs" / "final-five.toml")
    audits = tuple(
        BaselineAudit.load(ROOT / "baselines" / "audits" / f"{candidate_id}.toml")
        for candidate_id in FINAL_FIVE
    )
    reviews = AuditReviewSet.load(ROOT / "fixtures" / "benchmark" / "audit-reviews.json")
    registry = BaselineRegistry.load(ROOT / "baselines" / "registry.toml")
    selection = SelectionResult.load(ROOT / "fixtures" / "benchmark" / "selection-result.json")
    scope = ComparisonScope(
        protocol_version="1.0",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256="a" * 64,
    )

    authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=reviews,
        registry=registry,
        scope=scope,
        selection=selection,
    )

    assert authority.benchmark_state == derive_benchmark_state(
        program=program,
        registry=registry,
        scope=scope,
    )
    assert authority.review_set_sha256 == selection.review_set_sha256

    with pytest.raises(ProtocolValidationError, match="selection review set"):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=AuditReviewSet(reviews.reviews[:-1]),
            registry=registry,
            scope=scope,
            selection=selection,
        )

    with pytest.raises(ProtocolValidationError, match="selection scope authority"):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=registry,
            scope=ComparisonScope(
                protocol_version="1.0",
                dataset_manifest_sha256="e" * 64,
                adaptation_budget_sha256="a" * 64,
            ),
            selection=selection,
        )

    drifted_program_payload = selection.to_dict()
    drifted_program_payload.pop("selection_id")
    drifted_program_payload["program_sha256"] = "f" * 64
    drifted_program_selection = SelectionResult.create(**drifted_program_payload)
    with pytest.raises(ProtocolValidationError, match="selection program authority"):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=registry,
            scope=scope,
            selection=drifted_program_selection,
        )

    drifted_registry = BaselineRegistry(
        tuple(
            replace(baseline, display_name="Changed GAMENet")
            if baseline.baseline_id == "gamenet"
            else baseline
            for baseline in registry.baselines
        )
    )
    with pytest.raises(ProtocolValidationError, match="selection registry authority"):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=drifted_registry,
            scope=scope,
            selection=selection,
        )

    drifted_audits = (replace(audits[0], display_name="Changed GAMENet"), *audits[1:])
    diagnostics_payload = json.loads(
        (ROOT / "fixtures" / "benchmark" / "selection-diagnostics.json").read_text(encoding="utf-8")
    )
    drifted_selection = SelectionSpecification().select(
        program,
        drifted_audits,
        reviews,
        tuple(SelectionDiagnostic.from_dict(item) for item in diagnostics_payload["diagnostics"]),
        registry_authority_sha256=program_registry_authority_sha256(program, registry),
        scope_sha256=scope.scope_sha256,
    )
    with pytest.raises(ProtocolValidationError, match="selection audit set authority"):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=registry,
            scope=scope,
            selection=drifted_selection,
        )

    forged_payload = selection.to_dict()
    forged_payload.pop("selection_id")
    forged_payload["candidates"][0]["blockers"] = ["source_not_pass"]
    forged_payload["candidates"][0]["eligible"] = False
    forged_payload["candidates"][1]["blockers"] = []
    forged_payload["candidates"][1]["eligible"] = True
    forged_payload["selected_candidate_id"] = "safedrug"
    forged_selection = SelectionResult.create(**forged_payload)
    with pytest.raises(
        ProtocolValidationError, match="selection does not match current hard-gate result"
    ):
        LiveBenchmarkAuthority.create(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=registry,
            scope=scope,
            selection=forged_selection,
        )


def test_blocked_current_selection_suppresses_discovery() -> None:
    program = BaselineProgram.load(ROOT / "baselines" / "programs" / "final-five.toml")
    audits = tuple(
        BaselineAudit.load(ROOT / "baselines" / "audits" / f"{candidate_id}.toml")
        for candidate_id in FINAL_FIVE
    )
    scope = ComparisonScope(
        protocol_version="1.0",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256="a" * 64,
    )
    registry = _registry_with_qualified(*FINAL_FIVE)
    state = derive_benchmark_state(program=program, registry=registry, scope=scope)
    review = HumanReviewRecord.create(
        scope=scope,
        program=program,
        registry=registry,
        reviewed_qualifications=state.qualifications[:4],
        reviewer="research-steward",
        issued_at="2026-07-12T00:00:00Z",
    )
    diagnostics_payload = json.loads(
        (ROOT / "fixtures" / "benchmark" / "selection-diagnostics.json").read_text(encoding="utf-8")
    )
    selection = SelectionSpecification().select(
        program,
        audits,
        AuditReviewSet(()),
        tuple(SelectionDiagnostic.from_dict(item) for item in diagnostics_payload["diagnostics"]),
        registry_authority_sha256=program_registry_authority_sha256(program, registry),
        scope_sha256=scope.scope_sha256,
    )
    authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=AuditReviewSet(()),
        registry=registry,
        scope=scope,
        selection=selection,
        review=review,
    )

    snapshot = publish_medrec_status(authority=authority, clock=_clock)

    assert authority.benchmark_state.discovery_eligible
    assert selection.status == "blocked"
    assert snapshot.payload.stage is ProjectStage.AUDIT_BLOCKED
    assert not snapshot.payload.discovery_eligible


def test_reproduction_characterization_requires_current_selection_acceptance() -> None:
    program = BaselineProgram.load(ROOT / "baselines" / "programs" / "final-five.toml")
    audits = tuple(
        BaselineAudit.load(ROOT / "baselines" / "audits" / f"{candidate_id}.toml")
        for candidate_id in FINAL_FIVE
    )
    reviews = AuditReviewSet.load(ROOT / "fixtures" / "benchmark" / "audit-reviews.json")
    selection = SelectionResult.load(ROOT / "fixtures" / "benchmark" / "selection-result.json")
    authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=reviews,
        registry=BaselineRegistry.load(ROOT / "baselines" / "registry.toml"),
        scope=ComparisonScope(
            protocol_version="1.0",
            dataset_manifest_sha256="d" * 64,
            adaptation_budget_sha256="a" * 64,
        ),
        selection=selection,
    )
    acceptance = SelectionAcceptance.create(
        selection=selection,
        candidate_id="gamenet",
        reviewer="research-steward",
        issued_at="2026-07-12T00:00:00Z",
    )
    attempts = tuple(
        ReproductionAttempt(
            attempt_id=f"attempt-{ordinal}",
            outcome="completed",
            source_sha256="1" * 64,
            environment_sha256="2" * 64,
            adapter_sha256="3" * 64,
            adapter_smoke_sha256="4" * 64,
            input_manifest_sha256="5" * 64,
            seed_policy_sha256="6" * 64,
            artifact_sha256=f"{ordinal + 6:x}" * 64,
        )
        for ordinal in (1, 2)
    )
    policy = ReproductionStabilityPolicy()
    variance_checks = tuple(
        VarianceCheck(output_id, True, 0.01, 0.005, f"{ordinal:x}" * 64)
        for ordinal, output_id in enumerate(
            ("jaccard", "precision", "recall", "f1", "mean_medication_count"),
            start=1,
        )
    )
    characterization_evidence = {
        "baseline_id": "gamenet",
        "mode": "reproduction",
        "selection_acceptance_sha256": acceptance.acceptance_sha256,
        "planned_attempts": 2,
        "attempts": attempts,
        "protocol_violations": 0,
        "upstream_reference_sha256": "c" * 64,
        "split_semantics_sha256": "d" * 64,
        "selection_semantics_sha256": "e" * 64,
        "evaluation_semantics_sha256": "f" * 64,
    }
    characterization = ReproductionCharacterization.create(
        policy,
        variance_checks=variance_checks,
        **characterization_evidence,
    )
    unresolved_characterization = ReproductionCharacterization.create(
        policy,
        variance_checks=variance_checks[:-1],
        **characterization_evidence,
    )
    failed_characterization = ReproductionCharacterization.create(
        policy,
        variance_checks=tuple(
            replace(check, observed_variance=0.02) if check.check_id == "jaccard" else check
            for check in variance_checks
        ),
        **characterization_evidence,
    )

    missing = publish_medrec_status(
        authority=authority,
        characterization=characterization,
        clock=_clock,
    )
    accepted = publish_medrec_status(
        authority=authority,
        characterization=characterization,
        selection_acceptance=acceptance,
        clock=_clock,
    )
    unresolved = publish_medrec_status(
        authority=authority,
        characterization=unresolved_characterization,
        selection_acceptance=acceptance,
        clock=_clock,
    )
    failed = publish_medrec_status(
        authority=authority,
        characterization=failed_characterization,
        selection_acceptance=acceptance,
        clock=_clock,
    )
    stale = publish_medrec_status(
        authority=authority,
        characterization=characterization,
        selection_acceptance=SelectionAcceptance.create(
            selection=selection,
            candidate_id="gamenet",
            reviewer="second-steward",
            issued_at="2026-07-12T00:01:00Z",
        ),
        clock=_clock,
    )
    alternate_payload = selection.to_dict()
    alternate_payload.pop("selection_id")
    alternate_payload["candidates"][0]["diagnostics"]["comparison_representativeness"]["value"] = (
        "medium"
    )
    alternate_selection = SelectionResult.create(**alternate_payload)
    alternate_authority = LiveBenchmarkAuthority.create(
        program=program,
        audits=audits,
        reviews=reviews,
        registry=BaselineRegistry.load(ROOT / "baselines" / "registry.toml"),
        scope=ComparisonScope(
            protocol_version="1.0",
            dataset_manifest_sha256="d" * 64,
            adaptation_budget_sha256="a" * 64,
        ),
        selection=alternate_selection,
    )
    selection_drifted = publish_medrec_status(
        authority=alternate_authority,
        characterization=characterization,
        selection_acceptance=acceptance,
        clock=_clock,
    )
    legacy = publish_medrec_status(
        authority=authority,
        characterization=ReproductionCharacterization.load(
            ROOT / "fixtures" / "benchmark" / "reproduction-characterization-v1.json"
        ),
        clock=_clock,
    )

    assert missing.payload.stage is ProjectStage.LANE_PROPOSED
    assert missing.primary_blocker is not None
    assert missing.primary_blocker.reason_code == "selection_acceptance_missing"
    assert accepted.payload.stage is ProjectStage.LANE_PROPOSED
    assert accepted.primary_blocker is not None
    assert accepted.primary_blocker.reason_code == "reproduction_characterization_not_controlled"
    assert unresolved.payload.stage is ProjectStage.LANE_PROPOSED
    assert unresolved.primary_blocker is not None
    assert unresolved.primary_blocker.reason_code == "reproduction_characterization_not_controlled"
    assert failed.payload.stage is ProjectStage.LANE_PROPOSED
    assert failed.primary_blocker is not None
    assert failed.primary_blocker.reason_code == "reproduction_characterization_not_controlled"
    assert stale.primary_blocker is not None
    assert stale.primary_blocker.reason_code == "selection_acceptance_stale"
    assert selection_drifted.payload.stage is ProjectStage.LANE_PROPOSED
    assert selection_drifted.primary_blocker is not None
    assert selection_drifted.primary_blocker.reason_code == "selection_acceptance_stale"
    assert "selection-acceptance" not in {
        item.authority_id for item in selection_drifted.authorities
    }
    assert legacy.primary_blocker is not None
    assert legacy.primary_blocker.reason_code == "reproduction_characterization_legacy"


def test_medrec_milestones_are_projected_from_scoped_benchmark_state() -> None:
    pending = _payload(
        qualified_count=4,
        review_state=HumanReviewState.PENDING,
    )
    eligible = _payload(
        qualified_count=5,
        review_state=HumanReviewState.ACCEPTED,
        discovery_eligible=True,
    )

    assert pending.stage is ProjectStage.REVIEW_PENDING
    assert eligible.stage is ProjectStage.DISCOVERY_ELIGIBLE
    assert pending.qualified_count == 4
    assert eligible.qualified_count == 5


def test_shared_lineage_is_a_four_layer_projection_not_replication_evidence() -> None:
    status = _status()
    wire = status.to_dict()["payload"]

    assert {item.layer for item in status.payload.shared_lineage} == set(LAYERS)
    assert all(
        item.candidate_ids == ("safedrug", "molerec") for item in status.payload.shared_lineage
    )
    assert "replication" not in json.dumps(wire).lower()


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/repo",
        "//github.com/example/repo",
        "javascript:alert(1)",
        "data:text/plain,no",
        "file:///tmp/no",
        "https://user:secret@github.com/example/repo",
        "https://github.com/example/repo?access_token=secret",
        "https://github.com/example/repo#fragment",
        "https://github.com.evil.invalid/example/repo",
        "https://127.0.0.1/example/repo",
        "https://localhost/example/repo",
        "https://169.254.1.2/example/repo",
        "https://github.com/example/repo\nheader:value",
    ],
)
def test_evidence_url_rejects_unsafe_or_unapproved_targets(url: str) -> None:
    with pytest.raises(ProtocolValidationError, match="evidence URL") as caught:
        validate_evidence_url(url)

    assert url not in str(caught.value)


def test_evidence_url_accepts_closed_public_https_hosts() -> None:
    assert (
        validate_evidence_url("https://github.com/example/repo?plain=1")
        == "https://github.com/example/repo?plain=1"
    )
    assert validate_evidence_url("https://raw.githubusercontent.com/example/repo/rev/file")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda wire: wire.update({"notes": "anything"}), "unknown field"),
        (lambda wire: wire["payload"].update({"patient_id": "patient-1"}), "unknown field"),
        (lambda wire: wire["payload"].update({"predictions": ["RX_A"]}), "unknown field"),
        (lambda wire: wire["payload"].update({"weights": [0.1]}), "unknown field"),
        (lambda wire: wire["payload"].update({"logs": ["private"]}), "unknown field"),
        (lambda wire: wire["payload"].update({"credentials": "secret"}), "unknown field"),
        (
            lambda wire: wire["payload"]["candidates"][0].update(
                {"display_name": "/Users/researcher/private"}
            ),
            "local path",
        ),
        (lambda wire: wire["payload"].update({"score": float("nan")}), "unknown field"),
    ],
)
def test_closed_status_schema_rejects_sensitive_or_arbitrary_content(
    mutation, message: str
) -> None:
    wire = _status().to_dict()
    mutation(wire)

    with pytest.raises(ProtocolValidationError, match=message):
        ProjectStatus.from_dict(wire)


def test_primary_blocker_and_next_action_are_permutation_invariant() -> None:
    blockers = (
        StatusBlocker(BlockerCategory.REMOTE_PREFLIGHT, "remote_preflight_expired"),
        StatusBlocker(BlockerCategory.READINESS, "comparison_scope_incomplete", "retain"),
        StatusBlocker(BlockerCategory.SOURCE_LICENSE, "license_not_pass", "gamenet"),
        StatusBlocker(BlockerCategory.AUTHORIZATION, "authorization_missing"),
        StatusBlocker(BlockerCategory.SOURCE_LICENSE, "license_not_pass", "safedrug"),
    )

    observed = {
        (
            _status(blockers=permutation).primary_blocker,
            _status(blockers=permutation).next_action,
            _status(blockers=permutation).to_json(),
        )
        for permutation in itertools.permutations(blockers)
    }

    assert len(observed) == 1
    primary, action, _ = observed.pop()
    assert primary == StatusBlocker(BlockerCategory.AUTHORIZATION, "authorization_missing")
    assert action is not None and action.action_id == "refresh_authorization"


def test_stale_and_authority_mismatch_fail_closed() -> None:
    current = _status()
    stale = current.for_use(
        clock=lambda: NOW + timedelta(minutes=6),
        expected_authorities=current.authorities,
    )
    mismatched = current.for_use(
        clock=_clock,
        expected_authorities=_authorities("e"),
    )

    assert stale.condition is SnapshotCondition.STALE
    assert mismatched.condition is SnapshotCondition.DEGRADED
    assert stale.permitted_actions == mismatched.permitted_actions == ()
    assert stale.next_action is mismatched.next_action is None


def test_malformed_snapshot_uses_only_a_degraded_last_known_good(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    path.write_text('{"partial":', encoding="utf-8")
    last_known_good = _status()

    recovered = load_status(
        path,
        clock=_clock,
        expected_authorities=last_known_good.authorities,
        last_known_good=last_known_good,
    )

    assert recovered.condition is SnapshotCondition.DEGRADED
    assert recovered.permitted_actions == ()
    assert recovered.next_action is None


def test_atomic_write_never_replaces_good_snapshot_with_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "status.json"
    original = _status()
    original.write_atomic(path)
    changed = _status(authorities=_authorities("e"))

    def interrupted_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr("medrec_research._validation.os.replace", interrupted_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        changed.write_atomic(path)

    assert ProjectStatus.from_json(path.read_text(encoding="utf-8")) == original
    assert not list(tmp_path.glob(".status.json.*.tmp"))


def test_default_freshness_is_five_minutes_and_non_utc_clocks_are_rejected() -> None:
    assert _status().valid_until == "2026-07-11T01:07:03Z"

    with pytest.raises(ProtocolValidationError, match="UTC"):
        ProjectStatus.create(
            project_id="medrec-research",
            authorities=_authorities(),
            blockers=(),
            payload=_payload(),
            clock=lambda: datetime(2026, 7, 11, 1, 2, 3),
        )


def test_nonfinite_values_are_rejected_before_publication() -> None:
    wire = _status().to_dict()
    wire["payload"]["qualified_count"] = float("inf")

    with pytest.raises(ProtocolValidationError, match="qualified_count"):
        ProjectStatus.from_dict(wire)


@pytest.mark.parametrize(
    ("name", "stage"),
    [
        ("blocked.json", ProjectStage.AUDIT_BLOCKED),
        ("review-pending.json", ProjectStage.REVIEW_PENDING),
        ("discovery-eligible.json", ProjectStage.DISCOVERY_ELIGIBLE),
    ],
)
def test_checked_in_status_fixtures_round_trip(name: str, stage: ProjectStage) -> None:
    path = ROOT / "fixtures" / "status" / name
    snapshot = ProjectStatus.from_json(path.read_text(encoding="utf-8"))

    assert snapshot.payload.stage is stage
    assert ProjectStatus.from_json(snapshot.to_json()) == snapshot
