<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `PRE_IDEA_PREMISE_AUDIT`

**Paper objective**: the next surviving route must be capable of becoming the project's first formal **method paper**, targeting at least a CCF-A venue family. Pure benchmark, measurement, survey, and indefinitely exploratory work are not acceptable terminal outcomes.

**Current authorization**:

- Do **not** create Idea 006 yet.
- Do **not** touch the test split.
- Do **not** launch another feature-mining sequence over frozen predictions.
- Authorize exactly one bounded empirical premise gate, `B0 — Cardinality Attribution`, under [`research/premise-audit/README.md`](../premise-audit/README.md).
- Axis A is blocked before data execution until it can name an independent positive therapeutic target beyond direct rule applicability.
- If B0 fails, return `NO_HIGH_VALUE_DIRECTION_YET`; do not repair the failed premise by adding features, model classes, thresholds, or subgroups.

This stage exists because the remaining uncertainty is partly empirical and cannot be resolved by literature search alone. It is a bounded pre-Idea exception, not a new permanent research phase.

## Authoritative evidence base

Project evidence:

- Ideas 001--005 and their formal research decisions under [`research/ideas/`](../ideas/).
- Cross-route failure records and controls under [`research/memory/failures/`](failures/).
- [`reusable-lessons.md`](reusable-lessons.md).
- Current baseline and evaluation contracts in [`ARCHITECTURE.md`](../../ARCHITECTURE.md), [`baselines/registry.toml`](../../baselines/registry.toml), and [`docs/playbooks/RESEARCH_WORKFLOW.md`](../../docs/playbooks/RESEARCH_WORKFLOW.md).

Literature evidence:

- The user-maintained `xray-papers-innovation-summary.md` is the primary 64-paper prior supplied for this reorientation. It covers 2026-03 through 2026-08 and is not currently a repository-owned artifact.
- A narrow current-source refresh is recorded in [`literature-opportunity-map.md`](literature-opportunity-map.md).

## Failure landscape

### 1. Post-hoc same-action routes have repeatedly collapsed under stronger controls

Ideas 001--004 and the historical EGSF route repeatedly tested low-dimensional observables or transformations layered on unchanged recommender behavior. The decisive pattern is narrower than "the backbone already knows everything":

- frozen score/constraint observables must beat frozen recommender confidence and route-specific trivial controls;
- order-equivalent score transforms do not create new routing information;
- within-set rank and prescription-relative confidence features did not add robust incremental signal;
- the tested train-only NPMI co-selection scalar did not add robust incremental signal over the expanded strong control;
- a context-conditioned post-hoc selector was absorbed by a strong global scalar control.

The evidence closes cosmetic post-hoc resurrection of these premises. It does **not** prove that a materially different end-to-end objective or supervision signal extracted from the same raw EHR fields is impossible.

### 2. Statistical or taxonomic structure is not clinical action semantics

Idea 005 found reproducible output structure, but strict semantic admission left only `C09A -> C09C` as an admitted ATC-3 alternative relation, covering 11 patients (2.79%) and one ATC-2 parent. The other supported relations were largely complementary therapy, distinct disease stage/context, contraindicated mechanisms, or coarse taxonomy co-location rather than therapeutic alternatives.

Therefore output regularity, shared indication, and ATC proximity cannot be promoted directly into substitution semantics.

### 3. A method cannot receive rules that the baseline is denied

The EG-TER route lost its claimed policy advantage after contraindication, severe-DDI, and coverage feasibility filters were leveled across policies. Future rule-conditioned methods must compare against a rule-matched baseline that receives the same non-oracle information.

### 4. Empirical feasibility and finite-sample certifiability are different gates

CRC-PS reached an empirically plausible action family but admitted no action under its finite-grid corrected certificate. The evidence does not identify whether sample size, margin, correction, or action-family geometry was the dominant cause. The reusable conclusion is narrower: certification adds a separate statistical-evidence burden and should not be the first investment before a mechanism has earned evidence.

## Higher-order reusable constraints

### C1a — Closed: post-hoc same-information cosmetic resurrection

When the learned predictor and action are frozen, replacing a failed low-dimensional observable with a monotone transform, nearby scalar statistic, or more expressive post-hoc function over the same tested information does not constitute a new scientific premise.

Status: **CLOSED for the tested information/action setting**.

### C1b — Open, low prior: same raw data with new end-to-end supervision

A different training objective, supervision signal, or action formulation can change what is learned from the same raw EHR fields. Ideas 001--004 do not falsify that class.

Status: **OPEN, LOW PRIOR / HIGH COLLISION**. It must carry a new supervision or action premise, not merely a new encoder.

### C2 — Semantic admission precedes architecture

Any route whose claimed contribution depends on therapeutic substitution, required treatment, contraindication resolution, or acceptable alternatives must establish that the required clinical relation is observable and externally grounded at the repository's action resolution before model implementation.

### C3 — Rule entitlement must be symmetric

If an external rule or deterministic feasibility predicate is available to the proposed method, the strongest simple baseline receives the same rule. Learned value must exist after this leveling.

### C4 — Certification follows mechanism evidence

Do not make statistical certification the primary novelty before a non-certified mechanism has demonstrated enough scientific value to justify the additional evidence burden.

## Research-space boundary map

| Route / premise | Current status | Evidence boundary | Reopen condition |
| --- | --- | --- | --- |
| Frozen-output DDI/tension scalar routing | `CLOSED` | Idea 001 selective singleton-deletion setting | New observable information or different action semantics, not a scalar rewrite |
| Pure score-geometry remapping | `CLOSED` | Idea 002 ordering-equivalent routing | A representation that provably changes decision information, not numeric calibration alone |
| Within-prescription relative/rank features | `CLOSED` | Idea 003 tested representation family | New supervision or non-post-hoc action formulation |
| Static train-only NPMI co-selection scalar | `CLOSED` | Idea 004 tested scalar relation | Materially different relational semantics plus its own strong control |
| Generic post-hoc contextual scalar selector | `CLOSED` | EGSF frozen-output selector family | New information source or end-to-end objective that cannot be reduced to the strong scalar control |
| ATC-2/ATC-3 sibling substitution in current 131-label space | `CLOSED` | Idea 005 strict semantic admission | Finer action resolution or an externally grounded alternative-treatment mapping with material cohort support |
| Current EG-TER repair policy | `CLOSED` | Rule-levelled comparison | A mechanism whose value remains after identical feasibility rules are given to controls |
| Current CRC-PS certified action family | `CLOSED` | Frozen R006 contract | New preregistered route with a different scientific mechanism, not parameter relaxation |
| Same raw EHR data + materially different end-to-end supervision | `OPEN, LOW PRIOR` | Not falsified by post-hoc failures | Clear supervision/mechanism hypothesis and closest-work separation |
| Generic longitudinal/trajectory modeling | `OPEN, CROWDED` | MR-DTR, DrugDoctor, HeteroMed and related work | A specific unresolved mechanism, not "use history better" |
| Generic rule/KG/RAG/agent safety modeling | `OPEN, CROWDED` | KATMed, RES-MR, SafeRx-Agent, ATLAS and related work | A method contribution beyond rule injection or verifier assembly |
| Count-controlled safety versus treatment recovery | `ACTIVE PREMISE` | Not yet tested under current frozen outputs | Pass B0 and then formulate a deployable learned mechanism |
| Action-space granularity as root cause | `OPEN PREMISE` | Suggested by Idea 005 and fine-grained recent work | Evidence that current 131-label abstraction destroys a material decision relation and can be remapped without turning the project into benchmark reconstruction |

`CLOSED` always means closed under the recorded scientific premise and evidence boundary; it is not a permanent ban on every future problem sharing the same noun.

## Axis A — Path-dependent rule applicability

### Status

`BLOCKED_AT_A0_POSITIVE_TARGET`

A direct conditional rule can determine whether a medication is currently forbidden or permissible. When a contraindication deactivates, the rule establishes permissibility, not that the medication should now be recommended. A learned "refresh" mechanism therefore needs an independent positive therapeutic target that direct current-state rule application does not already provide.

No such target is currently admitted in the repository. Idea 005 specifically warns against deriving it from ATC proximity or naive shared indication.

### Consequence

Do not count active-to-inactive episodes and do not build a stale-state model yet. Axis A reopens only if a narrow external source provides a positive, temporally observable treatment relation at usable action resolution, with enough cohort support to evaluate learned value beyond a rule-matched baseline.

If Axis A reopens, its mandatory controls include:

- direct current-state rule application;
- simple history/recency control;
- a meaning-preserving or clinically irrelevant null perturbation baseline for counterfactual sensitivity.

## Axis B — Cardinality attribution before treatment-preserving safety

### Status

`AUTHORIZED_B0_ONLY`

The unresolved premise is not yet "we need a new safety model." It is:

> Does the apparent safety/fidelity trade-off materially depend on suppressing medication count, such that restoring the reference count recovers target medications but measurably worsens normalized DDI rate?

B0 uses frozen validation-only MoleRec scores because those artifacts already exist or can be regenerated by inference under the frozen identity. No model training, new features, threshold search, or test access is authorized.

The exact-count comparison uses the ground-truth medication count and is therefore **oracle-count, diagnostic-only, and non-deployable**. Its role is mechanism attribution, not a method baseline for final deployment claims.

See [`research/premise-audit/README.md`](../premise-audit/README.md) for the frozen decision rule.

### Advancement rule

B0 must pass before any treatment-preserving safety method is designed. A pass authorizes `ccf-idea-optimizer` to formulate a deployable mechanism whose contribution is not oracle cardinality and which must eventually face simple count-prediction and DDI-aware allocation controls.

A B0 failure terminates this axis. Do not add omission features, diagnosis maps, GNNs, LLMs, or subgroup mining to rescue it.

## Validation and confirmation boundary

The validation cohort has already been used repeatedly for route selection. This is acceptable for the current **hypothesis-selection** role but it is not untouched confirmatory evidence. Building an OOF infrastructure solely for B0 would add engineering cost without changing the paper claim, because B0 is not publication evidence.

Therefore:

- B0 may reuse or regenerate frozen validation-only target-free MoleRec predictions;
- B0 outputs are route-selection evidence only;
- the test split remains untouched;
- a surviving method must later receive a fresh, explicitly frozen claim-support protocol before test evaluation.

## Publication-shape constraint

A route advances only if it can plausibly support all three components of a CCF-A method paper:

1. a nontrivial problem/mechanism statement, not a metric observation;
2. a deployable method whose value survives the strongest simple control and rule entitlement;
3. multi-baseline/multi-setting evidence after the method survives hypothesis selection.

Diagnostics are allowed only to decide whether to invest in that method. They are not themselves the intended paper contribution.

## Current gate and next owner

Current gate: `B0 — Cardinality Attribution`.

Primary owner: `ccf-experiment-designer` in raw protocol / hypothesis-selection mode.

Local execution owner: repository Agent, using the prompt supplied with this handoff.

Next state:

- `PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF` -> `ccf-idea-optimizer`, then `ccf-idea-reviewer` before implementation;
- `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF` -> `NO_HIGH_VALUE_DIRECTION_YET`, followed by one bounded `ccf-literature-searcher / exploratory` reset over method-capable pre-prediction supervision or action-formulation opportunities outside the closed map;
- no result permits automatic creation of Idea 006 without the optimizer/reviewer gate.
