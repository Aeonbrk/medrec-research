<!-- markdownlint-disable MD013 -->

# Idea 005 Review — Safety-Preserving Substitution Structure

## Verdict

`SELECT_FOR_MINIMAL_GATE_ONLY`

The method direction is worth one cheap falsification gate because it predicts a concrete error phenotype in already available validation outputs. It is not yet mature enough to justify a method implementation.

## Core hypothesis

Safety-aware multi-label recommendation may suppress a risky medication without reallocating decision mass toward another acceptable action. Before claiming that mechanism, the current ATC-3 output must first show a non-trivial sibling-group mass-allocation failure that cannot be reduced to per-medication threshold calibration.

## Why this direction survives prior failures

Ideas 001--004, EGSF, and EG-TER primarily constrain frozen-output scalar routing, weak-control comparisons, and unfair feasibility/safety baselines. They do not test whether the output space itself contains a repeated choose-one / mass-allocation failure.

The prior failures nevertheless impose two controls:

1. count and calibration effects must not be mistaken for a new mechanism;
2. a stronger simple decoder/control must be tested before a structured method is built.

Gate 01 addresses the second point with per-medication threshold calibration. Prescription-count decomposition is a later diagnostic if the route survives; it is not a Gate 01 kill rule.

## Closest-work pressure

### LEAP

LEAP already models medication-label dependencies through sequential decoding and incorporates safety knowledge in the objective. Therefore Idea 005 cannot claim that medication outputs were previously independent or that dependency-aware decoding is new.

### MSAM

MSAM already organizes medication sets into higher-level semantic units to model collective medication effects. Therefore generic medication grouping or hierarchy is not a novelty claim.

### FineMed

FineMed decomposes visit-level medication recommendation into diagnosis-aware sub-recommendations and uses medication mapping to obtain fine-grained drug-disease supervision. Therefore Idea 005 must not become a diagnosis-to-medication-group formulation.

### RES-MR and KATMed family

Recent safe-medication work already studies personalized safety boundaries and differentiable contraindication / safety knowledge. Therefore generic individualized safety or another DDI-aware loss is not a novelty claim.

### Beyond Accuracy

Beyond Accuracy makes undertreatment / clinical-goal preservation an important evaluation concern. It motivates asking whether low-risk recommendations are achieved by suppression, but it does not by itself establish the proposed output-allocation mechanism.

## Exact potential novelty delta

The only defensible downstream novelty target is:

> Existing safety-aware objectives can penalize unsafe actions without specifying where the removed decision mass should go; a method would explicitly reallocate decision mass within externally defensible alternative-choice structure rather than merely suppressing treatment.

Gate 01 does not claim this delta has been established. It tests whether the prerequisite output phenotype exists.

## Strongest objection

ATC hierarchy is not therapeutic-equivalence ground truth. Low co-occurrence is also not therapeutic substitutability. Therefore Gate 01 deliberately uses ATC-2 siblings only as candidate output groups and forbids a clinical-substitution interpretation.

If Gate 01 passes, semantic admission must be a separate gate using a small number of exposed high-support groups and external evidence. If credible semantic admission cannot be obtained cheaply, the route should stop rather than expand into a knowledge-engineering project.

## Strongest simple killer control

Dev-only per-medication threshold calibration.

If independently calibrated labels remove the material split-mass / duplicate-sibling signature on Audit, the structural story is unnecessary under the current data and representation.

## Gate 01 decision value

A negative result is useful because it removes the highest-ranked method direction at low cost before architecture work. A positive result is also useful because it identifies a concrete, auditable failure phenotype that can be carried into semantic admission and then method design.

## Known risks

- ATC-3 is coarse and may already collapse many clinically meaningful substitution decisions.
- Sibling groups may be sparse or dominated by a single pharmacological area.
- The noisy-OR diagnostic may expose score dispersion without implying a correct alternative action.
- A PASS still leaves the semantic-substitution problem unresolved.

These are Gate 01 admission risks, not reasons to add more machinery before the Gate.
