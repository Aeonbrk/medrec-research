from __future__ import annotations

import shlex
import subprocess

import pytest

from medrec_research import BaselineDefinition, BaselineRegistry, ProtocolValidationError
from medrec_research.remote_executor import BaselineLauncher, RemoteExecutor, RemoteSubmission

LOCAL_REVISION = "a" * 40
ENVIRONMENT_SHA256 = "e" * 64
REMOTE_ROOT = "/root/zhb/medrec-research"
DATA_ROOT = "/root/zhb/medrec-data"
TEST_BASELINE_REVISION = "1" * 40


ADAPTER_REVISION = "sha256:" + "0" * 64
TEST_RUNNER = "baselines/adapters/safedrug_archived.py"
TEST_INPUTS = (
    "data/records_final.pkl",
    "data/voc_final.pkl",
    "data/ddi_A_final.pkl",
)


def _launcher(baseline_id: str = "gamenet") -> BaselineLauncher:
    return BaselineLauncher(
        baseline_id=baseline_id,
        conda_environment="medrec-safedrug-archived",
        upstream_root="/root/zhb/SafeDrug",
        required_data_subdirectory="mimic-iii",
        command=("python", TEST_RUNNER, baseline_id),
        adapter_files=(TEST_RUNNER,),
        required_inputs=TEST_INPUTS,
    )


def _baseline(
    *,
    baseline_id: str = "gamenet",
    readiness: str = "registered",
    command: list[str] | None = None,
    adapter_revision: str | None = ADAPTER_REVISION,
    environment_sha256: str | None = ENVIRONMENT_SHA256,
    pinned: bool = True,
    source_revision: str = TEST_BASELINE_REVISION,
) -> BaselineDefinition:
    cmd = command or list(_launcher(baseline_id).command)
    cmd_toml = str(cmd).replace("'", '"')
    source_status = "pinned" if pinned else "needs_pin"
    source_rev = f'revision = "{source_revision}"' if pinned else ""

    adapter_rev_line = f'adapter_revision = "{adapter_revision}"' if adapter_revision else ""
    env_line = f'environment_sha256 = "{environment_sha256}"' if environment_sha256 else ""

    return BaselineRegistry.from_toml(
        f"""schema_version = 1

[[baselines]]
baseline_id = "{baseline_id}"
display_name = "{baseline_id}"
supported_modes = ["reproduction", "comparison"]
readiness = "{readiness}"
adapter_command = {cmd_toml}
{adapter_rev_line}
{env_line}

[baselines.source]
repository = "https://github.com/ycq091044/SafeDrug"
{source_rev}
status = "{source_status}"
"""
    ).get(baseline_id)


class ScriptedExecutor(RemoteExecutor):
    def __init__(
        self,
        *,
        fail_gate: str | None = None,
        gpu_output: str | None = None,
        responses: dict[str, str] | None = None,
    ):
        super().__init__(
            launchers={
                baseline_id: _launcher(baseline_id)
                for baseline_id in ("gamenet", "safedrug", "retain", "leap-safedrug")
            }
        )
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
            "data-input": "ok",
            "launcher": "ok",
            "launcher-digest": ADAPTER_REVISION,
            "baseline-source-clean": "",
            "baseline-source-revision": TEST_BASELINE_REVISION,
            "baseline-inputs": "ok",
            "environment": ENVIRONMENT_SHA256,
            "environment-imports": "ok",
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
    baseline: BaselineDefinition | None = None,
    dry_run: bool = False,
) -> RemoteSubmission:
    return executor.run_baseline(
        baseline or _baseline(),
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

    executor = RemoteExecutor(launchers={"gamenet": _launcher()}, runner=runner)
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
    assert f"python {TEST_RUNNER} gamenet" in submission.command
    assert f"MEDREC_RUN_ID={submission.session_id}" in submission.command
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


def test_undeclared_adapter_fails_before_ssh() -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="adapter_command"):
        _run(executor, baseline=_baseline(command=["custom", "adapter.py"]))

    assert executor.calls == []


def test_unpinned_source_fails_before_ssh() -> None:
    executor = ScriptedExecutor()

    with pytest.raises(ProtocolValidationError, match="pinned"):
        _run(executor, baseline=_baseline(pinned=False))

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
        "launcher",
        "launcher-digest",
        "baseline-source-clean",
        "baseline-source-revision",
        "baseline-inputs",
        "environment",
        "environment-imports",
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
    assert "status --porcelain --untracked-files=all" in clean_commands["source-clean"]
    assert "status --porcelain --untracked-files=no" in clean_commands["baseline-source-clean"]
    assert "safe.directory" in clean_commands["baseline-source-clean"]
    data_input = next(command for _, command, gate in executor.calls if gate == "data-input")
    assert f"test -d {DATA_ROOT}/mimic-iii" in data_input
    launch = executor.calls[-1][1]
    assert f"MEDREC_RUN_ID={submission.session_id}" in launch
    assert f"MEDREC_DATA_ROOT={DATA_ROOT}" in launch
    assert "SAFEDRUG_ROOT=/root/zhb/SafeDrug" in launch
    assert "CUDA_VISIBLE_DEVICES=0" in launch
    assert "GPU_ID=" not in launch
    assert "CONDA_ENV=medrec-safedrug-archived" in launch
    assert f"python {TEST_RUNNER} gamenet" in launch


def test_safedrug_family_profiles_launch_and_preflight() -> None:
    for profile in ["safedrug", "retain", "leap-safedrug"]:
        executor = ScriptedExecutor()
        base = _baseline(baseline_id=profile)
        sub = _run(executor, baseline=base)
        assert sub.baseline_id == profile
        assert sub.session_id.startswith(f"medrec-baseline-{profile}-")
        assert f"python {TEST_RUNNER} {profile}" in sub.command
        assert "baseline-inputs" in [gate for _, _, gate in executor.calls]


@pytest.mark.parametrize(
    "gate",
    [
        "identity",
        "source-clean",
        "source-revision",
        "data-root",
        "data-input",
        "launcher",
        "launcher-digest",
        "baseline-source-clean",
        "baseline-source-revision",
        "baseline-inputs",
        "environment",
        "environment-imports",
        "gpu",
        "gpu-processes",
        "disk",
    ],
)
def test_failed_preflight_never_creates_tmux(gate: str) -> None:
    executor = ScriptedExecutor(fail_gate=gate)
    base = _baseline(baseline_id="safedrug")

    with pytest.raises(ProtocolValidationError, match=gate):
        _run(executor, baseline=base)

    assert "tmux-launch" not in [observed for _, _, observed in executor.calls]


@pytest.mark.parametrize(
    ("responses", "error"),
    [
        ({"identity": "not-root"}, "identity"),
        ({"source-clean": "?? untracked.py"}, "source-clean"),
        ({"source-revision": "b" * 40}, "source-revision"),
        ({"data-root": "missing"}, "data-root"),
        ({"data-input": "missing"}, "data-input"),
        ({"launcher": "missing"}, "launcher"),
        ({"launcher-digest": "sha256:" + "f" * 64}, "adapter digest"),
        ({"baseline-source-clean": "?? untracked.py"}, "baseline-source-clean"),
        ({"baseline-source-revision": "b" * 40}, "baseline-source-revision"),
        ({"baseline-inputs": "missing"}, "baseline required input"),
        ({"environment": "f" * 64}, "environment"),
        ({"environment-imports": "failed"}, "environment import probe"),
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
        _run(executor, baseline=_baseline(baseline_id="safedrug"))

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
            _baseline(),
            source_revision=LOCAL_REVISION,
            gpu_index=0,
            remote_root=REMOTE_ROOT,
            data_root=unsafe_path,
            min_free_gpu_mib=20000,
            min_free_disk_gib=100,
        )

    assert executor.calls == []
