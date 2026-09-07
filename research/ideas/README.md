<!-- markdownlint-disable MD013 -->

# Early-Stage Research Ideas

This directory is the fundamental organizational unit for exploratory, early-stage medication recommendation research.

## Purpose

Each idea folder represents one focused scientific line before it graduates to a paper project or is terminated. The project optimizes expected scientific value per unit research time: every active Idea must expose its central uncertainty to a bounded falsification gate before architecture or publication expansion.

## Invariants for Each Idea

Every Idea must answer:

1. **Core Hypothesis**: What specific mechanism or behavior is proposed?
2. **Key Uncertainty**: What strongest simple explanation could make the mechanism false or trivial?
3. **Next Minimal Experiment**: What is the cheapest decisive test?
4. **Existing Evidence**: What empirical or literature evidence supports/constrains it?
5. **Current Verdict**: `active`, `revised`, `terminated`, or `graduated`.

## Lifecycle & code promotion

- Idea-stage prototypes and diagnostic code stay inside `research/ideas/<idea>/` until they demonstrate genuine reusable ownership.
- Generalizable negative lessons are distilled into `research/memory/`; idea-local dead ends stay with the Idea.
- A method graduates to `papers/<paper-name>/` only after hypothesis-selection gates establish a real method contribution and the project has a credible claim-support plan.
- The existing project test split and any newly quarantined claim-support split remain inaccessible until an explicitly frozen later stage authorizes them.

## Ideas index

| ID | Title | Status | Core uncertainty / terminal reason | Next minimal experiment |
| :--- | :--- | :--- | :--- | :--- |
| [`001-tension-guided-verification`](001-tension-guided-verification/README.md) | Tension-Guided Verification | **Terminated** (`STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`) | DDI/tension pressure did not add routing information beyond recommender confidence and the strong scalar control. | None; route closed under recorded boundary. |
| [`002-score-geometry-sufficiency`](002-score-geometry-sufficiency/README.md) | Score-Geometry Sufficiency | **Terminated** (`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`) | Preregistered score geometry was ordering-equivalent to raw score and supplied no new routing information. | None; no cosmetic score remapping rescue. |
| [`003-prescription-relative-confidence`](003-prescription-relative-confidence/README.md) | Prescription-Relative Confidence Residual | **Terminated** (`STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`) | Within-prescription rank/relative confidence failed after the expanded score/size/prevalence control. | None; no nonlinear same-information rescue. |
| [`004-co-selection-compatibility`](004-co-selection-compatibility/README.md) | Frequency-Corrected Co-Selection Compatibility | **Terminated** (`STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`) | Train-only NPMI co-selection compatibility did not add reliable routing value beyond the strongest simple control. | None; same-source relation-statistic substitutions are not authorized. |
| [`005-safety-substitution-structure`](005-safety-substitution-structure/README.md) | Safety-Preserving Substitution Structure | **Terminated** (`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`) | Predictive ATC sibling structure survived calibration but failed strict therapeutic semantic admission at current action resolution. | None; reopen only with materially different action semantics/evidence. |
| [`006-exposure-conditional-medication-recommendation`](006-exposure-conditional-medication-recommendation/README.md) | Exposure-Conditional Medication Recommendation | **Terminated** (`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`) | Exposure-localized training substantially reduced the frozen DDI surrogate, but failed the equal-entitlement learned-vs-direct-control gate: the direct exposure-aware reranker retained higher Recall@5. | None; no safety-loss/model rescue under the same active-exposure/DDI premise. |

## Current authoritative direction

There is currently **no active Idea**.

Idea 006 closed at Gate 01 with a valid R0 resource result but no admitted learned-method contribution. Its execution-confirmed order/eMAR infrastructure remains reusable for materially different scientific questions.

Next owner: `ccf-pipeline-orchestrator` for cross-idea consolidation and one bounded research-space reset. No Idea 007 is automatically authorized.
