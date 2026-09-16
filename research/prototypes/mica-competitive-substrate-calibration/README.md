# Stage -1G — Competitive substrate calibration

Status: `COMMON131_FROZEN_PRIMARY; NATIVE173_LANES_PRESERVED_SECONDARY; EXECUTION_IN_PROGRESS`

## 2026-09-16 protocol amendment — comparability-driven common131 primary

During Stage -1G execution, the literature/source audit established that the
MoleRec/SafeDrug/Carmen lineage and official ARMR MIMIC-III/MIMIC-IV assets
share one 131-code ATC4 identity (ARMR MIMIC-IV uses a different insertion
order). Therefore the primary comparison surface is now the additive
canonical common-131 benchmark on both datasets. The pre-existing native-173
MIMIC-IV jobs and results are preserved as secondary robustness evidence; no
new native-173 lanes are started after this freeze.

This is a comparability-driven correction made before interpreting the external
comparison, not a performance-driven vocabulary choice. The exact source
audit and mapping are in
[`research/benchmarks/mimiciv-medrec-common131/semantic-audit.json`](../../benchmarks/mimiciv-medrec-common131/semantic-audit.json).

The common-131 semantic verdict is
`COMMON_131_RECONSTRUCTABLE_WITH_DOCUMENTED_MAPPING`. The canonical hash of
the sorted code set is
`6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08`.

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
2. `COMMON131_FREEZE`: primary-source identity audit, additive MIMIC-IV projection, and mechanical checks.
3. `G1_QUALIFICATION`: primary-source and official-code compatibility qualification for external baselines.
4. `G2_SIX_GPU_SCREEN`: ARMR, MoleRec, and GAMENet on common131, one seed, full method-specific Train/Dev budget; preserved native-173 jobs remain secondary.
5. `READOUT`: common evaluation, paired patient-cluster bootstrap diagnostics, Pareto/competitiveness decision.

## Terminal verdicts

Exactly one:

- `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS`
- `MICA_SUBSTRATE_BORDERLINE`
- `MICA_SUBSTRATE_OUTCLASSED`
- `INSUFFICIENT_COMPETITIVE_CALIBRATION`
- `STOP_MICA_GENERALIZATION_EQUIVALENCE_FAILURE`
- `BENCHMARK_SEMANTICS_REQUIRE_REVIEW`

Only `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS` authorizes returning to the bounded Stage 0 RSM contract review. It still does not authorize Test or paper claims.
