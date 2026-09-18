# ECRC cardinality-context bounded screen authorization — 2026-09-18

Status: **AUTHORIZED FOR DEVELOPMENT SCREEN / NOT A FORMAL IDEA**

## Belief update

The post-RouteFact family reset identifies one unresolved structure that is
materially different from the terminated pairwise/compositional and semantic
families:

> regimen cardinality may act as a global decision context that changes which
> named medications are preferred.

This is narrower than generic set prediction and narrower than predicting a
medication count.

Evidence motivating one bounded screen:

- DrugQuery remains the strongest repeated positive mechanism.
- B0 oracle-count changed only set size under frozen MoleRec ranking and
  increased Dev Jaccard by approximately `+0.01285`; its original
  count-mediated normalized-DDI premise still remains falsified.
- Frozen-unary pairwise co-label oracle headroom was approximately
  `+0.00026` Jaccard.
- RIME composition was approximately `-0.00199` Jaccard below its matched
  count-only control.

These observations do not prove deployable cardinality value. They justify
testing whether medication identity preference changes with regimen size.

## Closest-work boundary

Primary-source review rules out novelty claims based on:

- joint cardinality and set distributions;
- random finite set prediction;
- conditional Bernoulli / fixed-cardinality subset likelihood;
- medication-set decoding in general;
- medication-count normalization in general.

The only candidate contribution is the computation-level distinction:

`patient evidence + hypothesized regimen size -> named-medication utilities`

versus

`patient evidence -> fixed named-medication ranking; regimen size only chooses Top-K`.

SSPNet occupies broad medication-set decoding. DCSD-MR explicitly reports
drug-count normalization, but the currently public official repository does
not expose implementation sufficient to determine whether its medication
utilities are themselves cardinality-conditioned. Novelty confidence is
therefore adequate for DEVELOPMENT screening and inadequate for Paper Candidate
Freeze.

## Authorized screen

The frozen implementation is
`research/prototypes/ecrc-cardinality-context/`.

Six GPU lanes are authorized:

- seed `20260923`: `kind_bce` vs `kcond_bce`;
- seed `20260923`: `kind_exact` vs `kcond_exact`;
- seed `20260924`: `kind_exact` vs `kcond_exact`.

The exact pair is primary. The BCE pair is supporting attribution only. The
second exact seed is stability evidence, not HPO.

No Test access, additional seed, alternate rank, learning-rate sweep, DDI
training objective, decoder bias, graph, retrieval, MoE, semantic bottleneck,
or pairwise medication interaction is authorized.

## Decision semantics

Use the committed summarizer without changing thresholds after results exist.

- Oracle-K is privileged mechanism attribution only.
- Predicted-K is deployable evidence.
- If oracle-K does not show material KCond-vs-KInd choice value, kill ECRC.
- If oracle-K is material but predicted-K is not, exactly one bounded
  size-predictor redesign is authorized.
- A candidate that only beats a collapsed control does not survive.
- A positive count head by itself is not promoted as the method.

Test remains sealed throughout this screen.
