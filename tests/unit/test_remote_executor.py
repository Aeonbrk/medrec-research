from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from medrec_research import BaselineRegistry, ProtocolValidationError
from medrec_research.remote_executor import (
    PREPROCESSING_REVISION,
    FrozenSchedule,
    RemoteExecutor,
    RemoteSubmission,
    validate_reproduction_continuation,
)

LOCAL_REVISION = "a" * 40
ENVIRONMENT_SHA256 = "e" * 64
REMOTE_ROOT = "/root/zhb/medrec-research"
DATA_ROOT = "/root/zhb/medrec-data"
TEST_BASELINE_REVISION = "1" * 40

TEST_PROGRAM = "baselines/safedrug_archived.py"
TEST_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ddi_mask_H.pkl",
    "ehr_adj_final.pkl",
    "idx2drug.pkl",
)

SUCCESSOR_LANES = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
    "molerec-embedding",
)
SUCCESSOR_MAPPING = {
    "molerec-retain": (3, "12-15,44-47", 0),
    "molerec-leap": (4, "16-19,48-51", 1),
    "molerec-gamenet": (5, "20-23,52-55", 1),
    "molerec-safedrug-lr-1e-5": (6, "24-27,56-59", 1),
    "molerec-safedrug-lr-1e-4": (1, "4-7,36-39", 0),
    "molerec-safedrug-lr-5e-4": (2, "8-11,40-43", 0),
    "molerec-embedding": (0, "0-3,32-35", 0),
}
PROJECT_ENVIRONMENT_SHA256 = "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
PROJECT_SOURCE_REVISIONS = {
    "safedrug_archived": "8deee38cfdb2a38882377ff95cce5922d6d9e8d6",
    "molerec": "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a",
}


def _registry(*, verified: bool = True) -> BaselineRegistry:
    identity = f'environment_sha256 = "{ENVIRONMENT_SHA256}"\n' if verified else ""
    baseline_entries = "\n".join(
        f'''[[baselines]]
baseline_id = "{baseline_id}"
display_name = "{baseline_id}"
supported_modes = ["reproduction", "comparison"]
readiness = "registered"
reproduction_program = "safedrug-archived"

[baselines.source]
repository = "https://github.com/ycq091044/SafeDrug"
revision = "{TEST_BASELINE_REVISION}"
status = "pinned"
'''
        for baseline_id in ("gamenet", "safedrug", "retain", "leap-safedrug")
    )
    return BaselineRegistry.from_toml(
        f'''schema_version = 1

[[reproduction_programs]]
program_id = "safedrug-archived"
entrypoint = "{TEST_PROGRAM}"
conda_environment = "medrec-safedrug-archived"
upstream_root = "/root/zhb/SafeDrug"
dataset_subdirectory = "snapshots/safedrug-archived-ijcai21"
run_subdirectory = "runs/safedrug-archived"
required_inputs = {list(TEST_INPUTS)!r}
import_modules = ["torch", "models", "util"]
probe_contract = "safedrug_archived_probe"
required_probe_checks = ["cuda_tensor", "rdkit_brics", "dnc_forward"]
expected_dataset_counts = {{ patients = [6350], visits = [14995, 15032], medications = [131], ddi_pairs = [448], molecular_substructures = [491] }}
{identity}

{baseline_entries}
'''.replace("'", '"')
    )


def _valid_probe_json(baseline_id: str = "gamenet") -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "kind": "safedrug_archived_probe",
            "scope": "full",
            "baseline_id": baseline_id,
            "source_revision": TEST_BASELINE_REVISION,
            "environment": {
                "conda_explicit_sha256": ENVIRONMENT_SHA256,
                "cuda_visible_device_count": 1,
            },
            "checks": {
                "cuda_tensor": "passed",
                "rdkit_brics": "passed",
                "dnc_forward": "passed",
                "imports": {"torch": "passed", "models": "passed", "util": "passed"},
            },
            "inputs": {name: "passed" for name in TEST_INPUTS},
            "dataset_counts": {
                "patients": 6350,
                "visits": 14995,
                "medications": 131,
                "ddi_pairs": 448,
                "molecular_substructures": 491,
            },
        }
    )


def _project_schedule_payload(*, harness_revision: str = LOCAL_REVISION) -> dict[str, object]:
    mapping = {
        lane_id: {"gpu": gpu, "cpu_set": cpu_set, "numa": numa}
        for lane_id, (gpu, cpu_set, numa) in SUCCESSOR_MAPPING.items()
    }
    return {
        "schema_version": 1,
        "stage": "u7-measured-gpu-schedule",
        "schedule_state": "frozen",
        "harness_revision": harness_revision,
        "environment_sha256": PROJECT_ENVIRONMENT_SHA256,
        "preprocessing_revision": PREPROCESSING_REVISION,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "model_source_revisions": PROJECT_SOURCE_REVISIONS,
        "selected_mapping": "B",
        "gpu7_reserved": True,
        "formal_execution": {
            "mode": "formal",
            "reserved_gpu": 7,
            "gpu_order": [SUCCESSOR_MAPPING[lane_id][0] for lane_id in SUCCESSOR_LANES],
            "cpu_set_order": [SUCCESSOR_MAPPING[lane_id][1] for lane_id in SUCCESSOR_LANES],
        },
        "mapping": mapping,
    }


def _project_schedule(*, harness_revision: str = LOCAL_REVISION) -> FrozenSchedule:
    return FrozenSchedule.from_dict(
        _project_schedule_payload(harness_revision=harness_revision),
        expected_lane_ids=SUCCESSOR_LANES,
    )


class ScriptedExecutor(RemoteExecutor):
    def __init__(
        self,
        *,
        registry: BaselineRegistry | None = None,
        fail_gate: str | None = None,
        gpu_output: str | None = None,
        responses: dict[str, str] | None = None,
    ):
        super().__init__(registry or _registry())
        self.calls: list[tuple[str, str, str]] = []
        self.fail_gate = fail_gate
        self.gpu_output = gpu_output or "0, GPU-0, 24000, 0"
        self.responses = responses or {}

    def ssh(self, host: str, command: str, *, gate: str) -> str:
        self.calls.append((host, command, gate))
        if gate == self.fail_gate:
            raise ProtocolValidationError(f"remote {gate} check failed")
        parts = command.split()
        baseline_match = "gamenet"
        for name in ("gamenet", "safedrug", "retain", "leap-safedrug"):
            if name in parts:
                baseline_match = name
                break
        outputs = {
            "identity": "root",
            "source-clean": "",
            "source-revision": LOCAL_REVISION,
            "data-root": "ok",
            "data-input": "ok",
            "program": "ok",
            "baseline-source-clean": "",
            "baseline-source-revision": TEST_BASELINE_REVISION,
            "baseline-inputs": "ok",
            "environment": ENVIRONMENT_SHA256,
            "program-probe": _valid_probe_json(baseline_match),
            "gpu": self.gpu_output,
            "disk": str(200 * 1024 * 1024),
            "tmux-launch": "",
            "tmux-cleanup": "",
        }
        outputs.update(self.responses)
        return outputs[gate]


def _run(
    executor: RemoteExecutor,
    *,
    baseline_id: str = "gamenet",
    dry_run: bool = False,
) -> RemoteSubmission:
    return executor.run_baseline(
        baseline_id,
        source_revision=LOCAL_REVISION,
        gpu_index=0,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=dry_run,
    )


def _run_smoke(
    executor: RemoteExecutor,
    *,
    baseline_id: str = "gamenet",
    dry_run: bool = False,
) -> RemoteSubmission:
    return executor.run_smoke(
        baseline_id,
        source_revision=LOCAL_REVISION,
        gpu_index=0,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=dry_run,
    )


def test_ssh_uses_only_approved_alias_and_strict_options() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "root\n", "")

    executor = RemoteExecutor(_registry(), runner=runner)
    assert executor.ssh("319-lab", "id -un", gate="identity") == "root"
    assert calls == [
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "StrictHostKeyChecking=yes",
            "319-lab",
            "id -un",
        ]
    ]

    with pytest.raises(ProtocolValidationError, match="approved 319 alias"):
        executor.ssh("custom-host", "id -un", gate="identity")
    assert len(calls) == 1


def test_remote_executor_dry_run_uses_registry_program_without_ssh() -> None:
    executor = RemoteExecutor(_registry(verified=False))

    submission = executor.run_baseline(
        "gamenet",
        source_revision=LOCAL_REVISION,
        gpu_index=0,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=True,
    )

    assert not submission.preflight_performed
    assert submission.host is None
    assert f"python {REMOTE_ROOT}/{TEST_PROGRAM} gamenet" in submission.command
    assert "--upstream-root /root/zhb/SafeDrug" in submission.command
    assert f"--dataset-root {DATA_ROOT}/snapshots/safedrug-archived-ijcai21" in submission.command
    assert f"--run-root {DATA_ROOT}/runs/safedrug-archived/" in submission.command
    assert f"MEDREC_RUN_ID={submission.session_id}" in submission.command


def test_remote_executor_smoke_dry_run_adds_smoke_mode_and_smoke_session_id() -> None:
    executor = RemoteExecutor(_registry(verified=False))

    submission = executor.run_smoke(
        "safedrug",
        source_revision=LOCAL_REVISION,
        gpu_index=1,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=True,
    )

    assert not submission.preflight_performed
    assert submission.host is None
    assert submission.session_id.startswith("medrec-smoke-safedrug-")
    assert "--mode smoke" in submission.command
    assert "CUDA_VISIBLE_DEVICES=1" in submission.command


def test_primary_connection_failure_uses_only_approved_fallback() -> None:
    class PrimaryUnavailableExecutor(ScriptedExecutor):
        def ssh(self, host: str, command: str, *, gate: str) -> str:
            if host == "319-lab" and gate == "identity":
                self.calls.append((host, command, gate))
                raise ProtocolValidationError("remote identity check failed")
            return super().ssh(host, command, gate=gate)

    executor = PrimaryUnavailableExecutor()

    submission = _run(executor)

    assert submission.host == "319-lab-via-server"
    assert [host for host, _, gate in executor.calls if gate == "identity"] == [
        "319-lab",
        "319-lab-via-server",
    ]


def test_real_run_requires_verified_program_before_ssh() -> None:
    executor = RemoteExecutor(_registry(verified=False))

    with pytest.raises(ProtocolValidationError, match="verified environment_sha256"):
        _run(executor)


def test_unknown_baseline_fails_before_ssh() -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="not registered"):
        _run(executor, baseline_id="unknown")

    assert executor.calls == []


def test_successful_preflight_precedes_explicit_tmux_launch() -> None:
    executor = ScriptedExecutor()

    submission = _run(executor)

    assert submission.preflight_performed
    assert submission.host == "319-lab"
    assert submission.baseline_id == "gamenet"
    assert submission.session_id.startswith("medrec-baseline-gamenet-")
    assert [gate for _, _, gate in executor.calls] == [
        "identity",
        "source-clean",
        "source-revision",
        "data-root",
        "data-input",
        "program",
        "baseline-source-clean",
        "baseline-source-revision",
        "baseline-inputs",
        "environment",
        "gpu",
        "disk",
        "program-probe",
        "tmux-launch",
    ]
    clean_commands = {
        gate: command
        for _, command, gate in executor.calls
        if gate in {"source-clean", "baseline-source-clean"}
    }
    assert clean_commands.keys() == {"source-clean", "baseline-source-clean"}
    assert "status --porcelain --untracked-files=all" in clean_commands["source-clean"]
    assert "status --porcelain --untracked-files=no" in clean_commands["baseline-source-clean"]
    assert "safe.directory" in clean_commands["baseline-source-clean"]
    data_input = next(command for _, command, gate in executor.calls if gate == "data-input")
    assert f"test -d {DATA_ROOT}/snapshots/safedrug-archived-ijcai21" in data_input
    launch = executor.calls[-1][1]
    assert f"MEDREC_RUN_ID={submission.session_id}" in launch
    assert f"MEDREC_DATA_ROOT={DATA_ROOT}" in launch
    assert "SAFEDRUG_ROOT=/root/zhb/SafeDrug" in launch
    assert "CUDA_VISIBLE_DEVICES=0" in launch
    assert "GPU_ID=" not in launch
    assert "CONDA_ENV=medrec-safedrug-archived" in launch
    assert f"python {REMOTE_ROOT}/{TEST_PROGRAM} gamenet" in launch


def test_smoke_submission_executes_smoke_tmux_launch() -> None:
    executor = ScriptedExecutor()

    submission = _run_smoke(executor, baseline_id="safedrug")

    assert submission.preflight_performed
    assert submission.session_id.startswith("medrec-smoke-safedrug-")
    assert "--mode smoke" in submission.command
    launch = executor.calls[-1][1]
    assert f"tmux new-session -d -s {shlex.quote(submission.session_id)}" in launch
    assert "--mode smoke" in launch


def test_smoke_submission_binds_requested_cpu_set() -> None:
    executor = ScriptedExecutor()

    submission = executor.run_smoke(
        "safedrug",
        source_revision=LOCAL_REVISION,
        gpu_index=1,
        cpu_set="0-3,32-35",
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=True,
    )

    assert submission.cpu_set == "0-3,32-35"
    assert "taskset --cpu-list 0-3,32-35 env" in submission.command


def test_safedrug_family_profiles_launch_and_preflight() -> None:
    for profile in ["safedrug", "retain", "leap-safedrug"]:
        executor = ScriptedExecutor()
        sub = _run(executor, baseline_id=profile)
        assert sub.baseline_id == profile
        assert sub.session_id.startswith(f"medrec-baseline-{profile}-")
        assert f"python {REMOTE_ROOT}/{TEST_PROGRAM} {profile}" in sub.command
        assert "baseline-inputs" in [gate for _, _, gate in executor.calls]


@pytest.mark.parametrize(
    "gate",
    [
        "identity",
        "source-clean",
        "source-revision",
        "data-root",
        "data-input",
        "program",
        "baseline-source-clean",
        "baseline-source-revision",
        "baseline-inputs",
        "environment",
        "program-probe",
        "gpu",
        "disk",
    ],
)
def test_failed_preflight_never_creates_tmux(gate: str) -> None:
    executor = ScriptedExecutor(fail_gate=gate)
    with pytest.raises(ProtocolValidationError, match=gate):
        _run(executor, baseline_id="safedrug")

    assert "tmux-launch" not in [observed for _, _, observed in executor.calls]


@pytest.mark.parametrize(
    ("responses", "error"),
    [
        ({"identity": "not-root"}, "identity"),
        ({"source-clean": "?? untracked.py"}, "source-clean"),
        ({"source-revision": "b" * 40}, "source-revision"),
        ({"data-root": "missing"}, "data-root"),
        ({"data-input": "missing"}, "data-input"),
        ({"program": "missing"}, "Program"),
        ({"baseline-source-clean": "?? untracked.py"}, "baseline-source-clean"),
        ({"baseline-source-revision": "b" * 40}, "baseline-source-revision"),
        ({"baseline-inputs": "missing"}, "baseline required input"),
        ({"environment": "f" * 64}, "environment"),
        ({"program-probe": "invalid json"}, "program probe output is not valid JSON"),
        (
            {
                "program-probe": json.dumps(
                    {
                        "schema_version": 1,
                        "kind": "safedrug_archived_probe",
                        "scope": "full",
                        "baseline_id": "safedrug",
                        "source_revision": TEST_BASELINE_REVISION,
                        "environment": {
                            "conda_explicit_sha256": ENVIRONMENT_SHA256,
                            "cuda_visible_device_count": 1,
                        },
                        "checks": {
                            "cuda_tensor": "failed",
                            "rdkit_brics": "passed",
                            "dnc_forward": "passed",
                            "imports": {"torch": "passed", "models": "passed", "util": "passed"},
                        },
                        "inputs": {name: "passed" for name in TEST_INPUTS},
                        "dataset_counts": {
                            "patients": 6350,
                            "visits": 14995,
                            "medications": 131,
                            "ddi_pairs": 448,
                            "molecular_substructures": 491,
                        },
                    }
                )
            },
            "program probe failed runtime checks",
        ),
        (
            {
                "program-probe": json.dumps(
                    {
                        "schema_version": 1,
                        "kind": "safedrug_archived_probe",
                        "scope": "full",
                        "baseline_id": "safedrug",
                        "source_revision": TEST_BASELINE_REVISION,
                        "environment": {
                            "conda_explicit_sha256": ENVIRONMENT_SHA256,
                            "cuda_visible_device_count": 1,
                        },
                        "checks": {
                            "cuda_tensor": "passed",
                            "rdkit_brics": "passed",
                            "dnc_forward": "passed",
                            "imports": {"torch": "passed", "models": "passed", "util": "passed"},
                        },
                        "inputs": {name: "passed" for name in TEST_INPUTS},
                        "dataset_counts": {
                            "patients": 6349,
                            "visits": 14995,
                            "medications": 131,
                            "ddi_pairs": 448,
                            "molecular_substructures": 491,
                        },
                    }
                )
            },
            "dataset counts do not match expected B0",
        ),
        (
            {
                "program-probe": json.dumps(
                    {
                        **json.loads(_valid_probe_json("safedrug")),
                        "dataset_counts": {
                            "patients": 6350,
                            "visits": 14000,
                            "medications": 131,
                            "ddi_pairs": 448,
                            "molecular_substructures": 491,
                        },
                    }
                )
            },
            "dataset counts do not match expected B0",
        ),
        ({"gpu": "not,a,valid,report,shape"}, "GPU report is invalid"),
        ({"gpu": "1, GPU-0, 24000, 0"}, "GPU report is invalid"),
        ({"gpu": "0, GPU-0, 24000, 10.1"}, "GPU is busy"),
        ({"gpu": "0, GPU-0, 19999, 0"}, "GPU capacity is insufficient"),
        ({"disk": "not-an-integer"}, "disk report is invalid"),
        ({"disk": str(99 * 1024 * 1024)}, "disk capacity is insufficient"),
    ],
)
def test_invalid_preflight_result_never_creates_tmux(responses: dict[str, str], error: str) -> None:
    executor = ScriptedExecutor(responses=responses)

    with pytest.raises(ProtocolValidationError, match=error):
        _run(executor, baseline_id="safedrug")

    assert "tmux-launch" not in [gate for _, _, gate in executor.calls]


def test_program_probe_validation_uses_declared_contract() -> None:
    registry = _registry()
    baseline = registry.get("gamenet")
    program = replace(
        registry.get_program("safedrug-archived"),
        probe_contract="custom_probe",
        required_probe_checks=("custom_check",),
        expected_dataset_counts=(("visits", (7,)),),
    )
    probe = json.loads(_valid_probe_json())
    probe["kind"] = "custom_probe"
    probe["checks"] = {
        "custom_check": "passed",
        "imports": probe["checks"]["imports"],
    }
    probe["dataset_counts"] = {"visits": 7}

    RemoteExecutor._validate_program_probe(
        json.dumps(probe),
        baseline=baseline,
        program=program,
        expected_environment_sha256=ENVIRONMENT_SHA256,
        profile_id="gamenet",
    )


def test_program_probe_requires_every_declared_runtime_check() -> None:
    probe = json.loads(_valid_probe_json("safedrug"))
    del probe["checks"]["dnc_forward"]
    executor = ScriptedExecutor(responses={"program-probe": json.dumps(probe)})

    with pytest.raises(ProtocolValidationError, match="runtime checks"):
        _run(executor, baseline_id="safedrug")

    assert "tmux-launch" not in [gate for _, _, gate in executor.calls]


def test_shared_gpu_at_utilization_limit_allows_tmux_launch_without_process_query() -> None:
    executor = ScriptedExecutor(gpu_output="0, GPU-0, 24000, 10")

    _run(executor)

    assert "tmux-launch" in [gate for _, _, gate in executor.calls]
    assert "gpu-processes" not in [gate for _, _, gate in executor.calls]


def test_busy_gpu_fails_before_tmux() -> None:
    executor = ScriptedExecutor(gpu_output="0, GPU-0, 24000, 10.1")

    with pytest.raises(ProtocolValidationError, match="GPU is busy"):
        _run(executor)

    assert "tmux-launch" not in [gate for _, _, gate in executor.calls]


def test_launch_failure_attempts_cleanup_for_the_new_session() -> None:
    executor = ScriptedExecutor(fail_gate="tmux-launch")

    with pytest.raises(ProtocolValidationError, match="tmux-launch"):
        _run(executor)

    assert [gate for _, _, gate in executor.calls[-2:]] == ["tmux-launch", "tmux-cleanup"]
    launch_parts = shlex.split(executor.calls[-2][1])
    cleanup_parts = shlex.split(executor.calls[-1][1])
    assert launch_parts[4] == cleanup_parts[3]


@pytest.mark.parametrize("unsafe_path", ["relative/path", "/data/../private", "/data/bad\npath"])
def test_remote_paths_must_be_absolute_normalized_values(unsafe_path: str) -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="data_root"):
        executor.run_baseline(
            "gamenet",
            source_revision=LOCAL_REVISION,
            gpu_index=0,
            remote_root=REMOTE_ROOT,
            data_root=unsafe_path,
            min_free_gpu_mib=20000,
            min_free_disk_gib=100,
        )

    assert executor.calls == []


def test_run_baseline_with_reproduction_lane_id_and_learning_rate_override() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    submission = executor.run_baseline(
        "molerec-safedrug-lr-1e-5",
        source_revision=LOCAL_REVISION,
        gpu_index=6,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        dry_run=True,
        schedule=_project_schedule(),
    )

    assert submission.baseline_id == "molerec-safedrug-lr-1e-5"
    assert (
        "SafeDrug.py safedrug" in submission.command
        or "safedrug_archived.py safedrug" in submission.command
    )
    assert "--learning-rate 1e-05" in submission.command


def test_seven_lane_reproduction_all_lanes_dry_run() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    lanes = [(lane_id, SUCCESSOR_MAPPING[lane_id][0]) for lane_id in SUCCESSOR_LANES]
    schedule = _project_schedule()
    submissions = [
        executor.run_baseline(
            lane_id,
            source_revision=LOCAL_REVISION,
            gpu_index=gpu,
            remote_root=REMOTE_ROOT,
            data_root=DATA_ROOT,
            min_free_gpu_mib=20000,
            min_free_disk_gib=100,
            dry_run=True,
            attempt_id="attempt-schedule",
            schedule=schedule,
        )
        for lane_id, gpu in lanes
    ]
    assert len(submissions) == 7
    assert [s.baseline_id for s in submissions] == [lane[0] for lane in lanes]


def test_successor_formal_lane_requires_frozen_schedule() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)

    with pytest.raises(ProtocolValidationError, match="frozen schedule"):
        executor.run_baseline(
            "molerec-retain",
            source_revision=LOCAL_REVISION,
            gpu_index=0,
            remote_root=REMOTE_ROOT,
            data_root=DATA_ROOT,
            min_free_gpu_mib=20000,
            min_free_disk_gib=100,
        )

    assert executor.calls == []


def test_exact_frozen_schedule_resolves_declared_cpu_sets_before_submission() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    schedule = _project_schedule()
    requested = [(lane_id, SUCCESSOR_MAPPING[lane_id][0]) for lane_id in SUCCESSOR_LANES]

    resolved = executor.validate_frozen_schedule(
        schedule,
        source_revision=LOCAL_REVISION,
        attempt_id="attempt-schedule",
        requested_lanes=requested,
        requested_cpu_sets=(None,) * len(requested),
        require_complete=True,
    )

    assert resolved == tuple(SUCCESSOR_MAPPING[lane_id][1] for lane_id in SUCCESSOR_LANES)
    assert executor.calls == []


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("duplicate_gpu", "duplicate GPUs"),
        ("overlapping_cpu", "CPU allocation"),
        ("altered_gpu", "GPU allocation"),
        ("reserved_gpu", "reserved GPU"),
    ],
)
def test_schedule_allocation_mismatch_blocks_before_remote_submission(
    mutation: str, error: str
) -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    schedule = _project_schedule()
    requested = [(lane_id, SUCCESSOR_MAPPING[lane_id][0]) for lane_id in SUCCESSOR_LANES]
    requested_cpu_sets: tuple[str | None, ...] = (None,) * len(requested)
    if mutation == "duplicate_gpu":
        requested[1] = (requested[1][0], requested[0][1])
    elif mutation == "overlapping_cpu":
        requested_cpu_sets = (SUCCESSOR_MAPPING[SUCCESSOR_LANES[0]][1],) * len(requested)
    elif mutation == "altered_gpu":
        requested[0] = (requested[0][0], requested[0][1] + 10)
    else:
        schedule = replace(
            schedule,
            allocations=tuple(
                replace(allocation, gpu_index=7)
                if allocation.lane_id == SUCCESSOR_LANES[0]
                else allocation
                for allocation in schedule.allocations
            ),
        )

    with pytest.raises(ProtocolValidationError, match=error):
        executor.validate_frozen_schedule(
            schedule,
            source_revision=LOCAL_REVISION,
            attempt_id="attempt-schedule",
            requested_lanes=requested,
            requested_cpu_sets=requested_cpu_sets,
            require_complete=True,
        )

    assert executor.calls == []


def test_schedule_omitted_lane_blocks_before_remote_submission() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    schedule = _project_schedule()
    requested = [(lane_id, SUCCESSOR_MAPPING[lane_id][0]) for lane_id in SUCCESSOR_LANES[:-1]]

    with pytest.raises(ProtocolValidationError, match="every frozen schedule lane"):
        executor.validate_frozen_schedule(
            schedule,
            source_revision=LOCAL_REVISION,
            attempt_id="attempt-schedule",
            requested_lanes=requested,
            requested_cpu_sets=(None,) * len(requested),
            require_complete=True,
        )

    assert executor.calls == []


def test_reaccepted_schedule_preserves_source_mapping_and_binds_attempt() -> None:
    project_registry = BaselineRegistry.load(
        Path(__file__).parents[2] / "baselines" / "registry.toml"
    )
    executor = ScriptedExecutor(registry=project_registry)
    source = _project_schedule(harness_revision="a" * 40)

    continuation = source.reaccept(
        source_schedule_id="u7-schedule",
        harness_revision="b" * 40,
        attempt_id="formal-20260828-a09fcab-u8-b",
    )

    assert continuation.harness_revision == "b" * 40
    assert continuation.owner_attempt_id == "formal-20260828-a09fcab-u8-b"
    assert continuation.source_schedule_id == "u7-schedule"
    assert continuation.source_harness_revision == "a" * 40
    assert continuation.allocations == source.allocations
    assert continuation.model_source_revisions == source.model_source_revisions
    assert continuation.selected_mapping == source.selected_mapping
    reparsed = FrozenSchedule.from_dict(continuation.to_dict(), expected_lane_ids=SUCCESSOR_LANES)
    assert reparsed == continuation
    assert executor.validate_frozen_schedule(
        reparsed,
        source_revision="b" * 40,
        attempt_id="formal-20260828-a09fcab-u8-b",
        requested_lanes=[(lane_id, SUCCESSOR_MAPPING[lane_id][0]) for lane_id in SUCCESSOR_LANES],
        requested_cpu_sets=(None,) * len(SUCCESSOR_LANES),
        require_complete=True,
    ) == tuple(SUCCESSOR_MAPPING[lane_id][1] for lane_id in SUCCESSOR_LANES)
    assert executor.calls == []


@pytest.mark.parametrize("missing_field", ["attempt_id", "source_schedule_id"])
def test_reaccepted_schedule_requires_attempt_and_source_identity(
    missing_field: str,
) -> None:
    payload = _project_schedule_payload(harness_revision="b" * 40)
    payload.update(
        {
            "schema_version": 2,
            "attempt_id": "formal-20260828-a09fcab-u8-b",
            "source_harness_revision": "a" * 40,
            "source_schedule_id": "u7-schedule",
        }
    )
    del payload[missing_field]

    with pytest.raises(ProtocolValidationError, match="reaccepted frozen schedule"):
        FrozenSchedule.from_dict(payload, expected_lane_ids=SUCCESSOR_LANES)


def test_continuation_admission_reopens_exactly_seven_recoveries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_id = "formal-20260828-a09fcab-u8-b"
    registry = BaselineRegistry.load(Path(__file__).parents[2] / "baselines" / "registry.toml")
    source = _project_schedule(harness_revision="a" * 40)
    artifact_ids: dict[str, str] = {}
    identities: dict[str, dict[str, str]] = {}
    for lane in registry.reproduction_lanes:
        source_root = tmp_path / "runs" / lane.lane_id
        recovery_root = source_root / "recoveries" / f"recovery-{lane.lane_id}"
        recovery_root.mkdir(parents=True)
        artifact_ids[lane.lane_id] = str((recovery_root / "result.json").relative_to(tmp_path))
        baseline = registry.get(lane.scientific_baseline_id)
        identities[lane.lane_id] = {
            "attempt_id": attempt_id,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": source.harness_revision,
            "model_source_revision": baseline.source.revision,
            "preprocessing_revision": source.preprocessing_revision,
            "snapshot_id": source.snapshot_id,
            "environment_sha256": source.environment_sha256,
            "mode": "formal",
            "submission_id": f"submission-{lane.lane_id}",
        }

    def reopen(training_root: Path, **_: object) -> dict[str, object]:
        lane_id = training_root.parent.parent.name
        return {"identity": identities[lane_id], "result": {"recovery": {}}}

    monkeypatch.setattr("medrec_research.remote_executor.reopen_training_evidence", reopen)
    continuation = validate_reproduction_continuation(
        registry=registry,
        source_schedule=source,
        source_schedule_id="u7-schedule",
        attempt_root=tmp_path,
        attempt_id=attempt_id,
        training_artifact_ids=artifact_ids,
        harness_revision="b" * 40,
    )

    assert continuation.owner_attempt_id == attempt_id
    assert continuation.harness_revision == "b" * 40
    assert continuation.allocations == source.allocations


def test_recovered_test_command_targets_reserved_gpu_without_training() -> None:
    registry = BaselineRegistry.load(Path(__file__).parents[2] / "baselines" / "registry.toml")
    executor = RemoteExecutor(registry)

    command = executor.test_launch_command(
        "molerec-safedrug-lr-1e-4",
        attempt_id="formal-20260828-a09fcab-u8-b",
        submission_id="formal-20260828-a09fcab-u8-b-test-safedrug",
        harness_revision="b" * 40,
        remote_root="/root/zhb/medrec-research",
        data_root="/root/zhb/medrec-data",
        recovery_run_root="/root/zhb/medrec-data/runs/source/recoveries/recovery-safedrug",
        training_source_root="/root/zhb/medrec-data/runs/source",
        test_root="/root/zhb/medrec-data/runtime/continuation/tests/molerec-safedrug",
        selection_path="/root/zhb/medrec-data/runtime/attempt/selection.json",
    )

    assert "CUDA_VISIBLE_DEVICES=7" in command
    assert "--phase test" in command
    assert "--phase training" not in command
    assert "--training-source-root /root/zhb/medrec-data/runs/source" in command
    assert "--run-root /root/zhb/medrec-data/runs/source/recoveries/recovery-safedrug" in command
    assert (
        "--test-root /root/zhb/medrec-data/runtime/continuation/tests/molerec-safedrug" in command
    )
