# Handoff: No Admitted Method Direction

## Current state

The repository has completed Ideas 001--005, the cross-idea research-space reorientation, B0 Cardinality Attribution, and the single bounded post-B0 exploratory literature reset.

- **Previous Idea**: `005-safety-substitution-structure`
- **Previous Idea Status**: `TERMINATED / STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **B0**: `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`
- **Current Stage**: `NO_HIGH_VALUE_DIRECTION_YET`
- **Paper Objective**: first formal method paper, targeting at least a CCF-A venue family
- **Current Active Idea**: none
- **Idea 006**: not created and not authorized
- **Current Research-Space SSOT**: `research/memory/research-space-reorientation.md`
- **Current Literature Opportunity Map**: `research/memory/literature-opportunity-map.md`
- **Post-B0 Search Folder**: `research/memory/literature-search-20260905-prescription-supervision-reset/`
- **B0 Failure Record**: `research/memory/failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md`
- **Test Split**: untouched and not authorized

## B0 decision

B0 is closed.

The frozen oracle-count diagnostic evaluated 1,220 validation visits and did **not** expose the preregistered count-mediated normalized-DDI/fidelity trade-off.

Key evidence:

- under-count prevalence: 33.77%;
- over-count prevalence: 58.44%;
- original vs oracle-count F1: 0.6881 vs 0.6981;
- `delta F1 = +0.009977`, 95% CI `[+0.0067, +0.0134]`;
- original vs oracle-count pair-normalized DDI rate: 0.044519 vs 0.044516;
- `delta DDI = -0.000002`, 95% CI `[-0.0007, +0.0007]`;
- integrity audit: `PASS`;
- test isolation: confirmed.

The decisive failure is the absence of normalized-DDI change, not merely the near-threshold F1 point estimate.

Do not rescue Axis B by changing thresholds, adding features, mining subgroups, adding a second backbone, or building a model around the same count-mediated premise.

## Post-B0 exploratory reset

The one bounded `ccf-literature-searcher / exploratory` reset searched method-capable **pre-prediction supervision** opportunities outside the closed map.

The strongest seed was `selective prescription supervision`:

> historical prescription positives are observed treatment actions, while an unprescribed medication is not automatically a proven clinical negative.

Closest-work pressure includes:

- KRAM: MedRec label-noise robustness;
- DMRNet: medication-frequency/history debiasing;
- FineMed: diagnosis-level supervision;
- WSDM 2020 and NeurIPS 2025: generic PU/MNAR implicit-feedback learning;
- current simple false-negative weighting losses.

`ccf-idea-optimizer` refined the strongest method route to **trajectory-privileged negative reliability**: use future longitudinal context only during training to attenuate low-confidence negative gradients while keeping deployment current/past-only.

`ccf-idea-reviewer` returned:

`PIVOT_WITH_RESCUE_ROUTE / DO_NOT_CREATE_IDEA_006`

Weighted score: `3.54 / 5`.

The route is not admitted because:

1. a future prescription does not establish that the medication should have been prescribed earlier;
2. current retrospective MIMIC labels cannot validate a latent clinically acceptable treatment set;
3. narrowing the claim to better fit the same observed labels makes the route vulnerable to 'generic PU/noisy-label regularization applied to MedRec';
4. no current low-cost evidence source resolves that identifiability/evaluation problem.

Strict review: `research/memory/literature-search-20260905-prescription-supervision-reset/idea-admission-review.md`.

## Current workflow decision

`NO_HIGH_VALUE_DIRECTION_YET` is the authoritative state.

This state does **not** authorize another local diagnostic. It also does not authorize `ccf-idea-optimizer` on the rejected selective-supervision seed without a changed scientific resource.

The project should remain idle at the experiment layer until a future research-space reset changes at least one binding resource:

1. **Supervision semantics** — an independently grounded multi-valid treatment or reliable-negative target at useful scale;
2. **Patient state** — clinically richer state variables sufficient to support a mechanism that diagnosis/procedure-only data cannot identify;
3. **Action resolution** — a feasible remapping with evidence that the current 131-label abstraction destroys a material decision relation.

Any future reset must compare the infrastructure cost against the closest 2023--2026 methods before authorizing another Idea.

## Publication constraint

The next Idea must plausibly support a CCF-A **method paper** with:

- a nontrivial and falsifiable problem/mechanism statement;
- a deployable method rather than a diagnostic result;
- a novelty delta after closest current work;
- strongest-simple-control comparisons;
- no clinical semantic claim without semantic admission;
- a feasible claim-support path beyond the already adaptive validation cohort;
- eventual multi-backbone / multi-setting evidence after hypothesis selection.

Do not create a benchmark, measurement, survey, or months-long feature-search project as a substitute for a method direction.

## Next owner

`ccf-pipeline-orchestrator`

Current action: **no local Agent execution is required**.

A new owner should be assigned only when the user/project deliberately changes one of the three binding resources above or supplies new evidence that reopens a recorded boundary.
