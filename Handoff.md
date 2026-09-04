# Handoff: Pre-Idea Premise Audit

## Current state

The repository has completed the Idea 005 semantic-admission route and the subsequent cross-idea research-space reorientation.

- **Previous Idea**: `005-safety-substitution-structure`
- **Previous Idea Status**: `TERMINATED / STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **Current Stage**: `PRE_IDEA_PREMISE_AUDIT`
- **Paper Objective**: first formal method paper, targeting at least a CCF-A venue family
- **Current Active Idea**: none
- **Idea 006**: not created and not authorized
- **Current Research-Space SSOT**: `research/memory/research-space-reorientation.md`
- **Current Literature Opportunity Map**: `research/memory/literature-opportunity-map.md`
- **Current Premise Protocol**: `research/premise-audit/README.md`
- **Authorized Gate**: `B0 — Cardinality Attribution`
- **Axis A**: `BLOCKED_AT_A0_POSITIVE_TARGET`
- **Axis B**: `AUTHORIZED_B0_ONLY`
- **Test Split**: remains untouched and is not authorized for B0

## Workflow decision

The current uncertainty is not a pure literature question. It is a bounded project-local premise question:

> Under the frozen MoleRec validation predictions, does restoring the reference medication count with the unchanged score ranking recover a material amount of target fidelity while materially increasing the pair-normalized DDI rate?

This is a hypothesis-selection diagnostic only. It is not intended to become a benchmark, measurement paper, or final contribution.

## B0 frozen boundary

B0 may:

- reuse an existing restricted validation-only frozen MoleRec prediction payload;
- regenerate validation-only target-free MoleRec inference under the exact frozen identity if complete 131-medication scores are not present;
- construct the oracle-count diagnostic `TopK(score, |target medications|)`;
- compute the frozen metrics and patient-clustered bootstrap defined in `research/premise-audit/README.md`;
- commit only public-safe aggregate summary, decision, and standalone audit runner.

B0 must not:

- retrain or fine-tune a recommender;
- access or inspect the test split;
- add a second backbone;
- introduce new features, clinical mappings, action-space remapping, or hyperparameter search;
- create Idea 006;
- continue to another diagnostic if the frozen B0 gate fails.

## Decision routing

### If B0 passes

Record `PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF` and hand off to:

1. `ccf-idea-optimizer` to formulate a **deployable method** whose contribution is not oracle cardinality;
2. `ccf-idea-reviewer` to challenge novelty, mechanism, controls, and CCF-A paper viability before implementation.

Only after those gates may a new Idea folder be created.

### If B0 fails

Record `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF` and set the project state to `NO_HIGH_VALUE_DIRECTION_YET`.

Do not rescue Axis B by adding omission features, diagnosis maps, GNNs, LLMs, subgroup mining, or alternative thresholds. The next owner is `ccf-pipeline-orchestrator`, followed by at most one bounded `ccf-literature-searcher / exploratory` reset over method-capable pre-prediction supervision or action-formulation opportunities outside the closed research-space map.

## Axis A boundary

Do not execute the earlier active-to-inactive episode-counting plan. The route currently lacks an independently admitted positive therapeutic target beyond direct current-state rule applicability. A rule becoming inactive establishes permissibility, not that the medication should be recommended.

Axis A reopens only if an external source supplies a positive, temporally observable treatment relation at usable action resolution and the learned component can be evaluated beyond a rule-matched baseline.

## Publication constraint

The project is no longer optimizing for novelty in isolation. A surviving route must plausibly support a CCF-A method paper with:

- a nontrivial and falsifiable problem/mechanism statement;
- a deployable method rather than a diagnostic result;
- strongest-simple-control comparisons and symmetric rule entitlement;
- multi-baseline/multi-setting claim-support evidence only after hypothesis selection.

The current B0 diagnostic exists only to decide whether that method investment is justified.

## Next execution owner

Local repository Agent executes B0 exactly from `research/premise-audit/README.md`, then commits the public-safe protocol implementation and result artifacts. No other research execution is authorized in the same run.
