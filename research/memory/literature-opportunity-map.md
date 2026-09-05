<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-05.

Current project state: `RESOURCE_ADMISSION_R0`.

The earlier B0 cardinality premise failed and the selective-prescription-supervision reset was not admitted. A subsequent resource-changing reset has selected one route for **resource admission only**:

> exposure-localized medication safety at provider order time.

Detailed packet: [`resource-reset-20260905-exposure-localized-safety/`](resource-reset-20260905-exposure-localized-safety/).

Strict pre-Idea verdict: `ACCEPT_TO_DEVELOP / RESOURCE_ADMISSION_REQUIRED`, weighted score `4.04/5`.

No Idea 006 exists. R0 must pass before Idea creation.

The user-maintained `xray-papers-innovation-summary.md` 64-paper map remains the primary supplied literature prior; this file records the current decision-relevant opportunity state.

## Closed or strongly compressed spaces

### Count-mediated treatment-preserving safety

`CLOSED under B0`.

Oracle reference-count matching changed retrospective fidelity but left pair-normalized DDI essentially unchanged. Cardinality is not the current safety mechanism.

### Selective prescription supervision

`NOT ADMITTED`.

The problem that unprescribed medications are not necessarily exhaustive clinical negatives is real, but current retrospective prescription labels cannot identify a latent acceptable-treatment set. Future medication occurrence does not establish earlier appropriateness, while narrower variants collide with KRAM and generic PU/MNAR correction.

### Generic longitudinal/history modeling

`CROWDED / LOW PRIOR`.

MR-DTR, DrugDoctor, HeteroMed, DMRNet, HypeMed, ChainCare and related work already cover dynamic treatment regimes, medication inheritance/expansion, monitoring-event chains, history recalibration, and visit-conditioned retrieval.

### Generic rule/KG/RAG/agent safety

`CROWDED / LOW PRIOR`.

KATMed, RES-MR, SafeRx-Agent, ATLAS and related work already cover contraindication-aware learning, personalized safety boundaries, knowledge-grounded verification, and patient-specific conflict reasoning. The repository's rule-entitlement control remains mandatory.

### Generic finer action granularity

`CROWDED / HIGH COST`.

FineMed, SafeRx-Agent, GRAIN and RxEval already push beyond coarse visit-level ATC-3 prediction toward diagnosis-level subrecommendations, ATC-L4, active ingredients, and drug-dose-route units.

### Order-time medication prediction by itself

`PRIOR ART`.

Rough et al. (2020), DOI `10.1002/cpt.1826`, already create one example per inpatient medication-order event, use only patient information available before the order, and predict medication orders in the following 10-minute window over 990 normalized medication concepts. Therefore temporal causal masking / next-order prediction is not the new contribution.

## Selected resource reset: exposure-localized DDI semantics

### Source-supported premise

Current MedRec commonly regularizes or evaluates a medication combination through a static pairwise DDI graph at visit/set level. That abstraction assumes pairwise risk relevance whenever both medications are members of the same predicted or observed set.

Clinical DDI decision-support literature does not make that assumption universally:

- time-dependent DDIs can depend on administration spacing;
- contextualized DDI algorithms use concomitant exposure intervals;
- stopped medications, short courses, route, laboratory state, and administration timing can suppress otherwise pairwise alerts;
- changing administration time is itself a common medication-safety intervention.

MIMIC-IV exposes the corresponding data resource:

- `prescriptions` and `poe` record medication requests/orders;
- `emar` and `emar_detail` record actual medication administrations;
- `poe_id`, `pharmacy_id`, and medication/product identifiers provide linkage paths depending on the local version;
- eMAR is distinct from prescription/request semantics.

This creates a specific opportunity:

> condition medication-recommendation DDI pressure on a **pre-order, execution-confirmed active regimen**, rather than on the union of every medication that appears somewhere in the hospitalization.

This is a new risk-state semantic, not merely another temporal encoder.

## Closest-work subtraction

| Work / family | Already covered | Remaining delta for current route |
| --- | --- | --- |
| Rough et al. 2020 inpatient medication-order prediction | order-time task, pre-order-only EHR, next-order multilabel prediction | safety pressure conditioned on current executed-active regimen |
| SafeDrug / static-DDI MedRec | differentiable DDI pressure | dynamic applicability state instead of full predicted-set pair union |
| KATMed 2026 | differentiable clinical contraindication constraints | medication-exposure state rather than drug-disease rule applicability |
| HeteroMed 2026 | dynamic medication expansion/inheritance plus expected DDI regularizer | DDI applicability itself becomes order-time state-dependent |
| SafeRx-Agent / GRAIN 2026 | finer safety/action granularity | current route is temporal/execution applicability, not finer taxonomy alone |
| Contextualized DDI CDS | concomitant exposure, time-dependent alert suppression, stopped-drug/course context | learns medication recommendation under dynamic risk state rather than only firing/suppressing alerts |

A focused search did not find a recent MedRec paper whose central method is actual-administration / execution-confirmed active exposure-conditioned DDI regularization for order-time recommendation. This is provisional novelty, not proof of exhaustiveness.

## Why eMAR is not a new label

Administration evidence is used only to define an operational medication-exposure state. It is **not** treated as proof of optimal therapy or clinical safety.

The method/evaluation language must remain:

- medication-order fidelity;
- exposure-localized DDI surrogate;
- execution-confirmed concomitant medication state.

Do not claim ADE reduction, optimal prescribing, or physiologic exposure without separate evidence.

## Current opportunity judgment

| Research axis | Judgment | Current action |
| --- | --- | --- |
| Post-hoc score/context routing | `CLOSED` | none |
| Count-mediated safety/coverage | `CLOSED` | none |
| ATC sibling substitution | `CLOSED` | none |
| Selective prescription supervision | `NOT ADMITTED` | reopen only with identifiable supervision |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | none |
| Generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | none |
| Generic fine-grained action mapping | `CROWDED / HIGH COST` | none |
| Order-time prediction alone | `PRIOR ART` | none |
| **Exposure-localized order-time safety** | **`SELECTED FOR RESOURCE ADMISSION`** | execute R0 only |

## R0 requirement

Before any method or Idea 006, the project must verify on a quarantined Discovery subset of raw MIMIC-IV that:

1. medication order and eMAR administration resources can be linked and normalized at useful scale;
2. the resulting action/DDI vocabulary is large enough for a general medication-recommendation method;
3. among DDI pairs where both medications were actually administered in one hospitalization, a material fraction are not execution-confirmed concurrently active;
4. a strictly pre-order active medication state can be constructed without future events or discharge-coded current-visit diagnoses/procedures.

Protocol: [`resource-reset-20260905-exposure-localized-safety/r0-resource-admission-protocol.md`](resource-reset-20260905-exposure-localized-safety/r0-resource-admission-protocol.md).

R0 is the only authorized next evidence collection.

## Stable source links

- Rough et al. 2020 medication-order prediction: https://doi.org/10.1002/cpt.1826
- MIMIC-IV data paper: https://doi.org/10.1038/s41597-022-01899-x
- MIMIC-IV on FHIR: https://physionet.org/content/mimic-iv-fhir/
- Time-dependent DDI alerts: https://doi.org/10.1197/jamia.M2810
- High-priority DDI criteria: https://doi.org/10.1186/1472-6947-13-65
- Contextualized DDI management: https://doi.org/10.1002/cpt.2624
- Contextualized DDI algorithms: https://pmc.ncbi.nlm.nih.gov/articles/PMC7976224/
- SafeRx-Agent: https://arxiv.org/abs/2605.29146
- GRAIN: https://arxiv.org/abs/2608.00098
- Temporal leakage appraisal: https://doi.org/10.1016/j.jbi.2026.105016
