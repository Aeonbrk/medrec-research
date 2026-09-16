# Current research state — 2026-09-17

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current position

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Human-facing phase: CREDIBLE REFERENCE SETUP
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
Paper claim: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Historical `Stage -1*`, Gate, Reproduction Mode, and Comparison Mode names remain provenance only. New paper-facing work is governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`

The former Unified Research Protocol v1.0/v1.1 and `baselines/registry.toml` remain historical integration/provenance records; they do not automatically certify a future paper row.

## Development philosophy

The proposed method may receive substantially greater Train/Dev research effort than external baselines. Equal cumulative architecture/HPO budgets are not a fairness requirement.

Fairness requires that a competitor is not weakened by our execution choices: trustworthy method identity, required assets, legal information budget, reasonable training horizon, declared Dev-only checkpoint/operating-point selection, and source-informed investigation of obvious failures. Baseline tuning is an anti-underoptimization safeguard, not a symmetric-search requirement.

Central ablations and matched controls also need a reasonable Dev selection opportunity when mechanically reusing the full model's recipe would materially disadvantage them.

## Valid development evidence

Medication-specific evidence selection remains the strongest surviving mechanism.

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV native | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Current interpretation:

> In the tested single-seed Train/Dev comparisons, medication-specific evidence selection moved accuracy in the same favorable direction on MIMIC-III and MIMIC-IV surfaces. Stability across training randomness is not yet established.

These results are `DEVELOPMENT` evidence. They are not final-table superiority, SOTA, universal safety improvement, or a calibration claim. The fixed-131/generalized MICA implementation passed exact no-training equivalence on the 131-medication path.

## Benchmark strategy

Default paper routing is now:

- **MIMIC-III canonical-131**: main literature-facing comparison surface.
- **MIMIC-IV harmonized/common-131**: default main MIMIC-IV literature-facing comparison surface, pending canonical-lineage identity audit.
- **MIMIC-IV native-173**: broader-target validation surface.

`Literature-facing` does not mean identical benchmark identity. Equal medication count does not establish equal cohort, preprocessing, split, eligibility, input semantics, or evaluator.

Before Paper Candidate Freeze, benchmark roles may change only for structural reasons such as faithful-baseline feasibility, missing scientific assets, target-space relevance, or the final mechanism's dependence on long-tail/cardinality structure. They may not change because one observed surface is easier to win.

The MIV harmonized/common-131 lineage audit must compare exact medication identities, ATC terminology/semantics, mapping rules where reconstructable, zero-support coordinates, eligible-visit/projected-empty rules, cardinality changes, DDI identity/projection, and what is actually known to match published benchmark lineages.

Native-173 with only internal controls supports an internal mechanism/broader-target claim. Competitive superiority on native-173 requires at least one credible external comparator relevant to the claim.

Two MIMIC-IV vocabulary surfaces are not two independent datasets.

## Competitive baseline fidelity state

Temporary project-side ARMR, MoleRec, GAMENet, and RETAIN outputs from the former Stage -1G path are diagnostic only and must not support method ranking or paper superiority claims. The invalidation does **not** mean every departure from official code is forbidden. Benchmark-specific Dev selection is allowed when declared and bounded, while changes that materially alter scientific method/training semantics require equivalence evidence or a variant identity.

The earlier separately qualified five-model MIMIC-III program remains historical reference evidence, not automatic final-paper evidence.

## Architecture status

Direct Partial Regimen Assignment / structured-set prediction remains an untested candidate, not an admitted paper method.

If pursued, its question must be framed around explicit set-level competition, variable cardinality, and uniqueness in training/decoding—not the false claim that independent-label models contain no medication dependence, and not an unsupported claim that anonymous slots are clinical regimen roles.

A 2×2 evidence-by-decoder experiment is preferred only when the two factors can be independently manipulated without changing information access or introducing confounds. Otherwise use narrower matched controls.

The proposed method should be optimized toward the strongest defensible form, considering predictive effect, seed stability, mechanism clarity, closest-work distinction, DDI/cardinality behavior when relevant, robustness, and cost—not only the largest single Dev metric.

## Current bounded dependencies

These are scoped dependencies, not one global training gate:

1. **MIMIC-III evaluator/selection freeze** — enough to launch SharedPool-vs-DrugQuery stability.
2. **MIV harmonized-131 canonical-lineage audit** — enough to justify its paper-facing role and naming.
3. **Baseline Method Cards/recovery** — source-backed MoleRec and ARMR first; each may start independently when its identity, reference-sanity conditions, and selection procedure are frozen.
4. **Prediction-time semantics / evaluation-feedback history** — continue only where the result can change an upcoming experiment or manuscript claim.
5. **Structured-set closest-work boundary** — required before expensive RSM/set-model training.

## Near-term experiment routing

Once dependency 1 is complete, run:

```text
MIMIC-III SharedPool × 3 development seeds
MIMIC-III DrugQuery × 3 development seeds
```

This is an architecture-decision stability test, not final paper confirmation.

With eight GPUs, the six MICA stability runs may execute in parallel. The remaining two GPUs may run credible MoleRec/ARMR recovery when those paths are ready. GPU occupancy is not a goal; do not launch unresolved work merely to fill devices.

## Final evidence boundary

A result can be final-table eligible without being an untouched confirmation result. Every paper-facing evaluation surface must declare its feedback status. The primary confirmatory conclusion for a new method should have at least one population that did not feed back into model/protocol selection when such a population can be supported honestly.

MIMIC-IV Test remains the highest-value currently sealed confirmation surface. Do not access it during Credible Reference Setup or Architecture Hypothesis Testing.

## Next action

Finish only the bounded dependencies required for the first credible parallel experiment wave: MIII evaluator/selection freeze, harmonized-131 identity audit, and source-backed MoleRec/ARMR Method Cards/recovery. Do not resume invalidated runners or start broad baseline sweeps.
