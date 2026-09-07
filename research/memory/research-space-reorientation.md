<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `IDEA_006_GATE_01`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. Pure benchmark, measurement, survey, and indefinitely exploratory work are not acceptable terminal outcomes.

**Current active Idea**: [`006-exposure-conditional-medication-recommendation`](../ideas/006-exposure-conditional-medication-recommendation/README.md).

**Current authorization**:

- execute exactly the frozen Idea-006 Gate 01;
- use R0 Discovery only for InnerTrain/InnerTune and R0 Dev only for the final frozen Gate-01 evaluation;
- keep R0 Holdout and the existing project test split untouched;
- do not add richer state, a second backbone, a new DDI source, dose/route, labs/vitals, an LLM, or another architecture before Gate 01 passes.

Gate-01 SSOT:

[`../ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md`](../ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md).

## Authoritative evidence base

Project-local evidence now includes:

- Ideas 001--005 and their formal termination records;
- historical EGSF, EG-TER, and CRC-PS failure memory;
- B0 Cardinality Attribution: `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`;
- rejected selective-prescription-supervision reset: `PIVOT_WITH_RESCUE_ROUTE / DO_NOT_CREATE_IDEA_006`, `3.54/5`;
- R0 Exposure Resource & Premise Admission: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE` at commit `ea134b7e75583186242bc72bc71eb2975b812edc`;
- final closest-work check: `NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`;
- Idea-006 strict review: `ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`, `4.30/5`.

The user-maintained `xray-papers-innovation-summary.md` remains the primary supplied 64-paper literature prior; the current decision-specific search evidence is recorded under [`resource-reset-20260905-exposure-localized-safety/`](resource-reset-20260905-exposure-localized-safety/).

## Failure landscape

### F1 — post-hoc same-action routes are strongly compressed

Ideas 001--004 and EGSF repeatedly showed that low-dimensional observables layered on frozen predictions fail to add robust value once the strongest simple controls are supplied. Cosmetic score/rank/DDI/co-selection resurrection remains closed.

### F2 — statistical or taxonomic structure is not clinical action semantics

Idea 005 found reproducible ATC output structure, but strict therapeutic-semantic admission collapsed to one small relation. Taxonomy or shared indication cannot be promoted to therapeutic substitution without independent admission.

### F3 — rule entitlement must be symmetric

EG-TER showed that a learned method cannot receive a clinical feasibility/risk signal that the baseline is denied. Any future rule- or DDI-conditioned method must beat a direct control with identical information entitlement.

### F4 — certification adds an independent evidence burden

CRC-PS established that empirical feasibility does not imply finite-sample certifiability. Certification remains downstream of mechanism evidence.

### F5 — cardinality does not explain the current normalized-DDI behavior

B0 showed that oracle-count correction changed fidelity and absolute DDI-pair burden but left pair-normalized DDI essentially unchanged. Count-mediated treatment-preserving safety is closed under that premise.

### F6 — selective prescription supervision remains unidentifiable under current labels

A prescription is an observed treatment action, not an exhaustive clinical relevance set. However, future prescription occurrence does not establish earlier appropriateness, and current MIMIC labels cannot validate a latent acceptable-treatment set. Generic PU/noisy-label formulations therefore remain a low-value route without a changed supervision resource.

## Higher-order reusable constraints

### C1a — closed: post-hoc same-information cosmetic resurrection

Changing a statistic or function over already tested frozen information is not a new premise.

### C1b — open: changed objective/state semantics can be genuinely new

A materially different training objective or decision state can alter what is learned from the same clinical domain, but the target/state must be observable and identifiable.

### C2 — semantic admission precedes clinical interpretation

Therapeutic alternatives, treatment obligations, hidden positives, or clinical appropriateness require independent grounding before architecture.

### C3 — equal risk/rule entitlement

Any external DDI/rule signal available to the method must be available to the strongest direct control.

### C4 — certification follows mechanism evidence

Do not spend the first method-paper budget on guarantees before learned value exists.

### C5 — cardinality burden is not normalized interaction propensity

Absolute DDI-pair count can move mechanically with medication count while pair-normalized interaction tendency remains unchanged.

### C6 — admitted: hospitalization pair membership is not current exposure applicability

R0 upgrades this from an external-literature hypothesis to a project-local empirical constraint.

On MIMIC-IV 3.1 Discovery, among eMAR-observed DDI pairs where both medications were actually administered in the same hospitalization:

- denominator: 1,050,523 patient-hospitalization-pair episodes;
- execution-confirmed overlap: 829,366;
- static-only: 221,157;
- `static_only_fraction = 21.0521%`;
- contributing patients: 68,695;
- unique DDI relations: 391;
- relations with at least 20 static-only episodes: 280.

Therefore visit/hospitalization co-membership materially overstates **operational concomitant exposure** under the frozen R0 definition.

Boundary: this does not prove that static-only pairs are clinically safe, that overlap causes harm, or that an exposure-conditioned learner is useful.

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen / advance condition |
| --- | --- | --- | --- |
| Frozen-output DDI/tension scalar routing | `CLOSED` | Idea 001 | genuinely new information/state/action semantics |
| Pure score-geometry remapping | `CLOSED` | Idea 002 | changed decision information, not calibration |
| Within-prescription relative/rank features | `CLOSED` | Idea 003 | new supervision or pre-prediction mechanism |
| Static train-only NPMI co-selection scalar | `CLOSED` | Idea 004 | materially different relational semantics |
| Generic post-hoc contextual selector | `CLOSED` | EGSF | new information source/end-to-end premise |
| ATC sibling therapeutic substitution | `CLOSED` | Idea 005 | new action resolution + admitted semantics |
| Current EG-TER repair route | `CLOSED` | rule-levelled comparison | independent learned value after equal rules |
| Current CRC-PS certificate route | `CLOSED` | frozen certificate family | new mechanism, not looser certificate |
| Count-mediated treatment-preserving safety | `CLOSED` | B0 | new coverage/safety semantics not based on count |
| Selective prescription supervision | `NOT ADMITTED` | 2026-09-05 reset | identifiable multi-valid/reliable-negative target |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, DMRNet, ChainCare | specific non-generic mechanism |
| Generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | KATMed, RES-MR, SafeRx-Agent, ATLAS | contribution beyond rule injection/verifier assembly |
| Generic finer action mapping | `CROWDED / HIGH COST` | FineMed, SafeRx-Agent, GRAIN, RxEval | evidence that action remapping itself enables a new mechanism |
| Order-time prediction alone | `PRIOR ART` | Rough et al. 2020 | not a novelty route |
| **Exposure-localized order-time DDI learning** | **`ACTIVE IDEA 006`** | R0 + final closest-work check | pass equal-entitlement Gate 01 |

`CLOSED` always means closed under the recorded scientific premise/evidence boundary, not a universal prohibition.

## Why Idea 006 was admitted

The resource reset changes **risk-state semantics**, not merely features.

At order time $t$, the candidate method conditions incremental DDI pressure on a strictly pre-order active regimen $A_t$ constructed from:

- prior provider orders;
- prior execution-confirmed eMAR administrations;
- pre-$t$ provider D/C transactions.

It explicitly forbids future administrations, final retrospective status, and discharge-coded current-visit diagnoses/procedures.

The final closest-work check subtracts order-time prediction, contextual DDI-CDS, static-DDI MedRec, personalized safety, and finer drug granularity. The surviving search-scoped delta is the **interaction** between order-time medication recommendation and execution-localized DDI applicability.

## Idea 006 killer uncertainty

The method can still fail for one simple reason:

> once $A_t$ and the DDI matrix are known, a deterministic greedy exposure-aware reranker may capture all useful benefit.

This is why Gate 01 does not ask merely whether the new loss lowers DDI. It asks whether learned exposure-conditioned optimization beats a direct reranker receiving identical risk information at fixed output count.

If that comparison fails, Idea 006 terminates; the valid R0 measurement does not become the target method paper.

## Gate 01 evidence boundary

Primary evaluation:

- fixed `K=5`;
- target-free DDI-opportunity bursts only;
- primary fidelity: `Recall@5`;
- primary safety surrogate: `IncrementalExposureDDI@5`;
- common 10% InnerTune risk-reduction budget;
- patient-clustered paired bootstrap, 2,000 replicates, seed `260907`;
- all tuning inside R0 Discovery; R0 Dev evaluated once after freeze.

Primary killer control: `DirectExposureRerank` using the same Base logits, $A_t$, and DDI matrix.

Gate result must be either:

- `PASS_GATE01_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`, or
- `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

There is no Gate-01 rescue branch.

## Evidence and publication boundaries

R0 Holdout remains a fresh future claim-support reserve. The existing historical project test split also remains untouched.

Neither R0 nor Gate 01 may claim:

- ADE reduction;
- clinical appropriateness;
- physiologic exposure;
- prospective patient benefit.

The defensible language is medication-order fidelity plus an exposure-localized DDI surrogate.

## Current next owner

Local repository Agent executes the frozen Idea-006 Gate 01, followed by `ccf-integrity-auditor`.
