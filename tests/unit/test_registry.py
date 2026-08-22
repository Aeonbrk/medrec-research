from __future__ import annotations

from pathlib import Path

import pytest

from medrec_research import (
    BaselineDefinition,
    BaselineReadiness,
    BaselineRegistry,
    ComparisonQualification,
    ProtocolValidationError,
    ReadinessEvidence,
    ReadinessGate,
    ResearchMode,
    SourceIdentity,
    SourceStatus,
)


def pinned_source() -> SourceIdentity:
    return SourceIdentity(
        repository="https://example.invalid/medrec.git",
        revision="0123456789abcdef",
        status=SourceStatus.PINNED,
    )


def registered_baseline(*, baseline_id: str = "reference") -> BaselineDefinition:
    return BaselineDefinition(
        baseline_id=baseline_id,
        display_name=baseline_id,
        source=pinned_source(),
        supported_modes=(ResearchMode.REPRODUCTION, ResearchMode.COMPARISON),
        readiness=BaselineReadiness.REGISTERED,
        adapter_command=("python", "-m", "example_adapter"),
        adapter_revision="adapter-0123456789abcdef",
        environment_sha256="e" * 64,
    )


def smoke_evidence() -> tuple[ReadinessEvidence, ...]:
    return (
        ReadinessEvidence(ReadinessGate.ADAPTER_SMOKE, "1" * 64),
        ReadinessEvidence(ReadinessGate.ENVIRONMENT_LOCK, "2" * 64),
    )


def comparison_qualification(
    *,
    dataset_manifest_sha256: str = "d" * 64,
    adaptation_budget_sha256: str = "3" * 64,
) -> ComparisonQualification:
    return ComparisonQualification(
        protocol_version="1.0",
        dataset_manifest_sha256=dataset_manifest_sha256,
        adaptation_budget_sha256=adaptation_budget_sha256,
        evidence=(
            ReadinessEvidence(
                ReadinessGate.ADAPTATION_BUDGET,
                adaptation_budget_sha256,
            ),
            ReadinessEvidence(ReadinessGate.COHORT_IDENTITY, "4" * 64),
            ReadinessEvidence(ReadinessGate.CORE_INTEGRITY, "5" * 64),
            ReadinessEvidence(ReadinessGate.DETERMINISTIC_ADAPTER, "6" * 64),
            ReadinessEvidence(ReadinessGate.INDEPENDENT_EVALUATION, "7" * 64),
        ),
    )


def test_registry_rejects_missing_source_identity() -> None:
    with pytest.raises(ProtocolValidationError, match="source"):
        BaselineRegistry.from_dict(
            {
                "schema_version": 1,
                "baselines": [
                    {
                        "baseline_id": "gamenet",
                        "display_name": "GAMENet",
                        "supported_modes": ["reproduction", "comparison"],
                        "readiness": "registered",
                        "adapter_command": ["python", "adapter.py"],
                        "verification_evidence": [],
                    }
                ],
            }
        )


def test_registry_loads_toml_through_public_interface() -> None:
    registry = BaselineRegistry.from_toml(
        """
        schema_version = 1

        [[baselines]]
        baseline_id = "reference"
        display_name = "Reference"
        supported_modes = ["reproduction"]
        readiness = "smoke_ready"
        adapter_command = ["medrec-research", "reference"]
        adapter_revision = "adapter-0123456789abcdef"
        environment_sha256 = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

        [[baselines.readiness_evidence]]
        gate = "adapter_smoke"
        artifact_sha256 = "1111111111111111111111111111111111111111111111111111111111111111"

        [[baselines.readiness_evidence]]
        gate = "environment_lock"
        artifact_sha256 = "2222222222222222222222222222222222222222222222222222222222222222"

        [baselines.source]
        repository = "builtin:medrec_research.reference"
        revision = "0.1.0"
        status = "pinned"
        """
    )

    assert registry.get("reference").readiness is BaselineReadiness.SMOKE_READY


def test_registry_rejects_skipped_readiness_transition() -> None:
    with pytest.raises(ProtocolValidationError, match=r"registered.*smoke_ready"):
        registered_baseline().advance_readiness(
            BaselineReadiness.COMPARISON_READY,
            qualifications=(comparison_qualification(),),
        )


@pytest.mark.parametrize("baseline_id", ["gamenet", "safedrug"])
def test_unverified_archived_models_are_not_comparable(baseline_id: str) -> None:
    baseline = BaselineDefinition(
        baseline_id=baseline_id,
        display_name=baseline_id,
        source=SourceIdentity(
            repository=f"https://example.invalid/{baseline_id}.git",
            revision=None,
            status=SourceStatus.NEEDS_PIN,
        ),
        supported_modes=(ResearchMode.REPRODUCTION, ResearchMode.COMPARISON),
        readiness=BaselineReadiness.REGISTERED,
    )

    assert not baseline.is_comparable


def test_readiness_advances_one_verified_step_at_a_time() -> None:
    smoke_ready = registered_baseline().advance_readiness(
        BaselineReadiness.SMOKE_READY,
        evidence=smoke_evidence(),
    )
    comparison_ready = smoke_ready.advance_readiness(
        BaselineReadiness.COMPARISON_READY,
        qualifications=(comparison_qualification(),),
    )

    assert comparison_ready.is_comparable
    assert {item.gate for item in comparison_ready.readiness_evidence} == {
        ReadinessGate.ADAPTER_SMOKE,
        ReadinessGate.ENVIRONMENT_LOCK,
    }
    assert comparison_ready.qualifies_for(
        protocol_version="1.0",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256="3" * 64,
    )


def test_comparison_ready_requires_scoped_qualification() -> None:
    with pytest.raises(ProtocolValidationError, match="Comparison Qualification"):
        BaselineDefinition(
            baseline_id="reference",
            display_name="Reference",
            source=pinned_source(),
            supported_modes=(ResearchMode.COMPARISON,),
            readiness=BaselineReadiness.COMPARISON_READY,
            adapter_command=("python", "-m", "example_adapter"),
            adapter_revision="adapter-0123456789abcdef",
            environment_sha256="e" * 64,
            readiness_evidence=smoke_evidence(),
        )


def test_comparison_qualification_does_not_transfer_to_another_dataset() -> None:
    baseline = (
        registered_baseline()
        .advance_readiness(
            BaselineReadiness.SMOKE_READY,
            evidence=smoke_evidence(),
        )
        .advance_readiness(
            BaselineReadiness.COMPARISON_READY,
            qualifications=(comparison_qualification(),),
        )
    )

    assert not baseline.qualifies_for(
        protocol_version="1.0",
        dataset_manifest_sha256="0" * 64,
        adaptation_budget_sha256="3" * 64,
    )

    expanded = baseline.add_comparison_qualification(
        comparison_qualification(dataset_manifest_sha256="0" * 64)
    )
    assert expanded.qualifies_for(
        protocol_version="1.0",
        dataset_manifest_sha256="0" * 64,
        adaptation_budget_sha256="3" * 64,
    )


def test_archive_evidence_does_not_impersonate_upstream_source() -> None:
    baseline = BaselineDefinition(
        baseline_id="archive-example",
        display_name="Archive Example",
        source=SourceIdentity(
            repository=None,
            revision=None,
            status=SourceStatus.NEEDS_PIN,
        ),
        supported_modes=(ResearchMode.REPRODUCTION,),
        readiness=BaselineReadiness.REGISTERED,
        archive_evidence=(
            "New-Search@9971464253c556345262b22ed6d44b2cc14c9da8:medication-rec/archive-example",
        ),
    )

    assert baseline.source.repository is None
    assert baseline.archive_evidence


def test_project_registry_makes_no_readiness_claims() -> None:
    registry = BaselineRegistry.load(Path(__file__).parents[2] / "baselines" / "registry.toml")

    assert len(registry.baselines) == 6
    assert {baseline.readiness for baseline in registry.baselines} == {BaselineReadiness.REGISTERED}
    gamenet = registry.get("gamenet")
    assert gamenet.adapter_command == (
        "bash",
        "baselines/scripts/run_gamenet_319.sh",
        "gamenet",
    )
    assert gamenet.adapter_revision == (
        "sha256:580f1eebe9bb48c8966d9c616e4f6c65825ee1115f3c4ee30b36676c69136cb1"
    )
    assert gamenet.environment_sha256 == (
        "971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe"
    )
    safedrug = registry.get("safedrug")
    assert safedrug.adapter_command == (
        "bash",
        "baselines/scripts/run_safedrug_family_319.sh",
        "safedrug",
    )
    assert safedrug.adapter_revision == (
        "sha256:6b41609974a6bb9eedc00fb8ee1d9afa90c5ba2c256b03028d4b18357d7d475a"
    )
    assert safedrug.environment_sha256 == (
        "971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe"
    )
    retain = registry.get("retain")
    assert retain.adapter_command == (
        "bash",
        "baselines/scripts/run_safedrug_family_319.sh",
        "retain",
    )
    assert retain.adapter_revision == (
        "sha256:6b41609974a6bb9eedc00fb8ee1d9afa90c5ba2c256b03028d4b18357d7d475a"
    )
    assert retain.environment_sha256 == (
        "971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe"
    )
    leap = registry.get("leap-safedrug")
    assert leap.display_name == "LEAP (SafeDrug main)"
    assert leap.adapter_command == (
        "bash",
        "baselines/scripts/run_safedrug_family_319.sh",
        "leap-safedrug",
    )
    assert leap.adapter_revision == (
        "sha256:6b41609974a6bb9eedc00fb8ee1d9afa90c5ba2c256b03028d4b18357d7d475a"
    )
    assert leap.environment_sha256 == (
        "971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe"
    )
    assert leap.source.status is SourceStatus.PINNED
    assert not leap.is_comparable
