"""Start a fresh, source-tree production harness for browser tests."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from medrec_research.action_gate import ActionAuthorization, AuthorityBundle, RemotePreflight
from medrec_research.aris_bridge import ArisRevisionRecord
from medrec_research.harness import create_harness_server
from medrec_research.project_status import ProjectStatus
from medrec_research.reproduction_contract import DecisionPacket
from medrec_research.research_session import RemoteSessionPreflight, ResearchSession


def main() -> None:
    root = Path(__file__).parents[2]
    fixture = ProjectStatus.from_json(
        (root / "fixtures/status/discovery-eligible.json").read_text(encoding="utf-8")
    )
    now = datetime.now(UTC).replace(microsecond=0)
    current = ProjectStatus.create(
        project_id=fixture.project_id,
        authorities=fixture.authorities,
        blockers=fixture.blockers,
        payload=fixture.payload,
        clock=lambda: now,
        freshness=timedelta(hours=1),
    )
    with TemporaryDirectory(prefix="medrec-production-e2e-") as directory:
        runtime = Path(directory)
        status_path = runtime / "status.json"
        bundle_path = runtime / "authority-bundle.json"
        status_path.write_text(current.to_json(indent=2), encoding="utf-8")
        shared = {
            "project_id": current.project_id,
            "target_id": "319-wild",
            "action_id": current.next_action.action_id,
            "snapshot_sha256": current.snapshot_sha256,
            "scope_sha256": next(
                item.sha256 for item in current.authorities if item.authority_id == "scope"
            ),
            "authorities": current.authorities,
            "issued_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
        }
        authorization = ActionAuthorization.create(
            issuer_id="research-steward",
            source_id="steward-approval",
            **shared,
        )
        preflight = RemotePreflight.create(
            issuer_id="aris",
            source_id="remote-preflight",
            remote_revision="e" * 40,
            **shared,
        )
        bundle = AuthorityBundle(
            current_authorities=current.authorities,
            current_remote_profile_id="319-wild",
            current_remote_revision="e" * 40,
            authorization_issuer_id="research-steward",
            authorization_source_id="steward-approval",
            preflight_issuer_id="aris",
            preflight_source_id="remote-preflight",
            authorizations=(authorization,),
            preflights=(preflight,),
        )
        bundle_path.write_text(bundle.to_json(indent=2), encoding="utf-8")
        session = ResearchSession(runtime, clock=lambda: datetime.now(UTC))
        session.authority_bundle_path = bundle_path
        session.preflight = RemoteSessionPreflight(
            observed_at=now.isoformat().replace("+00:00", "Z"),
            reachable=False,
            fallback_used=False,
            identity_ok=False,
            checkout_exists=False,
            checkout_clean=False,
            local_revision=None,
            remote_revision=None,
            revision_matches=False,
            data_root_ready=False,
            conda_available=False,
            environment_verified=False,
            gpu_count=0,
            gpu_available=0,
            disk_free_gib=0,
            blockers=("remote-execution-not-authorized",),
        )
        # The browser harness uses a public-safe synthetic revision authority. It is
        # test setup, never a production fallback or remote execution credential.
        session.aris_revision = ArisRevisionRecord(
            observed_at=now.isoformat().replace("+00:00", "Z"),
            candidate_revision="e" * 40,
            active_revision="e" * 40,
            last_known_good_revision="e" * 40,
            candidate_valid=True,
            fallback_used=False,
            blockers=(),
            manifest_sha256="f" * 64,
        )
        session.runtime.mkdir(parents=True)
        session.packet_dir.mkdir()
        session.h2_dir.mkdir()
        session.action_request_dir.mkdir()
        session.execution_dir.mkdir()
        session.contract_path.parent.mkdir(parents=True, exist_ok=True)
        session.contract_path.write_bytes(
            (root / "fixtures/benchmark/safedrug-batch-h1.json").read_bytes()
        )
        base_packet = DecisionPacket.from_json(
            (root / "fixtures/benchmark/decision-packet-accepted.json").read_text(encoding="utf-8")
        )
        for lane_id in (
            "gamenet",
            "safedrug",
            "molerec",
            "retain",
            "leap-safedrug",
        ):
            attempt = replace(
                base_packet.attempts[0],
                attempt_id=f"{lane_id}-attempt",
                lane_id=lane_id,
                attempt_sha256="",
            )
            packet = replace(
                base_packet,
                packet_id=f"{lane_id}-packet",
                lane_id=lane_id,
                attempts=(attempt,),
                attempted_lane_ids=(lane_id,),
                completed_lane_ids=(lane_id,),
                packet_sha256="",
            )
            (session.packet_dir / f"{lane_id}.json").write_text(
                packet.to_json(indent=2), encoding="utf-8"
            )
        session.create_h1(
            {
                "kind": "h1_input",
                "schema_version": 1,
                "owner": "production-e2e",
                "rationale": "public-safe synthetic production harness",
            }
        )
        server = create_harness_server(
            status_path=status_path,
            expected_authorities=current.authorities,
            clock=lambda: datetime.now(UTC),
            port=int(os.environ.get("MEDREC_HARNESS_PORT", "0")),
            actions_enabled=True,
            authority_bundle_path=bundle_path,
            research_loop_path=session.loop_path,
            hitl_session=session,
        )
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
