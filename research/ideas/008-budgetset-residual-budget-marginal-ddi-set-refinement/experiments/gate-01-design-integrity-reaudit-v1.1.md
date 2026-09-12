<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Re-audit — Idea 008 Protocol v1.1

## Audit status

- **Audit owner**: `ccf-integrity-auditor`
- **Audit mode**: independent pre-execution integrity re-audit
- **Starting revision**: `d248da5e410cfd739ac398f7ddfb1d4db1163aa5`
- **Protocol revision audited**: `v1.1`
- **Protocol blob**: `b6ae6971e98bb6bf63a2e9a8f3462efd84eba3ab`
- **Prior audit**: [`gate-01-design-integrity-audit.md`](gate-01-design-integrity-audit.md), preserved unchanged
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: unopened
- **Quarantine**: intact
- **Verdict**: `DESIGN_INTEGRITY_FAIL`

This re-audit asks only whether protocol v1.1 is scientifically identity-preserving, leakage-safe, uniquely executable, and capable of producing one mechanical PASS/KILL interpretation. It does not reopen Idea 008, add experiment breadth, or execute the Gate.

## Revision-scope audit

The correction commit `30c8ae539f04b1c3ab4b772149e87a76b3833c8a -> d248da5e410cfd739ac398f7ddfb1d4db1163aa5` changes only five protocol/state documentation files. It does not change code, data, backbone assets, baseline registry, training outputs, or quarantined material. The scientific backbone, candidate pool, cardinality rule, initialization, `T=2`, budgets, objective, LR/eta grid, gamma, seeds, killer roles, fixed-lambda support, primary utility, practical margins, bootstrap count/seed, PASS standard, and quarantine remain unchanged.

## B1 — Residual scientific identity

`PASS`.

BudgetSet v1.1 restores the admitted explicit frozen-score residual anchor:

$$
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)}.
$$

Independent uses the same residual-anchor principle:

$$
z_i^{ind}=s_i+u_\psi(s_i,e_i)-\operatorname{softplus}(g_\psi(s_i,e_i,b,d_i,p_i))d_i.
$$

The learned utility heads refine rather than replace the frozen backbone scorer. BudgetSet-vs-Independent therefore continues to isolate composition-dependent current-set feedback rather than entitlement to learn a replacement recommendation utility model.

## B2 — MoleRec representation

`PASS`.

Protocol v1.1 uniquely freezes `e_i(x)` to the candidate row of `molecule_embeddings` immediately before `self.score_extractor` in pinned `yangnianzu0515/MoleRec@dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`. The pinned forward constructs `molecule_embeddings` through patient-derived `substruct_weight`, so the representation is patient/visit-conditioned. The same frozen no-gradient forward supplies both `s_i(x)` and `e_i(x)`, and no alternate internal tensor is allowed. Repository Comparison inference uses the same pinned model in evaluation mode with `torch.no_grad()`.

## B3 — Gate01-Dev / Gate01-Audit split

`PASS`.

The membership contract is mechanically unique:

```text
namespace = "idea008-gate01-v1"
patient_id = zero-based integer patient index in pinned records_final.pkl
             canonical Comparison split ordering
patient key = ASCII decimal patient_id
message = namespace + ":" + patient key
encoding = UTF-8
hash = SHA-256
value = first 8 digest bytes as unsigned big-endian integer
u = value / 2^64
Dev iff u < 0.5
Audit iff u >= 0.5
```

All visits from one patient inherit one assignment. No label, outcome, DDI value, prediction, or model result enters the split. Audit data remain unopened.

## B4 — Low-cardinality execution

`PASS`.

Greedy is uniquely defined for reachable low-cardinality cases:

```text
K_x = 0 -> empty set
K_x = 1 -> highest frozen s_i, canonical medication-order tie-break
```

Both have zero hard DDI and zero budget violation and bypass pair-budget Greedy logic. Other score-producing methods retain exact `TopK_{K_x}` semantics; protocol-wide `R_DDI`, relaxed pair risk, and marginal DDI are zero for `K_x < 2`, so no low-cardinality mathematical branch remains undefined.

## B5 — Checkpoint, patience, and configuration selection

`PASS`.

Each `family × configuration × seed` trains independently and receives one Dev evaluation per epoch. The per-seed checkpoint key is uniquely ordered by higher compliant-budget count, higher primary-region mean Jaccard, lower mean positive violation, then earlier epoch. Patience is local to the seed/configuration, resets only on a new best checkpoint, and stops after five consecutive non-improving Dev evaluations or the 30-epoch ceiling. Exactly one checkpoint is retained per seed/configuration.

Configuration selection then aggregates only the three retained seed checkpoints, applies the frozen aggregate Dev criterion, and uniquely breaks remaining ties by smaller learning rate then smaller `eta`. Audit cannot select epoch, seed, configuration, or hyperparameter.

## B6 — Aggregation, frontier, bootstrap, and seed semantics

`FAIL` due to one remaining execution-blocking empty-frontier ambiguity.

The following v1.1 corrections are otherwise sufficient and pass re-audit:

- visit is the metric observation unit and patient is the bootstrap cluster unit;
- learned predictions and operating points are computed per seed before arithmetic seed-mean aggregation;
- target compliance uses visit means per seed and arithmetic means across the three learned seeds;
- responsiveness uses the family-level seed-mean achieved hard-DDI rates;
- composition change is literal hard-set inequality, excludes `K_x=0`, is computed per seed, then averaged across seeds;
- Greedy and Fixed-lambda remain deterministic rather than being duplicated as fake seeds;
- Independent uses matched seeds for seed-robustness comparisons;
- bootstrap resamples patients with multiplicity, includes all visits, recomputes operating points and the control frontier inside every replicate, and never bootstraps a precomputed scalar gap;
- favorable seed uses a sign-only rule rather than a second `0.005` materiality threshold when its frontier comparator exists.

### Remaining blocker — favorable seed is undefined when the eligible control frontier is empty

Section 11 explicitly supports the reachable case in which no control operating point satisfies

$$
R_C\le R_B+\delta_R.
$$

In that case the aggregate comparison switches to the protocol's safer-than-entire-sampled-frontier rule.

Section 12.2 nevertheless defines a seed as favorable only through

$$
G_{r,C}=U_{B,r}-F_C(R_{B,r}),
$$

with favorable iff `G_{r,C} > 0`. When the seed-specific eligible-control set is empty, `F_C(R_{B,r})` is undefined, so the seed-specific gap and favorable status are undefined.

This is execution-blocking because the same stored predictions can lead compliant implementations to treat such a seed as favorable, non-favorable, or not evaluable. That directly changes the `>=2/3` rule, `KILL_SEED_FRAGILITY`, and potentially PASS.

This is not an exotic corner case: the protocol itself explicitly authorizes and evaluates the safer-than-entire-frontier branch.

**Minimum correction**: extend Section 12.2 with one explicit sign-only seed-level comparator for the empty-eligible-frontier case, for both deterministic controls and matched Independent seeds. The correction must specify the comparator and any tie-break needed to choose it, then define favorable deterministically without changing the aggregate material-frontier rule or introducing a new `0.005` seed threshold. No other B6 statistic or scientific choice needs to change.

## B7 — Terminal precedence

`PASS`.

The protocol freezes one exact top-to-bottom order:

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

The first triggered condition is the primary verdict; later triggered conditions are secondary reasons only. `INCONCLUSIVE_STOP` cannot override an earlier explicit stop or killer.

## Integrity summary

```text
B1 scientific identity: PASS
B2 representation: PASS
B3 split: PASS
B4 low-cardinality execution: PASS
B5 learned selection: PASS
B6 aggregation/statistics/seeds: FAIL — one empty-frontier favorable-seed blocker
B7 terminal precedence: PASS

Scientific identity preserved: YES
Control fairness preserved: YES
Selection leakage found: NO
PASS/KILL mechanically unique: NO
New execution blocker: YES
```

The Gate hypothesis remains the admitted narrow question about incremental value of residual-budget marginal-DDI joint-set refinement beyond equal-information Greedy and Independent controls. It has not drifted into a clinical-safety guarantee, new utility scorer, best-possible MedRec model, or full SOTA comparison.

## Verdict

`DESIGN_INTEGRITY_FAIL`

Protocol v1.1 must not be implemented, trained, or executed yet. The only required follow-up is the bounded B6 seed-favorable empty-frontier definition above. B1–B5 and B7 are closed by this re-audit and must not be reopened absent new contradictory evidence.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.1: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: bounded B6 empty-frontier favorable-seed correction only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
