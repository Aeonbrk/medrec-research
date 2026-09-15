# Handoff: MICA Screen Complete — Mechanism Killed

Updated: 2026-09-15.

The verified starting `origin/main` was `2496f39ffa3085e29e4ae9edeca217215b8aba0e`. Execution finalization and the complete MICA screen are now finished at source revision `9616c6b381a259e49b8e737ab26e2ebca73aa505`. Both arms completed 60 epochs on the canonical Train/Dev split; aggregate evidence is recorded in [`research/prototypes/mica/result.json`](research/prototypes/mica/result.json). Raw checkpoints, predictions and logs remain private on 319.

## Workspace and deliverables

- Current branch: `main`.
- The starting `HEAD` and freshly fetched `origin/main` were both `2496f39ffa3085e29e4ae9edeca217215b8aba0e` before execution finalization.
- `research/prototypes/mica/` is tracked in the pushed execution revision `9616c6b381a259e49b8e737ab26e2ebca73aa505`.
- Design and scientific contract: [`research/prototypes/mica/README.md`](research/prototypes/mica/README.md). It contains ERAN verdict, primary-source provenance, full model equations/shapes/configuration, matched control, execution plan, decision rules, and renderable Mermaid figure.
- Model draft: `research/prototypes/mica/mica.py`.
- Runner draft: `research/prototypes/mica/run_mica.py`.
- Synthetic preflight draft: `research/prototypes/mica/preflight_mica.py`.
- Aggregate decision script draft: `research/prototypes/mica/summarize_mica.py`.

## Selected architecture

**ERAN verdict: REPLACE.** MICA means Medication-Indexed Clinical Assembly. Its hypothesis is that candidate medication identity should affect clinical code-to-code and current/history composition before evidence aggregation. The scientific object is a separate clinical evidence field for each medication, not a conserved evidence-allocation budget or a correction to MoleRec scores.

```text
Candidate: exact EHR tokens X → medication conditioning F_m → clinical assembly T → medication-specific readout
Control:   exact EHR tokens X → clinical assembly T → medication conditioning F_m → identical readout
```

Both arms use identical parameter shapes, inputs, optimizer, loss, decoder and update budget. Current D/P codes remain individual tokens; every strictly earlier visit supplies three mean tokens (D/P/M) with ordinal visit lag. There is no persistent medication state, latent intent target, medication-to-medication residual, retrieval, or inherited backbone.

Proposed fixed configuration: 131 medications, hidden width 128, two clinical attention blocks, four heads, FFN width 256, batch 16 visits, 60 complete epochs, AdamW `3e-4`, weight decay `1e-4`, seed `20260914`, BCE plus `0.05` normalized DDI penalty, fixed probability threshold `0.35`, best full-Dev Jaccard checkpoint with earliest tie. Read the prototype README for the exact formulas and initialization; do not infer missing implementation details from this summary.

The raw EHR information budget is the canonical admission-level task. Current D/P code availability is a benchmark entitlement, not proof of pre-order clinical timestamps. Medication history is strictly preceding observed visits. Train/Dev only: 4,233/1,004 patients and 10,489/2,130 visits.

## What has and has not been verified

| Area | Status / evidence |
| --- | --- |
| Repository base and scientific state | Verified at the requested revision; existing Ideas and numerical anchors below remain unchanged. |
| Literature | X-Ray summary found in the user's local `Documents/notes/xray-papers-innovation-summary.md`; relevant motifs and inventory inspected. Primary-source DrugDoctor, SSPNet, HypeMed, Rx-Expert, FLAME, Set Transformer and FiLM checked. FineMed's official repository/publisher material checked, but full equations remained inaccessible. No verified novelty claim. |
| Architecture and code review | Main-agent design/inspection performed; independent reviewer failed due to agent usage limits before returning findings. This is **not** a review pass. |
| Implementation | Model, runner, synthetic preflight and aggregate decision script are execution-finalized. The runner binds the whole clean checkout, requires `--source-revision`, uses strict Jaccard improvement, writes one progress schema, records selected versus epoch-60 evidence, and freezes/records TF32 policy. |
| Local verification before handoff | Scoped syntax/Ruff checks target only the final MICA files. These checks do not establish CUDA or real-data validity. |
| Runtime verification | Real-data contract preflight and the single synthetic CUDA preflight passed on the final clean checkout. Both official arms completed all 60 epochs in `medrec-molerec-table1`. |
| Remote activity | Primary `319-lab` passed account/capacity checks; additive isolated checkout used revision `9616c6b381a259e49b8e737ab26e2ebca73aa505`; Early ran on GPU 0 and Late on GPU 1. |
| Results | Public-safe aggregate evidence is in `research/prototypes/mica/result.json`; raw checkpoints, predictions and logs remain on 319. |

## Execution outcome

The final run passed the required preflights and completed both arms. The frozen aggregate decision is `KILL_MICA_MECHANISM`: Early Jaccard `0.5415802299`, Late Jaccard `0.5416562262`, ΔJ `-0.0000759963`. The selected checkpoints were both epoch 3; epoch-60 Dev rows are separately recorded and were not substituted.

Execution-only failures preserved outside the scientific result were: two preflight retries while correcting exact data-root binding and bounded CUDA equality checking, and one detached-launch wrapper failure caused by pre-populating arm output directories. The successful retry used the same final revision, seed, configuration, split and two authorized arms; no rescue experiment or scientific parameter change occurred.

## Remote resumption context

The final remote operation used the primary `319-lab` target. Runtime was Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy `1.23.5`, and CUDA was available; the recorded run evidence is bound to that environment.

The existing remote research checkout at `246e4f3620ac9b39973e9e5f6385d8f2a765058c` with unrelated untracked Idea 006/resource-reset directories was preserved. The run used an additive isolated checkout at the final execution revision, with Early on GPU 0 and Late on GPU 1; no additional arms were launched.

The private remote output root was `/root/zhb/medrec-mica-runs/9616c6b381a259e49b8e737ab26e2ebca73aa505-attempt2`; raw artifacts remain outside Git. The public-safe aggregate was summarized on 319 and recorded locally as `research/prototypes/mica/result.json`.

## Current scientific state

- **Authoritative synthesis**: `research/memory/current-research-state.md`
- **Active formal Idea**: none
- **Ideas 001--008**: terminated
- **Idea 009**: not created
- **Active formal Gate**: none
- **Modern-backbone calibration**: `MODERN_BACKBONE_CALIBRATION_COMPLETE`
- **Strong-unary residual-correction route**: deprioritized as a primary direction
- **Current phase**: step back, search broadly, then prototype one new architecture/mechanism on Train/Dev by default

According to the current recorded evidence, G3/G4, R0 Holdout, and the historical project test remain quarantined from the recent exploratory prototype sequence.

## Current empirical anchors

| Surface | Jaccard | PRAUC | DDI | Role |
| --- | ---: | ---: | ---: | --- |
| MoleRec | 0.529174 | 0.773576 | 0.072223 | strong simple canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.784240 | 0.073328 | best observed executed admissible Train/Dev reference so far; not an active paper direction |
| HypeMed-LeakageSafe | 0.512112 | 0.753822 | 0.059404 | faithful recent reference; canonically weak on accuracy |
| Rx-Expert coarse | 0.510522 | 0.757858 | 0.077303 | faithful recent architecture-family reference; backbone reset stopped |
| DMGExNet | — | — | — | literature/architecture reference only; information-budget mismatch prevents canonical numerical comparison |

The earlier HypeMed-inspired `0.431689` result is non-faithful historical output and must not be used as canonical HypeMed performance.

## Most recent residual-dependence result

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

Observed terminal recommendation from the run:

`DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`

Interpretation:

- visit-specific co-label dependence exists;
- under this W-only formulation it is not aligned with material set-accuracy headroom above the strong MoleRec unary;
- deployable mean-field recovery is harmful.

Routing guidance:

- deprioritize `strong unary + pairwise residual medication correction` as the primary paper mechanism;
- do not continue to CRF/energy/beam-search/partial-set-completion rescue solely for this residual signal;
- do **not** generalize this into a ban on medication-specific interaction, patient-regimen reasoning, or structured prediction inside a materially different architecture.

The older `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP` result is retained as a historical intermediate probe but is not the current routing basis because its learned calibration confounded the comparison to raw MoleRec.

## Other recent terminal prototypes

- NeedCover: `KILL_NEEDCOVER_MECHANISM`.
- MedState: `KILL_PERSISTENT_MED_STATE`.
- RxUnitSet: `KILL_RXUNIT_UNSUPPORTABLE_TARGET`.
- FutureGraphKD: `STOP_NO_FUTURE_STATE_SIGNAL`.
- RxDiffSet-v0: `STOP_RXDIFFSET_V0`.
- TheraCompose-v0: `STOP_THERACOMPOSE_V0`.
- HyperEdit sequential: `STOP_HYPEREDIT`; GraphRefine-SameK remains a weak diagnostic/reference only.
- HypeMed faithful: `HYPEMED_CANONICAL_WEAK`; previous simplified adapter invalidated.
- Rx-Expert: `STOP_RXEXPERT_BACKBONE_RESET`.
- DMGExNet: `DMGEXNET_INFORMATION_BUDGET_MISMATCH`.

See `research/prototypes/README.md` for the reconciled inventory.

## Next assigned task

No further MICA execution is authorized by this handoff. Preserve the kill result, do not create Idea 009 or open a formal Gate automatically, and require a materially different proposal before another architecture screen.

The mechanism cutoff is Early minus Late Jaccard: `<=0.002` kills; `(0.002,0.004]` is weak and not a survivor; `>0.004` is a signal. Project survival additionally requires the precise accuracy or safety bar in README §8. A positive mechanism delta against a weak control alone is insufficient. No held-out selection, broad sweep, automatic rescue, or interpretation of incomplete runs as passes.

## Routing

```text
Active Idea: none
Idea 009: absent
Formal Gate: none
Backbone hunting: complete by default
Strong-unary pairwise residual rescue: deprioritized
Held-out architecture selection: forbidden
MICA: `KILL_MICA_MECHANISM`; complete and closed
Current session: execution and evidence intake complete
Next owner: future architecture search under the current-state routing boundary
```
