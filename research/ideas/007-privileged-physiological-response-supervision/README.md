<!-- markdownlint-disable MD013 -->

# Idea 007: Privileged Physiological Response Supervision

- **Idea ID**: `007-privileged-physiological-response-supervision`
- **Status**: `ADMITTED_GATE_01_DESIGN_FROZEN_IMPLEMENTABILITY_CLOSED`
- **Stage**: `IDEA_007_GATE_01_DESIGN_FROZEN_IMPLEMENTABILITY_CLOSED_TRAINING_NOT_AUTHORIZED`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_007`
- **Admission owner**: `ccf-pipeline-orchestrator`
- **Admission source revision**: `e301a0dbc8f511da038cad115ac80b108907f264`
- **Strict review score**: `4.17 / 5.00` (medium-high confidence)
- **Gate 01 owner**: `ccf-experiment-designer`
- **Gate 01 design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`, implementability-closed revision)
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md) (`DESIGNED_NOT_EXECUTED`)
- **Physiology source spec**: [`experiments/gate-01-physiology-source-spec.md`](experiments/gate-01-physiology-source-spec.md)
- **Training**: `NOT_AUTHORIZED`
- **Response outcomes**: not accessed

Idea 007 was formally created/admitted after the completed strict review. This is
one bounded kill-first Gate-01 cycle, not a claim that the method works and not
publication evidence.

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
   `A`; unsupported examples remain in the full recommendation objective; no
   unchosen medication receives a counterfactual response; the student and all
   normalization statistics are strictly pre-order. Any leakage, unmatched
   support, or differential recommendation reweighting invalidates the Gate.

The Gate-01 family is fixed as:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Generic KD (required because the proposed implementation contains a
  teacher/student alignment term);
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

## Data and authorization boundary

The protocol permits a future mechanical response-linkage/coverage preflight only
to determine whether the already admitted method has enough non-concentrated
support. It is not exploratory research and it cannot inspect recommendation
outcomes or tune the protocol. The preflight has fixed count, coverage, medication
concentration, and patient-concentration floors; failure stops before training.

`Gate01-Train`, `Gate01-Dev`, and `Gate01-Audit` are patient-disjoint and ordered
by a frozen hash split. Dev can select only among fixed checkpoints using the
predeclared rule. Audit is read once after every choice is frozen. MIMIC-IV G3/G4,
R0 Holdout, and the historical project test split remain quarantined and
uninspected.

No response coverage run, training run, Audit evaluation, result table, patient
record, prediction, weight, or private trace is created by this admission/design
workflow. A later execution requires a new explicit authorization after the
audited design state.

## Provenance

- Strict admission review: [`../../memory/model-reset-20260908-privileged-physiological-response/idea-review.md`](../../memory/model-reset-20260908-privileged-physiological-response/idea-review.md)
- Closest-work subtraction: [`../../memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md`](../../memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md)
- Frozen optimizer contract: [`../../memory/model-reset-20260908-privileged-physiological-response/idea-optimization.md`](../../memory/model-reset-20260908-privileged-physiological-response/idea-optimization.md)
- Reusable mechanism constraint: [`../../memory/failures/privileged-response-preidea--response-specificity-not-yet-identified.md`](../../memory/failures/privileged-response-preidea--response-specificity-not-yet-identified.md)

## Current state

```text
Stage: IDEA_007_GATE_01_DESIGN_FROZEN_IMPLEMENTABILITY_CLOSED_TRAINING_NOT_AUTHORIZED
Active Idea: 007-privileged-physiological-response-supervision
Idea 007: created/admitted
Gate 01: design frozen / implementability closed / independently audited
Training: NOT AUTHORIZED
Next action: stop; await explicit future execution authorization
```
