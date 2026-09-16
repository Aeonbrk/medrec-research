<!-- markdownlint-disable MD013 -->

# Gate 01 runner integrity verification: Idea 008

## Verification status

- **Verifier role**: independent runner-integrity verifier
- **Runner revision verified**: `aa0a66818cd5bfbdda41a07250db9812228de31e`
- **Execution authorization**: [`gate-01-execution-authorization.md`](gate-01-execution-authorization.md)
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Formal recommendation-model training**: `NOT_RUN / NOT_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact
- **Verdict**: `RUNNER_INTEGRITY_FAIL`

This verification is restricted to the new execution-specific runner and targeted tests. It does not reopen Idea admission, protocol design, design integrity, the mechanical-preflight result, or the existing implementation-integrity pass.

## Revision scope

Relative to the execution-authorization revision `b2232a91922b6d975fea47407bf131570e5d3591`, the runner work adds only:

- `experiments/gate01_execution.py`;
- `tests/unit/test_idea008_gate01_execution.py`;
- state updates in `Handoff.md` and the Idea README.

No Gate protocol, mechanical-preflight implementation, baseline registry, quarantined-data artifact, scientific result, or historical test artifact changed.

## Scientific identity

`PASS`.

The runner preserves:

- BudgetSet utility head `[s_i,e_i] -> 64 -> 32 -> 1`;
- BudgetSet risk-price head `[s_i,e_i,rho] -> 64 -> 32 -> 1`;
- Independent utility head `[s_i,e_i] -> 64 -> 32 -> 1`;
- Independent risk-price head `[s_i,e_i,b,d_i,p_i] -> 64 -> 32 -> 1`;
- GELU activation and no dropout;
- explicit `+s_i` residual anchors;
- exact `T=2` BudgetSet state recomputation;
- Independent no-current-set-feedback boundary;
- BCE-with-logits + hinge-DDI + fixed-cardinality objective;
- AdamW, weight decay `1e-4`, LR/eta grid, `gamma=1e-3`, seeds `2002/2003/2004`, epoch ceiling `30`, and patience `5`;
- frozen checkpoint key and configuration key aliases from the verified preflight module;
- Audit evaluation only after a Dev-selected configuration/checkpoint set exists.

No protocol-identity regression was found.

## R1: Device execution path

`FAIL`.

`train_seed_configuration(..., device=...)` moves the learned model to `device`, but ordinary batch values are subsequently converted by `_as_float_tensor(scores)` without that device. `_prepare_scores_embeddings` therefore preserves the input's CPU device and feeds those tensors into the already-moved model.

This is reachable through the supported execution surface because the frozen MoleRec extraction contract materializes public-safe scores/embeddings as ordinary Python/CPU values. A normal 319 call using `device="cuda"` can therefore fail before the first learned update with a CPU/CUDA mismatch.

Required bounded correction: make one component own device placement consistently for scores, embeddings, budgets, DDI, targets, `K_x`, and Independent static summaries before model execution. Do not change model semantics.

## R2: Learned selection closure

`FAIL`.

The runner implements `train_seed_configuration`, which trains one `family × configuration × seed`, and it implements `select_configuration_result`, which selects among four configuration records.

However, the runner does not itself execute or validate the complete frozen selection graph:

```text
4 configurations
× 3 learned seeds
-> 12 independently trained retained checkpoints per family
-> three-seed Dev aggregation per configuration
-> derive n_compliant_config, U_primary_config, V_all_config
-> frozen configuration selection
-> retain exactly three checkpoints of the selected configuration
```

Instead, `ConfigurationDevResult` accepts `n_compliant_config`, `u_primary_config`, and `v_all_config` from the caller. The current tests likewise inject those values directly. A later execution caller would therefore still own a protocol-critical selection calculation outside the independently verified runner.

Required bounded correction: add one Idea-local runner path that enumerates exactly `CONFIGURATION_GRID × LEARNED_SEEDS`, derives the configuration-level Dev quantities from the retained seed checkpoints using the frozen aggregation semantics, applies the existing configuration key, and returns the selected configuration plus its three retained checkpoints. No extra grid, seed, metric, or tie-break is permitted.

## Test evidence

The coding handoff reports:

```text
29 passed, 9 skipped
405 passed, 9 skipped
Ruff: PASS
Markdown lint: PASS
```

The nine skips are PyTorch-dependent runner tests because local PyTorch was unavailable. That does not create a third scientific blocker, but the corrected runner cannot receive an integrity pass until the full targeted runner suite executes in the frozen `medrec-molerec-table1` environment on 319. The post-correction verification must include the supported device path.

## Boundary after verification

The formal Gate-execution phase remains authorized at the pipeline level, but recommendation-model training remains unauthorized. Gate01-Audit remains unopened. G3/G4, R0 Holdout, and historical project test remain untouched.

The only authorized next work is bounded runner correction plus synthetic/targeted verification. No design review, new model, new solver, new hyperparameter, new seed, or data expansion is authorized.

## Verdict

```text
RUNNER_INTEGRITY_FAIL
```

## Routing

```text
Stage: IDEA_008_GATE_01_RUNNER_INTEGRITY_FAIL_PENDING_BOUNDED_CORRECTION
Formal training: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Next owner: local coding agent
Next task: fix R1 and R2, run the complete targeted runner suite in the frozen 319 environment, and return for narrow runner-integrity re-verification
```
