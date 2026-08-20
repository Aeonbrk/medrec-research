from __future__ import annotations

from pathlib import Path

from medrec_research.research_orchestrator import ResearchOrchestrator


def test_research_orchestrator_phases(tmp_path: Path):
    orchestrator = ResearchOrchestrator(root=tmp_path, interactive=False)

    # Phase 1: Establish baseline (dry-run)
    b_res = orchestrator.establish_baseline("safedrug", dry_run=True)
    assert b_res["baseline_id"] == "safedrug"

    # Phase 1: Establish baseline (record execution)
    b_res_full = orchestrator.establish_baseline("safedrug", dry_run=False)
    assert b_res_full["baseline_id"] == "safedrug"
    assert (tmp_path / "research" / "baselines" / "safedrug" / "result.json").exists()
    assert (tmp_path / "research" / "baselines" / "safedrug" / "analysis.md").exists()

    # Phase 2: Discover ideas
    hypotheses = orchestrator.discover_ideas("safedrug")
    assert len(hypotheses) >= 3
    assert (
        tmp_path / "research" / "hypotheses" / f"{hypotheses[0]['id']}-{hypotheses[0]['slug']}.md"
    ).exists()

    # Phase 3: Review idea
    review_report = orchestrator.review_idea("H001")
    assert review_report["verdict"] in ("Go", "Revise", "Kill")
    assert (tmp_path / "research" / "reviews" / "H001-review.md").exists()

    # Phase 4: Design experiment & contract
    contract, exp_yaml = orchestrator.design_experiment("H001")
    assert contract["contract_id"] == "H001-contract"
    assert "experiment_id" in exp_yaml
    assert (tmp_path / "research" / "contracts" / "H001-contract.json").exists()
    assert (tmp_path / "experiments" / "H001-exp.yaml").exists()

    # Phase 5: Run experiment (dry-run)
    exp_res = orchestrator.run_experiment("H001-substructure", dry_run=True)
    assert exp_res["status"] == "dry_run_success"

    # Phase 6: Analyze evidence
    ev_report = orchestrator.analyze_evidence("H001-substructure")
    assert (tmp_path / "research" / "evidence" / "H001-evidence.md").exists()
    assert "metrics" in ev_report


def test_research_orchestrator_loop_dry_run(tmp_path: Path):
    orchestrator = ResearchOrchestrator(root=tmp_path, interactive=False)
    # Full loop in dry run mode should run smoothly without error
    orchestrator.run_loop("safedrug", dry_run=True)
