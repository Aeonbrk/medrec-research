<!-- markdownlint-disable MD013 -->

# Gate 01 Runner Integrity Re-verification — Idea 008

## Verification status

- **Verifier role**: independent runner-integrity verifier
- **Runner revision verified**: `4c3ac46365ade339f307be449b8a7dca3c8bb16c`
- **Correction parent**: `e306421d982dfb4276c6606f92db688d3b470732`
- **Prior runner verification**: [`gate-01-runner-integrity-verification.md`](gate-01-runner-integrity-verification.md), verdict `RUNNER_INTEGRITY_FAIL`
- **Execution authorization**: [`gate-01-execution-authorization.md`](gate-01-execution-authorization.md)
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Formal recommendation-model training during verification**: `NOT_RUN`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact
- **Verdict**: `RUNNER_INTEGRITY_PASS`

This re-verification is limited to the two bounded blockers recorded by the prior runner-integrity failure. It does not reopen Idea admission, protocol design, design integrity, mechanical preflight, or the earlier implementation-integrity pass.

## Revision scope

The correction revision changes only the Idea-local execution runner, its targeted unit tests, and authoritative state documentation. It does not change protocol v1.2, the mechanical-preflight implementation, baseline registry, frozen MoleRec identity, data partitions, quarantined artifacts, or scientific results.

## Scientific identity

`PASS`.

The corrected runner preserves the previously verified BudgetSet/Independent equations, explicit frozen-score residual anchors, exact `T=2`, MLP widths, GELU/no-dropout architecture, objective, AdamW shell, frozen LR/eta/seed grid, checkpoint key, patience semantics, deterministic controls, and Dev-before-Audit boundary.

No scientific-identity regression was found.

## R1 — Device execution path

`PASS`.

The runner now resolves one execution device for a learned invocation and materializes every learned-execution input on that device before forward/objective execution:

- frozen MoleRec scores;
- frozen MoleRec visit-conditioned candidate embeddings;
- requested budget tensor;
- DDI matrix;
- labels;
- `K_x`;
- Independent Train-only `d_i` and `p_i` summaries.

Frozen scores, embeddings, DDI data, labels, budgets, and static summaries are detached from upstream graphs. `train_seed_configuration` moves the model when a device is requested, resolves the resulting execution device, prepares each batch through the shared placement path, and uses the prepared tensors for both the model forward and the objective.

The targeted suite includes CPU/list placement, frozen-feature detach behavior, Independent static-input placement, and a CUDA forward/backward/AdamW step. The committed handoff records that the approved `medrec-molerec-table1` environment executed the CUDA path successfully.

The prior CPU/CUDA mismatch path is closed.

## R2 — Learned selection closure

`PASS`.

The runner now owns the complete learned-family Dev-selection graph:

```text
4 frozen configurations
× 3 learned seeds
-> 12 independent seed/configuration runs
-> one retained Dev checkpoint per run
-> three retained seed checkpoints per configuration
-> seed-mean Dev operating points at b_L,b_M,b_H
-> derive n_compliant_config, U_primary_config, V_all_config
-> frozen lexicographic configuration selection
-> exactly three retained checkpoints for the selected configuration
```

`ConfigurationDevResult` derives its aggregate quantities from the three retained seed checkpoint budget metrics. Caller-provided `n_compliant_config`, `u_primary_config`, or `v_all_config` fields are rejected rather than trusted.

`train_learned_family` enumerates exactly the frozen configuration grid and learned seeds, verifies the returned family/configuration/seed identity for every run, rejects duplicate or missing run identities, constructs all four configuration records, applies the existing frozen configuration-selection key, and returns only the selected configuration's three retained checkpoints for later Audit use.

Gate01-Audit is absent from all training/checkpoint/configuration selection interfaces.

The prior unverified downstream-selection gap is closed.

## Verification evidence

The correction handoff records:

```text
Local targeted tests: 32 passed, 12 skipped
Local regression: 408 passed, 12 skipped
319 targeted PyTorch tests: 44 passed, 0 skipped
CUDA/device smoke: PASS
Ruff check/format: PASS
Markdown lint: PASS
```

The local skips are explained by the local environment lacking PyTorch. The frozen 319 `medrec-molerec-table1` environment executed the exact targeted execution-runner and mechanical-preflight files with PyTorch available, including the CUDA path, so the previously required PyTorch-dependent verification is satisfied.

GitHub exposes no separate CI status on the verified revision; no CI claim is made.

## Verdict

```text
RUNNER_INTEGRITY_PASS
```

No runner-integrity blocker remains. This pass establishes execution readiness only. It is not a Gate 01 scientific result and does not itself open Gate01-Audit.

## Routing

```text
Runner revision: 4c3ac46365ade339f307be449b8a7dca3c8bb16c
Runner integrity: RUNNER_INTEGRITY_PASS
Protocol v1.2: unchanged
Gate01-Train/Dev scientific execution during verification: NOT_RUN
Gate01-Audit: UNOPENED
G3/G4: UNTOUCHED
R0 Holdout: UNTOUCHED
Historical project test: UNTOUCHED
Next owner: ccf-pipeline-orchestrator
Next decision: activate the already-frozen Gate01-Train/Dev phase or identify a concrete new blocker
```
