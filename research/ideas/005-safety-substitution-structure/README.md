<!-- markdownlint-disable MD013 -->

# Idea 005: Safety-Preserving Substitution Structure

- **Idea ID**: `005-safety-substitution-structure`
- **Status**: `GATE_01_PASSED / SEMANTIC_ADMISSION_PENDING`
- **Scientific stage**: Idea / hypothesis selection
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Primary method direction**: safety by substitution, not suppression
- **Gate 01**: [`experiments/gate-01-output-structure-signature.md`](experiments/gate-01-output-structure-signature.md)
- **Gate 01 Summary**: [`experiments/gate-01-summary.json`](experiments/gate-01-summary.json)
- **Integrity Audit**: [`experiments/gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md) (`INTEGRITY_PASS`)
- **Research Decision**: [`research-decision.md`](research-decision.md) (`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`)
- **Design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Literature grounding**: [`literature-search-20260904-safety-substitution-output-structure/`](literature-search-20260904-safety-substitution-output-structure/)
- **Strict idea review**: [`idea-review.md`](idea-review.md)
- **Gate 02**: `NOT_AUTHORIZED`
- **Test split**: remains unindexed, unpredicted, and untouched

## Scientific question

The candidate paper direction asks whether safety-aware medication recommendation should redirect a risky medication decision toward an acceptable alternative rather than merely removing medication probability mass.

The immediate uncertainty is more basic:

$$
\boxed{\text{Does the existing ATC-3 output space exhibit a reproducible alternative-choice mass-allocation failure at all?}}
$$

Gate 01 therefore does not train a new model and does not claim clinical substitutability. It tests whether frozen MoleRec produces two prespecified sibling-group error signatures that remain after the strongest cheap calibration control.

## Why this is materially different from Ideas 001--004

Ideas 001--004 tested low-dimensional observables or transformations on a frozen recommender for medication-level routing. Their repeated scoped failures lower the expected value of another scalar/context reranker.

Idea 005 instead asks about the structure of the multi-label output itself. The proposed downstream mechanism, if admitted, would change how prediction mass is allocated among alternative actions under safety pressure. Gate 01 is only a premise test for that method direction.

## Candidate group semantics

The current executable medication vocabulary is ATC-3. For Gate 01 only, medications sharing the same three-character ATC-2 prefix form an **ATC-2 sibling candidate group** when at least two ATC-3 codes are present in the frozen vocabulary.

This grouping is an output-space probe, not a therapeutic-equivalence definition:

$$
\text{same ATC-2 parent} \not\Rightarrow \text{clinically substitutable}.
$$

No clinical safety, treatment obligation, indication equivalence, or therapeutic interchangeability claim is authorized at Gate 01.

## Falsifiable mechanism premise

For a sibling group $G$ with frozen MoleRec scores $p_m$, define the diagnostic aggregate

$$
S_G = 1-\prod_{m\in G}(1-p_m).
$$

$S_G$ is a noisy-OR-style diagnostic score only. It is not interpreted as a calibrated probability.

Among visits whose observed prescription contains exactly one member of $G$, Gate 01 tests two mutually exclusive signatures:

### Split-mass false negative

The observed group member is not predicted, no member of $G$ is predicted, but

$$
S_G\ge0.5.
$$

### Duplicate-sibling false positive

The observed group member is predicted and at least one additional non-target sibling in $G$ is also predicted.

If these signatures are material under the frozen threshold and remain material after Dev-only per-medication threshold calibration, the output-structure premise survives. If not, the route stops before any group-aware decoder or loss is built.

## Strongest simple killer control

The strongest cheap control is **Dev-only per-medication threshold calibration**. Each medication threshold is chosen independently on the fresh Dev partition to maximize medication-level F1, with deterministic tie-breaking, then frozen before Audit.

This control directly tests whether the proposed structural signature is merely a per-label calibration artifact.

If the calibrated policy no longer satisfies the preregistered materiality conditions, Gate 01 terminates with:

`STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION`

No architecture rescue is authorized.

## Cheapest decisive experiment

One validation-only Gate 01 using one frozen MoleRec checkpoint:

1. stage validation-only contexts and targets without indexing test;
2. run the frozen target-free Comparison adapter once;
3. verify the adapter prediction set is exactly the set of vocabulary scores at threshold `0.5`;
4. create a fresh patient-disjoint Dev/Audit split with seed `2005`;
5. fit per-medication thresholds on Dev only;
6. evaluate raw and calibrated sibling-group signatures on Audit;
7. apply the frozen mechanical decision tree.

No retraining, multi-backbone comparison, LLM inference, external guideline mapping, ATC-4 rebuild, or test evaluation is authorized.

## What PASS would mean

`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION` means only:

> Under the frozen MoleRec ATC-3 validation setting, a material ATC-2-sibling output-structure error signature remains after Dev-only per-medication threshold calibration.

PASS authorizes only a later semantic-admission question: whether the exposed high-support groups contain enough externally defensible therapeutic alternatives to support the intended safety-by-substitution method claim.

## What PASS would not prove

PASS would not prove:

- ATC siblings are therapeutic substitutes;
- observed prescriptions are clinically optimal;
- the signatures are caused by DDI training;
- safety optimization causes undertreatment;
- a group-aware decoder or loss will improve recommendation;
- clinical safety or patient benefit;
- cross-backbone or test-set generalization.

## Stop boundary

Any Gate 01 stop closes this output-structure route under the current ATC-3 representation. Do not rescue it by switching to ATC-4, mining a new co-occurrence relation, adding a hierarchy model, changing the group-mass formula, adding more signatures, or training a group-aware architecture after inspecting the result.

Gate 02 remains `NOT_AUTHORIZED` even on PASS until Gate 01 evidence is independently audited and a new protocol is explicitly approved.
