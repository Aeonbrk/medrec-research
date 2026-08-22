from __future__ import annotations

import subprocess

import pytest

from medrec_research import BaselineDefinition, BaselineRegistry, ProtocolValidationError
from medrec_research.remote_executor import RemoteExecutor, RemoteSubmission

LOCAL_REVISION = "a" * 40
ENVIRONMENT_SHA256 = "e" * 64
REMOTE_ROOT = "/root/zhb/medrec-research"
DATA_ROOT = "/root/zhb/medrec-data"


def _baseline(*, readiness: str = "smoke_ready") -> BaselineDefinition:
    readiness_fields = ""
    if readiness != "registered":
        readiness_fields = f'''adapter_command = ["python", "adapter.py"]
adapter_revision = "adapter-0123456789abcdef"
environment_sha256 = "{ENVIRONMENT_SHA256}"

[[baselines.readiness_evidence]]
gate = "adapter_smoke"
artifact_sha256 = "{"1" * 64}"

[[baselines.readiness_evidence]]
gate = "environment_lock"
artifact_sha256 = "{"2" * 64}"
'''
    return BaselineRegistry.from_toml(
        f'''schema_version = 1

[[baselines]]
baseline_id = "gamenet"
display_name = "GAMENet"
supported_modes = ["reproduction", "comparison"]
readiness = "{readiness}"
{readiness_fields}
[baselines.source]
repository = "https://github.com/ycq091044/SafeDrug"
revision = "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a"
status = "pinned"
'''
    ).get("gamenet")


class ScriptedExecutor(RemoteExecutor):
    def __init__(
        self,
        *,
        fail_gate: str | None = None,
        gpu_output: str | None = None,
        responses: dict[str, str] | None = None,
    ):
        super().__init__()
        self.calls: list[tuple[str, str, str]] = []
        self.fail_gate = fail_gate
        self.gpu_output = gpu_output or "0, GPU-0, 24000, 0"
        self.responses = responses or {}

    def ssh(self, host: str, command: str, *, gate: str) -> str:
        self.calls.append((host, command, gate))
        if gate == self.fail_gate:
            raise ProtocolValidationError(f"remote {gate} check failed")
        outputs = {
            "identity": "root",
            "source-clean": "",
            "source-revision": LOCAL_REVISION,
            "data-root": "ok",
            "launcher": "ok",
            "baseline-source-clean": "",
            "baseline-source-revision": "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
            "environment": ENVIRONMENT_SHA256,
            "gpu": self.gpu_output,
            "gpu-processes": "",
            "disk": str(200 * 1024 * 1024),
            "tmux-launch": "",
            "tmux-cleanup": "",
        }
        outputs.update(self.responses)
        return outputs[gate]


def _run(
    executor: RemoteExecutor, *, baseline: BaselineDefinition | None = None
) -> RemoteSubmission:
    return executor.run_baseline(
        baseline or _baseline(),
        source_revision=LOCAL_REVISION,
        gpu_index=0,
        remote_root=REMOTE_ROOT,
        data_root=DATA_ROOT,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
    )


def test_ssh_uses_only_approved_alias_and_strict_options() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "root\n", "")

    executor = RemoteExecutor(runner=runner)
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


def test_remote_executor_dry_run_uses_explicit_launcher_without_ssh() -> None:
    executor = ScriptedExecutor()

    submission = executor.run_baseline(
        _baseline(readiness="registered"),
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
    assert "bash baselines/scripts/run_gamenet_319.sh gamenet" in submission.command
    assert executor.calls == []


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


def test_registered_baseline_fails_before_ssh() -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="smoke_ready"):
        _run(executor, baseline=_baseline(readiness="registered"))

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
        "launcher",
        "baseline-source-clean",
        "baseline-source-revision",
        "environment",
        "gpu",
        "gpu-processes",
        "disk",
        "tmux-launch",
    ]
    clean_commands = {
        gate: command
        for _, command, gate in executor.calls
        if gate in {"source-clean", "baseline-source-clean"}
    }
    assert clean_commands.keys() == {"source-clean", "baseline-source-clean"}
    assert all(
        "status --porcelain --untracked-files=all" in command for command in clean_commands.values()
    )
    launch = executor.calls[-1][1]
    assert f"MEDREC_DATA_ROOT={DATA_ROOT}" in launch
    assert "GPU_ID=0" in launch
    assert "CONDA_ENV=medrec-gamenet" in launch
    assert "bash baselines/scripts/run_gamenet_319.sh gamenet" in launch


@pytest.mark.parametrize(
    "gate",
    [
        "identity",
        "source-clean",
        "source-revision",
        "data-root",
        "launcher",
        "baseline-source-clean",
        "baseline-source-revision",
        "environment",
        "gpu",
        "gpu-processes",
        "disk",
    ],
)
def test_failed_preflight_never_creates_tmux(gate: str) -> None:
    executor = ScriptedExecutor(fail_gate=gate)

    with pytest.raises(ProtocolValidationError, match=gate):
        _run(executor)

    assert "tmux-launch" not in [observed for _, _, observed in executor.calls]


@pytest.mark.parametrize(
    ("responses", "error"),
    [
        ({"identity": "not-root"}, "identity"),
        ({"source-clean": "?? untracked.py"}, "source-clean"),
        ({"source-revision": "b" * 40}, "source-revision"),
        ({"data-root": "missing"}, "data-root"),
        ({"launcher": "missing"}, "launcher"),
        ({"baseline-source-clean": "?? untracked.py"}, "baseline-source-clean"),
        ({"baseline-source-revision": "b" * 40}, "baseline-source-revision"),
        ({"environment": "f" * 64}, "environment"),
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
        _run(executor)

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


def test_launch_failure_does_not_terminate_remote_jobs_automatically() -> None:
    executor = ScriptedExecutor(fail_gate="tmux-launch")

    with pytest.raises(ProtocolValidationError, match="tmux-launch"):
        _run(executor)

    assert "tmux-cleanup" not in [gate for _, _, gate in executor.calls]


@pytest.mark.parametrize("unsafe_path", ["relative/path", "/data/../private", "/data/bad\npath"])
def test_remote_paths_must_be_absolute_normalized_values(unsafe_path: str) -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="data_root"):
        executor.run_baseline(
            _baseline(),
            source_revision=LOCAL_REVISION,
            gpu_index=0,
            remote_root=REMOTE_ROOT,
            data_root=unsafe_path,
            min_free_gpu_mib=20000,
            min_free_disk_gib=100,
        )

    assert executor.calls == []


def test_remote_executor_parse_progress() -> None:
    executor = RemoteExecutor()
    assert executor._parse_progress("") == "Idle / Not started"
    assert executor._parse_progress("Training Epoch 15/50 in progress...") == "Epoch 15/50"
    assert executor._parse_progress("Processing batch 100, completed 75%") == "75%"
