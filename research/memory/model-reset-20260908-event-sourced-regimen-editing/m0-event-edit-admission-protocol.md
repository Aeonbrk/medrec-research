<!-- markdownlint-disable MD013 -->

# M0 — Event-Sourced Regimen-Edit Admission Protocol

## 1. Gate identity

- **Gate ID**: `M0_EVENT_SOURCED_EDIT_ADMISSION`
- **Stage**: `PRE_IDEA_EVENT_EDIT_M0`
- **Active Idea**: none
- **Idea 007**: not created / not authorized
- **Purpose**: decide whether explicit provider-order action semantics support a method-level event-edit representation before any full architecture is developed
- **PASS verdict**: `PASS_M0_EVENT_EDIT_STRUCTURE`
- **FAIL verdict**: `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`

This is a single bounded method-premise gate. It is not a benchmark study and not the final paper model.

## 2. Scientific question

> At a strictly causal inpatient medication-order decision point, do explicit `(action, medication)` marks derived from raw `poe.transaction_type` form a sufficiently supported and state-consistent target, and does a fixed structured action-medication decoder add predictive value beyond an equal-entitlement separate-head classifier with the same deterministic state-validity mask?

The candidate action set is exactly:

`{New, Change, D/C}`.

The medication vocabulary is exactly the frozen 131 ATC-L4 concepts already used by the order-time infrastructure.

## 3. Why this gate precedes a new model

A new architecture is scientifically admissible only if the new decision structure carries information that a simple same-input control cannot absorb.

M0 therefore freezes the encoder family and tests only the structural hypothesis:

`medication-only target -> explicit action-medication edit target`.

If the fixed structured decoder fails, no deeper Transformer, Mamba, GNN, point-process model, or larger hyperparameter search is authorized under this premise.

## 4. Data boundary

### 4.1 Source

Use raw MIMIC-IV `3.1` provider-order data and the existing leakage-safe medication normalization/linkage infrastructure.

Required source fields include at least:

- `subject_id`;
- `hadm_id`;
- `poe_id`;
- `ordertime`;
- `transaction_type`;
- medication linkage fields needed to map orders to the frozen 131-concept vocabulary.

### 4.2 Temporal admissibility

Retain only decision events satisfying:

`year(decision_time) == patient.anchor_year`.

M0 may use only the already admitted chronological environments:

- G0: `2008 - 2010`;
- G1: `2011 - 2013`;
- G2: `2014 - 2016`.

M0 must not inspect G3/G4 (`2017 - 2022`) in any form, including aggregate counts, label frequencies, event distributions, features, predictions, or metrics.

### 4.3 Additional quarantines

M0 must not inspect:

- R0 Holdout;
- the historical project test split.

### 4.4 Patient split

Within the admitted G0/G1/G2 patient universe, assign patients deterministically using the frozen subject-only salt:

`event-edit-m0-20260908`.

Use:

- `EditTrain`: 80%;
- `EditTune`: 10%;
- `EditAudit`: 10%.

All partitions must be patient-disjoint. No event from `EditAudit` may be inspected before the M0 freeze manifest is written.

## 5. Decision-point construction

Use the existing 10-minute causal order-burst convention unless mechanical incompatibility with explicit `D/C` marks is found. Any such incompatibility must terminate execution and be reported; it must not be silently redefined.

At each decision time `t`:

- history may contain only events with timestamp `< t`;
- current regimen state `A_t` must be reconstructed using only information available `< t`;
- target marks are mapped `New`, `Change`, and `D/C` medication-order events in `[t, t + 10 minutes)` under the frozen burst convention;
- one target mark is one pair `(action, medication)`;
- multiple marks may occur in one burst.

The mark vocabulary therefore contains exactly `3 x 131 = 393` marks.

Do not reinterpret the raw transaction labels as therapeutic intent. They are provider-order workflow actions.

## 6. Phase A — semantic/support admission

Phase A runs before any model training. If any required condition fails, stop immediately and return `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE` without training Phase B.

### A1. Overall support

Require:

- mapped all-action target events >= `250,000`;
- distinct contributing patients >= `10,000`.

### A2. Per-action support

For each of `New`, `Change`, and `D/C`, require:

- mapped target events >= `20,000`;
- distinct contributing patients >= `2,000`.

### A3. State consistency

The deterministic pre-order regimen state must be clinically/workflow coherent enough to support state-valid decoding.

Require:

- fraction of mapped `Change` target events whose medication is active immediately before `t` >= `0.70`;
- fraction of mapped `D/C` target events whose medication is active immediately before `t` >= `0.70`.

Do **not** require `New` to target an inactive medication. Renewal/reorder workflows can legitimately produce `New` transactions for a medication that is already represented in the reconstructed regimen state.

### A4. Distributed action semantics

Require at least `50` medication concepts that each have at least `50` target events in at least two of the three action classes.

This rejects a degenerate setting in which action prediction is effectively a small list of action-specific medications.

### A5. Integrity

Report exact counts, patient counts, state-consistency fractions, and the distributed-support count separately for `EditTrain`, `EditTune`, and the pre-freeze-visible aggregate excluding `EditAudit` where appropriate. Do not inspect `EditAudit` to make Phase-A design changes.

## 7. Common encoder contract

If Phase A passes, all learned variants use one common lightweight causal encoder family. The encoder is intentionally frozen as a control surface, not optimized as the contribution.

Use the existing order-time representation family:

- medication embedding: `64`;
- transaction-type embedding: `8`;
- elapsed-time projection: `8`;
- one-layer GRU hidden size: `128`;
- current 131-dimensional pre-order regimen state;
- log-hours-since-admission scalar;
- dropout: `0.10`.

The encoder consumes exactly the same information for all variants.

No architecture grid is allowed.

## 8. Model variants

### 8.1 FlatMark

`FlatMark` is the unstructured joint-label baseline.

- common encoder;
- one linear output layer with `393` logits;
- no deterministic state mask.

This tests whether simply preserving the action label is already sufficient.

### 8.2 SeparateHeads + DirectStateMask — strongest simple control

This is the mandatory killer control.

- common encoder;
- three independent linear heads, each outputting `131` logits for one action;
- concatenate to `393` mark logits;
- deterministic state-validity mask applied at decoding/evaluation time.

The mask is:

- `Change(m)` invalid when `A_t[m] = 0`;
- `D/C(m)` invalid when `A_t[m] = 0`;
- `New(m)` is never masked solely from active-state membership.

Do not use DDI, drug interactions, diagnosis rules, external knowledge, or post-order events in the mask.

### 8.3 StateEditProbe — fixed structured mechanism probe

`StateEditProbe` uses the same common encoder and the same deterministic state mask as the strongest control.

Let the common encoder emit hidden state `h`.

Define:

- medication base logits `b(h) = Linear(h) in R^131`;
- query `q(h) = Linear(h) in R^32`;
- learned medication embeddings `u_m in R^32`;
- learned action embeddings `v_a in R^32`;
- learned action bias `c_a`;
- learned active-state coefficient `d_a`.

For action `a` and medication `m`, before masking:

`s[a,m] = b_m(h) + <q(h), u_m elementwise-multiply v_a> + c_a + d_a * A_t[m]`.

The rank is fixed at `32`.

At decoding/evaluation time apply exactly the same state-validity mask as `SeparateHeads + DirectStateMask`.

No decoder-rank search, auxiliary loss, DDI term, extra encoder, or action-specific hand tuning is allowed.

## 9. Training contract

All three variants use:

- multilabel binary cross-entropy over the full 393-mark vocabulary;
- the same optimizer family and learning rate;
- the same batch size, subject to hardware memory only;
- the same maximum epochs;
- the same deterministic seed policy;
- early stopping selected only on `EditTune` BCE with the same patience rule.

Hardware-driven batch-size reduction is allowed only if applied equally to all variants and recorded before training.

No per-model hyperparameter search is allowed.

## 10. Freeze and audit access

Before any `EditAudit` access, serialize a freeze manifest containing at least:

- exact code revision;
- data-construction identity;
- split salt and partition counts available without reading `EditAudit` outcomes;
- vocabulary identity;
- all model definitions and fixed dimensions;
- optimizer/training settings;
- selected checkpoints from `EditTune`;
- metric definitions;
- bootstrap seed and replicate count;
- PASS/FAIL logic.

After this freeze, `EditAudit` may be accessed exactly once for the final M0 evaluation.

## 11. Metrics

### 11.1 Primary metric

For each action `a`, compute `ActionRecall@5_a` on audit bursts containing at least one true mark of action `a`. Rank only marks belonging to that action after applying the variant's frozen decoding rule.

Define:

`MacroActionRecall@5 = mean(ActionRecall@5_New, ActionRecall@5_Change, ActionRecall@5_D/C)`.

This is the primary metric.

### 11.2 Secondary metrics

Report:

- per-action PRAUC and macro-action PRAUC;
- `JointMarkRecall@5`: Recall@5 over the full 393-mark ranking;
- `MedicationRecall@5`: collapse action scores for medication `m` using the maximum valid action score, rank medications, and compare against the true medication concepts appearing in the burst;
- state-invalid prediction rate for `Change` and `D/C` before masking as an audit diagnostic;
- action prevalence and medication-frequency stratified results as descriptive diagnostics only, with no post-hoc gate changes.

## 12. Uncertainty estimation

For every primary probe-versus-control delta, use `2,000` paired patient-clustered bootstrap replicates on `EditAudit`.

Freeze bootstrap seed:

`26090807`.

Report percentile 95% confidence intervals.

The comparison of interest is always:

`StateEditProbe - (SeparateHeads + DirectStateMask)`.

## 13. Frozen PASS rule

M0 returns `PASS_M0_EVENT_EDIT_STRUCTURE` only if **all** of the following hold at full precision:

1. all Phase-A support and state-consistency conditions pass;
2. `Delta MacroActionRecall@5 >= +0.010` and its 95% CI lower bound is `> 0`;
3. `Delta JointMarkRecall@5 >= +0.005` and its 95% CI lower bound is `> 0`;
4. `Delta MedicationRecall@5 >= -0.005`;
5. for each individual action, `Delta ActionRecall@5_a >= -0.010`;
6. the integrity audit returns PASS.

Otherwise return:

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`.

There is no borderline or rescue state.

## 14. Interpretation boundary

A PASS means only:

> explicit event-sourced action-medication structure has demonstrated incremental predictive value beyond the strongest same-information direct state-mask control, sufficient to justify method design and strict novelty review.

A PASS does not yet establish a publishable method, clinical utility, causal treatment reasoning, or superiority to state-of-the-art MedRec models.

A FAIL means the event-edit structural premise is not admitted under this frozen task and resource setting.

## 15. Routing after M0

### PASS

Return to `ccf-pipeline-orchestrator`.

Then, and only then:

1. run `ccf-idea-optimizer` on the single event-sourced regimen-editing family;
2. run strict `ccf-idea-reviewer` against MICRON, ARMR, HeteroMed, Rough et al., COGNet, and generic marked temporal point-process / state-transition baselines;
3. create Idea 007 only if the method delta survives review.

### FAIL

Return to:

`NO_HIGH_VALUE_DIRECTION_YET`.

Do not run M0b.

## 16. Explicitly prohibited rescue actions

Within this reset, do not:

- change the temporal environments or inspect G3/G4;
- inspect R0 Holdout or the historical test split;
- add DDI/safety objectives;
- add labs, vitals, notes, or discharge-coded future information;
- add an LLM, KG, guideline engine, or external drug rule;
- change the 131-medication vocabulary;
- merge or relabel the three action classes after seeing results;
- tune the structured rank;
- replace the common encoder with a Transformer/Mamba/GNN after a failed M0;
- run subgroup rescue experiments;
- create Idea 007 before the prescribed PASS routing is complete.

## 17. Required artifacts from local execution

The local Agent must produce in this directory:

- `run_m0_event_edit_admission.py`;
- `m0-summary.json`;
- `m0-decision.md`;
- `m0-integrity-audit.md`.

The decision document must state the exact Phase-A values, all three model rows, all frozen gate conditions, quarantine confirmations, and next CCFA owner.
