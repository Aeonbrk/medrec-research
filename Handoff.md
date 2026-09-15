# Handoff: MICA Execution Finalization — Screen Pending

Updated: 2026-09-15.

The verified starting `origin/main` was `2496f39ffa3085e29e4ae9edeca217215b8aba0e`. This handoff records the execution-finalization state after that revision; no MICA training, CUDA model preflight, real-data architecture screen, source deployment, or detached remote job has been launched yet.

## Workspace and deliverables

- Current branch: `main`.
- The starting `HEAD` and freshly fetched `origin/main` were both `2496f39ffa3085e29e4ae9edeca217215b8aba0e` before execution finalization.
- `research/prototypes/mica/` is tracked in the execution-finalization commit; the run must use that exact clean immutable revision.
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
| Runtime verification | No model forward/backward was executed in the declared environment. No CUDA preflight or real-data split/vocabulary validation ran. |
| Remote activity | Read-only SSH account, GPU/disk, checkout status and Python/package-version inspection only. No source transfer, environment change, job creation, training or GPU model inference. |
| Results | No MICA metrics, checkpoint, survival verdict or runtime evidence exists. |

## Remaining execution work

The execution-finalization implementation is complete. Remaining work is only the authorized run:

1. On a new additive 319 checkout, verify the exact final revision, clean status, `medrec-molerec-table1` environment, GPU capacity, disk and the two canonical data roots.
2. Run both `--preflight-only` data-contract checks and exactly one `preflight_mica.py --device cuda` check.
3. If and only if those pass, launch the complete Early/Late 60-epoch screen, retain private artifacts on 319, summarize the two completed result files, and apply the frozen decision.

The scientific risk remains whether early conditioning earns any benefit over the matched late control. Its greater per-example compute is acknowledged; parameter count and optimization opportunities, not FLOPs, are matched.

## Remote resumption context

Read `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` again immediately before the next authorized remote operation. In this session the primary `319-lab` connection failed; `319-lab-via-server` authenticated. Observed environment: Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy `1.23.5`, scikit-learn `1.2.0`, CUDA available. These observations are not a future preflight pass.

The existing remote research checkout was at `246e4f3620ac9b39973e9e5f6385d8f2a765058c` with unrelated untracked Idea 006/resource-reset directories. Preserve it; use an additive isolated checkout at the final execution revision. The old GPU observation is stale: recheck immediately before submission and never touch unrelated processes. Proposed allocation is Early on GPU 0, Late on GPU 1, subject to current capacity; no additional arms are planned.

No remote MICA output directory or monitoring session has been created. Snapshot and Train/Dev identities are in the prototype README and existing prototype commands; private data and execution output roots remain outside Git.

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

## Next assigned execution task

Use the finalized source revision for the minimum Remote Preflight and synthetic/data-contract checks → full Early/Late Train/Dev screen → aggregate evidence intake → apply the predeclared decision. Do not start a new brainstorm, create Idea 009 or open a formal Gate as part of this handoff.

The mechanism cutoff is Early minus Late Jaccard: `<=0.002` kills; `(0.002,0.004]` is weak and not a survivor; `>0.004` is a signal. Project survival additionally requires the precise accuracy or safety bar in README §8. A positive mechanism delta against a weak control alone is insufficient. No held-out selection, broad sweep, automatic rescue, or interpretation of incomplete runs as passes.

## Routing

```text
Active Idea: none
Idea 009: absent
Formal Gate: none
Backbone hunting: complete by default
Strong-unary pairwise residual rescue: deprioritized
Held-out architecture selection: forbidden
MICA: execution finalized; not run
Current session: execution finalization complete
Next owner: run the assigned minimum preflight and full Train/Dev screen
```
