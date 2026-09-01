<!-- markdownlint-disable MD013 -->

# Research Organization

This directory manages the core scientific lifecycle for early-stage research: `Idea → Minimal Experiment → Evidence → Decision → revise / kill / continue → Paper`.

## Directory Structure

- **`ideas/`**: The fundamental unit of early-stage research. Each active idea has its own directory (e.g., `ideas/001-tension-guided-verification/`). Each idea should clearly answer: what is the core hypothesis, what is the key uncertainty, what is the next minimal experiment, what is the existing evidence, and what is the current verdict. Idea-specific experiments, failures, and decisions stay here.
- **`baselines/`**: Research infrastructure. This includes baseline reproduction reports, preflight qualifications (`preflight/`), baseline architectural decisions (`decisions/`), and baseline-specific reproduction failures (`failures/`). Baseline reproduction is infrastructure and is separated from scientific idea failures.
- **`memory/`**: Cross-idea reusable knowledge. When an idea fails completely, or when generalizable lessons emerge, they are distilled into global memory. This includes global failure records (`failures/`), literature memory, and accumulated research experience.

## Workflow: Idea to Paper

1. **Idea Stage (`ideas/<idea-name>/`)**: A research direction starts as an idea folder containing a clear core hypothesis, key uncertainty, next minimal experiment, existing evidence, and current verdict.
2. **Minimal Experiment (Hypothesis Selection)**: Experiments here (`ideas/<idea>/experiments/`) are designed strictly for *hypothesis selection* — asking "what research decision will this change?" and seeking the cheapest disconfirming test.
   - *Code promotion rule*: Prototype scripts stay local to the idea. Only when a capability survives falsification and is reused across multiple experiments or ideas is it promoted to `src/medrec_research/` (`idea-local prototype → reusable capability → src/`).
3. **Evidence & Decision**: Audited evidence produces a clear verdict: revise hypothesis, kill the idea, or continue to the next gate.
4. **Failure & Lesson Preservation**:
   - *Idea-specific failures* remain inside `ideas/<idea-name>/` to document its experimental history.
   - *Cross-idea generalizable lessons* (e.g., negative controls, methodology pitfalls) are distilled into `memory/reusable-lessons.md` or `memory/failures/`.
5. **Mature to Paper (`papers/<paper-name>/`)**: Once an idea survives hypothesis selection and is ready to enter the manuscript stage, it graduates to a paper project.
   - Experiments in `papers/<paper>/experiments/` are *claim-support experiments* (full-scale multi-backbone runs, comprehensive ablations, robustness stress tests, statistical significance, and reviewer-requested verification). Early-stage hypothesis filtering is not repeated here.

## Source boundary

Historical memory is based on `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path named here or in a linked record refers to that revision. See the [archive evidence index](memory/archive-evidence-index.md) for the source map.

## Navigation

- [Accumulated Experience](memory/accumulated-experience.md) is the lifecycle-aware ledger for every canonical idea, experiment, and claim, including superseded early passes.
- [Literature Memory](memory/literature-memory.md) inventories every canonical paper card and preserves its archived relevance boundary.
- [Reusable Lessons](memory/reusable-lessons.md) holds cross-route controls and claim limits that new work must carry forward.
- [Decision Records](baselines/decisions/) holds authoritative decisions on baseline sources, data lineages, and protocol choices.
- [Failure Records](memory/failures/) remain the detailed non-revival boundaries for the three terminal method routes and reproduction attempts.
- [GAMENet controlled reproduction](baselines/failures/gamenet-reproduction-2026-07-13.md) records the current upstream-reproduction stop conditions. It is an operational failure record, not a method result.
- [SafeDrug Table 2 mismatch](baselines/failures/safedrug-four-model-table2-mismatch-2026-08-26.md) records the pilot four-model reproduction outcome (12/20 point intervals passed, 3/3 relationships passed, terminal verdict `completed_mismatch`).

## Current scientific state

- The SafeDrug four-model full reproduction pilot (`formal-20260826-025500`) confirmed all 3 directional relationships but matched only 12 of 20 strict point intervals, yielding `completed_mismatch`. It is succeeded by the five-model MoleRec Table 1 reproduction plan ([`../docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`](../docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md)).
- The EGSF context-conditioned selector route failed its strong-control gate. A global fixed-lambda reranker explained the apparent selector gain, including under exact medication-count control. The route remains useful as a negative benchmark and control-design lesson, not as an active method. See the [EGSF selector Failure Record](memory/failures/egsf-selector--global-scalar-reranking-dominance.md).
- The EG-TER repair-policy route failed after hard-safety and coverage filters were leveled across baselines. `D_therapeutic` retains a narrow role as a continuous diagnostic metric, subject to its validation limits; it does not establish repair-policy superiority or clinical safety. See the [EG-TER repair Failure Record](memory/failures/eg-ter-repair--hard-safety-filter-baseline-trap.md).
- The current CRC-PS calibrated action family ended at R006 with no certified action rule. R007 is blocked for that route. A change to its risk budget, correction, grid, loss, guards, utility floor, or count rule would define a new preregistered route. See the [CRC-PS R006 Failure Record](memory/failures/crc-ps-r006--conformal-risk-certificate-exhaustion.md).
- No replacement method is promoted by this memory. At the archive cutoff, Count-Preserved Slotwise Shortlist-or-Escalate had earned only a route-specific novelty check. The discovery report explicitly withheld `/research-refine` and recorded incomplete literature coverage (`idea-stage/POST_CRCPS_CONSTRAINED_DISCOVERY.md` at the source commit).
- The deployment-action, count/coverage, and under-prescription gaps remain useful problem statements, but the failed CRC-PS guarantee cannot be reused as their solution (`docs/PROJECT_SENSE.md` and `research-wiki/query_pack.md` at the source commit).
- Historical backup routes and proposed audit work are not active methods. Their status, supporting sources, and literature overlap are recorded in the [Accumulated Experience](memory/accumulated-experience.md) ledger.

## Reuse policy

Start new work with the [Accumulated Experience](memory/accumulated-experience.md), [Literature Memory](memory/literature-memory.md), [reusable lessons](memory/reusable-lessons.md), and the relevant Failure Record. Literature Memory is the archived literature floor; each new route still needs a current literature review and novelty check. Reusing an evaluation metric, control, harness, or failure taxonomy does not reactivate its parent route. A new route needs its own preregistration, comparison contract, and evidence.

## Claim limits

The archive does not establish clinical safety, therapeutic equivalence, current baseline reproducibility, or Comparison Mode readiness. It contains retrospective, proxy-based, synthetic, and adversarial evidence with route-specific limits. Those limits travel with every reused artifact.
