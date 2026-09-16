<!-- markdownlint-disable MD013 -->

# Gate 01 implementation / mechanical preflight Authorization: Idea 008

## Authorization status

- **Starting revision**: `df883b8405bea0c274950084d6871eefc7594393`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Design integrity evidence**: [`gate-01-design-integrity-reaudit-v1.2.md`](gate-01-design-integrity-reaudit-v1.2.md)
- **Design integrity verdict**: `DESIGN_INTEGRITY_PASS`
- **Stage**: `IDEA_008_GATE_01_IMPLEMENTATION_MECHANICAL_PREFLIGHT_AUTHORIZED`
- **Implementation**: `AUTHORIZED_NOT_STARTED`
- **Mechanical preflight**: `AUTHORIZED_NOT_RUN`
- **Implementation owner**: local coding agent
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Formal Gate execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside this phase

This authorization implements the already-frozen Gate 01 protocol. It does not redesign the method, alter protocol v1.2, produce scientific Gate evidence, or authorize model training.

## Frozen implementation contract

Protocol v1.2 is the single scientific source of truth. Historical audits are context only.

BudgetSet must implement the exact residual recurrence

$$
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)},
$$

with

$$
q_i^{(t)}=\sigma(z_i^{(t)}),
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\ne i}D_{ij}q_j^{(t)},
$$

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}),
$$

and exactly `T=2`:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
```

The second step must use the recomputed `q1`; stale `q0`, `c0`, or `rho0` is an implementation mismatch. Final score-producing outputs use exact `TopK(K_x)` with canonical medication-order tie-breaking.

The frozen backbone is `MoleRec / molerec-embedding` at upstream revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`. The same frozen `eval()` / no-gradient forward must expose both `s_i(x)` and the visit-conditioned `molecule_embeddings[i]` immediately before `score_extractor` as `e_i(x)`. No other MoleRec tensor may substitute for `e_i(x)`, no gradient may enter MoleRec, and MoleRec may not be retrained or modified.

## Allowed repository scope

Keep the implementation Idea-local. The canonical implementation/preflight entrypoint is:

```text
research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/
experiments/gate01_mechanical_preflight.py
```

The unit-test file is:

```text
tests/unit/test_idea008_gate01_mechanical_preflight.py
```

The existing `tests/unit/test_gate_01_mechanical_preflight.py` belongs to Idea 007 and must not be replaced or repurposed.

If the preflight emits a machine-readable public-safe record, use:

```text
research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/
experiments/gate-01-mechanical-preflight.json
```

Do not add a general-purpose package, framework, compatibility layer, feature flag, solver abstraction, migration layer, or `src/` promotion for this unproven Idea.

## Required implementation surface

Implement only the minimum code needed to faithfully realize protocol v1.2 and mechanically verify it:

- frozen MoleRec feature/logit extraction;
- deterministic Gate01-Dev / Gate01-Audit split function using the exact v1.2 hash contract;
- hard and relaxed DDI functions;
- marginal DDI `c_i`;
- BudgetSet `T=2` recurrence with the explicit `+s_i` residual anchor;
- Budget-Conditioned Independent Scorer with no current-set feedback;
- deterministic Fixed-K Budget-Aware Greedy + 1-Swap;
- deterministic fixed-lambda family;
- exact `TopK(K_x)` and canonical tie-breaking;
- `K_x=0` / `K_x=1` semantics;
- visit-level metric aggregation and target-compliance quantities;
- composition-response logic;
- aggregate frontier comparison, including the safer-than-entire-frontier branch;
- v1.2 empty-frontier seed comparator;
- matched-seed Independent favorable logic and deterministic Greedy handling;
- patient-clustered bootstrap with multiplicity preservation and within-replicate frontier recomputation;
- checkpoint, patience, and configuration-selection keys;
- frozen top-to-bottom terminal-verdict precedence.

Writing code for these semantics is authorized. Running BudgetSet or Independent training is not.

## Mechanical preflight checks

The implementation may report `MECHANICAL_PREFLIGHT_PASS` only when all of the following implementation-critical checks pass:

1. the explicit `+s_i` residual anchor is present in BudgetSet and Independent;
2. MoleRec `s_i` and `e_i(x)` are produced by the same frozen no-gradient forward;
3. `e_i(x)` aligns with the complete 131-medication candidate vocabulary;
4. `T=2` recomputes `q`, `c`, and `rho` after the first update;
5. every hard-output path satisfies exact `K_x`;
6. `K_x=0` and `K_x=1` behavior matches protocol v1.2;
7. the patient split reproduces the exact namespace / serialization / SHA-256 / first-eight-byte big-endian contract;
8. Greedy+1Swap is deterministic and preserves fixed `K_x`;
9. Independent cannot consume current-set `q`, `c`, `rho`, pairwise current-set features, or iterative feedback;
10. the ordinary eligible-frontier comparator implements the frozen rule;
11. the empty-frontier comparator is total and deterministic using lower DDI, then higher Jaccard, then canonical control-point order;
12. Independent seed robustness is matched `2002<->2002`, `2003<->2003`, `2004<->2004`;
13. deterministic Greedy and Fixed-lambda controls are not duplicated into artificial seeds;
14. patient-clustered bootstrap preserves sampled-patient multiplicity and recomputes all operating points and the control frontier inside each replicate;
15. terminal verdict uses the frozen Section 13 top-to-bottom precedence.

Use synthetic fixtures for pure functions. Do not access restricted data to test logic that can be established synthetically.

## Frozen-backbone mechanical integration allowance

One narrow real-backbone integration preflight is authorized because a mock cannot establish the exact pinned MoleRec extraction point.

It may use only:

- upstream MoleRec revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- the existing Comparison-qualified `molerec-embedding` frozen checkpoint, checkpoint SHA-256 `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`;
- dataset identity `molerec-table1-comparison-v1-1`;
- canonical Comparison **Train** examples only.

It may observe only what is needed to establish implementation faithfulness: source/checkpoint identity, `eval()` / no-gradient behavior, shared-forward provenance, tensor ranks/shapes, the 131-candidate alignment, and equality/consistency between the extracted pre-`score_extractor` tensor and the score produced from that same forward.

It must not compute or persist recommendation utility, DDI performance, budget response, composition response, frontier results, patient-level predictions, split membership, or any scientific Gate result. No raw clinical rows, patient identifiers, logits, candidate embeddings, or checkpoints enter Git.

Gate01-Audit must remain unopened. G3/G4, R0 Holdout, and the historical project test remain untouched.

## Allowed execution

```text
ALLOWED
- implementation under the Idea-008 experiment directory
- unit tests
- synthetic deterministic fixtures
- static/import/shape checks
- targeted and repository regression tests needed to detect implementation regressions
- the explicitly bounded frozen-backbone Train-only mechanical inference above

NOT ALLOWED
- BudgetSet training
- Independent training
- checkpoint or hyperparameter selection from real model runs
- three-seed scientific experiment execution
- Gate01-Audit access or evaluation
- scientific utility/DDI/composition/frontier result generation
- PASS/KILL_GATE_01 decision
- new budgets, seeds, model families, solvers, losses, or architecture variants
```

Unit-test execution and mechanical frozen-backbone inference are not Gate execution.

## Failure and pass semantics

Any failure of a frozen implementation-critical contract yields:

```text
STOP_IMPLEMENTATION_MISMATCH
```

Fix the implementation only. Do not change protocol v1.2 to accommodate code.

The mechanical phase may return:

```text
MECHANICAL_PREFLIGHT_PASS
```

only when every required mechanical check succeeds. This state means implementation faithfulness only. It does not mean `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES`.

## Completion and handoff

A successful coding-agent handoff must include:

- starting and final repository revisions;
- exact files changed;
- targeted unit-test result;
- relevant repository regression-test result;
- frozen-backbone mechanical integration result, if run;
- confirmation that no training or scientific Gate execution occurred;
- confirmation that Gate01-Audit and all quarantined partitions remained unopened;
- machine-readable preflight record if one was produced.

Commit and push the bounded implementation/preflight changes to `main` only after the mechanical checks pass and the working tree is clean. Do not mark Gate 01 scientifically passed.

After `MECHANICAL_PREFLIGHT_PASS`, route to an independent implementation/protocol verification against Gate 01 v1.2. That verifier must not train models or open Gate01-Audit. After independent verification, return to `ccf-pipeline-orchestrator`; only then may the pipeline decide whether formal Gate execution can be authorized.
