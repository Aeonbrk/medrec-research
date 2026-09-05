<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `NO_HIGH_VALUE_DIRECTION_YET`

**Paper objective**: the next surviving route must be capable of becoming the project's first formal **method paper**, targeting at least a CCF-A venue family. Pure benchmark, measurement, survey, and indefinitely exploratory work are not acceptable terminal outcomes.

**Current authorization**:

- Do **not** create Idea 006.
- Do **not** touch the test split.
- Do **not** rescue B0 with new features, models, thresholds, or subgroups.
- Do **not** start another open-ended diagnostic sequence.
- The single bounded post-B0 literature reset is complete.
- No experiment execution is currently authorized.

## Authoritative evidence base

Project evidence:

- Ideas 001--005 and formal decisions under [`research/ideas/`](../ideas/).
- Cross-route failures under [`research/memory/failures/`](failures/).
- B0 protocol and result under [`research/premise-audit/`](../premise-audit/).
- [`reusable-lessons.md`](reusable-lessons.md).

Current search evidence:

- [`literature-opportunity-map.md`](literature-opportunity-map.md).
- [`literature-search-20260905-prescription-supervision-reset/`](literature-search-20260905-prescription-supervision-reset/).
- The user-maintained `xray-papers-innovation-summary.md` remains the primary 64-paper prior supplied for this reorientation; it is not repository-owned.

## Failure landscape

### 1. Post-hoc same-action routes are strongly compressed

Ideas 001--004 and EGSF repeatedly showed that low-dimensional post-hoc observables layered on frozen predictions fail to provide robust incremental value after strong controls. This closes cosmetic resurrection of the tested score, rank, DDI/tension, and static co-selection premises.

It does **not** prove that the same raw EHR fields cannot support a materially different end-to-end objective or supervision signal.

### 2. Statistical or taxonomic structure is not clinical action semantics

Idea 005 found reproducible ATC output structure but strict semantic admission left only `C09A -> C09C`, covering 11 patients (2.79%) and one qualifying ATC-2 parent. ATC proximity, shared indication, or output regularity cannot be promoted directly into therapeutic substitution.

### 3. Rule entitlement must be symmetric

EG-TER showed that a learned policy cannot receive clinical feasibility machinery that a strong baseline is denied. Any future rule-conditioned method must beat a rule-matched control.

### 4. Certification adds an independent evidence burden

CRC-PS showed that empirical feasibility does not imply finite-sample certifiability. Certification should follow mechanism evidence rather than serve as the first novelty investment.

### 5. Cardinality does not explain the current normalized-DDI/fidelity behavior

B0 tested whether restoring reference prescription size under the unchanged frozen MoleRec ranking exposed a material fidelity-versus-DDI trade-off.

The frozen verdict was:

`FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`

Key evidence:

- 33.77% of validation visits were under-counted, but 58.44% were over-counted.
- Oracle-count reduced mean prediction size from 21.55 to 19.95.
- F1 rose from 0.6881 to 0.6981 (`delta = +0.009977`, 95% CI `[+0.0067, +0.0134]`), missing the frozen `+0.010` point floor.
- Pair-normalized DDI rate remained effectively unchanged: 0.044519 versus 0.044516 (`delta = -0.000002`, 95% CI `[-0.0007, +0.0007]`).

The decisive scientific point is not the near-threshold F1 result. The normalized DDI mechanism was absent. Absolute DDI-pair burden changed mechanically with set size, but pair-normalized interaction propensity did not.

See [`failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md`](failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md).

## Higher-order reusable constraints

### C1a — Closed: post-hoc same-information cosmetic resurrection

When predictor outputs and action semantics are frozen, replacing a failed low-dimensional observable with a nearby transform, statistic, or more expressive post-hoc function over the same tested information is not a new scientific premise.

### C1b — Open in principle: same raw data with new end-to-end supervision

A materially different training objective or supervision signal can change what is learned from the same raw EHR fields. Ideas 001--004 do not falsify that class. The 2026-09-05 reset examined the most promising such seed—selective prescription supervision—but strict review did not admit it under current evidence.

### C2 — Semantic admission precedes architecture

Therapeutic substitution, treatment obligation, contraindication resolution, acceptable alternatives, or hidden-positive claims require an independently grounded relation at the action resolution before architecture design.

### C3 — Rule entitlement must be symmetric

If an external rule is available to a proposed method, the strongest simple baseline receives it as well.

### C4 — Certification follows mechanism evidence

Do not spend the first method-paper budget on guarantees before a non-certified mechanism has earned scientific evidence.

### C5 — Separate cardinality burden from normalized interaction propensity

Changing medication count can mechanically alter absolute DDI-pair burden without altering pair-normalized DDI propensity. Any future undertreatment/safety claim must make that distinction explicit.

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen condition |
| --- | --- | --- | --- |
| Frozen-output DDI/tension scalar routing | `CLOSED` | Idea 001 | New information or action semantics, not a scalar rewrite |
| Pure score-geometry remapping | `CLOSED` | Idea 002 | Decision information must change, not numeric calibration alone |
| Within-prescription relative/rank features | `CLOSED` | Idea 003 | New supervision or non-post-hoc action formulation |
| Static train-only NPMI co-selection scalar | `CLOSED` | Idea 004 | Materially different relational semantics plus strong controls |
| Generic post-hoc contextual scalar selector | `CLOSED` | EGSF | New information source or end-to-end objective |
| ATC sibling substitution in current 131-label space | `CLOSED` | Idea 005 | Finer action resolution or independently grounded alternative-treatment mapping with material support |
| Current EG-TER repair policy | `CLOSED` | Rule-levelled comparison | Independent learned value after equal feasibility rules |
| Current CRC-PS certified action family | `CLOSED` | Frozen R006 contract | New mechanism, not certificate relaxation |
| Count-mediated treatment-preserving safety | `CLOSED` | B0 | New independently grounded coverage semantics not relying on count-to-DDI attribution |
| Generic longitudinal/trajectory modeling | `OPEN, CROWDED` | MR-DTR, DrugDoctor, HeteroMed, DMRNet and related work | A specific mechanism outside generic history use |
| Generic rule/KG/RAG/agent safety modeling | `OPEN, CROWDED` | KATMed, RES-MR, SafeRx-Agent, ATLAS and related work | Independent contribution beyond rule injection/verifier assembly |
| Generic diagnosis-aware fine-graining | `OPEN, CROWDED` | FineMed | Different decision/supervision semantics, not diagnosis mapping alone |
| Action-space granularity | `OPEN, HIGH COST / HIGH COLLISION` | Idea 005 plus GRAIN/SafeRx-Agent/RxEval/FineMed | Evidence that remapping recovers a material, method-relevant decision relation |
| Selective prescription supervision / uncertain negatives | `NOT ADMITTED` | 2026-09-05 bounded reset and strict review | Identifiable supervision/evaluation source beyond generic PU/KRAM/history controls |

`CLOSED` is always conditional on the recorded scientific premise and evidence boundary.

## Bounded reset result: selective prescription supervision

The post-B0 exploratory search asked whether the project should move from feature engineering to supervision semantics:

> An observed prescription is a positive action, but is every unprescribed medication a reliable clinical negative?

The problem boundary has real external support: current prescribing evaluation can distinguish essential therapies, acceptable alternatives, and unsafe options; current MedRec case analyses also contain examples where an out-of-ground-truth continuation is clinically plausible. Generic recommendation research, however, already has mature PU/MNAR and false-negative correction methods, while KRAM directly addresses MedRec label noise, DMRNet addresses frequency/history bias, and FineMed addresses finer supervision.

`ccf-idea-optimizer` refined the strongest route to training-time trajectory-privileged negative reliability: future longitudinal context would be used only during training to attenuate low-confidence negative gradients, while deployment remains current/past-only.

`ccf-idea-reviewer` did **not** admit the route. The core blocker is identifiability/evaluation:

- a future medication does not establish that it should have been prescribed earlier;
- current retrospective labels cannot validate a latent clinically acceptable treatment set;
- if the claim is narrowed to better agreement with the same observed labels, the contribution risks collapsing into generic noisy-label/PU regularization.

Strict review: [`literature-search-20260905-prescription-supervision-reset/idea-admission-review.md`](literature-search-20260905-prescription-supervision-reset/idea-admission-review.md), weighted score `3.54/5`, verdict `PIVOT_WITH_RESCUE_ROUTE / DO_NOT_CREATE_IDEA_006`.

## Current research judgment

`NO_HIGH_VALUE_DIRECTION_YET`

This is not a statement that medication recommendation lacks open problems. It means that, under the current executable data, accumulated failure boundaries, closest 2023--2026 work, and the requirement that the first formal project become a CCF-A-level **method** paper, no route currently deserves another implementation unit.

The next move should not be another local feature or diagnostic. A future reset must change one of the scientific resources that is currently binding the project—most plausibly supervision semantics, clinically richer patient state, or action resolution—and must first justify the added infrastructure cost against current closest work.

## Validation and test boundary

The validation cohort has been used repeatedly for route selection and is not untouched confirmatory evidence. B0 was one final bounded route-selection diagnostic under that policy.

The test split remains untouched. No test access is authorized while the project is in `NO_HIGH_VALUE_DIRECTION_YET`.
