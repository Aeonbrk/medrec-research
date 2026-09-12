<!-- markdownlint-disable MD013 -->

# Gate 01 Protocol — BudgetSet Residual-Budget Marginal-DDI Set Refinement

## Protocol status

- **Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Owner**: `ccf-experiment-designer`
- **Mode**: `ccf-experiment-designer / design`
- **Stage**: `IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT`
- **Status**: `DESIGNED_NOT_EXECUTED`
- **Design revision**: `v1.2`
- **Design date**: `2026-09-13`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Integrity state**: `PENDING_REAUDIT`
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test are outside this Gate
- **Gate01-Audit**: unopened
- **Results**: none

This is the single cheapest falsification protocol for Idea 008. It freezes the admitted method, equal-information killers, budget support, validation-only selection, uncertainty, practical margins, and terminal rules before any Gate-01 model training or outcome is observed. It is hypothesis-selection evidence only, not publication claim-support evidence.

## 1. Gate 01 hypothesis

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient medication cardinality, does residual-budget marginal-DDI joint set refinement provide incremental utility–DDI frontier value beyond cheap equal-information direct optimization and independent budget conditioning?

A pass requires the claimed joint-set interaction to add value beyond both frozen killers over both separated primary operating regions. A Base-only gain is insufficient.

## 2. Frozen scientific setting

### 2.1 Backbone and exact candidate representation

Use one already-qualified frozen backbone only:

- method: `MoleRec`;
- profile: `molerec-embedding`;
- upstream repository: `yangnianzu0515/MoleRec`;
- upstream revision: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- prediction threshold used only to define Frozen Base cardinality: `0.5`;
- medication vocabulary size: `131`;
- all MoleRec parameters are frozen;
- no backbone retraining is permitted inside Gate 01.

For visit/patient instance `x`, define `e_i(x)` exactly as the candidate-specific `molecule_embeddings[i]` tensor produced inside the pinned MoleRec `MoleRecModel.forward` immediately before the tensor is consumed by `self.score_extractor`.

The deterministic extraction contract is:

```text
pinned MoleRec src/modules/MoleRec.py
MoleRecModel.forward
-> patient_repr
-> query
-> substruct_weight
-> global_embeddings / substruct_embeddings
-> molecule_embeddings = self.aggregator(...)
-> score = self.score_extractor(molecule_embeddings).t()
```

The same no-gradient frozen MoleRec forward pass produces both:

- `s_i(x)`: the candidate pre-threshold logit from `score`;
- `e_i(x)`: the corresponding row of `molecule_embeddings` immediately before `score_extractor`.

Therefore:

- all MoleRec parameters are frozen;
- no gradient enters MoleRec;
- `e_i(x)` is patient/visit-conditioned because the forward pass conditions `molecule_embeddings` through the patient-derived `substruct_weight`;
- there is no separate embedding training;
- no global molecular embedding, substructure embedding, checkpoint parameter, or other MoleRec internal tensor may substitute for `e_i(x)`;
- BudgetSet and Independent receive the same `s_i(x)` and `e_i(x)` from the same frozen forward.

No new medication, molecular, ingredient, or patient encoder is allowed.

### 2.2 Dataset and access boundary

Reuse the repository Comparison Mode dataset identity `molerec-table1-comparison-v1-1` and its existing medication vocabulary and DDI asset. Gate 01 may use only the canonical benchmark Train and Validation partitions.

- canonical Train -> `Gate01-Train`;
- canonical Validation -> deterministic patient-disjoint `Gate01-Dev` / `Gate01-Audit`;
- the Dev/Audit ratio remains exactly `0.5 / 0.5`;
- one patient's visits may appear in only one of Dev or Audit;
- no labels, outcomes, predictions, model results, or DDI values enter split assignment;
- Audit remains unopened until all Train/Dev selection is frozen.

The unique split procedure is:

```text
namespace = "idea008-gate01-v1"
patient_id = zero-based integer patient index in the pinned records_final.pkl
             canonical Comparison split ordering
patient key = ASCII decimal representation of patient_id
              with no leading or trailing whitespace
message = namespace + ":" + patient key
digest = SHA-256(message encoded as UTF-8)
value = first 8 digest bytes interpreted as unsigned big-endian integer
u = value / 2^64

Gate01-Dev   iff u < 0.5
Gate01-Audit iff u >= 0.5
```

All visits belonging to one patient inherit that patient's assignment. The upstream frozen MoleRec checkpoint may have been selected previously under repository baseline infrastructure; it is never reselected using Gate01-Audit.

Zero permission in this Gate:

- G3/G4;
- R0 Holdout;
- historical project test;
- any alternative validation split selected after outcomes are seen.

Patient-level rows, memberships, logits, predictions, and checkpoints remain outside Git.

## 3. Candidate pool and exact cardinality

For every visit `x`, every method receives the same candidate pool:

```text
C_x = complete 131-medication vocabulary
```

No method-specific filtering, retrieval, ground-truth membership filter, test-derived filter, or extra feasible candidate is permitted.

Define the Frozen Base set

$$
S_{base}(x)=\{i:\sigma(s_i)\ge 0.5\},
$$

and freeze

$$
K_x=|S_{base}(x)|.
$$

`K_x` is determined only by the frozen backbone, never by ground-truth medication count and never by requested budget `b`.

Every hard output from Frozen Base, Greedy+1Swap, Independent, Fixed-lambda, and BudgetSet must satisfy

$$
|S_b(x)|=K_x
$$

exactly. For score-producing methods, the final set is `TopK_{K_x}`. Any score tie is resolved by ascending medication code according to the repository's canonical vocabulary ordering; implementation must use that canonical vocabulary order rather than introduce a second ordering.

For `K_x < 2`:

$$
R_{DDI}(S)=0,\qquad R_{DDI}(q)=0,\qquad c_i(q)=0.
$$

These visits remain in utility and exact-cardinality reporting.

## 4. Budget calibration and support

Let `r_train` be the visit-mean hard-set DDI rate of Frozen Base on `Gate01-Train`, computed after `K_x` is frozen:

$$
r_{train}=\operatorname{mean}_{x\in Gate01\text{-}Train}R_{DDI}(S_{base}(x)).
$$

If `r_train = 0`, the primary terminal condition is `STOP_NO_BASE_DDI_HEADROOM`.

Freeze exactly:

$$
b_L=0.60r_{train},\qquad b_M=0.80r_{train},\qquad b_H=1.00r_{train}.
$$

No clipping, extra target, denser sweep, interpolation target, or extrapolation target is allowed.

Training support for conditional learned methods is

$$
P_B=\operatorname{Uniform}\{b_L,b_M,b_H\},
$$

sampled independently per recommendation example. Evaluation reports all three targets. `b_L` and `b_M` are the two primary regions; `b_H` is the loose anchor for responsiveness and composition response.

## 5. BudgetSet definition

### 5.1 Relaxed state

Use frozen MoleRec logits:

$$
z_i^{(0)}=s_i,\qquad q_i^{(0)}=\sigma(z_i^{(0)}).
$$

For `K_x >= 2`:

$$
R_{DDI}(q)=\frac{\sum_{i<j}D_{ij}q_iq_j}{\binom{K_x}{2}},
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\ne i}D_{ij}q_j^{(t)},
$$

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}).
$$

`rho` is relaxed surrogate constraint slack only.

### 5.2 Learned heads and residual anchor

BudgetSet contains only two shared candidate heads:

- utility head `u_phi([s_i,e_i])`: MLP `input -> 64 -> 32 -> 1`;
- residual-conditioned risk-price head `g_phi([s_i,e_i,rho])`: MLP `input -> 64 -> 32 -> 1`.

Both use GELU and no dropout. `s_i` and `e_i(x)` are frozen MoleRec inputs.

At iteration `t`:

$$
u_i=u_\phi(s_i,e_i),
$$

$$
\lambda_i^{(t)}=\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)})),
$$

$$
\Delta_i^{(t)}=u_i-\lambda_i^{(t)}c_i^{(t)},
$$

$$
z_i^{(t+1)}=s_i+\Delta_i^{(t)}
=s_i+u_\phi(s_i,e_i)
-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)},
$$

$$
q_i^{(t+1)}=\sigma(z_i^{(t+1)}).
$$

The explicit frozen base score `s_i` is the residual anchor. The learned utility head refines that scorer; it does not replace it.

Freeze `T=2`. Iteration 1 must recompute both `c_i(q^(1))` and `rho^(1)` from the changed relaxed composition. No `T` sweep is permitted.

Final hard output:

$$
S_b=\operatorname{TopK}_{K_x}(z^{(2)}).
$$

## 6. Training objective and learned selection

BudgetSet and Independent use the same multi-label objective and the same labels:

$$
\mathcal L =
\mathbb E_{b\sim P_B}\left[
\mathcal L_{rec}(z_b,y)
+\eta[R_{DDI}(q_b)-b]_+
+\gamma\left(\sum_iq_{b,i}-K_x\right)^2
\right],
$$

where `L_rec` is mean binary cross-entropy with logits over all 131 medications and `q_b=sigmoid(z_b)`.

Frozen common training shell:

- optimizer: AdamW;
- weight decay: `1e-4`;
- maximum epochs: `30`;
- early-stopping patience: `5` Dev evaluations;
- `gamma = 1e-3`, not tuned;
- learning rate: `{3e-4, 1e-3}`;
- `eta`: `{5, 10}`;
- learned seeds: `{2002, 2003, 2004}`;
- exactly `4` configurations per learned family;
- no additional optimizer, width, depth, dropout, auxiliary loss, monotonic loss, frontier loss, contrastive loss, distillation loss, or rescue loss.

BudgetSet and Independent use exactly the same selection procedure.

### 6.1 Per-seed checkpoint selection

Each `family × hyperparameter configuration × seed` is trained independently. At the end of every epoch, evaluate that run once on Gate01-Dev at all three requested budgets.

For each epoch compute, from that seed's visit-level predictions:

1. `n_compliant`: number of requested budgets satisfying the Dev compliance rule in Section 10.2;
2. `U_primary`: arithmetic mean of Dev Jaccard at `b_L` and `b_M`;
3. `V_all`: arithmetic mean over `b_L,b_M,b_H` of mean positive budget violation.

The checkpoint key is lexicographic:

```text
higher n_compliant
then higher U_primary
then lower V_all
then earlier epoch
```

The current epoch becomes the new best checkpoint only when it is strictly better under this exact key. The patience counter is local to that seed/configuration, resets only when the current epoch becomes the new best checkpoint, otherwise increments by one, and stops training after `5` consecutive non-improving Dev evaluations or at the 30-epoch ceiling.

Retain exactly one best checkpoint for each `seed × configuration`.

### 6.2 Configuration selection

For a configuration, evaluate the three retained seed checkpoints and first form the seed-aggregate Dev quantities using Section 10's learned-family aggregation rules. From those aggregate operating points compute:

1. `n_compliant_config`: number of requested budgets satisfying the aggregate Dev compliance rule;
2. `U_primary_config`: arithmetic mean of aggregate Jaccard at `b_L` and `b_M`;
3. `V_all_config`: arithmetic mean over all three budgets of aggregate mean positive violation.

Select one configuration per learned family lexicographically:

```text
higher n_compliant_config
then higher U_primary_config
then lower V_all_config
then smaller learning rate
then smaller eta
```

After the configuration is selected, Audit uses exactly the three retained checkpoints belonging to that single configuration. Gate01-Audit never selects epoch, seed, configuration, or hyperparameter.

## 7. Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic control receives exactly `s`, `D`, `C_x`, `b`, and `K_x`. It has no learned parameters.

Objective:

$$
\max_S\sum_{i\in S}s_i
$$

subject to

$$
|S|=K_x,\qquad R_{DDI}(S)\le b.
$$

Low-cardinality branches are frozen:

```text
K_x = 0 -> return the empty set
K_x = 1 -> return the single candidate with maximum frozen s_i
           using ascending medication code / canonical vocabulary order as tie-break
```

For both branches:

```text
hard DDI = 0
relaxed pair risk = 0 where applicable
budget violation = 0
```

Do not invoke ordinary pair-budget Greedy logic for `K_x < 2`.

For `K_x >= 2`, deterministic construction is:

1. set `S = empty` and total pair budget `B=b*binom(K_x,2)`;
2. until `|S|=K_x`, among remaining candidates whose addition keeps current DDI-pair count no larger than `B`, add the highest-`s_i` candidate; if none exists, add the candidate with smallest incremental DDI-pair count, breaking ties by higher `s_i` and then canonical medication order;
3. if the completed set violates `b`, repeatedly apply the selected/unselected 1-swap that most reduces `max(0,R_DDI(S)-b)`; break ties by larger retained `sum s_i`, then canonical medication order; stop when feasible or when no swap reduces violation;
4. once feasible, repeatedly apply the feasible 1-swap with the largest positive increase in `sum s_i`; break ties by lower resulting DDI rate and then canonical medication order;
5. stop when no improving feasible 1-swap exists.

If Step 3 cannot reach feasibility, return the locally minimum-violation fixed-K set and record the violation. Do not add another solver, restart family, MILP, MIQP, beam search, or evolutionary method.

## 8. Killer 2 — Budget-Conditioned Independent Scorer

Train-only static DDI summaries for medication `i` are:

$$
d_i=\frac{1}{|C|-1}\sum_{j\ne i}D_{ij},
$$

$$
p_i=
\frac{\#\{x\in Train:i\in y_x\land \exists j\in y_x,D_{ij}=1\}}
{\max(1,\#\{x\in Train:i\in y_x\})}.
$$

`d_i` and `p_i` are frozen before Dev/Audit evaluation.

Independent receives:

- the same frozen `s_i(x)`;
- the same frozen patient/visit-conditioned `e_i(x)`;
- requested `b`;
- static `d_i`;
- static `p_i`.

It uses the same utility-head architecture as BudgetSet and a risk-price head with the same `64 -> 32 -> 1` hidden widths:

$$
u_i=u_\psi(s_i,e_i),
$$

$$
\lambda_i^{ind}=
\operatorname{softplus}(g_\psi(s_i,e_i,b,d_i,p_i)),
$$

$$
z_i^{ind}
=s_i+u_\psi(s_i,e_i)
-\operatorname{softplus}(g_\psi(s_i,e_i,b,d_i,p_i))d_i.
$$

The explicit `+s_i` anchor is mandatory. Independent may not access `q^(t)`, `c_i(q)`, `R_DDI(q)`, `rho`, current provisional prescription, pairwise candidate-to-current-set features, or iterative set feedback. Final output is exact `TopK_{K_x}`.

Its optimizer, objective, seeds, tuning grid, early stopping, checkpoint rule, and configuration-selection rule are identical to BudgetSet. Static scalar inputs make the control no weaker in learned input capacity; no parameter-count rescue is allowed.

## 9. Fixed-lambda supporting family

This family is supporting evidence only.

For each visit, standardize frozen logits by the order-preserving affine transform

$$
\tilde s_i=
\frac{s_i-\operatorname{mean}(s)}
{\max(\operatorname{std}(s),10^{-6})}.
$$

For each

```text
lambda in {0, 0.25, 0.5, 1, 2, 4}
```

run two deterministic refinement steps:

$$
z^{(0)}=\tilde s,\qquad q^{(0)}=\sigma(z^{(0)}),
$$

$$
z_i^{(t+1)}=\tilde s_i-\lambda c_i(q^{(t)}),\qquad
q_i^{(t+1)}=\sigma(z_i^{(t+1)}),
$$

then exact `TopK_{K_x}`.

For each requested target `b`, choose one `lambda_b` using Gate01-Train only by minimizing

$$
|\operatorname{mean}R_{DDI}(S_\lambda)-b|.
$$

Ties prefer larger mean frozen `sum s_i` and then smaller `lambda`. Freeze the selected values before Dev/Audit. Different targets may map to the same lambda; support must not expand.

## 10. Metrics, observation unit, and target semantics

### 10.1 Base observation and utility

The metric observation unit is `visit`. The bootstrap cluster unit is `patient`.

Primary utility:

```text
Jaccard
```

Supporting utility:

```text
F1
PRAUC
```

Jaccard, F1, hard-set DDI, budget violation, and composition response are computed first at visit level. PRAUC uses each method's final candidate ranking. For Greedy+1Swap, selected medications rank above unselected medications; within each group use frozen `s_i` and then canonical medication order.

### 10.2 Learned-seed aggregation and compliance

For BudgetSet or Independent, each `seed × requested budget` produces its own visit-level predictions and aggregate operating point:

$$
(R_{seed,b},U_{seed,b}).
$$

Do not average logits or predictions across seeds.

The learned-family operating point is:

$$
R_b=\frac{1}{3}\sum_{seed}R_{seed,b},
\qquad
U_b=\frac{1}{3}\sum_{seed}U_{seed,b}.
$$

For every seed and requested budget, compute across visits:

$$
V_{seed,b}=
\operatorname{mean}_{visits}
[\max(0,R_x-b)],
$$

$$
A_{seed,b}=
\operatorname{mean}_{visits}R_x.
$$

Family-level compliance quantities are arithmetic means over the three seeds:

$$
V_b=\frac{1}{3}\sum_{seed}V_{seed,b},
\qquad
A_b=\frac{1}{3}\sum_{seed}A_{seed,b}.
$$

A learned-family target is Gate-compliant iff:

```text
V_b <= 0.005
A_b <= b + 0.005
```

BudgetSet must satisfy this at all three requested budgets. Per-seed values must also be retained for seed-robustness reporting.

For deterministic Greedy and Fixed-lambda, compute the same visit-mean quantities once; do not duplicate the predictions into artificial seeds.

For every method and budget report:

- requested `b`;
- visit-mean hard-set achieved DDI;
- visit-mean positive violation;
- visit-mean absolute achieved-vs-requested deviation;
- conventional pooled pairwise DDI rate as supporting context;
- mean medication count;
- exact per-visit `K_x` agreement rate.

Exact cardinality compliance must be `100%` for every compared method.

### 10.3 Responsiveness

For BudgetSet, define `R_L`, `R_M`, and `R_H` as the family-level mean-across-seeds achieved hard-DDI rates from Section 10.2.

Material responsiveness requires:

$$
R_L+0.005\le R_M,
$$

$$
R_M+0.005\le R_H.
$$

### 10.4 Composition response

For a seed and two budgets, a visit changes composition iff the hard sets are literally unequal:

```text
S_b1(x) != S_b2(x)
```

The denominator is all evaluated visits with `K_x >= 1`. Visits with `K_x=0` are excluded because prescription composition cannot change.

For each learned seed, compute the fraction of eligible visits whose hard set changes. Gate-level composition response is the arithmetic mean over the three BudgetSet seeds.

Both transitions must satisfy:

```text
b_L -> b_M: change rate >= 10%
b_M -> b_H: change rate >= 10%
```

Retain per-seed change rates. Set-overlap statistics may be reported as supporting context, but no overlap threshold replaces literal set inequality.

## 11. Frontier comparison

Practical margins are frozen:

```text
delta_U = 0.005 absolute Jaccard
delta_R = 0.005 absolute hard-set DDI rate
```

For a control family `C`, form its three operating points. For a BudgetSet point with achieved risk `R_B`, define:

$$
F_C(R_B)=\max\{U_C:R_C\le R_B+\delta_R\}.
$$

When this set is non-empty:

$$
G_C=U_B-F_C(R_B).
$$

BudgetSet is materially outside that control frontier at a primary region iff:

```text
mean aggregate G_C >= 0.005
and bootstrap 95% CI lower bound(G_C) > 0
```

If no control point satisfies `R_C <= R_B + delta_R`, compare against the control's safest point. The region counts as materially outside only if:

```text
R_control - R_B >= 0.005
U_B - U_control >= -0.005
bootstrap 95% CI lower bound(U_B - U_control) > -0.005
```

For a killer control, `comparable / ≈` means the evidence does not establish BudgetSet's practical frontier advantage and the control is within the practical margin or better. Operationally, if the relevant utility-gap 95% CI upper bound is `<= 0.005`, the control is comparable. If the interval straddles the practical boundary without proving either material superiority or comparability, the comparison is inconclusive.

The two required separated primary regions are exactly `b_L` and `b_M`, and they count only if BudgetSet is target-compliant and the responsiveness rule separates achieved risk by at least `0.005`.

Aggregate learned-family frontiers use the Section 10.2 seed-mean operating points. The Independent aggregate control frontier is therefore constructed from its three seed-mean operating points at `b_L,b_M,b_H`.

## 12. Bootstrap and seed robustness

### 12.1 Patient-clustered bootstrap

Use exactly:

```text
1000 patient-clustered bootstrap resamples
seed = 80081
95% CI = empirical 2.5th and 97.5th percentiles
```

For each bootstrap replicate:

1. sample patients with replacement from Gate01-Audit;
2. include all visits belonging to each sampled patient;
3. preserve multiplicity when a patient is sampled more than once;
4. recompute visit-level aggregate metrics from the fixed predictions;
5. recompute every sampled operating point;
6. for learned families, first compute each seed's operating point and then apply the frozen arithmetic mean across seeds;
7. recompute the control frontier `F_C(R_B)` inside that replicate;
8. recompute `G_C` or the safer-than-entire-frontier utility difference inside that replicate.

Do not bootstrap an already-computed scalar gap. Do not refit models inside bootstrap replicates. The deterministic Greedy and Fixed-lambda families remain one deterministic prediction set each.

For BudgetSet-vs-Independent aggregate comparisons, each replicate forms the Independent family control frontier from the replicate's three seed-mean Independent operating points before computing the BudgetSet gap.

### 12.2 Favorable-seed rule

Frozen learned seeds are:

```text
{2002, 2003, 2004}
```

For every BudgetSet seed `r`, required primary budget region, and killer control `C`, let the sampled control operating points be indexed by `j` and define

$$
E_{r,C}=\{j:R_{C,j}\le R_{B,r}+\delta_R\}.
$$

The seed-level comparator is total whenever the required control family contains at least one sampled operating point.

**Branch A — non-empty eligible frontier.** If $E_{r,C}\ne\varnothing$, define

$$
F_{r,C}=\max_{j\in E_{r,C}}U_{C,j},
$$

$$
G_{r,C}=U_{B,r}-F_{r,C}.
$$

Seed `r` is favorable iff

```text
G_{r,C} > 0
```

This is the existing ordinary-frontier rule.

**Branch B — empty eligible frontier.** If $E_{r,C}=\varnothing$, every sampled control point satisfies $R_{C,j}>R_{B,r}+\delta_R$. Select one unique control reference endpoint

$$
j^\star=\operatorname*{arg\,min}_j\left(R_{C,j},-U_{C,j},o_j\right)
$$

under lexicographic ordering:

1. lower hard-set DDI $R_{C,j}$;
2. then higher Jaccard $U_{C,j}$;
3. then lower canonical control-point order $o_j$.

Canonical control-point order follows the already-frozen requested-budget order

```text
b_L < b_M < b_H
```

and any other sampled point already defined by a control family retains that family's existing deterministic protocol order. No performance-dependent ordering is introduced.

Define

$$
H_{r,C}=U_{B,r}-U_{C,j^\star}.
$$

In this empty-frontier branch only, seed `r` is favorable iff

$$
H_{r,C}\ge 0.
$$

Thus `H_{r,C}>0` is favorable, `H_{r,C}<0` is non-favorable, and `H_{r,C}=0` is favorable because this branch already guarantees the strict lower-risk direction $R_{B,r}+\delta_R<R_{C,j^\star}$. This is a zero-margin, direction-only seed-robustness test. Do not apply an additional `0.005` utility threshold, bootstrap interval, composite scalar, or hypervolume criterion at seed level; material sufficiency remains solely the aggregate Section 11 frontier test.

For deterministic Greedy, each BudgetSet seed is compared against the same single deterministic Greedy family. Use Branch A when its eligible set is non-empty and Branch B otherwise. Do not manufacture Greedy seeds.

For Independent, use matched seeds only:

```text
BudgetSet 2002 <-> Independent 2002
BudgetSet 2003 <-> Independent 2003
BudgetSet 2004 <-> Independent 2004
```

For BudgetSet seed `r`, the control points used in either branch are only the sampled operating points of matched Independent seed `r`; do not mix Independent seeds in the seed-robustness comparator. Aggregate Independent frontier and bootstrap semantics remain those of Sections 11 and 12.1.

At each required `killer × primary-region` comparison, at least `2/3` BudgetSet seeds must be favorable under this two-branch rule. Otherwise trigger `KILL_SEED_FRAGILITY`. The `0.005` material-win threshold remains an aggregate frontier criterion and is not reused as a favorable-seed threshold.

If a required killer control family contains zero sampled operating points, the Gate implementation is invalid and Section 13.1 applies; the case is not assigned a seed-favorable status.

## 13. Formal terminal decision precedence

Evaluate the following conditions in this exact top-to-bottom order. The first triggered condition is the primary verdict. Any later condition that is also true is recorded only as a secondary reason and never changes the primary verdict.

1. `STOP_INVALID_GATE_IMPLEMENTATION`
2. `STOP_NO_BASE_DDI_HEADROOM`
3. `KILL_TARGET_SEMANTICS`
4. `KILL_BUDGET_RESPONSE`
5. `KILL_COMPOSITION_RESPONSE`
6. `KILL_BUDGETSET`
7. `KILL_JOINT_SET_INTERACTION`
8. `KILL_SEED_FRAGILITY`
9. `INCONCLUSIVE_STOP`
10. `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES`

### 13.1 STOP_INVALID_GATE_IMPLEMENTATION

Trigger if any compared method fails exact `K_x` compliance, any method receives a different candidate pool, DDI matrix, frozen logits, requested target, or frozen cardinality, or any required killer control family has zero sampled operating points. No scientific conclusion follows.

### 13.2 STOP_NO_BASE_DDI_HEADROOM

Trigger if `r_train = 0`.

### 13.3 KILL_TARGET_SEMANTICS

Trigger if BudgetSet fails the Section 10.2 target-compliance rule at any of the three requested targets.

### 13.4 KILL_BUDGET_RESPONSE

Trigger if either responsiveness inequality in Section 10.3 fails.

### 13.5 KILL_COMPOSITION_RESPONSE

Trigger if either adjacent composition-change rate in Section 10.4 is below `10%`.

### 13.6 KILL_BUDGETSET

BudgetSet must be materially outside the Greedy+1Swap frontier at both `b_L` and `b_M`. Trigger if Greedy is comparable/better at either primary region or BudgetSet establishes a material aggregate win at only one primary region.

### 13.7 KILL_JOINT_SET_INTERACTION

BudgetSet must be materially outside the Independent frontier at both `b_L` and `b_M`. Trigger if Independent is comparable/better at either primary region or BudgetSet establishes a material aggregate win at only one primary region.

### 13.8 KILL_SEED_FRAGILITY

Trigger if any required `killer × primary-region` comparison has fewer than `2/3` favorable BudgetSet seeds under Section 12.2.

### 13.9 INCONCLUSIVE_STOP

Use only when all prior explicit stop/kill conditions are false, PASS requirements are not fully satisfied, and the frozen protocol provides no authorized further discriminator. It cannot override an already-triggered stop or killer. Do not increase seeds, change thresholds, add budgets, alter `T`, expand model capacity, add losses, or switch backbones.

### 13.10 PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES

Return PASS only if all hold:

1. every compared hard output has exact `|S_b|=K_x`;
2. BudgetSet is target-compliant at all three budgets;
3. `R_L+0.005<=R_M` and `R_M+0.005<=R_H`;
4. both adjacent composition transitions change hard set on at least `10%` of eligible visits;
5. BudgetSet is materially outside the Greedy+1Swap frontier at `b_L`;
6. BudgetSet is materially outside the Greedy+1Swap frontier at `b_M`;
7. BudgetSet is materially outside the Independent frontier at `b_L`;
8. BudgetSet is materially outside the Independent frontier at `b_M`;
9. all four required killer-region comparisons satisfy the `>=2/3` favorable-seed rule.

A pass means only that the admitted mechanism survives its cheapest equal-information falsification gate.

## 14. Reporting schema

The Gate report must contain real values only:

| Method | Budget / lambda | Seed | Jaccard | F1 | PRAUC | Hard-set DDI | Mean violation | Abs deviation | Mean meds | Exact-K rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen Base | fixed | deterministic | TBD | TBD | TBD | TBD | n/a | n/a | TBD | TBD |
| Greedy+1Swap | `b_L,b_M,b_H` | deterministic | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Independent Conditional | `b_L,b_M,b_H` | `2002..2004` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Fixed-lambda | selected `lambda_b` | deterministic | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| BudgetSet | `b_L,b_M,b_H` | `2002..2004` | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Also report:

- `r_train`, `b_L`, `b_M`, `b_H`;
- selected Fixed-lambda values;
- per-seed and family-level target/compliance quantities;
- BudgetSet adjacent achieved-DDI gaps;
- per-seed and family-level adjacent set-change rates;
- aggregate frontier gaps and 95% patient-clustered bootstrap intervals for both killers at both primary regions;
- seed-specific favorable-sign table for all four required killer-region comparisons;
- selected learned configuration plus each retained seed checkpoint epoch from Dev only;
- quarantine confirmation.

## 15. Authorization boundary and routing

Gate 01 does not authorize:

- another backbone;
- another candidate pool;
- another solver family;
- denser budget sweep;
- `T` search;
- a new encoder, Transformer, Mamba, MoE, RL, LLM, retrieval, ingredient, or molecular branch;
- additional losses or regularizers;
- subgroup mining;
- G3/G4, R0 Holdout, or historical test access;
- paper-level SOTA benchmarking.

Protocol v1.2 is corrected but not yet integrity-approved. Implementation remains `NOT_STARTED`; training and execution remain `NOT_AUTHORIZED`; Gate01-Audit remains unopened. The next owner is `ccf-integrity-auditor` for independent pre-execution re-audit. Only a future integrity pass may return routing to `ccf-pipeline-orchestrator` for an execution-authorization decision.
