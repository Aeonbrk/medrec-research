from __future__ import annotations

from medrec_research.remote_executor import RemoteExecutor, SSHConfig


def test_ssh_config_from_dict():
    data = {
        "host": "custom-host",
        "user": "tester",
        "key_path": "~/.ssh/custom_rsa",
        "remote_data_root": "/custom/data",
        "port": 2222,
        "timeout": 120,
    }
    cfg = SSHConfig.from_dict(data)
    assert cfg.host == "custom-host"
    assert cfg.user == "tester"
    assert cfg.port == 2222
    assert cfg.timeout == 120
    assert cfg.remote_data_root == "/custom/data"


def test_remote_executor_dry_run():
    executor = RemoteExecutor()
    job_id = executor.run_baseline("safedrug", {"conda_env": "safedrug-env"}, dry_run=True)
    assert "medrec-baseline-safedrug-" in job_id

    exp_job_id = executor.run_experiment("H001-substructure", {}, dry_run=True)
    assert "medrec-exp-H001-substructure-" in exp_job_id


def test_remote_executor_parse_progress():
    executor = RemoteExecutor()
    assert executor._parse_progress("") == "Idle / Not started"
    assert executor._parse_progress("Training Epoch 15/50 in progress...") == "Epoch 15/50"
    assert executor._parse_progress("Processing batch 100, completed 75%") == "75%"
