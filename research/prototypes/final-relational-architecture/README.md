# Final Relational Architecture Search

Status: **EXECUTION TERMINATED EARLY / DECISIVE COMPLETED EVIDENCE PRESERVED**

This round is intentionally placed before relational multi-seed stability.

The project already has one stable architecture foundation:

~~~text
medication-specific direct access to unpooled fine clinical codes
~~~

Across four prospective DEVELOPMENT conditions, resolution_code - resolution_visit produced:

~~~text
Delta J:
+0.011536
+0.010836
+0.014262
+0.010303

mean Delta J = +0.011734
4 / 4 positive
mean Delta F1 = +0.010118
mean Delta PRAUC = +0.007976
mean Delta DDI = -0.001640

verdict:
STABLE_FINE_CODE_ACCESS
~~~

The first relational prototype then showed:

~~~text
summary-level multiplicative relation
vs matched additive composition

Delta J = +0.004105
Delta F1 = +0.003371
Delta PRAUC = +0.001131
Delta DDI = -0.005341
~~~

but its absolute Jaccard (0.542982) remained below the stable FineCode foundation (0.546626).

Therefore this round does not spend compute stabilizing relational-v1. It asks whether a better paper-intended relational architecture can be built on top of the stable FineCode foundation.

## First-principles diagnosis of relational-v1

Relational-v1 first compresses each modality:

~~~text
D codes --q_m--> d_m
P codes --q_m--> p_m
H codes --q_m--> h_m
~~~

and only then forms:

~~~text
u_D(d_m) * u_P(p_m)
u_D(d_m) * u_H(h_m)
u_P(p_m) * u_H(h_m)
~~~

If d_m = sum_i alpha_mi x_i and p_m = sum_j beta_mj y_j, then:

~~~text
d_m * p_m
=
sum_i sum_j alpha_mi beta_mj (x_i * y_j)
~~~

The pair weight factorizes as alpha_mi beta_mj. It cannot assign a genuinely non-separable importance to one specific diagnosis-procedure pair.

This recreates the same structural risk already exposed by the FineCode experiments: relation evidence may be compressed before the medication-level decision can identify the relevant fine-grained object.

## Target paper architecture

All new candidates preserve the validated FineCode unary path:

~~~text
all legal fine clinical codes
        |
        | medication-specific direct read
        v
foundation context c_m
~~~

A relational branch is added in parallel:

~~~text
fine D / P / historical-M tokens
        |
        v
cross-type code-pair relations
        |
        | medication-conditioned relation attention
        v
r_DP,m / r_DH,m / r_PH,m
~~~

Medication decision:

~~~text
[c_m,
 r_DP,m,
 r_DH,m,
 r_PH,m,
 q_m,
 persistence_m]
        |
        v
medication logit
~~~

The relation branch never replaces the stable FineCode foundation.

## Explicit hidden-rank pair relation

For a relation type such as D-P, projected token factors use the full model hidden rank (128 dimensions):

~~~text
a_i = U_D x_i
b_j = U_P y_j
~~~

and the pair feature is represented implicitly as:

~~~text
phi_ij = a_i * b_j
~~~

For medication m, a relation query g_m gives a non-separable pair logit:

~~~text
s_mij = <g_m, a_i * b_j> / sqrt(r)
beta_mij = softmax over valid code pairs
r_DP,m = sum_i sum_j beta_mij (V_D x_i * V_P y_j)
~~~

The execution target is 8 NVIDIA RTX 3090 GPUs with 24 GB each. Relation space is therefore kept at the full 128-dimensional model hidden width rather than an artificial 64-dimensional bottleneck. The model therefore keeps the complete legal cross-type pair search space instead of introducing top-K pair pruning or summary-only approximations. Medication chunking is only an exact memory-scheduling device: it changes peak activation memory and throughput, not the mathematical relation scores or outputs.

The implementation computes explicit medication-by-code-pair attention score tensors in chunks and immediately contracts them into relation contexts rather than materializing a persistent medication-by-pair-by-relation-dimension feature tensor.

No top-K relation mining, pair-count cap, or pair-count hyperparameter is introduced.

## Eight-lane architecture ladder

All architecture lanes use the same canonical project-owned DEVELOPMENT RNG convention.

### Pair A — preserve FineCode + test summary relation operator

~~~text
summary_add
vs
summary_mul
~~~

Both retain the exact FineCode foundation c_m.

Both perform medication-specific modality reads d_m, p_m, h_m.

Control:

~~~text
r_DP = (u_D + u_P) / sqrt(2)
r_DH = (u_D + u_H) / sqrt(2)
r_PH = (u_P + u_H) / sqrt(2)
~~~

Candidate:

~~~text
r_DP = u_D * u_P
r_DH = u_D * u_H
r_PH = u_P * u_H
~~~

Question: does the original relational-v1 multiplicative signal survive when it augments rather than replaces the stable FineCode foundation?

### Pair B — relation-before-pooling

~~~text
factorized_pair
vs
nonseparable_pair
~~~

Both retain FineCode.

Both use fine D/P/H tokens and the same relation projections.

Control uses factorized pair weights derived from independent medication-specific token distributions:

~~~text
beta_mij = alpha_mi * alpha_mj
~~~

Candidate computes the pair score jointly:

~~~text
beta_mij = softmax_ij <g_m, U x_i * V x_j>
~~~

Question: does a medication need to identify a specific clinical code pair before relation aggregation, rather than combine independently selected unary evidence?

This is the central hypothesis of the round.

### Pair C — relation-type evidence competition

~~~text
nonseparable_pair
vs
joint_competition_pair
~~~

Both use non-separable fine-code pair relations.

Control normalizes D-P, D-H and P-H relation evidence separately, so every available relation type receives its own normalized evidence channel.

Candidate uses one joint normalized evidence budget across all valid cross-type pairs while preserving three typed output contexts. Before joint normalization, each relation type receives a fixed correction of minus log(valid pair count), so relation types with more combinatorial pairs do not receive extra probability mass merely because they contain more pairs.

Question: should a medication be allowed to suppress an irrelevant relation type rather than forcing D-P, D-H and P-H to contribute independently?

### Pair D — visit/time structure as relation attributes

~~~text
untyped_edge_pair
vs
temporal_edge_pair
~~~

Both use non-separable joint relation competition.

Neither performs visit pooling or recurrent temporal compression.

Control exposes only relation-type identity (D-P / D-H / P-H) to the edge scorer.

Candidate uses the same scorer and additionally exposes:

~~~text
same-visit indicator
current-history indicator
both-historical indicator
log(1 + visit-lag gap)
~~~

to the medication-conditioned pair scorer.

Question: can visit/time structure help when represented as an attribute of a fine clinical relation instead of being used to compress codes into visit states?

## Additional anchor lane

A canonical foundation_code lane reproduces the exact preceding resolution_code architecture under the new 30-epoch exploration runner.

Its selected checkpoint and Dev output are expected to match the prior canonical foundation because the historical selected checkpoint was epoch 5.

Any material reproduction drift invalidates the new runner.

The eight physical lanes are:

~~~text
GPU 0  foundation_code
GPU 1  summary_add
GPU 2  summary_mul
GPU 3  factorized_pair
GPU 4  nonseparable_pair
GPU 5  joint_competition_pair
GPU 6  untyped_edge_pair
GPU 7  temporal_edge_pair
~~~

Pair C reuses nonseparable_pair as its separate-normalization control. Pair D uses a dedicated constant-edge control so temporal-edge attribution remains exact.

## 30-epoch exploration horizon

This round follows Paper Experiment Contract v1.3:

~~~text
30 complete epochs
~~~

No early stopping.

Complete Dev evaluation occurs every epoch.

A matched comparison is scientifically interpretable only if both selected checkpoints satisfy:

~~~text
selected_epoch <= 25
~~~

If either arm selects epoch 26–30:

~~~text
HORIZON_CENSORED
~~~

The exact pair must be extended unchanged to 60 epochs before a scientific verdict is issued.

## Frozen mechanism rule

For each matched candidate minus control:

~~~text
Delta J <= +0.002
=> KILL / no material mechanism signal

+0.002 < Delta J <= +0.004
=> WEAK / normally stop

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> CLEAN_MECHANISM_SIGNAL

Delta J > +0.004 with guardrail failure
=> SIGNAL_WITH_SUPPORTING_METRIC_COST
~~~

This round is architecture search. It does not automatically combine all positive mechanisms.

After completion, the strongest coherent complete variant is scientifically arbitrated before stability.

## Frozen DEVELOPMENT protocol

~~~text
profile:
mimic-iii-canonical-131-paper-dev-v1

Train:
4,233 patients / 10,489 visits

Dev:
1,004 patients / 2,130 visits

Test:
SEALED

epochs:
30 complete epochs

batch:
16 visits

optimizer:
AdamW

lr:
1e-4

weight decay:
1e-4

gradient clip:
5.0

loss:
BCE + 0.05 * normalized DDI penalty

thresholds:
0.05 ... 0.95

selection:
joint complete-Dev checkpoint / operating-point selection
by patient-macro Jaccard

canonical RNG:
torch/cuda/python = 1203
numpy = 2048
~~~

No Test, MIMIC-IV, HPO, relation-rank sweep, extra relation type, safety rescue or additional seed is authorized by this architecture-search round.

## Execution note

The originating cloud environment could not resolve raw.githubusercontent.com, so server-side py_compile/import checks remain execution-blocking. The 319 local agent must complete static syntax/import checks and the committed CUDA/data preflight before any training lane is launched.

## Execution Outcome and Preserved Evidence (2026-09-19)

Execution was carried out on the 319 Execution Plane across 8 physical RTX 3090 GPUs at frozen source revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00`. Five upstream lanes ran to full 30-epoch completion. Following decisive failure of the upstream non-separable pair hypothesis, the remaining 3 downstream lanes were terminated cleanly to preserve compute.

### Completed 30-Epoch Scientific Evidence

| Lane | Status | Params | Selected Ckpt / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Dev Avg Meds | $\Delta J$ vs Foundation |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `foundation_code` | **COMPLETE** | 1,295,367 | Ep 5 / 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.4289 | 0.000000 |
| `summary_add` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.549611 | 0.700831 | 0.795774 | 0.070840 | 20.4097 | **+0.002984** |
| `summary_mul` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.546079 | 0.697773 | 0.794356 | 0.069782 | 19.9987 | -0.000547 |
| `factorized_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.30 | 0.544349 | 0.696591 | 0.792744 | 0.072023 | 21.4859 | -0.002277 |
| `nonseparable_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.543162 | 0.694911 | 0.792572 | 0.070803 | 19.9211 | -0.003464 |

### Truncated Execution State

| Lane | Status | Last Completed Epoch | Observed Ckpt at Termination | Elapsed Wall-Clock | Peak VRAM | Termination Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `joint_competition_pair` | **TRUNCATED_NON_INTERPRETABLE** | 25/30 | Ep 5 (OP=0.30) | 31,511s (525m) | 14,276 MB | Low expected value after upstream pair failure |
| `untyped_edge_pair` | **TRUNCATED_NON_INTERPRETABLE** | 24/30 | Ep 5 (OP=0.30) | 32,012s (533m) | 14,276 MB | Low expected value after upstream pair failure |
| `temporal_edge_pair` | **TRUNCATED_NON_INTERPRETABLE** | 15/30 | Ep 5 (OP=0.30) | 31,948s (532m) | 14,276 MB | Low expected value after upstream pair failure |

Partial metrics from truncated lanes are descriptive execution state only. They are not valid scientific evidence and must not be used for mechanism survive/kill decisions.

### Matched Pair Verdicts

- **Pair A (`summary_operator`: `summary_add` vs `summary_mul`)**: $\Delta J = -0.003531$. Multiplicative conjunction fails against additive composition (`KILL_NO_MATERIAL_SIGNAL`).
- **Pair B (`pair_granularity`: `factorized_pair` vs `nonseparable_pair`)**: $\Delta J = -0.001187$. Non-separable pair attention does not improve over factorized attention, and both fall below the foundation anchor (`KILL_NO_MATERIAL_SIGNAL`).

### Primary Architectural Takeaway

`summary_add` achieved the highest absolute Dev Jaccard (0.549611). Its additive structure indicates that modality-separated medication-specific evidence channels provide a promising architecture direction. It is classified as `BEST_COMPLETED_ARCHITECTURE_CLUE` (not `FINAL_MODEL`) pending capacity-matched isolation.

Research routing: `TERMINATE_RELATIONAL_PAIR_REFINEMENT_REFORMULATE_AROUND_MODALITY_SEPARATED_FINE_CODE_EVIDENCE`.
