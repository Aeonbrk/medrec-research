from __future__ import annotations

import json
import shlex
import subprocess

import pytest

from medrec_research import BaselineRegistry, ProtocolValidationError
from medrec_research.remote_executor import RemoteExecutor, RemoteSubmission

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


class ScriptedExecutor(RemoteExecutor):
    def __init__(
        self,
        *,
        fail_gate: str | None = None,
        gpu_output: str | None = None,
        responses: dict[str, str] | None = None,
    ):
        super().__init__(_registry())
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
            "gpu-processes": "",
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
        "gpu-processes",
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
        "gpu-processes",
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
                            "visits": 15032,
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
        ({"gpu": "0, GPU-0, 24000, 1"}, "GPU is busy"),
        ({"gpu": "0, GPU-0, 19999, 0"}, "GPU capacity is insufficient"),
        ({"gpu-processes": "not-a-gpu-uuid"}, "GPU process report is invalid"),
        ({"gpu-processes": "GPU-0"}, "GPU is busy"),
        ({"disk": "not-an-integer"}, "disk report is invalid"),
        ({"disk": str(99 * 1024 * 1024)}, "disk capacity is insufficient"),
    ],
)
def test_invalid_preflight_result_never_creates_tmux(responses: dict[str, str], error: str) -> None:
    executor = ScriptedExecutor(responses=responses)

    with pytest.raises(ProtocolValidationError, match=error):
        _run(executor, baseline_id="safedrug")

    assert "tmux-launch" not in [gate for _, _, gate in executor.calls]


def test_nvidia_idle_process_sentinel_allows_tmux_launch() -> None:
    executor = ScriptedExecutor(responses={"gpu-processes": "No running processes found"})

    _run(executor)

    assert "tmux-launch" in [gate for _, _, gate in executor.calls]


def test_busy_gpu_fails_before_tmux() -> None:
    executor = ScriptedExecutor(gpu_output="0, GPU-0, 24000, 1")

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
