<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `PRE_IDEA_PRACTICE_SHIFT_S0`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. Pure benchmark/measurement work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes.

**Current active Idea**: none.

**Idea 007**: not created / not authorized.

**Only authorized empirical work**: [`literature-search-20260908-medication-practice-shift/s0-practice-shift-admission-protocol.md`](literature-search-20260908-medication-practice-shift/s0-practice-shift-admission-protocol.md).

Later MIMIC-IV temporal groups (`2017 - 2019`, `2020 - 2022`), R0 Holdout, and the historical project test split remain quarantined.

## Cumulative failure landscape

### F1 — post-hoc same-information routes are compressed

Ideas 001--004 and EGSF repeatedly showed that low-dimensional transformations or selectors over already available frozen information do not establish incremental value once the strongest simple controls are supplied.

### F2 — statistical structure is not clinical action semantics

Idea 005 found reproducible ATC output structure but failed strict therapeutic-substitution admission. Taxonomy/shared indication cannot be promoted into clinical interchangeability without independent semantic evidence.

### F3 — equal information/rule entitlement is mandatory

EG-TER and Idea 006 establish the same higher-order control principle in two settings:

> if a learned method receives an external rule, risk relation, or operational state signal, the strongest direct control must receive the identical information.

### F4 — certification is a separate burden

CRC-PS showed empirical feasibility does not imply finite-sample certifiability. Guarantees remain downstream of mechanism evidence.

### F5 — medication cardinality is not normalized interaction propensity

B0 showed that changing medication count altered absolute DDI burden but not pair-normalized DDI propensity. Count-mediated treatment-preserving safety is closed under the tested premise.

### F6 — latent acceptable-treatment supervision is not identified

The selective-prescription-supervision reset found a plausible problem but no defensible latent clinical target under current retrospective labels. Generic PU/noisy-label learning is not enough for the first method paper.

### F7 — new state semantics do not imply learned-method value

Idea 006 is terminated with:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

R0 established a real operational exposure-state mismatch (`static_only_fraction = 21.0521%`). Exposure-conditioned training also reached the common safety budget where the tested conventional static DDI loss did not.

Nevertheless, on frozen Dev the equal-entitlement direct exposure reranker retained higher Recall@5 than the learned ExposureConditional model:

- DirectExposureRerank Recall@5: `0.509797`;
- ExposureConditional Recall@5: `0.505470`;
- EC minus reranker Recall delta: approximately `-0.004327`;
- 95% CI: `[-0.005315, -0.003362]`.

The learned route therefore failed its preregistered primary killer comparison.

Failure memory: [`failures/exposure-conditioned-learning-gate-01--direct-control-sufficiency.md`](failures/exposure-conditioned-learning-gate-01--direct-control-sufficiency.md).

## Higher-order reusable constraints

### C1 — cosmetic post-hoc resurrection is closed

A new statistic/function over an already failed frozen information premise is not a new research direction.

### C2 — semantic admission precedes clinical interpretation

Therapeutic alternatives, hidden positives, treatment obligations, clinical appropriateness, or patient-specific harm require independently grounded semantics.

### C3 — direct-use sufficiency must be challenged first

A new external signal or decision-state semantic can justify a learned method only if the learned method creates incremental value beyond direct use of the same signal.

### C4 — certification follows mechanism evidence

Do not make guarantees the first novelty investment.

### C5 — separate count effects from normalized interaction propensity

Absolute pair burden can move mechanically with output size.

### C6 — admitted resource fact: visit/hospitalization DDI co-membership is not current execution overlap

R0 remains valid and reusable as infrastructure/evidence, but it is not itself the target paper.

### C7 — new candidate constraint: deployment shift must beat marginal-prior correction

Medication frequencies are strongly imbalanced and can change over time. A temporal-domain method premise is not admitted merely because future-period performance drops.

Before any adaptation method, the project must ask whether a patient-disjoint target-era per-medication logit-bias correction explains most of the degradation.

Status: `EXTERNAL-EVIDENCE SUPPORTED / PROJECT-LOCAL ADMISSION PENDING`.

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen / advance condition |
| --- | --- | --- | --- |
| Frozen-output DDI/tension scalar routing | `CLOSED` | Idea 001 | genuinely new information/state/action semantics |
| Score geometry | `CLOSED` | Idea 002 | changed decision information |
| Prescription-relative/rank features | `CLOSED` | Idea 003 | new pre-prediction mechanism/supervision |
| Static co-selection scalar | `CLOSED` | Idea 004 | materially different relational semantics |
| ATC sibling substitution | `CLOSED` | Idea 005 | new action resolution + admitted therapeutic semantics |
| Count-mediated safety/coverage | `CLOSED` | B0 | different safety/coverage mechanism |
| Selective prescription supervision | `NOT ADMITTED` | supervision reset | identifiable multi-valid target |
| Exposure-conditioned DDI learning | `CLOSED` | Idea 006 Gate 01 | genuinely different safety target/action problem, not richer use of the same active-DDI signal |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, DMRNet, ChainCare | specific non-generic mechanism |
| Generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | KATMed, RES-MR, SafeRx-Agent, ATLAS | contribution beyond rule injection/verifier assembly |
| Multi-dataset MIMIC/eICU evaluation | `PRIOR ART / NOT A METHOD GAP` | HypeMed, KATMed, Rx-Expert, NLA-MMR | source-to-target deployment problem required |
| Temporal/external validation itself | `PRIOR ART` | narrow schizophrenia recommender + broader EHR literature | adaptation mechanism required |
| **Residual medication-transition practice shift** | **`SELECTED FOR S0`** | current bounded reset | pass target-prior-control S0 |

`CLOSED` is always conditional on the recorded scientific premise, not a universal ban on the noun.

## Current reset: Medication-Transition Practice Shift

Literature packet:

[`literature-search-20260908-medication-practice-shift/`](literature-search-20260908-medication-practice-shift/).

The retained search shows:

- multi-dataset generalization claims are crowded;
- temporal/external degradation is not itself novel;
- MIMIC-IV explicitly exposes `anchor_year_group` for medical-practice-over-time analyses;
- no retained close general MedRec method makes residual forward prescribing-practice adaptation, after medication-prior correction, its central problem.

The project therefore does not create Idea 007 yet.

## S0 admission question

> Does a source-era causal medication-order predictor suffer a material forward-period Recall@5 gap that remains material after a target-era medication-marginal/logit-bias adjustment estimated from disjoint target adaptation patients?

S0 deliberately gives the trivial explanation a strong chance to win.

### Temporal environments

Only decision bursts satisfying:

`year(decision_time) == anchor_year`

are retained, so `anchor_year_group` gives an unambiguous approximate care period.

- Source: `2008 - 2010` + `2011 - 2013`
- Target: `2014 - 2016`
- Future reserve: `2017 - 2019` + `2020 - 2022`

### Killer simple control

`TargetPriorBias` applies only a medication-specific logit shift estimated from a patient-disjoint target-era prior-build cohort. One scalar strength is selected on a separate target-era bias-tune cohort.

No target-era model weight training is allowed in S0.

### PASS

`PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT` requires:

- adequate cohort scale;
- at least `0.020` source-to-target Recall@5 gap with CI lower bound above `0.010`;
- bias-only recovery no greater than 50%;
- at least `0.010` residual gap after bias adjustment with CI lower bound above zero.

Only then may `ccf-idea-optimizer` attempt a method hypothesis.

### FAIL

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT` returns the project to `NO_HIGH_VALUE_DIRECTION_YET`.

No alternative year split, eICU rescue, feature expansion, or Idea 007 is implied.

## Publication boundary

Even on S0 PASS, the project may claim only empirical forward-domain degradation/residual shift until a method survives later gates. It may not call the observed change causal practice drift without stronger evidence.

The first paper remains method-first. S0 exists only to decide whether that method investment is justified.

## Current next owner

Local repository Agent executes S0 exactly as frozen, then runs `ccf-integrity-auditor`.
