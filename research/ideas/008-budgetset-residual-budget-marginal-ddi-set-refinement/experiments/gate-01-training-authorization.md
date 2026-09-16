<!-- markdownlint-disable MD013 -->

# Gate 01 Train/Dev execution authorization: Idea 008

## Authorization status

- **Starting authoritative revision**: `4c3ac46365ade339f307be449b8a7dca3c8bb16c`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Design integrity**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity**: [`gate-01-runner-integrity-reverification.md`](gate-01-runner-integrity-reverification.md), verdict `RUNNER_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Gate01-Train + Gate01-Dev execution**: `AUTHORIZED_NOT_RUN`
- **Gate01-Audit**: `UNOPENED / NOT_AUTHORIZED`
- **Quarantine**: intact
- **Next owner**: local execution agent

No pre-execution implementation blocker remains. This artifact activates only the Train/Dev portion of the already-frozen Gate 01 protocol. It does not authorize Gate01-Audit, produce a terminal Gate verdict, or change any scientific choice.

## 1. Frozen executable identity

Use exactly the corrected runner revision admitted by the integrity pass:

```text
gate01_execution.py revision context:
4c3ac46365ade339f307be449b8a7dca3c8bb16c

MoleRec / molerec-embedding upstream revision:
dd5afaf0a503fd3de3229f86ec7f26b345d10e3a

Frozen checkpoint SHA-256:
5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca

Dataset identity:
molerec-table1-comparison-v1-1

Candidate vocabulary:
131 medications
```

Use the existing `medrec-molerec-table1` environment and existing Comparison execution conventions. Do not modify MoleRec, its checkpoint, the baseline registry, or protocol v1.2.

## 2. Data access authorized now

### Gate01-Train

Gate01-Train is authorized for exactly these operations:

1. frozen MoleRec `eval()` / no-gradient extraction of the same `s_i(x)` and `e_i(x)` for every training visit;
2. Frozen Base `K_x` derivation using probability threshold `0.5`;
3. computation of `r_train` from Frozen Base Train predictions and freezing:

   ```text
   b_L = 0.60 * r_train
   b_M = 0.80 * r_train
   b_H = 1.00 * r_train
   ```

4. Train-only Independent static summaries `d_i` and `p_i`;
5. Train-only fixed-lambda selection from exactly `{0,0.25,0.5,1,2,4}` for each requested target;
6. BudgetSet training over exactly four frozen configurations and seeds `{2002,2003,2004}`;
7. Independent training with exactly the same configuration/seed entitlement.

If `r_train = 0`, stop under the existing protocol path. Do not open Dev or Audit to rescue the condition.

### Gate01-Dev

Gate01-Dev is authorized only for the learned-family selection procedure frozen in protocol v1.2:

- once per epoch, evaluate that `family × configuration × seed` checkpoint at exactly `b_L,b_M,b_H`;
- derive `n_compliant`, `U_primary`, and `V_all` from those three Dev operating points;
- apply the exact checkpoint key;
- apply patience `5` and maximum `30` epochs;
- retain one best checkpoint for every `seed × configuration`;
- aggregate the three retained seeds for each of the four configurations;
- derive `n_compliant_config`, `U_primary_config`, and `V_all_config`;
- select one configuration per learned family using the exact frozen key;
- retain exactly the three checkpoints `{2002,2003,2004}` of the selected configuration.

No Dev result may change architecture, grid support, budgets, seeds, optimizer, objective, control family, protocol threshold, or data partition.

## 3. Gate01-Audit remains sealed

Gate01-Audit is explicitly not authorized in this phase.

Do not read Audit rows, split members, frozen features, predictions, metrics, utility, DDI, composition response, control frontier, bootstrap interval, seed robustness, or terminal verdict.

Gate01-Audit may be considered for authorization only after all of the following are frozen without Audit access:

```text
r_train
b_L,b_M,b_H
Independent d_i,p_i
selected fixed-lambda value per requested target
BudgetSet selected LR/eta configuration
BudgetSet retained checkpoints for seeds 2002/2003/2004
Independent selected LR/eta configuration
Independent retained checkpoints for seeds 2002/2003/2004
```

After those values/checkpoints are frozen, stop execution and return to `ccf-pipeline-orchestrator` for an Audit-authorization decision.

## 4. Frozen learned families

BudgetSet and Independent remain exactly as protocol v1.2 defines.

BudgetSet:

```text
utility: [s_i,e_i] -> 64 -> 32 -> 1
risk-price: [s_i,e_i,rho] -> 64 -> 32 -> 1
activation: GELU
dropout: none
T = 2
```

Independent:

```text
utility: [s_i,e_i] -> 64 -> 32 -> 1
risk-price: [s_i,e_i,b,d_i,p_i] -> 64 -> 32 -> 1
activation: GELU
dropout: none
no current-set feedback
```

The explicit `+s_i` residual anchor is mandatory in both families.

## 5. Frozen optimization shell

```text
optimizer: AdamW
weight_decay: 1e-4
learning rates: {3e-4,1e-3}
eta: {5,10}
gamma: 1e-3
learned seeds: {2002,2003,2004}
max epochs: 30
patience: 5
training budget sampler: Uniform{b_L,b_M,b_H}
```

No additional optimizer, scheduler, seed, LR, eta, loss, regularizer, width, depth, dropout, auxiliary task, or rescue run is authorized.

## 6. Train/Dev outputs that may be retained

Keep under the restricted 319 data root rather than Git:

- learned checkpoints;
- per-epoch Dev predictions/metrics needed for the frozen selection keys;
- Train/Dev frozen feature caches if used;
- patient/visit-level data;
- private run logs.

Git may later receive only public-safe aggregate execution records and routing artifacts consistent with the repository workflow. Do not commit patient identifiers, split membership, raw rows, embeddings, logits, predictions, checkpoints, or private host traces.

The Train/Dev completion handoff must report the real frozen selection values and checkpoint epochs, but must not expose restricted patient-level material.

## 7. Stop conditions

Stop without opening Audit if any of the following occurs:

- repository/source/checkpoint/dataset/environment identity mismatch;
- runner revision differs from the integrity-passed revision without a new integrity check;
- frozen MoleRec extraction mismatch;
- candidate vocabulary or `K_x` contract mismatch;
- any extra/missing configuration or seed;
- any Audit access before Train/Dev freeze;
- an implementation/runtime failure that would require code or protocol changes.

For an implementation/runtime failure, preserve the failure evidence and return to the pipeline coordinator. Do not patch and continue against the same scientific run without a new integrity decision.

## 8. Explicitly not authorized

```text
no Gate01-Audit
no G3/G4
no R0 Holdout
no historical project test
no protocol redesign
no new architecture
no new encoder
no new hyperparameter
no new seed
no new budget
no solver expansion
no post-hoc rescue
no paper-level SOTA expansion
```

## 9. Completion boundary

The Train/Dev phase is complete only when:

- Train-only budgets/static summaries/fixed-lambda choices are frozen;
- BudgetSet has one selected frozen configuration and three retained checkpoints;
- Independent has one selected frozen configuration and three retained checkpoints;
- the selected checkpoint epochs are recorded;
- all selections were made without Gate01-Audit access;
- no quarantined partition was touched.

At that point set the next proposed state to:

```text
IDEA_008_GATE_01_TRAIN_DEV_COMPLETE_PENDING_AUDIT_AUTHORIZATION
```

and stop. Do not open Audit in the same execution step.

## Routing

```text
Formal Train/Dev authorization: YES
Formal recommendation-model training: AUTHORIZED_NOT_RUN
Gate01-Train: AUTHORIZED
Gate01-Dev: AUTHORIZED_FOR_SELECTION_ONLY
Gate01-Audit: UNOPENED / NOT_AUTHORIZED
G3/G4: UNTOUCHED
R0: UNTOUCHED
Historical project test: UNTOUCHED
Next owner: local execution agent
```
