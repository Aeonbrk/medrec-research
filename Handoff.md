# Handoff

Updated: 2026-09-17.

```text
Verified revision before independent review: e99e06ce3022c499525b286c2ee5781cf755e478
Current work: COMPETITIVE BASELINE FIDELITY REVIEW — COMPLETE
Historical execution record: former Stage -1G competitive calibration
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
Held-out/Test use: untouched / not authorized
```

Independent review verdict: the cleanup itself is accepted, but the former Stage -1G external-run qualification is not. The temporary ARMR, MoleRec, GAMENet, and RETAIN runners do not establish published-method fidelity, so their MIMIC-III/MIMIC-IV outputs and dependent bootstrap comparisons are diagnostic only. Do not resume those runners.

Still valid for their stated development scope:

- MICA DrugQuery vs SharedPool cross-dataset Train/Dev mechanism replication;
- fixed-131/generalized-MICA exact-equivalence evidence;
- frozen MIMIC-IV native-173 benchmark;
- harmonized MIMIC-IV common-131 materialization and semantic audit;
- MICA common-131 aggregates;
- the earlier separately qualified five-model MIMIC-III baseline evidence as historical reference, not automatically as final-paper rows.

Current review authority:

- `research/prototypes/mica-competitive-substrate-calibration/fidelity-review.json`
- `research/memory/decisions/2026-09-17-competitive-baseline-fidelity-review.md`

The old `protocol.md` and `qualification.json` in that prototype are preserved as historical pre-audit records and are superseded for execution.

Next action: synthesize the independent experimental-standard review (including Astra's advice) and define a simple paper-oriented experiment standard before any new GPU run.

Do not read Test, resume the invalidated external runners, start RSM, create Idea 009, or treat temporary baseline rankings as scientific superiority evidence before that standard is frozen.
