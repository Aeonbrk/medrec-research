# Competitive baseline calibration — historical execution record

Former internal name: `Stage -1G — Competitive substrate calibration`.

Status: `TERMINATED_AFTER_INDEPENDENT_FIDELITY_REVIEW`

This directory preserves the historical design, qualification attempt, common-131 benchmark linkage, temporary runners, cleanup records, and fidelity review for the competitive-baseline calibration attempt. It is not the current execution contract.

## Current authority

The independent post-cleanup review is recorded in:

- [`fidelity-review.json`](fidelity-review.json)
- [`cleanup-invalidation.json`](cleanup-invalidation.json)
- [`../../memory/decisions/2026-09-17-competitive-baseline-fidelity-review.md`](../../memory/decisions/2026-09-17-competitive-baseline-fidelity-review.md)

The frozen historical [`protocol.md`](protocol.md) and [`qualification.json`](qualification.json) are preserved for provenance. Their external-baseline admission is superseded for execution and must not be resumed without a new paper-oriented experimental standard.

## What remains valid

- G0 fixed-131/generalized-MICA exact-equivalence evidence.
- MIMIC-IV common-131 materialization and semantic audit.
- MICA common-131 SharedPool/DrugQuery development aggregates.
- The fact that the temporary external runs occurred under the recorded code/configuration.
- Cleanup accounting and stop provenance.

## What is invalidated for scientific comparison

All temporary external results produced by the former Stage -1G runner family are diagnostic only, including completed MIMIC-III outputs and stopped MIMIC-IV outputs.

The fidelity audit found:

- ARMR checkpoint/model-selection semantics diverged from the pinned official source.
- MoleRec changed the official per-visit optimizer-update semantics into shuffled batch-32 training through a custom batched forward path.
- GAMENet used a project-side batched `ProtocolGAMENet` rather than the unchanged official model/training path.
- RETAIN used a project-side `ProtocolRETAIN` path and did not establish published-method identity for this calibration lane.

Therefore these outputs cannot support statements that MICA outperforms the corresponding published methods. Dependent bootstrap intervals do not repair the upstream identity problem.

## Common-131 boundary

`research/benchmarks/mimiciv-medrec-common131/` remains a preserved harmonized Train/Dev development surface. It is not an official universal MIMIC-IV benchmark. The final paper role of common-131 versus native-173 is intentionally left for the next experimental-standard design.

## No terminal substrate verdict

No `MICA_SUBSTRATE_*` verdict is issued. The failed element was the external-comparison execution identity, not the already established MICA DrugQuery-vs-SharedPool mechanism replication.

No new experiment should be launched from the historical protocol. The next research task is to define a paper-oriented experimental standard and then decide whether competitive calibration, architecture development, or both should be rerun under that standard.
