<!-- markdownlint-disable MD013 -->

# Current Research State — 2026-09-15

This file is the authoritative **current scientific synthesis and routing state** for `medrec-research`. It does not replace run-local evidence; it reconciles it.

## 1. Current phase

```text
Active formal Idea: none
Ideas 001--008: terminated
Idea 009: not created
Active formal Gate: none
Modern-backbone calibration: complete
Interaction-first residual family: closed as a primary direction
Current action: architecture-first open search
```

No named new architecture is pre-approved. The next candidate should emerge from a step-back search, not from attachment to MoleRec, GraphRefine, HypeMed, Rx-Expert, RCER, or any other existing formulation.

According to the current recorded evidence, G3/G4, R0 Holdout, and the historical project test remain quarantined from the recent exploratory prototype sequence.

## 2. Evidence hierarchy

When summaries conflict:

1. run-local result JSON / audit / source-bound README is authoritative for that run;
2. this file is authoritative for current cross-project interpretation;
3. current indexes and `Handoff.md` summarize this file;
4. older search, review, authorization, literature, and reorientation documents are historical snapshots.

A historical `CLOSED`, `CROWDED`, `PRIOR ART`, or `NOT AUTHORIZED` label applies to its dated formulation and workflow state. It is not a permanent ban on an architectural primitive.

## 3. Canonical comparison anchors

| Surface | Jaccard | F1 | PRAUC | DDI | AvgMed | Current role |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 | strong simple canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 | current executed admissible Train/Dev ceiling; **not** an active paper direction |
| HypeMed-LeakageSafe | 0.512112 | 0.668091 | 0.753822 | 0.059404 | 23.6549 | faithful recent baseline/reference; accuracy too weak for backbone reset |
| HypeMed-OfficialSemantics | 0.514256 | 0.670078 | 0.755615 | 0.059559 | 23.5770 | faithful sensitivity/reference, not canonical comparison surface |
| Rx-Expert coarse | 0.510522 | 0.666965 | 0.757858 | 0.077303 | 22.4268 | faithful recent architecture-family reference; not a new backbone |
| DMGExNet | — | — | — | — | — | literature/architecture reference only; canonical numerical comparison blocked by information-budget mismatch |

The old HypeMed-inspired `0.431689` result is `SUPERSEDED_NON_FAITHFUL_HYPEMED_ADAPTER` and must never be presented as canonical HypeMed performance.

`MODERN_BACKBONE_CALIBRATION_COMPLETE`: do not continue hunting public backbones without a specific scientific reason. A strong baseline is a comparator, not a mandatory substrate for the next model.

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

- Sequential HyperEdit: `STOP_HYPEREDIT`; Jaccard `0.497527`, DDI `0.064668`, severe under-prescription.
- Retrieval-only fusion: small movement around MoleRec.
- `GraphRefine-SameK`: Jaccard `0.533650` (`+0.004476` vs MoleRec) with slightly worse DDI `+0.001105`.
- Interpretation: there is a weak patient-conditioned ranking signal, but the effect is too small to justify a paper direction and later interaction-first evidence does not support repeated residual-graph rescue.

### TheraCompose-v0

`STOP_THERACOMPOSE_V0`. Latent therapeutic intents + patient-conditioned medication interactions + structured energy/inference collapsed far below the strong baseline. This kills that v0 formulation, not all latent-intent or structured-set models.

### RxDiffSet-v0

`STOP_RXDIFFSET_V0`. Full denoising and SameK outputs remained materially below MoleRec/GraphRefine; one-step denoising approached but did not beat MoleRec. Do not tune this denoising formulation further without a materially new mechanism.

### FutureGraphKD-v0

`STOP_NO_FUTURE_STATE_SIGNAL`. Immediate-next-visit diagnosis/procedure information provided only `+0.000513` Teacher-over-Student Jaccard on the supported subset. The signal itself was weak; this is not merely a KD failure.

### NeedCover

`KILL_NEEDCOVER_MECHANISM`. Regimen-conditioned residual diagnosis-need reasoning was worse than the matched static two-pass control (`NeedCover - StaticTwoPass = -0.003773` Jaccard).

### MedState

`KILL_PERSISTENT_MED_STATE`. Persistent per-medication latent trajectories were worse than the matched stateless relational reader; persistence itself showed no positive mechanism value in this formulation.

### RxUnitSet

`KILL_RXUNIT_UNSUPPORTABLE_TARGET`. `(drug, dose, route)` prescription-unit semantics had high raw route/dose observability but insufficient stable admission-level unit identity and no proven strictly preceding episode context under the available canonical inputs. No model was trained.

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

Current interpretation:

- visit-specific residual co-label dependence **exists**;
- true label context is meaningfully better than shuffled context;
- but almost none of that dependence provides set-accuracy headroom beyond the original MoleRec unary surface;
- deployable mean-field recovery is harmful on Jaccard, NLL, and PRAUC.

Family-level decision: `CLOSE_INTERACTION_FIRST_FAMILY`.

Mechanistic note: `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`.

The earlier `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP` is retained as historical probe evidence but is superseded for routing by the frozen-unary identification result. Do **not** proceed to CRF/energy/beam-search/partial-set-completion rescue solely to recover this pairwise residual signal; the privileged Oracle ceiling itself is too small.

## 6. Cross-project lessons

### Strong unary quality dominates many local corrections

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

The frozen-unary residual probe is the clearest example: co-label dependence is measurable, but the original strong unary has already absorbed nearly all set-accuracy-relevant benefit.

### Failure scope must stay local

Negative evidence should prevent equivalent reruns, not prevent innovation. A component from a failed route may still be useful inside a new architecture with a different object or information flow. Do not turn memory into a novelty firewall.

## 7. Open research space

The project should now search broadly for a genuinely different formulation. High-leverage possibilities include, but are not limited to:

- new architecture built from scratch rather than a MoleRec correction;
- medication-specific or decision-specific clinical evidence acquisition;
- new prediction granularity or hierarchy;
- structured list/set generation where the structure is the primary model rather than a residual head;
- patient-specific conditional computation when it changes information flow rather than only capacity;
- new decoder/inference mechanisms tied to a demonstrated source of headroom;
- new supervision/training paradigms with supportable targets;
- coherent combinations of known primitives that create a different capability.

These are search directions, not requirements. Adjacent fields should be searched for mechanisms rather than fashion.

Do not assume the next model must use MoleRec, GraphRefine, hypergraphs, MoE, retrieval, medication graphs, or any previously successful component.

## 8. Next workflow

1. Step back and perform broad method/closest-family search, including adjacent structured prediction and recommendation work.
2. Converge to **one** Rank-1 candidate with a concrete scientific mechanism.
3. Check enough literature to avoid an obvious duplicate and identify the strongest control; do not demand a full novelty proof before a cheap prototype.
4. Run one seed / one main config on Train/Dev with the strongest relevant baseline and a decisive mechanism ablation.
5. Continue only for material signal; allow at most one bounded redesign when the result identifies a concrete hidden failure.
6. For a survivor, perform rigorous primary-source novelty/closest-work verification, stronger baselines, multiple seeds, formal experiment design, and untouched evaluation.

The governing principle is:

> Search broadly, execute narrowly, and kill weak directions quickly. Spend rigor on survivors, not ceremony on weak candidates.
