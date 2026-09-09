<!-- markdownlint-disable MD013 -->

# Idea 007: Privileged Physiological Response Supervision

- **Idea ID**: `007-privileged-physiological-response-supervision`
- **Status**: `TERMINATED_AT_GATE_01_P1`
- **Stage**: `IDEA_007_TERMINATED_AT_GATE_01_P1`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_007`
- **Admission owner**: `ccf-pipeline-orchestrator`
- **Admission source revision**: `e301a0dbc8f511da038cad115ac80b108907f264`
- **Strict review score**: `4.17 / 5.00` (medium-high confidence)
- **Gate 01 owner**: `ccf-experiment-designer`
- **Gate 01 design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`, objective-domain closed / V7 executable)
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md) (frozen `v1.2`)
- **Physiology source spec**: [`experiments/gate-01-physiology-source-spec.md`](experiments/gate-01-physiology-source-spec.md)
- **P0 freeze**: [`experiments/gate-01-p0-freeze.json`](experiments/gate-01-p0-freeze.json) (`PASS`)
- **P1 mechanical preflight**: [`experiments/gate-01-mechanical-preflight.json`](experiments/gate-01-mechanical-preflight.json) (`STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT`)
- **P1 integrity audit**: [`experiments/gate-01-p1-integrity-audit.md`](experiments/gate-01-p1-integrity-audit.md) (`INTEGRITY_AUDIT_PASS`)
- **Canonical failure memory**: [`../../memory/failures/privileged-physiological-response-gate-01-p1--insufficient-support.md`](../../memory/failures/privileged-physiological-response-gate-01-p1--insufficient-support.md)
- **Training**: `NOT_AUTHORIZED`
- **Response outcomes / model metrics**: not accessed

Idea 007 was formally created/admitted after the completed strict review. Its
bounded kill-first Gate-01 cycle ended at the P1 mechanical support preflight;
this is not a claim that the method works and not publication evidence.

## Scientific question

At a medication-order decision point, can actual post-administration physiological
values, available only during training, provide medication-in-context
response-associated supervision that improves a strictly pre-order deployable
candidate-medication student beyond ordinary pre-order information and matched
semantic-ablation controls?

The scientific object is:

> Use the realized medication-in-context physiological trajectory only as
> training-time privileged supervision for a strictly pre-order medication
> recommender. The permitted interpretation is an observational
> response-associated predictive representation under the historical care policy.

The method must not require post-order medication, future administration, future
labs/vitals, future monitoring masks, discharge-coded information, or any
future-derived preprocessing statistic at inference.

## What this Idea is and is not

The generic primitives are already prior art: response-aware MedRec,
monitoring-aware chains, joint MedRec/lab prediction, MedRec knowledge
distillation, clinical privileged-modality transfer, and future-to-current
teacher/student learning. The Idea is admitted only for the MedRec-specific
response-supervision object and its prospective matched subtraction.

It may claim only a predictive response-associated representation. It may not claim
treatment effect, causal response, drug efficacy, therapeutic benefit,
counterfactual outcome, clinical optimality, or individualized causal benefit.

## Frozen Gate-01 contract

The complete protocol is in
[`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md). Its frozen
contracts are summarized here:

1. **R1 — Medication-specificity subtraction.** Generic Future-State Auxiliary /
   Medication-Ablated Future uses the same recommendation examples, administered
   positive support, administration anchor, future window, future-value/mask
   availability, deployable student, latent dimension, identical teacher shell and
   parameter count, auxiliary weight, optimizer, and update entitlement as
   Proposed. It removes focal medication identity and medication-specific response
   construction only from the privileged target branch. A comparable result stops
   with `STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE`.
2. **R2 — Monitoring-policy separation.** Monitoring-Mask-Only receives the same
   response support, future window, measurement availability/frequency pattern,
   student, capacity, loss, optimizer, and updates, but no physiological values or
   value-derived summary. A comparable result stops with
   `STOP_MONITORING_POLICY_SUFFICIENCY`.
3. **R3 — Equal support and deployment entitlement.**
   `A(e)=1` only for an actually administered positive focal-medication event with
   a valid linked future window. All privileged variants share the same `E_rec` and
   `A`; student recommendation loss covers full `E_rec`, while teacher
   recommendation and alignment both use exactly `A(e)=1`. Unsupported examples
   never construct a teacher branch and remain in the student objective without
   deletion, reweighting, or resampling; no unchosen medication receives a
   counterfactual response. The student and all student normalization statistics
   are strictly pre-order. Any leakage, unmatched support, or differential
   recommendation reweighting invalidates the Gate.

The Gate-01 family is fixed as:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Generic Pre-Order KD: a parameter-independent non-deployed teacher exactly
  isomorphic to `S_pre`, using the same strict pre-order schema, causal GRU,
  candidate embedding, interaction MLP, and 64-d latent, with no future input
  (required because the proposed method contains a teacher/student alignment term);
- Proposed Privileged Physiological Response Supervision.

An aligned REFINE/ChainCare-style comparison may be added only when task semantics
make it fair; it cannot replace any required mechanism control.

## Frozen decision and stop boundary

The primary endpoint is patient-mean `Recall@5` at fixed `K=5`. The protocol fixes
three training seeds, a two-level patient/seed bootstrap, `2,000` replicates, and
the practical margin `delta_practical = 0.005` absolute Recall@5 before execution.

For each killer control `C`, Proposed is **materially better** only when its point
advantage is at least `0.005` and the paired 95% bootstrap lower bound is strictly
positive. `C ≈ Proposed` is defined mechanically when the paired 95% upper bound
for Proposed's advantage is at most `0.005`; that result terminates the
response-specific mechanism. A statistically inconclusive interval also stops
admission and cannot trigger rescue. Proposed must additionally be non-inferior to
Strict Pre-Order Base with lower bound above `-0.005`.

No rescue is allowed with a larger teacher, Transformer-to-Mamba/GNN replacement,
different response window, extra modalities, subgroup mining, post-hoc feature
expansion, second response definition, favorable seed selection, or new split.

## Gate 01 P0/P1 result

P0 froze the protocol identity, source specification, `idea007-gate01-v1` patient
split, administration anchor, six-channel response tensor, `A(e)` support rule,
and all support/concentration floors. The P1 runner then assigned patient
partitions before any response-linked aggregate and used only the existing causal
order-time recommendation-example universe.

The public-safe aggregate record is:

| Scope | `E_rec` | `N_A` | Coverage | Supported patients | Supported meds | Min events/med |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Global | 5,553,455 | 163,610 | 0.029461 | 12,372 | 116 | 1 |
| Gate01-Train | 3,907,607 | 114,350 | 0.029263 | 8,686 | 114 | 1 |
| Gate01-Dev | 826,301 | 25,091 | 0.030365 | 1,796 | 103 | 1 |
| Gate01-Audit | 819,547 | 24,169 | 0.029491 | 1,890 | 103 | 1 |

Coverage fails the frozen global (`0.10`) and partition (`0.05`) floors in every
scope, and the minimum supported-events-per-counted-medication floor fails in
every scope. Medication concentration passes; patient concentration passes
globally and in Train but fails both frozen patient checks in Dev and Audit.
Therefore the frozen decision is
`STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT`. No rescue is
authorized, and the response-specific mechanism terminates at Gate 01 P1.

## Data and authorization boundary

The protocol permitted one mechanical response-linkage/coverage preflight only to
determine whether the already admitted method had enough non-concentrated support.
That preflight is complete and stopped before training. It did not inspect
recommendation outcomes or tune the protocol; the fixed count, coverage,
medication-concentration, and patient-concentration floors were applied as frozen.

`Gate01-Train`, `Gate01-Dev`, and `Gate01-Audit` are patient-disjoint and ordered
by a frozen hash split. Dev can select only among fixed checkpoints using the
predeclared rule. Audit is read once after every choice is frozen. MIMIC-IV G3/G4,
R0 Holdout, and the historical project test split remain quarantined and
uninspected.

No model training, Gate01 Dev/Audit model evaluation, result table, patient record,
prediction, weight, or private trace was created. G3/G4, R0 Holdout, and the
historical project test remain quarantined.

## Provenance

- Strict admission review: [`../../memory/model-reset-20260908-privileged-physiological-response/idea-review.md`](../../memory/model-reset-20260908-privileged-physiological-response/idea-review.md)
- Closest-work subtraction: [`../../memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md`](../../memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md)
- Frozen optimizer contract: [`../../memory/model-reset-20260908-privileged-physiological-response/idea-optimization.md`](../../memory/model-reset-20260908-privileged-physiological-response/idea-optimization.md)
- Reusable mechanism constraint: [`../../memory/failures/privileged-response-preidea--response-specificity-not-yet-identified.md`](../../memory/failures/privileged-response-preidea--response-specificity-not-yet-identified.md)

## Current state

```text
Stage: IDEA_007_TERMINATED_AT_GATE_01_P1
Idea 007: TERMINATED_AT_GATE_01_P1
Decision: STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT
P0 freeze: PASS
Gate 01: design frozen / objective-domain closed / V7 executable / independently audited
P1 mechanical preflight: STOP
Implementation: P1 runner only; full V1-V8 NOT STARTED
Formal training: NOT RUN
Training: NOT AUTHORIZED
No rescue authorized
Quarantine: intact
Project Active Idea: none
Project Stage: PRE_IDEA_AFTER_IDEA_007_SUPPORT_TERMINATION
New Idea: NOT CREATED
Next owner: ccf-idea-optimizer / exploratory
```
