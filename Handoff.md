# Handoff: Architecture-First Open Search

## Current scientific state

- **Authoritative synthesis**: `research/memory/current-research-state.md`
- **Active formal Idea**: none
- **Ideas 001--008**: terminated
- **Idea 009**: not created
- **Active formal Gate**: none
- **Modern-backbone calibration**: `MODERN_BACKBONE_CALIBRATION_COMPLETE`
- **Interaction-first residual family**: `CLOSE_INTERACTION_FIRST_FAMILY`
- **Current phase**: step back, search broadly, then prototype one new architecture/mechanism on Train/Dev

According to the current recorded evidence, G3/G4, R0 Holdout, and the historical project test remain quarantined from the recent exploratory prototype sequence.

## Current empirical anchors

| Surface | Jaccard | PRAUC | DDI | Role |
| --- | ---: | ---: | ---: | --- |
| MoleRec | 0.529174 | 0.773576 | 0.072223 | strong simple canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.784240 | 0.073328 | current executed admissible Train/Dev ceiling; not an active paper direction |
| HypeMed-LeakageSafe | 0.512112 | 0.753822 | 0.059404 | faithful recent reference; canonically weak on accuracy |
| Rx-Expert coarse | 0.510522 | 0.757858 | 0.077303 | faithful recent architecture-family reference; backbone reset stopped |
| DMGExNet | — | — | — | literature/architecture reference only; information-budget mismatch prevents canonical numerical comparison |

The earlier HypeMed-inspired `0.431689` result is non-faithful historical output and must not be used as canonical HypeMed performance.

## Most recent family-level result

The frozen-unary residual-dependence isolation fixed the original MoleRec logits and learned only a symmetric zero-diagonal residual interaction matrix.

Key deltas:

```text
FrozenOracle - MoleRec:
  Jaccard +0.000257
  NLL     -0.010482
  PRAUC   -0.010974

FrozenOracle - FrozenShuffled:
  Jaccard +0.010644

FrozenMeanField - MoleRec:
  Jaccard -0.003437
```

Interpretation:

- visit-specific co-label dependence exists;
- it is not aligned with material set-accuracy headroom above the strong MoleRec unary;
- deployable mean-field recovery is harmful;
- do not continue to CRF/energy/beam-search/partial-set-completion rescue for this pairwise residual signal.

Family-level decision: `CLOSE_INTERACTION_FIRST_FAMILY`.

Mechanistic note: `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`.

The older `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP` result is retained as a historical intermediate probe and is superseded for routing by the frozen-unary identification result.

## Other recent terminal prototypes

- NeedCover: `KILL_NEEDCOVER_MECHANISM`.
- MedState: `KILL_PERSISTENT_MED_STATE`.
- RxUnitSet: `KILL_RXUNIT_UNSUPPORTABLE_TARGET`.
- FutureGraphKD: `STOP_NO_FUTURE_STATE_SIGNAL`.
- RxDiffSet-v0: `STOP_RXDIFFSET_V0`.
- TheraCompose-v0: `STOP_THERACOMPOSE_V0`.
- HyperEdit sequential: `STOP_HYPEREDIT`; GraphRefine-SameK remains a weak diagnostic/anchor only.
- HypeMed faithful: `HYPEMED_CANONICAL_WEAK`; previous simplified adapter invalidated.
- Rx-Expert: `STOP_RXEXPERT_BACKBONE_RESET`.
- DMGExNet: `DMGEXNET_INFORMATION_BUDGET_MISMATCH`.

See `research/prototypes/README.md` for the reconciled inventory.

## Next research action

Do **not** start another diagnostic on a closed family and do **not** hunt another public backbone by default.

Use the next cycle for architecture-first discovery:

```text
step back
→ broad MedRec + adjacent-method search
→ formulate one Rank-1 mechanism-bearing candidate
→ enough closest-work checking to avoid an obvious duplicate
→ one seed / one main config / Train+Dev
→ strongest relevant baseline + decisive mechanism ablation
→ continue / redesign once / kill
```

The candidate is not required to use MoleRec or any previously successful component. New architectures, prediction granularities, decoders, representations, supervision paradigms, and coherent combinations are open.

Novelty is a survivor/paper requirement, not a reason to block a cheap architecture prototype. Historical failure and literature files are evidence and discovery aids; they do not impose global bans on architectural primitives.

## Routing

```text
Active Idea: none
Idea 009: absent
Formal Gate: none
Backbone hunting: complete by default
Interaction-first residual rescue: closed
Held-out architecture selection: forbidden
Next owner: architecture / method search, then one bounded Train/Dev prototype
```
