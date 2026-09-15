<!-- markdownlint-disable MD013 -->

# Prototype Inventory

`research/prototypes/` is the pre-Idea execution lane. These artifacts are bounded Train/Dev architecture, mechanism, target-supportability, and baseline-calibration screens. They are evidence, not a queue of routes that must be rescued.

Current cross-project interpretation is authoritative in [`../memory/current-research-state.md`](../memory/current-research-state.md).

## Inventory

| Prototype | Question / family | Current decision | Reusable evidence |
| --- | --- | --- | --- |
| [`hyperedit/`](hyperedit/README.md) | retrieval-conditioned patient-specific medication graph + sequential editor | `STOP_HYPEREDIT`; GraphRefine-SameK retained only as a diagnostic/anchor | fixed-cardinality graph ranking reached Jaccard `0.533650`; effect is too small and DDI slightly worse; not an active paper route |
| [`theracompose/`](theracompose/README.md) | latent therapeutic intents + structured energy/set reconciliation | `STOP_THERACOMPOSE_V0` | this v0 structured formulation collapsed; does not ban all latent-intent/set models |
| [`rxdiffset/`](rxdiffset/README.md) | diffusion-like medication-set denoising | `STOP_RXDIFFSET_V0` | full denoising and SameK remained below strong anchors; one-step nearly recovered MoleRec |
| [`futuregraphkd/`](futuregraphkd/README.md) | next-visit privileged diagnosis/procedure teacher | `STOP_NO_FUTURE_STATE_SIGNAL` | privileged future state itself supplied only tiny Teacher-over-Student signal |
| [`needcover/`](needcover/README.md) | regimen-conditioned residual diagnosis-need reasoning | `KILL_NEEDCOVER_MECHANISM` | matched dynamic residual mechanism was worse than StaticTwoPass |
| [`medstate/`](medstate/README.md) | persistent latent state per medication identity | `KILL_PERSISTENT_MED_STATE` | persistence was worse than matched stateless relation model |
| [`rxunit-support/`](rxunit-support/README.md) | `(drug, dose, route)` prescription-unit target | `KILL_RXUNIT_UNSUPPORTABLE_TARGET` | target semantics unsupported under current causal timing; no model trained |
| [`residual-dependence/`](residual-dependence/README.md) | residual medication-label interaction above frozen MoleRec unary | `CLOSE_INTERACTION_FIRST_FAMILY`; mechanistic note `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY` | FrozenOracle adds only `+0.000257` Jaccard over MoleRec; statistical dependence exists but provides negligible set-accuracy headroom |
| [`hypeinteract/`](hypeinteract/README.md) | HypeMed calibration + proposed interaction stage | HypeMed adapter superseded; faithful HypeMed `HYPEMED_CANONICAL_WEAK`; HypeInteract not run | official-source fidelity materially changes conclusions; faithful recent baseline remains below MoleRec accuracy |
| [`dmgexnet-reset/`](dmgexnet-reset/README.md) | DMGExNet modern-backbone calibration | `DMGEXNET_INFORMATION_BUDGET_MISMATCH` | literature score is not canonical frontier because official auxiliary rows use future/target-derived information |
| [`rxexpert-reset/`](rxexpert-reset/README.md) | Rx-Expert coarse MoE/multimodal backbone calibration | `STOP_RXEXPERT_BACKBONE_RESET` | faithful conditional routing and drug features did not beat MoleRec; router did not collapse |

## Family-level interpretation

### Local correction / interaction-first family

Ideas 001--004, HyperEdit/GraphRefine, NeedCover, MedState, and the frozen-unary residual probe provide substantial negative evidence against treating small residual corrections or medication-medication dependence as the primary missing source of set accuracy. The final frozen-unary Oracle ceiling is decisive for the tested pairwise residual family.

This does **not** ban medication-specific computation or interactions inside a genuinely different architecture. It closes the route where the paper claim is essentially `strong unary + residual medication interaction/correction` without a new source of headroom.

### Structured set / decoder prototypes

TheraCompose-v0 and RxDiffSet-v0 were weak. Their exact formulations should not be tuned repeatedly. They do not establish that every structured generator, list model, or decoder is unpromising; a future structured method should be motivated by a different object or demonstrated inference headroom rather than by renaming these prototypes.

### Privileged / future supervision

Idea 007 and FutureGraphKD show two different limitations: response-specific supervision lacked support, and generic immediate-next-visit state carried little incremental signal. Future privileged supervision remains possible only with a materially different, supportable signal and a clear deployable student entitlement.

### Modern backbone calibration

The calibration phase is complete. HypeMed and Rx-Expert are useful recent references but do not reset the canonical accuracy frontier. DMGExNet is not numerically comparable under the point-in-time information budget. Do not continue backbone hunting by default.

## Prototype policy

A new prototype should answer one scientific question with the smallest decisive experiment. It may use a new architecture from scratch. It does not require a formal Idea or Gate. If it survives, then invest in closest-work verification, stronger baselines, multiple seeds, and formal claim-support experiments.

Historical prototype decisions are scoped to their implementations and controls. Reuse components when they participate in a materially different mechanism; do not repeat equivalent weak formulations under new names.
