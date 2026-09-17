<!-- markdownlint-disable MD013 -->

# Prototype inventory

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
| [`rime/`](rime/README.md) | regimen-conditioned marginal energy versus a count-only energy control | implemented; not trained | one-seed MIMIC-III Train/Dev screen with native greedy flips; remote preflight and both 60-epoch arms are unperformed |
| [`hypeinteract/`](hypeinteract/README.md) | HypeMed calibration + proposed interaction stage | HypeMed adapter superseded; faithful HypeMed `HYPEMED_CANONICAL_WEAK`; HypeInteract not run | official-source fidelity materially changes conclusions; faithful recent baseline remains below MoleRec accuracy |
| [`dmgexnet-reset/`](dmgexnet-reset/README.md) | DMGExNet modern-backbone calibration | `DMGEXNET_INFORMATION_BUDGET_MISMATCH` | literature score is not a canonical numerical reference because official auxiliary rows use future/target-derived information |
| [`rxexpert-reset/`](rxexpert-reset/README.md) | Rx-Expert coarse MoE/multimodal backbone calibration | `STOP_RXEXPERT_BACKBONE_RESET` | faithful conditional routing and drug features did not beat MoleRec; router did not collapse |
| [`mica/`](mica/README.md) | shared versus medication-specific evidence selection and pre-pooling conditioning | `PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY` | complete one-seed three-arm screen: DrugQuery−SharedPool ΔJ `+0.009814`; MICA-Late−DrugQuery ΔJ `−0.000588`; preserve medication-specific pooling, drop the extra pre-pooling FiLM step |
| [`mica-v2-screen/`](mica-v2-screen/README.md) | MICA-Core accuracy and safe-decision extensions | `KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH` | complete six-lane screen: FineHistory weak (`ΔJ +0.003327`), DualEvidence killed, SafePTO/SafeRank safety trade-off loses too much Jaccard, and SetContext killed; full aggregate rows are in [`result.json`](mica-v2-screen/result.json) |
| [`mica-dynamic-query-screen/`](mica-dynamic-query-screen/README.md) | patient-conditioned medication queries beyond MICA-Core's patient-dependent keys/values | `KILL_PATIENT_CONDITIONED_QUERY_FAMILY` | complete six-lane screen: GlobalDynamic−StaticMultiQuery `ΔJ −0.000679`, EvidenceDynamic−StaticMultiQuery `ΔJ −0.000560`, and DynamicAdapter−StaticAdapter `ΔJ −0.000729`; all dynamic deltas are non-material |

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

### MICA-v2 extension screen

The six complete single-seed Train/Dev lanes were run from one canonical split
after a passing preflight.  The corrected Core anchor reproduced DrugQuery at
Dev Jaccard `0.5422441561`.  FineHistory was weak (`+0.003327` Jaccard) and
DualEvidence was killed (`−0.000517`); both therefore reset the history
refinement family.  SafePTO reduced DDI by `0.022026` but lost `0.011659`
Jaccard, so there was no useful accuracy-preserving safe headroom.  SafeRank
reduced DDI by `0.022139` relative to Core but lost `0.012926` Jaccard and did
not add value over SafePTO.  SetContext did not beat its parameter-matched
SelfOnly control (`ΔJ −0.000474`).

Interpretation and routing are local to this exploratory screen: retain the
validated MICA-Core DrugQuery base, do not rescue these lanes, and return
to a materially different architecture search.  The source-revision exception
for the corrected Core/SafeRank reruns and the excluded runtime-only attempts
are recorded in `mica-v2-screen/result.json`; no Idea 009 or formal Gate was
created.

### MICA dynamic-query screen

The six authorized single-seed Train/Dev lanes tested whether the query used by
each medication should itself change with current patient evidence. Static
multi-query and static adapter controls isolated extra capacity from dynamic
conditioning. All three matched dynamic deltas were within `0.002` Jaccard:
GlobalDynamic−StaticMultiQuery `−0.000679`,
EvidenceDynamic−StaticMultiQuery `−0.000560`, and
DynamicAdapter−StaticAdapter `−0.000729`. The frozen conclusion is
`KILL_PATIENT_CONDITIONED_QUERY_FAMILY`; no dynamic arm reached material
headroom above the same-revision Core. This is exploratory Train/Dev evidence,
not held-out evaluation, a formal Gate, or a latent-route interpretation.

## Prototype policy

A new prototype should answer one scientific question with the smallest decisive experiment. It may use a new architecture from scratch. A formal Idea or Gate is normally unnecessary for a cheap Train/Dev architecture screen, but early formalization is appropriate when target semantics, information entitlement, privileged supervision, or another scientific contract must be fixed before modeling.

If a prototype survives, invest in closest-work verification, stronger baselines, multiple seeds, and formal claim-support experiments.

Historical prototype decisions are scoped to their implementations and controls. Reuse components when they participate in a materially different mechanism; do not repeat equivalent weak formulations under new names.
