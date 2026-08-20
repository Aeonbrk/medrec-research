from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest

from medrec_research import cli

ROOT = Path(__file__).parents[2]


class _LocalSession:
    calls: ClassVar[list[tuple[str, object]]] = []

    def __init__(self, root: Path, *, clock: object) -> None:
        self.root = root
        self.clock = clock

    def apply_monitor_observation(self, value: object) -> dict[str, object]:
        self.calls.append(("monitor", value))
        assert isinstance(value, dict)
        return {
            "kind": "execution_record",
            "request_sha256": value["request_sha256"],
            "schema_version": 1,
        }

    def intake_reproduction_evidence(self, value: object) -> dict[str, object]:
        self.calls.append(("evidence", value))
        return {
            "kind": "decision_packet",
            "packet_sha256": "b" * 64,
            "schema_version": 1,
        }


@pytest.mark.parametrize(
    ("command", "call_name", "identifier_field", "identifier"),
    [
        ("monitor-apply", "monitor", "request_sha256", "a" * 64),
        ("evidence-intake", "evidence", "packet_sha256", "b" * 64),
    ],
)
def test_local_ingress_commands_do_not_prepare_or_run_remote_transport(
    command: str,
    call_name: str,
    identifier_field: str,
    identifier: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _LocalSession.calls = []
    monkeypatch.setattr(cli, "ResearchSession", _LocalSession)
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    value = {
        "kind": "public-safe-input",
        "request_sha256": "a" * 64,
        "schema_version": 1,
    }
    input_path.write_text(json.dumps(value), encoding="utf-8")

    assert (
        cli.main(
            [
                command,
                "--root",
                str(ROOT),
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output[identifier_field] == identifier
    assert _LocalSession.calls == [(call_name, value)]
    assert capsys.readouterr().out.strip() == identifier


def test_local_ingress_rejects_oversized_input_before_session_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _LocalSession.calls = []
    monkeypatch.setattr(cli, "ResearchSession", _LocalSession)
    input_path = tmp_path / "oversized.json"
    input_path.write_text("x" * (1024 * 1024 + 1), encoding="utf-8")

    with pytest.raises(SystemExit):
        cli.main(
            [
                "evidence-intake",
                "--root",
                str(ROOT),
                "--input",
                str(input_path),
                "--output",
                str(tmp_path / "output.json"),
            ]
        )

    assert _LocalSession.calls == []
