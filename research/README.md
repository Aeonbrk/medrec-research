<!-- markdownlint-disable MD013 -->

# Research Memory

This directory holds the curated scientific state carried from the read-only `New-Search` Research Archive. It records what the archive supports, what failed, what remains reusable, and which claims remain unresolved. It is not a workflow log or an artifact dump.

## Source boundary

This memory is based on `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path named here or in a linked record refers to that revision. See the [archive evidence index](archive-evidence-index.md) for the source map.

## Navigation

- [Accumulated Experience](accumulated-experience.md) is the lifecycle-aware ledger for every canonical idea, experiment, and claim, including superseded early passes.
- [Literature Memory](literature-memory.md) inventories every canonical paper card and preserves its archived relevance boundary.
- [Reusable Lessons](reusable-lessons.md) holds cross-route controls and claim limits that new work must carry forward.
- [Decision Records](decisions/) holds authoritative decisions on baseline sources, data lineages, and protocol choices.
- [Failure Records](failures/) remain the detailed non-revival boundaries for the three terminal method routes and reproduction attempts.
- [GAMENet controlled reproduction](failures/gamenet-reproduction-2026-07-13.md) records the current upstream-reproduction stop conditions. It is an operational failure record, not a method result.
- [SafeDrug Table 2 mismatch](failures/safedrug-four-model-table2-mismatch-2026-08-26.md) records the pilot four-model reproduction outcome (12/20 point intervals passed, 3/3 relationships passed, terminal verdict `completed_mismatch`).

## Current scientific state

- The SafeDrug four-model full reproduction pilot (`formal-20260826-025500`) confirmed all 3 directional relationships but matched only 12 of 20 strict point intervals, yielding `completed_mismatch`. It is succeeded by the five-model MoleRec Table 1 reproduction plan ([`../docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`](../docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md)).
- The EGSF context-conditioned selector route failed its strong-control gate. A global fixed-lambda reranker explained the apparent selector gain, including under exact medication-count control. The route remains useful as a negative benchmark and control-design lesson, not as an active method. See the [EGSF selector Failure Record](failures/egsf-selector.md).
- The EG-TER repair-policy route failed after hard-safety and coverage filters were leveled across baselines. `D_therapeutic` retains a narrow role as a continuous diagnostic metric, subject to its validation limits; it does not establish repair-policy superiority or clinical safety. See the [EG-TER repair Failure Record](failures/eg-ter-repair.md).
- The current CRC-PS calibrated action family ended at R006 with no certified action rule. R007 is blocked for that route. A change to its risk budget, correction, grid, loss, guards, utility floor, or count rule would define a new preregistered route. See the [CRC-PS R006 Failure Record](failures/crc-ps-r006.md).
- No replacement method is promoted by this memory. At the archive cutoff, Count-Preserved Slotwise Shortlist-or-Escalate had earned only a route-specific novelty check. The discovery report explicitly withheld `/research-refine` and recorded incomplete literature coverage (`idea-stage/POST_CRCPS_CONSTRAINED_DISCOVERY.md` at the source commit).
- The deployment-action, count/coverage, and under-prescription gaps remain useful problem statements, but the failed CRC-PS guarantee cannot be reused as their solution (`docs/PROJECT_SENSE.md` and `research-wiki/query_pack.md` at the source commit).
- Historical backup routes and proposed audit work are not active methods. Their status, supporting sources, and literature overlap are recorded in the [Accumulated Experience](accumulated-experience.md) ledger.

## Reuse policy

Start new work with the [Accumulated Experience](accumulated-experience.md), [Literature Memory](literature-memory.md), [reusable lessons](reusable-lessons.md), and the relevant Failure Record. Literature Memory is the archived literature floor; each new route still needs a current literature review and novelty check. Reusing an evaluation metric, control, harness, or failure taxonomy does not reactivate its parent route. A new route needs its own preregistration, comparison contract, and evidence.

## Claim limits

The archive does not establish clinical safety, therapeutic equivalence, current baseline reproducibility, or Comparison Mode readiness. It contains retrospective, proxy-based, synthetic, and adversarial evidence with route-specific limits. Those limits travel with every reused artifact.
