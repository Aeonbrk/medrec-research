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
    ReproductionProgram,
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


def test_v1_1_qualification_requires_amendment_and_method_profile() -> None:
    with pytest.raises(ProtocolValidationError, match=r"v1.1.*amendment.*profile"):
        ComparisonQualification(
            protocol_version="1.1",
            dataset_manifest_sha256="d" * 64,
            adaptation_budget_sha256="3" * 64,
            evidence=comparison_qualification().evidence,
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


def test_project_registry_qualifies_exactly_the_five_target_baselines() -> None:
    registry = BaselineRegistry.load(Path(__file__).parents[2] / "baselines" / "registry.toml")

    assert len(registry.baselines) == 6
    assert registry.get("reference").readiness is BaselineReadiness.REGISTERED
    target_ids = {"retain", "leap-safedrug", "gamenet", "safedrug", "molerec"}
    targets = tuple(registry.get(baseline_id) for baseline_id in target_ids)
    assert {baseline.readiness for baseline in targets} == {BaselineReadiness.COMPARISON_READY}
    assert all(baseline.is_comparable for baseline in targets)
    shared_scopes = {
        (
            qualification.protocol_version,
            qualification.dataset_manifest_sha256,
            qualification.adaptation_budget_sha256,
            qualification.protocol_amendment_sha256,
        )
        for baseline in targets
        for qualification in baseline.comparison_qualifications
    }
    assert shared_scopes == {
        (
            "1.1",
            "82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712",
            "180fd7e4f813a7e803facaf6c89f66c27f93843f1b3aea429aab501b5bfd8bb5",
            "c5b8ac4ad6696b3293a711fd65aa194263877b26b6a7557d1d874e6adc8be929",
        )
    }
    assert (
        len(
            {
                qualification.method_profile_sha256
                for baseline in targets
                for qualification in baseline.comparison_qualifications
            }
        )
        == 5
    )
    assert len(registry.reproduction_programs) == 2
    assert {p.program_id for p in registry.reproduction_programs} == {
        "safedrug-archived",
        "molerec",
    }
    program = registry.get_program("safedrug-archived")
    assert isinstance(program, ReproductionProgram)
    assert program.program_id == "safedrug-archived"
    assert program.conda_environment == "medrec-molerec-table1"
    assert program.is_319_verified
    assert program.environment_sha256 == (
        "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
    )
    gamenet = registry.get("gamenet")
    assert gamenet.display_name == "GAMENet (SafeDrug archived)"
    assert gamenet.source.revision == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
    assert gamenet.reproduction_program == program.program_id
    safedrug = registry.get("safedrug")
    assert safedrug.display_name == "SafeDrug (archived)"
    assert safedrug.source.revision == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
    assert safedrug.reproduction_program == program.program_id
    retain = registry.get("retain")
    assert retain.display_name == "RETAIN (SafeDrug archived)"
    assert retain.source.revision == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
    assert retain.reproduction_program == program.program_id
    leap = registry.get("leap-safedrug")
    assert leap.display_name == "LEAP (SafeDrug archived)"
    assert leap.source.revision == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
    assert leap.reproduction_program == program.program_id
    assert leap.source.status is SourceStatus.PINNED
    assert leap.is_comparable

    molerec = registry.get("molerec")
    assert molerec.display_name == "MoleRec (Table 1)"
    assert molerec.reproduction_program == "molerec"

    assert len(registry.reproduction_lanes) == 7
    lane_ids = [lane.lane_id for lane in registry.reproduction_lanes]
    assert lane_ids == [
        "molerec-retain",
        "molerec-leap",
        "molerec-gamenet",
        "molerec-safedrug-lr-1e-5",
        "molerec-safedrug-lr-1e-4",
        "molerec-safedrug-lr-5e-4",
        "molerec-embedding",
    ]
    assert registry.get_lane("molerec-retain").profile_id == "retain"
    assert registry.get_lane("molerec-safedrug-lr-1e-5").learning_rate == 1e-5


def test_reproduction_lane_validation_rejects_duplicates_and_dangling_references() -> None:
    from medrec_research import ReproductionLane

    with pytest.raises(ProtocolValidationError, match="lane_id"):
        BaselineRegistry(
            baselines=(registered_baseline(baseline_id="gamenet"),),
            reproduction_programs=(
                ReproductionProgram(
                    program_id="safedrug-archived",
                    entrypoint="baselines/safedrug_archived.py",
                    conda_environment="env",
                    upstream_root="/root/SafeDrug",
                    dataset_subdirectory="snapshots",
                    run_subdirectory="runs",
                    required_inputs=("a.pkl",),
                    import_modules=("torch",),
                ),
            ),
            reproduction_lanes=(
                ReproductionLane(
                    lane_id="lane-1",
                    scientific_baseline_id="gamenet",
                    program_id="safedrug-archived",
                    profile_id="gamenet",
                ),
                ReproductionLane(
                    lane_id="lane-1",
                    scientific_baseline_id="gamenet",
                    program_id="safedrug-archived",
                    profile_id="gamenet",
                ),
            ),
        )

    with pytest.raises(ProtocolValidationError, match="unknown Reproduction Program"):
        BaselineRegistry(
            baselines=(registered_baseline(baseline_id="gamenet"),),
            reproduction_programs=(),
            reproduction_lanes=(
                ReproductionLane(
                    lane_id="lane-1",
                    scientific_baseline_id="gamenet",
                    program_id="missing-program",
                    profile_id="gamenet",
                ),
            ),
        )

    with pytest.raises(ProtocolValidationError, match="unknown scientific baseline"):
        BaselineRegistry(
            baselines=(),
            reproduction_programs=(
                ReproductionProgram(
                    program_id="prog-1",
                    entrypoint="baselines/prog.py",
                    conda_environment="env",
                    upstream_root="/root/prog",
                    dataset_subdirectory="snapshots",
                    run_subdirectory="runs",
                    required_inputs=("a.pkl",),
                    import_modules=("torch",),
                ),
            ),
            reproduction_lanes=(
                ReproductionLane(
                    lane_id="lane-1",
                    scientific_baseline_id="missing-baseline",
                    program_id="prog-1",
                    profile_id="gamenet",
                ),
            ),
        )
