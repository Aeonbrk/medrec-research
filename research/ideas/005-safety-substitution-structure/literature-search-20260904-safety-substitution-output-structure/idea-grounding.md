<!-- markdownlint-disable MD013 -->

# Idea Grounding — Safety by Substitution, Not Suppression

## Problem

Medication-recommendation safety work often penalizes unsafe combinations or contraindicated drugs. A lower-risk set can nevertheless arise by removing medications rather than by finding a safer alternative. Existing project history also shows that medication count and feasibility controls can explain apparent method gains.

## Mechanism candidate

A downstream method would treat safety as a constrained allocation problem:

$$
\text{unsafe action} \rightarrow \text{acceptable alternative}
$$

rather than:

$$
\text{unsafe action} \rightarrow \varnothing.
$$

The method is not yet authorized because the current data may not expose enough alternative-choice structure at ATC-3.

## Why Gate 01 comes first

The proposed mechanism predicts an output phenotype before any method is built: score mass can be split across sibling choices, or multiple sibling choices can be emitted where the observed prescription contains one.

If this phenotype is absent, rare, single-group dominated, or explained by per-medication threshold calibration, there is no reason to build a group-aware decoder or loss.

## Semantic boundary

ATC-2 sibling structure is used only to generate candidate output groups. ATC classification is not therapeutic-equivalence ground truth. A Gate 01 PASS therefore leads to semantic admission, not directly to model training.

## Research decision chain

```text
Gate 01: output-structure signature exists beyond per-med calibration?
  NO  -> stop Idea 005 route
  YES -> independent integrity audit
       -> later semantic-admission Gate only
       -> method design only if semantic admission also passes
```
