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

Current session evidence:

- The frozen `mimic-iii-canonical-131-paper-dev-v1` profile and MIV common-131 run-critical audit are committed. MICA SharedPool/DrugQuery pairs for seeds `20260917` and `20260918` completed under that profile; the paired decision is recorded in `research/memory/decisions/2026-09-17-mica-paired-stability-update.md`.
- A source-native MoleRec lane is still running remotely under the pinned MoleRec source and current clean harness revision. It has no terminal result yet; monitor its detached run and do not promote partial values.
- The first MoleRec launch failed before creating a run root because the generic CLI omitted a preprocessing revision. The replacement lane explicitly binds `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`; preserve both identities in the review packet.
- ARMR remains conditional and was not launched because the pinned runtime lacks the official `einops` dependency. SSPNet remains `NOVELTY_UNRESOLVED` / `SSPNET_EXECUTION_UNRESOLVED`; expensive structured training is blocked.
- MIV paper-lineage wording remains asynchronous. MIMIC-IV Test stays sealed; no MIV sentinel or structured Full/control run is authorized by this evidence.

MICA stability is not an architecture gate. Default next evidence is two new paired MIMIC-III seeds per arm under the frozen profile; add the third pair when MICA remains central, the first pairs disagree, or otherwise-ready GPU capacity makes completion cheapest. If MICA runs are short and no higher-value task is ready, six-way parallel completion is acceptable.

A structured-set prototype may begin before baseline recovery finishes once its legal I/O contract, closest-work difference, minimum model, and strongest matched independent-label control are clear. Do not protect the MICA narrative by forcing the new model to use MICA.

If the first valid MIII full/control result plus an additional paired check show a signal worth pursuing, move early to MIV harmonized131 and native173 sentinel pairs rather than waiting for complete MIII three-seed evidence. The two MIV surfaces are target-space views of the same dataset, not independent replications.

Management targets: architecture route decision by 2026-10-05; normal Paper Candidate target 2026-10-09 to 2026-10-13; hard stop for this architecture-search cycle 2026-10-16. Dates do not override evidence.

Do not access MIMIC-IV Test, resume invalidated former Stage -1G runners, change benchmark roles because one surface is easier to win, or extend a weak architecture by unrelated retrieval/DDI/refinement patches.
