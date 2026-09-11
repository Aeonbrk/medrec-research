# Strict Drug-Changing Supportability Protocol

This packet executes the already admitted strict drug-changing order-revision
object. It is a bounded pre-Idea supportability check, not a model experiment.

## Identity and scope

- Protocol: `STRICT_DRUG_CHANGING_SUPPORTABILITY`
- Starting revision: `15b3cffe42dd08cbfc9e2d8bf34ee766520a67a2`
- Upstream semantic admission: `PASS_SEMANTIC_ADMISSION`
- Expected strict-event identity: `N_strict = 1,040`
- MIMIC-IV: `3.1`
- Allowed temporal groups: `G0 = 2008 - 2010`, `G1 = 2011 - 2013`,
  `G2 = 2014 - 2016`
- Temporal group membership is determined only by `patients.anchor_year_group`.
  `patients.anchor_year` remains an authorized field but is not used to exclude
  traces by calendar year.
- Existing R0 subject split: `u = int(SHA256(f"{subject_id}|exposure-reset-20260905").hexdigest()[:8], 16) / 0xFFFFFFFF`; only `u < 0.85` is admitted
- G3/G4, R0 Holdout, and historical project test remain quarantined

## Frozen semantic object

The directional observed workflow trace is:

```text
x_pre -> m- -> DeltaI -> D/C(m-) -> m+
```

The runner must resolve `m-` only through the explicit
`d.discontinue_of_poe_id == o-.poe_id` link. `o-`, `d`, and `m+` are
`order_type == "Medications"`, share the same subject, non-null hospitalization,
and non-null ordering provider. The old-to-D/C and D/C-to-New windows are each
`0..600` seconds with strict `poe_seq` direction `o- < d < m+` (the
old-to-D/C lower bound is inclusive; the post-D/C New lower bound is strict).

Medication identity is the singleton set of mapped ATC-L4 concepts linked
through a POE ID, resolved through the existing NDC-to-ATC-L4 mapping and
frozen 85% Discovery formulary consensus into the frozen 131-concept
vocabulary. Both old and New identities must be singletons and must differ.

For each eligible source D/C, construct the complete eligible post-D/C New set
before testing identity difference. Admit only if the old order has exactly one
eligible source D/C, the D/C has exactly one eligible New, and that New has
reverse in-degree exactly one across all eligible source D/C relations. No
nearest/first selection or tie-breaking is permitted.

The trace is directional historical workflow evidence only. It does not assert
replacement, correction, clinical preference, therapeutic substitution,
medication error, clinical correctness, or `m+ > m- | x_pre`; it does not assume
`DeltaI = 0`.

## Authorized source fields

Only these fields may be read after the clean remote checkout preflight:

- `patients`: `subject_id`, `anchor_year`, `anchor_year_group`
- `poe`: `poe_id`, `poe_seq`, `subject_id`, `hadm_id`, `ordertime`,
  `order_type`, `transaction_type`, `discontinue_of_poe_id`,
  `order_provider_id`
- `prescriptions`: `subject_id`, `poe_id`, `pharmacy_id`, `ndc`,
  `formulary_drug_cd`

No admissions, eMAR, pharmacy, physiology, outcomes, model, prediction,
historical-test, G3/G4, or R0-Holdout clinical rows may be read.

## Frozen supportability criteria

Let `T` be the strict trace set and `N = |T|`.

| ID | Criterion | Required |
| --- | --- | ---: |
| C1 | `N_strict` | `>= 500` |
| C2 | unique patients | `>= 200` |
| C3 | effective patients `N^2 / sum_i n_i^2` | `>= 150` |
| C4 | unique admissions | `>= 250` |
| C5 | unique source actions | `>= 20` |
| C6 | source actions with patients `>= 10` | `>= 15` |
| C7 | effective source actions `N^2 / sum_m (n_m-)^2` | `>= 10` |
| C8 | unique destination actions | `>= 20` |
| C9 | effective destination actions `N^2 / sum_m (n_m+)^2` | `>= 10` |
| C10 | second-largest G0/G1/G2 event share | `>= 0.20` |
| C11 | second-largest G0/G1/G2 patient share | `>= 0.20` |

No criterion compensates for another. Do not compute pair recurrence,
concentration alternatives, subgroup support, predictive metrics, or model
results.

The runner must parse and validate this frozen machine-readable block before it
opens any MIMIC table:

```json
{
  "protocol": "STRICT_DRUG_CHANGING_SUPPORTABILITY",
  "expected_strict_events": 1040,
  "criteria": {
    "C1_total_support": {"op": ">=", "value": 500},
    "C2_patient_breadth": {"op": ">=", "value": 200},
    "C3_patient_concentration": {"op": ">=", "value": 150},
    "C4_admission_contexts": {"op": ">=", "value": 250},
    "C5_source_breadth": {"op": ">=", "value": 20},
    "C6_source_recurrence": {"op": ">=", "value": 15},
    "C7_source_concentration": {"op": ">=", "value": 10},
    "C8_destination_breadth": {"op": ">=", "value": 20},
    "C9_destination_concentration": {"op": ">=", "value": 10},
    "C10_temporal_event_width": {"op": ">=", "value": 0.20},
    "C11_temporal_patient_width": {"op": ">=", "value": 0.20}
  }
}
```

## Decision

Emit `PASS_STRICT_DRUG_CHANGING_SUPPORTABILITY` only when the semantic identity
is exactly re-materialized as 1,040 events, all frozen invariants have zero
violations, and C1--C11 all pass. A pass authorizes only a fresh frozen design
for `Pair/Context Incremental Value`; that stage is not executed here.

If any criterion fails, emit
`ABANDON_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_STRICT_TRACE_SUPPORT` and
terminate the candidate under this definition. No rescue or semantic change is
allowed.
