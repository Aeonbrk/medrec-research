<!-- markdownlint-disable MD001 MD013 MD036 -->

# Gate 02 — Confidence Sufficiency and Residual Constraint Signal

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

This is not a publication experiment and does not establish a deployable policy.

The purpose is to run the cheapest experiment that can falsify the need for a Tension-specific mechanism before any Tension model is implemented.

---

# 1. Scientific state entering Gate 02

Gate 01 has established one narrow result:

> Under the frozen MoleRec backbone, the frozen DDI-active candidate universe, and the fixed singleton deletion operator $R_0$, candidate-level marginal revision outcomes are heterogeneous enough that selective allocation can matter.

Gate 01 does **not** establish:

* that Tension predicts revision value;
* that DDI pressure contains information beyond the recommender's own confidence;
* that context conditioning is necessary;
* that a learned selector is necessary;
* that any clinical safety or patient-benefit claim holds.

For every Gate 01 eligible candidate,

$$
m\in\hat M_t
$$

and

$$
d_t(m)>0,
$$

therefore

$$
\Delta V_{t,m}<0.
$$

Under singleton deletion,

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

For Jaccard, this implies:

$$
\Delta J_{t,m}\geq0
\iff
m\notin M_t.
$$

Therefore the Gate 01 label simplifies exactly to:

$$
\boxed{
Y^{PB}_{t,m}
=
\mathbf 1[m\notin M_t]
}
$$

within the DDI-active predicted-medication candidate universe.

So Gate 02 is fundamentally asking:

$$
\boxed{
\text{Can target-free observable signals identify false-positive medications among DDI-active predictions?}
}
$$

This formulation supersedes any vague interpretation of “revision value” for this fixed $R_0$ experiment.

---

# 2. Historical-failure adjudication

Historical failure records are evidence, not axioms.

## 2.1 EGSF selector failure

Retain:

> Test the strongest simple explanation before attributing gains to context conditioning.

Do not mechanically inherit:

* the historical global DDI-lambda action family;
* exact prescription-count controls designed for full prescription reranking;
* the old candidate frontier;
* the old selector mechanism.

Why:

Gate 02 has a materially different target:

$$
Y^{PB}=\mathbf1[m\notin M_t],
$$

a materially different evidence source:

$$
s_t(m)=\text{frozen MoleRec medication probability},
$$

and a fixed singleton action whose medication-count change is already matched candidate-by-candidate.

The appropriate modern analogue of the EGSF strong control is therefore:

1. `ScoreOnly`;
2. a broad but simple global `Score + DDI-degree` scalar control.

If these explain the signal, do not build a richer Tension model.

## 2.2 EG-TER hard-filter failure

Retain fully:

> All non-oracle policies must receive exactly the same candidate eligibility and feasibility rules.

Therefore Random, RiskOnly, ScoreOnly, Scalar, and Oracle operate on exactly the same Gate 02 candidate universe.

No policy-specific contraindication/filter/coverage rule may be introduced.

## 2.3 CRC-PS failure

Retain:

> A failed preregistered gate is a route boundary.

Do not inherit conformal machinery because Gate 02 is not a certification experiment.

If Gate 02 rejects the Tension premise, do not rescue it by changing:

* budgets;
* candidate definition;
* score bins;
* scalar grid;
* label;
* support threshold;
* interaction definition

after inspecting the audit result.

Such a change would constitute a new preregistered route.

---

# 3. Integrity Gate 01 — mandatory upstream closure

Before formal 319 execution of Gate 02 or interpretation of any Gate 02 results, hand Gate 01 to:

`ccf-integrity-auditor`

Mode:

`full`, with emphasis on `claim-audit + numeric-audit`.

Gate 02 repository implementation and synthetic verification may be prepared in advance because software checks produce no Gate 02 scientific evidence. However, formal execution and evaluation remain strictly blocked until Gate 01 achieves `AUDIT_PASS`.

This audit must operate where the restricted Gate 01 artifact is authorized to remain.

Do not copy:

`candidate-revision-values.jsonl`

into Git or another unauthorized environment.

## Required Gate 01 audit inputs

1. `gate-01-routing-opportunity.md`
2. frozen Gate 01 runner revision
3. restricted 319:
   `candidate-revision-values.jsonl`
4. public:
   `gate-summary.json`
5. `Handoff.md`

## Auditor must independently verify

From the restricted candidate rows:

* eligible candidate count;
* eligible visit count;
* eligible patient count;
* beneficial-patient support;
* non-beneficial-patient support;
* overall $Y^{PB}$ prevalence;
* Random expectation;
* RiskOnly ordering and yields;
* Oracle ordering and yields;
* all reported gaps;
* 1,000-replicate patient-cluster bootstrap with seed 1203;
* final Gate 01 verdict.

Logical invariants:

$$
\Delta V=-d_t(m)<0
$$

for every eligible candidate, and

$$
Y^{PB}
=
\mathbf1[
\Delta J\geq0
\land
\Delta V<0
].
$$

The auditor must also classify the following claim:

> “Gate 01 confirms the Tension hypothesis.”

as `overstated / unsupported`.

The supported statement is:

> “Gate 01 confirms routing headroom under the frozen $R_0$ setting.”

## Integrity Gate 01 outcome

Only:

`AUDIT_PASS`

permits Gate 02 formal execution.

Any numeric mismatch affecting the verdict:

`AUDIT_BLOCK`

and Gate 02 formal execution must stop.

Minor wording-only overclaim does not invalidate Gate 01 numerics, but must be corrected before Gate 02 results are interpreted.

---

# 4. Venue and evidence assumptions

Evidence standard:

CCF-A-style AI/ML hypothesis-selection discipline.

Exact publication venue is not yet frozen.

Therefore Gate 02 optimizes for:

* strong simple controls;
* fair candidate surfaces;
* patient-level uncertainty;
* mechanism falsification;
* reproducibility;
* explicit negative stopping rules.

It does not optimize publication layout or create manuscript claims.

---

# 5. Frozen scientific setting

Reuse the exact Gate 01 scientific identities.

Backbone:

* MoleRec
* source revision:
  `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
* checkpoint SHA256:
  `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
* profile:
  `molerec-embedding`
* threshold:
  `0.5`

Dataset:

* `molerec-table1-comparison-v1-1`
* snapshot:
  `molerec-table1-c721-www23`
* Dataset Manifest:
  `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712`
* DDI asset:
  `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7`
* feature availability:
  `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9`
* medication vocabulary:
  131 medications

Environment:

`medrec-molerec-table1`

with frozen Conda explicit SHA256:

`6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda`

Split:

**validation only**

Test patients, visits, features, targets, scores, or metrics must not participate in Gate 02.

---

# 6. Candidate universe

Use exactly the Gate 01 eligibility rule:

$$
\mathcal Q_t
=
\{
m\in\hat M_t:
d_t(m)>0
\}.
$$

No policy may alter $\mathcal Q$.

For every candidate retain:

* MoleRec probability $s_t(m)$ from existing schema-v2 `vocabulary_scores`;
* active DDI degree $d_t(m)$;
* Gate 01 label $Y^{PB}$;
* deterministic patient/visit traversal indices.

No new model inference target is introduced.

---

# 7. Development / audit separation

Unlike Gate 01, Gate 02 contains one tunable simple scalar baseline.

Therefore target-based scalar selection and final evaluation must be separated.

Take validation patients only and perform one deterministic patient-level split:

* `Gate02-Dev`: 50%
* `Gate02-Audit`: 50%

Procedure:

1. start from the complete validation patient universe $\text{patient\_order} \in \{0, \dots, N_{\text{val\_patients}} - 1\}$ as defined by `validation_patient_count` in the staged metadata (ensuring patients without eligible follow-up visits are included in the permutation so that seeded shuffling does not shift subsequent patient assignments);
2. shuffle patient indices with PRNG seed `1203`;
3. assign the first half to Dev and the remainder to Audit;
4. all visits/candidates from one patient remain in exactly one partition.

The split itself is frozen before inspecting Gate 02 outcomes.

Both Dev and Audit should separately report:

* beneficial patients;
* non-beneficial patients;
* eligible candidates.

Reuse Gate 01's support rule:

if either outcome is represented by fewer than 50 patients in the Audit partition:

`INSUFFICIENT_SUPPORT`.

Do not move patients between partitions to repair support.

---

# 8. Baseline matrix

## 8.1 Random

Uniform review among eligible Audit candidates.

Expected yield:

$$
P(Y^{PB}=1).
$$

No repeated Monte Carlo simulation is required for the point estimate.

---

## 8.2 RiskOnly

Reuse Gate 01:

$$
R_{\text{risk}}(t,m)=d_t(m).
$$

Rank descending.

Tie-break:

1. medication code ascending;
2. patient traversal;
3. visit traversal.

Purpose:

preserve Gate 01's constraint-pressure-only baseline.

---

## 8.3 ScoreOnly — primary strongest simple control

For each eligible predicted medication, use its frozen MoleRec probability:

$$
s_t(m).
$$

Low-confidence predicted medications receive higher review priority:

$$
R_{\text{score}}(t,m)=1-s_t(m).
$$

Equivalent monotone forms such as:

$$
-s_t(m)
$$

or

$$
0.5-s_t(m)
$$

must **not** be reported as separate baselines.

They produce the same ordering.

Rank:

$$
s_t(m)\uparrow.
$$

Tie-break using the same deterministic ordering as every other non-oracle policy.

This is Gate 02's central falsification control.

---

# 9. Strong global scalar control

To prevent repeating the EGSF weak-control mistake, include one simple two-signal global scalar before any Tension model.

On the Dev partition, freeze the maximum DDI degree:

$$
D_{\max}^{\text{Dev}}
=
\max_{(t',m')\in \mathcal Q_{\text{Dev}}} d_{t'}(m').
$$

Define the normalized constraint degree on Dev:

$$
q_t^{\text{Dev}}(m)
=
\frac{d_t(m)}{D_{\max}^{\text{Dev}}}.
$$

Thus on Dev:

$$
q_t^{\text{Dev}}(m)\in(0,1].
$$

On the Audit partition, evaluation must continue to use the frozen Dev denominator $D_{\max}^{\text{Dev}}$:

$$
q_t^{\text{Audit}}(m)
=
\frac{d_t(m)}{D_{\max}^{\text{Dev}}}.
$$

Do not renormalize using Audit maximum degree. If an Audit candidate's degree exceeds $D_{\max}^{\text{Dev}}$, $q_t^{\text{Audit}}(m) > 1$ is permitted.

Define:

$$
R_\lambda(t,m)
=
(1-s_t(m))
+
\lambda q_t(m).
$$

Higher value receives earlier review.

Predeclare:

$$
\Lambda=
\{
-8,-4,-2,-1,-0.5,-0.25,
0,
0.25,0.5,1,2,4,8
\}.
$$

Important:

$$
\lambda=0
$$

is exactly ScoreOnly.

Negative values are deliberately allowed.

They test whether constraint pressure provides information in the **opposite** direction from the original Tension story.

## Lambda selection

Use only Gate02-Dev labels.

For every $\lambda$ compute:

$$
PBYield_\lambda(10\%)
$$

and

$$
PBYield_\lambda(20\%).
$$

Selection score:

$$
S_{\lambda}
=
\frac{
PBYield_\lambda(10\%)
+
PBYield_\lambda(20\%)
}{2}.
$$

Choose the $\lambda$ with highest $S_\lambda$.

Tie-breaking:

1. smaller $|\lambda|$;
2. prefer $\lambda=0$ if still tied;
3. otherwise numerical ascending order.

After selection, freeze $\lambda^*$.

Audit labels may never influence:

* $\lambda^*$;
* the lambda grid;
* normalization;
* tie-breaking.

Then evaluate the frozen $\lambda^*$ exactly once on Gate02-Audit.

---

# 10. Oracle

Analysis-only upper bound.

Use the same Gate 01 ordering:

1. $Y^{PB}$ descending;
2. $\Delta J$ descending;
3. $-\Delta V$ descending;
4. medication code;
5. deterministic traversal order.

Oracle is not a predictor and must not be described as one.

---

# 11. Budgets

Use:

$$
B\in\{10\%,20\%,30\%\}.
$$

For Audit candidate count $N_A$:

$$
k(B)
=
\lfloor B N_A\rfloor.
$$

The primary decision budgets are:

$$
10\%,20\%.
$$

The 30% budget is secondary consistency evidence.

---

# 12. Primary evidence

For every policy $\pi$:

$$
PBYield_\pi(B)
=
\frac{
\sum_{(t,m)\in Q_\pi(B)}
Y^{PB}_{t,m}
}{
|Q_\pi(B)|
}.
$$

Report:

### ScoreOnly against simple controls

$$
Gap_{Score-Random}(B)
=
PBYield_{Score}(B)
-
PBYield_{Random}(B)
$$

$$
Gap_{Score-Risk}(B)
=
PBYield_{Score}(B)
-
PBYield_{Risk}(B).
$$

### Residual headroom

$$
Gap_{Oracle-Score}(B)
=
PBYield_{Oracle}(B)
-
PBYield_{Score}(B).
$$

### Incremental DDI scalar value

$$
Gap_{Scalar-Score}(B)
=
PBYield_{\lambda^\*}(B)
-
PBYield_{Score}(B).
$$

And:

$$
Gap_{Oracle-Scalar}(B)
=
PBYield_{Oracle}(B)
-
PBYield_{\lambda^\*}(B).
$$

---

# 13. Headroom-capture diagnostic

For policy $\pi$:

$$
HC_\pi(B)
=
\frac{
PBYield_\pi(B)-PBYield_{Random}(B)
}{
PBYield_{Oracle}(B)-PBYield_{Random}(B)
}.
$$

Report for:

* ScoreOnly;
* frozen Scalar.

This is a diagnostic fraction of available Oracle headroom captured.

Do **not** invent a post-hoc “good enough” threshold from the observed values.

The formal gate uses confidence intervals below.

---

# 14. Tension-interaction diagnostic

A simple additive scalar can miss a genuine support-pressure interaction.

Therefore include exactly one preregistered interaction diagnostic, without training a Tension model.

Using **Dev only**, freeze the median MoleRec score among eligible Dev candidates:

$$
\tau_s
=
Median_{\mathcal Q_{Dev}}(s_t(m)).
$$

On Audit define:

Support:

$$
LowSupport:
s_t(m)<\tau_s
$$

$$
HighSupport:
s_t(m)\geq\tau_s.
$$

Pressure:

$$
LowPressure:
d_t(m)=1
$$

$$
HighPressure:
d_t(m)\geq2.
$$

Compute the four Audit prevalences:

$$
p_{LL}, p_{LH}, p_{HL}, p_{HH}.
$$

Define the difference-in-differences interaction:

$$
I_{Tension}
=
(p_{HH}-p_{HL})
-
(p_{LH}-p_{LL}).
$$

Interpretation:

$$
I_{Tension}>0
$$

means increasing DDI pressure is more associated with false-positive status among high-support predictions than among low-support predictions.

This is the narrow interaction pattern required by the original Tension story.

It does not establish a usable Tension policy.

Each of the four cells must contain candidates from at least 50 distinct patients to support a directional interaction conclusion.

Otherwise mark:

`INTERACTION_INSUFFICIENT_SUPPORT`.

---

# 15. Uncertainty

Use patient-clustered bootstrap.

Frozen configuration:

* resamples: 1,000
* seed: 1203
* resampling unit: Audit patient

Do not reselect $\lambda^*$ inside Audit bootstrap replicates.

$\lambda^*$ is already frozen from Dev.

Report 95% intervals for:

* ScoreOnly yield;
* Scalar yield;
* ScoreOnly - Random;
* ScoreOnly - RiskOnly;
* Oracle - ScoreOnly;
* Scalar - ScoreOnly;
* Oracle - Scalar;
* $I_{Tension}$.

---

# 16. Formal decision tree

## Gate 02-A — Is model confidence already sufficient?

Require support first.

At both primary budgets:

$$
B=10\%,20\%.
$$

If the 95% interval for:

$$
Gap_{Oracle-Score}(B)
$$

does **not** lie strictly above zero at both budgets:

Verdict:

`STOP_SCORE_SUFFICIENT`

Interpretation:

> No reliable residual allocation headroom beyond the frozen recommender score has been established.

Do not build Tension.

---

If:

$$
LowerCI[
Gap_{Oracle-Score}(10\%)
]>0
$$

and

$$
LowerCI[
Gap_{Oracle-Score}(20\%)
]>0,
$$

then residual headroom survives ScoreOnly.

Proceed to Gate 02-B.

---

# 17. Gate 02-B — Does DDI pressure add information beyond confidence?

Evaluate frozen $\lambda^*$.

### Case B1 — positive-direction simple scalar succeeds

If:

$$
\lambda^\*>0
$$

and at both 10% and 20%:

$$
LowerCI[
Gap_{Scalar-Score}(B)
]>0,
$$

Verdict:

`PASS_POSITIVE_INCREMENTAL_CONSTRAINT_SIGNAL`

Interpretation:

> Constraint pressure contains reproducible target-free allocation information beyond MoleRec confidence in the direction compatible with the Tension premise.

This permits a later Tension-specific mechanism gate.

It does **not** yet justify a learned Tension model.

---

### Case B2 — opposite-direction signal succeeds

If:

$$
\lambda^\*<0
$$

and Scalar significantly beats ScoreOnly at both primary budgets:

Verdict:

`PIVOT_OPPOSITE_PRESSURE_SIGNAL`

Interpretation:

> DDI degree carries incremental information, but in a direction inconsistent with the proposed high-pressure Tension mechanism.

Do not proceed with the original Tension formulation.

The result demands problem reformulation.

---

### Case B3 — scalar does not improve ScoreOnly

If Scalar does not significantly beat ScoreOnly at both primary budgets, inspect only the preregistered interaction diagnostic.

If:

* all four interaction cells pass support; and
* the 95% CI for $I_{Tension}$ lies strictly above zero,

Verdict:

`PASS_INTERACTION_ONLY_SIGNAL`

Interpretation:

> No useful global additive degree effect was established, but a preregistered support-pressure interaction survives.

This permits one later Gate 03 that tests a Tension interaction against ScoreOnly and the frozen scalar control.

Do not yet train a full complex selector.

---

If neither the scalar improvement nor supported interaction survives:

Verdict:

`STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`

Interpretation:

> Gate 01 routing headroom exists, but current evidence does not show that DDI pressure explains residual false-positive ranking information beyond MoleRec confidence.

Do not build Tension from this route.

---

# 18. What Gate 02 must never claim

Even after a positive result, do not claim:

* clinical safety;
* safe medication deletion;
* treatment correctness;
* clinician intent;
* causal evidence;
* therapeutic necessity;
* deployable verification policy;
* Tension method superiority.

A positive Gate 02 supports only a narrow statement about target-free prediction of retrospective candidate labels.

---

# 19. Result table schema

All unknown values remain `TBD` until formal execution.

| Policy                        | 10% PBYield | 20% PBYield | 30% PBYield | 95% CI available | Role                           |
| ----------------------------- | ----------: | ----------: | ----------: | ---------------- | ------------------------------ |
| Random                        |         TBD |         TBD |         TBD | yes              | prevalence baseline            |
| RiskOnly                      |         TBD |         TBD |         TBD | yes              | constraint-only                |
| ScoreOnly                     |         TBD |         TBD |         TBD | yes              | strongest confidence control   |
| Score+Risk Scalar $\lambda^*$ |         TBD |         TBD |         TBD | yes              | strongest simple joint control |
| Oracle                        |         TBD |         TBD |         TBD | yes              | analysis upper bound           |

Second table:

| Quantity                | 10% | 20% | 30% |
| ----------------------- | --: | --: | --: |
| Score - Random          | TBD | TBD | TBD |
| Score - RiskOnly        | TBD | TBD | TBD |
| Oracle - Score          | TBD | TBD | TBD |
| Scalar - Score          | TBD | TBD | TBD |
| Oracle - Scalar         | TBD | TBD | TBD |
| Score Headroom Capture  | TBD | TBD | TBD |
| Scalar Headroom Capture | TBD | TBD | TBD |

Interaction table:

| Support | Pressure | Audit candidates | Distinct patients | $P(Y^{PB}=1)$ |
| ------- | -------- | ---------------: | ----------------: | ------------: |
| Low     | Low      |              TBD |               TBD |           TBD |
| Low     | High     |              TBD |               TBD |           TBD |
| High    | Low      |              TBD |               TBD |           TBD |
| High    | High     |              TBD |               TBD |           TBD |

And:

$$
I_{Tension}=TBD,
$$

with 95% CI `TBD`.

---

# 20. Restricted artifact contract

Keep on 319 only:

`gate-02-candidates.jsonl`

Minimum fields:

```text
patient_id
visit_id
patient_order
visit_order
gate02_partition
medication_code
model_score
active_ddi_degree
pareto_beneficial
delta_jaccard
delta_violation
```

Also restricted:

`gate-02-dev-selection.json`

containing:

```text
lambda_grid
dev_candidate_count
dev_patient_count
degree_normalization_max
support_score_median
per_lambda_dev_yield_10
per_lambda_dev_yield_20
per_lambda_selection_score
selected_lambda
tie_break_rule
```

No Audit outcome may appear in this selection artifact.

---

# 21. Public-safe artifact

Return locally only:

`gate-02-summary.json`

It may contain:

* frozen public identities;
* Dev/Audit aggregate counts (including `dev_candidates`, `dev_patients`, `dev_beneficial_patients`, `dev_non_beneficial_patients`);
* support counts;
* selected $\lambda^*$;
* policy yields;
* gaps;
* headroom capture;
* bootstrap intervals;
* interaction aggregate;
* decision criteria;
* final verdict.

It must not contain:

* patient IDs;
* visit IDs;
* candidate rows;
* raw prediction vectors;
* restricted filesystem paths.

---

# 22. Integrity Gate 02 — mandatory post-execution gate

After formal Gate 02 execution, stop immediately.

Invoke:

`ccf-integrity-auditor`

before any Tension design or Gate 03.

Mode:

`full`

with primary emphasis on:

* claim-audit;
* numeric-audit;
* result-to-claim consistency.

## Required artifacts

1. Gate 02 preregistration
2. exact frozen runner revision
3. restricted `gate-02-candidates.jsonl`
4. restricted `gate-02-dev-selection.json`
5. public `gate-02-summary.json`
6. Gate 01 audited summary
7. Handoff / result interpretation text

## Auditor must verify

### Identity

All frozen baseline, dataset, checkpoint, environment, adapter, DDI and vocabulary identities match the preregistration.

### Split integrity

* no test data;
* patients are disjoint across Gate02-Dev and Gate02-Audit;
* seed and split rule reproduce exactly.

### Selection integrity

Recompute every Dev $\lambda$ result.

Verify that $\lambda^*$ is exactly the preregistered optimum.

Verify:

* no Audit labels participated in lambda selection;
* no grid changes occurred after execution;
* normalization came only from Dev.

### Numeric integrity

Independently recompute from restricted Audit rows:

* Random;
* RiskOnly;
* ScoreOnly;
* frozen Scalar;
* Oracle;
* all PBYields;
* all gaps;
* HeadroomCapture;
* interaction cells;
* $I_{Tension}$;
* patient-cluster bootstrap;
* final verdict.

### Claim integrity

Classify every downstream statement as:

* supported;
* partially supported;
* unsupported;
* overstated;
* unclear.

In particular reject any automatic transition:

`Gate 02 pass → Tension method works`.

A Gate 02 positive result only authorizes a **new Tension-specific hypothesis test**.

---

# 23. Integrity Gate 02 decision

Only:

`INTEGRITY_PASS`

allows the research pipeline to advance.

If numerical recomputation changes the Gate verdict:

`INTEGRITY_BLOCK`.

If numbers are correct but wording is overstated:

`INTEGRITY_PASS_WITH_CLAIM_CORRECTION`

and wording must be corrected before the next research stage.

---

# 24. Minimal smoke scope

Do not repeat Gate 01's broad synthetic suite.

Test only new executable critical paths:

1. extraction of the candidate medication's frozen `vocabulary_score`;
2. deterministic patient Dev/Audit split;
3. ScoreOnly ordering;
4. lambda selection using Dev only;
5. proof that changing Audit labels cannot alter $\lambda^*$;
6. restricted-artifact independent recomputation;
7. interaction-cell calculation.

Smoke tests are software checks only.

They are not scientific evidence.

---

# 25. Execution priority

### P0 — Gate 01 Integrity Closure

Run `ccf-integrity-auditor`.

If blocked, stop. Must achieve `AUDIT_PASS` before P4.

### P1 — Gate 02 preregistration

Create the protocol and freeze all definitions above.

### P2 — Minimal implementation

Reuse the current process adapter and schema-v2 `vocabulary_scores`. Implementation and synthetic tests may be prepared in advance of P0 without constituting experimental execution.

Do not add a second adapter architecture.

Do not train Tension.

### P3 — Static / synthetic verification

Only the changed-path checks above.

### P4 — Formal 319 Gate 02 execution

Requires P0 `AUDIT_PASS`.

Validation only.

Generate restricted + public artifacts.

Stop immediately afterward.

### P5 — Gate 02 Integrity Audit

Run `ccf-integrity-auditor`.

### P6 — Research decision

Hand the audited verdict to:

`ccf-pipeline-orchestrator`

Possible next states:

```text
STOP_SCORE_SUFFICIENT
STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL
PIVOT_OPPOSITE_PRESSURE_SIGNAL
PASS_INTERACTION_ONLY_SIGNAL
PASS_POSITIVE_INCREMENTAL_CONSTRAINT_SIGNAL
INSUFFICIENT_SUPPORT
INTEGRITY_BLOCK
```

Only the two positive-signal states permit a Gate 03 Tension-specific experiment.

None of them automatically permits a full publication model.

---

# 26. Missing values

All Gate 02 empirical quantities are currently:

`TBD`.

No Gate 02 result has been generated.

Do not infer likely outcomes from Gate 01.

---

# 27. No-fabrication status

No experimental value in this design is fabricated.

Gate 01 values are prior supplied evidence.

Every Gate 02 outcome must come from the formal frozen execution and pass independent Integrity Audit.

---

# 28. Next CCFA owner

Immediate:

`ccf-integrity-auditor` for Gate 01 closure (P0).

After `AUDIT_PASS`:

formal 319 execution of Gate 02 (P4).

After Gate 02 execution:

`ccf-integrity-auditor`.

After `INTEGRITY_PASS`:

`ccf-pipeline-orchestrator`.

Do not invoke `ccf-paper-writer`, `ccf-visual-composer`, or Tension model implementation at this stage.
