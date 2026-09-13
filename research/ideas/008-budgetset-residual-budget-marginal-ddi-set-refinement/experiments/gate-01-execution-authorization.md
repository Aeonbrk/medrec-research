<!-- markdownlint-disable MD013 -->

# Gate 01 Formal Execution Authorization — Idea 008

## Authorization status

- **Starting authoritative revision**: `efbb26113f9340e24d5d24c47e13d3e4d46987b8`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Design integrity**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Independent implementation verification**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `FORMAL_GATE_01_EXECUTION_AUTHORIZED`
- **Execution-specific learned runner**: `REQUIRED / NOT_YET_IMPLEMENTED`
- **Runner implementation**: `AUTHORIZED`
- **Formal recommendation-model training**: `NOT_YET_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact
- **Next owner**: local coding agent

No scientific-design blocker remains. This artifact admits Idea 008 into the formal Gate-execution phase and freezes the downstream execution contract. It does not itself run the Gate, train BudgetSet or Independent, or open Gate01-Audit.

The current repository contains a verified mechanical-preflight module, not the complete learned scientific runner. The remaining work is bounded execution implementation. A new runner must pass an implementation-integrity check against this artifact and protocol v1.2 before recommendation-model training is activated. No design review is reopened.

## 1. Allowed implementation scope

The execution runner remains Idea-local.

Canonical new runner:

```text
research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/
experiments/gate01_execution.py
```

Canonical targeted test file:

```text
tests/unit/test_idea008_gate01_execution.py
```

The runner may import the mechanically verified pure functions and frozen MoleRec extraction contract from:

```text
research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/
experiments/gate01_mechanical_preflight.py
```

Do not modify `gate01_mechanical_preflight.py`, its tests, the protocol, the design-integrity re-audit, the mechanical-preflight record, baseline registry, or existing baseline programs unless a concrete protocol mismatch is found. A mismatch is a blocker to implementation, not permission to redesign the protocol.

Do not create a general framework, reusable package, compatibility layer, feature-flag system, solver abstraction, or `src/` promotion for this unproven Idea.

## 2. Frozen data and access boundary

The Gate uses dataset identity:

```text
molerec-table1-comparison-v1-1
```

The only partitions in the Gate are:

```text
canonical Comparison Train -> Gate01-Train
canonical Comparison Validation -> deterministic patient-disjoint Gate01-Dev / Gate01-Audit
```

The split remains the exact protocol-v1.2 SHA-256 patient-only split.

Current authorization is deliberately staged:

```text
runner implementation and synthetic/unit verification: AUTHORIZED
recommendation-model training: NOT_YET_AUTHORIZED
Gate01-Audit access: NOT_AUTHORIZED / UNOPENED
```

After the new runner passes implementation integrity, a later routing step may activate:

- `Gate01-Train` for BudgetSet/Independent training and Train-only calibration;
- `Gate01-Dev` for epoch/checkpoint/configuration selection only.

`Gate01-Audit` may be opened only after all Train/Dev selections are frozen. Once opened, it is evaluation-only. It may be used to compute the frozen visit-level metrics, target compliance, composition response, aggregate frontiers, matched-seed robustness, patient-clustered bootstrap intervals, and the terminal Gate verdict. It must not influence:

- epoch selection;
- seed selection;
- checkpoint selection;
- configuration selection;
- learning-rate selection;
- `eta` selection;
- any architecture or protocol choice.

Zero permission throughout Gate 01:

- G3/G4;
- R0 Holdout;
- historical project test;
- any alternate validation split;
- any paper-level SOTA expansion.

## 3. Frozen MoleRec identity

Use exactly:

```text
Backbone: MoleRec / molerec-embedding
Upstream revision: dd5afaf0a503fd3de3229f86ec7f26b345d10e3a
Checkpoint SHA-256: 5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca
Dataset identity: molerec-table1-comparison-v1-1
Candidate vocabulary: 131 medications
```

All MoleRec parameters remain frozen. One frozen `eval()` / no-gradient forward produces both the candidate logits `s_i(x)` and the corresponding visit-conditioned `molecule_embeddings[i]` immediately before `score_extractor` as `e_i(x)`. BudgetSet and Independent receive the same `s_i(x)` and `e_i(x)` from that same forward.

No MoleRec retraining, alternate checkpoint, alternate embedding tensor, additional patient encoder, medication encoder, molecular encoder, or ingredient encoder is allowed.

## 4. Exact cardinality and budgets

For each visit:

```text
K_x = count(sigmoid(s_i) >= 0.5)
```

Every hard-output method must return exactly `K_x` medications with canonical medication-order tie-breaking. For `K_x < 2`, hard and relaxed DDI risk and marginal DDI are zero. `K_x=0` returns the empty set; the deterministic Greedy `K_x=1` branch returns the highest frozen-score medication.

Compute `r_train` from Frozen Base on Gate01-Train and freeze exactly:

```text
b_L = 0.60 * r_train
b_M = 0.80 * r_train
b_H = 1.00 * r_train
```

If `r_train = 0`, the terminal rule is `STOP_NO_BASE_DDI_HEADROOM`.

## 5. BudgetSet architecture

Frozen recurrence:

$$
q_i^{(0)}=\sigma(s_i),
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\ne i}D_{ij}q_j^{(t)},
$$

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}),
$$

$$
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)
-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)}.
$$

Freeze exactly two refinement steps:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
-> exact TopK(K_x)
```

The learned heads are:

```text
utility head: [s_i, e_i] -> 64 -> 32 -> 1
risk-price head: [s_i, e_i, rho] -> 64 -> 32 -> 1
activation: GELU
dropout: none
```

No `T` sweep, width/depth sweep, dropout, new loss, new encoder, or alternate recurrence is allowed.

## 6. Independent architecture

Independent receives only:

```text
s_i(x)
e_i(x)
requested b
Train-only static d_i
Train-only static p_i
```

Its heads are:

```text
utility head: [s_i, e_i] -> 64 -> 32 -> 1
risk-price head: [s_i, e_i, b, d_i, p_i] -> 64 -> 32 -> 1
activation: GELU
dropout: none
```

Its score is:

$$
z_i^{ind}=s_i+u_\psi(s_i,e_i)
-\operatorname{softplus}(g_\psi(s_i,e_i,b,d_i,p_i))d_i.
$$

Independent must not access current-set `q`, marginal `c`, relaxed `R_DDI(q)`, residual slack `rho`, a provisional prescription, pair-to-current-set features, or iterative feedback. Final output is exact `TopK(K_x)`.

## 7. Frozen objective and optimization shell

BudgetSet and Independent use the same labels and objective:

$$
\mathcal L=
\mathbb E_{b\sim P_B}
\left[
\operatorname{BCEWithLogits}(z_b,y)
+\eta[R_{DDI}(q_b)-b]_+
+\gamma(\sum_iq_{b,i}-K_x)^2
\right].
$$

Freeze exactly:

```text
P_B = Uniform{b_L,b_M,b_H}
optimizer = AdamW
weight_decay = 1e-4
learning rates = {3e-4, 1e-3}
eta = {5, 10}
gamma = 1e-3
learned seeds = {2002, 2003, 2004}
max epochs = 30
patience = 5 Dev evaluations
configurations per learned family = 4
```

No additional seed, optimizer, schedule, loss, regularizer, auxiliary task, architecture variant, or tuning dimension is allowed.

## 8. Checkpoint and configuration selection

Each `family × configuration × seed` is trained independently. At every epoch, evaluate once on Gate01-Dev at all three budgets.

Per-seed checkpoint key is exactly:

```text
higher n_compliant
then higher U_primary
then lower V_all
then earlier epoch
```

where `U_primary` is the arithmetic mean Dev Jaccard at `b_L` and `b_M`, and `V_all` is the arithmetic mean over all three budgets of mean positive violation.

Patience is local to each seed/configuration and stops after five consecutive non-improving Dev evaluations or at epoch 30.

Retain one best checkpoint per `seed × configuration`.

For each learned family, select one configuration from the three retained seed checkpoints using the aggregate Dev key:

```text
higher n_compliant_config
then higher U_primary_config
then lower V_all_config
then smaller learning rate
then smaller eta
```

After configuration selection, freeze the selected configuration and its three retained seed checkpoints before any Gate01-Audit access.

## 9. Frozen controls

### Fixed-K Budget-Aware Greedy + 1-Swap

Use the exact deterministic protocol-v1.2 algorithm with identical `s`, DDI matrix, complete candidate pool, requested budget, and `K_x`. Do not add restarts, MILP/MIQP, beam search, evolutionary search, or another solver family.

### Fixed-lambda supporting family

Use exactly:

```text
lambda in {0, 0.25, 0.5, 1, 2, 4}
```

Select one `lambda_b` for each requested target using Gate01-Train only by minimizing absolute achieved-DDI distance to the target, with the frozen tie-break. Freeze these values before Dev/Audit evaluation.

## 10. Metrics and target compliance

Observation unit is `visit`; bootstrap cluster unit is `patient`.

Primary utility:

```text
Jaccard
```

Supporting utility:

```text
F1
PRAUC
```

For learned families, do not average logits or predictions across seeds. Aggregate operating-point utility/risk and compliance quantities by arithmetic mean across the three seed-level aggregate values exactly as protocol v1.2 defines.

A learned-family target is compliant iff:

```text
mean positive violation V_b <= 0.005
mean achieved hard DDI A_b <= b + 0.005
```

BudgetSet must comply at all three targets.

Exact cardinality agreement must be `100%` for every compared method.

## 11. Budget and composition response

BudgetSet material DDI responsiveness requires:

```text
R_L + 0.005 <= R_M
R_M + 0.005 <= R_H
```

Composition response uses literal hard-set inequality on visits with `K_x >= 1`.

Both transitions must satisfy:

```text
b_L -> b_M: mean change rate >= 10%
b_M -> b_H: mean change rate >= 10%
```

Per-seed change rates must be retained.

## 12. Aggregate frontier rule

Freeze:

```text
delta_U = 0.005
delta_R = 0.005
```

For a control family `C` and BudgetSet point `(R_B,U_B)`, if at least one control point satisfies `R_C <= R_B + delta_R`, compare against the maximum utility among eligible control points. BudgetSet is materially outside the control frontier only if:

```text
mean aggregate utility gap >= 0.005
and patient-clustered bootstrap 95% CI lower bound(gap) > 0
```

If the eligible frontier is empty, compare against the control's safest point and require:

```text
R_control - R_B >= 0.005
U_B - U_control >= -0.005
bootstrap 95% CI lower bound(U_B - U_control) > -0.005
```

The two required primary regions are exactly `b_L` and `b_M`.

## 13. Seed robustness

Learned seeds are exactly:

```text
2002
2003
2004
```

For a non-empty eligible seed-level control frontier, BudgetSet seed `r` is favorable iff its utility gap is strictly positive.

For an empty eligible frontier, select the unique control endpoint by:

```text
lower DDI
then higher Jaccard
then canonical control-point order
```

and mark the BudgetSet seed favorable iff its utility difference is `>= 0`.

Independent seed comparisons are matched only:

```text
2002 <-> 2002
2003 <-> 2003
2004 <-> 2004
```

Deterministic Greedy is not duplicated into artificial seeds.

Each required `killer × primary-region` comparison must have at least `2/3` favorable BudgetSet seeds or `KILL_SEED_FRAGILITY` triggers.

## 14. Patient-clustered bootstrap

Use exactly:

```text
1000 patient-clustered resamples
seed = 80081
95% CI = empirical 2.5th and 97.5th percentiles
```

Each replicate samples Audit patients with replacement, preserves sampled-patient multiplicity, includes all visits for each sampled patient, recomputes every operating point, reapplies learned-family seed aggregation, rebuilds the control frontier inside the replicate, and recomputes the relevant gap.

Do not bootstrap an already-computed scalar and do not refit models inside bootstrap replicates.

## 15. Terminal verdict precedence

Evaluate in this exact order; the first triggered condition is primary:

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

No later condition may replace an earlier triggered verdict.

## 16. Explicitly not authorized

```text
no protocol redesign
no extra hyperparameters
no additional seeds
no new architectures
no new encoders
no feature fishing
no solver expansion
no post-hoc rescue
no G3/G4
no R0 Holdout
no historical project test
no paper-level SOTA expansion
```

Also do not use Gate01-Audit for epoch, seed, checkpoint, configuration, or hyperparameter selection.

## 17. Immediate routing

The next owner is a local coding agent.

Its task is only to implement `gate01_execution.py` and targeted tests so that the frozen learned components and execution semantics are mechanically realizable. It must not train BudgetSet or Independent, open Gate01-Audit, compute scientific Gate results, or alter protocol identity.

On completion, the runner implementation must be checked against protocol v1.2 and this authorization. The expected next state is:

```text
IDEA_008_GATE_01_RUNNER_IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION
```

Only after a runner-integrity pass may the pipeline activate recommendation-model training.
