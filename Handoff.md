# Handoff

Updated: 2026-09-17.

```text
Current phase: CREDIBLE REFERENCE SETUP
Paper Experiment Contract: v1.0 CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`
- `research/memory/current-research-state.md`

The new contract supersedes Reproduction/Comparison Mode as the active paper-facing experiment abstraction. Historical Unified Research Protocol and baseline registry records remain provenance only.

Still valid development evidence:

- MICA DrugQuery vs SharedPool single-seed Train/Dev gains on MIMIC-III and MIMIC-IV;
- fixed-131/generalized-MICA equivalence;
- frozen MIMIC-IV native-173 materialization;
- MIMIC-IV common-131 harmonized materialization;
- earlier qualified five-model MIMIC-III rows as historical references only.

Do not use the temporary former Stage -1G ARMR/MoleRec/GAMENet/RETAIN outputs for method ranking. Do not resume those runners.

Current bounded audits:

1. prediction-time semantics for current diagnosis/procedure inputs;
2. historical evaluation feedback/Test exposure and known/unknown cross-population overlap;
3. native-173 feasibility for scientifically relevant baselines.

These are scoped dependencies, not a global no-training gate. MIMIC-III SharedPool/DrugQuery three-seed stability may start once the MIMIC-III task/evaluator/selection profile is fixed. A baseline recovery may start once its Method Card and source/reference conditions are frozen. Structured-set training additionally requires a clear closest-work computational distinction.

Do not access MIMIC-IV Test, treat a historically exposed benchmark as independent confirmation, silently replace failed final seeds, or add selection opportunities after observing final-run trajectories.

One next action: execute the bounded audits needed for the next concrete experiments, then launch the smallest credible parallel set rather than a broad benchmark sweep.
