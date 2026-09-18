# ECRC cardinality-context mechanism screen

Status: **DESIGN FROZEN / IMPLEMENTATION READY / NOT YET EXECUTED**

This bounded DEVELOPMENT experiment tests one scientific hypothesis:

> Regimen cardinality is not merely an output count.  The hypothesized regimen
> size can change which named medications should be preferred for the same
> patient evidence.

This is not Idea 009, a formal Gate, a Test run, a SOTA claim, or a claim that
joint cardinality/set prediction is new.  Random-finite-set / set-prediction
literature already models joint set cardinality and element distributions.
The narrow mechanism under test is **cardinality-conditioned named-medication
choice** in medication recommendation.

## Evidence motivating the screen

The mechanism is admitted because three project results leave this specific
structure unresolved:

- B0 oracle-count kept MoleRec ranking fixed and changed only set size:
  Dev Jaccard `0.533966 -> 0.546813` (`+0.012848`).  B0 correctly failed
  its original count-mediated DDI premise; the accuracy headroom remains a
  diagnostic, not deployable evidence.
- Frozen-unary pairwise dependence had only `+0.000257` oracle Jaccard
  headroom over MoleRec, reducing the prior on pairwise medication interaction
  as the main accuracy lever.
- RIME composition was `-0.001988` Jaccard below its matched count-only
  control.  This does not prove count modeling works; it says the tested
  equal-cardinality composition identity did not add value.

DrugQuery remains a building block only: late medication-specific evidence
selection is reused as a clean patient-to-medication interface.

## Closest-work boundary

The screen must not be described as inventing:

- joint cardinality and set prediction;
- fixed-cardinality subset distributions;
- dynamic programming for conditional Bernoulli / elementary-symmetric
  normalizers;
- medication-count normalization;
- generic set decoding.

The paper-level identity is viable only if primary-source review continues to
support the narrower distinction:

> `K` changes medication utilities/ranking, rather than merely selecting how
> many items to take from a fixed ranking.

SSPNet occupies broad medication-set decoding.  DCSD-MR explicitly uses
drug-count normalization, but its public repository currently does not expose
implementation sufficient to verify whether medication utilities themselves
are conditioned on predicted cardinality.  This uncertainty permits a
development screen, not a novelty freeze.

## Model

All ECRC arms use the same target-free MICA DrugQuery clinical path.  Let
`h_m(x)` be the existing medication-specific feature and `c(x)` the masked
mean clinical context.

A shared size head predicts

`p(K=k|x) = softmax(size_head(c(x)))`,

where `K_max` is the maximum Train target cardinality.

Medication utilities are

`u_m(x,k) = base_m(x) + <g_m(x), v(k)> / sqrt(r)`.

The low-rank width is frozen at `r=8`.

Two parameter-matched mechanisms are exposed:

- `KInd`: use the mean of all `v(k)` rows for every example, so medication
  ranking is independent of cardinality while every parameter remains active.
- `KCond`: use the row `v(k)` selected by the cardinality.

The cardinality embedding table initializes to zero, so paired arms start from
identical medication utilities.

At inference every ECRC arm uses only

`K_hat = argmax p(K|x)`

and returns exact Top-`K_hat` medication utilities with canonical vocabulary
tie breaking.  Current target cardinality is never an inference input.

## Two training semantics

### BCE pair

`KInd-BCE` and `KCond-BCE` use the same joint objective:

`L = [Bernoulli-NLL(Y | u(x,K*)) + CE(K*, size_head(x))] / 131`.

`K*=|Y|` is target supervision during Train only.

This pair asks whether the cardinality context helps under an ordinary
independent-label medication likelihood.

### Exact fixed-cardinality pair

`KInd-Exact` and `KCond-Exact` use

`p(Y=S | x,K=k) proportional to exp(sum_{m in S} u_m(x,k)) * 1[|S|=k]`.

The exact normalizer is the `k`th elementary symmetric polynomial and is
computed in log space by dynamic programming in `O(131*K)`.

The joint objective is

`L = [NLL_fixed_K(Y | x,K*) + CE(K*, size_head(x))] / 131`.

This pair is the **primary Rank-1 comparison** because its probability support
is exactly consistent with the claimed cardinality state.

No DDI term, retrieval, molecular feature, set self-attention, reranker,
semantic bottleneck, or threshold search is added.  DDI is evaluation-only.

## Six GPU lanes

Use one implementation revision and six independent processes:

| GPU lane | Variant | Seed | Role |
| --- | --- | ---: | --- |
| 0 | `kind_bce` | 20260923 | BCE matched control |
| 1 | `kcond_bce` | 20260923 | BCE mechanism |
| 2 | `kind_exact` | 20260923 | exact matched control, seed A |
| 3 | `kcond_exact` | 20260923 | exact mechanism, seed A |
| 4 | `kind_exact` | 20260924 | exact matched control, seed B |
| 5 | `kcond_exact` | 20260924 | exact mechanism, seed B |

The second exact seed is deliberate parallel stability evidence, not
hyperparameter search.  No other seed, rank, loss weight, optimizer, or
decoder variant is authorized by this screen.

## Frozen training budget

- MIMIC-III `mimic-iii-canonical-131-paper-dev-v1`
- Train/Dev only; Test remains sealed
- 60 complete Train epochs
- batch size 16
- AdamW, constant learning rate `1e-4`
- weight decay `1e-4`
- gradient clipping 5
- float32, deterministic CUDA policy used by MICA
- best complete-Dev patient-macro Jaccard checkpoint
- native predicted-cardinality Top-K decoding; no operating-point sweep exists

Each matched pair uses identical initialization and visit permutations.

## Diagnostics

At the selected checkpoint, evaluate two surfaces:

1. **predicted-K** — deployable and used for the primary comparison;
2. **oracle-K** — privileged diagnostic only, using Dev target cardinality.

Oracle-K never selects a checkpoint and never counts as model performance.

Interpretation:

- predicted-K weak, oracle-K KCond-vs-KInd > `+0.004`: size estimation is a
  concrete bottleneck; at most one bounded size-predictor redesign is allowed.
- oracle-K KCond-vs-KInd <= `+0.002`: kill cardinality-conditioned medication
  choice; do not tune the size head to rescue it.

## Frozen decision

Primary statistic is the mean paired exact delta over seeds A and B:

`DeltaJ_exact = mean[J(KCond-Exact_s) - J(KInd-Exact_s)]`.

The exact pair is interpreted in two stages.

**Mechanism attribution (oracle-K, privileged diagnostic):**

- mean oracle-K KCond-vs-KInd Jaccard must exceed `+0.004`;
- both oracle-K seed deltas must be positive.
- if mean oracle-K delta <= `+0.002`, return
  `KILL_ECRC_CHOICE_MECHANISM`; do not rescue the size head.

**Deployable value (predicted-K):**

- mean predicted-K KCond-vs-KInd Jaccard must exceed `+0.004`;
- both predicted-K exact seed deltas must be positive;
- mean F1 delta >= `-0.002`;
- mean PRAUC delta >= `-0.002`;
- mean DDI delta <= `+0.002`;
- mean KCond-Exact Jaccard must be at least `0.537316`, i.e. no more than
  `0.002` below the current MIMIC-III DrugQuery development anchor `0.539316`.

If oracle-K shows a material mechanism but predicted-K fails the deployable
criterion, return `REDESIGN_SIZE_HEAD_ONLY`.  This is the only pre-authorized
scientific redesign.  If both mechanism and deployable criteria pass, return
`SURVIVE_ECRC`; predicted-K mean delta >= `+0.008` returns
`STRONG_SURVIVE_ECRC`.

The BCE pair is supporting attribution, not a second gate.  Same-direction
BCE and Exact gains strengthen the claim that cardinality context, rather than
one structured likelihood, carries the effect.

## If it fails

Do not sweep `r`, loss weights, K bins, temperatures, learning rates, or
decoder biases.  Do not add DDI repair, retrieval, graphs, MoE, semantic
routes, or pairwise medication interactions.  A size-head redesign is allowed
only under the oracle-K bottleneck condition above.  Otherwise kill the tested
formulation and reassess the paper route.
