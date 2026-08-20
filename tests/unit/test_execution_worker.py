from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from medrec_research.action_gate import ActionRequest
from medrec_research.aris_bridge import ArisRevisionRecord
from medrec_research.execution_control import (
    DeclarationKind,
    DurableExecutionQueue,
    ExecutionDeclaration,
)
from medrec_research.execution_worker import DeclarationBoundWorker

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _request() -> ActionRequest:
    return ActionRequest.create(
        request_id="action-context-aaaaaaaaaaaaaaaaaaaa",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="refresh_remote_preflight",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "c" * 64},),
        authorization_sha256="d" * 64,
        preflight_sha256="e" * 64,
        remote_revision="f" * 40,
    )


def _declaration() -> ExecutionDeclaration:
    return ExecutionDeclaration(
        project_id="medrec-research",
        target_id="319-wild",
        lane_id="gamenet",
        baseline_id="gamenet",
        action_id="refresh_remote_preflight",
        kind=DeclarationKind.LOCAL,
        source_revision="f" * 40,
        environment_id="medrec-gamenet",
        resource_profile_id="single-gpu-low-cost",
        command_template_id="fixed-read-only-preflight",
        launch_template_id="gamenet-preflight",
        evidence_schema_id="safedrug-source-native-v1",
        source_path_id="source",
        data_path_id="data",
        output_path_id="output",
    )


def _aris(*, valid: bool) -> ArisRevisionRecord:
    return ArisRevisionRecord(
        observed_at="2026-08-16T12:00:00Z",
        candidate_revision="f" * 40 if valid else "a" * 40,
        active_revision="f" * 40 if valid else "b" * 40,
        last_known_good_revision="f" * 40,
        candidate_valid=valid,
        fallback_used=not valid,
        blockers=() if valid else ("aris-candidate-fallback",),
        manifest_sha256="1" * 64,
    )


def test_worker_persists_declaration_derived_envelope(tmp_path: Path) -> None:
    request_dir = tmp_path / "requests"
    queue_dir = tmp_path / "queue"
    submission_dir = tmp_path / "submissions"
    request_dir.mkdir()
    request = _request()
    request_path = request_dir / f"{request.request_sha256}.json"
    request_path.write_text(request.to_json(), encoding="utf-8")
    declaration = _declaration()
    queue = DurableExecutionQueue(queue_dir, clock=lambda: NOW)
    record = queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256="2" * 64,
        h1_approval_sha256="3" * 64,
    )
    worker = DeclarationBoundWorker(
        queue,
        request_dir,
        submission_dir,
        clock=lambda: NOW,
    )

    submission = worker.prepare(record, declaration, aris_revision=_aris(valid=True))

    assert submission.status == "awaiting-local-dispatch"
    assert submission.request_sha256 == request.request_sha256
    assert "command" not in submission.to_dict()
    replay = DeclarationBoundWorker(
        queue,
        request_dir,
        submission_dir,
        clock=lambda: datetime(2026, 8, 16, 13, 0, tzinfo=UTC),
    ).prepare(record, declaration, aris_revision=_aris(valid=True))
    assert replay == submission
    assert worker.records() == (submission,)


def test_worker_blocks_when_aris_candidate_is_not_current(tmp_path: Path) -> None:
    request_dir = tmp_path / "requests"
    queue_dir = tmp_path / "queue"
    submission_dir = tmp_path / "submissions"
    request_dir.mkdir()
    request = _request()
    request_dir.joinpath(f"{request.request_sha256}.json").write_text(
        request.to_json(), encoding="utf-8"
    )
    declaration = _declaration()
    queue = DurableExecutionQueue(queue_dir, clock=lambda: NOW)
    record = queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256="2" * 64,
        h1_approval_sha256="3" * 64,
    )
    worker = DeclarationBoundWorker(queue, request_dir, submission_dir, clock=lambda: NOW)

    submission = worker.prepare(record, declaration, aris_revision=_aris(valid=False))

    assert submission.status == "blocked"
    assert "aris-candidate-unverified" in submission.blockers
    assert worker.records() == ()

    recovered = worker.prepare(record, declaration, aris_revision=_aris(valid=True))

    assert recovered.status == "awaiting-local-dispatch"
    assert recovered.blockers == ()
    assert worker.records() == (recovered,)


def test_worker_keeps_project_and_aris_revisions_as_separate_authorities(
    tmp_path: Path,
) -> None:
    request_dir = tmp_path / "requests"
    request_dir.mkdir()
    request = _request()
    request_dir.joinpath(f"{request.request_sha256}.json").write_text(
        request.to_json(), encoding="utf-8"
    )
    declaration = _declaration()
    queue = DurableExecutionQueue(tmp_path / "queue", clock=lambda: NOW)
    record = queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256="2" * 64,
        h1_approval_sha256="3" * 64,
    )
    aris = ArisRevisionRecord(
        observed_at="2026-08-16T12:00:00Z",
        candidate_revision="a" * 40,
        active_revision="a" * 40,
        last_known_good_revision="a" * 40,
        candidate_valid=True,
        fallback_used=False,
        blockers=(),
        manifest_sha256="1" * 64,
    )

    submission = DeclarationBoundWorker(
        queue,
        request_dir,
        tmp_path / "submissions",
        clock=lambda: NOW,
    ).prepare(record, declaration, aris_revision=aris)

    assert request.remote_revision == "f" * 40
    assert aris.active_revision == "a" * 40
    assert submission.status == "awaiting-local-dispatch"
