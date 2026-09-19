# MHEF Normalization-Domain Screen

Status: **EXECUTION_COMPLETE_HYPOTHESIS_FALSIFIED** (Routing: `KILL_MHEF_NORMALIZATION_HYPOTHESIS`)

This screen follows the final relational-architecture termination. It does not rescue pair-relation modeling and does not stabilize `summary_add`.

The paper-intended hypothesis is narrower:

> Candidate-medication-specific fine-code evidence should not force diagnosis, procedure, and historical-medication evidence to compete inside one normalized attention budget before each heterogeneous source has contributed to the medication decision.

The model family is provisionally named **Medication-Conditioned Heterogeneous Evidence Factorization (MHEF)**. The name is not a novelty claim.

## Frozen evidence basis

The current project evidence establishes:

- medication-specific evidence selection is repeatedly useful;
- medication-specific direct access to fine clinical codes is the strongest stable project-owned mechanism;
- patient-conditioned medication-query generation failed;
- medication-specific temporal recurrence did not materially help;
- iterative rereading was not stable;
- dense explicit fine-code pair relations failed;
- output-side set/cardinality/pairwise repair has low prior;
- `summary_add` is the best completed recent clue but is confounded by larger capacity and multiple modality-separated reads.

The resulting architectural question is therefore not whether another relation operator helps. It is whether **the normalization boundary itself is wrong**.

## Scientific object

For medication $m$ and fine clinical evidence token $i$:

$$
s_{mi}=\frac{(W_q d_m)^T(W_k h_i)}{\sqrt d},
\qquad v_i=W_v h_i.
$$

The stable FineCode path remains:

$$
\alpha^G_{mi}=\operatorname{softmax}_{i\in E}(s_{mi}),
\qquad
c^G_m=\sum_{i\in E}\alpha^G_{mi}v_i.
$$

The MHEF private evidence channels use the **same** medication query, token scores, key projection and value projection. Only the softmax domain changes:

$$
\alpha^t_{mi}=\operatorname{softmax}_{i\in E_t}(s_{mi}),
\qquad
c^t_m=\sum_{i\in E_t}\alpha^t_{mi}v_i,
$$

for $t\in\{D,P,H\}$, where $H$ denotes strictly previous medication evidence.

The private contexts remain separate until medication-level prediction. They are not first collapsed into a shared patient vector.

## Decisive matched control: CoupledBudget

`coupled_budget_add` computes the same token scores and value vectors, exposes the same four downstream evidence slots, uses the same final scorer, and has the same parameter count.

Its only scientific difference is that D/P/H share one typed-evidence softmax:

$$
\alpha^C_{mi}
=
\operatorname{softmax}_{i\in E_D\cup E_P\cup E_H}(s_{mi}).
$$

The field slots are then obtained without renormalization:

$$
\tilde c^t_m
=
\sum_{i\in E_t}\alpha^C_{mi}v_i.
$$

Equivalently,

$$
\tilde c^t_m=\rho_{m,t}c^t_m,
\qquad
\rho_{m,D}+\rho_{m,P}+\rho_{m,H}=1.
$$

Thus CoupledBudget preserves representation width and field identity while retaining the zero-sum evidence-budget constraint. MHEF removes only that constraint.

## Prediction heads

### Additive evidence head — paper-intended formulation

A single shared evidence scorer is reused for global / diagnosis / procedure / history channels:

$$
r_{m,t}=f_\theta(c^t_m,d_m,e_t).
$$

A separate shared persistence contribution uses the existing medication persistence features. The final medication logit is:

$$
z_m=b_m+r^{persist}_m+\sum_{t\in\{G,D,P,H\}}r_{m,t}.
$$

There is no patient-conditioned medication query, no view-gating MLP, no pair graph, and no post-hoc safety reranker.

### Concat control head

The concat pair replaces the additive decomposition with one matched-capacity MLP over:

$$
[c^G_m,c^D_m,c^P_m,c^H_m,d_m,persistence_m].
$$

This tests whether the normalization effect is real or specific to the additive evidence-decomposition head.

## Eight physical GPU lanes

All eight lanes instantiate exactly the same `MHEFModel` parameter graph and initialization. Variants change only forward computation.

| GPU | Lane | Structural question |
| ---: | --- | --- |
| 0 | `mhef_independent_add` | Rank-1 paper-intended architecture |
| 1 | `coupled_budget_add` | **Decisive test:** independent vs shared D/P/H normalization budget |
| 2 | `wide_global_add` | Can four global FineCode slots plus the same head/capacity absorb the gain? |
| 3 | `mhef_independent_concat` | Independent budgets under generic concat fusion |
| 4 | `coupled_budget_concat` | Exact matched control for GPU 3 |
| 5 | `private_only_add` | Does the stable global FineCode path add complementary value beyond private views? |
| 6 | `hash_partition_a_add` | Does semantic D/P/H grouping beat a cardinality-matched nonsemantic partition? |
| 7 | `hash_partition_b_add` | Second deterministic nonsemantic partition control |

The hash controls preserve, per example:

- the exact set of typed evidence tokens;
- the exact D/P/H bucket cardinalities;
- model parameters and initialization;
- global FineCode path.

Only private-view token membership is deterministically permuted.

## Falsification rules

The primary comparison is:

```text
mhef_independent_add - coupled_budget_add
```

Use the current project screen rule:

```text
Delta J <= +0.002
=> KILL_MHEF_NORMALIZATION_HYPOTHESIS

+0.002 < Delta J <= +0.004
=> WEAK / normally stop

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> CLEAN_MECHANISM_SIGNAL

Delta J > +0.004 with guardrail failure
=> SIGNAL_WITH_SUPPORTING_METRIC_COST / stop without safety rescue
```

Additional attribution requirements before multi-seed stability:

1. `mhef_independent_add - wide_global_add > +0.002 J`; otherwise capacity/fusion can absorb the gain.
2. `mhef_independent_concat - coupled_budget_concat > +0.002 J` with guardrails; otherwise the signal is head-dependent.
3. MHEF must beat both hash-partition controls by `> +0.002 J`; otherwise the evidence supports generic partitioning, not heterogeneous clinical views.
4. The complete Rank-1 model should at least reach the prior completed architecture best (`summary_add`, Dev Jaccard 0.549611) before being treated as the architecture worth stabilizing.
5. `mhef_independent_add - private_only_add <= +0.002 J` means the global path should be removed before stability rather than preserved by inertia.

No DDI rescue, query adapter, extra hop, relation branch, threshold tuning, or hidden-size/head sweep is authorized by this screen.

## Frozen DEVELOPMENT protocol

```text
profile:
mimic-iii-canonical-131-paper-dev-v1

training:
30 complete epochs
no early stopping
complete Dev every epoch

horizon rule:
selected epoch <= 25 -> interpretable
selected epoch 26-30 -> HORIZON_CENSORED
then extend the exact affected lane(s) unchanged to 60 epochs

canonical RNG:
torch/cuda/python = 1203
numpy = 2048

optimizer / loss / batch / evaluator / operating-point selection:
inherit the frozen Evidence-Access Portfolio / Paper Experiment Contract profile

Test:
SEALED
```

## Execution boundary

Cloud-side work freezes the design and implementation only.

The 319 local agent must still perform:

1. clean-checkout / immutable-revision verification;
2. CUDA + private snapshot + Train/Dev preflight;
3. the eight full 30-epoch lanes;
4. exact unchanged 60-epoch extension only if horizon censoring triggers;
5. aggregate summary generation;
6. scientific routing from real results.

Partial lanes are execution state only and are not scientific evidence.

## Completed execution evidence (2026-09-19)

Execution was performed on the 319 Execution Plane across 8 physical RTX 3090 GPUs at frozen revision `4584f8a0d080f4300f9ba5778da08f7f82cdc805`.

All 8 lanes completed all 30 planned epochs without early stopping or numerical divergence. Test set remained completely sealed (`test_loaded = false`). All 8 lanes reached peak Dev performance at Epoch 5; no horizon-censoring extension to 60 epochs was triggered (`safe_selected_epoch_max = 25 >= 5`).

### All eight completed lanes

| Lane | GPU | Params | Epochs | Best Ep | Best OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Avg Med |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mhef_independent_add` | 0 | 1,476,874 | 30 | 5 | 0.30 | 0.549397 | 0.700657 | 0.794860 | 0.072165 | 21.58 |
| `coupled_budget_add` | 1 | 1,476,874 | 30 | 5 | 0.30 | 0.547986 | 0.699394 | 0.793084 | 0.071378 | 21.05 |
| `wide_global_add` | 2 | 1,476,874 | 30 | 5 | 0.30 | **0.549980** | 0.701313 | 0.794769 | 0.072489 | 21.59 |
| `mhef_independent_concat` | 3 | 1,476,874 | 30 | 5 | 0.30 | 0.545593 | 0.697693 | 0.794941 | 0.073200 | 21.67 |
| `coupled_budget_concat` | 4 | 1,476,874 | 30 | 5 | 0.35 | 0.545500 | 0.697330 | 0.793394 | 0.070904 | 20.25 |
| `private_only_add` | 5 | 1,476,874 | 30 | 5 | 0.30 | 0.547128 | 0.698678 | 0.792935 | 0.072477 | 21.32 |
| `hash_partition_a_add` | 6 | 1,476,874 | 30 | 5 | 0.35 | 0.544909 | 0.696626 | 0.793541 | 0.071163 | 20.33 |
| `hash_partition_b_add` | 7 | 1,476,874 | 30 | 5 | 0.35 | 0.544926 | 0.696638 | 0.793559 | 0.071163 | 20.33 |

### Matched comparisons

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `normalization_add` | `mhef_independent_add` | `coupled_budget_add` | +0.001410 | +0.001263 | +0.001776 | +0.000787 | `KILL_NO_MATERIAL_SIGNAL` |
| `capacity_wide_global` | `mhef_independent_add` | `wide_global_add` | -0.000583 | -0.000656 | +0.000091 | -0.000324 | `KILL_NO_MATERIAL_SIGNAL` |
| `normalization_concat` | `mhef_independent_concat` | `coupled_budget_concat` | +0.000093 | +0.000363 | +0.001547 | +0.002296 | `KILL_NO_MATERIAL_SIGNAL` |
| `global_complement` | `mhef_independent_add` | `private_only_add` | +0.002269 | +0.001979 | +0.001926 | -0.000312 | `WEAK_STOP` |
| `semantic_partition_a` | `mhef_independent_add` | `hash_partition_a_add` | +0.004488 | +0.004031 | +0.001320 | +0.001002 | `CLEAN_MECHANISM_SIGNAL` |
| `semantic_partition_b` | `mhef_independent_add` | `hash_partition_b_add` | +0.004471 | +0.004019 | +0.001302 | +0.001002 | `CLEAN_MECHANISM_SIGNAL` |

### Absolute position against prior milestones

- Rank-1 candidate (`mhef_independent_add`): Dev Jaccard = **0.549397**
- Prior completed best (`summary_add`): Dev Jaccard = **0.549611** ($\Delta J = -0.000214$)
- FineCode unaugmented foundation (`foundation_code`): Dev Jaccard = **0.546626** ($\Delta J = +0.002770$)

### Scientific findings and terminal routing

1. **Decoupled normalization does not produce material independent value**: The primary hypothesis test (`mhef_independent_add` vs `coupled_budget_add`) yields only $\Delta J = +0.001410$ (+0.141 pp), failing the $+0.0030$ material signal threshold. Under the concat fusion head, the normalization delta drops to effectively zero ($\Delta J = +0.000093$, +0.009 pp).
2. **Gain is absorbed by wide global capacity**: The matched capacity control (`wide_global_add`), which provides four identical heads over the undivided global FineCode evidence vector, achieves Dev Jaccard = **0.549980**, outperforming `mhef_independent_add` by $+0.000583$. The modest lift over baseline is entirely attributable to multi-head capacity absorption rather than heterogeneous normalization decoupling.
3. **Partition controls confirm semantic dependency**: The deterministic cardinality-preserving hash controls (`hash_partition_a_add` and `hash_partition_b_add`) degrade to Dev Jaccard 0.5449. This confirms that randomly splitting tokens harms semantic alignment, but does not salvage the normalization decoupling hypothesis given the failure against `coupled_budget_add` and `wide_global_add`.
4. **Terminal Scientific Routing**: **`KILL_MHEF_NORMALIZATION_HYPOTHESIS`**. No multi-seed stability or MIMIC-IV replication is authorized. The hypothesis of candidate-specific heterogeneous evidence normalization factorization is definitively closed.
