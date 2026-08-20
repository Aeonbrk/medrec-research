from __future__ import annotations

from medrec_research.team_spawner import TeamSpawner


def test_team_spawner_all_teams():
    spawner = TeamSpawner()

    # 1. Baseline Team
    b_team = spawner.spawn_baseline_team("safedrug")
    assert len(b_team.members) == 3
    assert "Team spawned" in b_team.describe_team()
    b_res = b_team.execute(dry_run=True)
    assert b_res["baseline_id"] == "safedrug"
    assert "metrics" in b_res

    # 2. Research Team
    r_team = spawner.spawn_research_team(b_res)
    assert len(r_team.members) == 4
    hypotheses = r_team.execute()
    assert len(hypotheses) >= 3
    assert hypotheses[0]["id"] == "H001"

    # 3. Review Team
    rev_team = spawner.spawn_review_team("H001")
    assert len(rev_team.members) == 3
    rev_res = rev_team.review_hypothesis(hypotheses[0])
    assert "verdict" in rev_res
    assert rev_res["hypothesis_id"] == "H001"

    # 4. Feature Team
    f_team = spawner.spawn_feature_team("H001", hypotheses[0])
    assert len(f_team.members) == 3
    contract, exp_yaml = f_team.execute()
    assert contract["contract_id"] == "H001-contract"
    assert "HierarchicalSubstructureSafeDrug" in exp_yaml

    # 5. Execution Team
    e_team = spawner.spawn_execution_team("H001-substructure", {})
    assert len(e_team.members) == 2
    e_res = e_team.execute(dry_run=True)
    assert e_res["status"] == "dry_run_success"
