# Current research state — 2026-09-19

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current position

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Human-facing phase: EBRA_REGIMEN_ASSIGNMENT_SCREEN_DESIGN_FROZEN_IMPLEMENTATION_PENDING
Paper Experiment Contract: v1.0 + v1.1 + v1.2 + v1.3 + v1.4 amendments CURRENT
Paper claim: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Historical `Stage -1*`, Gate, Reproduction Mode, and Comparison Mode names remain provenance only. New paper-facing work is governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_4.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`

The active execution-routing decision is:

- `research/memory/decisions/2026-09-17-evidence-first-execution-sequencing.md`

## Development philosophy

The proposed method may receive substantially greater Train/Dev research effort than external baselines. Equal cumulative architecture/HPO budgets are not a fairness requirement.

Fairness requires that a competitor is not weakened by our execution choices: trustworthy method identity, required assets, legal information budget, reasonable training horizon, declared Dev-only checkpoint/operating-point selection, and source-informed investigation of obvious failures. Baseline tuning is an anti-underoptimization safeguard, not a symmetric-search requirement.

Central ablations and matched controls also need reasonable Dev selection when mechanically reusing the full model's recipe would materially disadvantage them.

For new project-owned initial DEVELOPMENT screens, the canonical RNG convention is inherited from MoleRec: `torch=1203`, CUDA PyTorch `1203`, Python `random=1203`, and NumPy `2048`. Internal matched controls share that convention. External published baselines instead preserve their source-native seed policy when available. A survivor must still expand to a predeclared multi-seed stability experiment; the canonical seed is not stability evidence.

As of contract v1.4, new project-owned early DEVELOPMENT architecture/mechanism screens default to **15 complete epochs**, not early stopping. A decisive matched comparison is interpretable only when every arm selects Epoch 10 or earlier. Selection in Epochs 11–15 triggers an exact unchanged extension of that pair to 30 epochs; the existing v1.3 26–30 -> 60 censoring safeguard remains active for such extensions. This change is prospective and does not rewrite historical 30/60-epoch evidence.

## Valid development evidence

Medication-specific evidence selection remains the strongest surviving mechanism.

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV native | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Current interpretation:

> In the tested Train/Dev comparisons, medication-specific evidence selection moved accuracy in the same favorable direction on MIMIC-III and MIMIC-IV surfaces. Two new matched MIMIC-III seed pairs reproduce the favorable Jaccard/F1/PRAUC and lower-DDI direction; medication cardinality is mixed. This remains development evidence, not a final superiority or safety claim.

These results are `DEVELOPMENT` evidence. They are not final-table superiority, SOTA, universal safety improvement, or a calibration claim. The fixed-131/generalized MICA implementation passed exact no-training equivalence on the 131-medication path.

MICA remains a possible building block and mechanism control, not a mandatory backbone or permission gate for a distinct architecture.

### Evidence-access architecture portfolio (2026-09-18)

An eight-lane 60-epoch portfolio screen on `mimic-iii-canonical-131-paper-dev-v1` (revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3`, 1,295,367 parameters per variant, zero Test access) evaluated four orthogonal evidence-access bottlenecks against matched controls:

- **Code-level evidence resolution (`resolution_code`)**: Medication-specific attention directly over fine clinical code tokens beats within-visit pooling (`resolution_visit`) by $\Delta J = +0.011536$ (0.546626 vs 0.535091), with uniform gains in F1 ($+0.0102$), PR-AUC ($+0.0078$), and lower DDI rate ($-0.005589$). Verdict: `MECHANISM_SIGNAL`.
- **Iterative evidence re-access (`depth_reread`)**: Re-querying clinical evidence with updated medication states beats state-only refinement (`depth_state`) at identical depth and parameter count by $\Delta J = +0.004144$ (0.551259 vs 0.547115), achieving peak portfolio Dev Jaccard with favorable safety ($\Delta \text{DDI} = -0.000731$). Verdict: `MECHANISM_SIGNAL`.
- **Prediction granularity (`prediction_local`)**: Local potential scoring per token delivers strong Jaccard gain ($\Delta J = +0.012976$ over `prediction_aggregate`), but violates the frozen DDI guardrail ($\Delta \text{DDI} = +0.003843 > +0.0020$). Verdict: `SIGNAL_WITH_SUPPORTING_METRIC_COST`.
- **Pre-temporal medication state (`temporal_med`)**: Yields $\Delta J = +0.000447$ over `temporal_shared`, failing the $+0.0020$ threshold. Verdict: `KILL_NO_MATERIAL_SIGNAL`.

Portfolio routing: `MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION`. Per the frozen contract, no compound model is automatically scheduled without prior scientific arbitration and primary-source closest-work audits.

### Iterative evidence survivor screen (2026-09-18)

An eight-lane 60-epoch survivor screen on `mimic-iii-canonical-131-paper-dev-v1` at revision `82fb054abefe3a4b6560c9a3a2fd8640a32bc944` (1,295,367 parameters per variant, zero Test access) evaluated:

1. **Final-architecture resolution attribution (`reread_code` vs `reread_visit`)**: Code-level evidence resolution remains decisively supported inside the multi-hop re-reading computation graph: $\Delta J = +0.014651$ (0.551259 vs 0.536608), $\Delta \text{F1} = +0.013301$, $\Delta \text{PRAUC} = +0.011395$, $\Delta \text{DDI} = -0.002295$. Verdict: `CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE`.
2. **Depth stability across prospective seeds (`depth_reread` vs `depth_state`)**: Evaluated across 4 conditions (`canonical` inherited from portfolio, plus prospective offsets `stability_1`, `stability_2`, `stability_3`). Results: `canonical` $\Delta J = +0.004144$; `stability_1` $\Delta J = -0.000650$; `stability_2` $\Delta J = +0.001365$; `stability_3` $\Delta J = +0.003033$. Positive conditions: 3/4; material ($> +0.002$) conditions: 2/4; mean $\Delta J = +0.001973$ (below $+0.004$ threshold); mean $\Delta \text{DDI} = +0.002130$ (violating guardrail). Verdict: `UNSTABLE_DEPTH_REREAD`.

Survivor screen routing: `RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE`. Iterative re-reading is not promoted to Paper Candidate review; the project returns to architecture search.

### Relational evidence architecture screen (2026-09-18)

An eight-lane 60-epoch architecture screen on `mimic-iii-canonical-131-paper-dev-v1` at revision `18ae6c89dcb6ca52137e18ebeabe36bd5a303002` (zero Test access) evaluated:

1. **Fine-code stability across prospective random seeds**: Medication-specific fine-code selection is strictly stable across 4 conditions (`canonical`, `stability_1`, `stability_2`, `stability_3`), with 4/4 positive conditions, 4/4 conditions $> +0.010$ Jaccard gain, mean $\Delta J = +0.011734$, and favorable safety (mean $\Delta \text{DDI} = -0.001640$). Verdict: `STABLE_FINE_CODE_ACCESS`. Fine-code access is frozen as a verified foundational component.
2. **Relational evidence hypothesis**: Candidate-conditioned multiplicative conjunction ($u_D \odot u_P$, $u_D \odot u_H$, $u_P \odot u_H$) outperforms matched additive/unary composition at 1,427,080 parameters by $\Delta J = +0.004105$ (0.542982 vs 0.538877), $\Delta \text{F1} = +0.003371$, $\Delta \text{PRAUC} = +0.001131$, with a substantial reduction in DDI rate ($\Delta \text{DDI} = -0.005341$). Verdict: `RELATIONAL_EVIDENCE_SIGNAL`.

Screen routing: `PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN`. Relational cross-type evidence conjunction qualifies for multi-seed stability evaluation.

### Final relational architecture search & early termination (2026-09-19)

An eight-lane 30-epoch architecture search on `mimic-iii-canonical-131-paper-dev-v1` at revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00` (zero Test access) evaluated whether forming non-separable cross-type code pairs ($O(N_D \times N_P)$) before pooling overcomes the factorized formulation of relational-v1.

Five upstream lanes completed all 30 planned epochs:

1. `foundation_code`: Ep 5 / 0.30, Dev Jaccard = **0.546626** (exact numerical reproduction of prior `resolution_code`, difference $< 10^{-9}$).
2. `summary_add`: Ep 5 / 0.35, Dev Jaccard = **0.549611**, F1 = 0.7008, PRAUC = 0.7958, DDI = 0.0708.
3. `summary_mul`: Ep 5 / 0.35, Dev Jaccard = **0.546079**, F1 = 0.6978, PRAUC = 0.7944, DDI = 0.0698.
4. `factorized_pair`: Ep 5 / 0.30, Dev Jaccard = **0.544349**, F1 = 0.6966, PRAUC = 0.7927, DDI = 0.0720.
5. `nonseparable_pair`: Ep 5 / 0.35, Dev Jaccard = **0.543162**, F1 = 0.6949, PRAUC = 0.7926, DDI = 0.0708.

Completed matched comparisons:

- **Pair A (`summary_operator`)**: Multiplicative conjunction underperforms additive composition ($\Delta J = -0.003532$, verdict `KILL_NO_MATERIAL_SIGNAL`).
- **Pair B (`pair_granularity`)**: Non-separable pair attention does not improve over factorized attention ($\Delta J = -0.001187$, verdict `KILL_NO_MATERIAL_SIGNAL`). Both pair-level formulations underperform the single-code baseline `foundation_code` (0.546626).

Three downstream lanes (`joint_competition_pair`, `untyped_edge_pair`, `temporal_edge_pair`) built on the failed non-separable pair formulation were terminated early for efficiency and marked `TRUNCATED_NON_INTERPRETABLE` (partial metrics are descriptive execution state only, not valid scientific evidence).

Key architectural takeaway: `summary_add` achieved the highest Dev Jaccard (0.549611, $+0.002984$ vs foundation). Because its additive slots are a linear rotation of $(u_D, u_P, u_H)$, it is not relational reasoning; rather, it indicates that providing distinct, un-entangled representation channels for each clinical modality is effective. It is classified as `BEST_COMPLETED_ARCHITECTURE_CLUE` pending capacity-matched isolation.

Screen routing: `TERMINATE_RELATIONAL_PAIR_REFINEMENT_REFORMULATE_AROUND_MODALITY_SEPARATED_FINE_CODE_EVIDENCE`.

### MHEF normalization-domain architecture screen (2026-09-19)

An eight-lane 30-epoch architecture screen on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `4584f8a0d080f4300f9ba5778da08f7f82cdc805` (1,476,874 parameters per variant across all eight lanes, zero Test access) tested whether candidate-specific fine-code evidence should decouple diagnosis ($D$), procedure ($P$), and historical medication ($H$) evidence from a shared softmax into independent normalization budgets before medication-level prediction.

All eight physical RTX 3090 GPU lanes completed all 30 planned epochs. All lanes selected their best checkpoint at Epoch 5 (`safe_selected_epoch_max = 25 >= 5`, no horizon censoring):

1. `mhef_independent_add`: Ep 5 / 0.30, Dev Jaccard = **0.549397**, F1 = 0.700657, PRAUC = 0.794860, DDI = 0.072165.
2. `coupled_budget_add` (matched normalization control): Ep 5 / 0.30, Dev Jaccard = **0.547986**, F1 = 0.699394, PRAUC = 0.793084, DDI = 0.071378.
3. `wide_global_add` (matched capacity absorption control): Ep 5 / 0.30, Dev Jaccard = **0.549980**, F1 = 0.701313, PRAUC = 0.794769, DDI = 0.072489.
4. `mhef_independent_concat`: Ep 5 / 0.30, Dev Jaccard = **0.545593**, F1 = 0.697693, PRAUC = 0.794941, DDI = 0.073200.
5. `coupled_budget_concat`: Ep 5 / 0.35, Dev Jaccard = **0.545500**, F1 = 0.697330, PRAUC = 0.793394, DDI = 0.070904.
6. `private_only_add`: Ep 5 / 0.30, Dev Jaccard = **0.547128**, F1 = 0.698678, PRAUC = 0.792935, DDI = 0.072477.
7. `hash_partition_a_add`: Ep 5 / 0.35, Dev Jaccard = **0.544909**, F1 = 0.696626, PRAUC = 0.793541, DDI = 0.071163.
8. `hash_partition_b_add`: Ep 5 / 0.35, Dev Jaccard = **0.544926**, F1 = 0.696638, PRAUC = 0.793559, DDI = 0.071163.

Key matched comparison outcomes:

- **Primary normalization test (`normalization_add`)**: Decoupled normalization yields $\Delta J = +0.001410$ (+0.141 pp) over the coupled budget, failing the $+0.0030$ material signal threshold (`KILL_NO_MATERIAL_SIGNAL`). Under concat fusion, the delta drops to $\Delta J = +0.000093$ (+0.009 pp).
- **Capacity absorption (`capacity_wide_global`)**: Four identical global FineCode slots with the same head capacity (`wide_global_add`) reach Dev Jaccard = **0.549980**, exceeding `mhef_independent_add` by $+0.000583$. The modest lift over baseline is entirely absorbed by multi-head capacity rather than heterogeneous normalization decoupling.
- **Partition controls (`semantic_partition_a/b`)**: Nonsemantic hash partitions degrade performance to $0.5449$, confirming that randomly splitting tokens destroys semantic alignment, but this does not salvage the primary hypothesis.
- **Absolute position**: `mhef_independent_add` (0.549397) does not beat prior best `summary_add` (0.549611, $\Delta J = -0.000214$).

Screen routing: `KILL_MHEF_NORMALIZATION_HYPOTHESIS`. No multi-seed stability or MIMIC-IV replication is authorized.

### MSED evidence-distribution architecture screen (2026-09-19)

An eight-lane 30-epoch architecture screen on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `e54d3d5a2a5145d14beadb109d574ad82efdae9e` (1,363,465 parameters across all six MSED variants, 30 complete epochs, zero Test access) evaluated whether predicting medications from the empirical distribution shape of longitudinal FineCode support potentials carries decision value beyond a single scalar point statistic (`logmeanexp`).

All eight physical RTX 3090 GPU lanes completed 30 planned epochs without early stopping. All lanes selected best Dev checkpoints between Epochs 3 and 8 (`safe_selected_epoch_max = 25 >= 8`, zero horizon censoring):

1. `msed_ecf_global` (Rank-1 distribution candidate): Ep 8 / 0.35, Dev Jaccard = **0.546806**, F1 = 0.698507, PRAUC = 0.793325, DDI = 0.076335.
2. `point_lme_global` (decisive point-LME matched control): Ep 8 / 0.35, Dev Jaccard = **0.546180**, F1 = 0.698087, PRAUC = 0.792862, DDI = 0.076761.
3. `point_mean_global` (mean point summary control): Ep 7 / 0.35, Dev Jaccard = **0.546378**, F1 = 0.698442, PRAUC = 0.791671, DDI = 0.077119.
4. `point_max_global` (max point summary control): Ep 8 / 0.35, Dev Jaccard = **0.546652**, F1 = 0.698253, PRAUC = 0.793283, DDI = 0.074867.
5. `msed_ecf_only` (distribution without global context): Ep 8 / 0.35, Dev Jaccard = **0.530734**, F1 = 0.684700, PRAUC = 0.777805, DDI = 0.071420.
6. `point_lme_only` (matched control for lane 4): Ep 5 / 0.30, Dev Jaccard = **0.534433**, F1 = 0.687944, PRAUC = 0.780670, DDI = 0.076338.
7. `prediction_local_anchor` (historical local-LME anchor): Ep 3 / 0.35, Dev Jaccard = **0.548911**, F1 = 0.700462, PRAUC = 0.794832, DDI = 0.075148.
8. `foundation_code_anchor` (historical FineCode anchor): Ep 5 / 0.30, Dev Jaccard = **0.546626**, F1 = 0.698386, PRAUC = 0.792678, DDI = 0.071069.

Key matched comparison outcomes:

- **Primary distribution test (`distribution_beyond_lme_global`)**: Representing the empirical support distribution via characteristic spectrum yields $\Delta J = +0.000626$ (+0.063 pp) over scalar LME, failing the $+0.0020$ material signal threshold (`KILL_NO_MATERIAL_SIGNAL`).
- **Distribution in isolation (`distribution_beyond_lme_only`)**: Without global FineCode context, characteristic spectrum distribution encoding performs worse than scalar LME ($\Delta J = -0.003699$, -0.370 pp).
- **Point summary controls**: `msed_ecf_global` does not materially outperform simple linear mean ($\Delta J = +0.000428$) or hard max ($\Delta J = +0.000154$).
- **Anchor integrity**: Both historical anchors reproduce with exactly 0.0 absolute difference across all five metrics.
- **Absolute position**: `msed_ecf_global` (0.546806) underperforms prior best control `wide_global_add` (0.549980, $\Delta J = -0.003174$), prior best architecture `summary_add` (0.549611, $\Delta J = -0.002805$), and `prediction_local_anchor` (0.548911, $\Delta J = -0.002105$).

Screen routing: `KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`. No multi-seed stability or MIMIC-IV replication is authorized. Decision note: `research/memory/decisions/2026-09-19-msed-evidence-distribution-screen-verdict.md`.

### MEMB mutual-binding family screen (2026-09-19)

An eight-lane 30-epoch architecture screen on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2` (1,295,367 parameters across all eight variants, 30 complete epochs, zero Test access) evaluated whether evidence should be penalized by its cross-medication commonness ($c_i = \text{logsumexp}_n S[n,i] - \log(M)$) before evidence aggregation across both global FineCode and PredictionLocal reads.

All eight physical RTX 3090 GPU lanes completed all 30 planned epochs without early stopping. All lanes selected best Dev checkpoints between Epochs 3 and 7 (`safe_selected_epoch_max = 25 >= 7`, zero horizon censoring):

1. `mutual_code` (scale-2 mutual FineCode candidate): Ep 7 / 0.35, Dev Jaccard = **0.542110**, F1 = 0.694402, PRAUC = 0.785345, DDI = 0.076355.
2. `scale2_code` (scale-2 sharpening control): Ep 5 / 0.30, Dev Jaccard = **0.540015**, F1 = 0.693071, PRAUC = 0.785565, DDI = 0.071793.
3. `specificity_code` (scale-1 commonness candidate): Ep 5 / 0.30, Dev Jaccard = **0.547125**, F1 = 0.698713, PRAUC = 0.793489, DDI = 0.071194.
4. `foundation_code_anchor` (exact scale-1 control + historical anchor): Ep 5 / 0.30, Dev Jaccard = **0.546626**, F1 = 0.698386, PRAUC = 0.792678, DDI = 0.071069.
5. `mutual_local` (scale-2 mutual PredictionLocal candidate): Ep 5 / 0.35, Dev Jaccard = **0.547092**, F1 = 0.698671, PRAUC = 0.794902, DDI = 0.067738.
6. `scale2_local` (scale-2 local sharpening control): Ep 5 / 0.35, Dev Jaccard = **0.548099**, F1 = 0.699482, PRAUC = 0.795203, DDI = 0.068090.
7. `specificity_local` (scale-1 local-commonness candidate): Ep 5 / 0.30, Dev Jaccard = **0.548141**, F1 = 0.699645, PRAUC = 0.795108, DDI = 0.070112.
8. `prediction_local_anchor` (exact scale-1 control + historical anchor): Ep 3 / 0.35, Dev Jaccard = **0.548911**, F1 = 0.700462, PRAUC = 0.794832, DDI = 0.075148.

Key matched comparison outcomes:

- **Code commonness scale 1 (`specificity_code - foundation_code_anchor`)**: Subtracting commonness without score sharpening yields $\Delta J = +0.000499$ (+0.050 pp), failing the $+0.0020$ threshold (`KILL_NO_MATERIAL_SIGNAL`).
- **Code commonness scale 2 (`mutual_code - scale2_code`)**: While $\Delta J = +0.002095$, this is an artifact of partial recovery from the severe degradation caused by scale-2 sharpening (`scale2_code` loses $-0.006611$ relative to base foundation); both scale-2 lanes underperform `foundation_code_anchor` ($0.546626$), and `mutual_code` incurs a large $+0.004562$ DDI safety cost (`WEAK_STOP`).
- **Local commonness scale 1 (`specificity_local - prediction_local_anchor`)**: $\Delta J = -0.000770$ (-0.077 pp, `KILL_NO_MATERIAL_SIGNAL`). DDI drops by $-0.005036$, failing the pre-registered Pareto gate of $\Delta \text{DDI} \le -0.010$.
- **Local commonness scale 2 (`mutual_local - scale2_local`)**: $\Delta J = -0.001007$ (-0.101 pp, `KILL_NO_MATERIAL_SIGNAL`).
- **Anchor integrity**: Both historical anchors reproduce with exactly 0.0 absolute difference across all five metrics.

Screen routing: `KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`. No multi-seed stability or MIMIC-IV replication is authorized. Decision note: `research/memory/decisions/2026-09-19-memb-mutual-binding-screen-verdict.md`.

### Terminated mechanism screens

- **Medication–Evidence Mutual Binding (MEMB)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2` (1,295,367 parameters across all eight lanes, zero added parameters, 30 complete epochs, zero Test access). Tested whether penalizing evidence common to competing medication identities via commonness penalty $c_i = \text{logsumexp}_n S[n,i] - \log(M)$ before aggregation improves medication decisions across global FineCode and PredictionLocal reads at two score scales. Result: scale-1 commonness deltas $\Delta J = +0.000499$ (code) and $\Delta J = -0.000770$ (local) fail the $+0.0020$ material signal threshold (`KILL_NO_MATERIAL_SIGNAL`); scale-2 mutual code gain ($\Delta J = +0.002095$, DDI $+0.004562$) merely partially recovers from the $-0.006611$ damage caused by score sharpening, with both scale-2 variants trailing base foundation ($0.546626$); local mutual matching underperforms its control ($\Delta J = -0.001007$); Pareto DDI reduction ($-0.0050$) falls short of the $-0.010$ gate. Falsified and terminated per frozen decision boundary (`KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`); no multi-seed or MIMIC-IV evaluation scheduled. Decision note: `research/memory/decisions/2026-09-19-memb-mutual-binding-screen-verdict.md`.

- **Medication-Specific Evidence Distribution (MSED)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `e54d3d5a2a5145d14beadb109d574ad82efdae9e` (1,363,465 parameters across all six MSED variants, 30 complete epochs, zero Test access). Tested whether representing the empirical distribution shape of medication-specific FineCode support potentials via an empirical characteristic spectrum carries decision value beyond a single scalar `logmeanexp` point statistic. Result: primary comparison delta $\Delta J = +0.000626$ fails the $+0.0020$ threshold (`KILL_NO_MATERIAL_SIGNAL`); in isolation without global context, distribution spectrum underperforms scalar LME by $\Delta J = -0.003699$; candidate trails prior best control `wide_global_add` (0.549980 vs 0.546806, $\Delta J = -0.003174$). Falsified and terminated per frozen decision boundary (`KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`); no multi-seed or MIMIC-IV evaluation scheduled. Decision note: `research/memory/decisions/2026-09-19-msed-evidence-distribution-screen-verdict.md`.

- **Medication-Conditioned Heterogeneous Evidence Factorization (MHEF)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` at frozen revision `4584f8a0d080f4300f9ba5778da08f7f82cdc805` (1,476,874 parameters across all 8 variants, 30 complete epochs, zero Test access). Tested whether decoupling diagnosis, procedure, and history evidence into independent normalization budgets outperforms a shared zero-sum budget. Result: primary comparison delta $\Delta J = +0.001410$ fails the $+0.0030$ threshold (`KILL_NO_MATERIAL_SIGNAL`), concat delta is $+0.000093$, and the gain is entirely absorbed by wide global multi-head capacity (`wide_global_add` $J = 0.549980$ vs candidate $0.549397$). Falsified and terminated per frozen decision boundary (`KILL_MHEF_NORMALIZATION_HYPOTHESIS`); no multi-seed or MIMIC-IV evaluation scheduled. Decision note: `research/memory/decisions/2026-09-19-mhef-normalization-screen-verdict.md`.

- **Dense Non-Separable Clinical Code Pairs (`nonseparable_pair`)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` at revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00` (1,511,304 parameters, 30 complete epochs, zero Test access). Tested whether scoring explicit pairwise code interactions before pooling improves over factorized pair attention. Result: $\Delta J = -0.001187$ (nonseparable_pair 0.543162 vs factorized_pair 0.544349), and both underperform the single-code baseline `foundation_code` (0.546626). Combinatorial cross-code pairs dilute medication-conditioned evidence with uninformative co-occurrences while multiplying memory from 1.1GB to 6.4GB–14.3GB. Falsified and terminated per frozen decision boundary (`KILL_NO_MATERIAL_SIGNAL`); downstream pair refinements truncated. Decision note: `research/memory/decisions/2026-09-19-final-relational-architecture-early-termination.md`.

- **Iterative Evidence Depth Re-Reading (`depth_reread`)**: Evaluated across a 4-condition stability screen on `mimic-iii-canonical-131-paper-dev-v1` at revision `82fb054abefe3a4b6560c9a3a2fd8640a32bc944` (60 complete epochs per lane, 1,295,367 parameters in all variants, zero Test access). While the canonical seed showed a $+0.004144$ gain, prospective seeds failed the strict stability criteria (mean $\Delta J = +0.001973$, 1 of 4 conditions negative at $\Delta J = -0.000650$, only 2 of 4 conditions $> +0.0020$, and mean $\Delta \text{DDI} = +0.002130$ violating safety guardrail). Terminated per frozen decision rule (`RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE`); no cherry-picked seeds or post-hoc rescue authorized. Decision note: `research/memory/decisions/2026-09-18-iterative-evidence-survivor-screen.md`.
- **Drug-Conditioned Precedent Memory (DCPM)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seed `20260921`, 60 complete epochs, 1,079,428 parameters in both arms, zero Test access). Tested whether candidate-specific query attention over cross-patient Train precedents improves prediction over a shared patient query. Result: $\Delta J = -0.001403$ (DCPM 0.542203 vs SharedPrecedent control 0.543606), $\Delta \text{DDI} = +0.002181$. Falsified and terminated per the frozen decision boundary (`KILL_DCPM_MECHANISM`); no post-hoc tuning or re-test authorized. Decision note: `research/memory/decisions/2026-09-18-dcpm-mechanism-screen-falsification.md`.
- **Route-Factored Medication Recommendation (RouteFact)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seed `20260922`, 60 complete epochs, 914,497 parameters in both arms, source revision `8eee27ad88b63990cc8f1c5355b4a47bd84c7923`, zero Test access). Tested whether forcing medication prediction through a noisy-OR over Train-supported multi-hot administration routes improves prediction over direct medication prediction with identical auxiliary route supervision. Result: $\Delta J = -0.008252$ (RouteFact 0.534931 vs RouteAux control 0.543183), $\Delta \text{F1} = -0.006919$, $\Delta \text{PR-AUC} = -0.005145$, $\Delta \text{DDI} = -0.001539$, $\Delta \text{AvgMed} = +0.115149$. Falsified and terminated per the frozen decision boundary (`KILL_ROUTEFACT_MECHANISM`); no post-hoc tuning, taxonomy merging, loss sweeps, or re-test authorized. Decision note: `research/memory/decisions/2026-09-18-routefact-mechanism-screen-falsification.md`.
- **Exact-Cardinality Regimen Choice (ECRC)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seeds `20260923` and `20260924`, 60 complete epochs across 6 lanes, 437,571 parameters in all four variants, source revision `c668a8e4a194c92a8933068e8ff99991d014c185`, zero Test access). Tested whether regimen cardinality acts as an informative decision context that changes named-medication preference utilities ($u_m(x, K)$) under exact fixed-cardinality and BCE formulations. Result: mean exact oracle-K $\Delta J = +0.000341$ (+0.034%, failing the $+0.004$ gate), mean exact predicted-K $\Delta J = -0.000491$ (negative deployable value), mean candidate Jaccard $0.531769$ (below the $0.537316$ floor). Falsified and terminated per the frozen decision boundary (`KILL_ECRC_CHOICE_MECHANISM`); no size-head tuning, rank sweeps, or re-tests authorized. Decision note: `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-verdict.md`.
- **Clinical Concept Trajectory Memory (CCTM)**: Evaluated via Train-only data supportability audit on `mimic-iii-canonical-131-paper-dev-v1` at source revision `fbdcdafdf93aa4d14fa0cea2d19039ff7b02c488` (4,233 Train patients, 10,489 visits, 6,256 history-bearing prediction events, zero Dev/Test access). Tested whether repeated typed clinical concepts are sufficiently dense across prediction events to justify an addressable concept-trajectory evidence memory. Result: all-history coverage 47.6% (pass), non-med coverage 37.4% (pass), events with $\ge 3$ recurrent D/P trajectories 36.5% (fail, threshold $\ge 50\%$), events with $\ge 5$ recurrent D/P/M trajectories 40.6% (fail, threshold $\ge 50\%$). Falsified and terminated per the frozen decision boundary (`KILL_CCTM_SUPPORTABILITY`); the median history-bearing event has zero recurrent trajectories. Decision note: `research/memory/decisions/2026-09-18-cctm-trajectory-support-falsification.md`.
- **Pre-Temporal Medication State (MedTemporal)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` at revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3` (canonical seed, 60 complete epochs, 1,295,367 parameters, zero Test access). Tested whether candidate medication identity entering before longitudinal GRU compression improves prediction over a shared longitudinal representation when explicit medication persistence features are provided. Result: $\Delta J = +0.000447$ (temporal_med 0.544932 vs temporal_shared control 0.544485), failing the $+0.002$ threshold. Terminated per the frozen decision rule (`KILL_NO_MATERIAL_SIGNAL`). Decision note: `research/memory/decisions/2026-09-18-evidence-access-portfolio-screen.md`.

## Benchmark strategy

Default paper routing remains:

- **MIMIC-III canonical-131**: main literature-facing comparison surface.
- **MIMIC-IV harmonized/common-131**: default main MIMIC-IV literature-facing comparison surface, pending canonical-lineage identity audit.
- **MIMIC-IV native-173**: broader-target validation surface.

`Literature-facing` does not mean identical benchmark identity. Equal medication count does not establish equal cohort, preprocessing, split, eligibility, input semantics, or evaluator.

Before Paper Candidate Freeze, benchmark roles may change only for structural reasons such as faithful-baseline feasibility, missing scientific assets, target-space relevance, or the final mechanism's dependence on long-tail/cardinality structure. They may not change because one observed surface is easier to win.

The harmonized-131 audit is now split into:

- **run-critical checks now**: exact coordinate identity, target/DDI alignment, projection semantics, zero-support handling, and empty-target/eligibility rules;
- **paper-claim checks asynchronously**: how far this surface actually matches named literature lineages and what terminology is defensible.

MIV harmonized131 and native173 are target-space views of the same underlying MIMIC-IV population, not independent datasets. Native173 with only internal controls supports an internal broader-target/mechanism claim; competitive superiority there requires at least one credible external comparator relevant to the claim.

## Competitive baseline fidelity state

Temporary project-side MoleRec, GAMENet, and RETAIN outputs from the former Stage -1G path remain diagnostic only and must not support method ranking or paper superiority claims. The current ARMR lane is separate and source-pinned.

MoleRec remains the first recovery priority. The released source-native training lane is still running and has no terminal artifact; because that entrypoint uses its own source split, partial or source-split values cannot enter the frozen paper-profile table. A separate source-faithful adapter now binds the canonical MIMIC-III profile: its one-epoch smoke completed as non-evidence with no Test access, and its 50-epoch formal lane is running detached under the same pinned source and environment. Until the formal lane reaches a terminal artifact and independent audit, its partial values remain excluded.

- ARMR current-profile formal recovery is complete and passed an independent integrity audit. It is a credible DEVELOPMENT external anchor, not a Paper Candidate or final superiority claim;
- promote SSPNet when structured/set prediction becomes the active hypothesis, SSPNet is confirmed as the closest relevant comparator, and a trustworthy execution path exists. Bounded probes now reach finite forward and one-patient source training/evaluation after explicit mechanical edge-case isolation; they remain non-evidence and the frozen-profile adapter still requires independent source-fidelity review.
- otherwise keep SSPNet as a bounded source/CPU recovery task while the closest-work distinction remains unresolved.

SafeDrug rises in priority only if safety/molecular claims become central. GAMENet, RETAIN, and HypeMed are added only when they fill a distinct scientific role.

Architecture work does not wait for baseline completion, but Paper Candidate Freeze requires credible external positioning.

## Architecture status

### Terminated screen: ECRC cardinality context (2026-09-18)

The bounded DEVELOPMENT screen for **cardinality-conditioned named-medication choice** (ECRC) completed all 60 epochs across 6 lanes on physical GPUs 0–5 on 319.

Result:

- Exact primary oracle-K $\Delta J = +0.000341$ (failing the $+0.004$ mechanism gate; triggering $\le +0.002$ kill rule).
- Exact primary predicted-K $\Delta J = -0.000491$ (negative deployable value; Seed B $\Delta J = -0.001015$).
- Absolute candidate Jaccard: $0.531769$ (below the $0.537316$ anchor floor).
- Verdict: `KILL_ECRC_CHOICE_MECHANISM`.

Under the tested rank-8 ECRC formulation and DrugQuery evidence path, conditioning named-medication utilities on regimen cardinality produced negligible oracle-K re-ranking value. That formulation is closed and receives no rescue. The result is strong negative evidence for this mechanism, not a universal proof that every future model containing a cardinality variable must fail.

Artifact: `research/prototypes/ecrc-cardinality-context/ecrc-comparison.json`.
Decision note: `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-verdict.md`.

### Terminated diagnostic: CCTM trajectory supportability (2026-09-18)

The bounded pre-architecture data supportability audit for **Clinical Concept Trajectory Memory** (CCTM) completed against `mimic-iii-canonical-131-paper-dev-v1` Train split (4,233 patients, 10,489 visits, 6,256 history-bearing prediction events, zero Dev/Test access).

Result:

- Event-level non-med recurrent support: $36.52\%$ of history-bearing events have $\ge 3$ recurrent D/P trajectories (failing the $\ge 50\%$ supportability gate).
- Event-level all-concept recurrent support: $40.58\%$ of history-bearing events have $\ge 5$ recurrent D/P/M trajectories (failing the $\ge 50\%$ supportability gate).
- Pervasiveness failure: $59.26\%$ of history-bearing visits have zero recurrent trajectories; median recurrent trajectory count across prediction events is 0.0.
- Verdict: `KILL_CCTM_SUPPORTABILITY`.

Concept trajectories are not a pervasive substrate across the clinical population. CCTM architecture exploration is permanently terminated without model implementation, threshold relaxation, or ontology restructuring.

Artifact: `research/diagnostics/cctm-trajectory-support/result.json`.
Decision note: `research/memory/decisions/2026-09-18-cctm-trajectory-support-falsification.md`.

### Completed screen: Evidence-access architecture portfolio (2026-09-18)

An eight-lane 60-epoch portfolio screen tested four orthogonal evidence-access bottlenecks against matched controls at equal parameter count (1,295,367) on physical GPUs 0–7 on 319 (revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3`):

- **Temporal placement**: `temporal_med` $\Delta J = +0.000447 \rightarrow$ `KILL_NO_MATERIAL_SIGNAL`. Pre-temporal medication identity does not add value when persistence features are present.
- **Evidence resolution**: `resolution_code` $\Delta J = +0.011536 \rightarrow$ `MECHANISM_SIGNAL` (clean survivor; F1 $+0.0102$, PR-AUC $+0.0078$, DDI $-0.0056$).
- **Interaction depth**: `depth_reread` $\Delta J = +0.004144 \rightarrow$ `MECHANISM_SIGNAL` (clean survivor; peak Dev Jaccard $0.551259$, F1 $+0.0038$, PR-AUC $+0.0054$, DDI $-0.0007$).
- **Prediction granularity**: `prediction_local` $\Delta J = +0.012976 \rightarrow$ `SIGNAL_WITH_SUPPORTING_METRIC_COST` (strong Jaccard gain, but DDI penalty $+0.003843 > +0.0020$).

Routing verdict: `MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION`. Per frozen contract, no compound model is automatically scheduled without prior scientific arbitration and primary-source closest-work audits.

Artifact: `research/prototypes/evidence-access-portfolio/result.json`.
Decision note: `research/memory/decisions/2026-09-18-evidence-access-portfolio-screen.md`.

### EBRA regimen-assignment screen — design frozen (2026-09-20)

After MEMB/MSED/MHEF falsification, the next architecture hypothesis moves from evidence manipulation to **decision factorization**.

Evidence-Bound Regimen Assignment (EBRA) preserves the strong FineCode principle: each medication first obtains a medication-specific fine-evidence proposal. The new mechanism then asks whether the final prescription should be trained and decoded as one unordered partial assignment rather than as 131 fixed binary responsibilities.

The frozen causal comparison is deliberately stronger than a plain BCE baseline:

- both arms share the same FineCode proposal bank;
- both use K=M=131 learned decision queries;
- both use the same one-layer self-attention, cross-attention, FFN, full medication score matrix, NULL scorer, information budget, and initialization convention;
- fixed_multilabel hard-binds slot k to medication k and trains BCE on L[k,k]-L[k,NULL], followed by the paper-contract Dev-selected global threshold;
- ebra_assignment allows every slot to choose any medication or NULL, trains with permutation-invariant bipartite supervision, and decodes by one-to-one assignment with no threshold or cardinality head.

This formulation is not a claim that medication dependencies or set-to-set MedRec are new. SSPNet already occupies permutation-consistent/set-to-set medication decoding but its published head remains sigmoid/threshold multi-label classification. DETR/DSPN occupy generic direct-set and matching primitives. The pre-screen claim is only the computation-level question of **fixed named-label responsibility versus native medication-or-NULL partial assignment under a matched FineCode proposal/decoder graph**.

Frozen screen:

~~~text
surface: mimic-iii-canonical-131-paper-dev-v1
seed: torch/cuda/python=1203, numpy=2048
training: 15 complete epochs, no early stopping
main pair: ebra_assignment - fixed_multilabel
Test: SEALED
~~~

Contract v1.4 horizon-censoring applies unchanged. Primary mechanism survival requires Delta J > +0.004 with F1/PRAUC losses no worse than 0.002 and DDI increase no greater than 0.002; Delta J <= +0.002 kills the assignment hypothesis. A DDI reduction of at least 0.010 with J/F1/PRAUC loss each no worse than 0.005 routes to Pareto review.

Design: research/memory/decisions/2026-09-20-ebra-regimen-assignment-screen-design.md.  
Prototype spec: research/prototypes/ebra-regimen-assignment-screen/README.md.  
Closest-work boundary: research/prototypes/ebra-regimen-assignment-screen/closest-work-audit.md.  
Local execution handoff: research/prototypes/ebra-regimen-assignment-screen/local-agent-handoff.md.

Implementation and 319 execution are now authorized for this frozen pair only. No slot-count, NULL-bias, decoder-depth, assignment-temperature, retrieval, MoE, DDI-reranking, cardinality-head, or output-repair sweep is authorized.

## Near-term evidence routing

The current sequencing is dependency-driven rather than stage-serial.

### MIMIC-III common contract

Before the next MIII runs, freeze only what can change their interpretation: patient split, legal information budget, target/eligible-event semantics, core evaluator, and joint Dev checkpoint/operating-point selection.

### MICA stability

The default two new paired MIII seeds per arm under the frozen profile are now complete:

```text
SharedPool seed A / DrugQuery seed A
SharedPool seed B / DrugQuery seed B
```

Add a third paired seed only when MICA remains a central component/control, the two pairs disagree and change routing, or otherwise-ready GPU capacity makes completion cheaper than another decision boundary. The current two-pair direction is stable for accuracy/PRAUC/DDI but not medication cardinality, so it supports continued development without forcing a third pair now.

Historical single-seed evidence remains separate unless it exactly satisfies the new run contract.

### Early cross-surface falsification

Do not wait for complete MIII three-seed evidence before testing a promising new architecture on MIV.

After the first valid MIII full/control result and at least one additional paired check show a signal worth pursuing, start sentinel full/control pairs on:

- MIV harmonized/common-131;
- MIV native-173.

If a known implementation/mechanism fault is already visible on MIII, fix or kill it before propagating the faulty model across surfaces.

## GPU and human-bandwidth policy

Treat eight GPUs as a ready-task queue, not fixed phase slots.

Priority order:

1. matched full/control pairs that can change architecture routing;
2. closest/strong external comparator recovery;
3. early second-surface falsification;
4. additional paired seeds needed for a live decision;
5. secondary analyses.

GPU occupancy is not an objective. Keep human implementation bandwidth narrow: at most one actively changing architecture and one baseline recovery requiring heavy code modification at the same time. Additional finished implementations may train concurrently.

## Decision boundaries and management targets

Continue a formulation when matched controls show a worthwhile effect/trade-off, repeated paired evidence does not expose clear instability, cardinality/operating-point controls do not explain the result away, closest-work distinction remains valid, and complexity is commensurate with value.

Allow one bounded scientific redesign only for a concrete observed failure with a pre-written expected fix. Preventable implementation bugs do not consume the scientific redesign allowance.

Kill the tested formulation when full-budget repeated evidence does not support value, a reasonable cardinality control explains the gain, the result depends on unfair information/control choices, added cost is unjustified, or the one evidence-driven redesign fails.

Reset the architecture family when closest work already occupies the core computation, failure points to the structured-set hypothesis itself, or continuation degenerates into unrelated retrieval/DDI/refinement patches. Allow at most one family reset in this research cycle.

Management targets, not scientific pass criteria:

- **2026-10-05**: current architecture route decision — continue, bounded redesign, or kill/reset;
- **2026-10-09 to 2026-10-13**: normal-path target for a credible Paper Candidate;
- **2026-10-16**: hard stop for this architecture-search cycle;
- **2026-10-26 to 2026-11-04**: target frozen-confirmation window only if prerequisites are complete;
- **2026-11-11 to 2026-11-18**: target first complete manuscript/evidence package.

If no survivor exists by 2026-10-16, stop the current architecture search and reassess the paper route rather than opening another rescue sequence.

## Final evidence boundary

A Paper Candidate requires more than internal repeatability: the method difference must be experimentally identifiable; the core effect cannot be a single-seed event; both main paper surfaces need credible external reference positioning; obvious cardinality/leakage/capacity/control-quality explanations must be addressed; DDI/cardinality/efficiency costs must be known; and the closest comparator relevant to the final claim cannot remain an unresolved conceptual omission.

Stable small internal gains do not automatically justify a Paper Candidate when credible external methods remain clearly stronger unless a different evidence-backed safety/efficiency/robustness contribution supports the claim.

MIMIC-IV Test remains sealed throughout reference setup and architecture search. Harmonized131 and native173 derived from the same MIMIC-IV population must be handled inside one frozen confirmation cycle; observing one Test surface cannot be used to redesign the other and still call it untouched.

## Next action

Implement and execute the frozen EBRA matched pair on branch prototype/ebra-regimen-assignment-screen.

The local agent should first run only the scoped preflight needed to establish same information/proposal/decision graph, parameter matching, permutation-invariant candidate loss, duplicate-free assignment decoding, finite forward/backward, and zero Test loading. Then run fixed_multilabel and ebra_assignment for 15 complete epochs under contract v1.4.

Do not redesign EBRA from partial curves. Do not create extra EBRA lanes to occupy GPUs. Apply the frozen survive/weak/kill routing after the pair is interpretable, update aggregate public-safe evidence, and keep Test sealed. Detached baseline recovery may continue independently.
