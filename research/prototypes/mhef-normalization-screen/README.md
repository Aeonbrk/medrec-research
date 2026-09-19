# MHEF Normalization-Domain Screen

Status: **DESIGN + IMPLEMENTATION READY / EXECUTION PENDING 319 PREFLIGHT**

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
