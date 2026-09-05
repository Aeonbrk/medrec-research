<!-- markdownlint-disable MD013 -->

# Search Notes — Resource Reset: Exposure-Localized Medication Safety

## Search mode

`ccf-literature-searcher / exploratory`, narrowed to one resource-changing question after the project reached `NO_HIGH_VALUE_DIRECTION_YET`.

Search date: 2026-09-05.

Target: a method-capable route for the project's first formal paper, targeting at least a generic CCF-A venue family. Pure benchmark, measurement, or open-ended feature exploration is excluded.

## Reset question

The previous project state identified three binding resources: supervision semantics, richer patient state, and action resolution. This reset asked whether changing one or more of those resources creates a falsifiable method problem that is not already occupied by 2023--2026 medication-recommendation work.

## Resource branches screened

### 1. Supervision semantics alone

Rejected for immediate continuation.

The previous bounded reset already examined selective prescription supervision and trajectory-privileged negative reliability. Strict review found that latent clinically acceptable treatment is not identifiable from current retrospective prescription labels, while narrowing the claim collapses toward generic PU/noisy-label learning.

### 2. Richer patient state alone

Crowded and insufficiently specific.

Recent methods already model richer temporal/monitoring context, including ChainCare-style lab/medication monitoring chains, dynamic clinical trajectories, multi-attribute EHR encoders, and time-aware treatment models. Merely adding labs/vitals does not define a new scientific mechanism.

### 3. Finer action granularity alone

Crowded and high-cost.

SafeRx-Agent moves to ATC-L4, GRAIN moves to active ingredients, FineMed decomposes visit-level targets into diagnosis-aware subrecommendations, and RxEval evaluates drug-dose-route prescription units. A finer vocabulary alone is not enough.

### 4. Prescription-time causal masking / next-order prediction

Rejected as novelty.

Rough et al. (Clinical Pharmacology & Therapeutics, 2020) already generated one example per inpatient medication-order event, used only EHR information available before order time, and predicted medications ordered within the following 10 minutes over 990 medication concepts. Therefore "prescription-time state with no future leakage" is prior art, not a 2026 method contribution.

### 5. Joint medication timing prediction

Not selected.

Predicting medication plus administration time risks treating workflow timing as a normative clinical target. Existing temporal-event / medication-change literature also substantially reduces novelty. This would reintroduce an identifiability problem similar to the rejected supervision route.

## Strongest surviving resource change

### Exposure-localized safety at medication-order time

Current safe MedRec normally evaluates or regularizes a medication set using a static DDI adjacency relation. That abstraction treats DDI risk as a property of co-membership in the predicted visit-level set.

Clinical DDI decision-support literature uses a different semantic object: **concomitant or contextually active exposure**. Timing, route, course status, current laboratory state, and whether one drug has already stopped can determine whether a pairwise alert is applicable. Time-dependent DDIs can sometimes be mitigated by separating administration times.

MIMIC-IV provides the missing resource. Provider medication requests/orders are available in `prescriptions` / `poe`, while actual medication administration is separately recorded in `emar` / `emar_detail`; ICU administrations also exist in `inputevents`. The official MIMIC-IV data paper states that eMAR records administration, unlike `prescriptions`, which records medication requests, and supplies `poe_id` / `pharmacy_id` linkage fields.

This permits a different method problem:

> At a medication-order decision point, recommend the next medication action from only pre-order patient information while conditioning safety pressure on the **currently executed active regimen**, rather than on the union of all medications that appear anywhere in the hospitalization.

The route changes risk semantics and decision state, not merely the encoder.

## Direct-collision search

Queries explicitly combined medication recommendation with administration time, eMAR, co-administration, concurrent exposure, dynamic DDI, temporal DDI, and safe medication recommendation.

No searched 2023--2026 MedRec paper was found whose central method is actual-administration / executed-active exposure-conditioned DDI regularization for order-time medication recommendation.

This is not proof of global novelty. Closest pressure is split across two literature lines:

1. medication-order prediction at event time (Rough et al., 2020);
2. contextual/time-dependent DDI decision support using concomitant exposure, administration timing, course status, and patient context.

The method must create a non-obvious interaction between those lines rather than simply concatenate them.

## Important methodological warning

MIMIC-IV eMAR is not a clinical-correctness label. Administration means a medication was actually given; it does not prove that the treatment was optimal or harmless.

Therefore the proposed route must use eMAR only to define an **operational executed-exposure state**. Claims are limited to exposure-localized DDI surrogates and medication-order fidelity. ADE prevention or clinical safety claims would require separate evidence.

## Next decision

The route is strong enough for strict idea review but depends on a new raw-data resource. No Idea 006 should be created until a single bounded `R0 — Exposure Resource & Premise Admission` confirms that MIMIC-IV order/administration events can be linked and normalized at useful scale and that visit-union DDI materially differs from executed-active DDI applicability.
