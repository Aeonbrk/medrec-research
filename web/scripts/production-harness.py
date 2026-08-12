"""Start a fresh, source-tree production harness for browser tests."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from medrec_research.action_gate import ActionAuthorization, AuthorityBundle, RemotePreflight
from medrec_research.harness import create_harness_server
from medrec_research.project_status import ProjectStatus


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
        status_path = Path(directory) / "status.json"
        bundle_path = Path(directory) / "authority-bundle.json"
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
        server = create_harness_server(
            status_path=status_path,
            expected_authorities=current.authorities,
            clock=lambda: datetime.now(UTC),
            port=int(os.environ.get("MEDREC_HARNESS_PORT", "0")),
            actions_enabled=True,
            authority_bundle_path=bundle_path,
            research_loop_path=root / "fixtures/status/research-loop-mixed.json",
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
