# Handoff: MICA Attribution Complete — DrugQuery Preserved

Updated: 2026-09-15.

The verified starting `origin/main` was `dfec9fb6ebda7893168e3f0263825dd8f1fb44fc`. The three-arm attribution implementation and complete runs are finished at source revision `cd731bb0abe3dca3ebaa8a3e5346eeff74270f75`. SharedPool, DrugQuery, and MICA-Late each completed 60 epochs on the canonical Train/Dev split; aggregate evidence is recorded in [`research/prototypes/mica/result.json`](research/prototypes/mica/result.json). Raw checkpoints, predictions and logs remain private on 319.

## Workspace and deliverables

- Current branch: `main`.
- The starting `HEAD` and freshly fetched `origin/main` were both `dfec9fb6ebda7893168e3f0263825dd8f1fb44fc` before implementation.
- `research/prototypes/mica/` is tracked in implementation revision `cd731bb0abe3dca3ebaa8a3e5346eeff74270f75`.
- Design and scientific contract: [`research/prototypes/mica/README.md`](research/prototypes/mica/README.md). It contains ERAN verdict, primary-source provenance, full model equations/shapes/configuration, matched control, execution plan, decision rules, and renderable Mermaid figure.
- Model draft: `research/prototypes/mica/mica.py`.
- Runner draft: `research/prototypes/mica/run_mica.py`.
- Synthetic preflight draft: `research/prototypes/mica/preflight_mica.py`.
- Aggregate decision script draft: `research/prototypes/mica/summarize_mica.py`.

## Selected architecture

**Attribution conclusion: PRESERVE DRUGQUERY.** MICA means Medication-Indexed Clinical Assembly. The screen tested whether the strong surface depends on medication-specific evidence selection and whether conditioning before pooling adds an independent contribution. The scientific object remains medication-specific clinical evidence, not a conserved evidence-allocation budget or a correction to MoleRec scores.

```text
SharedPool: exact EHR tokens X → shared clinical assembly T → one shared pool → F_m → head
DrugQuery:  exact EHR tokens X → shared clinical assembly T → medication-specific pool → F_m → head
MICA-Late:  exact EHR tokens X → shared clinical assembly T → F_m → medication-specific pool → head
```

All three arms use identical parameter shapes, inputs, optimizer, loss, decoder and update budget. Current D/P codes remain individual tokens; every strictly earlier visit supplies three mean tokens (D/P/M) with ordinal visit lag. There is no persistent medication state, latent intent target, medication-to-medication residual, retrieval, or inherited backbone.

Proposed fixed configuration: 131 medications, hidden width 128, two clinical attention blocks, four heads, FFN width 256, batch 16 visits, 60 complete epochs, AdamW `3e-4`, weight decay `1e-4`, seed `20260914`, BCE plus `0.05` normalized DDI penalty, fixed probability threshold `0.35`, best full-Dev Jaccard checkpoint with earliest tie. Read the prototype README for the exact formulas and initialization; do not infer missing implementation details from this summary.

The raw EHR information budget is the canonical admission-level task. Current D/P code availability is a benchmark entitlement, not proof of pre-order clinical timestamps. Medication history is strictly preceding observed visits. Train/Dev only: 4,233/1,004 patients and 10,489/2,130 visits.

## What has and has not been verified

| Area | Status / evidence |
| --- | --- |
| Repository base and scientific state | Verified at the requested revision; existing Ideas and numerical anchors below remain unchanged. |
| Literature | X-Ray summary found in the user's local `Documents/notes/xray-papers-innovation-summary.md`; relevant motifs and inventory inspected. Primary-source DrugDoctor, SSPNet, HypeMed, Rx-Expert, FLAME, Set Transformer and FiLM checked. FineMed's official repository/publisher material checked, but full equations remained inaccessible. No verified novelty claim. |
| Architecture and code review | Main-agent design/inspection performed for the bounded attribution implementation; no broad review or redesign was requested. |
| Implementation | Model, runner, synthetic preflight and aggregate decision script are execution-finalized. The runner binds the whole clean checkout, requires `--source-revision`, uses strict Jaccard improvement, writes one progress schema, records selected versus epoch-60 evidence, and freezes/records TF32 policy. |
| Local verification before handoff | Scoped syntax/Ruff checks target only the final MICA files. These checks do not establish CUDA or real-data validity. |
| Runtime verification | Real-data contract, target-free/parameter, and single synthetic CUDA preflights passed on the final clean checkout. All three arms completed 60 epochs in `medrec-molerec-table1`. |
| Remote activity | Primary `319-lab` failed connection and approved fallback `319-lab-via-server` passed account/capacity checks; additive isolated checkout used revision `cd731bb0abe3dca3ebaa8a3e5346eeff74270f75`; SharedPool/DrugQuery/Late ran on GPUs 0/1/2. |
| Results | Public-safe aggregate evidence is in `research/prototypes/mica/result.json`; raw checkpoints, predictions and logs remain on 319. |

## Execution outcome

The final run passed the required preflights and completed all three arms. Selected epoch 3 Dev Jaccards were SharedPool `0.5324303341`, DrugQuery `0.5422441561`, and MICA-Late `0.5416562262`; epoch-60 Dev rows are separately recorded and were not substituted. The primary `Δ_query` is `+0.0098138220` and secondary `Δ_film` is `−0.0005879299`. The frozen aggregate conclusion is `PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY`.

The earlier Early hypothesis remains killed and was not rerun. No additional ablation, rescue, held-out evaluation, Idea 009, or formal Gate was created.

## Remote resumption context

The primary `319-lab` connection failed its preflight; the approved fallback `319-lab-via-server` was used. Runtime was Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy `1.23.5`, and CUDA was available; the recorded run evidence is bound to that environment.

The existing remote research checkout at `246e4f3620ac9b39973e9e5f6385d8f2a765058c` with unrelated untracked Idea 006/resource-reset directories was preserved. The run used an additive isolated checkout at the final execution revision, with SharedPool on GPU 0, DrugQuery on GPU 1, and MICA-Late on GPU 2; no additional arms were launched.

The private remote output root was `/root/zhb/medrec-mica-attribution-cd731bb`; raw artifacts remain outside Git. The public-safe aggregate was summarized on 319 and recorded locally as `research/prototypes/mica/result.json`.

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

No further MICA execution is authorized by this handoff. Preserve the attribution result, do not create Idea 009 or open a formal Gate automatically, and require a materially different proposal before another architecture screen.

The frozen comparisons are DrugQuery minus SharedPool for medication-specific evidence selection and MICA-Late minus DrugQuery for pre-pooling conditioning. A positive result against a weak control alone is insufficient; this screen records the matched rows and stops without rescue or additional ablation.

## Routing

```text
Active Idea: none
Idea 009: absent
Formal Gate: none
Backbone hunting: complete by default
Strong-unary pairwise residual rescue: deprioritized
Held-out architecture selection: forbidden
MICA: `PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY`; attribution complete and closed
Current session: execution and evidence intake complete
Next owner: future architecture search under the current-state routing boundary
```
