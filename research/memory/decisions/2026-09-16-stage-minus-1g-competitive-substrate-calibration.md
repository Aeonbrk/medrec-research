# Stage -1G before Stage 0: calibrate competitive substrate first

## Context / Trigger

Stage -1F established a real cross-dataset mechanism result: MICA DrugQuery improves over matched SharedPool on both frozen Train/Dev surfaces. The remaining evidence gap is external competitiveness, especially on MIMIC-IV. Existing MIMIC-III references are useful but mix historical comparison surfaces, while MIMIC-IV has no strong external method evaluated under the frozen project task.

Strong medication-recommendation papers such as MoleRec do not establish a method only through internal ablations. They pair mechanism evidence with broad, faithful external comparisons under common task semantics and report accuracy, safety, prescribing behavior, and uncertainty. More recent IJCAI/TOIS work such as ARMR, SSPNet, and HypeMed extends this norm to MIMIC-III and MIMIC-IV.

The project does not need the full final-paper benchmark before every new prototype, but it does need to know whether MICA is already clearly outclassed before investing in an MICA-derived RSM architecture.

## Decision

Insert `STAGE -1G — COMPETITIVE SUBSTRATE CALIBRATION` before Stage 0.

Stage -1G will:

1. resolve the fixed-131/generalized-MICA no-training equivalence concern;
2. qualify external baselines from primary papers and official code;
3. run exactly three faithful baseline families on both MIMIC-III and MIMIC-IV using six GPUs in parallel;
4. preserve method-appropriate training rather than forcing a common optimizer;
5. recompute common accuracy/safety metrics under the frozen task and collect basic efficiency evidence;
6. use paired patient-cluster bootstrap on Dev only as a calibration diagnostic;
7. decide whether MICA remains a credible substrate before any RSM implementation.

The preferred recent candidates are ARMR, HypeMed, and SSPNet. SSPNet is executed only if trustworthy implementation provenance can be established; otherwise an established compatible method such as GAMENet is used. Molecular methods such as SafeDrug or MoleRec require complete method-native medication asset support or an official missing-item policy before they can be admitted on MIMIC-IV.

## Rejected Alternatives

- **Start RSM immediately after Stage -1F.** Rejected because internal mechanism replication does not establish that the substrate is externally competitive on MIMIC-IV.
- **Run the full final paper benchmark now.** Rejected because multi-seed Test confirmation, exhaustive baselines, and final statistics should still be paid only after a model-level survivor exists.
- **Force every baseline to AdamW `1e-4`.** Rejected as false fairness. External methods should keep their documented optimizer/loss/training semantics while sharing the prediction task, data roles, information budget, and evaluation surface.
- **Use published MIMIC-IV numbers directly.** Rejected because recent papers use different cohorts, vocabularies, preprocessing, and information budgets. Literature scores are context, not direct project comparisons.
- **Fill all six GPUs even when a baseline is incompatible.** Rejected because compute utilization is subordinate to scientific fidelity.

## Consequences / Invariants

- Stage 0 RSM is deferred until Stage -1G terminates.
- Test, G3/G4, R0 Holdout, and historical held-out surfaces remain untouched.
- Stage -1G is one-seed Train/Dev calibration, not a SOTA claim.
- A faithful strong external baseline that materially dominates MICA on either dataset is allowed to kill or demote the MICA-derived direction.
- If MICA remains competitive across both datasets, Stage 0 may test whether direct partial regimen assignment adds a new material capability.
- Final paper evidence, if a method survives, should exceed the Stage -1G rigor with multiple training seeds, untouched Test, broader baseline coverage, decisive ablations, and final statistical evidence.

Frozen execution contract: `research/prototypes/mica-competitive-substrate-calibration/protocol.md`.
