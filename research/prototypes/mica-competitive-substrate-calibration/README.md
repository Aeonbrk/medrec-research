# Stage -1G — Competitive substrate calibration

Status: `DESIGNED_NOT_EXECUTED`

Stage -1F established that medication-specific evidence selection (`DrugQuery`) improves over matched `SharedPool` on both frozen Train/Dev surfaces. Stage -1G asks a different question:

> Is MICA-Core competitive enough against strong, faithful external methods on both MIMIC-III and MIMIC-IV to justify building the next architecture on top of it?

This is a pre-Idea, pre-Gate calibration stage. It does not create a paper claim, open Test, implement RSM, or perform final benchmark confirmation.

The frozen execution contract is in [`protocol.md`](protocol.md).

## Why this stage exists

The current evidence has strong internal mechanism attribution but uneven external coverage. MIMIC-III has several high-quality reproduction/reference surfaces; MIMIC-IV currently has only the matched SharedPool/DrugQuery pair under the frozen project protocol. That is sufficient to establish cross-dataset mechanism replication, but not enough to judge whether MICA is a competitive paper substrate.

The design follows the experimental logic used by strong medication-recommendation papers rather than forcing every model into one optimizer recipe:

- same task semantics, data roles, information budget, and evaluator;
- faithful method-specific training and model logic;
- strong baselines spanning recent and established families;
- accuracy, safety, prescribing-size, calibration, and efficiency reporting;
- dual-dataset evidence;
- final multi-seed/Test/statistical confirmation deferred until a method survives.

Primary-source reference points include MoleRec (WWW 2023), ARMR and SSPNet (IJCAI 2025), and HypeMed (TOIS 2026).

## Planned phases

1. `G0_EQUIVALENCE`: no-training fixed-131 vs generalized-MICA equivalence audit.
2. `G1_QUALIFICATION`: primary-source and official-code compatibility qualification for external baselines.
3. `G2_SIX_GPU_SCREEN`: three qualified baseline families × two datasets, one seed, full intended Train/Dev budget.
4. `G3_CALIBRATION_READOUT`: common evaluation, paired patient-cluster bootstrap diagnostics, Pareto/competitiveness decision.

## Terminal verdicts

Exactly one:

- `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS`
- `MICA_SUBSTRATE_BORDERLINE`
- `MICA_SUBSTRATE_OUTCLASSED`
- `INSUFFICIENT_COMPETITIVE_CALIBRATION`
- `STOP_MICA_GENERALIZATION_EQUIVALENCE_FAILURE`

Only `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS` authorizes returning to the bounded Stage 0 RSM contract review. It still does not authorize Test or paper claims.
