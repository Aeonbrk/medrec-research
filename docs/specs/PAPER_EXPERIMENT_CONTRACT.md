# Paper Experiment Contract

Version: `1.0`
Status: `CURRENT PAPER-FACING EXPERIMENT CONTRACT`
Effective date: `2026-09-17`

This contract governs new paper-facing Medication Recommendation experiments. Historical `Reproduction Mode`, `Comparison Mode`, `Stage -1*`, and Gate records remain valid provenance for what they actually did, but they do not define new paper experiments.

The contract is intentionally small. A rule belongs here only if it prevents a concrete source of scientific ambiguity, unfairness, leakage, post-hoc freedom, or irreproducibility.

## 1. Evidence roles

Experiments have three evidence roles.

### Development

Development evidence is used to decide what to test next. It may use one seed, Train/Dev, bounded tuning, checkpoint selection, operating-point selection, matched controls, and diagnostics. It does not support final superiority, SOTA, or confirmatory claims.

### Paper candidate

A paper candidate has a substantially frozen scientific mechanism, a defensible closest-work distinction, credible competitive anchors, repeated development evidence, and stable benchmark/evaluator semantics. Candidate numbers are still not automatically final-paper confirmation.

### Final-table eligible

A result is final-table eligible only when all of the following hold:

- method identity, benchmark profile, split, information budget, evaluator, tuning procedure, and final seed set were frozen before final training/evaluation;
- all model and operating-point selection used Train/Dev only;
- all predeclared final runs and reportable failures are accounted for;
- configuration, selected checkpoint, prediction/evaluator identity, and aggregate output are traceable;
- no unresolved correctness issue remains.

`FINAL-TABLE ELIGIBLE` means a result may transparently appear in a paper table. It does **not** imply that the evaluation population is an untouched confirmatory population.

Every evaluation surface must declare one feedback status:

- `UNSEEN_FOR_PROJECT_DECISIONS`: no known result from the population influenced model, protocol, benchmark, or analysis choices;
- `HISTORICALLY_FEEDBACK_EXPOSED`: results from the population have influenced project decisions;
- `UNKNOWN_PENDING_AUDIT`: history is not yet established.

A historically exposed standard benchmark may still appear in a paper table, but it must not be described as independent confirmation. The primary confirmatory conclusion for a new method should be supported by at least one evaluation population that was not used to choose the method or protocol.

## 2. Prediction task and timing

The current scientific task is visit-level medication-set prediction:

```text
current visit diagnoses + current visit procedures
+ strictly previous visit diagnosis/procedure/medication history
-> current visit medication set
```

Current target medications and future visits are never inputs.

Before a benchmark is used for a prospective or point-in-time clinical claim, its profile must establish when current diagnosis/procedure features are known relative to the target medications. If within-visit timing cannot be established, use the narrower description `visit-level medication-set prediction conditioned on current clinical codes and prior longitudinal history` and do not imply admission-time prospective prescribing.

Prediction-time semantics are benchmark facts, not model-level assumptions.

## 3. Benchmark profiles

Each paper-facing benchmark profile must bind:

- cohort and patient-disjoint split;
- exact eligible-example definition and membership identity;
- input information budget and history construction;
- medication vocabulary and target mapping/projection;
- all data-derived assets and which split fitted them;
- evaluation feedback status;
- known patient/record overlap with other claimed confirmation populations, or `unknown` when not established.

Current surfaces have provisional roles:

- **MIMIC-III canonical-131**: canonical medication-space and literature interface. Direct numerical comparability still depends on cohort, split, input, selection, and evaluator semantics. Historical Test feedback must be audited before any confirmatory language.
- **MIMIC-IV native-173**: preferred dataset-native candidate for the second main benchmark. Its paper role depends on baseline feasibility and timing/feedback audits.
- **MIMIC-IV common-131**: harmonized compatibility surface. It is a projected task, not the full native MIMIC-IV medication-set task. Its changed target cardinality, projected-empty examples, and zero-support coordinates must remain explicit.

Do not make a benchmark primary merely because it is easier for existing code. Do not extend a published method to a new vocabulary merely by changing an output dimension when required scientific assets are missing.

## 4. Evaluator

The current evaluator contract is [`PAPER_EVALUATOR_SPEC.md`](PAPER_EVALUATOR_SPEC.md).

Primary endpoint: `patient-macro Jaccard`.

Secondary accuracy metrics: patient-macro F1 and patient-macro PRAUC/AP, plus visit-macro counterparts as supplementary context.

Safety/context reporting includes pooled predicted-pair DDI rate and predicted medication count. Lower DDI caused by under-prescription is not, by itself, evidence of safer treatment.

The exact sample eligibility, aggregation order, empty-set behavior, OOV/zero-support handling, continuous-score definition, and DDI edge cases are evaluator semantics and may not be changed after observing Test results.

## 5. Published-method identity

New paper experiments use one method identity, not separate active `Reproduction` and `Comparison` worlds.

Each external method receives a concise Method Card following [`../guides/PAPER_METHOD_CARD_TEMPLATE.md`](../guides/PAPER_METHOD_CARD_TEMPLATE.md). The card records source identity, scientific core, benchmark adaptation, training/selection rights, known paper/source discrepancies, and sanity evidence.

The governing principle is:

> Preserve the scientific method, not every accidental implementation detail.

Changes fall into three classes.

### Mechanical integration

Generally allowed when they preserve the represented computation: file/ID translation, vocabulary reindexing, padding/storage/device changes, common evaluator wiring, and Train-only reconstruction of statistics or graphs that the method already requires.

For an engineering rewrite claimed equivalent, run the smallest targeted input/output/update check that could detect a meaningful semantic change. Exact numerical equivalence is not required across genuinely different vocabularies or assets.

### Benchmark development choices

Learning rate, reasonable regularization, training horizon, validation checkpoint rule, early stopping, and decoder operating point may be selected on Train/Dev under the bounded policy below. These choices must be explicit and predeclared for the experiment; they do not automatically define a different scientific method.

### Scientific changes

Core objective, supervision, memory/update mechanism, medication representation, information availability, set/sequence factorization, external knowledge, or an optimization rewrite that materially changes training dynamics cannot be silently treated as the published method. Such a change needs equivalence evidence or an explicit variant identity.

## 6. Reference sanity

A baseline should demonstrate that the integrated path is not obviously degraded before expensive cross-benchmark use.

Numerical historical references are admissible as sanity checks only when dataset/split, input budget, sample eligibility, metric aggregation, and selection profile are sufficiently aligned. Otherwise, source-path and training-semantic checks take precedence and historical numbers are context only.

A large drop from a sufficiently aligned trusted reference triggers investigation. It is not a target that must be tuned back to before admission.

## 7. Bounded Dev tuning

Before screening a method's configurations, record the candidate list and stopping condition. Search continuation must not depend on the method's gap to the proposed model.

Default entitlement per main method/benchmark is:

- one source/default recipe;
- up to five bounded candidate recipes when a concrete reason exists;
- one tuning seed for initial screening;
- the best two candidates receive a second development seed;
- choose the frozen recipe by mean Dev primary score over those two seeds, with a predeclared deterministic tie-break.

Typical tunable dimensions are learning rate, one major regularization variable, one source-backed method weight, and a justified training horizon. Do not form a broad Cartesian sweep.

A training-horizon extension is allowed only under a predeclared non-convergence criterion and before final training. `The score is not high enough` is not such a criterion.

The proposed method must also use an explicit bounded recipe-selection budget after its architecture is frozen. Historical architecture-search effort is acknowledged rather than falsely claimed equal to baseline tuning effort.

## 8. Joint checkpoint and operating-point selection

Checkpoint and threshold/decoder selection are one joint Dev procedure.

For every predeclared validation checkpoint:

1. evaluate every predeclared operating point;
2. compute Dev patient-macro Jaccard;
3. retain the best operating point for that checkpoint;
4. select the checkpoint/operating-point pair with the highest Dev patient-macro Jaccard.

Tie-break, in order:

1. operating point closest to the predeclared method default;
2. fixed operating-point order;
3. earlier checkpoint.

Maximum training budget, validation times, and patience are frozen before the final training run. Methods do not need the same update count or the same number of validation checkpoints, but validation opportunities may not be added in response to an observed final-run trajectory.

For sigmoid multilabel methods, the default paper profile uses global thresholds `0.05, 0.10, ..., 0.95` plus any source-native global threshold not already on that grid. Per-drug thresholds are not allowed unless they are part of the studied method.

Structured/generative decoders may instead expose one scientifically natural operating-point dimension such as NULL, stopping, or cardinality bias. If none exists, use native decoding.

A fixed common threshold or native-threshold-only profile is not scientifically forbidden; it is simply a different evaluation profile. The project main comparison uses the Dev-selected profile above unless a frozen paper-candidate contract explicitly states otherwise.

## 9. Development and final seeds

Exploration defaults:

- initial mechanism/architecture screen: one seed;
- survivor stability check: three development seeds.

Before **a method's final training begins**, freeze its final seed count, exact seed set, configuration, budget, validation schedule, and operating-point procedure. Three final seeds are an acceptable minimum. Five are preferred when compute is cheap or when the method is the final method, closest comparator, strongest nominated comparator, or a central mechanism control.

Methods need not all have the same seed count, but the count and role must be disclosed and may not be chosen in response to final-run behavior.

### Failure handling

- recoverable interruption: resume or restart the same seed and same configuration;
- numerical divergence, OOM, or no valid checkpoint: keep the failure in the record; do not silently replace the seed;
- bug fix: change only the bug, then rerun every affected predeclared seed under the same frozen configuration.

Selective seed removal and `rerun until good` are prohibited.

## 10. Final confirmation and Test

`Test once` means one frozen confirmatory analysis phase, not literally one evaluator call.

Before entering that phase, freeze methods, configurations, final seeds, benchmark profiles, evaluator, selection procedure, reported subgroups/curves, and nominated formal comparisons.

A `strongest comparator` used for a predeclared paired claim is nominated **before Test** from Dev evidence and scientific role. It is not chosen after observing Test. If the paper later makes a formal claim against whichever baseline is Test-best, the analysis must account for that additional comparison/multiplicity.

During Final Confirmation, all predeclared methods/seeds may be evaluated in batches. Test results may narrow conclusions but may not trigger model, threshold, seed, or protocol changes within the same confirmation cycle.

If a Test-exposed bug is discovered:

- evaluator bug: recompute all affected methods consistently;
- method bug: fix only the bug and rerun all affected frozen seeds;
- split/leakage error: the affected confirmation is invalid.

Once Test has been seen, do not relabel a repaired evaluation as never exposed.

## 11. Statistical reporting

Main-table trainable methods report `mean ± sample SD` across their frozen final training seeds.

For a small predeclared set of central comparisons, use paired patient-cluster bootstrap on the same evaluation population:

- sample patients with replacement;
- retain all eligible visits for each sampled patient;
- use the identical resample for both methods;
- recompute the metric per seed;
- average across the frozen seed set;
- report the method difference and a 95% percentile interval.

`5000` resamples is the project default, not a universal publication rule.

Seed SD describes optimization/training variability. The patient-cluster interval describes patient-sampling variability conditional on the trained models. Neither replaces the other. A patient-bootstrap interval excluding zero does not, by itself, establish stability to training randomness.

If multiple formal significance claims are made, predeclare multiplicity handling; otherwise label intervals as nominal, comparison-specific uncertainty summaries.

## 12. Safety, cardinality, and efficiency

Main performance reporting includes Jaccard, F1, PRAUC/AP, pooled-pair DDI, and predicted medication count. Target medication count is a benchmark reference and need not be repeated for every method row.

The main table is an **accuracy-oriented Dev-Jaccard-selected operating-point comparison**. It does not represent each method's safety-optimal operating point.

For the final method and a small number of key comparators, add an accuracy-DDI operating curve using predeclared decoder points and show medication count. If comparable medication rankings exist, one fixed-cardinality diagnostic may be added to test whether a DDI advantage is mostly a recommendation-count effect.

Efficiency reporting includes trainable parameters, end-to-end inference latency, and a short training-cost summary. Structured solvers/assignment and data transfer required online are part of inference latency.

## 13. Architecture hypothesis testing

Architecture exploration remains narrow:

```text
one mechanism-bearing hypothesis
-> one real Train/Dev screen
-> strong matched control
-> survive / bounded redesign once / kill
```

Do not require all benchmark/baseline audits to finish before unrelated experiments. An experiment may start when the unresolved items that can change **that experiment's interpretation or execution** are resolved.

Examples:

- MIMIC-III SharedPool/DrugQuery stability requires the MIMIC-III task/split/evaluator/selection profile to be fixed; it does not require native-173 SSPNet feasibility.
- A baseline recovery run requires that baseline's source identity, Method Card, benchmark profile, and selection procedure to be fixed.
- A structured-set prototype requires its closest-work computational distinction and minimum model definition to be clear before expensive training.

## 14. Structured-set candidate

The current untested candidate should be framed, if pursued, as:

> Can explicit set-level competition, variable cardinality, and uniqueness in training/decoding improve medication-set prediction over independent-label objectives under the same clinical evidence?

Do not claim that independent-label models contain no medication dependence. Do not call unsupervised slots `clinical regimen roles`.

A first prototype should remain minimal: legal EHR evidence, medication-specific or shared proposals as appropriate, latent set elements, medication-or-NULL prediction, permutation-invariant matching, and uniqueness-aware decoding. Do not add DDI repair, retrieval, MoE, FiLM, or multi-stage refinement in the first screen.

A 2×2 evidence-by-decoder experiment is preferred **only if** the evidence mechanism and structured-set mechanism can be independently manipulated while keeping information access and training semantics interpretable. If that factorization is not valid, use matched controls that isolate the main mechanism and narrow the claim. A 2×2 layout is not a requirement.

When a valid 2×2 is used, inspect the interaction `(D-B) - (C-A)` before claiming synergy; four pairwise deltas alone do not establish an interaction.

If structured/set prediction survives, closest-work clarification for SSPNet or any closer primary-source method is required before paper-candidate freeze. A broken repository is not sufficient reason to ignore the closest scientific comparator.

## 15. Research lifecycle

Human-facing research phases are descriptive, not opaque stage numbers:

1. **Credible Reference Setup** — define the prediction problem, evaluator, benchmark roles, baseline identities, and closest-work boundary needed by the next experiments.
2. **Architecture Hypothesis Testing** — test one computation change with matched Train/Dev controls; survive, redesign once, or kill.
3. **Paper Candidate Freeze** — freeze the exact claim, methods, benchmarks, tuning/selection policy, seeds, and final analyses.
4. **Final Confirmation** — execute the frozen non-feedback evaluation and produce paper-ready evidence or a narrower conclusion.

Historical `Stage -1*` and Gate labels remain provenance only.

## 16. Current bounded audits

The following audits are current decision dependencies, not a global training gate:

- **Prediction-time semantics**: establish what current diagnosis/procedure information supports in the claim language.
- **Evaluation feedback history**: establish MIMIC-III/MIMIC-IV Test exposure and whether claimed confirmation populations are known to overlap at patient/record level; unknown overlap is reported as unknown rather than inferred away.
- **MIMIC-IV native-173 baseline feasibility**: for relevant external methods, distinguish mechanical output-space adaptation from missing scientific assets or a method rewrite.

Resolve only the audit items that can change the experiment being launched.

## 17. Current MICA interpretation

The existing MICA evidence supports this statement only:

> In the tested single-seed Train/Dev comparisons, medication-specific evidence selection moved performance in the same favorable accuracy direction on MIMIC-III and MIMIC-IV surfaces; stability across training randomness is not yet established.

Current MICA numbers are development evidence, not paper-ready superiority, universal safety improvement, or proof of calibration.

After the MIMIC-III evaluator/selection profile is frozen, a three-seed SharedPool-vs-DrugQuery stability experiment is an appropriate architecture decision experiment. It does not need to wait for unrelated native-173 or SSPNet audits.

## 18. Resource policy

Up to eight RTX 3090-class GPUs may be used concurrently. GPU occupancy is not a research objective. Prefer parallel seeds, matched controls, independent baseline recovery, or distinct architecture hypotheses over parameter fishing. Leaving a GPU idle is better than launching an experiment with unresolved interpretation.
