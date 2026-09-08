<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `PRE_IDEA_EVENT_EDIT_M0`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. A genuinely new model is allowed. Pure benchmark/measurement work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes.

**Current active Idea**: none.

**Idea 007**: not created / not authorized.

**Only authorized empirical work**: [`model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md`](model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md).

MIMIC-IV G3/G4 future groups, R0 Holdout, and the historical project test split remain quarantined.

## Cumulative failure landscape

### F1 — post-hoc same-information routes are compressed

Ideas 001--004 and EGSF repeatedly showed that low-dimensional transformations or selectors over already available frozen information do not establish incremental value once the strongest simple controls are supplied.

### F2 — statistical structure is not clinical action semantics

Idea 005 found reproducible ATC output structure but failed strict therapeutic-substitution admission. Taxonomy/shared indication cannot be promoted into clinical interchangeability without independent semantic evidence.

### F3 — equal information/rule entitlement is mandatory

EG-TER and Idea 006 establish the same higher-order control principle in two settings:

> if a learned method receives an external rule, risk relation, operational state, or deterministic feasibility signal, the strongest direct control must receive the identical information.

### F4 — certification is a separate burden

CRC-PS showed empirical feasibility does not imply finite-sample certifiability. Guarantees remain downstream of mechanism evidence.

### F5 — medication cardinality is not normalized interaction propensity

B0 showed that changing medication count altered absolute DDI burden but not pair-normalized DDI propensity. Count-mediated treatment-preserving safety is closed under the tested premise.

### F6 — latent acceptable-treatment supervision is not identified

The selective-prescription-supervision reset found a plausible problem but no defensible latent clinical target under current retrospective labels. Generic PU/noisy-label learning is not enough for the first method paper.

### F7 — new state semantics do not imply learned-method value

Idea 006 established a real execution-exposure state mismatch, but the learned ExposureConditional model failed its equal-entitlement direct-reranker challenge. A valid new state representation is not itself a method contribution.

### F8 — chronology does not imply harmful deployment shift

The Medication Practice-Shift S0 gate returned:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

Under the frozen G0+G1 source versus G2 target protocol:

- `R_source = 0.4310427829`;
- `R_target_base = 0.4403698933`;
- `G_base = -0.0093271104`;
- 95% CI `[-0.0145853913, -0.0035238892]`.

The source-era predictor therefore performed better, not worse, on the target era. Target-prior logit correction improved target Recall@5 further to `0.4441638446`.

Chronological separation by itself is not evidence for a temporal-adaptation method.

Failure memory: [`failures/medication-practice-shift-s0--no-material-forward-degradation.md`](failures/medication-practice-shift-s0--no-material-forward-degradation.md).

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

### C6 — admitted resource fact: hospitalization DDI co-membership is not current execution overlap

Idea-006 R0 remains valid as infrastructure/evidence, but not as the target paper.

### C7 — deployment adaptation requires actual degradation

Do not invest in adaptation because two periods differ. First establish a material forward loss after giving simple target-marginal correction a fair chance.

### C8 — a new model must encode a new scientific object, not merely a new backbone

Transformer/Mamba/GNN/point-process architectures are allowed only when the proposed mechanism changes the decision object, supervision, state transition, or information flow in a way that can be independently falsified. A deeper encoder over the same failed target is not a reset.

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
| Exposure-conditioned DDI learning | `CLOSED` | Idea 006 Gate 01 | genuinely different safety target/action problem |
| Residual medication-practice adaptation | `CLOSED` | S0 | actual material forward degradation under a materially different deployment setting |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, DMRNet, ChainCare | specific non-generic decision mechanism |
| Generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | KATMed, RES-MR, SafeRx-Agent, ATLAS | contribution beyond rule injection/verifier assembly |
| Multi-dataset MIMIC/eICU evaluation | `PRIOR ART / NOT A METHOD GAP` | HypeMed, KATMed, Rx-Expert, NLA-MMR | source-to-target method problem required |
| Temporal/external validation itself | `PRIOR ART` | prior temporal/external validation work | method mechanism required |
| **Event-sourced regimen editing** | **`SELECTED FOR M0`** | raw POE action marks + current order-time infrastructure | pass equal-entitlement structural probe M0 |

`CLOSED` is conditional on the recorded scientific premise, not a universal ban on the noun.

## Current reset: Event-Sourced Regimen Editing

Reset packet:

[`model-reset-20260908-event-sourced-regimen-editing/`](model-reset-20260908-event-sourced-regimen-editing/).

### Structural observation

The existing order-time model already consumes historical medication transaction types and a pre-order active regimen. Its current target nevertheless collapses present `New` and `Change` transactions into medication-only labels and excludes present `D/C` from the target.

This means the pipeline observes action semantics in the past while discarding those semantics at the current supervised decision.

The candidate reset makes the target an explicit provider-order mark:

`(action, medication)`, where `action in {New, Change, D/C}`.

This is not a claim of therapeutic intent. It is an EHR order-workflow action.

### Closest-work boundary

Change-aware MedRec is not new: MICRON predicts visit-level additions/removals; ARMR models new versus historical medications; HeteroMed models expansion/inheritance. Order-time prediction is also not new: Rough et al. predict medication identities in a 10-minute order horizon.

The search-scoped opportunity is their intersection:

> strictly causal provider-order-time prediction of explicit regimen-edit marks over an event-sourced medication state.

The eventual method, if admitted, must derive value from that explicit edit structure rather than from a larger encoder.

### Strongest trivial explanation

The action labels may appear useful only because a deterministic state mask rules out impossible `Change` and `D/C` actions for inactive medications.

Therefore M0 gives the same state mask and the same inputs to the mandatory killer control:

`SeparateHeads + DirectStateMask`.

The fixed `StateEditProbe` must beat this control. It does not receive extra information.

## M0 admission question

> Are raw `New / Change / D/C` marks sufficiently supported and state-consistent, and does a fixed structured action-medication decoder create incremental predictive value beyond the strongest equal-entitlement direct state-mask classifier?

### Phase A

Before training, test support and state consistency. Failure stops the route immediately.

### Phase B

Only on Phase-A PASS, compare:

1. `FlatMark`;
2. `SeparateHeads + DirectStateMask`;
3. fixed rank-32 `StateEditProbe` with the identical mask.

No architecture grid is authorized.

### PASS

`PASS_M0_EVENT_EDIT_STRUCTURE` requires all frozen conditions in the M0 protocol, including statistically positive gains over the direct masked control and medication-level non-inferiority.

Only then may `ccf-idea-optimizer` design a full method within this single family, followed by strict `ccf-idea-reviewer` before Idea 007 exists.

### FAIL

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE` returns the project to `NO_HIGH_VALUE_DIRECTION_YET`.

No M0b or deeper-encoder rescue is allowed.

## Publication boundary

M0 is premise-selection evidence, not the paper. Even on PASS, the project must still demonstrate a genuine method contribution, novelty delta, multi-baseline claim support, and later untouched evaluation before promotion to a paper directory.

The first paper remains method-first.

## Current next owner

Local repository Agent executes M0 exactly as frozen, then runs `ccf-integrity-auditor`.
