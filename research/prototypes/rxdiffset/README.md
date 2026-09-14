# RxDiffSet-v0

RxDiffSet-v0 is a throwaway architecture prototype, not Idea 009. It tests
whether a patient-conditioned denoiser can reconstruct a complete corrupted
medication set and express set dependencies beyond independent MoleRec
medication scores.

## Architecture

- Each visit supplies 131 medication tokens containing the frozen,
  patient-specific MoleRec embedding (`64` dimensions), frozen MoleRec score,
  noisy binary membership, and an eight-level noise embedding. Embeddings are
  consumed per visit; they are not averaged across visits.
- Two hidden-112, four-head relation-biased self-attention blocks are
  permutation-equivariant over medication tokens. The two relation channels
  are the existing normalized EHR co-prescription and DDI matrices.
- Train-only per-medication prevalence drives replacement corruption. At each
  sampled level, a clean bit is preserved with `alpha_bar` or replaced by a
  Bernoulli draw from that prevalence. The denoiser predicts clean membership
  with BCE and predicts a Train-derived categorical cardinality (`K=0..53`).
- Inference starts from a seeded prevalence state, runs seven bounded reverse
  transitions, then decodes Top-K with the predicted cardinality. `SameK` uses
  the frozen MoleRec cardinality only as a diagnostic; it is not the standalone
  model output.

## Screen protocol

One seed (`20260914`), one configuration, six epochs, batch size 64, learning
rate `1e-3`, weight decay `1e-4`, cardinality-loss weight `0.25`, and the fixed
schedule `[1.00, 0.92, 0.80, 0.66, 0.50, 0.35, 0.20, 0.08]`. The screen used
10,489 Train visits and 2,130 Gate01-Dev visits from the existing MoleRec
artifact. No held-out resource, bootstrap, confidence interval, sweep, or
additional seed was used. The execution code was bound to commit
`2bbc2324b396b78cf91f0cd5355433a7a4e90449`.

## Screen result

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 |
| RxDiffSet standalone | 0.468094 | 0.626363 | 0.750617 | 0.077299 | 16.3272 |
| RxDiffSet-SameK | 0.502426 | 0.659597 | 0.750617 | 0.079234 | 21.5451 |
| RxDiffSet one-step | 0.525527 | 0.680454 | 0.772476 | 0.072910 | 19.4723 |

The standalone cardinality MAE was `5.0028` with mean predicted cardinality
`16.3272`. SameK preserved the MoleRec cardinality exactly for every visit.
The standalone set changed on `100.00%` of visits versus MoleRec, with mean
symmetric difference `7.3634`; SameK changed `93.76%` with mean symmetric
difference `4.5850`.

Across reverse denoising, `100.00%` of visits changed from the initial noisy
state to the final state, and every visit changed at least once. Mean
membership flips per transition were
`[19.6324, 18.3615, 16.4394, 12.2197, 8.1094, 3.9934, 1.0502]`.

The one-step denoiser is closer to MoleRec than the full reverse output, while
the SameK surface remains well below GraphRefine-SameK and has worse DDI than
MoleRec. Joint denoising therefore did not produce a material accuracy/safety
decision surface in this v0 screen.

Decision: `STOP_RXDIFFSET_V0`.
