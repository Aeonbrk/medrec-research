# Current research state — 2026-09-17

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current position

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Human-facing phase: CREDIBLE REFERENCE SETUP
Paper Experiment Contract: v1.0 CURRENT
Paper claim: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Historical `Stage -1*`, Gate, Reproduction Mode, and Comparison Mode names remain provenance only. New paper-facing work is governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`

The former Unified Research Protocol v1.0/v1.1 and `baselines/registry.toml` remain historical integration/provenance records; they do not automatically certify a future paper row.

## Valid development evidence

Medication-specific evidence selection remains the strongest surviving mechanism.

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV native | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Current interpretation:

> In the tested single-seed Train/Dev comparisons, medication-specific evidence selection moved accuracy in the same favorable direction on MIMIC-III and MIMIC-IV surfaces. Stability across training randomness is not yet established.

These results are `DEVELOPMENT` evidence. They are not final-table superiority, SOTA, universal safety improvement, or a calibration claim. The fixed-131/generalized MICA implementation passed exact no-training equivalence on the 131-medication path.

## Benchmark surfaces

- **MIMIC-III canonical-131**: canonical medication-space/literature interface. Direct numerical comparability still depends on cohort, split, input, selection, and evaluator semantics. Historical Test feedback remains to be audited.
- **MIMIC-IV native-173**: frozen dataset-native surface and preferred candidate for the second main benchmark, subject to baseline feasibility and timing/feedback audits.
- **MIMIC-IV common-131**: harmonized projected compatibility surface. It changes target space/cardinality and is not the full native MIMIC-IV medication task.

Two MIMIC-IV vocabulary surfaces are not two independent datasets.

## Competitive baseline fidelity state

The cleanup and independent fidelity review remain authoritative for the failed temporary calibration runners.

Temporary project-side ARMR, MoleRec, GAMENet, and RETAIN outputs from the former Stage -1G path are diagnostic only and must not support method ranking or paper superiority claims. The invalidation does **not** mean every departure from official code is forbidden under the new contract; benchmark-specific Dev selection is allowed when declared and bounded, while changes that materially alter the scientific method/training process require equivalence evidence or a variant identity.

The earlier separately qualified five-model MIMIC-III program remains historical reference evidence, not automatic final-paper evidence.

## Architecture status

Direct Partial Regimen Assignment / structured-set prediction remains an untested candidate, not an admitted paper method.

If pursued, its question must be framed around explicit set-level competition, variable cardinality, and uniqueness in training/decoding—not the false claim that independent-label models contain no medication dependence, and not an unsupported claim that anonymous slots are clinical regimen roles.

A 2×2 evidence-by-decoder experiment is preferred only when the two factors can be independently manipulated without changing information access or introducing confounds. Otherwise use narrower matched controls.

## Current bounded audits

Three audits are active decision dependencies, not one global training gate:

1. **Prediction-time semantics** — establish what current diagnosis/procedure timing supports in the claim language.
2. **Evaluation feedback history** — establish MIMIC-III/MIMIC-IV Test exposure and whether claimed confirmation populations are known to overlap at patient/record level; unknown remains unknown.
3. **MIMIC-IV native-173 baseline feasibility** — for relevant external methods, distinguish mechanical output-space adaptation from missing scientific assets or a scientific rewrite.

Only resolve the unknowns that can change the experiment being launched.

## Near-term experiment routing after relevant audits

Once the MIMIC-III task/evaluator/selection profile is fixed, a three-seed SharedPool-vs-DrugQuery stability experiment is authorized as an architecture-decision experiment without waiting for unrelated native-173 or SSPNet work.

A source-backed baseline recovery run may start once that method's Method Card, benchmark profile, reference-sanity conditions, and bounded Dev selection are frozen.

A structured-set prototype must wait until the closest-work computational distinction and minimum model definition are clear.

With eight GPUs, a useful later parallel layout is six MIMIC-III MICA stability runs plus two independent credible baseline recovery lanes, but GPU occupancy is not a requirement and unresolved experiments should not be launched merely to fill devices.

## Final evidence boundary

A result can be final-table eligible without being an untouched confirmation result. Every paper-facing evaluation surface must declare its feedback status. The primary confirmatory conclusion for a new method should have at least one population that did not feed back into model/protocol selection when such a population can be supported honestly.

MIMIC-IV Test remains the highest-value currently sealed confirmation surface. Do not access it during Credible Reference Setup or Architecture Hypothesis Testing.

## Next action

Execute the bounded audits above and create Method Cards only for baselines that are about to be recovered. Do not resume the invalidated temporary runners or start broad baseline sweeps.
