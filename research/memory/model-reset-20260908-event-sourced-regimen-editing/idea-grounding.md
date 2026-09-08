<!-- markdownlint-disable MD013 -->

# Idea Grounding: Event-Sourced Regimen Editing

## Decision context

The project is seeking a first formal method paper targeting at least a CCF-A Data/Mining/AI venue family. A genuinely new model is acceptable. Pure benchmark/measurement work, indefinite diagnostics, and months of feature fishing are not acceptable.

S0 closed the temporal-practice-shift route with `FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`. The next reset therefore changes the learning problem rather than rescuing the failed shift premise.

## Project-local evidence

The Idea-006 common order-time backbone already receives:

- historical medication concepts;
- historical medication transaction types;
- elapsed time between historical transactions;
- the strictly pre-order active regimen;
- time since admission.

The current target construction nevertheless keeps only current `New` and `Change` medication orders and maps them to a medication-only 131-dimensional target. The current action type is therefore discarded, and `D/C` is excluded from the target.

This creates a concrete candidate information loss:

> the model observes past order actions and regimen state, but the supervised decision collapses the present action into a medication identity.

M0 tests whether this discarded action-state structure is predictive enough to justify a new method family.

## Closest work and exact delta

### Rough et al. — Predicting Inpatient Medication Orders From EHR Data

Stable source: https://doi.org/10.1002/cpt.1826

Rough et al. predict specific inpatient medication orders whenever a medication order is placed, with a 10-minute multilabel horizon and only pre-order EHR information. This is the closest task-level precedent for order-time prediction.

Covered already:

- trigger-time inpatient prediction;
- irregularly spaced predictions;
- 10-minute medication-order horizon;
- causal use of information available before order entry.

Not covered by that work:

- explicit `New / Change / D/C` action marks;
- a reconstructed regimen state as the object being edited;
- state-valid action decoding;
- learned action-medication structure beyond medication identity.

### MICRON — Change Matters

Stable source: https://doi.org/10.24963/ijcai.2021/513

MICRON explicitly predicts medication addition and removal sets by modeling differences between consecutive visits.

Covered already:

- medication-change prediction rather than only full-set prediction;
- explicit addition/removal semantics;
- medication-state reconstruction across visits.

Remaining distinction:

- MICRON infers changes from visit snapshots rather than using raw provider-order transaction marks;
- the decision unit is visit-level, not order-time;
- `Change` as an explicit CPOE transaction type is not the target;
- the within-admission event stream and current order state are not the central representation.

Therefore "predict medication changes" alone is not novel enough.

### ARMR — Adaptively Responsive Network for Medication Recommendation

Stable source: https://doi.org/10.24963/ijcai.2025/871

ARMR explicitly balances reuse of historical medications and introduction of new drugs according to changing patient state.

Covered already:

- new-versus-existing medication distinction;
- adaptive response to recent versus distant history;
- visit-level dynamic medication recommendation.

Remaining distinction:

- no raw order transaction target;
- no provider-order-time `Change / D/C` mark prediction;
- no event-sourced regimen edit process.

### HeteroMed

Stable source: https://doi.org/10.1007/s13755-026-00430-5

HeteroMed uses collaborative drug expansion and inheritance to model medication increases and decreases while integrating heterogeneous EHR knowledge.

Covered already:

- increase/decrease-aware recommendation;
- temporal modeling;
- explicit handling of existing versus newly introduced medications.

Remaining distinction:

- still visit-level;
- action semantics are inferred from prescription-set evolution rather than raw `poe.transaction_type`;
- no order-time event-sourced state machine is the central task.

## Search-scoped opportunity

The retained evidence supports a narrow opportunity at the intersection of two established lines:

1. visit-level change-aware medication recommendation;
2. order-time medication prediction.

The under-tested intersection is:

> strictly causal, order-time recommendation of explicit medication-regimen edit actions from an event-sourced medication state.

This is a search-scoped opportunity, not a novelty proof. A final closest-work check remains mandatory before Idea 007.

## Candidate mechanism

The candidate method family is not "use a larger Transformer". Its mechanism is structural:

1. represent medication history as an irregular event stream;
2. maintain a causal regimen state before each decision point;
3. predict joint action-medication marks rather than medication identity alone;
4. enforce the same state-valid action constraints in both learned method and direct control;
5. share statistical strength across action types and medications through a structured decoder;
6. in a later Idea, if admitted, model event timing and state transitions explicitly rather than reverting to visit-level set generation.

## Strongest trivial explanation

The action labels may be useful only because simple deterministic state validity already removes impossible outputs.

Therefore the required killer control is:

`SeparateHeads + DirectStateMask`

It receives the same history, current regimen, action labels, and deterministic state-valid mask as the structured probe. If the structured probe cannot beat this control, the method story is not admitted.

## M0 scientific question

> Do raw order-action semantics form a sufficiently supported and state-consistent target, and does a fixed structured action-medication decoder add predictive value beyond an equal-entitlement separate-head classifier plus the same direct state-validity mask?

## Scope exclusions

M0 must not use:

- DDI or medication-safety objectives;
- external KG or guideline rules;
- LLMs;
- labs/vitals/notes;
- alternative medication vocabularies;
- future-reserve cohorts;
- a deeper encoder rescue.

The reset succeeds only if the new decision structure itself carries incremental learned value.

## Current confidence

- Problem importance: `moderate-high` — medication management is intrinsically an edit process, and order-time support is more deployment-aligned than discharge-coded visit snapshots.
- Project-resource fit: `high` — raw POE transaction types and causal order-time infrastructure already exist.
- Novelty confidence: `moderate / needs-final-search` — closest work covers either visit-level changes or order-time medication identity, but a final strict overlap review is still required.
- Expected research-time efficiency: `high if M0 passes` — the premise can be falsified with one bounded run before building a final architecture.
