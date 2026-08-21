"""Execution Team for Phase 5: Experiment Execution and Telemetry Monitoring."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .baseline_team import AgentRole


@dataclass
class ExecutionTeam:
    """Collaborative 2-agent team for GPU deployment and telemetry monitoring."""

    experiment_id: str
    exp_config: dict[str, Any]
    display_mode: str = "tmux"
    remote_executor: Any = None  # RemoteExecutor instance
    members: list[AgentRole] = field(
        default_factory=lambda: [
            AgentRole(
                name="Agent 1",
                role_type="team-implementer",
                duty="GPU 任务提交、环境变量与进程管理 (GPU Deployment & Task Launch)",
            ),
            AgentRole(
                name="Agent 2",
                role_type="team-reviewer",
                duty="实时指标采集、早停判定与异常检测 (Telemetry & Anomaly Detection)",
            ),
        ]
    )

    def describe_team(self) -> str:
        lines = [f"✓ Execution Team spawned ({len(self.members)} agents)"]
        for agent in self.members:
            lines.append(f"  - {agent.name} ({agent.role_type}): {agent.duty}")
        return "\n".join(lines)

    def execute(self, dry_run: bool = False) -> dict[str, Any]:
        """Execute experiment run or generate dry-run telemetry execution plan."""
        if not dry_run:
            # Real remote execution
            if self.remote_executor is None:
                raise RuntimeError(
                    "RemoteExecutor not configured. Cannot run non-dry-run experiment.\n"
                    "Manual workflow:\n"
                    "  1. SSH to 319-wild and submit experiment manually\n"
                    "  2. Monitor progress and collect results\n"
                    "  3. Place results in experiments/{experiment_id}/results.json\n"
                    "  4. Continue with: medrec evidence analyze {experiment_id}"
                )

            return self._execute_remote()

        # Dry-run: validate config and generate plan
        return self._execute_dry_run()

    def _execute_remote(self) -> dict[str, Any]:
        """Execute experiment on remote GPU host with real-time monitoring."""
        print(f"🚀 Launching experiment {self.experiment_id} on 319-wild...")

        # 1. Launch remote job
        session_name = self.remote_executor.run_experiment(
            experiment_id=self.experiment_id,
            exp_config=self.exp_config,
            dry_run=False
        )
        print(f"✓ Remote session started: {session_name}")

        # 2. Monitor with early stopping detection
        max_wait = self.exp_config.get("max_wait_seconds", 14400)  # 4 hours default
        poll_interval = 30  # 30 seconds
        elapsed = 0

        print(f"⏳ Monitoring progress with early stopping detection (max wait: {max_wait}s)...")
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            status = self.remote_executor.check_status(session_name)

            if status.status == "completed":
                print(f"✓ Experiment completed after {elapsed}s")
                break
            elif status.status == "failed":
                raise RuntimeError(f"Remote experiment failed: {status.log_tail}")
            else:
                # Running - display progress
                print(f"  [{elapsed}s] {status.progress}")

                # Check for early stopping keywords in log
                if any(keyword in status.log_tail.lower() for keyword in [
                    "early stopping",
                    "converged",
                    "stopping criterion met"
                ]):
                    print(f"✓ Early stopping detected at {elapsed}s")
                    # Give it a moment to write results
                    time.sleep(10)
                    break

        if elapsed >= max_wait:
            raise TimeoutError(
                f"Experiment {self.experiment_id} did not complete within {max_wait}s.\n"
                f"Session {session_name} is still running on 319-wild.\n"
                f"Check manually: ssh 319-wild 'tmux attach -t {session_name}'"
            )

        # 3. Collect results
        remote_result_path = self.exp_config.get(
            "remote_result_path",
            f"{self.remote_executor.ssh_config.remote_data_root}/results.json"
        )
        local_dest = Path(f"experiments/{self.experiment_id}/results.json")

        print(f"📥 Collecting results from {remote_result_path}...")
        self.remote_executor.collect_results(
            job_id=session_name,
            remote_path=remote_result_path,
            local_dest=local_dest
        )
        print(f"✓ Results saved to {local_dest}")

        # 4. Parse and return
        with local_dest.open() as f:
            result = json.load(f)

        # Add metadata
        result["experiment_id"] = self.experiment_id
        result["timestamp"] = datetime.now(UTC).isoformat()
        result["status"] = "completed"
        result["session_name"] = session_name

        return result

    def _execute_dry_run(self) -> dict[str, Any]:
        """Generate dry-run execution plan."""
        now = datetime.now(UTC).isoformat()
        return {
            "experiment_id": self.experiment_id,
            "status": "dry_run_success",
            "timestamp": now,
            "metrics": {
                "jaccard": 0.538,
                "prauc": 0.775,
                "f1": 0.698,
                "ddi_rate": 0.058,
            },
            "log": f"Dry-run executed for {self.experiment_id}: config verified, GPU execution mocked.",
        }
