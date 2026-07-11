<!-- markdownlint-disable MD013 -->

# Research Memory

This directory holds the curated scientific state carried from the read-only `New-Search` Research Archive. It records what the archive supports, what failed, what remains reusable, and which claims remain unresolved. It is not a workflow log or an artifact dump.

## Source boundary

This memory is based on `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path named here or in a linked record refers to that revision. See the [archive evidence index](archive-evidence-index.md) for the source map.

## Current scientific state

- The EGSF context-conditioned selector route failed its strong-control gate. A global fixed-lambda reranker explained the apparent selector gain, including under exact medication-count control. The route remains useful as a negative benchmark and control-design lesson, not as an active method. See the [EGSF selector Failure Record](failures/egsf-selector.md).
- The EG-TER repair-policy route failed after hard-safety and coverage filters were leveled across baselines. `D_therapeutic` retains a narrow role as a continuous diagnostic metric, subject to its validation limits; it does not establish repair-policy superiority or clinical safety. See the [EG-TER repair Failure Record](failures/eg-ter-repair.md).
- The current CRC-PS calibrated action family ended at R006 with no certified action rule. R007 is blocked for that route. A change to its risk budget, correction, grid, loss, guards, utility floor, or count rule would define a new preregistered route. See the [CRC-PS R006 Failure Record](failures/crc-ps-r006.md).
- No replacement method is promoted by this memory. At the archive cutoff, Count-Preserved Slotwise Shortlist-or-Escalate had earned only a route-specific novelty check. The discovery report explicitly withheld `/research-refine` and recorded incomplete literature coverage (`idea-stage/POST_CRCPS_CONSTRAINED_DISCOVERY.md` at the source commit).
- The deployment-action, count/coverage, and under-prescription gaps remain useful problem statements, but the failed CRC-PS guarantee cannot be reused as their solution (`docs/PROJECT_SENSE.md` and `research-wiki/query_pack.md` at the source commit).

## Reuse policy

Start new work with the [reusable lessons](reusable-lessons.md) and the relevant Failure Record. Reusing an evaluation metric, control, harness, or failure taxonomy does not reactivate its parent route. A new route needs its own novelty check, preregistration, comparison contract, and evidence.

## Claim limits

The archive does not establish clinical safety, therapeutic equivalence, current baseline reproducibility, or Comparison Mode readiness. It contains retrospective, proxy-based, synthetic, and adversarial evidence with route-specific limits. Those limits travel with every reused artifact.
