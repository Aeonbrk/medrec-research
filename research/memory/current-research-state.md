<!-- markdownlint-disable MD013 -->

# Current Research State — 2026-09-16

This file is the authoritative **current scientific synthesis and routing state** for `medrec-research`. It does not replace run-local evidence; it reconciles it.

## 1. Current phase

```text
Active formal Idea: none
Ideas 001--008: terminated
Idea 009: not created
Active formal Gate: none
Current stage: STAGE -1 — MICA CORE CONSOLIDATION + TRAINING DIAGNOSIS + MIMIC-IV READINESS
Stage status: PRE-IDEA / PRE-GATE / NO PAPER CLAIM / NO HOLDOUT TEST / NO NEW METHOD FAMILY
Modern-backbone calibration: complete
Strong-unary residual-correction route: deprioritized as a primary direction
Current action: review the frozen MIMIC-IV Train/Dev screen contract; remain in Stage -1
```

No new architecture family, Idea 009, formal Gate, held-out evaluation, or
multi-seed run is authorized in Stage -1. The earlier architecture-search
directions remain deferred until this substrate work is complete.

According to the current recorded evidence, G3/G4, R0 Holdout, and the historical project test remain quarantined from the recent exploratory prototype sequence.

## 2. Evidence hierarchy and epistemic labels

When summaries conflict:

1. run-local result JSON / audit / source-bound README is authoritative for that run;
2. this file is authoritative for current cross-project interpretation and routing;
3. current indexes and `Handoff.md` summarize this file;
4. older search, review, authorization, literature, and reorientation documents are historical snapshots.

Use three distinct labels in current-state synthesis:

- **Observed result**: directly produced by an experiment, audit, or source review.
- **Interpretation**: scientific reading of one or more observed results.
- **Routing guidance**: what the project should prioritize or deprioritize next.

Do not promote a routing inference into a runner-produced terminal verdict. A historical `CLOSED`, `CROWDED`, `PRIOR ART`, or `NOT AUTHORIZED` label applies to its dated formulation and workflow state; it is not a permanent ban on an architectural primitive.

## 3. Canonical comparison anchors

| Surface | Jaccard | F1 | PRAUC | DDI | AvgMed | Current role |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 | strong simple canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 | best observed executed admissible Train/Dev reference so far; **not** an active paper direction |
| HypeMed-LeakageSafe | 0.512112 | 0.668091 | 0.753822 | 0.059404 | 23.6549 | faithful recent baseline/reference; accuracy too weak for backbone reset |
| HypeMed-OfficialSemantics | 0.514256 | 0.670078 | 0.755615 | 0.059559 | 23.5770 | faithful sensitivity/reference, not canonical comparison surface |
| Rx-Expert coarse | 0.510522 | 0.666965 | 0.757858 | 0.077303 | 22.4268 | faithful recent architecture-family reference; not a new backbone |
| DMGExNet | — | — | — | — | — | literature/architecture reference only; canonical numerical comparison blocked by information-budget mismatch |

The old HypeMed-inspired `0.431689` result is `SUPERSEDED_NON_FAITHFUL_HYPEMED_ADAPTER` and must never be presented as canonical HypeMed performance.

Observed phase result: `MODERN_BACKBONE_CALIBRATION_COMPLETE`.

Routing guidance: do not continue hunting public backbones by default without a specific scientific reason. A strong baseline is a comparator, not a mandatory substrate for the next model.

## 4. Formal Ideas 001--008

| Idea | Terminal scope |
| --- | --- |
| 001 Tension-Guided Verification | no incremental constraint signal beyond recommender confidence / strong scalar control |
| 002 Score-Geometry Sufficiency | score geometry was ordering-equivalent; no new routing information |
| 003 Prescription-Relative Confidence | expanded relative/rank features failed the strong control |
| 004 Co-Selection Compatibility | NPMI/co-selection scalar added no reliable incremental value |
| 005 Safety-Preserving Substitution Structure | tested ATC substitution semantics failed admission |
| 006 Exposure-Conditional Medication Recommendation | learned method lost to equal-entitlement direct control |
| 007 Privileged Physiological Response Supervision | Gate 01 P1 stopped before training because response support was insufficient/materially concentrated |
| 008 BudgetSet | `KILL_TARGET_SEMANTICS`: learned budget conditioning collapsed across requested budgets while explicit optimization exposed a visible trade-off |

All eight Ideas remain terminated. Their components may be reused in materially different formulations; their frozen hypotheses should not be silently modified and revived under the same Idea number.

## 5. Prototype and mechanism evidence

### HyperEdit / GraphRefine

Observed results:

- Sequential HyperEdit: `STOP_HYPEREDIT`; Jaccard `0.497527`, DDI `0.064668`, severe under-prescription.
- Retrieval-only fusion: small movement around MoleRec.
- `GraphRefine-SameK`: Jaccard `0.533650` (`+0.004476` vs MoleRec) with slightly worse DDI `+0.001105`.

Interpretation: there is a weak patient-conditioned ranking signal. It is useful as evidence and as a comparison reference, but it is not a paper-scale result by itself.

Routing guidance: do not repeatedly rescue the same residual-graph formulation; medication-specific computation or graph structure remains open inside a materially different architecture.

### TheraCompose-v0

Observed result: `STOP_THERACOMPOSE_V0`. Latent therapeutic intents + patient-conditioned medication interactions + structured energy/inference collapsed far below the strong baseline.

Interpretation: this kills that v0 formulation, not all latent-intent or structured-set models.

### RxDiffSet-v0

Observed result: `STOP_RXDIFFSET_V0`. Full denoising and SameK outputs remained materially below MoleRec/GraphRefine; one-step denoising approached but did not beat MoleRec.

Routing guidance: do not tune this denoising formulation further without a materially new mechanism.

### FutureGraphKD-v0

Observed result: `STOP_NO_FUTURE_STATE_SIGNAL`. Immediate-next-visit diagnosis/procedure information provided only `+0.000513` Teacher-over-Student Jaccard on the supported subset.

Interpretation: the tested privileged signal itself was weak; this is not merely a KD implementation failure.

### NeedCover

Observed result: `KILL_NEEDCOVER_MECHANISM`. Regimen-conditioned residual diagnosis-need reasoning was worse than the matched static two-pass control (`NeedCover - StaticTwoPass = -0.003773` Jaccard).

### MedState

Observed result: `KILL_PERSISTENT_MED_STATE`. Persistent per-medication latent trajectories were worse than the matched stateless relational reader; persistence itself showed no positive mechanism value in this formulation.

### RxUnitSet

Observed result: `KILL_RXUNIT_UNSUPPORTABLE_TARGET`. `(drug, dose, route)` prescription-unit semantics had high raw route/dose observability but insufficient stable admission-level unit identity and no proven strictly preceding episode context under the available canonical inputs. No model was trained.

### Modern public backbones

- HypeMed: faithful re-run substantially invalidated the simplified adapter but remained canonically weak (`HYPEMED_CANONICAL_WEAK`).
- Rx-Expert: faithful coarse model retained routing and drug features but scored `0.510522` Jaccard; `STOP_RXEXPERT_BACKBONE_RESET`.
- DMGExNet: official auxiliary whole-patient rows contain future information and `med131_new.pkl` is target-derived; `DMGEXNET_INFORMATION_BUDGET_MISMATCH`. This is not evidence that its architecture is weak.

### Residual medication-label dependence

The first conditional probe reported `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP`, but its pairwise model and ScoreOnly control learned separate calibration parameters `A,b`. It therefore did not isolate headroom above the original strong MoleRec unary surface.

The frozen-unary follow-up removed that confound:

| Surface | NLL | PRAUC | Jaccard | F1 | Precision | Recall | Mean count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MoleRec / FrozenNeutral | 0.246618 | 0.773576 | 0.529174 | 0.683480 | 0.661221 | 0.736513 | 21.545071 |
| FrozenShuffled | 0.264541 | 0.747369 | 0.518786 | 0.674247 | 0.655150 | 0.725246 | 21.492489 |
| FrozenOracle | 0.236136 | 0.762602 | 0.529430 | 0.683539 | 0.671101 | 0.718177 | 20.815023 |
| FrozenMeanField | 0.248891 | 0.767215 | 0.525737 | 0.680518 | 0.661540 | 0.730321 | 21.416901 |

Key deltas:

- `FrozenOracle - MoleRec`: Jaccard `+0.000257`, NLL `-0.010482`, PRAUC `-0.010974`.
- `FrozenOracle - FrozenShuffled`: Jaccard `+0.010644`.
- `FrozenMeanField - MoleRec`: Jaccard `-0.003437`.

Observed terminal recommendation from the actual frozen-unary run:

`DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`

Interpretation:

- visit-specific residual co-label dependence exists;
- true label context is meaningfully better than shuffled context;
- under this W-only residual formulation, privileged true-label context provides only `+0.000257` Jaccard above the original MoleRec surface;
- deployable mean-field recovery is harmful on Jaccard, NLL, and PRAUC.

Routing guidance:

- deprioritize `strong unary + pairwise residual medication correction` as the primary paper mechanism;
- do not proceed to CRF/energy/beam-search/partial-set-completion solely to recover this specific pairwise residual signal, because the measured privileged set-accuracy headroom is negligible;
- this does **not** close medication-specific interaction, structured prediction, or patient-regimen reasoning when they play a materially different role upstream or inside a new architecture.

The earlier `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP` remains valid as historical probe output from the confounded formulation, but it is not the current routing basis.

### MICA — Medication-Indexed Clinical Assembly

Observed result from the complete source-bound three-arm attribution screen: starting `origin/main` revision `dfec9fb6ebda7893168e3f0263825dd8f1fb44fc`, implementation/run revision `cd731bb0abe3dca3ebaa8a3e5346eeff74270f75`:

- SharedPool (`X → T → shared pool → F_m`) selected epoch 3: Dev Jaccard `0.532430`, F1 `0.686189`, PRAUC `0.787419`, DDI `0.077247`.
- DrugQuery (`X → T → medication-specific pool → F_m`) selected epoch 3: Dev Jaccard `0.542244`, F1 `0.695006`, PRAUC `0.792730`, DDI `0.076300`.
- MICA-Late (`X → T → F_m → medication-specific pool`) selected epoch 3: Dev Jaccard `0.541656`, F1 `0.694569`, PRAUC `0.792254`, DDI `0.075664`.
- All three arms completed 60 epochs under the same frozen configuration and `848900` parameters. Epoch-60 Dev Jaccards were SharedPool `0.458946`, DrugQuery `0.474090`, and MICA-Late `0.475597`; they are recorded as final-epoch evidence and were not substituted for selected-checkpoint metrics.
- Primary `Δ_query = DrugQuery − SharedPool = +0.009814` (meaningful, below the `0.010` strong-signal threshold).
- Secondary `Δ_film = MICA-Late − DrugQuery = −0.000588` (no material contribution).

The frozen attribution conclusion is `PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY`: medication-specific evidence selection carries the strong surface in this matched decomposition, while applying the same FiLM conditioner before pooling adds no material Dev Jaccard. This is exploratory single-seed Train/Dev evidence, not held-out evaluation, a formal Gate, or a novelty conclusion; medication/label-specific attention remains prior art.

Routing guidance: preserve DrugQuery as the MICA-Core substrate for this tested attribution and stop. Do not rerun Early, create Idea 009, open a formal Gate, or add a rescue/ablation cycle. The conclusion is local to this three-arm decomposition and does not make a novelty claim or ban other materially different medication-specific computation.

### MICA-v2 accuracy and safe-decision extension screen

Observed result: six complete single-seed Train/Dev lanes were executed after a
passing targeted preflight on the canonical `molerec-table1-c721-www23`
snapshot (`4233/10489` Train patients/visits and `1004/2130` Dev
patients/visits; exact 131-ID vocabulary).  The requested starting
`origin/main` was `dc6a7f2f9084ff51902be6674650ce36947ea6e8`.  The baseline
launch used `9aba7ba1070bda24be5541723c4870e64ee3fa77`; a proven-equivalent
runtime fix at `6d8d3fd473569a9b6425954bc0fb263657b284c9` was used only for the
invalid Core and SafeRank reruns.  This scoped mixed-revision exception is
explicit in the run result and is not collapsed into one source revision.

Environment was Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy `1.23.5`,
float32 with TF32 disabled and deterministic cuDNN, on the approved fallback
`319-lab-via-server`.  Actual GPU allocation was Core 0, FineHistory 1,
DualEvidence 2, SafeRank 3, SelfOnly 4, and SetContext 6; GPU 5 was busy with
an unrelated process and was not touched.  SafeSwap incremental and SafeRank
vectorized ranking implementations passed their scoped equivalence checks.

Selected complete-Dev rows (the run-local result also stores Train rows,
precision/recall, count standard deviation, NLL, wall time, and peak memory)
were:

| Arm | Params | Epoch | Jaccard | F1 | PRAUC | DDI | AvgMed | Epoch-60 Jaccard |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 848900 | 3 | 0.542244156 | 0.695005519 | 0.792730126 | 0.076299636 | 19.9535 | 0.474090260 |
| FineHistory | 848900 | 3 | 0.545571259 | 0.698012548 | 0.793580091 | 0.076861089 | 20.4568 | 0.474567144 |
| DualEvidence | 849285 | 3 | 0.541726823 | 0.694895597 | 0.790286786 | 0.075270373 | 20.5211 | 0.471593672 |
| SafePTO | 848900 | 3 | 0.530585641 | 0.684883786 | 0.792730126 | 0.054273453 | 19.9535 | 0.465547732 |
| SafeRank | 848900 | 3 | 0.529318395 | 0.683672466 | 0.792415427 | 0.054160684 | 19.8300 | 0.466505052 |
| SelfOnly | 981380 | 4 | 0.540036756 | 0.692749231 | 0.790218582 | 0.077534246 | 19.8662 | 0.472723310 |
| SetContext | 981380 | 4 | 0.539562262 | 0.692592812 | 0.789016459 | 0.078843891 | 19.4488 | 0.471958603 |

Interpretation from the frozen rules:

- `ΔJ_fine = +0.003327103`: `WEAK_FINE_HISTORY`, not a survivor.
- `ΔJ_dual = −0.000517333`: `KILL_DUAL_EVIDENCE`; with FineHistory weak,
  `RESET_HISTORY_REFINEMENT_FAMILY` applies.
- SafePTO versus Core is `ΔJ −0.011658515`, `ΔDDI −0.022026183`: the DDI
  reduction does not preserve enough Jaccard, so
  `NO_MICA_SAFE_DECISION_HEADROOM`.
- SafeRank versus Core is `ΔJ −0.012925762`, `ΔDDI −0.022138952`; it fails
  project survival.  SafeRank versus SafePTO is `ΔJ −0.001267247`,
  `ΔDDI −0.000112769`, so there is no material incremental value.
- SetContext versus SelfOnly is `ΔJ −0.000474494`, `ΔDDI +0.001309645`:
  `KILL_SET_CONTEXT`.

Routing guidance: keep the validated MICA-Core DrugQuery substrate and return
to a materially different architecture search.  The single frozen next route
is `KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH`.  This remains
exploratory single-seed Train/Dev evidence: no held-out evaluation, additional
seed, formal Gate, Audit, G3/G4, R0 Holdout, historical project test, rescue,
or Idea 009 was performed.  Runtime-only failed attempts are excluded from the
metrics but retained in `research/prototypes/mica-v2-screen/result.json`.

### MICA dynamic-query screen

Observed result: six complete single-seed Train/Dev lanes tested whether a
medication's query should itself change with current patient evidence. The run
used one clean revision `5083cdba2e02067f949e8a6fe0c4dcf2f323748b` on
`319-lab-via-server`, with Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy
`1.23.5`, and actual GPUs `0,1,2,3,4,6`. The canonical data-contract and
synthetic CUDA preflights passed after a scoped numerical identity fix.

Selected Dev Jaccards were Core `0.542244156`, StaticMultiQuery `0.543054168`,
GlobalDynamicMultiQuery `0.542375545`, EvidenceDynamicMultiQuery `0.542493823`,
StaticQueryAdapter `0.542281479`, and DynamicQueryAdapter `0.541552428`.
Matched deltas were GlobalDynamic−StaticMultiQuery `−0.000678623`,
EvidenceDynamic−StaticMultiQuery `−0.000560345`, and
DynamicAdapter−StaticAdapter `−0.000729051`; all are within the frozen
`0.002` no-material-contribution threshold. The complete aggregate evidence is
`research/prototypes/mica-dynamic-query-screen/result.json`.

Interpretation: neither tested dynamic route-mixture signal nor continuous
patient-conditioned query generation added material set-accuracy value above
its matched static capacity control. This does not support latent-indication,
therapeutic-mode, or causal-route claims.

Frozen conclusion: `KILL_PATIENT_CONDITIONED_QUERY_FAMILY`. Routing guidance is
`KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH`; no rescue, extra
seed, held-out evaluation, formal Gate, Audit, G3/G4, R0 Holdout, historical
test, or Idea 009 follows.

## 6. STAGE -1 consolidation (2026-09-16)

This is the current bounded state. It is exploratory Train/Dev evidence and a
protocol-readiness record, not a paper claim or a new method proposal. The
authoritative start revision was `fccd2484c10aa9cf7a48cb02504a8fa78b61dde6`;
the Stage -1 experiment source revision was
`5864011a864851c7eba1ed2a0742221c9e7dcf5f`.

### Training-dynamics diagnosis (Stage -1A)

The complete progress artifacts covered 15 arms: MICA SharedPool, DrugQuery,
and MICA-Late; MICA-v2 Core, FineHistory, DualEvidence, SelfOnly, SetContext,
and SafeRank; and all six Dynamic Query arms. SafePTO has a public aggregate
row but no epoch-level progress and was not classified. With 10,489 Train
visits and batch 16, one epoch is 656 optimizer updates; epochs 3, 4, and 60
are approximately 1,968, 2,624, and 39,360 updates. Twelve included arms peak
at epoch 3 and three at epoch 4.

Observed Train BCE and total loss continue to decrease (Train DDI loss is
recorded in the curve file), while Dev NLL rises and Dev Jaccard/PRAUC fall
after the early peak. The predeclared diagnosis is
`OVERFIT_DOMINANT`: the common recipe/encoder dynamics and rapid late
memorization explain the timing better than a DrugQuery-specific defect. This
does not change the prior DrugQuery attribution or the closed-family verdicts.
The aggregate diagnosis is
[`diagnosis.json`](../diagnostics/mica-training-dynamics/diagnosis.json), with
curves in
[`learning_curves.csv`](../diagnostics/mica-training-dynamics/learning_curves.csv).

### Training-recipe test (Stage -1B)

The three declared MICA-Core arms were complete for 60 epochs. Relative to
the constant `3e-4` anchor, constant `1e-4` selected epoch 5, raised peak
Jaccard from `0.542244` to `0.542280`, kept peak PRAUC within `0.002`
(`0.790848` versus `0.792730`), and reduced Jaccard/PRAUC drop and NLL drift
to `0.067581/0.074983/0.309206` from
`0.068154/0.078207/0.337782`. Cosine decay reduced the Jaccard/PRAUC drop
but had larger NLL drift (`0.430405`). The bounded decision is
`ADOPT_STABLE_RECIPE_FOR_STAGE_MINUS_1C` with constant AdamW `1e-4`, seed
`20260914`, and all other settings unchanged. See
[`recipe-result.json`](../prototypes/mica-core-consolidation/recipe-result.json).

### Intrinsic consolidation (Stage -1C)

Using that recipe, Core, OneClinicalBlock, NoPostReadConditioner, and
SimplifiedHead all completed 60 epochs with selected epoch 5. The public-safe
rows and rule evaluation are in
[`consolidation-result.json`](../prototypes/mica-core-consolidation/consolidation-result.json).
No control met all predeclared accuracy, parameter, and late-stability
conditions, so the result is `KEEP_EXISTING_MICA_CORE`. In particular,
NoPostReadConditioner reduced parameters and met the peak floors, but its
PRAUC drop (`0.075625`) was slightly worse than Core (`0.074983`); the linear
SimplifiedHead also missed both peak floors.

### MIMIC-IV readiness and materialization (Stage -1D/-1E)

The frozen contract defines `(D_t, P_t, H_<t) -> M_t`, where history contains
only strictly earlier visits and the current prescription-derived medication
set is target-only. It uses patient-level `2/3, 1/6, 1/6` roles, dataset-native
vocabularies, deterministic versioned NDC/formulary → RxNorm → ATC4 mapping,
the fixed MICA metric/threshold/checkpoint semantics, and a pre-training
leakage/split/DDI coverage contract.

Observed Stage -1E materialization on the approved 319 plane (adapter revision
`e87411be3df305f55a4a68d10a9db3eb505e1232`) produced 149,001 Train patients /
364,492 visits / 308,824 target-bearing examples and 37,076 Dev patients /
90,033 visits / 76,529 examples. Diagnosis, procedure, and medication target
vocabularies were fitted/reported with Train-only rules; Dev diagnosis OOV is
`0.001109`, procedure OOV `0.005854`, and medication-target OOV `0.0`.
Normalization covers `0.785936` Train and `0.785400` Dev eligible prescription
rows. The frozen 131-concept, 91-supported-concept, 448-pair SafeDrug/MoleRec
DDI authority represents 129 source concepts, retains 90 supported concepts,
and projects 443 pairs on the 173-concept Train medication vocabulary; the
projected matrix is finite, binary, symmetric, and zero-diagonal.

All required mechanical checks pass: source identity, patient disjointness,
chronology, strict history, current-target exclusion, Train-only vocabulary
fit, deterministic normalization, DDI validity, and Train/Dev serialization
reload. Test membership is sealed by count/digest only; Test medication targets
were not loaded, fitted, tuned, or evaluated. The terminal readiness is
`MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV`, recorded in the
[`public-safe manifest`](../benchmarks/mimiciv-medrec/manifest.json) and
[`mechanical checks`](../benchmarks/mimiciv-medrec/mechanical-checks.json).

The next and only authorized action is a separate review of the prepared
MIMIC-IV Train/Dev SharedPool versus MICA-Core/DrugQuery screen. Do not run it,
open Stage 0, create Idea 009, or open a formal Gate automatically.

## 7. Cross-project lessons

### Strong unary quality absorbs many local corrections

Several reranking, residual, interaction, and structured-decoding routes show real local signal but not enough incremental set accuracy above the strongest unary surface. Small local gains should not be inflated into a paper story.

### Representation complexity is not automatically recommendation quality

Faithful HypeMed and Rx-Expert are sophisticated recent architectures yet remain below MoleRec on the canonical accuracy surface. More representation machinery alone is not a research mechanism.

### Cardinality can hide ranking effects, but it is not automatically the paper

SameK diagnostics are useful to separate ranking from set-size failure. GraphRefine demonstrated a ranking effect at fixed MoleRec cardinality, while several standalone models under-prescribed. This is a diagnostic lesson, not an instruction to build another cardinality head.

### Fidelity and information budget come before baseline conclusions

The simplified HypeMed adapter was misleading; faithful code recovered `+0.082567` Jaccard over that approximation. DMGExNet showed that a high literature score may rely on a different prediction-time information budget. Baseline conclusions require semantic fidelity and comparable entitlement.

### Supportability can kill a target before modeling

Idea 007 and RxUnitSet show that some attractive supervision/target objects are not adequately supported under the available data semantics. Run cheap supportability checks when failure would truly terminate the formulation.

### Statistical dependence is not necessarily decision headroom

The frozen-unary residual probe is the clearest example: co-label dependence is measurable, but this W-only oracle context adds essentially no set-accuracy improvement above the frozen MoleRec surface.

### Failure scope must stay local

Negative evidence should prevent equivalent reruns, not prevent innovation. A component from a failed route may still be useful inside a new architecture with a different object or information flow. Do not turn memory into a novelty firewall.

## 8. Deferred open research space

After the Stage -1 next action is complete, the project may search broadly for
a genuinely different formulation. High-leverage possibilities include, but
are not limited to:

- new architecture built from scratch rather than a MoleRec correction;
- medication-specific or decision-specific clinical evidence acquisition;
- new prediction granularity or hierarchy;
- structured list/set generation where the structure is the primary model rather than a residual head;
- patient-specific conditional computation when it changes information flow rather than only capacity;
- new decoder/inference mechanisms tied to a demonstrated source of headroom or a new decision process;
- new supervision/training paradigms with supportable targets;
- coherent combinations of known primitives that create a different capability or inductive bias.

These are search directions, not requirements. Adjacent fields should be searched for mechanisms rather than fashion.

Do not assume the next model must use MoleRec, GraphRefine, hypergraphs, MoE, retrieval, medication graphs, or any previously successful component.

## 9. Next workflow

1. Review the frozen MIMIC-IV Train/Dev screen contract; implementation is
   prepared but no model run is authorized in Stage -1E.

No Stage 0, Idea 009, formal Gate, Audit, held-out Test, or additional seed
follows automatically from this handoff.
