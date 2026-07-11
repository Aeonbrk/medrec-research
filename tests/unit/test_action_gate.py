from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from medrec_research.action_gate import (
    ActionAuthorization,
    ActionIntent,
    AuthorityBundle,
    RemotePreflight,
    evaluate_action,
)
from medrec_research.errors import ProtocolValidationError
from medrec_research.project_status import AuthorityDigest, ProjectStatus

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 7, 11, 1, 3, tzinfo=UTC)
TARGET_ID = "319-wild"
REMOTE_REVISION = "e" * 40


def _snapshot() -> ProjectStatus:
    return ProjectStatus.from_json(
        (ROOT / "fixtures/status/discovery-eligible.json").read_text(encoding="utf-8")
    )


def _authorization(snapshot: ProjectStatus, **changes: object) -> ActionAuthorization:
    values: dict[str, object] = {
        "issuer_id": "research-steward",
        "source_id": "steward-approval",
        "project_id": snapshot.project_id,
        "target_id": TARGET_ID,
        "action_id": "begin_discovery",
        "snapshot_sha256": snapshot.snapshot_sha256,
        "scope_sha256": "d" * 64,
        "authorities": snapshot.authorities,
        "issued_at": "2026-07-11T01:01:00Z",
        "expires_at": "2026-07-11T01:05:00Z",
    }
    values.update(changes)
    return ActionAuthorization.create(**values)


def _preflight(snapshot: ProjectStatus, **changes: object) -> RemotePreflight:
    values: dict[str, object] = {
        "issuer_id": "aris",
        "source_id": "remote-preflight",
        "project_id": snapshot.project_id,
        "target_id": TARGET_ID,
        "action_id": "begin_discovery",
        "snapshot_sha256": snapshot.snapshot_sha256,
        "scope_sha256": "d" * 64,
        "authorities": snapshot.authorities,
        "remote_revision": REMOTE_REVISION,
        "issued_at": "2026-07-11T01:01:00Z",
        "expires_at": "2026-07-11T01:05:00Z",
    }
    values.update(changes)
    return RemotePreflight.create(**values)


def _valid_inputs() -> tuple[ProjectStatus, ActionIntent, AuthorityBundle]:
    snapshot = _snapshot()
    authorization = _authorization(snapshot)
    preflight = _preflight(snapshot)
    intent = ActionIntent(
        request_id="request-001",
        action_id="begin_discovery",
        target_id=TARGET_ID,
        snapshot_sha256=snapshot.snapshot_sha256,
        scope_sha256="d" * 64,
        authorization_sha256=authorization.authorization_sha256,
        preflight_sha256=preflight.preflight_sha256,
    )
    bundle = AuthorityBundle(
        current_authorities=snapshot.authorities,
        current_remote_profile_id=TARGET_ID,
        current_remote_revision=REMOTE_REVISION,
        authorization_issuer_id="research-steward",
        authorization_source_id="steward-approval",
        preflight_issuer_id="aris",
        preflight_source_id="remote-preflight",
        authorizations=(authorization,),
        preflights=(preflight,),
    )
    return snapshot, intent, bundle


def test_valid_request_is_deterministic_and_matches_fixture() -> None:
    snapshot, intent, bundle = _valid_inputs()
    snapshot_before = snapshot.to_dict()
    bundle_before = bundle

    first = evaluate_action(intent=intent, snapshot=snapshot, authority_bundle=bundle, now=NOW)
    second = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=bundle,
        now=NOW + timedelta(seconds=30),
    )

    assert first == second
    assert first.status == "allowed"
    assert first.reason_code == "action_request_created"
    assert first.request is not None
    assert first.request.to_dict() == second.request.to_dict()
    assert snapshot.to_dict() == snapshot_before
    assert bundle == bundle_before
    expected = json.loads(
        (ROOT / "fixtures/status/action-allowed.json").read_text(encoding="utf-8")
    )
    assert first.to_dict() == expected


def test_missing_bundle_fails_closed_and_matches_fixture() -> None:
    snapshot, intent, _ = _valid_inputs()

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=None,
        now=NOW,
    )

    assert decision.reason_code == "authority_bundle_missing"
    expected = json.loads(
        (ROOT / "fixtures/status/action-blocked.json").read_text(encoding="utf-8")
    )
    assert decision.to_dict() == expected


@pytest.mark.parametrize("field", ("command", "argv", "path", "host", "env", "payload"))
def test_wire_contracts_reject_unknown_execution_fields(field: str) -> None:
    _, intent, bundle = _valid_inputs()
    records = (
        (ActionIntent.from_dict, intent.to_dict()),
        (ActionAuthorization.from_dict, bundle.authorizations[0].to_dict()),
        (RemotePreflight.from_dict, bundle.preflights[0].to_dict()),
    )

    for parser, payload in records:
        with pytest.raises(ProtocolValidationError, match="unknown field"):
            parser({**payload, field: "forbidden"})


def test_snapshot_authority_drift_fails_closed() -> None:
    snapshot, intent, bundle = _valid_inputs()
    changed = tuple(
        AuthorityDigest(item.authority_id, "f" * 64) if item.authority_id == "registry" else item
        for item in bundle.current_authorities
    )

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=replace(bundle, current_authorities=changed),
        now=NOW,
    )

    assert decision.reason_code == "authority_drift"


def test_expired_snapshot_fails_closed() -> None:
    snapshot, intent, bundle = _valid_inputs()

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=bundle,
        now=datetime(2026, 7, 11, 1, 8, tzinfo=UTC),
    )

    assert decision.reason_code == "snapshot_expired"


@pytest.mark.parametrize(
    ("member", "reason_code"),
    (("authorizations", "authorization_duplicate"), ("preflights", "preflight_duplicate")),
)
def test_duplicate_matching_authority_records_fail_closed(member: str, reason_code: str) -> None:
    snapshot, intent, bundle = _valid_inputs()
    duplicated = getattr(bundle, member) * 2

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=replace(bundle, **{member: duplicated}),
        now=NOW,
    )

    assert decision.reason_code == reason_code


@pytest.mark.parametrize(
    ("member", "replacement", "reason_code"),
    (
        ("authorizations", {"issuer_id": "attacker"}, "authorization_untrusted"),
        ("authorizations", {"expires_at": "2026-07-11T01:03:00Z"}, "authorization_not_current"),
        ("authorizations", {"project_id": "other-project"}, "authorization_mismatch"),
        ("preflights", {"source_id": "ambient-state"}, "preflight_untrusted"),
        ("preflights", {"issued_at": "2026-07-11T01:04:00Z"}, "preflight_not_current"),
        ("preflights", {"action_id": "request_reproduction"}, "preflight_mismatch"),
    ),
)
def test_authority_record_failures_are_stable(
    member: str, replacement: dict[str, object], reason_code: str
) -> None:
    snapshot, intent, bundle = _valid_inputs()
    record = (
        _authorization(snapshot, **replacement)
        if member == "authorizations"
        else _preflight(snapshot, **replacement)
    )
    intent = replace(
        intent,
        **{
            "authorization_sha256" if member == "authorizations" else "preflight_sha256": (
                record.authorization_sha256
                if member == "authorizations"
                else record.preflight_sha256
            )
        },
    )

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=replace(bundle, **{member: (record,)}),
        now=NOW,
    )

    assert decision.reason_code == reason_code


def test_remote_revision_drift_fails_closed() -> None:
    snapshot, intent, bundle = _valid_inputs()

    decision = evaluate_action(
        intent=intent,
        snapshot=snapshot,
        authority_bundle=replace(bundle, current_remote_revision="f" * 40),
        now=NOW,
    )

    assert decision.reason_code == "remote_target_drift"


def test_unadvertised_action_and_wrong_target_fail_closed() -> None:
    snapshot, intent, bundle = _valid_inputs()

    assert (
        evaluate_action(
            intent=replace(intent, action_id="request_reproduction"),
            snapshot=snapshot,
            authority_bundle=bundle,
            now=NOW,
        ).reason_code
        == "action_not_permitted"
    )
    assert (
        evaluate_action(
            intent=replace(intent, target_id="other-profile"),
            snapshot=snapshot,
            authority_bundle=bundle,
            now=NOW,
        ).reason_code
        == "remote_target_drift"
    )


@pytest.mark.parametrize("revision", ("HEAD", "main", "E" * 40, "e" * 39, "e" * 41))
def test_remote_revision_must_be_immutable(revision: str) -> None:
    snapshot = _snapshot()

    with pytest.raises(ProtocolValidationError, match="immutable"):
        _preflight(snapshot, remote_revision=revision)


def test_content_digest_tampering_is_rejected() -> None:
    _, _, bundle = _valid_inputs()
    authorization = bundle.authorizations[0].to_dict()
    preflight = bundle.preflights[0].to_dict()

    with pytest.raises(ProtocolValidationError, match="does not match"):
        ActionAuthorization.from_dict({**authorization, "project_id": "other-project"})
    with pytest.raises(ProtocolValidationError, match="does not match"):
        RemotePreflight.from_dict({**preflight, "remote_revision": "f" * 40})


def test_authority_bundle_strict_wire_roundtrip(tmp_path: Path) -> None:
    _, _, bundle = _valid_inputs()
    path = tmp_path / "authority-bundle.json"
    path.write_text(bundle.to_json(indent=2), encoding="utf-8")

    assert AuthorityBundle.from_dict(bundle.to_dict()) == bundle
    assert AuthorityBundle.from_json(bundle.to_json()) == bundle
    assert AuthorityBundle.load(path) == bundle

    with pytest.raises(ProtocolValidationError, match="unknown field"):
        AuthorityBundle.from_dict({**bundle.to_dict(), "command": "forbidden"})
