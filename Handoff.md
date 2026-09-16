# Handoff

Updated: 2026-09-17.

```text
Current phase: CREDIBLE REFERENCE SETUP + ARCHITECTURE PREPARATION
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-17-evidence-first-execution-sequencing.md`

Current routing is dependency-driven, not serial. Do not wait for all baselines or all MICA seeds before architecture work. Make the evidence most capable of killing or redirecting the paper arrive early.

Immediate work:

1. freeze the minimum MIMIC-III task/evaluator/selection profile and legal information budget;
2. start source-backed MoleRec recovery; use ARMR as the default second lane, but promote SSPNet if structured-set prediction becomes the active hypothesis and a trustworthy path is available;
3. time-box the structured/set closest-work computation audit; expensive structured training stays blocked until the computational distinction and minimal matched control are clear;
4. audit harmonized/common-131 run-critical identity/alignment now; paper-lineage wording can finish asynchronously;
5. continue prediction-time and historical Test-feedback audits only where they change an upcoming experiment or claim.

MICA stability is not an architecture gate. Default next evidence is two new paired MIMIC-III seeds per arm under the frozen profile; add the third pair when MICA remains central, the first pairs disagree, or otherwise-ready GPU capacity makes completion cheapest. If MICA runs are short and no higher-value task is ready, six-way parallel completion is acceptable.

A structured-set prototype may begin before baseline recovery finishes once its legal I/O contract, closest-work difference, minimum model, and strongest matched independent-label control are clear. Do not protect the MICA narrative by forcing the new model to use MICA.

If the first valid MIII full/control result plus an additional paired check show a signal worth pursuing, move early to MIV harmonized131 and native173 sentinel pairs rather than waiting for complete MIII three-seed evidence. The two MIV surfaces are target-space views of the same dataset, not independent replications.

Management targets: architecture route decision by 2026-10-05; normal Paper Candidate target 2026-10-09 to 2026-10-13; hard stop for this architecture-search cycle 2026-10-16. Dates do not override evidence.

Do not access MIMIC-IV Test, resume invalidated former Stage -1G runners, change benchmark roles because one surface is easier to win, or extend a weak architecture by unrelated retrieval/DDI/refinement patches.
