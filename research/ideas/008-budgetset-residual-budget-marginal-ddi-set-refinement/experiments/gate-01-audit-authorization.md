<!-- markdownlint-disable MD013 -->

# Gate 01 Audit Execution Authorization — Idea 008

## Authorization status

- **Authoritative revision before authorization**: `91fa61f181bfc6d543e13f412b1602c12ef90913`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Design integrity**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity**: `RUNNER_INTEGRITY_PASS`
- **Gate01-Train + Gate01-Dev**: `COMPLETE`
- **Gate01-Audit**: `AUTHORIZED_NOT_RUN`
- **Quarantine**: intact
- **Next owner**: local execution agent

All Train-only and Dev selection quantities required by the prior authorization are frozen without Audit access. This artifact authorizes only the terminal Gate01-Audit evaluation defined by protocol v1.2. It does not authorize new training, tuning, selection, protocol changes, or access to any quarantined partition outside Gate01-Audit.

## 1. Frozen executable and scientific identity

Use exactly:

```text
MoleRec source revision:
dd5afaf0a503fd3de3229f86ec7f26b345d10e3a

MoleRec profile:
molerec-embedding

Frozen checkpoint SHA-256:
5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca

Dataset identity:
molerec-table1-comparison-v1-1

Candidate vocabulary:
131 medications

Environment:
medrec-molerec-table1
```

The corrected execution runner and protocol semantics remain unchanged. No replacement checkpoint or MoleRec retraining is permitted.

## 2. Frozen Train-only quantities

```text
r_train = 0.07728988868497694
b_L = 0.04637393321098616
b_M = 0.06183191094798155
b_H = 0.07728988868497694

fixed lambda at b_L = 1.0
fixed lambda at b_M = 0.5
fixed lambda at b_H = 0.0
```

Independent `d_i` and `p_i` remain exactly the Gate01-Train-only frozen summaries used during training. Audit must not recompute them from Audit.

## 3. Frozen learned selections

BudgetSet:

```text
learning_rate = 0.001
eta = 5.0
seed 2002 retained epoch = 6
seed 2003 retained epoch = 10
seed 2004 retained epoch = 6
```

Independent:

```text
learning_rate = 0.001
eta = 5.0
seed 2002 retained epoch = 7
seed 2003 retained epoch = 6
seed 2004 retained epoch = 6
```

Only these retained checkpoints are eligible for Gate01-Audit. Audit results cannot replace a checkpoint, configuration, seed, fixed-lambda value, or budget.

## 4. Authorized Audit operations

Gate01-Audit may now be opened exactly once for the frozen terminal evaluation. The execution may:

1. extract the frozen MoleRec scores and visit-conditioned medication embeddings for Audit using the same `eval()` / no-gradient semantics;
2. derive each Audit visit's fixed `K_x` from the frozen base threshold `sigmoid(s_i) >= 0.5`;
3. evaluate Frozen Base and the deterministic Fixed-K Budget-Aware Greedy + 1-Swap control at the protocol-required operating points;
4. evaluate the Train-selected fixed-lambda supporting control at its already-frozen lambda for each requested target;
5. evaluate the three retained BudgetSet seeds at exactly `b_L`, `b_M`, and `b_H`;
6. evaluate the three retained Independent seeds at exactly `b_L`, `b_M`, and `b_H`;
7. compute the protocol-defined primary Jaccard and supporting F1/PRAUC, achieved hard-set DDI, positive violation/compliance quantities, budget response, and composition response;
8. construct the protocol-defined aggregate control frontiers and primary-region comparisons against both primary killers;
9. run exactly `1000` patient-clustered bootstrap resamples with seed `80081`, preserving patient multiplicity and recomputing operating points/frontiers inside each replicate as protocol v1.2 requires;
10. compute the matched-seed robustness result for each required `killer × primary-region` comparison using only seeds `2002`, `2003`, and `2004`;
11. apply the protocol v1.2 terminal precedence and emit exactly one terminal Gate 01 classification.

No Audit result may be used to make a new selection before classification.

## 5. Frozen terminal precedence

Apply exactly:

```text
1. STOP_INVALID_GATE_IMPLEMENTATION
2. STOP_NO_BASE_DDI_HEADROOM
3. KILL_TARGET_SEMANTICS
4. KILL_BUDGET_RESPONSE
5. KILL_COMPOSITION_RESPONSE
6. KILL_BUDGETSET
7. KILL_JOINT_SET_INTERACTION
8. KILL_SEED_FRAGILITY
9. INCONCLUSIVE_STOP
10. PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES
```

Do not reinterpret or reorder the precedence after observing Audit results.

## 6. Execution restrictions

Do not:

```text
retrain BudgetSet
retrain Independent
retrain MoleRec
change or substitute checkpoints
change LR or eta
change seeds
change budgets
reselect fixed lambda
recompute Independent d_i/p_i from Audit
add a control
add a solver
change T
change the objective
change metrics or thresholds
change frontier definitions
change bootstrap count or seed
change data partitions
open G3/G4
open R0 Holdout
open the historical project test
run paper-level SOTA benchmarking
perform post-hoc rescue
```

A runtime or implementation problem that requires a code or protocol change blocks the Audit. Preserve the failure evidence and return to the pipeline coordinator; do not patch and continue the same formal Audit execution.

## 7. Evidence and artifact boundary

Restricted patient/visit-level Audit rows, extracted features, logits, predictions, checkpoints, bootstrap internals, and private execution logs stay under the approved 319 data root.

Git may receive only public-safe aggregate evidence and routing artifacts. A public result may record the frozen identities, aggregate metrics, protocol checks, bootstrap intervals, seed-robustness counts, and terminal verdict, but no patient identifiers, split membership, raw prediction rows, embeddings, logits, or model weights.

## 8. Completion boundary

Audit execution is complete only when all frozen operating points and controls required by protocol v1.2 have been evaluated, all required response/frontier/bootstrap/seed-robustness checks are available, and exactly one terminal classification has been produced under the frozen precedence.

After completion, stop. Do not start another experiment, rescue, SOTA comparison, manuscript draft, or new Idea in the same execution step.

Propose the next state:

```text
IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT
```

The next owner is:

```text
ccf-integrity-auditor
```

The integrity audit must independently check the public-safe aggregate result against protocol v1.2 and the frozen execution identities before `ccf-pipeline-orchestrator` makes the scientific research decision.

## Routing

```text
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: AUTHORIZED_NOT_RUN
G3/G4: UNTOUCHED
R0 Holdout: UNTOUCHED
Historical project test: UNTOUCHED
Protocol revision: v1.2 unchanged
Runner: unchanged
Stage: IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION
Next owner: local execution agent
```
