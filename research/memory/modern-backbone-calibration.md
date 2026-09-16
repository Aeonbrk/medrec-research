# Modern-backbone calibration

This is the compact authoritative record for the completed 2026-09-14--2026-09-15 modern-backbone calibration phase. It is comparison and audit state, not a new experiment: reconciliation performed no training, no new evaluation, no held-out Audit/test access, no Idea 009 creation, and no model redesign.

## Provenance

- Authoritative base before reconciliation: `origin/main` at `530f4d22111f385c8f735454cde36155363d7292`.
- Integrated branch tips: `debug/hypemed-fidelity-20260914` at `fb7e3aecd94ed6d34b0b5c05299d71171751e470`; `prototype/dmgexnet-reset-20260914` at `a064a58b418e449d52efe056f2609398fc38bb3a`; `prototype/rxexpert-reset-20260914` at `969ff85938f63df1e8ef0476d8e639cc062486e0`.
- Detailed artifacts: [HypeMed fidelity debug](../prototypes/hypeinteract/fidelity_debug/README.md), [DMGExNet information-budget audit](../prototypes/dmgexnet-reset/README.md), and [Rx-Expert coarse screen](../prototypes/rxexpert-reset/README.md).
- Metrics below are visit-macro results on the canonical Train/Gate01-Dev comparison surface with the project 131-medication DDI resource. The held-out Audit/test resources were not read by these screens.

## Unified backbone table

| Surface | Role / state | Jaccard | F1 | PRAUC | DDI | AvgMed |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec | Canonical anchor | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK | Canonical anchor; empirical Train/Dev ceiling among executed admissible surfaces | 0.533650 | 0.687394 | 0.784240 | 0.073328 | - |
| HypeMed-LeakageSafe, epoch 75 | Canonical HypeMed comparison surface; `HYPEMED_CANONICAL_WEAK` | 0.512112 | 0.668091 | 0.753822 | 0.059404 | 23.6549 |
| HypeMed-OfficialSemantics, epoch 75 | Faithful sensitivity/reference run; not the canonical comparison surface | 0.514256 | 0.670078 | 0.755615 | 0.059559 | 23.5770 |
| Rx-Expert coarse | Trustworthy recent architecture-family reference; `RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY`; `STOP_RXEXPERT_BACKBONE_RESET` | 0.510522 | 0.666965 | 0.757858 | 0.077303 | 22.4268 |
| DMGExNet | No canonical metric; `DMGEXNET_INFORMATION_BUDGET_MISMATCH` | - | - | - | - | - |

The earlier HypeMed-inspired adapter's `Jaccard 0.431689` is `SUPERSEDED_NON_FAITHFUL_HYPEMED_ADAPTER`. It is historical diagnostic output only and is not canonical HypeMed performance. The faithful HypeMed terminal interpretation is `HYPEMED_PREVIOUS_ADAPTER_INVALIDATED` plus `HYPEMED_CANONICAL_WEAK`; leakage-safe HypeMed is the comparison row above.

DMGExNet remains a literature architecture reference and reported-performance reference, not a unified canonical numerical frontier. Its official auxiliary patient rows union all admissions, are unavailable at prediction time, and `med131_new.pkl` is target-derived; this is an information-budget mismatch, not evidence that the architecture is weak.

Rx-Expert is a trustworthy recent architecture-family comparison/reference, not a new backbone. The faithful coarse run required only the documented minor execution patches and stopped at `STOP_RXEXPERT_BACKBONE_RESET`; `RxExpert-NoMoE` and other rescue paths were not run.

## Phase conclusion

`MODERN_BACKBONE_CALIBRATION_COMPLETE`

HypeMed and Rx-Expert provide trustworthy recent comparison/reference surfaces, while DMGExNet cannot enter the canonical numerical frontier under the point-in-time information budget. GraphRefine-SameK remains the empirical Train/Dev ceiling among executed admissible surfaces. Do not revive GraphRefine as a paper direction or initiate additional backbone hunting. After the independent architecture/novelty review finishes, the next research step is architecture-first new-model prototyping.

## Reusable methodological lessons

> Public baseline adaptation must be fidelity-first. Prefer official source + thin data wrapper. A semantically inspired rewrite cannot be used to reject a published method.
> Reported literature performance is not automatically a comparable frontier; information budget and prediction-time semantics must match.
