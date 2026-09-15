<!-- markdownlint-disable MD013 -->

# Prototype Inventory

`research/prototypes/` is the default pre-Idea execution lane for bounded Train/Dev architecture, mechanism, target-supportability, and baseline-calibration screens. A prototype may fail, succeed, or only answer a diagnostic question. These artifacts are evidence, not a queue of routes that must be rescued.

Current cross-project interpretation is authoritative in [`../memory/current-research-state.md`](../memory/current-research-state.md). Run-local README/result files remain authoritative for what each run actually returned.

## Inventory

| Prototype | Question / family | Observed result | Current interpretation / reusable evidence |
| --- | --- | --- | --- |
| [`hyperedit/`](hyperedit/README.md) | retrieval-conditioned patient-specific medication graph + sequential editor | `STOP_HYPEREDIT`; GraphRefine-SameK diagnostic Jaccard `0.533650` | fixed-cardinality graph ranking shows a small real effect with slightly worse DDI; useful as evidence/reference, not an active paper route |
| [`theracompose/`](theracompose/README.md) | latent therapeutic intents + structured energy/set reconciliation | `STOP_THERACOMPOSE_V0` | this v0 structured formulation collapsed; does not ban all latent-intent/set models |
| [`rxdiffset/`](rxdiffset/README.md) | diffusion-like medication-set denoising | `STOP_RXDIFFSET_V0` | full denoising and SameK remained below strong references; one-step nearly recovered MoleRec |
| [`futuregraphkd/`](futuregraphkd/README.md) | next-visit privileged diagnosis/procedure teacher | `STOP_NO_FUTURE_STATE_SIGNAL` | privileged future state itself supplied only tiny Teacher-over-Student signal |
| [`needcover/`](needcover/README.md) | regimen-conditioned residual diagnosis-need reasoning | `KILL_NEEDCOVER_MECHANISM` | matched dynamic residual mechanism was worse than StaticTwoPass |
| [`medstate/`](medstate/README.md) | persistent latent state per medication identity | `KILL_PERSISTENT_MED_STATE` | persistence was worse than matched stateless relation model |
| [`rxunit-support/`](rxunit-support/README.md) | `(drug, dose, route)` prescription-unit target | `KILL_RXUNIT_UNSUPPORTABLE_TARGET` | target semantics unsupported under current causal timing; no model trained |
| [`residual-dependence/`](residual-dependence/README.md) | residual medication-label interaction above frozen MoleRec unary | actual frozen-unary terminal recommendation: `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY` | FrozenOracle adds only `+0.000257` Jaccard over MoleRec; current routing deprioritizes `strong unary + pairwise residual correction`, not interaction generally |
| [`hypeinteract/`](hypeinteract/README.md) | HypeMed calibration + proposed interaction stage | HypeMed adapter superseded; faithful HypeMed `HYPEMED_CANONICAL_WEAK`; HypeInteract not run | official-source fidelity materially changes conclusions; faithful recent baseline remains below MoleRec accuracy |
| [`dmgexnet-reset/`](dmgexnet-reset/README.md) | DMGExNet modern-backbone calibration | `DMGEXNET_INFORMATION_BUDGET_MISMATCH` | literature score is not a canonical numerical reference because official auxiliary rows use future/target-derived information |
| [`rxexpert-reset/`](rxexpert-reset/README.md) | Rx-Expert coarse MoE/multimodal backbone calibration | `STOP_RXEXPERT_BACKBONE_RESET` | faithful conditional routing and drug features did not beat MoleRec; router did not collapse |
| [`mica/`](mica/README.md) | medication identity before versus after shared clinical assembly | `KILL_MICA_MECHANISM` | complete one-seed Early/Late screen had ΔJ `-0.000076`; Early/Late selected checkpoints were both near `0.542` but the ordering intervention did not help |

## Family-level interpretation

### Local correction / strong-unary residual-correction route

Ideas 001--004, HyperEdit/GraphRefine, NeedCover, MedState, and the frozen-unary residual probe provide substantial negative evidence against treating small residual corrections or pairwise medication dependence on top of an already strong unary surface as the primary missing source of set accuracy.

The frozen-unary experiment's actual terminal recommendation is `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`. Its measured W-only privileged Oracle headroom over MoleRec is only `+0.000257` Jaccard. The project-level routing implication is therefore to deprioritize repeated `strong unary + pairwise residual correction` variants.

This does **not** ban medication-specific computation, patient-regimen interaction, graph structure, or structured prediction inside a genuinely different architecture. It is not evidence that every interaction-first model is impossible.

### Structured set / decoder prototypes

TheraCompose-v0 and RxDiffSet-v0 were weak. Their exact formulations should not be tuned repeatedly. They do not establish that every structured generator, list model, or decoder is unpromising; a future structured method should be motivated by a different object, capability, inductive bias, or decision process rather than by renaming these prototypes.

### Privileged / future supervision

Idea 007 and FutureGraphKD show two different limitations: response-specific supervision lacked support, and generic immediate-next-visit state carried little incremental signal. Future privileged supervision remains possible with a materially different, supportable signal and a clear deployable-student entitlement.

### Modern backbone calibration

The calibration phase is complete. HypeMed and Rx-Expert are useful recent references but do not improve the best observed canonical accuracy reference. DMGExNet is not numerically comparable under the point-in-time information budget. Do not continue backbone hunting by default.

## Prototype policy

A new prototype should answer one scientific question with the smallest decisive experiment. It may use a new architecture from scratch. A formal Idea or Gate is normally unnecessary for a cheap Train/Dev architecture screen, but early formalization is appropriate when target semantics, information entitlement, privileged supervision, or another scientific contract must be fixed before modeling.

If a prototype survives, invest in closest-work verification, stronger baselines, multiple seeds, and formal claim-support experiments.

Historical prototype decisions are scoped to their implementations and controls. Reuse components when they participate in a materially different mechanism; do not repeat equivalent weak formulations under new names.
