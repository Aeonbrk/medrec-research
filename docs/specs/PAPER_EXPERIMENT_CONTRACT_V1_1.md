# Paper Experiment Contract v1.1 amendment

Status: `CURRENT ADDITIVE AMENDMENT`
Effective date: `2026-09-17`

Read this amendment together with [`PAPER_EXPERIMENT_CONTRACT.md`](PAPER_EXPERIMENT_CONTRACT.md). It changes only the points below. All other v1.0 rules remain active.

## 1. Development effort is intentionally asymmetric

Paper fairness does **not** require equal cumulative architecture-search or hyperparameter-search budgets between the proposed method and external baselines.

The proposed method is the research object and may receive substantially greater Train/Dev development effort, including architecture search, loss/decoder design, mechanism-informed hyperparameter optimization, and bounded redesign. This asymmetry must not be described as an equal-budget search advantage.

External baselines instead receive an anti-underoptimization guarantee:

- use a trustworthy implementation and all scientifically required assets;
- preserve the method's scientific core and legal information budget;
- give it a reasonable training horizon and a declared Dev-only checkpoint/operating-point procedure;
- investigate obvious training/fidelity failures independently of whether the baseline threatens the proposed method;
- perform source-informed bounded tuning when there is a concrete reason to expect the default recipe is mismatched to the benchmark.

The default `one source/default + up to five bounded candidates` policy in v1.0 is a practical ceiling for baseline recovery/configuration screening, not a requirement that every method consume the same number of trials and not a cap on the historical research effort used to invent the proposed method.

Search continuation or early stopping for a baseline must not depend on its gap to the proposed model. A weak score is not evidence that a baseline has been sufficiently optimized; a strong score is not permission to change its rules.

The governing principle is:

> Maximize the proposed method on Train/Dev; do not handicap competitors.

## 2. Matched controls and ablations also need a fair operating point

Ablations and matched controls need not repeat the full research history of the proposed method. However, a paper may not attribute a performance gap to one mechanism when the control is materially disadvantaged by an obviously unsuitable inherited recipe.

For central mechanism controls:

- use the same legal information budget and evaluator;
- give each control a reasonable Dev-only training/selection opportunity;
- distinguish a fixed-recipe diagnostic from an independently tuned control when the distinction matters to the claim;
- narrow the attribution claim if the factor cannot be isolated without changing other important computation or information access.

## 3. Default benchmark roles

The default paper strategy is now:

- **MIMIC-III canonical-131**: main literature-facing comparison surface;
- **MIMIC-IV harmonized/common-131**: main MIMIC-IV literature-facing comparison surface;
- **MIMIC-IV native-173**: broader-target validation surface.

This role assignment is provisional until the canonical-lineage identity audit below is complete. It is chosen to reduce method-irrelevant adaptation uncertainty and improve comparison interpretability, not because one surface produces a larger observed advantage.

`Literature-facing` means compatible enough to support a controlled comparison interface. It does **not** mean that equal medication count implies equal cohort, preprocessing, split, eligibility, input semantics, or evaluator.

`Broader-target validation` means testing whether the mechanism persists when the medication universe is not restricted to the harmonized 131 space. If native-173 contains only the proposed method and internal matched controls, it supports only an internal mechanism/generalization claim. A competitive-superiority claim on native-173 requires at least one credible external comparator relevant to that claim.

Before Paper Candidate Freeze, benchmark roles may be changed only for structural scientific reasons such as target-space relevance, faithful baseline feasibility, missing required assets, or the final mechanism's dependence on long-tail/cardinality structure. They may not be changed because one observed surface is easier to win.

## 4. Harmonized-131 identity audit

Before describing MIMIC-IV harmonized/common-131 as connected to a canonical literature lineage, verify and record at least:

- exact medication code identities, not just vocabulary size;
- ATC level/code-string semantics and terminology;
- medication normalization/mapping rules to the extent reconstructable;
- zero-support coordinates and how they enter metrics/decoding;
- eligible-visit and projected-empty-target rules;
- target-cardinality consequences of projection;
- DDI identity/projection semantics;
- which similarities to published benchmarks are established and which remain unknown.

If exact cohort/preprocessing identity is not established, use names such as `MIMIC-IV harmonized-131` or `canonical-131-projected`, not language implying exact reproduction of another paper's MIMIC-IV benchmark.

## 5. Optimization target for the proposed method

Development should seek the strongest **defensible** method, not merely the largest single Dev metric. Architecture decisions should jointly consider:

- predictive effect and seed stability;
- mechanism attribution and closest-work distinction;
- DDI/cardinality behavior when relevant;
- robustness across the intended benchmark roles;
- parameter/latency/asset cost;
- whether the additional complexity creates a distinct capability rather than another correction layer.

This is a research-routing principle, not a weighted numerical objective.
