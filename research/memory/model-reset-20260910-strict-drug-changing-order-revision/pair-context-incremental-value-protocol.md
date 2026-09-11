# Pair/Context Incremental Value Protocol

## Scientific status

This is a frozen pre-Idea execution under `PRE_IDEA_PAIR_CONTEXT_INCREMENTAL_VALUE`.
It is not Idea 008, Gate 01, a supportability audit, or a paper result. The only
scientific object is the already admitted strict drug-changing order-revision trace:

```text
x_pre -> m- -> DeltaI -> D/C(m-) -> m+
```

The trace is a directional observed workflow-revision trace. It is not a wrong-
medication correction, validated RAR, therapeutic substitution, clinically superior
replacement, optimal replacement, treatment preference, or `m+ ≻ m- | x_pre`.

## Scientific question

Does strict drug-changing order-revision supervision contain context-dependent,
cross-patient predictive value beyond ordinary flattened final-prescription
supervision and trivial source/destination frequency structure?

The null is that there is no practically material cross-patient information in
`X = x_pre` about `D = m+` conditional on `S = m-` beyond ordinary flattened
medication-set supervision, `P(D)`, `P(D|S)`, or matched extra destination-label
exposure.

## Population and partition

Use all and only the already admitted 1,040 strict events in G0/G1/G2. Do not apply
any pair-count, source-count, destination-count, medication, patient, admission, or
subgroup filter. G3, G4, the R0 Holdout, and the historical project test split are
quarantined.

The existing R0 subject partition is frozen:

```python
salt = "exposure-reset-20260905"
u = int(SHA256(f"{subject_id}|{salt}").hexdigest()[:8], 16) / 0xffffffff

Discovery: u < 0.70
Dev:       0.70 <= u < 0.85
Holdout:   u >= 0.85
```

Discovery is the only fit population. Dev is evaluated once. Holdout is not loaded
into an experiment dataset and all traces from one subject remain together.

## MIMIC access declaration

The runner may read only the following MIMIC-IV 3.1 fields:

- `patients`: fields required by the frozen strict-trace population and R0 partition
  contract (`subject_id`, `anchor_year`, `anchor_year_group`);
- `poe`: `poe_id`, `poe_seq`, `subject_id`, `hadm_id`, `ordertime`, `order_type`,
  `transaction_type`, `discontinue_of_poe_id`, and `order_provider_id`;
- `prescriptions`: `subject_id`, `poe_id`, `pharmacy_id`, `ndc`, and
  `formulary_drug_cd`;
- `admissions`: `subject_id`, `hadm_id`, and `admittime`, solely for
  `log1p(hours since admission)`;
- `emar`: `subject_id`, `hadm_id`, `poe_id`, `pharmacy_id`, `charttime`, and
  `event_txt`, solely to identify the frozen Idea-006 administration event types
  at `charttime < t_minus` for the active-regimen indicator.

No other MIMIC table, column, event-type distribution, administration attribute,
future signal, G3/G4 row, R0 Holdout row, or historical project-test row is read or
materialized.

## Strict trace identity

The strict semantic object is reproduced without modification:

1. The old order is linked only by `d.discontinue_of_poe_id == o-.poe_id`.
2. `o-`, `d`, and `o+` are Medication workflow objects with the same subject, same
   non-null hospitalization, and same non-null ordering provider.
3. `o- -> d` is in `[0, 600]` seconds and `d -> o+` is in `(0, 600]` seconds.
4. `poe_seq` is chronologically ordered as `o- < d < o+`.
5. Old and New orders each map to exactly one concept in the frozen 131-action
   ATC-L4 MedRec vocabulary.
6. The complete eligible post-D/C New set is constructed before applying
   `identity(m-) != identity(m+)`.
7. One old order has exactly one eligible source D/C, one D/C has exactly one
   eligible New, and one New is not consumed by another source D/C.
8. `identity(m-) != identity(m+)`.

No nearest/first New, tie-breaking, different-provider matching, raw Change/D/C
regimen semantics, dose/route/frequency/formulation identity, hand mapping, or
clinical-correctness interpretation is permitted.

## Causal pre-order input

At focal source order time `t_minus`, `x_pre` contains only:

- the last 64 normalized medication POE transactions with `ordertime < t_minus`,
  each represented by medication concept, New/Change/D/C type, and `log1p` elapsed
  hours;
- the 131-dimensional execution-confirmed active-regimen indicator at `t_minus`;
- `log1p(hours since admission)`.

Historical D/C transactions resolve their referenced medication using the existing
frozen order-time builder. No timestamp at or after `t_minus`, focal DeltaI/D/C
linkage, `m+`, future administration, retrospective order status, post-source
information, future diagnoses/procedures, labs, vitals, notes, KG/molecular/LLM
features, or any other future signal enters `x_pre`.

## Targets and frozen models

For each strict event, construct the ordinary flattened 131-ATC-L4 medication-set
target for its admission using the established prescription normalization/mapping.
This target discards order-revision linkage and within-admission revision ordering.
Mapping disagreement with the strict semantic packet is `STOP_INVALID_EXECUTION`;
strict events are never silently dropped.

`FlatFinalBase` reuses `CommonOrderTimeBackbone` exactly:

```text
medication embedding 64
transaction embedding 8
elapsed projection 8
GRU hidden 128
active regimen 131
time scalar 1
MLP 260 -> 128 -> 131, ReLU, dropout 0.10
```

Train on Discovery ordinary flattened medication-set BCE only, with no validation,
early stopping, or tuning:

```text
optimizer: AdamW
learning rate: 1e-3
weight decay: 1e-5
batch size: 64
epochs: 20 exactly
seeds: 260911, 260912, 260913
```

Freeze each base model before strict `m+` supervision. The 128-dimensional
activation immediately before the final projection is `h_flat(x_pre)`.

The trace probe is a fixed 131-class linear softmax over
`[h_flat(x_pre); onehot(m-)]`, fit only on Discovery strict traces with zero
initialization, full-batch multinomial cross-entropy, deterministic LBFGS, and L2
coefficient `1e-4`. The context-only probe uses the identical records and training
with a zero 128-dimensional context block.

## Controls

Implement exactly these seven variants:

```text
DestinationMarginal
SourceTransitionPrior
FlatFinalBase
FlatFinalPlusSourcePrior
TraceContextOnly
PermutedPairContext
PairContext
```

For Discovery strict traces:

```text
p_D(d) = (n_d + 1) / (N + 131)
p_S(d|s) = (n_sd + p_D(d)) / (n_s + 1)
q_FS(d|x,s) ∝ softmax(flat-final logits)[d] * p_S(d|s)
```

An unseen source backs off to `p_D`. No sparse pair filtering is allowed.

`PermutedPairContext` has the exact PairContext architecture, labels, source
identities, and records, but Discovery `h_flat` contexts are assigned by one fixed
deterministic global permutation from other patients. The context marginal is
preserved, no context is assigned to an event from the same subject, and Dev is not
permuted.

## Metrics and bootstrap

For every Dev strict event, primary NLL is `-log p(m+)`. MRR and Hit@5 are secondary
report-only metrics. Event NLL and secondary metrics are averaged across the three
frozen base-model seeds before gate comparisons.

For each control `c`:

```text
G_c = (NLL_c - NLL_PairContext) / NLL_c
```

Use a paired patient-cluster bootstrap on R0 Dev with 5,000 replicates, seed 260911,
and subject-level clusters. A sampled patient contributes all of that patient's
strict events.

## Binary verdict

For every control in
`DestinationMarginal`, `SourceTransitionPrior`, `FlatFinalPlusSourcePrior`,
`TraceContextOnly`, and `PermutedPairContext`, all three conditions are required:

```text
observed G_c >= 0.05
95% patient-cluster bootstrap lower bound for G_c > 0
PairContext raw Dev NLL is lower than that control for each frozen seed
```

If all five controls pass, emit:

```text
PASS_PAIR_CONTEXT_INCREMENTAL_VALUE
```

This only means the frozen pre-Idea premise survived one bounded incremental-value
test. It does not establish clinical correctness, treatment effect, validated RAR,
therapeutic substitution, or superiority, and it does not authorize model training
beyond this execution.

If any condition fails, emit:

```text
ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE
```

There is no borderline state and no rescue. Do not alter thresholds, semantics,
mapping, population, features, architecture, capacity, windows, patients, or
medications after observing results.

## Invalid execution

Partition leakage, prohibited partition access, any `x_pre` leakage at or after
`t_minus`, focal D/C or `m+` leakage, silent strict-event filtering,
candidate/control sample mismatch, a label-changing permutation, non-finite
optimization, mapping divergence, source revision mismatch, or dirty remote checkout
produces `STOP_INVALID_EXECUTION` and no scientific verdict.

## Public-safe artifacts

The summary contains only protocol/revision identity, aggregate partition/event
counts, integrity checks, aggregate NLL/MRR/Hit@5 by variant and seed, five gate
comparisons with bootstrap intervals, quarantine flags, and the terminal verdict.
No patient IDs, admission IDs, POE IDs, provider IDs, event rows, raw predictions,
checkpoints, or restricted paths enter Git.

```json
{
  "protocol": "PAIR_CONTEXT_INCREMENTAL_VALUE",
  "source_revision": "15b3cffe42dd08cbfc9e2d8bf34ee766520a67a2",
  "semantic_admission": "PASS_SEMANTIC_ADMISSION",
  "strict_events_expected": 1040,
  "mimic_access": {
    "patients": ["subject_id", "anchor_year", "anchor_year_group"],
    "poe": [
      "poe_id",
      "poe_seq",
      "subject_id",
      "hadm_id",
      "ordertime",
      "order_type",
      "transaction_type",
      "discontinue_of_poe_id",
      "order_provider_id"
    ],
    "prescriptions": ["subject_id", "poe_id", "pharmacy_id", "ndc", "formulary_drug_cd"],
    "admissions": ["subject_id", "hadm_id", "admittime"],
    "emar": ["subject_id", "hadm_id", "poe_id", "pharmacy_id", "charttime", "event_txt"]
  },
  "partition": {
    "salt": "exposure-reset-20260905",
    "discovery_upper": 0.70,
    "dev_upper": 0.85,
    "holdout_lower": 0.85
  },
  "flat_final_base": {
    "learning_rate": 0.001,
    "weight_decay": 0.00001,
    "batch_size": 64,
    "epochs": 20,
    "seeds": [260911, 260912, 260913]
  },
  "trace_probe": {
    "classes": 131,
    "context_dim": 128,
    "l2": 0.0001,
    "initialization": "zero",
    "optimizer": "deterministic_lbfgs"
  },
  "permutation_seed": 260911,
  "bootstrap": {
    "replicates": 5000,
    "seed": 260911,
    "cluster": "subject_id"
  },
  "criteria": {
    "relative_gain": 0.05,
    "bootstrap_lower_bound": 0.0,
    "pair_context_lower_each_seed": true
  }
}
```
