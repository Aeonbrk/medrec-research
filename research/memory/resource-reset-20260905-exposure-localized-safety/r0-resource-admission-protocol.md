<!-- markdownlint-disable MD013 -->

# R0 — Exposure Resource & Premise Admission Protocol

## Status

`AUTHORIZED_RESOURCE_GATE`

This is a single bounded resource/premise gate before Idea creation.

No Idea 006 exists. No model training is authorized. No current project test split may be accessed.

## Decision question

Can raw MIMIC-IV support a method paper in which medication-order recommendation conditions DDI pressure on a pre-order, execution-confirmed active medication state, and is the resulting safety semantic materially different from visit-union DDI co-membership?

R0 answers resource feasibility and the minimum semantic premise together so that the project does not enter another diagnostic sequence.

## Required raw resources

Minimum hospital-wide tables:

- `patients`;
- `admissions`;
- `prescriptions`;
- `pharmacy`;
- `poe` and, if needed for medication-order identity, `poe_detail`;
- `emar`;
- `emar_detail`.

`inputevents`, `labevents`, `chartevents`, and other richer patient-state tables are optional for R0 and must not become additional gate requirements.

Use the locally available authorized MIMIC-IV version. Do not download a new private dataset as part of this gate. Record the version publicly; keep local paths private.

## Immediate patient-level quarantine

Before computing any scientific aggregate beyond table/schema counts, create a deterministic patient split from `subject_id` only:

```text
u = int(SHA256(f"{subject_id}|exposure-reset-20260905").hexdigest()[:8], 16) / 0xffffffff
Discovery: 0.00 <= u < 0.70
Dev:       0.70 <= u < 0.85
Holdout:   0.85 <= u <= 1.00
```

R0 scientific aggregates use **Discovery only**.

Dev is not used in R0.

Holdout membership may be assigned, but no Holdout medication, feature, target, DDI, or performance aggregate may be inspected. This new quarantine is independent of, and does not authorize access to, the existing project test split.

## Operational definitions

R0 must remain source-semantic and conservative.

### Medication request / order event

Use the documented medication request/order linkage available in the local MIMIC-IV version. Record which fields define:

- event time;
- hospitalization;
- medication identity;
- linkage to pharmacy/order records.

Do not infer an order time from later administration timestamps.

### Execution-confirmed active medication

For medication $m$ at order decision time $t$, online-state feasibility requires a construction that uses only information available on or before $t$.

At minimum, an execution-confirmed medication must have:

1. a medication order/request initiated before $t$;
2. at least one linked or medication-identity-matched eMAR administration before $t$;
3. no use of future administration events, discharge-coded current-visit diagnoses/procedures, or any other post-$t$ event to decide whether $m$ is active.

If an order `stoptime` or status field in the local schema is only known retrospectively, do not use it as an online input. Report the available past-only status/update fields and the strictest defensible online active-state construction.

The separate retrospective premise diagnostic below may use completed Discovery order intervals to determine whether two medications were ever concomitantly active; that retrospective diagnostic is not an inference feature.

### eMAR-observed visit-union DDI episode

For one Discovery hospitalization, include a DDI pair $(i,j)$ in the premise denominator only when:

1. both normalized medication concepts have at least one eMAR administration somewhere in that hospitalization; and
2. $(i,j)$ is present in the frozen DDI knowledge asset selected for R0.

Requiring administration evidence for **both** medications prevents missing eMAR coverage from being mislabeled as a temporal safety mismatch.

### Execution-confirmed overlapping DDI episode

An eMAR-observed visit-union DDI pair is execution-confirmed overlapping when completed order intervals for the two medications overlap and each medication has administration evidence inside the overlapping interval.

This is an **operational concomitant-exposure surrogate**, not physiological concentration, an ADE label, or proof that the interaction was clinically harmful.

### Static-only episode

A pair is `static-only` when it satisfies the eMAR-observed visit-union definition but does not satisfy the execution-confirmed overlap definition.

This is deliberately conservative: it tests whether even medications that were both actually administered during the same hospitalization can be incorrectly collapsed into one always-concurrent visit-level pair.

## Medication normalization

R0 may test more than one deterministic mapping path only to select one feasible shared identity; it may not hand-curate patient-specific mappings.

Preferred evidence order:

1. direct shared identifiers documented by MIMIC-IV (`pharmacy_id`, `poe_id`, `product_code` / formulary code as applicable);
2. existing project/local public-safe medication mapping assets with provenance;
3. a mechanically reproducible public terminology mapping already available locally.

Do not silently use medication strings as if they were standardized drug identities.

For each mapping path, report event-weighted coverage, unique medication concepts, and known-DDI vocabulary overlap.

## R0 required outputs

Discovery-only aggregate report must include:

1. raw MIMIC-IV version and required-table availability;
2. number of Discovery patients/hospitalizations with medication orders;
3. number of order/request events and eMAR administration events;
4. direct-link coverage through `pharmacy_id` / `poe_id` where applicable;
5. medication-normalization coverage for orders and administrations;
6. normalized action-vocabulary size;
7. number of normalized medications represented in the DDI asset;
8. number of eMAR-observed visit-union DDI patient-pair episodes;
9. number of execution-confirmed overlapping DDI patient-pair episodes;
10. `static_only_fraction = 1 - executed_overlap_episodes / emar_observed_visit_union_ddi_episodes` using the same normalized pair universe;
11. number of unique DDI relations and distinct patients contributing to both denominators;
12. distribution of static-only mismatch across DDI relations so one relation cannot silently dominate;
13. eMAR coverage heterogeneity across admissions, without attempting to infer clinical outcomes;
14. feasibility note on strictly pre-order active-state construction.

No model metric is computed.

## Frozen practical admission floors

Return `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE` only if **all** conditions hold on Discovery:

1. all minimum raw tables exist and contain linkable chronological medication events;
2. one deterministic medication-normalization path covers at least **80%** of eligible order events and **80%** of eligible administration events;
3. the resulting normalized action vocabulary contains at least **100 medication concepts**, with at least **60 concepts** represented in the frozen DDI asset;
4. at least **1,000 eMAR-observed visit-union DDI patient-pair episodes** occur across at least **500 distinct patients** and **30 unique DDI relations**;
5. at least **20%** of eMAR-observed visit-union DDI patient-pair episodes are `static-only` under the execution-confirmed overlap definition;
6. static-only mismatch is not concentrated in one relation: at least **10 DDI relations** each contribute at least **20 static-only patient-pair episodes**;
7. a strictly pre-order execution-confirmed medication state can be constructed without future medication events or discharge-coded current-visit diagnoses/procedures.

These are research-investment floors, not clinical thresholds. They require enough scale and semantic mismatch to justify rebuilding a method pipeline for a CCF-A paper.

Otherwise return:

`FAIL_R0_EXPOSURE_RESOURCE_OR_PREMISE`

## Interpretation boundaries

R0 PASS means only:

- raw MIMIC-IV can support the intended temporal state at useful scale;
- static visit-union DDI and execution-confirmed concomitant exposure differ materially in Discovery;
- the route deserves one method-level Idea and one learned-vs-direct-control gate.

R0 PASS does **not** establish:

- that execution-confirmed overlap causes an ADE;
- that non-overlap is clinically safe for every DDI;
- that administered medication is clinically optimal;
- that an exposure-conditioned model will beat a direct rule;
- that the eventual method is CCF-A publishable.

## No-rescue rule

If R0 fails:

- do not relax the frozen floors after seeing results;
- do not switch to a smaller disease subgroup;
- do not hand-curate a small medication set;
- do not replace eMAR with inferred timing solely to save the idea;
- do not start R1/R2;
- do not create Idea 006.

Record the failure and return the project to `NO_HIGH_VALUE_DIRECTION_YET`.

## Routing after PASS

If R0 passes:

1. `ccf-pipeline-orchestrator` records the admitted resource state;
2. create Idea 006 around exposure-conditional medication recommendation;
3. `ccf-experiment-designer` freezes Gate 01 before any training;
4. Gate 01 must compare end-to-end exposure-conditioned learning against the same exposure-risk signal used as a direct scalar reranker and hard filter.

No test or new Holdout access is authorized at R0 PASS.

## Public artifacts

Local execution may commit only aggregate/public-safe artifacts:

- one R0 runner in this reset folder;
- `r0-summary.json`;
- `r0-decision.md`.

Do not commit raw patient rows, subject identifiers, private data paths, restricted mapping dumps, or event-level extracts.
