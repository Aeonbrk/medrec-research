<!-- markdownlint-disable MD013 -->

# Search Notes — Safety Substitution and Output Structure

## Search objective

Resolve whether the proposed direction is merely a restatement of medication-label dependency, hierarchy-aware recommendation, diagnosis-specific recommendation, or generic safety regularization.

## Search conclusions used for Gate 01

1. Dependency-aware medication generation is old enough that no novelty can rest on replacing independent labels with a structured decoder. LEAP is a direct anchor.
2. Medication grouping / collective abstraction is also occupied; MSAM is a current close work.
3. Diagnosis-side decomposition is occupied by FineMed and therefore should not define the group semantics for Idea 005.
4. Personalized safety and rule-aware training are occupied by recent work such as RES-MR and KATMed.
5. Undertreatment is a legitimate safety-evaluation concern, but the current route must demonstrate a mechanism-specific error signature rather than optimizing a self-defined coverage metric.

## Important negative finding

No retained close work in the reviewed set directly establishes the specific combination:

```text
safety pressure
-> explicit alternative-choice decision mass reallocation
-> versus suppression
```

as the central mechanism in the current ATC-3 EHR MedRec setting.

This is a search-scoped novelty statement, not proof of universal novelty.

## Gate implication

Because semantic therapeutic alternatives are not yet established, Gate 01 must not use literature or ATC hierarchy to assert equivalence. It should first test the purely observable output-structure premise and defer semantic admission.
