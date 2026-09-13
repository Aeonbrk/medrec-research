<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Re-audit — Idea 008 Protocol v1.2

## Audit status

- **Audit owner**: `ccf-integrity-auditor`
- **Audit mode**: independent pre-execution integrity re-audit
- **Starting revision**: `90bba30b6454843df6a72d876e9b79c56daf7549`
- **Correction parent**: `2c340f5006505c6641d2f0d14a655c66efb2b055`
- **Protocol revision audited**: `v1.2`
- **Protocol blob audited**: `d4d9685266ebbe40974f0d1dc6e95c90b4aea91d`
- **Historical v1.0 audit**: [`gate-01-design-integrity-audit.md`](gate-01-design-integrity-audit.md), preserved unchanged
- **Historical v1.1 re-audit**: [`gate-01-design-integrity-reaudit-v1.1.md`](gate-01-design-integrity-reaudit-v1.1.md), preserved unchanged
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: unopened
- **Quarantine**: intact
- **Verdict**: `DESIGN_INTEGRITY_PASS`

This re-audit is restricted to the v1.2 correction of the single B6 empty-frontier favorable-seed blocker identified by the v1.1 re-audit. It does not reopen the admitted scientific object, redesign Gate 01, inspect Gate01-Audit, access G3/G4, R0 Holdout, or historical project test data, implement the method, train a model, or execute the Gate.

## Revision-scope audit

The correction revision `2c340f5006505c6641d2f0d14a655c66efb2b055 -> 90bba30b6454843df6a72d876e9b79c56daf7549` changes five research protocol/state documentation files and no code, data, model, baseline registry, training output, or quarantined artifact.

The only scientific protocol-semantic change is the B6 seed-robustness closure for an empty seed-specific eligible control frontier, plus the directly required invalid-implementation rule for a required killer family with zero sampled operating points. Accompanying edits propagate protocol revision/state and remove non-authoritative duplicate prose. They do not change the backbone, candidate pool, `K_x`, `q^(0)`, `T=2`, budgets, objective, LR grid, `eta` grid, `gamma`, learned seeds, Greedy algorithm, Independent architecture, fixed-lambda family, bootstrap, `delta_U`, `delta_R`, aggregate PASS criteria, kill criteria, or quarantine.

## B1 — Residual scientific identity

`PASS`.

The v1.2 correction does not change the explicit frozen-score residual anchor already passed in v1.1:

$$
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)}.
$$

Independent retains the same explicit `+s_i` anchor. The admitted scientific object remains residual-budget marginal-DDI fixed-cardinality set refinement rather than replacement utility learning.

## B2 — MoleRec representation

`PASS`.

The exact patient/visit-conditioned MoleRec `molecule_embeddings[i]` extraction point immediately before `score_extractor` is unchanged. BudgetSet and Independent still receive the same frozen `s_i(x)` and `e_i(x)` from the same no-gradient pinned MoleRec forward pass.

## B3 — Gate01-Dev / Gate01-Audit split

`PASS`.

The deterministic patient-only SHA-256 membership formula, namespace, serialization, byte interpretation, and `u < 0.5` / `u >= 0.5` boundary are unchanged. No selection or outcome quantity enters membership.

## B4 — Low-cardinality execution

`PASS`.

The `K_x=0` and `K_x=1` Greedy branches and protocol-wide zero pair-risk semantics for `K_x<2` are unchanged.

## B5 — Checkpoint, patience, and configuration selection

`PASS`.

The per-seed checkpoint key, local patience semantics, retained-checkpoint rule, three-seed configuration aggregation, and deterministic LR/`eta` tie-break remain unchanged. Gate01-Audit still cannot select epoch, seed, checkpoint, configuration, or hyperparameter.

## B6 — Aggregation, frontier, bootstrap, and seed semantics

`PASS`.

The v1.1 re-audit already passed the observation unit, learned-seed aggregation, compliance aggregation, responsiveness, literal composition response, deterministic-control handling, matched Independent seeds, and within-replicate frontier recomputation. Protocol v1.2 closes the sole remaining empty-frontier seed-comparator gap without modifying aggregate materiality.

### Ordinary-frontier branch

For BudgetSet seed `r`, required primary region, and killer control `C`, the protocol defines

$$
E_{r,C}=\{j:R_{C,j}\le R_{B,r}+\delta_R\}.
$$

When $E_{r,C}\ne\varnothing$:

$$
F_{r,C}=\max_{j\in E_{r,C}}U_{C,j},
$$

$$
G_{r,C}=U_{B,r}-F_{r,C}.
$$

The favorable rule remains exactly:

```text
G_r,C > 0  -> favorable
G_r,C <= 0 -> non-favorable
```

No ordinary-frontier seed threshold or statistic changed.

### Empty-frontier branch

When $E_{r,C}=\varnothing$, every sampled control point is strictly above the frozen risk allowance. Protocol v1.2 selects

$$
j^\star=\operatorname*{arg\,min}_j\left(R_{C,j},-U_{C,j},o_j\right)
$$

with one lexicographic order:

1. lower hard-set DDI;
2. higher Jaccard;
3. lower canonical control-point order.

For the required killer families in this Gate, sampled operating points are the already-frozen requested-budget points and therefore use the unique order

```text
b_L < b_M < b_H
```

Any additional sampled point already defined by a control family must retain that family's pre-existing deterministic protocol order. A required killer family with zero sampled operating points does not enter this branch; it triggers the existing highest-priority `STOP_INVALID_GATE_IMPLEMENTATION` condition.

For the selected endpoint,

$$
H_{r,C}=U_{B,r}-U_{C,j^\star}.
$$

The empty-frontier favorable rule is uniquely:

```text
H_r,C > 0 -> favorable
H_r,C < 0 -> non-favorable
H_r,C = 0 -> favorable
```

or equivalently

$$
\text{favorable}\iff H_{r,C}\ge 0.
$$

The equality case is coherent with the branch premise because $R_{B,r}+\delta_R<R_{C,j^\star}$ already establishes a strict lower-risk direction. Protocol v1.2 adds no seed-level `0.005` margin, bootstrap requirement, scalarization, composite score, or hypervolume rule.

### Aggregate materiality remains unchanged

Section 11 still freezes

```text
delta_U = 0.005
delta_R = 0.005
```

and, for a non-empty aggregate eligible frontier, requires

```text
mean aggregate G_C >= 0.005
and patient-clustered bootstrap 95% CI lower bound(G_C) > 0
```

The pre-existing safer-than-entire-frontier aggregate branch is also unchanged. Therefore the two levels remain distinct:

```text
aggregate criterion = material effect
seed criterion      = directional reproducibility
```

The seed correction does not lower the aggregate material-effect requirement.

### Greedy seed semantics

Greedy remains deterministic. Each BudgetSet seed is compared against the same deterministic three-point Greedy control family. No Greedy seeds are manufactured. Branch A or Branch B therefore always yields one boolean favorable/non-favorable result for each required BudgetSet-seed comparison, provided the control family is valid and non-empty.

### Independent matched-seed semantics

Seed robustness remains matched exactly:

```text
BudgetSet 2002 <-> Independent 2002
BudgetSet 2003 <-> Independent 2003
BudgetSet 2004 <-> Independent 2004
```

For BudgetSet seed `r`, only the matched Independent seed `r` sampled operating points enter Section 12.2. The three Independent seeds are not pooled into a seed-level frontier. Aggregate Independent frontier and bootstrap semantics remain the family-level aggregation defined in Sections 11 and 12.1.

### Mechanical totality

Given any valid stored predictions and any valid non-empty required sampled control family, Section 12.2 now returns exactly one boolean favorable/non-favorable result for every required seed × primary-region × killer comparison:

- non-empty `E_{r,C}` -> finite-set maximum -> unique scalar `G_{r,C}` -> one boolean;
- empty `E_{r,C}` -> finite non-empty lexicographic minimum with deterministic final order -> unique `j^star` -> unique scalar `H_{r,C}` -> one boolean;
- zero sampled operating points -> `STOP_INVALID_GATE_IMPLEMENTATION` before seed favorability is required.

No `undefined`, `NaN`, skip, or implementation-defined favorable status remains.

Each of the four required comparisons still requires at least `2/3` favorable BudgetSet seeds:

```text
BudgetSet vs Greedy at b_L
BudgetSet vs Greedy at b_M
BudgetSet vs Independent at b_L
BudgetSet vs Independent at b_M
```

Otherwise `KILL_SEED_FRAGILITY` triggers under the already-frozen precedence.

## B7 — Terminal precedence

`PASS`.

The top-to-bottom primary-verdict precedence is unchanged. `STOP_INVALID_GATE_IMPLEMENTATION` remains first, followed by the scientific stop/kill conditions, `INCONCLUSIVE_STOP`, and finally PASS. The first triggered condition remains the primary verdict.

## Integrity summary

```text
B1 scientific identity: PASS
B2 representation: PASS
B3 split: PASS
B4 low-cardinality execution: PASS
B5 learned selection: PASS
B6 aggregation/statistics/seeds: PASS
B7 terminal precedence: PASS

Empty-frontier comparator total: YES
Deterministic tie-break: YES
Greedy semantics unique: YES
Independent matched-seed semantics unique: YES
Aggregate material criterion unchanged: YES
Regression found: NO
New execution blocker: NO
Scientific identity preserved: YES
PASS/KILL mechanically unique: YES
```

## Verdict

`DESIGN_INTEGRITY_PASS`

Gate 01 protocol v1.2 is sufficiently total, deterministic, leakage-safe, identity-preserving, and mechanically interpretable for the next pipeline phase. This verdict does not execute Gate 01, open Gate01-Audit, authorize recommendation-model training, or authorize formal Gate execution.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / NOT EXECUTED
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
Next phase to route: implementation / mechanical preflight only
Formal Gate execution: NOT AUTHORIZED
```
