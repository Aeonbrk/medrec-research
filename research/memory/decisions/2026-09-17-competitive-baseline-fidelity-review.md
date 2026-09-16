# Competitive baseline calibration invalidated by fidelity audit

## Context / Trigger

The competitive-baseline calibration attempt (historically called `Stage -1G`) was stopped and compacted at `e99e06ce3022c499525b286c2ee5781cf755e478`. The cleanup itself preserved the benchmark and MICA evidence correctly, but it left one scientific question unresolved: whether the temporary external runners were faithful enough to support direct comparison with the named published methods.

The independent review compared the project runners against the pinned official training sources for ARMR, MoleRec, and GAMENet and inspected the project-side RETAIN path.

Primary execution evidence:

- `research/prototypes/mica-competitive-substrate-calibration/stage1g_external_runner.py`
- `research/prototypes/mica-competitive-substrate-calibration/run_molerec_common131.py`
- ARMR `seucoin/armr2@c0de843.../code/train_mynet.py`
- MoleRec `yangnianzu0515/MoleRec@dd5afaf.../src/training.py`
- GAMENet `sjy1203/GAMENet@da695b4.../code/train_GAMENet.py`
- `research/prototypes/mica-competitive-substrate-calibration/fidelity-review.json`

## Decision / Belief Update

Verdict: `CLEANUP_PASS_EXTERNAL_BASELINE_ADMISSION_FAIL`.

The former external-run qualification is not accepted as a paper-comparison identity:

- ARMR temporary execution changed model-selection semantics from official best-PRAUC plus PRAUC-decline early stopping to best Dev Jaccard.
- MoleRec temporary execution changed the official per-visit optimizer-update process into shuffled batch-32 optimization through a custom batched forward path.
- GAMENet temporary execution used a project-side batched `ProtocolGAMENet` and changed the official per-admission optimization process.
- RETAIN temporary execution used a project-side `ProtocolRETAIN` path without establishing an unchanged published-method core for this calibration lane.

Therefore all temporary external results produced by this runner family, including already completed MIMIC-III runs and stopped MIMIC-IV runs, are diagnostic only. Any bootstrap interval or apparent MICA advantage that depends on those external outputs is also diagnostic only.

No competitive-substrate verdict is issued.

## Rejected Interpretations

- Do not interpret the invalidation as evidence that ARMR, MoleRec, GAMENet, or RETAIN are weak methods.
- Do not interpret the invalidation as a failure of common-131 materialization; the benchmark projection and its semantic audit remain separate evidence.
- Do not invalidate the Stage -1F MICA DrugQuery-vs-SharedPool mechanism replication; that matched experiment does not depend on the external runners.
- Do not convert the old protocol into a new one by silently patching one runner at a time. The experimental standard itself is now under redesign.
- Do not use narrow Dev bootstrap intervals to compensate for an upstream method-identity error.

## Consequences / Invariants

- The historical `protocol.md` and `qualification.json` remain provenance records but are superseded for execution.
- The earlier separately qualified five-model MIMIC-III baseline program remains useful historical reference evidence; whether those rows can appear in a final paper depends on the future frozen paper experiment standard.
- Current MICA checkpoints remain development evidence. No paper-level multi-seed/Test retraining is authorized yet.
- MIMIC-IV Test remains sealed.
- Direct Partial Regimen Assignment / RSM remains an untested candidate; this review does not authorize its implementation.
- The next research task is to define a simple paper-oriented experiment standard covering published-method identity, allowed adaptation, Dev tuning, checkpoint/threshold policy, metric aggregation, seeds/uncertainty, and final Test use before any new GPU execution.
