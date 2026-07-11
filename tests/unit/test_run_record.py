from __future__ import annotations

from dataclasses import replace

import pytest

from medrec_research import (
    ArtifactChecksum,
    BaselineDefinition,
    BaselineReadiness,
    ComparisonQualification,
    EvaluationResult,
    ProtocolValidationError,
    ReadinessEvidence,
    ReadinessGate,
    ResearchMode,
    RunParameter,
    RunRecord,
    SourceIdentity,
    SourceStatus,
)

from .test_dataset_manifest import valid_manifest


def comparison_ready_baseline() -> BaselineDefinition:
    return BaselineDefinition(
        baseline_id="reference",
        display_name="Deterministic Reference",
        source=SourceIdentity(
            repository="builtin:medrec_research.reference",
            revision="0.1.0",
            status=SourceStatus.PINNED,
        ),
        supported_modes=(ResearchMode.REPRODUCTION, ResearchMode.COMPARISON),
        readiness=BaselineReadiness.COMPARISON_READY,
        adapter_command=("medrec-research", "reference-adapter"),
        adapter_revision="adapter-0123456789abcdef",
        environment_sha256="e" * 64,
        readiness_evidence=(
            ReadinessEvidence(ReadinessGate.ADAPTER_SMOKE, "1" * 64),
            ReadinessEvidence(ReadinessGate.ENVIRONMENT_LOCK, "2" * 64),
        ),
        comparison_qualifications=(
            ComparisonQualification(
                protocol_version="1.0",
                dataset_manifest_sha256=valid_manifest().manifest_sha256,
                adaptation_budget_sha256="a" * 64,
                evidence=(
                    ReadinessEvidence(ReadinessGate.ADAPTATION_BUDGET, "a" * 64),
                    ReadinessEvidence(ReadinessGate.COHORT_IDENTITY, "4" * 64),
                    ReadinessEvidence(ReadinessGate.CORE_INTEGRITY, "5" * 64),
                    ReadinessEvidence(ReadinessGate.DETERMINISTIC_ADAPTER, "6" * 64),
                    ReadinessEvidence(ReadinessGate.INDEPENDENT_EVALUATION, "7" * 64),
                ),
            ),
        ),
    )


def artifacts() -> tuple[ArtifactChecksum, ...]:
    return (ArtifactChecksum("aggregate-predictions", "f" * 64),)


def evaluation_visit_digest() -> str:
    return valid_manifest().split("test").visit_membership_digest


def test_run_record_is_deterministic_and_round_trips() -> None:
    baseline = comparison_ready_baseline()
    dataset = valid_manifest()
    record = RunRecord.create(
        mode=ResearchMode.COMPARISON,
        protocol_version="1.0",
        baseline=baseline,
        dataset=dataset,
        seed=7,
        selection_split="validation",
        evaluation_split="test",
        parameters=(RunParameter("top_k", 2),),
        evaluation=EvaluationResult(
            visit_count=2,
            jaccard=0.5,
            precision=0.5,
            recall=0.5,
            f1=0.5,
            mean_medication_count=2.0,
        ),
        adaptation_budget_sha256="a" * 64,
        artifact_checksums=artifacts(),
        evaluation_visit_membership_digest=evaluation_visit_digest(),
    )

    parsed = RunRecord.from_json(record.to_json(), baseline=baseline, dataset=dataset)
    assert parsed == record
    assert parsed.run_id == record.run_id
    assert "patient_id" not in record.to_json()
    assert "predicted_medications" not in record.to_json()
    assert parsed.baseline_readiness is BaselineReadiness.COMPARISON_READY
    assert parsed.adapter_revision == "adapter-0123456789abcdef"
    assert parsed.dataset_manifest_sha256 == dataset.manifest_sha256
    assert (
        parsed.evaluation_visit_membership_digest == dataset.split("test").visit_membership_digest
    )


def test_comparison_run_rejects_unverified_baseline() -> None:
    baseline = comparison_ready_baseline()
    baseline = BaselineDefinition(
        baseline_id=baseline.baseline_id,
        display_name=baseline.display_name,
        source=baseline.source,
        supported_modes=baseline.supported_modes,
        readiness=BaselineReadiness.SMOKE_READY,
        adapter_command=baseline.adapter_command,
        adapter_revision=baseline.adapter_revision,
        environment_sha256=baseline.environment_sha256,
        readiness_evidence=tuple(
            item
            for item in baseline.readiness_evidence
            if item.gate in {ReadinessGate.ADAPTER_SMOKE, ReadinessGate.ENVIRONMENT_LOCK}
        ),
    )

    with pytest.raises(ProtocolValidationError, match="Comparison Qualification"):
        RunRecord.create(
            mode=ResearchMode.COMPARISON,
            protocol_version="1.0",
            baseline=baseline,
            dataset=valid_manifest(),
            seed=7,
            selection_split="validation",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(1, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest=evaluation_visit_digest(),
        )


def test_run_record_rejects_test_selection_and_local_paths() -> None:
    with pytest.raises(ProtocolValidationError, match="selection_split"):
        RunRecord.create(
            mode=ResearchMode.COMPARISON,
            protocol_version="1.0",
            baseline=comparison_ready_baseline(),
            dataset=valid_manifest(),
            seed=7,
            selection_split="test",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(2, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest=evaluation_visit_digest(),
        )

    with pytest.raises(ProtocolValidationError, match="local path"):
        RunParameter("checkpoint", "checkpoint=/Users/researcher/private/model.pt")


def test_run_record_rejects_reproduction_mode() -> None:
    with pytest.raises(ProtocolValidationError, match="Comparison Mode"):
        RunRecord.create(
            mode=ResearchMode.REPRODUCTION,
            protocol_version="1.0",
            baseline=comparison_ready_baseline(),
            dataset=valid_manifest(),
            seed=7,
            selection_split="validation",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(2, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest=evaluation_visit_digest(),
        )


def test_run_record_rejects_partial_evaluation_cohort() -> None:
    with pytest.raises(ProtocolValidationError, match=r"visit_count.*test split"):
        RunRecord.create(
            mode=ResearchMode.COMPARISON,
            protocol_version="1.0",
            baseline=comparison_ready_baseline(),
            dataset=valid_manifest(),
            seed=7,
            selection_split="validation",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(1, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest=evaluation_visit_digest(),
        )


def test_run_record_rejects_wrong_evaluation_visit_membership() -> None:
    with pytest.raises(ProtocolValidationError, match="eligible test-visit digest"):
        RunRecord.create(
            mode=ResearchMode.COMPARISON,
            protocol_version="1.0",
            baseline=comparison_ready_baseline(),
            dataset=valid_manifest(),
            seed=7,
            selection_split="validation",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(2, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest="0" * 64,
        )


def test_run_record_rejects_qualification_from_another_dataset() -> None:
    baseline = comparison_ready_baseline()
    qualification = replace(
        baseline.comparison_qualifications[0],
        dataset_manifest_sha256="0" * 64,
    )
    baseline = replace(baseline, comparison_qualifications=(qualification,))

    with pytest.raises(ProtocolValidationError, match="Comparison Qualification"):
        RunRecord.create(
            mode=ResearchMode.COMPARISON,
            protocol_version="1.0",
            baseline=baseline,
            dataset=valid_manifest(),
            seed=7,
            selection_split="validation",
            evaluation_split="test",
            parameters=(),
            evaluation=EvaluationResult(2, 1.0, 1.0, 1.0, 1.0, 1.0),
            adaptation_budget_sha256="a" * 64,
            artifact_checksums=artifacts(),
            evaluation_visit_membership_digest=evaluation_visit_digest(),
        )


def test_comparison_record_requires_authoritative_registry_and_manifest() -> None:
    baseline = comparison_ready_baseline()
    dataset = valid_manifest()
    record = RunRecord.create(
        mode=ResearchMode.COMPARISON,
        protocol_version="1.0",
        baseline=baseline,
        dataset=dataset,
        seed=7,
        selection_split="validation",
        evaluation_split="test",
        parameters=(),
        evaluation=EvaluationResult(2, 1.0, 1.0, 1.0, 1.0, 1.0),
        adaptation_budget_sha256="a" * 64,
        artifact_checksums=artifacts(),
        evaluation_visit_membership_digest=evaluation_visit_digest(),
    )
    other_baseline = replace(baseline, adapter_revision="adapter-fedcba9876543210")

    with pytest.raises(ProtocolValidationError, match="authoritative baseline"):
        RunRecord.from_json(record.to_json(), baseline=other_baseline, dataset=dataset)
