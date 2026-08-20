from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from medrec_research.cli import main
from medrec_research.reproduction_contract import (
    DecisionPacket,
    EvidenceConclusion,
    H1Approval,
    H2Decision,
)

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "fixtures"


def _fixture(relative_path: str) -> Path:
    return FIXTURES / relative_path


def _write_h2_fixture(tmp_path: Path) -> Path:
    payload = json.loads(_fixture("benchmark/h2-decisions.json").read_text(encoding="utf-8"))[
        "accepted"
    ]
    path = tmp_path / "h2-accepted.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_rejected_packet(tmp_path: Path) -> Path:
    packet = DecisionPacket.from_json(
        _fixture("benchmark/decision-packet-accepted.json").read_text(encoding="utf-8")
    )
    rejected = replace(packet, conclusion=EvidenceConclusion.REJECTED, packet_sha256="")
    path = tmp_path / "decision-packet-rejected.json"
    path.write_text(rejected.to_json(), encoding="utf-8")
    return path


def _validate_reproduction_args(
    output: Path,
    *,
    packet: Path,
    h1: Path | None = None,
    h2: Path | None = None,
) -> list[str]:
    arguments = [
        "validate-reproduction",
        "--contract",
        str(_fixture("benchmark/safedrug-batch-h1.json")),
        "--packet",
        str(packet),
        "--output",
        str(output),
    ]
    if h1 is not None:
        arguments.extend(("--h1", str(h1)))
    if h2 is not None:
        arguments.extend(("--h2", str(h2)))
    return arguments


def test_validate_reproduction_accepts_current_h1_h2_and_is_public_safe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "validated.json"
    h2 = _write_h2_fixture(tmp_path)

    assert (
        main(
            _validate_reproduction_args(
                output,
                packet=_fixture("benchmark/decision-packet-accepted.json"),
                h1=_fixture("benchmark/h1-approval.json"),
                h2=h2,
            )
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["kind"] == "reproduction_validation"
    assert payload["h1"]["decision"] == "accepted"
    assert payload["h2"]["action"] == "go"
    assert payload["packet"]["conclusion"] == "accepted"
    assert "/private/" not in output.read_text(encoding="utf-8")
    assert "password" not in output.read_text(encoding="utf-8").lower()
    assert capsys.readouterr().out.strip() == payload["packet"]["packet_sha256"]


@pytest.mark.parametrize(
    ("packet_name", "expected_conclusion"),
    [
        ("decision-packet-accepted.json", "accepted"),
        ("decision-packet-inconclusive.json", "inconclusive"),
    ],
)
def test_validate_reproduction_preserves_independent_packet_conclusions(
    tmp_path: Path,
    packet_name: str,
    expected_conclusion: str,
) -> None:
    output = tmp_path / f"{packet_name}.validated.json"

    assert (
        main(
            _validate_reproduction_args(
                output,
                packet=_fixture(f"benchmark/{packet_name}"),
            )
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["packet"]["conclusion"] == (
        expected_conclusion
    )


def test_validate_reproduction_accepts_rejected_packet_without_upgrading_it(
    tmp_path: Path,
) -> None:
    output = tmp_path / "rejected.json"
    packet = _write_rejected_packet(tmp_path)

    assert main(_validate_reproduction_args(output, packet=packet)) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["packet"]["conclusion"] == "rejected"


def test_validate_reproduction_rejects_stale_h1_and_h2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contract_path = _fixture("benchmark/safedrug-batch-h1.json")
    packet_path = _fixture("benchmark/decision-packet-accepted.json")
    h2 = H2Decision.from_json(_write_h2_fixture(tmp_path).read_text(encoding="utf-8"))

    stale_h1 = replace(
        H1Approval.from_json(_fixture("benchmark/h1-approval.json").read_text(encoding="utf-8")),
        contract_sha256="c" * 64,
        approval_sha256="",
    )
    stale_h1_path = tmp_path / "h1-stale.json"
    stale_h1_path.write_text(stale_h1.to_json(), encoding="utf-8")

    with pytest.raises(SystemExit) as h1_error:
        main(
            _validate_reproduction_args(
                tmp_path / "h1-output.json",
                packet=packet_path,
                h1=stale_h1_path,
            )
        )
    assert h1_error.value.code == 2
    assert "H1 approval is stale" in capsys.readouterr().err

    stale_h2 = replace(h2, contract_sha256="d" * 64, decision_sha256="")
    stale_h2_path = tmp_path / "h2-stale.json"
    stale_h2_path.write_text(stale_h2.to_json(), encoding="utf-8")

    with pytest.raises(SystemExit) as h2_error:
        main(
            _validate_reproduction_args(
                tmp_path / "h2-output.json",
                packet=packet_path,
                h2=stale_h2_path,
            )
        )
    assert h2_error.value.code == 2
    assert "H2 decision is stale" in capsys.readouterr().err
    assert contract_path.exists()


def test_validate_research_loop_rejects_scientifically_stale_snapshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "loop.json"
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "validate-research-loop",
                "--status",
                str(_fixture("status/research-loop-stale.json")),
                "--output",
                str(output),
            ]
        )

    assert raised.value.code == 2
    assert "research loop status is stale" in capsys.readouterr().err


def test_validate_research_loop_accepts_current_snapshot(tmp_path: Path) -> None:
    output = tmp_path / "loop.json"
    assert (
        main(
            [
                "validate-research-loop",
                "--status",
                str(_fixture("status/research-loop-mixed.json")),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["stale"] is False
