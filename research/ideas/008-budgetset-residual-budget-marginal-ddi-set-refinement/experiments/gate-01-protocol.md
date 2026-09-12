<!-- markdownlint-disable MD013 -->

# Gate 01 Protocol — BudgetSet Residual-Budget Marginal-DDI Set Refinement

## Protocol status

- **Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Owner**: `ccf-experiment-designer`
- **Mode**: `ccf-experiment-designer / design`
- **Stage**: `IDEA_008_GATE_01_DESIGN_FROZEN_PENDING_INTEGRITY_AUDIT`
- **Status**: `DESIGNED_NOT_EXECUTED`
- **Design revision**: `v1.0`
- **Design date**: `2026-09-12`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Training**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test are outside this Gate
- **Results**: none

This is the single cheapest falsification protocol for Idea 008. It freezes the method, equal-information killers, budget support, validation-only selection, uncertainty, practical margins, and stop rules before any model training or Gate-01 outcome is observed. It is hypothesis-selection evidence only, not publication claim-support evidence.

## 1. Gate 01 hypothesis

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient medication cardinality, does residual-budget marginal-DDI joint set refinement provide incremental utility–DDI frontier value beyond cheap equal-information direct optimization and independent budget conditioning?

A pass requires the claimed joint-set interaction to add value beyond both frozen killers over at least two separated non-trivial operating regions. A Base-only gain is insufficient.

## 2. Frozen scientific setting

### 2.1 Backbone

Use one already-qualified frozen backbone only:

- method: `MoleRec`;
- profile: `molerec-embedding`;
- upstream revision: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- prediction threshold used only to define Frozen Base cardinality: `0.5`;
- medication vocabulary size: `131`;
- all MoleRec parameters are frozen;
- no backbone retraining is permitted inside Gate 01.

Use the frozen per-medication embedding tensor already consumed by the `molerec-embedding` predictor as `e_i`. It is read from the qualified checkpoint and receives no gradient. No new medication, molecular, ingredient, or patient encoder is allowed.

### 2.2 Dataset and access boundary

Reuse the repository's Comparison Mode dataset identity `molerec-table1-comparison-v1-1` and its existing medication vocabulary and DDI asset. Gate 01 may use only the canonical benchmark Train and Validation partitions.

- canonical Train -> `Gate01-Train`;
- canonical Validation patients -> deterministic patient-disjoint `Gate01-Dev` / `Gate01-Audit` split using hash salt `idea008-gate01-v1`, with the lower half of the hash range assigned to Dev and the upper half to Audit;
- one patient's visits may appear in only one of Dev or Audit;
- Audit is opened once, only after hyperparameters, checkpoints, budget calibration, and all Idea-008 selection rules are frozen from Train/Dev. The upstream frozen MoleRec checkpoint may have been selected previously under repository baseline infrastructure; it is never reselected using Gate01-Audit.

Zero permission in this Gate:

- G3/G4;
- R0 Holdout;
- historical project test;
- any alternative validation split selected after outcomes are seen.

Patient-level rows, memberships, logits, predictions, and checkpoints remain outside Git.

## 3. Candidate pool and cardinality

For every visit `x`, every method receives the same candidate pool:

```text
C_x = complete 131-medication vocabulary
```

No method-specific filtering, retrieval, ground-truth membership filter, test-derived filter, or extra feasible candidate is permitted.

Define Frozen Base set

$$
S_{base}(x)=\{i:\sigma(s_i)\ge 0.5\},
$$

with medication-code ascending used only to resolve exact threshold ties if needed, and freeze

$$
K_x=|S_{base}(x)|.
$$

`K_x` is therefore determined only by the frozen backbone, never by the ground-truth medication count and never by requested budget `b`.

Every hard output from Frozen Base, Greedy+1Swap, the Independent Conditional Scorer, the Fixed-lambda family, and BudgetSet must satisfy

$$
|S_b(x)|=K_x
$$

exactly. For methods that produce scores, the final set is `TopK_{K_x}` with medication-code ascending as the final tie-break.

For `K_x < 2`:

$$
R_{DDI}(S)=0,\qquad R_{DDI}(q)=0,\qquad c_i(q)=0.
$$

These visits remain in utility and cardinality reporting but contribute zero pairwise DDI risk by definition.

## 4. Budget calibration and support

Let `r_train` be the mean hard-set DDI rate of Frozen Base on `Gate01-Train`, computed after `K_x` is frozen:

$$
r_{train}=\mathbb E_{x\in Train}[R_{DDI}(S_{base}(x))].
$$

If `r_train = 0`, stop with `STOP_NO_BASE_DDI_HEADROOM`; the admitted budget-refinement mechanism has no non-trivial DDI operating range in this development pool.

Freeze exactly three requested targets:

$$
b_L=0.60r_{train},\qquad b_M=0.80r_{train},\qquad b_H=1.00r_{train}.
$$

No clipping, extra target, denser sweep, interpolation target, or extrapolation target is allowed in Gate 01.

Training support for conditional learned methods is

$$
P_B=\operatorname{Uniform}\{b_L,b_M,b_H\},
$$

sampled independently per recommendation example. Evaluation reports all three targets. `b_L` and `b_M` are the two primary operating regions; `b_H` is the loose anchor needed for responsiveness and composition-change checks.

## 5. BudgetSet definition

### 5.1 Relaxed state and initialization

Use frozen MoleRec pre-threshold logits `s_i` and define

$$
z_i^{(0)}=s_i,\qquad q_i^{(0)}=\sigma(z_i^{(0)}).
$$

This initialization is deterministic, budget-independent, and DDI-independent. It performs no hidden safety optimization.

For `K_x >= 2`, define

$$
R_{DDI}(q)=\frac{\sum_{i<j}D_{ij}q_iq_j}{\binom{K_x}{2}},
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\ne i}D_{ij}q_j^{(t)},
$$

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}).
$$

`rho` is surrogate relaxed constraint slack only.

### 5.2 Learned heads

BudgetSet contains only two shared candidate heads:

- utility head `u_phi([s_i,e_i])`: MLP `input -> 64 -> 32 -> 1`;
- residual-conditioned risk-price head `g_phi([s_i,e_i,rho])`: MLP `input -> 64 -> 32 -> 1`.

Both use GELU activations and no dropout. The MoleRec logits and medication embeddings are frozen inputs.

At iteration `t`:

$$
u_i=u_\phi(s_i,e_i),
$$

$$
\lambda_i^{(t)}=\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)})),
$$

$$
z_i^{(t+1)}=u_i-\lambda_i^{(t)}c_i^{(t)},
$$

$$
q_i^{(t+1)}=\sigma(z_i^{(t+1)}).
$$

Freeze `T=2`.

`T=2` is the minimum value that actually instantiates one composition-feedback cycle: iteration 0 changes the provisional relaxed set; iteration 1 then recomputes both marginal DDI cost and residual slack from that changed composition. `T=1` would reduce the Gate to a one-shot reranker on the frozen initialization and would not test the admitted iterative interaction. No `T` sweep is permitted.

The final hard set is

$$
S_b=\operatorname{TopK}_{K_x}(z^{(2)}).
$$

## 6. Training objective

For BudgetSet and the Independent Conditional Scorer, use the same multi-label objective and the same label set:

$$
\mathcal L = \mathbb E_{b\sim P_B}\left[
\mathcal L_{rec}(z_b,y)
+\eta[R_{DDI}(q_b)-b]_+
+\gamma\left(\sum_iq_{b,i}-K_x\right)^2
\right],
$$

where `L_rec` is mean binary cross-entropy with logits over the 131 medications and `q_b = sigmoid(z_b)`.

Frozen common training shell:

- optimizer: AdamW;
- weight decay: `1e-4`;
- maximum epochs: `30`;
- early-stopping patience: `5` Dev evaluations;
- `gamma = 1e-3`, not tuned;
- learning-rate entitlement: `{3e-4, 1e-3}`;
- `eta` entitlement: `{5, 10}`;
- total candidate configurations: exactly `4` per learned family;
- no other optimizer, width, depth, dropout, auxiliary loss, monotonic loss, frontier loss, contrastive loss, distillation loss, or rescue loss.

Use the same hyperparameter grid and the same model-selection rule for BudgetSet and the Independent Conditional Scorer.

For each configuration, Train fitting uses all three frozen seeds. Dev selection is based on seed-mean results and is lexicographic:

1. maximize the number of requested budgets satisfying the Dev compliance rule in Section 10.2;
2. among ties, maximize mean Jaccard over `b_L` and `b_M`;
3. then minimize mean positive budget violation over all three budgets;
4. then prefer the smaller learning rate, smaller `eta`, and earlier checkpoint in that order.

Audit is not used for checkpoint or hyperparameter selection.

## 7. Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This control receives exactly `s`, `D`, `C_x`, `b`, and `K_x`. It has no learned parameters.

Objective:

$$
\max_S\sum_{i\in S}s_i
$$

subject to

$$
|S|=K_x,\qquad R_{DDI}(S)\le b.
$$

Deterministic construction for `K_x >= 2`:

1. set `S = empty` and total pair budget `B=b*binom(K_x,2)`;
2. until `|S|=K_x`, among remaining candidates whose addition keeps the current DDI-pair count no larger than `B`, add the highest-`s_i` candidate; if none exists, add the candidate with the smallest incremental DDI-pair count, breaking ties by higher `s_i` and then medication code ascending;
3. if the completed set violates `b`, repeatedly apply the selected/unselected 1-swap that most reduces `max(0,R_DDI(S)-b)`; break ties by larger retained `sum s_i`, then medication codes ascending; stop when feasible or when no swap reduces violation;
4. once feasible, repeatedly apply the feasible 1-swap with the largest positive increase in `sum s_i`; break ties by lower resulting DDI rate and then medication codes ascending;
5. stop when no improving feasible 1-swap exists.

If Step 3 cannot reach feasibility, return the locally minimum-violation fixed-K set and record the violation; do not add another solver, restart family, MILP, MIQP, beam search, or evolutionary method.

Core killer:

```text
Greedy+1Swap comparable to or better than BudgetSet
-> KILL_BUDGETSET
```

## 8. Killer 2 — Budget-Conditioned Independent Scorer

This control is intentionally strong and budget-aware but cannot inspect provisional set composition.

Train-only static DDI summaries for medication `i` are:

$$
d_i=\frac{1}{|C|-1}\sum_{j\ne i}D_{ij},
$$

and

$$
p_i=\frac{\#\{x\in Train:i\in y_x\ \land\ \exists j\in y_x,D_{ij}=1\}}
{\max(1,\#\{x\in Train:i\in y_x\})}.
$$

`d_i` and `p_i` are frozen before Dev/Audit evaluation.

The independent scorer uses no less patient-conditioned information than BudgetSet: `s_i` is the same complete frozen patient-conditioned candidate score supplied to BudgetSet; neither Gate-01 method receives an additional patient encoder. Its inputs are:

- frozen `s_i`;
- frozen medication embedding `e_i`;
- requested `b`;
- static `d_i`;
- static `p_i`.

It uses the same utility head architecture as BudgetSet and a risk-price head with the same `64 -> 32 -> 1` hidden widths:

$$
u_i=u_\psi(s_i,e_i),
$$

$$
\lambda_i^{ind}=\operatorname{softplus}(g_\psi(s_i,e_i,b,d_i,p_i)),
$$

$$
z_i^{ind}=u_i-\lambda_i^{ind}d_i.
$$

The independent scorer may not access `q^(t)`, `c_i(q)`, `R_DDI(q)`, `rho`, a current provisional prescription, pairwise candidate-to-current-set features, or any iterative set feedback. It uses exact `TopK_{K_x}`.

Its optimizer, objective, seeds, tuning grid, early stopping, and selection rule are identical to BudgetSet. The extra static scalar inputs make its learnable capacity slightly larger, not smaller, than the BudgetSet heads; no parameter-count rescue is needed.

Core killer:

```text
Independent Conditional Scorer comparable to or better than BudgetSet
-> KILL_JOINT_SET_INTERACTION
```

## 9. Fixed-lambda family

This family is supporting evidence only. It asks whether one conditional model adds value beyond separately calibrated fixed operating points; it is not a third primary killer.

For each visit, standardize frozen logits by an order-preserving affine transform

$$
\tilde s_i=\frac{s_i-\operatorname{mean}(s)}{\max(\operatorname{std}(s),10^{-6})}.
$$

For each

```text
lambda in {0, 0.25, 0.5, 1, 2, 4}
```

run two deterministic refinement steps:

$$
z^{(0)}=\tilde s,\quad q^{(0)}=\sigma(z^{(0)}),
$$

$$
z_i^{(t+1)}=\tilde s_i-\lambda c_i(q^{(t)}),\quad q^{(t+1)}=\sigma(z_i^{(t+1)}),
$$

then exact `TopK_{K_x}`.

For each requested target `b`, choose one `lambda_b` using `Gate01-Train` only by minimizing

$$
|\operatorname{mean}R_{DDI}(S_{\lambda})-b|.
$$

Ties prefer larger mean frozen `sum s_i` and then smaller `lambda`. Freeze the selected `lambda_b` values before Dev/Audit. Different targets may map to the same lambda; do not expand the support if they do.

## 10. Metrics and target semantics

### 10.1 Utility

Primary utility metric:

```text
Jaccard
```

Supporting utility metrics:

```text
F1
PRAUC
```

Jaccard and F1 are computed from the final hard set. PRAUC uses each method's final candidate ranking. For Greedy+1Swap, selected medications rank above unselected medications and each group is ordered by frozen `s_i`, with medication code as final tie-break.

No Gate decision may switch the primary utility metric after results are seen.

### 10.2 DDI target and cardinality metrics

For every method and budget report:

- requested `b`;
- mean hard-set achieved `R_DDI(S_b)`;
- mean positive violation `mean(max(0,R_DDI(S_b)-b))`;
- mean absolute achieved-vs-requested deviation;
- conventional pooled pairwise DDI rate as supporting context;
- mean medication count;
- exact per-visit `K_x` agreement rate.

A requested target is Gate-compliant iff both hold:

```text
mean positive violation <= 0.005
mean achieved DDI <= b + 0.005
```

BudgetSet must satisfy this rule at all three requested targets. This is an operating-target tolerance, not a hard clinical guarantee.

Exact cardinality compliance must be `100%` for every compared method. Any cardinality mismatch invalidates the run and stops the Gate rather than being interpreted as scientific evidence.

### 10.3 Budget responsiveness and composition response

For BudgetSet, report the achieved-DDI slope against requested `b` and the adjacent ordering.

Material responsiveness requires:

```text
R_L + 0.005 <= R_M
R_M + 0.005 <= R_H
```

where `R_L`, `R_M`, and `R_H` are Audit mean hard-set DDI rates at the three targets.

For set composition, report adjacent-budget hard-set Jaccard and the fraction of visits whose prescription changes. Material composition response requires at least `10%` of visits to change hard set for both `b_L -> b_M` and `b_M -> b_H`.

If the scores move but the hard Top-K sets do not satisfy this change rule, BudgetSet has not demonstrated controllable set refinement.

## 11. Frontier comparison and statistical rule

Use `Gate01-Audit` only after all selection is frozen.

Uncertainty:

- patient-clustered bootstrap;
- `1000` resamples;
- bootstrap seed `80081`;
- patient is the resampling unit;
- for learned methods, aggregate each patient's metric contributions across the three frozen seeds before computing the bootstrap statistic;
- no model is refit inside bootstrap replicates.

Practical margins are frozen as

```text
delta_U = 0.005 absolute Jaccard
delta_R = 0.005 absolute hard-set DDI rate
```

For a control family `C`, form its three Audit operating points. For a BudgetSet point with achieved risk `R_B`, define the control frontier utility

$$
F_C(R_B)=\max\{U_C: R_C\le R_B+\delta_R\}.
$$

If the set is non-empty, define

$$
G_C=U_B-F_C(R_B).
$$

BudgetSet is **materially outside** that control frontier at the region iff

```text
mean(G_C) >= 0.005
and 95% bootstrap CI lower bound(G_C) > 0
```

If no control point satisfies `R_C <= R_B + delta_R`, BudgetSet is safer than the entire sampled control family. That region counts as materially outside only if, against the control's safest point,

```text
R_control - R_B >= 0.005
and U_B - U_control >= -0.005
and 95% CI lower bound(U_B - U_control) > -0.005
```

This is the sole Gate-01 meaning of a practical utility–DDI frontier win.

For a killer control, `comparable / ≈` means the evidence does not establish BudgetSet's practical frontier advantage and the control is within the practical margin or better. Operationally, if the relevant utility-gap 95% CI upper bound is `<= 0.005`, the control is comparable. If the interval straddles the practical boundary without proving either material superiority or comparability, return `INCONCLUSIVE_STOP`; do not tune the protocol.

The two required separated regions are exactly `b_L` and `b_M`. They count only if BudgetSet is target-compliant and the responsiveness rule confirms their achieved DDI values are separated by at least `0.005`.

## 12. Seeds and one-seed protection

Frozen learned-model seeds:

```text
{2002, 2003, 2004}
```

BudgetSet and the Independent Conditional Scorer use matched seeds and identical tuning entitlement. Greedy+1Swap and the Fixed-lambda family are deterministic and do not receive artificial seeds.

A frontier effect is not allowed to survive on one favorable seed only. At each primary region and against each killer, at least `2 of 3` BudgetSet seed-specific frontier utility gaps must have the favorable sign in addition to the pooled bootstrap rule in Section 11.

## 13. Formal decision tree

### 13.1 Mechanical invalidation

If any method fails exact `K_x` compliance, or any method receives a different candidate pool, DDI matrix, frozen logits, requested target, or cardinality:

```text
STOP_INVALID_GATE_IMPLEMENTATION
```

No scientific conclusion follows.

### 13.2 Budget semantics

If BudgetSet fails target compliance at any requested target:

```text
KILL_TARGET_SEMANTICS
```

If the adjacent achieved-DDI responsiveness rule fails:

```text
KILL_BUDGET_RESPONSE
```

If either adjacent composition-change rate is below `10%`:

```text
KILL_COMPOSITION_RESPONSE
```

No monotonic, budget-response, frontier, or rescue loss may be added afterward under Idea 008.

### 13.3 Greedy killer

BudgetSet must be materially outside the Greedy+1Swap frontier at both `b_L` and `b_M`.

If Greedy is comparable/better at either region, or BudgetSet wins only one isolated primary region:

```text
KILL_BUDGETSET
```

### 13.4 Independent-scorer killer

BudgetSet must be materially outside the Independent Conditional Scorer frontier at both `b_L` and `b_M`.

If the Independent scorer is comparable/better at either region, or BudgetSet wins only one isolated primary region:

```text
KILL_JOINT_SET_INTERACTION
```

This terminates Idea 008 as currently claimed.

### 13.5 Seed fragility

If either required primary-region advantage is carried by only one favorable BudgetSet seed:

```text
KILL_SEED_FRAGILITY
```

### 13.6 Inconclusive evidence

If a primary comparison interval straddles the frozen practical boundary and neither a material win nor comparability is established:

```text
INCONCLUSIVE_STOP
```

Do not increase seeds, change thresholds, add budgets, alter `T`, expand model capacity, add losses, or switch backbones as an Idea-008 rescue.

### 13.7 Pass

Return

```text
PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES
```

only if all of the following hold:

1. every compared hard output has exact `|S_b|=K_x`;
2. BudgetSet is target-compliant at all three budgets;
3. requested `b` materially changes hard-set achieved DDI in the frozen order;
4. adjacent budgets induce material hard-set medication substitutions;
5. BudgetSet is materially outside the Greedy+1Swap frontier at both `b_L` and `b_M`;
6. BudgetSet is materially outside the Independent Conditional frontier at both `b_L` and `b_M`;
7. both required frontier effects satisfy the one-seed protection rule.

A pass means only that the admitted mechanism survives its cheapest equal-information falsification gate. It does not establish clinical safety, clinical optimality, CCF-A readiness, or paper completion.

## 14. Reporting schema

The Gate report must contain, with no fabricated values:

| Method | Budget / lambda | Seed | Jaccard | F1 | PRAUC | Hard-set DDI | Mean violation | Abs deviation | Mean meds | Exact-K rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen Base | fixed | deterministic | TBD | TBD | TBD | TBD | n/a | n/a | TBD | TBD |
| Greedy+1Swap | `b_L,b_M,b_H` | deterministic | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Independent Conditional | `b_L,b_M,b_H` | `2002..2004` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Fixed-lambda | selected `lambda_b` | deterministic | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| BudgetSet | `b_L,b_M,b_H` | `2002..2004` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Also report:

- `r_train`, `b_L`, `b_M`, `b_H`;
- the three selected Fixed-lambda values;
- BudgetSet adjacent achieved-DDI gaps;
- adjacent set-change rates and set overlap;
- frontier gaps and 95% bootstrap intervals for both killers at both primary regions;
- seed-specific sign table for the four required killer-region comparisons;
- selected learned hyperparameters and checkpoint epoch from Dev only;
- quarantine confirmation.

## 15. No-rescue boundary and next routing

Gate 01 does not authorize:

- another backbone;
- another candidate pool;
- exact-solver zoo;
- denser budget sweep;
- `T` search;
- new encoder, Transformer, Mamba, MoE, RL, LLM, retrieval, ingredient, or molecular branch;
- additional losses;
- subgroup mining;
- G3/G4, R0 Holdout, or historical test access;
- paper-level SOTA benchmarking.

The protocol is `DESIGN_READY` but training remains `NOT_AUTHORIZED` until an independent `ccf-integrity-auditor` verifies design consistency, equal information entitlement, access boundaries, implementability, and decision-rule completeness. After an integrity pass, routing returns to `ccf-pipeline-orchestrator` for explicit execution authorization.
