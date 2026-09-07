<!-- markdownlint-disable MD013 -->

# S0 — Medication Practice-Shift Admission

## 0. Protocol identity

- **Stage**: `PRE_IDEA_PRACTICE_SHIFT_S0`
- **Owner**: `ccf-experiment-designer`
- **Mode**: bounded pre-Idea premise admission
- **Status**: `FROZEN / AUTHORIZED / NOT_EXECUTED`
- **Method Idea**: none; Idea 007 is not created
- **Primary data**: raw MIMIC-IV 3.1
- **Reusable task infrastructure**: leakage-safe provider-order-time burst pipeline from terminated Idea 006
- **DDI/safety objective**: forbidden
- **Later-period reserve**: MIMIC-IV anchor groups `2017 - 2019` and `2020 - 2022`, quarantined
- **Historical project test split**: forbidden
- **R0 Holdout**: remains forbidden

S0 is the only authorized empirical test in the post-Idea-006 reset. It asks whether a future-practice adaptation problem exists before any adaptation method is designed.

## 1. Decision question

> Does a source-era causal medication-order predictor suffer a material forward-period fidelity drop that remains material after a strong medication-level target-prior/logit-bias adjustment estimated from a patient-disjoint target-era adaptation cohort?

The strongest simple null is:

> Apparent temporal degradation is mostly marginal medication-frequency drift; per-medication intercept recalibration is sufficient.

S0 must prefer this null unless a substantial residual remains.

## 2. Why this is a pre-Idea gate

S0 is not a paper contribution and not a benchmark study.

A PASS establishes only that there is enough residual deployment shift to justify asking `ccf-idea-optimizer` for a MedRec-specific adaptation mechanism.

A FAIL terminates this reset. Do not respond by changing the era split, adding covariates, switching to eICU, or creating Idea 007.

## 3. Temporal environment construction

MIMIC-IV provides patient-level `anchor_year`, `anchor_year_group`, and shifted event timestamps.

To avoid ambiguous cross-group alignment, retain a decision burst for S0 only when:

```text
year(decision_time) == patient.anchor_year
```

For such a burst, its approximate real-care period is exactly the patient's documented `anchor_year_group`.

Allowed groups:

```text
G0 = 2008 - 2010
G1 = 2011 - 2013
G2 = 2014 - 2016
G3 = 2017 - 2019
G4 = 2020 - 2022
```

If the local MIMIC-IV 3.1 resource does not expose these groups, S0 fails rather than inventing an alternative temporal proxy.

Scientific usage:

- `G0 + G1`: source era
- `G2`: target adaptation/evaluation era
- `G3 + G4`: future reserve; no clinical/event/target aggregate may be inspected in S0

Because `anchor_year_group` is patient-level, patients cannot cross these environment groups.

## 4. Patient partitions inside eras

### 4.1 Source era `G0 + G1`

Hash source `subject_id` with:

```text
salt = medication-practice-shift-s0-source-20260908
```

using the existing project SHA256-to-unit-interval convention.

Assign:

```text
SourceTrain: 0.00 <= u < 0.80
SourceTune:  0.80 <= u < 0.90
SourceAudit: 0.90 <= u <= 1.00
```

- SourceTrain: model fitting and source medication-prior estimation.
- SourceTune: checkpoint selection only.
- SourceAudit: source-era reference performance only.

### 4.2 Target era `G2`

Hash target `subject_id` with:

```text
salt = medication-practice-shift-s0-target-20260908
```

Assign:

```text
TargetPriorBuild: 0.00 <= u < 0.10
TargetBiasTune:   0.10 <= u < 0.20
TargetAudit:      0.20 <= u <= 1.00
```

- TargetPriorBuild: target medication marginals only.
- TargetBiasTune: choose one scalar bias strength from the frozen grid.
- TargetAudit: one frozen outer evaluation after all choices are frozen.

No model parameter may be trained on target-era patients in S0.

## 5. Decision task

Reuse the Idea-006 provider-order-time task semantics, but remove all DDI/safety scientific roles.

Frozen task:

- positive order transactions: `New`, `Change`;
- `D/C` is a historical state transaction, not a positive target;
- non-overlapping 10-minute medication-order bursts;
- target interval `[t, t + 10 min)`;
- all model inputs strictly `< t`;
- target medication concepts deduplicated within the burst;
- frozen 131 ATC-L4 medication vocabulary and R0 deterministic medication normalization.

No current-hospitalization discharge-coded diagnosis/procedure information is allowed.

## 6. Common source predictor

Use exactly one non-novel source predictor. Architecture search is prohibited.

Reuse the Idea-006 `Base` architecture/input contract:

- last 64 normalized medication-order transactions strictly before `t`;
- medication embedding 64;
- transaction-type embedding 8;
- elapsed-time projection 8;
- one-layer GRU hidden size 128;
- strictly pre-order execution-confirmed active-regimen binary vector, used only as a medication-state feature and not with any DDI objective;
- `log1p(hours since admission)`;
- MLP `260 -> 128 -> 131`, ReLU, dropout 0.10;
- full-vocabulary unweighted BCE prediction loss.

Training contract:

```text
AdamW
lr = 1e-3
weight_decay = 1e-5
batch_size = 2048, or the largest deterministic power of two <= 2048 if genuine OOM
max_epochs = 5
patience = 1
checkpoint = lowest SourceTune BCE prediction loss
seed = 260908
```

No architecture, learning-rate, seed, sequence-length, or loss search is authorized.

## 7. Source-only baseline

`SourceOnly` is the frozen source predictor with no target-era adaptation.

Primary ranking is fixed:

```text
K = 5
```

Tie-break by ascending medication concept code.

## 8. Strong simple target-prior control

The only adaptation allowed in S0 is `TargetPriorBias`.

### 8.1 Marginal estimation

For each medication `m`, compute burst-level occurrence rates on:

- SourceTrain targets: `p_s(m)`;
- TargetPriorBuild targets: `p_t(m)`.

Use fixed Beta(1,1) smoothing:

```text
p(m) = (positive_bursts(m) + 1) / (total_bursts + 2)
```

Define the target-prior logit shift:

$$
\Delta b_m = \operatorname{logit}(p_t(m)) - \operatorname{logit}(p_s(m)).
$$

### 8.2 Bias-adjusted prediction

For frozen SourceOnly logits `z_t(m)`:

$$
z'_t(m)=z_t(m)+\alpha\Delta b_m.
$$

Frozen grid:

```text
alpha ∈ {0.0, 0.25, 0.5, 1.0, 2.0}
```

Choose alpha on `TargetBiasTune` by highest mean burst-level Recall@5; tie-break to the smaller alpha.

Then freeze alpha before any TargetAudit metric is computed.

This control receives target-era labels only through the explicitly allocated adaptation patients. It does not update encoder/model weights.

## 9. Metrics

Primary metric:

```text
Recall@5
```

Secondary:

- NDCG@5;
- Hit@5;
- micro-PRAUC from frozen probabilities/logits;
- medication-frequency distribution summaries;
- target medications unseen in SourceTrain, reported descriptively.

No DDI/safety metric participates in S0.

## 10. Primary quantities

Let:

```text
R_source = SourceOnly Recall@5 on SourceAudit
R_target_base = SourceOnly Recall@5 on TargetAudit
R_target_bias = frozen TargetPriorBias Recall@5 on TargetAudit
```

Define source-to-target base gap:

$$
G_{base}=R_{source}-R_{target\_base}.
$$

Define residual gap after target-prior correction:

$$
G_{bias}=R_{source}-R_{target\_bias}.
$$

When `G_base > 0`, define point-estimate recovery fraction:

$$
Recovery=\frac{R_{target\_bias}-R_{target\_base}}{G_{base}}.
$$

The recovery ratio is descriptive/gating at the point estimate; uncertainty gating is applied to the two gap quantities directly.

## 11. Statistical unit

Use 2,000 bootstrap replicates, seed `260908`.

Because SourceAudit and TargetAudit contain different patients, use an **independent patient-clustered two-sample bootstrap**:

1. sample SourceAudit patients with replacement, retaining all their bursts;
2. independently sample TargetAudit patients with replacement, retaining all their bursts;
3. compute `G_base` and `G_bias` for each replicate using the same TargetAudit patient multiplicities for SourceOnly and TargetPriorBias;
4. report two-sided 95% percentile intervals.

Do not use burst-level IID bootstrap.

## 12. Frozen support floors

Condition 1 passes only if all retained anchor-matched cohorts meet:

```text
SourceTrain:      >= 100,000 bursts and >= 5,000 patients
SourceTune:       >= 10,000 bursts and >= 500 patients
SourceAudit:      >= 10,000 bursts and >= 500 patients
TargetPriorBuild: >= 10,000 bursts and >= 500 patients
TargetBiasTune:   >= 10,000 bursts and >= 500 patients
TargetAudit:      >= 50,000 bursts and >= 2,000 patients
```

If any floor fails, return the S0 FAIL verdict. Do not broaden temporal alignment to recover sample size.

## 13. Frozen premise PASS rule

Return:

`PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT`

only if **all** conditions hold.

### Condition 1 — scale

All support floors in Section 12 pass.

### Condition 2 — material forward degradation

$$
G_{base} \ge 0.020
$$

and the 95% bootstrap CI lower bound for `G_base` is strictly greater than `0.010`.

### Condition 3 — marginal-prior control is insufficient

Both must hold:

$$
Recovery \le 0.50
$$

and

$$
G_{bias} \ge 0.010
$$

with the 95% bootstrap CI lower bound for `G_bias` strictly greater than zero.

Otherwise return:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

The thresholds are research-investment floors, not clinical-performance thresholds.

## 14. Interpretation

### PASS means only

A temporally later MIMIC-IV medication-order environment exhibits a material fidelity gap that cannot be explained or mostly repaired by patient-disjoint target-era medication marginal recalibration.

This supports investment in an adaptation-method hypothesis.

It does not establish:

- causal practice drift;
- superiority of any domain-adaptation architecture;
- cross-hospital generalization;
- clinical benefit;
- final paper novelty.

### FAIL means

Either the forward gap is too small, the sample is inadequate, or a simple medication-prior adjustment explains/repairs enough of the observed degradation that a new adaptation method has low expected scientific value.

## 15. No-rescue rule

On S0 FAIL, do not:

- choose different year groups;
- remove the anchor-year matching restriction;
- add diagnosis/procedure/lab/vital features;
- switch from order-time to visit-level labels;
- add eICU;
- fine-tune on TargetAudit;
- replace the bias control with a weaker control;
- create another S0 variant;
- create Idea 007.

Return to `NO_HIGH_VALUE_DIRECTION_YET`.

## 16. Routing on PASS

On S0 PASS:

1. stop local scientific execution;
2. return to `ccf-pipeline-orchestrator`;
3. invoke `ccf-idea-optimizer` on the single `MEDICATION_TRANSITION_PRACTICE_SHIFT` family;
4. require a strict idea review against generic fine-tuning/domain-adaptation/continual-learning baselines before Idea 007 creation.

Do not consume `G3`, `G4`, R0 Holdout, or the historical project test split on S0 PASS.

## 17. Public artifacts

Only public-safe artifacts may be committed:

- `run_s0_practice_shift_admission.py`;
- `s0-summary.json`;
- `s0-decision.md`;
- `s0-integrity-audit.md`.

No patient identifiers, event timestamps, raw rows, private paths, model checkpoints, or patient-level predictions may enter Git.

## 18. Integrity requirements

Post-execution `ccf-integrity-auditor` must verify:

- temporal group assignment follows `year(t) == anchor_year` exactly;
- G3/G4 clinical data were not inspected;
- TargetAudit was accessed only after source checkpoint, target priors, alpha, metrics, and PASS logic were frozen;
- target-prior control uses only TargetPriorBuild/TargetBiasTune labels;
- no model weights were trained on target-era patients;
- all numbers and confidence intervals match summary/decision;
- no temporal degradation is described as causal practice change without additional evidence.
