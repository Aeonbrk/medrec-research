<!-- markdownlint-disable MD013 -->

# Gate 01 Protocol — Privileged Physiological Response Supervision

## Protocol status

- **Idea**: `007-privileged-physiological-response-supervision`
- **Owner**: `ccf-experiment-designer`
- **Mode**: `ccf-experiment-designer / design`
- **Stage**: `IDEA_007_GATE_01_DESIGN_FROZEN_AUDITED_TRAINING_NOT_AUTHORIZED`
- **Status**: `DESIGNED_NOT_EXECUTED`
- **Design revision**: `v1.0`
- **Design date**: `2026-09-09`
- **Admission source revision**: `e301a0dbc8f511da038cad115ac80b108907f264`
- **Training**: `NOT_AUTHORIZED`
- **Results**: none; no model, response outcome, or split outcome has been inspected

This is the single kill-first protocol for the first Idea-007 mechanism gate. It
freezes the scientific question, support contract, chronology, controls, metrics,
decision thresholds, and no-rescue boundary before any training result is seen.
It is not publication claim-support evidence and it does not authorize local
scientific execution.

## 1. Scientific question and claim boundary

At a medication-order decision point, can realized post-administration
physiological values, available only during training, provide medication-in-context
response-associated supervision that improves a strictly pre-order deployable
student beyond ordinary pre-order information and matched controls that remove the
claimed response semantics?

The admitted scientific object is:

> Use actual post-administration medication-in-context physiological trajectories
> only as training-time privileged supervision for a strictly pre-order
> candidate-medication student. The method may claim an observational
> response-associated predictive representation under the historical care policy.

The Gate may not claim treatment effect, causal response, drug efficacy,
therapeutic benefit, counterfactual outcome, clinical optimality, or individualized
causal benefit. Post-administration physiology may also reflect severity,
co-medications, fluids, procedures, ventilation, dose/route, clinician actions,
spontaneous progression, treatment timing, and monitoring policy.

The Gate is a mechanism-admission test, not a test of clinical utility. A result
that improves over an ordinary Base but does not beat the matched killers does not
admit the response-specific Idea.

## 2. Frozen terminology

The following symbols are fixed before any execution:

- `E_rec`: the complete frozen recommendation-example set for the authorized
  Gate-01 development pool. It is the same set for every variant.
- `e`: one recommendation example with order decision time `t(e)`, patient,
  admission, and candidate focal medication `m(e)`.
- `a(e)`: the first actual positive eMAR administration of `m(e)` after `t(e)`
  in the same admission, with `0 < a(e)-t(e) <= 6 hours`. Later administrations
  do not replace this anchor.
- `W(e)`: the fixed future monitoring window `(a(e), a(e)+24 hours]`.
- `P`: the fixed six-channel physiological set
  `{heart_rate, systolic_blood_pressure, diastolic_blood_pressure,
  respiratory_rate, oxygen_saturation, temperature}`. Source-specific item IDs
  are mapped to these names by the existing public-safe Dataset Manifest; no
  seventh channel or substitute channel may be added after the preflight.
- `r_e`: the six-channel physiological value tensor in `W(e)` for `P`.
- `M_e`: the value-availability/missingness mask for exactly `P` and `W(e)`.
- `A(e)`:

  ```text
  A(e) = 1 iff e is an actually administered positive focal-medication event
         with a(e) satisfying the anchor rule and a valid linked W(e) containing
         at least two observed physiological timestamps and at least one valid
         value in the predeclared channel set; otherwise A(e) = 0.
  ```

`A(e)=0` disables only the auxiliary term. It never drops, changes, or
differentially reweights `e` in the recommendation objective. No response target
is constructed for an unchosen medication.

The administration anchor, 24-hour window, channel set, validity rule, and support
indicator are immutable after the mechanical preflight begins. A different window,
anchor, or response definition is a new Idea, not a Gate-01 repair.

## 3. Mechanical response-linkage and support preflight

The preflight is a pure mechanical sufficiency check. It may inspect event times,
administration linkage, future-window value availability, masks, and aggregate
support counts. It must not inspect recommendation outcomes, train a model, fit a
representation, compare metrics, or choose a protocol parameter. It is not an
exploratory research stage.

The preflight is run only on the authorized Gate-01 development pool after the
patient-disjoint split is frozen. `G3`, `G4`, `R0 Holdout`, and the historical
project test split are outside the pool and remain untouched.

### 3.1 Global support floors

The method is supportable only if all of the following hold on the complete
Gate-01 development pool and separately on each Train, Dev, and Audit partition:

| Quantity | Frozen floor |
| --- | ---: |
| `E_rec` count | at least `10,000` recommendation examples globally; at least `1,000` per partition |
| `N_A = sum_e A(e)` | at least `5,000` supported events globally; at least `500` per partition |
| response coverage `N_A / E_rec` | at least `0.10` globally and at least `0.05` per partition |
| distinct supported patients | at least `500` globally and at least `100` per partition |
| supported focal medications | at least `20` globally and at least `10` per partition |
| supported events per counted medication | at least `25` globally and at least `10` per partition |

### 3.2 Concentration floors

Support must not be carried by a few medications or patients. With
`p_m = N_m / N_A` and `p_i = N_i / N_A`, where `N_m` and `N_i` are supported
event counts for medication `m` and patient `i`, the following are frozen:

- `max_m p_m <= 0.25`;
- the five largest `p_m` sum to at most `0.60`;
- `max_i p_i <= 0.01`;
- the twenty largest `p_i` sum to at most `0.10`.

The same medication and patient concentration checks apply within each partition.
Ties are resolved by medication identifier or patient identifier ascending only for
reporting; no support unit is removed.

If any global or partition floor fails, the preflight returns
`STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT`, no model is
trained, and the response-specific mechanism terminates. The threshold values are
not changed after support is observed.

The preflight report, if later authorized, may contain only public-safe aggregate
counts and concentration summaries. Patient-level rows, split membership, raw
trajectories, and predictions never enter Git.

## 4. Chronology, splits, and access permissions

The Gate-01 development pool is partitioned once at the patient level using the
deterministic hash salt `idea007-gate01-v1`:

| Partition | Hash interval | Permission before design audit | Permission after design freeze |
| --- | --- | --- | --- |
| `Gate01-Train` | `[0.00, 0.70)` | no access in this design-only turn | model fitting and Train-only statistics after separate execution authorization |
| `Gate01-Dev` | `[0.70, 0.85)` | no access in this design-only turn | one fixed checkpoint-selection/QA pass after Train fitting; no protocol changes |
| `Gate01-Audit` | `[0.85, 1.00)` | no access in this design-only turn | one final frozen evaluation only after all training and selection choices are immutable |

The partition assignment is created before any response-linked aggregate is
computed. The preflight may read only the mechanical linkage fields defined in
Section 3. It may not use Audit outcomes to select a model, threshold, feature,
window, channel, support floor, or stop rule.

The following sources have zero permission in every Gate-01 step:

- MIMIC-IV `G3` and `G4` future reserve;
- `R0 Holdout`;
- the historical project test split.

There is no second validation split, hidden Gate 01b, subgroup-driven split,
response-definition search, or post-hoc repartitioning. Any execution artifact
must record the split salt, partition counts, and access order before Audit is
opened.

## 5. Student deployment contract

All variants that contain a privileged branch use the same deployable student
`S_pre` and the same inference inputs. The non-privileged controls use the same
backbone and recommendation head, with only the explicitly listed pre-order
physiology input difference.

### 5.1 Common student architecture

- one-layer GRU over the frozen causal pre-order event/state sequence, hidden size
  `128`;
- candidate-medication embedding size `64`;
- interaction MLP `256 -> 128 -> 64`, with the final `64`-dimensional vector used
  for response alignment and the recommendation head producing the medication
  score;
- fixed recommendation output cardinality `K=5` for the primary metric;
- no architecture search, width search, alternative backbone, or method-specific
  head is allowed.

`Strict Pre-Order Base` uses the frozen pre-order medication/order state and timing
context. `Base + Pre-Order Physiology` adds only pre-order physiological values and
their pre-order missingness indicators. `S_pre` for every privileged variant is the
same architecture as Base + Pre-Order Physiology and receives the same candidate
medication input `m(e)`.

### 5.2 Teacher capacity contract

Every trainable privileged branch uses one fixed teacher shell: a one-layer GRU
with hidden size `128`, a fixed input projection, LayerNorm, and a linear projection
to `d_resp = 64`. The input schema, sequence length, parameter count, optimizer,
and update budget are identical for `V3`–`V8`. An ablated signal is represented by
the predeclared zero/constant channel in that same schema; it never removes a
module or gives a control a smaller network. `V4` supplies the Train-only static
prototype through this shell, `V5` supplies the frozen within-stratum permutation,
and `V7` supplies the future-free pre-order teacher through the same shell. Thus
"comparable teacher capacity" means identical teacher architecture and parameter
count, not an informal attempt to match total FLOPs after results are seen.

### 5.3 Allowed and forbidden student information

The student may use only information available strictly before `t(e)`:

- prior order and administration history that is causal at `t(e)`;
- active pre-order regimen/state and admission context;
- pre-order labs/vitals and their pre-order missingness indicators;
- elapsed-time features and the candidate medication identity.

The student and every statistic used to normalize it must not use:

- post-order medication or future administration;
- any value or mask in `W(e)`;
- future labs/vitals or future monitoring frequency;
- discharge-coded or future-coded information;
- any statistic computed from future values, future masks, or future outcomes.

Normalization parameters are fit from Train-only pre-order information. The teacher,
future values, future masks, privileged targets, and future-derived preprocessing
are completely absent at inference. A violation is
`STOP_STUDENT_PATH_LEAKAGE` and invalidates the Gate rather than becoming an
implementation issue.

## 6. Objective and equal entitlement

Every variant uses the same recommendation labels, candidate universe, batches,
optimizer family, update budget, and evaluation code. The recommendation loss is
the mean over the full `E_rec` set. Privileged variants add a single fixed-weight
auxiliary term:

```text
L_v = mean_{e in E_rec} ell_rec^v(e)
      + 1.0 * mean_{e in E_rec, A(e)=1} ell_aux^v(e).
```

The auxiliary mean is defined as zero when `sum_e A(e)=0`, but the preflight floors
make that case a stop before training. `lambda_aux = 1.0`, latent dimension
`d_resp = 64`, AdamW (`lr=1e-3`, `weight_decay=1e-4`, `beta1=0.9`, `beta2=0.999`),
batch size `256`, maximum `50` epochs, and fixed seeds `7007`, `7008`, and `7009`
are frozen for every trainable variant. Every seed trains for the same maximum
updates; Dev checkpoint selection uses the same rule in Section 8 and cannot
change these quantities.

The student, latent dimension, auxiliary weight, optimizer/update entitlement,
administration anchor, future window, value/mask availability, `E_rec`, and `A`
are therefore equal across all privileged variants. Unsupported examples remain
in the recommendation objective for every variant.

## 7. Required variant family

The following rows are the complete minimum Gate-01 family. The variant names and
subtractions are frozen before training.

| ID | Variant | Privileged branch / student input | Scientific question |
| --- | --- | --- | --- |
| `V1` | Strict Pre-Order Base | no privileged branch; strictly pre-order state only | ordinary causal recommendation reference |
| `V2` | Base + Pre-Order Physiology | no privileged branch; adds only pre-order physiology/masks | whether ordinary richer pre-order physiology explains the gain |
| `V3` | Generic Future-State Auxiliary / Medication-Ablated Future | same `r_e`, `M_e`, `a(e)`, `W(e)`, `A`, `S_pre`, `d_resp`, capacity, `lambda`, optimizer, and updates as Proposed; removes focal-medication identity and medication-specific response construction from the target branch | R1 medication-specificity subtraction |
| `V4` | Static Medication Response Prototype | Train-only per-medication average future trajectory projected through the same `d_resp` target shell; no patient-specific future values; same `E_rec`, `A`, support, student, capacity, and updates | static medication identity/prototype explanation |
| `V5` | Response Shuffle | Proposed value/mask tensors permuted within focal-medication and measurement-availability strata with frozen seed `70070`; same `E_rec`, `A`, window, capacity, and updates | patient–medication–response correspondence |
| `V6` | Monitoring-Mask-Only | receives exactly `M_e` and fixed availability/frequency summaries over `W(e)` but no physiological values or value-derived summary; all other entitlement matches Proposed | R2 monitoring-policy sufficiency |
| `V7` | Generic KD | same student, latent dimension, loss, and update entitlement; teacher sees no future physiology or response target and is trained only from the ordinary pre-order recommendation task | whether generic teacher–student/KD mechanics suffice |
| `V8` | Proposed Privileged Physiological Response Supervision | teacher receives focal medication, allowed non-focal treatment context, `r_e`, and `M_e`; target is the medication-in-context response-associated latent; student remains `S_pre` | admitted response-specific method |

`V7` is required in this protocol because the admitted implementation has an
explicit teacher/student alignment term, so distillation mechanics are a live
alternative explanation. It uses the same `E_rec`, `A`, student, latent dimension,
loss weight, optimizer, and update entitlement as the other privileged variants;
only its teacher information source is changed. It cannot be omitted after results
are seen.

### 7.1 R1 exact subtraction

`V3` uses the identical observed future value tensor and mask as `V8`, the identical
administration anchor and future window, and the identical supported event set.
Its privileged branch may use only non-focal context defined in the Dataset
Manifest. It must not use a focal-medication embedding, medication-coded event
identifier, medication-conditioned delta, medication-specific label, or
per-medication response prototype. The candidate medication remains in `S_pre` in
both rows because removing it would change the recommendation task rather than
test the privileged target semantics.

If `V3` is comparable to `V8`, the frozen stop is:

`STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE`.

### 7.2 R2 exact subtraction

`V6` receives the same response support `A`, future window, measurement availability
and frequency pattern, student, latent dimension, teacher capacity, loss weight,
optimizer, and updates as `V8`, but no physiological value or value-derived
summary. A mask is allowed only as the predeclared missing-data input. If `V6` is
comparable to `V8`, the frozen stop is:

`STOP_MONITORING_POLICY_SUFFICIENCY`.

### 7.3 R3 positive-only and equal-support rule

All of `V3`–`V8` use the same `E_rec` and the same `A(e)`. No unchosen medication
receives a counterfactual response target. No unsupported example is silently
dropped, reweighted, or normalized differently. Any mismatch in support, sample
entitlement, recommendation weighting, or update budget is:

`STOP_UNMATCHED_SUPPORT_OR_SAMPLE_ENTITLEMENT`.

## 8. Training, Dev selection, and Audit evaluation

No step in this section is executed in the current workflow. It defines the only
future execution order if a separate authorization is granted after this design
audit.

1. **P0 — Freeze record.** Serialize this protocol revision, split salt, variant
   matrix, seeds, hyperparameters, normalization source, response permutation seed,
   metric code revision, and decision thresholds. Do not open Audit outcomes.
2. **P1 — Linkage preflight.** Run only the Section-3 mechanical checks. If any
   floor fails, stop before training.
3. **P2 — Train.** Fit every applicable variant on `Gate01-Train` with all three
   fixed seeds. No variant may receive a different number of examples, updates, or
   optimizer steps.
4. **P3 — Dev checkpoint rule.** For each method/seed, choose the earliest epoch
   among the fixed set `{10, 20, 30, 40, 50}` with the lowest full-`E_rec`
   recommendation loss on `Gate01-Dev`; break ties by the smaller epoch. No Dev
   metric, subgroup, response definition, or control result may alter the rule.
5. **P4 — Evaluation freeze.** Freeze the selected checkpoint, normalization
   parameters, candidate universe, `K=5`, metric implementation, bootstrap seed,
   and all stop rules. Record the exact configuration before reading any Audit
   recommendation outcome.
6. **P5 — Audit.** Read `Gate01-Audit` once and evaluate all frozen variants with
   identical target joins and patient-clustered aggregation. No checkpoint,
   threshold, architecture, or split can be changed after Audit access.
7. **P6 — Decision.** Apply Section 9 mechanically. A stop or inconclusive result
   closes the response-specific route; it does not authorize rescue or another
   response definition.

## 9. Metrics and frozen practical/statistical decision rule

The primary metric is patient-mean `Recall@5` on `Gate01-Audit`, with fixed output
cardinality `K=5`. Secondary descriptive metrics are `Jaccard@5`, `Precision@5`,
and micro-F1; they cannot override the primary decision or be selected after Audit.
No clinical benefit, efficacy, or causal metric is used.

For every required killer control `C`, define the primary paired contrast:

```text
Delta_C = mean_seed(Recall@5(Proposed) - Recall@5(C)).
```

The estimate averages the three frozen seeds. Uncertainty uses `2,000` two-level
bootstrap replicates with seed `70071`: sample Audit patients with replacement,
retain all their examples, and sample the three training seeds with replacement.
The same patient and seed multiplicities are used for both sides of every contrast.
Report the percentile 95% interval `[CI_low, CI_high]`; no post-hoc interval or
metric selection is allowed.

The practical margin is fixed before training at:

```text
delta_practical = 0.005 absolute Recall@5.
```

This is the sole operational meaning of `materially`, `comparable`, and `≈`:

- **Proposed materially better than `C`** iff
  `Delta_C >= 0.005` and `CI_low > 0.000`.
- **`C` comparable to Proposed (`C ≈ Proposed`)** iff
  `CI_high <= 0.005`. This includes a control that is better than Proposed; the
  response-specific method has not shown a material advantage.
- **Inconclusive** iff neither rule holds. A broad interval is not evidence of a
  mechanism: Gate 01 returns
  `STOP_GATE01_INCONCLUSIVE_NO_MECHANISM_ADMISSION` and does not continue to
  rescue, retune, or open a new response definition.

The Proposed variant must additionally be non-inferior to `V1` on the primary
metric: the 95% interval for `Recall@5(Proposed) - Recall@5(V1)` must have
`CI_low > -0.005`. Failure is `STOP_PROPOSED_NOT_NONINFERIOR_TO_BASE`.

Gate 01 can pass only if all applicable killer contrasts against Proposed are
`materially better` in the first rule and the Base non-inferiority rule passes.
Any `C ≈ Proposed` result immediately terminates the response-specific mechanism:

| Comparable control | Frozen stop |
| --- | --- |
| `V3` Generic Future-State Auxiliary / Medication-Ablated Future | `STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE` |
| `V6` Monitoring-Mask-Only | `STOP_MONITORING_POLICY_SUFFICIENCY` |
| `V4`, `V5`, or `V2` | `STOP_RESPONSE_SPECIFIC_MECHANISM_CONTROL_SUFFICIENCY` |
| `V7` Generic KD | `STOP_GENERIC_KD_MECHANICS_SUFFICIENCY` |

No result may be relabeled `comparable` or `materially better` using a secondary
metric, subgroup, favorable seed, or post-hoc confidence interval.

## 10. Explicit no-rescue boundary

The following outcomes are terminal for the response-specific Idea and cannot be
rescued under Idea 007:

- `V3` or any medication-ablated future is comparable to Proposed;
- `V6` is comparable to Proposed;
- `V5` Response Shuffle is comparable to Proposed;
- `V4` Static Medication Response Prototype is comparable to Proposed;
- `V2` Base + richer pre-order physiology is comparable to Proposed;
- `V7` Generic KD is comparable when applicable;
- support is insufficient or materially concentrated;
- any student-path leakage is found;
- any unmatched support, recommendation sample entitlement, or differential
  recommendation reweighting is found;
- the Gate is statistically inconclusive under the frozen rule;
- Proposed is not non-inferior to Strict Pre-Order Base.

Forbidden rescue actions include a larger teacher, Transformer-to-Mamba/GNN
replacement, a different response window, extra modalities, subgroup mining,
post-hoc feature expansion, a second response definition, extra response masks,
favorable-seed selection, or a new split. Each would change the scientific
question or weaken the matched subtraction and therefore requires a new Idea and
new review.

## 11. Privacy, evidence, and execution boundary

This protocol stores no patient-level data, split membership, trajectories,
predictions, weights, or response outcomes. A future run may commit only
public-safe aggregate linkage/preflight and Gate decision records after the
corresponding gate has been authorized and audited. The current workflow creates
no runner, no freeze manifest containing private values, no result table, and no
training artifact.

The current audited design-state record is:

```text
Idea 007: created/admitted
Gate 01: design frozen and independently audited; not executed
Training: NOT AUTHORIZED
Response outcomes: not accessed
G3/G4, R0 Holdout, historical project test: untouched
```

The next owner is a future explicitly authorized execution workflow. No execution
owner is authorized by this document.
