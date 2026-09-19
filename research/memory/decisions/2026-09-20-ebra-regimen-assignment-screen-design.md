# EBRA Regimen-Assignment Screen Design — 2026-09-20

Date: 2026-09-20  
Status: **DESIGN_FROZEN_IMPLEMENTATION_PENDING**

## Belief update

The current evidence no longer supports another evidence-pooling or evidence-competition rescue.

Stable positive signals are concentrated in two places:

- medication-specific access to patient evidence (DrugQuery);
- medication identity binding to fine clinical codes before visit/patient compression (FineCode, including repeated +0.010 to +0.014 Jaccard resolution effects).

PredictionLocal also produced a large local-support gain, but MSED falsified the interpretation that richer empirical support-distribution shape explains that gain. MHEF falsified modality-specific normalization as the necessary mechanism. MEMB falsified cross-medication evidence commonness/competition. Iterative rereading, dense clinical-code pairs, cross-patient precedent memory, cardinality-conditioned choice, route factorization, and output-side repair are also closed in their tested formulations.

The remaining high-leverage question is therefore at the **decision factorization** boundary:

> Once each medication has an evidence-bound fine-grained proposal, should the final prescription be trained and decoded as one unordered variable-cardinality assignment rather than as one fixed binary decision per named medication?

## Rank-1 hypothesis

**Evidence-Bound Regimen Assignment (EBRA).**

EBRA preserves medication-specific FineCode evidence access but replaces fixed label responsibility at the final decision layer with a permutation-invariant partial assignment.

The new scientific object is the prescription itself as an unordered partial assignment between a bank of decision slots and evidence-bound medication proposals.

This is not a DDI reranker, cardinality predictor, query adapter, iterative reader, medication-evidence competition mechanism, or post-hoc set repair.

## Shared evidence-bound proposal bank

Let the legal fine-grained clinical evidence tokens be:

~~~text
X = {x_1, ..., x_N}
~~~

and let q_m denote medication identity m.

For both candidate and matched control:

~~~text
a_mi = (Wq q_m)^T (Wk x_i) / sqrt(d)
alpha_mi = softmax_i(a_mi)
c_m = sum_i alpha_mi Wv x_i
z_m = LN(Wz [q_m || c_m || g])
~~~

where g contains only the same legal global/longitudinal context available to both arms.

The proposal bank is:

~~~text
Z = {z_1, ..., z_M}
~~~

with M=131 on mimic-iii-canonical-131-paper-dev-v1.

No current target medication enters the evidence input. No dynamic medication query, commonness normalization, recurrent rereading, dense code-pair construction, retrieval, or DDI-specific evidence rewrite is added.

## Shared decision block

Use K=M=131 learned decision queries so no target-cardinality oracle or hand-chosen maximum regimen size is introduced.

Both arms use the exact same query parameters and one minimal decoder block:

~~~text
S0 = learned_queries[K, d]
S1 = SelfAttention(S0)
H  = CrossAttention(S1, Z)
H  = FFN + residual/norm
~~~

Define the shared medication score matrix:

~~~text
L[k,m] = score(h_k, z_m)
L[k,NULL] = null_score(h_k)
~~~

Use the same scoring parameters in both arms. The full L matrix is computed in both arms.

The screen must keep this block minimal: one self-attention layer, one cross-attention layer, one FFN block. Do not add a second refinement stage unless a future surviving result justifies it.

## Arm A — fixed-responsibility matched control

Name: fixed_multilabel.

Slot k is permanently responsible for medication k.

Its binary medication logit is:

~~~text
b_m = L[m,m] - L[m,NULL]
~~~

Train using standard multi-label BCE against the 131-dimensional target vector.

At inference, apply the repository paper-contract Dev-selected global threshold procedure to sigmoid(b_m).

The off-diagonal score matrix is still computed, so the architecture, proposal bank, query bank, attention depth, and score function remain matched; the control simply does not permit responsibility reassignment.

## Arm B — EBRA partial assignment

Name: ebra_assignment.

Each decision slot may predict any medication or NULL:

~~~text
p_k = softmax([L[k,1], ..., L[k,M], L[k,NULL]])
~~~

For target set Y={y_1,...,y_n}, construct K targets consisting of the n unique medications plus K-n NULL entries and solve one minimum-cost bipartite assignment using negative log probability.

Use a balanced matched/unmatched objective:

~~~text
L_set =
  mean_{matched real targets} -log p_k(y)
  + mean_{NULL targets}       -log p_k(NULL)
~~~

Do not multiply the NULL term by K-n again; each mean contributes one normalized term.

At inference, solve the same one-to-one assignment between K slots and M medication identities plus K NULL dummy columns. A medication column may be used at most once; NULL may be used repeatedly through its dummy copies. The non-NULL assignments form the predicted regimen.

There is no threshold and no separate cardinality head. Regimen size is the number of slots assigned to non-NULL medications.

For continuous per-medication PRAUC reporting, predeclare:

~~~text
score_m = max_k log p_k(m)
~~~

This continuous score is evaluation-only and does not change discrete decoding.

## Exact mechanism distinction

The decisive difference is:

~~~text
fixed_multilabel:
evidence-bound medication proposals
-> fixed slot-to-medication responsibility
-> 131 binary targets
-> thresholded multi-hot set

ebra_assignment:
same proposals
-> same decision block
-> free slot-to-medication responsibility
-> medication-or-NULL categorical targets
-> bipartite assignment
-> native partial set
~~~

If assignment is removed, EBRA collapses directly to the matched fixed-responsibility multi-label model.

## Strong-control requirements

Before training, verify:

- identical legal information budget;
- identical encoder/proposal-bank implementation;
- identical learned query initialization;
- identical decision-block depth and width;
- identical score-function parameters;
- full L matrix computed in both arms;
- parameter counts equal except for mechanically unavoidable scalar/null bookkeeping; any mismatch must be <=1%, otherwise widen the control rather than weaken it;
- no target leakage;
- finite forward/backward;
- candidate matching loss invariant to permutation of target-medication order;
- Test never loaded.

No historical foundation_code, summary_add, or wide_global_add arm is the causal control. They may be reported as immutable references only.

## Training protocol

~~~text
surface: mimic-iii-canonical-131-paper-dev-v1
evidence role: DEVELOPMENT
seed convention: torch/cuda/python=1203, numpy=2048
main arms: fixed_multilabel vs ebra_assignment
training: 15 complete epochs
early stopping: none
Dev: complete Dev every epoch
selection: paper-contract joint checkpoint / operating-point procedure
Test: SEALED
~~~

The EBRA arm has native decoding and therefore no threshold operating-point dimension. The control receives the normal global threshold grid.

Contract v1.4 applies:

~~~text
both selected epochs <= 10
=> interpretable

either selected epoch 11-15
=> HORIZON_CENSORED_15_TO_30
=> extend exact pair unchanged to 30

30-epoch selected epoch 26-30
=> HORIZON_CENSORED_30_TO_60
=> extend exact pair unchanged to 60
~~~

## Frozen decision rule

Primary comparison:

~~~text
ebra_assignment - fixed_multilabel
~~~

Routing:

~~~text
Delta J <= +0.002
=> KILL_SET_ASSIGNMENT_HYPOTHESIS

+0.002 < Delta J <= +0.004
=> WEAK_STOP

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> SURVIVE_TO_STABILITY

Delta J > +0.004 with a supporting-metric guard failure
=> SIGNAL_REVIEW_BEFORE_STABILITY

Delta DDI <= -0.010
and Delta J >= -0.005
and Delta F1 >= -0.005
and Delta PRAUC >= -0.005
=> SURVIVE_TO_PARETO_REVIEW
~~~

Average medication count must always be reported. If an apparent gain is dominated by a large count shift, do not declare mechanism survival automatically; permit at most one fixed-cardinality diagnostic that can test whether the assignment effect survives count equalization.

No multi-seed stability, MIMIC-IV replication, or Test access is automatically authorized by this screen.

## Explicit non-rescue rule

A weak or negative result is not followed by:

- slot-count sweeps;
- NULL-bias sweeps;
- assignment-temperature sweeps;
- extra decoder layers;
- autoregressive ordering;
- DDI reranking;
- cardinality heads;
- retrieval;
- MoE;
- OT/Sinkhorn marginal tuning;
- post-hoc output repair.

A coding bug is fixed and the exact frozen comparison rerun. A scientific failure kills the tested assignment formulation.

## Adversarial review

The central risk is novelty and mechanism attribution, not implementation feasibility.

Generic direct set prediction, learned queries, bipartite matching, NULL/no-object prediction, permutation-invariant set supervision, and Transformer set decoders are established primitives. SSPNet already claims set-to-set medication recommendation and a permutation-consistent medication decoder.

The only worthwhile scientific distinction is therefore computational and narrow:

> Does replacing fixed named-label responsibility with native medication-or-NULL partial assignment add value when medication-specific FineCode proposal quality and decoder capacity are held matched?

If the matched experiment cannot support that distinction, EBRA is not a paper method.
