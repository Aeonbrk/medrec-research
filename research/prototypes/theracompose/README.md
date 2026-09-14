# TheraCompose

TheraCompose is a throwaway v0 architecture prototype, not Idea 009. It tests
whether medication recommendation is better represented as reconciliation among
multiple latent therapeutic intents than as one patient vector with independent
medication logits.

## v0 architecture

- Patient inputs are hashed current diagnosis/procedure sets, four historical
  visit events, and historical medications. A small GRU produces contextual
  event tokens.
- Exactly four permutation-symmetric slot-attention iterations produce latent
  intent representations and activity weights. Slots have no diagnosis-level
  supervision.
- Each slot scores all 131 medications using medication embeddings, patient
  context, and the frozen MoleRec score prior. A smooth activity-weighted
  log-sum-exp produces unary medication utilities.
- Two patient-conditioned medication message-passing layers produce pairwise
  compatibility and DDI-risk terms from EHR/DDI adjacency and intent support.
- A Train-derived categorical cardinality head predicts K. Inference starts at
  unary Top-K and performs at most three deterministic same-K improving swaps.
- The energy is `-unary - compatibility + DDI risk + intent coverage +
  cardinality consistency`. Four deterministic hard-negative families train a
  margin-ranking loss: high-score swaps, DDI-inducing swaps,
  intent-coverage deletion, and redundant addition.

The screen used one seed (`20260914`) and one configuration on 10,489 Train
visits and 2,130 Gate01-Dev visits. No held-out resource, bootstrap, or sweep
was used. The existing GraphRefine-SameK aggregate is used as a comparison
surface.

## Screen result

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 |
| TheraCompose unary-only | 0.068602 | 0.124186 | 0.163290 | 0.088447 | 19.2258 |
| TheraCompose full structured set | 0.064868 | 0.117899 | 0.163290 | 0.060483 | 19.2258 |

Cardinality MAE was `4.4441`. The full structured set changed 100% of Dev
visits versus MoleRec with mean symmetric difference `40.4516`; bounded
structured inference changed 85.49% of unary sets (mean symmetric difference
`2.9840`). Mean active intent slots was `0.0000` at the 0.5 activity threshold,
and the intent-coverage diagnostic was `0.9998`.

The structured energy reduced DDI but did not preserve medication ranking or
set quality. This is a weak effect and does not meet the TheraCompose survival
criteria.

Decision: `STOP_THERACOMPOSE_V0`.
