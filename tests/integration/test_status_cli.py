from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from medrec_research.cli import main
from medrec_research.project_status import ProjectStatus

ROOT = Path(__file__).parents[2]
PROGRAM = ROOT / "baselines/programs/classic-six.toml"
AUDITS = ROOT / "baselines/audits"
REVIEWS = ROOT / "fixtures/benchmark/audit-reviews.json"
DIAGNOSTICS = ROOT / "fixtures/benchmark/selection-diagnostics.json"
REGISTRY = ROOT / "baselines/registry.toml"
NOW = datetime(2026, 7, 11, 1, 3, tzinfo=UTC)


def _scope(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "adaptation_budget_sha256": "b" * 64,
                "dataset_manifest_sha256": "a" * 64,
                "protocol_version": "1.0",
            }
        ),
        encoding="utf-8",
    )


def test_real_six_audits_validate_and_selection_publishes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "audit-validate",
                "--program",
                str(PROGRAM),
                "--audit-dir",
                str(AUDITS),
            ]
        )
        == 0
    )
    assert len(capsys.readouterr().out.strip()) == 64

    output = tmp_path / "selection.json"
    assert (
        main(
            [
                "selection-publish",
                "--program",
                str(PROGRAM),
                "--audit-dir",
                str(AUDITS),
                "--reviews",
                str(REVIEWS),
                "--diagnostics",
                str(DIAGNOSTICS),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    selection = json.loads(output.read_text(encoding="utf-8"))
    assert selection["selected_candidate_id"] == "gamenet"
    assert capsys.readouterr().out.strip() == selection["selection_id"]


def test_status_publish_uses_injected_clock_and_is_byte_stable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scope = tmp_path / "scope.json"
    _scope(scope)
    outputs = (tmp_path / "status-1.json", tmp_path / "status-2.json")
    for output in outputs:
        assert (
            main(
                [
                    "status-publish",
                    "--program",
                    str(PROGRAM),
                    "--audit-dir",
                    str(AUDITS),
                    "--registry",
                    str(REGISTRY),
                    "--selection",
                    str(ROOT / "fixtures/benchmark/selection-result.json"),
                    "--scope",
                    str(scope),
                    "--output",
                    str(output),
                ],
                clock=lambda: NOW,
            )
            == 0
        )

    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    status = ProjectStatus.from_json(outputs[0].read_text(encoding="utf-8"))
    assert status.payload.qualified_count == 0
    assert all(candidate.readiness == "registered" for candidate in status.payload.candidates)
    public_status = outputs[0].read_text(encoding="utf-8")
    for restricted in (
        "patient_id",
        "predicted_medications",
        "/Users/",
        "/private/",
        "BEGIN PRIVATE KEY",
    ):
        assert restricted not in public_status
    assert capsys.readouterr().out.splitlines() == [status.snapshot_sha256] * 2


def test_explicit_stale_review_exits_two_without_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scope = tmp_path / "scope.json"
    output = tmp_path / "status.json"
    _scope(scope)

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "status-publish",
                "--program",
                str(PROGRAM),
                "--audit-dir",
                str(AUDITS),
                "--registry",
                str(REGISTRY),
                "--selection",
                str(ROOT / "fixtures/benchmark/selection-result.json"),
                "--scope",
                str(scope),
                "--human-review",
                str(ROOT / "fixtures/benchmark/human-review.json"),
                "--output",
                str(output),
            ],
            clock=lambda: NOW,
        )

    assert raised.value.code == 2
    assert "stale" in capsys.readouterr().err
    assert not output.exists()


def test_action_blocked_writes_decision_and_returns_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot = ProjectStatus.from_json(
        (ROOT / "fixtures/status/discovery-eligible.json").read_text(encoding="utf-8")
    )
    intent = tmp_path / "intent.json"
    intent.write_text(
        json.dumps(
            {
                "action_id": "begin_discovery",
                "authorization_sha256": "a" * 64,
                "kind": "action_intent",
                "preflight_sha256": "b" * 64,
                "request_id": "cli-request-001",
                "schema_version": 1,
                "scope_sha256": "d" * 64,
                "snapshot_sha256": snapshot.snapshot_sha256,
                "target_id": "319-wild",
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "decision.json"

    assert (
        main(
            [
                "action-evaluate",
                "--intent",
                str(intent),
                "--status",
                str(ROOT / "fixtures/status/discovery-eligible.json"),
                "--output",
                str(output),
            ],
            clock=lambda: NOW,
        )
        == 2
    )
    decision = json.loads(output.read_text(encoding="utf-8"))
    assert decision["reason_code"] == "authority_bundle_missing"
    assert capsys.readouterr().out.strip() == "authority_bundle_missing"


def test_help_has_no_remote_execution_input_surface(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["harness", "--help"])

    assert raised.value.code == 0
    help_text = capsys.readouterr().out.lower()
    for forbidden in ("--host", "--command", "--argv", "--env", "--ssh", "--remote-path"):
        assert forbidden not in help_text


def test_io_error_is_public_safe_and_does_not_echo_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "private-secret-program.toml"

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "audit-validate",
                "--program",
                str(private_path),
                "--audit-dir",
                str(AUDITS),
            ]
        )

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "input/output operation failed" in error
    assert str(private_path) not in error
