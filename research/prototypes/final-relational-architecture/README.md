# Final Relational Architecture Search

Status: **DESIGN FROZEN / IMPLEMENTATION IN PROGRESS / NOT EXECUTED**

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

## Low-rank pair relation

For a relation type such as D-P, projected token factors are:

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

The implementation uses tensor contraction and medication chunking rather than materializing a full pair-feature tensor.

No top-K relation mining or pair-count hyperparameter is introduced.

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
