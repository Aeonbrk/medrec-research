from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock

import pytest

from medrec_research.action_gate import ActionRequest
from medrec_research.aris_bridge import ArisRevisionRecord
from medrec_research.aris_transport import (
    ArisTransportManifest,
    ArisTransportReceipt,
    ArisTransportRegistry,
    ArisTransportStatus,
    FixedArisTransport,
    transport_package_sha256,
)
from medrec_research.aris_transport_remote import RemoteArisRun
from medrec_research.errors import ProtocolValidationError
from medrec_research.execution_control import (
    DeclarationKind,
    DurableExecutionQueue,
    ExecutionDeclaration,
    ExecutionState,
)
from medrec_research.execution_worker import DeclarationBoundWorker
from medrec_research.reproduction_contract import H1Approval, SafeDrugBatchContract
from medrec_research.research_session import RemoteSessionPreflight, ResearchSession

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _manifest() -> ArisTransportManifest:
    registry = ArisTransportRegistry.load_package()
    return ArisTransportManifest(
        request_sha256="1" * 64,
        submission_sha256="2" * 64,
        declaration_sha256="3" * 64,
        contract_sha256="4" * 64,
        h1_approval_sha256="5" * 64,
        preflight_sha256="6" * 64,
        transport_policy_sha256=registry.policy_sha256,
        transport_package_sha256=transport_package_sha256(),
        queue_manager_sha256="9" * 64,
        aris_revision="7" * 40,
        project_id="medrec-research",
        target_id="319-wild",
        lane_id="gamenet",
        action_id="request_reproduction",
        source_revision="8" * 40,
        environment_id="medrec-gamenet",
        resource_profile_id="single-gpu-low-cost",
        command_template_id="aris-source-native-reproduction",
        launch_template_id="safedrug-main-gamenet-source-native",
        evidence_schema_id="safedrug-source-native-v1",
        source_path_id="safedrug-main-checkout",
        data_path_id="medrec-data-root",
        output_path_id="gamenet-reproduction-output",
        max_attempts=1,
        gpu_count=1,
    )


def _replace_manifest(
    manifest: ArisTransportManifest,
    **changes: object,
) -> ArisTransportManifest:
    return replace(manifest, manifest_sha256="", **changes)


def _receipt(
    manifest: ArisTransportManifest,
    status: ArisTransportStatus,
    *,
    attempt: int = 1,
) -> ArisTransportReceipt:
    return ArisTransportReceipt(
        request_sha256=manifest.request_sha256,
        manifest_sha256=manifest.manifest_sha256,
        aris_revision=manifest.aris_revision,
        attempt=attempt,
        status=status,
        reason_code=f"aris-{status.value.replace('_', '-')}",
        observed_at="2026-08-18T12:00:00Z",
        scheduler_job_id="gamenet-111111111111",
    )


def _declaration() -> ExecutionDeclaration:
    return ExecutionDeclaration(
        project_id="medrec-research",
        target_id="319-wild",
        lane_id="gamenet",
        baseline_id="gamenet",
        action_id="request_reproduction",
        kind=DeclarationKind.REMOTE,
        source_revision="88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
        environment_id="medrec-gamenet",
        resource_profile_id="single-gpu-low-cost",
        command_template_id="aris-source-native-reproduction",
        launch_template_id="safedrug-main-gamenet-source-native",
        evidence_schema_id="safedrug-source-native-v1",
        source_path_id="safedrug-main-checkout",
        data_path_id="medrec-data-root",
        output_path_id="gamenet-reproduction-output",
    )


def test_registry_fixes_gamenet_transport_and_blocks_unverified_lanes() -> None:
    registry = ArisTransportRegistry.load_package()

    assert registry.project_id == "medrec-research"
    assert registry.target_id == "319-wild"
    assert registry.ssh_profiles == ("319-lab", "319-lab-via-server")
    template = registry.require_enabled_launch("safedrug-main-gamenet-source-native")
    assert template.environment_id == "medrec-gamenet"
    assert template.command == ("python", "GAMENet.py", "--cuda", "0")
    with pytest.raises(ValueError, match="transport-launch-unverified"):
        registry.require_enabled_launch("safedrug-main-source-native")


def test_fixed_wrapper_uses_only_registered_remote_argv(tmp_path: Path) -> None:
    manifest = _manifest()
    calls: list[tuple[list[str], str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, str(kwargs["input"])))
        receipt = _receipt(manifest, ArisTransportStatus.ACCEPTED)
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(receipt.to_dict()), stderr=""
        )

    transport = FixedArisTransport(tmp_path, clock=lambda: NOW, runner=runner)

    receipt = transport.submit(manifest, fallback_used=True)

    assert receipt.status is ArisTransportStatus.ACCEPTED
    assert calls[0][0] == [
        "rtk",
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        "319-lab-via-server",
        "/root/anaconda3/envs/medrec-core-evaluator/bin/python",
        "-m",
        "medrec_research.aris_transport_remote",
        "submit",
    ]
    assert ArisTransportManifest.from_json(calls[0][1]) == manifest
    assert "command" not in manifest.to_dict()
    assert not any("/" in str(value) for value in manifest.to_dict().values())


def test_transport_failure_requires_explicit_resume(tmp_path: Path) -> None:
    manifest = _manifest()
    operations: list[str] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        operation = command[-1]
        operations.append(operation)
        if operation == "submit":
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="private failure")
        receipt = _receipt(manifest, ArisTransportStatus.ACCEPTED)
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(receipt.to_dict()), stderr=""
        )

    transport = FixedArisTransport(tmp_path, clock=lambda: NOW, runner=runner)

    failed = transport.submit(manifest, fallback_used=False)
    replay = transport.submit(manifest, fallback_used=False)
    resumed = transport.resume(manifest, fallback_used=False)

    assert failed.status is ArisTransportStatus.TRANSPORT_FAILURE
    assert failed.reason_code == "aris-transport-command-failed"
    assert replay == failed
    assert resumed.status is ArisTransportStatus.ACCEPTED
    assert resumed.attempt == 1
    assert operations == ["submit", "resume"]
    assert "private failure" not in json.dumps(failed.to_dict())


def test_remote_helper_stages_isolated_workspace_and_fixed_queue_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    source_root = data_root / "sources" / "safedrug-main-checkout"
    private_data = data_root / "datasets" / "medrec-data-root" / "safedrug-main" / "output"
    (source_root / "src").mkdir(parents=True)
    (source_root / "data").mkdir()
    (source_root / "src" / "GAMENet.py").write_text("print('fixed')\n", encoding="utf-8")
    private_data.mkdir(parents=True)
    queue_manager = aris_root / "skills" / "experiment-queue" / "scripts" / "queue_manager.py"
    queue_manager.parent.mkdir(parents=True)
    queue_manager.write_text("# pinned scheduler\n", encoding="utf-8")
    manifest = _replace_manifest(
        _manifest(),
        queue_manager_sha256=sha256(queue_manager.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))

    def revision(path: Path) -> str | None:
        if path == aris_root.resolve():
            return manifest.aris_revision
        if path == source_root.resolve():
            return manifest.source_revision
        return None

    monkeypatch.setattr("medrec_research.aris_transport_remote._git_revision", revision)
    monkeypatch.setattr("medrec_research.aris_transport_remote._git_clean", lambda _path: True)
    run = RemoteArisRun(manifest, ArisTransportRegistry.load_package())
    monkeypatch.setattr(run, "_start_scheduler", lambda: (123, True))

    receipt = run.submit()

    assert receipt.status is ArisTransportStatus.ACCEPTED
    queue = json.loads(run.queue_manifest_path.read_text(encoding="utf-8"))
    job = queue["phases"][0]["jobs"][0]
    assert queue["conda"] == "medrec-gamenet"
    assert queue["gpus"] == list(range(8))
    assert queue["oom_retry"]["max_attempts"] == 1
    assert job["cmd"] == "python GAMENet.py --cuda 0"
    assert Path(job["expected_output"]).is_relative_to(run.run_root)
    assert (run.workspace / "data" / "output").resolve() == private_data.resolve()
    assert (run.workspace / "src" / "saved" / "GAMENet").resolve() == run.output_dir
    run.queue_state_path.write_text(
        json.dumps({"jobs": [{"id": run.job_id, "status": "running"}]}),
        encoding="utf-8",
    )
    recovered = run.resume()
    assert recovered.status is ArisTransportStatus.RUNNING
    assert recovered.attempt == 1


def test_local_transport_serializes_duplicate_submissions(tmp_path: Path) -> None:
    manifest = _manifest()
    entered = Event()
    release = Event()
    call_lock = Lock()
    calls = 0

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        with call_lock:
            calls += 1
        entered.set()
        assert release.wait(timeout=2)
        receipt = _receipt(manifest, ArisTransportStatus.ACCEPTED)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(receipt.to_dict()),
            stderr="",
        )

    first = FixedArisTransport(tmp_path, clock=lambda: NOW, runner=runner)
    second = FixedArisTransport(tmp_path, clock=lambda: NOW, runner=runner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_result = pool.submit(first.submit, manifest, fallback_used=False)
        assert entered.wait(timeout=2)
        second_result = pool.submit(second.submit, manifest, fallback_used=False)
        release.set()

    assert first_result.result().status is ArisTransportStatus.ACCEPTED
    assert second_result.result() == first_result.result()
    assert calls == 1


def test_remote_transport_serializes_duplicate_scheduler_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    source_root = data_root / "sources" / "safedrug-main-checkout"
    private_data = data_root / "datasets" / "medrec-data-root" / "safedrug-main" / "output"
    (source_root / "src").mkdir(parents=True)
    private_data.mkdir(parents=True)
    queue_manager = aris_root / "skills" / "experiment-queue" / "scripts" / "queue_manager.py"
    queue_manager.parent.mkdir(parents=True)
    queue_manager.write_text("# pinned scheduler\n", encoding="utf-8")
    manifest = _replace_manifest(
        _manifest(),
        queue_manager_sha256=sha256(queue_manager.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))
    monkeypatch.setattr(
        "medrec_research.aris_transport_remote._git_revision",
        lambda path: (
            manifest.aris_revision if path == aris_root.resolve() else manifest.source_revision
        ),
    )
    monkeypatch.setattr("medrec_research.aris_transport_remote._git_clean", lambda _path: True)
    entered = Event()
    release = Event()
    call_lock = Lock()
    starts = 0

    def start(_run: RemoteArisRun) -> tuple[int, bool]:
        nonlocal starts
        with call_lock:
            starts += 1
        entered.set()
        assert release.wait(timeout=2)
        return 123, True

    monkeypatch.setattr(RemoteArisRun, "_start_scheduler", start)
    first = RemoteArisRun(manifest, ArisTransportRegistry.load_package())
    second = RemoteArisRun(manifest, ArisTransportRegistry.load_package())
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_result = pool.submit(first.submit)
        assert entered.wait(timeout=2)
        second_result = pool.submit(second.submit)
        release.set()

    assert first_result.result().status is ArisTransportStatus.ACCEPTED
    assert second_result.result() == first_result.result()
    assert starts == 1


def test_remote_transport_rejects_policy_and_queue_manager_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    source_root = data_root / "sources" / "safedrug-main-checkout"
    private_data = data_root / "datasets" / "medrec-data-root" / "safedrug-main" / "output"
    source_root.mkdir(parents=True)
    private_data.mkdir(parents=True)
    queue_manager = aris_root / "skills" / "experiment-queue" / "scripts" / "queue_manager.py"
    queue_manager.parent.mkdir(parents=True)
    queue_manager.write_text("# pinned scheduler\n", encoding="utf-8")
    manifest = _replace_manifest(
        _manifest(),
        queue_manager_sha256=sha256(queue_manager.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))
    with pytest.raises(ValueError, match="policy binding"):
        RemoteArisRun(
            _replace_manifest(manifest, transport_policy_sha256="0" * 64),
            ArisTransportRegistry.load_package(),
        )

    monkeypatch.setattr(
        "medrec_research.aris_transport_remote._git_revision",
        lambda path: (
            manifest.aris_revision if path == aris_root.resolve() else manifest.source_revision
        ),
    )
    monkeypatch.setattr("medrec_research.aris_transport_remote._git_clean", lambda _path: True)
    queue_manager.write_text("# drifted scheduler\n", encoding="utf-8")
    with pytest.raises(ValueError, match="queue manager binding"):
        RemoteArisRun(manifest, ArisTransportRegistry.load_package()).submit()


def test_remote_cancel_rejects_reused_pid_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    (data_root / "sources" / "safedrug-main-checkout").mkdir(parents=True)
    (data_root / "datasets" / "medrec-data-root" / "safedrug-main" / "output").mkdir(parents=True)
    queue_manager = aris_root / "skills" / "experiment-queue" / "scripts" / "queue_manager.py"
    queue_manager.parent.mkdir(parents=True)
    queue_manager.write_text("# pinned scheduler\n", encoding="utf-8")
    manifest = _replace_manifest(
        _manifest(),
        queue_manager_sha256=sha256(queue_manager.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))
    run = RemoteArisRun(manifest, ArisTransportRegistry.load_package())
    run._persist_manifest()
    run.pid_path.write_text(
        json.dumps(
            {
                "command_sha256": "0" * 64,
                "kind": "aris_transport_scheduler",
                "manifest_sha256": manifest.manifest_sha256,
                "pid": os.getpid(),
                "process_group_id": os.getpgrp(),
                "schema_version": 1,
                "start_time_ticks": 1,
            }
        ),
        encoding="utf-8",
    )
    kills: list[int] = []
    monkeypatch.setattr(run, "_process_identity", lambda _pid: (2, os.getpgrp(), "1" * 64))
    monkeypatch.setattr(os, "killpg", lambda process_group, _signal: kills.append(process_group))

    with pytest.raises(ValueError, match="process identity changed"):
        run.cancel()

    assert kills == []


def test_remote_transport_rejects_runtime_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    outside = tmp_path / "outside"
    data_root.mkdir()
    outside.mkdir()
    (data_root / "aris").symlink_to(outside, target_is_directory=True)
    aris_root.mkdir()
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))

    with pytest.raises(ValueError, match="symlink component"):
        RemoteArisRun(_manifest(), ArisTransportRegistry.load_package())


def test_remote_transport_rejects_in_root_runtime_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "data-root"
    aris_root = tmp_path / "aris"
    real_runtime = data_root / "real-runtime"
    real_runtime.mkdir(parents=True)
    (data_root / "aris").symlink_to(real_runtime, target_is_directory=True)
    aris_root.mkdir()
    monkeypatch.setenv("MEDREC_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ARIS_REPO", str(aris_root))

    with pytest.raises(ValueError, match="symlink component"):
        RemoteArisRun(_manifest(), ArisTransportRegistry.load_package())


def test_dispatch_and_monitor_validation_failures_become_durable_review(
    tmp_path: Path,
) -> None:
    session = ResearchSession(ROOT, clock=lambda: NOW)
    session.execution_dir = tmp_path / "executions"
    session.action_request_dir = tmp_path / "requests"
    session.submission_dir = tmp_path / "submissions"
    session.transport_manifest_dir = tmp_path / "transport-manifests"
    session.transport_receipt_dir = tmp_path / "transport-receipts"
    session.execution_queue = DurableExecutionQueue(session.execution_dir, clock=lambda: NOW)
    session.aris_transport = FixedArisTransport(
        session.transport_receipt_dir,
        clock=lambda: NOW,
    )
    request = ActionRequest.create(
        request_id="action-context-dispatch-failure",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_reproduction",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "b" * 64},),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="9" * 40,
    )
    record = session.execution_queue.enqueue(
        request=request,
        declaration=_declaration(),
        contract_sha256="e" * 64,
        h1_approval_sha256="f" * 64,
    )

    session._dispatch_pending()

    record = session.execution_queue.load(record.request_sha256)
    assert record.state is ExecutionState.REVIEW_PENDING
    assert record.events[-1].reason_code == "execution-dispatch-invalid"

    second_request = ActionRequest.create(
        request_id="action-context-monitor-failure",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_reproduction",
        snapshot_sha256="1" * 64,
        scope_sha256="2" * 64,
        authorities=({"authority_id": "scope", "sha256": "2" * 64},),
        authorization_sha256="3" * 64,
        preflight_sha256="4" * 64,
        remote_revision="9" * 40,
    )
    active = session.execution_queue.enqueue(
        request=second_request,
        declaration=_declaration(),
        contract_sha256="5" * 64,
        h1_approval_sha256="6" * 64,
    )
    active = session.execution_queue.transition(
        active.request_sha256,
        state=ExecutionState.SUBMITTING,
        reason_code="aris-submission-accepted",
    )
    receipt = ArisTransportReceipt(
        request_sha256=active.request_sha256,
        manifest_sha256="7" * 64,
        aris_revision="8" * 40,
        attempt=1,
        status=ArisTransportStatus.ACCEPTED,
        reason_code="aris-submission-accepted",
        observed_at="2026-08-18T12:00:00Z",
    )
    session.aris_transport._persist(receipt)

    session.advance_transport(force=True)

    active = session.execution_queue.load(active.request_sha256)
    assert active.state is ExecutionState.REVIEW_PENDING
    assert active.events[-1].reason_code == "execution-monitor-invalid"


def test_session_binds_distinct_project_and_aris_revisions_and_replays_states(
    tmp_path: Path,
) -> None:
    session = ResearchSession(ROOT, clock=lambda: NOW)
    session.contract_path = tmp_path / "contract.json"
    session.h1_path = tmp_path / "h1.json"
    session.execution_dir = tmp_path / "executions"
    session.action_request_dir = tmp_path / "requests"
    session.submission_dir = tmp_path / "submissions"
    session.transport_manifest_dir = tmp_path / "transport-manifests"
    session.execution_queue = DurableExecutionQueue(session.execution_dir, clock=lambda: NOW)
    session.action_request_dir.mkdir()
    session.contract_path.write_bytes(
        (ROOT / "fixtures" / "benchmark" / "safedrug-batch-h1.json").read_bytes()
    )
    contract = SafeDrugBatchContract.from_json(session.contract_path.read_text(encoding="utf-8"))
    approval = H1Approval.create(
        contract,
        owner="transport-test",
        rationale="fixed server-only transport",
        approved_at="2026-08-18T12:00:00Z",
    )
    session.h1_path.write_text(approval.to_json(), encoding="utf-8")
    declaration = _declaration()
    request = ActionRequest.create(
        request_id="action-context-transport-test",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_reproduction",
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=({"authority_id": "scope", "sha256": "b" * 64},),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="9" * 40,
    )
    session.action_request_dir.joinpath(f"{request.request_sha256}.json").write_text(
        request.to_json(), encoding="utf-8"
    )
    record = session.execution_queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256=contract.contract_sha256,
        h1_approval_sha256=approval.approval_sha256,
    )
    session.preflight = RemoteSessionPreflight(
        observed_at="2026-08-18T12:00:00Z",
        reachable=True,
        fallback_used=True,
        identity_ok=True,
        checkout_exists=True,
        checkout_clean=True,
        local_revision="9" * 40,
        remote_revision="9" * 40,
        revision_matches=True,
        data_root_ready=True,
        conda_available=True,
        environment_verified=True,
        gpu_count=8,
        gpu_available=4,
        disk_free_gib=500,
        blockers=(),
    )
    session.aris_revision = ArisRevisionRecord(
        observed_at="2026-08-18T12:00:00Z",
        candidate_revision="7" * 40,
        active_revision="7" * 40,
        last_known_good_revision="7" * 40,
        candidate_valid=True,
        fallback_used=False,
        blockers=(),
        manifest_sha256="e" * 64,
    )
    submission = DeclarationBoundWorker(
        session.execution_queue,
        session.action_request_dir,
        session.submission_dir,
        clock=lambda: NOW,
    ).prepare(record, declaration, aris_revision=session.aris_revision)

    manifest = session._transport_manifest(record, submission, declaration)

    assert request.remote_revision == "9" * 40
    assert manifest.aris_revision == "7" * 40
    assert manifest.source_revision == "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a"
    assert manifest.max_attempts == 1
    assert manifest.gpu_count == 1
    record = session._apply_transport_receipt(
        record,
        _receipt(manifest, ArisTransportStatus.ACCEPTED),
    )
    record = session._apply_transport_receipt(
        record,
        _receipt(manifest, ArisTransportStatus.TRANSPORT_FAILURE),
    )
    recovery_operations: list[str] = []

    def recovery_runner(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        recovery_operations.append(command[-1])
        accepted = _receipt(manifest, ArisTransportStatus.ACCEPTED)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(accepted.to_dict()),
            stderr="",
        )

    session.aris_transport = FixedArisTransport(
        tmp_path / "recovery-transport-receipts",
        clock=lambda: NOW,
        runner=recovery_runner,
    )
    session.aris_transport._persist(_receipt(manifest, ArisTransportStatus.TRANSPORT_FAILURE))
    with pytest.raises(ProtocolValidationError, match="operation is not fixed"):
        session.control_transport(
            {
                "kind": "transport_control_input",
                "operation": "shell",
                "request_id": request.request_id,
                "schema_version": 1,
            }
        )
    with pytest.raises(ProtocolValidationError, match="unknown field"):
        session.control_transport(
            {
                "host": "319-wild",
                "kind": "transport_control_input",
                "operation": "resume",
                "request_id": request.request_id,
                "schema_version": 1,
            }
        )
    recovery = session.control_transport(
        {
            "kind": "transport_control_input",
            "operation": "resume",
            "request_id": request.request_id,
            "schema_version": 1,
        }
    )
    assert recovery["kind"] == "transport_control_result"
    assert recovery["operation"] == "resume"
    assert recovery["record"]["state"] == ExecutionState.SUBMITTING.value
    assert recovery_operations == ["resume"]
    record = session.execution_queue.load(record.request_sha256)
    for status in (ArisTransportStatus.RUNNING, ArisTransportStatus.COMPLETED):
        record = session._apply_transport_receipt(record, _receipt(manifest, status))

    assert record.state is ExecutionState.INTAKE
    assert [item.state for item in record.events] == [
        ExecutionState.QUEUED,
        ExecutionState.SUBMITTING,
        ExecutionState.REVIEW_PENDING,
        ExecutionState.SUBMITTING,
        ExecutionState.RUNNING,
        ExecutionState.MONITORING,
        ExecutionState.INTAKE,
    ]

    cancel_request = ActionRequest.create(
        request_id="action-context-cancel-reconcile",
        project_id="medrec-research",
        target_id="319-wild",
        action_id="request_reproduction",
        snapshot_sha256="1" * 64,
        scope_sha256="2" * 64,
        authorities=({"authority_id": "scope", "sha256": "2" * 64},),
        authorization_sha256="3" * 64,
        preflight_sha256="4" * 64,
        remote_revision="9" * 40,
    )
    session.action_request_dir.joinpath(f"{cancel_request.request_sha256}.json").write_text(
        cancel_request.to_json(),
        encoding="utf-8",
    )
    cancel_record = session.execution_queue.enqueue(
        request=cancel_request,
        declaration=declaration,
        contract_sha256=contract.contract_sha256,
        h1_approval_sha256=approval.approval_sha256,
    )
    cancel_submission = DeclarationBoundWorker(
        session.execution_queue,
        session.action_request_dir,
        session.submission_dir,
        clock=lambda: NOW,
    ).prepare(cancel_record, declaration, aris_revision=session.aris_revision)
    cancel_manifest = session._transport_manifest(
        cancel_record,
        cancel_submission,
        declaration,
    )
    operations: list[str] = []

    def cancel_runner(
        command: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        operations.append(command[-1])
        completed = _receipt(cancel_manifest, ArisTransportStatus.COMPLETED)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(completed.to_dict()),
            stderr="",
        )

    session.aris_transport = FixedArisTransport(
        tmp_path / "transport-receipts",
        clock=lambda: NOW,
        runner=cancel_runner,
    )
    failure = _receipt(cancel_manifest, ArisTransportStatus.TRANSPORT_FAILURE)
    session.aris_transport._persist(failure)
    cancel_record = session._apply_transport_receipt(cancel_record, failure)
    assert cancel_record.state is ExecutionState.REVIEW_PENDING

    cancel_input = {
        "kind": "transport_control_input",
        "operation": "cancel",
        "request_id": cancel_request.request_id,
        "schema_version": 1,
    }
    first_cancel = session.control_transport(cancel_input)
    second_cancel = session.control_transport(cancel_input)

    assert first_cancel["record"]["state"] == ExecutionState.INTAKE.value
    assert second_cancel["record"]["state"] == ExecutionState.INTAKE.value
    assert operations == ["cancel"]
