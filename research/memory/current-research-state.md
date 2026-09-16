# Current research state — 2026-09-17

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current position

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Current work: PAPER EXPERIMENT STANDARD DESIGN — PENDING
Previous work: competitive baseline fidelity review — COMPLETE
Paper claim: none
Held-out/Test use: untouched for current architecture development
```

The former `Stage -1G` name is retained only in historical artifact paths. Human-facing current state now uses descriptive research-purpose names.

## Validated development evidence

Medication-specific evidence selection remains the strongest surviving mechanism.

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV native | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Observed development verdict: `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`.

Interpretation: medication-specific clinical evidence selection has cross-dataset Train/Dev support. It is not a held-out paper result, SOTA claim, or stable safety claim.

The fixed-131 and generalized MICA implementations also passed exact no-training equivalence on the 131-medication path.

## Benchmark surfaces

- **MIMIC-III canonical-131**: established literature-compatible development/reference surface.
- **MIMIC-IV common-131**: harmonized cross-method Train/Dev surface created by exact ATC4 identity projection. It is not an official universal MIMIC-IV benchmark.
- **MIMIC-IV native-173**: frozen dataset-native benchmark and candidate robustness/generalization surface.

The final paper roles of these surfaces are not yet frozen. MIMIC-IV Test remains sealed.

## Competitive baseline fidelity review

The cleanup commit `e99e06ce3022c499525b286c2ee5781cf755e478` correctly stopped and compacted the incomplete external MIMIC-IV lanes without broad deletion or Test access.

The subsequent independent fidelity review invalidates the former external-run admission for scientific comparison:

- **ARMR**: the project runner selected the best Dev Jaccard checkpoint, while pinned official training selects the best PRAUC checkpoint and early-stops after two consecutive PRAUC declines.
- **MoleRec**: pinned official training performs an optimizer update for each visit inside each patient sequence; the project temporary runner rewrote forward/training into shuffled mini-batches of 32 with one optimizer step per batch.
- **GAMENet**: pinned official training performs per-admission optimizer updates with the official model; the temporary runner used a project-side `ProtocolGAMENet` batched implementation.
- **RETAIN**: the temporary lane used a project-side `ProtocolRETAIN` path rather than establishing an unchanged published-method execution identity.

Consequences:

- temporary MIMIC-III ARMR/MoleRec/GAMENet/RETAIN results from these runners are diagnostic only;
- stopped MIMIC-IV common-131/native-173 external lanes are diagnostic only;
- bootstrap comparisons that depend on those temporary external outputs are diagnostic only;
- no competitive-substrate verdict exists;
- the old prototype `protocol.md` and `qualification.json` are historical pre-audit records and must not be resumed as the current execution contract.

Machine-readable review: `research/prototypes/mica-competitive-substrate-calibration/fidelity-review.json`.

Scientific belief update: `research/memory/decisions/2026-09-17-competitive-baseline-fidelity-review.md`.

## Baseline evidence that remains useful

The earlier five-model MIMIC-III baseline program remains useful historical reference evidence because it used separately qualified, frozen Baseline Cores and an independent evaluator. Its approximate Jaccard results were RETAIN 0.4872, LEAP 0.4565, GAMENet 0.5034, SafeDrug 0.5142, and MoleRec 0.5269.

Those rows are not automatically final-paper results. The new paper experiment standard may change aggregation, seed, tuning, checkpoint, threshold, or final Test requirements; if so, paper-facing rows must be regenerated under the frozen final standard.

## Architecture status

Direct Partial Regimen Assignment / RSM remains an untested model-level candidate, not an admitted idea. It must not be started merely because MICA has internal mechanism signal.

Current MICA checkpoints remain development evidence. Do not spend paper-level multi-seed/Test compute on MICA until the paper experiment standard and the next architecture decision are resolved.

## Next action

Design one simple paper-oriented experimental standard that separates development evidence from paper-producing evidence and defines published-baseline fidelity, allowed adaptation, Dev tuning, checkpoint/threshold semantics, seed policy, uncertainty, metric aggregation, and Test use.

Use the independent Astra review as input, not as authority. Reconcile it against the verified project evidence above before launching any new experiment.
