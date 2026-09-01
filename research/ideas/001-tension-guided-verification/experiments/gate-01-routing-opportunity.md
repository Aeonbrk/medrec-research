# Gate 01 — Routing Opportunity Under a Fixed Revision Operator

* **Idea**: `001-tension-guided-verification`
* **Stage**: Idea / Hypothesis Selection
* **Status**: Preregistered before execution
* **Purpose**: Determine whether selective verification is worth studying before designing a Tension trigger.
* **Scope**: Retrospective validation-set medication prediction and constraint auditing only. This gate does not establish prospective prescribing semantics or clinical safety.

## Decision question

Under a frozen medication recommender and a fixed revision operator, do eligible medication decisions exhibit sufficiently heterogeneous marginal revision value that selective routing can outperform budget-blind review?

The gate tests:

$$
\boxed{
\text{Does a routing opportunity exist before asking whether Tension can predict it?}
}
$$

The experiment must not use Tension, uncertainty, evidence selection, a learned trigger, or a new recommender.

## Frozen setting

Use the current Unified Research Protocol v1.1 lineage.

Primary pilot backbone:

* MoleRec
* source revision: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
* profile: `molerec-embedding`
* use the exact frozen checkpoint/configuration belonging to the current Comparison-qualified method
* no retraining
* no checkpoint selection
* no threshold tuning

Dataset semantics:

* same `molerec-table1-c721-www23` dataset snapshot
* same patient-disjoint split construction
* **validation split only**
* 131-medication vocabulary
* same DDI asset as the current v1.1 Comparison Scope
* current diagnoses/procedures/history feature semantics remain unchanged

The test split must never be indexed, inspected, scored, evaluated, or used for selection or configuration during Gate 01. Because the source snapshot is a single combined archive, deserializing the dataset snapshot does not constitute test evaluation, provided that test patients, visits, features, and targets are never accessed or processed. Validation staging logic must isolate and process only the validation patient split.

This experiment is deliberately retrospective, so unresolved S-1 prospective timestamp semantics do not block it. If the route later makes a prospective recommendation claim, S-1 remains a separate hard validity gate.

## Candidate universe

For validation visit $t$, let the frozen predictor produce:

$$
\hat M_t.
$$

Let $C$ be the frozen DDI relation set, defined as symmetric unordered medication pairs $\{i, j\}$.

For medication $m\in\hat M_t$, define its active predicted-prescription DDI degree:

$$
d_t(m)
=
\sum_{j\in\hat M_t\setminus\{m\}}
\mathbf 1[\{m,j\}\in C].
$$

The eligible review universe is:

$$
\mathcal Q_t
=
\{m\in\hat M_t:d_t(m)>0\}.
$$

Therefore every eligible candidate is:

1. currently predicted present;
2. involved in at least one active DDI relation.

Do not expand the candidate universe using ground-truth medications.

## Fixed revision operator

Use exactly one deterministic revision operator:

$$
R_0(\hat M_t,m)
=
\hat M_t\setminus\{m\}.
$$

It removes the selected medication and changes nothing else.

This operator is intentionally simple. It is not proposed as the final verifier or clinical repair policy.

All reviewed candidates receive exactly the same one-medication deletion, so medication-count change is matched by construction.

## Singleton marginal revision value

Every eligible candidate is evaluated independently against the unchanged original prediction.

Define:

$$
\Delta J_{t,m}
=
Jaccard(R_0(\hat M_t,m),M_t)
-
Jaccard(\hat M_t,M_t).
$$

Define secondary fidelity change:

$$
\Delta F1_{t,m}
=
F1(R_0(\hat M_t,m),M_t)
-
F1(\hat M_t,M_t).
$$

Let:

$$
E_C(M)
=
\{(i,j):i,j\in M,\;\{i,j\}\in C\}.
$$

Define constraint change:

$$
\Delta V_{t,m}
=
|E_C(R_0(\hat M_t,m))|
-
|E_C(\hat M_t)|.
$$

Because only candidates with $d_t(m)>0$ are eligible:

$$
\Delta V_{t,m}<0.
$$

Primary revision outcome:

$$
Y^{PB}_{t,m}
=
\mathbf 1[
\Delta J_{t,m}\geq0
\land
\Delta V_{t,m}<0
].
$$

This means the singleton revision reduces an active DDI relation without reducing visit-level Jaccard.

Also record harmful revisions:

$$
Y^{H}_{t,m}
=
\mathbf 1[\Delta J_{t,m}<0].
$$

## Policies

This gate evaluates only three policies.

### Random

Uniform selection from the eligible candidate universe.

Its expected Pareto-beneficial yield equals the overall prevalence:

$$
P(Y^{PB}=1).
$$

Do not run repeated random policy simulations merely to estimate this expectation.

### RiskOnly

Rank candidates by descending active DDI degree:

$$
d_t(m).
$$

Tie-break deterministically by medication code ascending, followed by original validation traversal order. Tie-breaking must not depend on pseudonymous or randomized identifiers.

This is the strongest simple explanation required before pursuing Tension.

### Oracle

Oracle is an analysis-only upper bound and may use the observed target.

Rank lexicographically by:

1. $Y^{PB}$ descending;
2. $\Delta J$ descending;
3. $-\Delta V$ descending;
4. deterministic medication-code tie break (ascending);
5. deterministic original validation traversal order.

Oracle must never depend on pseudonymous identifiers and must never become a deployable policy or trigger feature.

## Budgets

Evaluate candidate-review budgets:

$$
B\in\{10\%,20\%,30\%\}
$$

of the eligible validation candidate universe.

The integer budget review cutoff is explicitly defined by the floor rule:

$$
k(B) = \lfloor B \times |\mathcal Q| \rfloor.
$$

Because these are maximum review allowances, the floor rule guarantees the budget cap is never exceeded. Support requirements guarantee $k(B) > 0$.

This gate measures selected-candidate yield only.

Do not simultaneously compose multiple singleton deletions into one prescription in Gate 01. That would introduce action coupling and belongs to a later allocation experiment.

For policy $\pi$:

$$
PBYield_\pi(B)
=
\frac{
\sum_{(t,m)\in Q_\pi(B)}Y^{PB}_{t,m}
}{
|Q_\pi(B)|
}.
$$

Report:

$$
Gap_{O-R}(B)
=
PBYield_{Oracle}(B)
-
PBYield_{Random}(B),
$$

and:

$$
Gap_{O-Risk}(B)
=
PBYield_{Oracle}(B)
-
PBYield_{RiskOnly}(B).
$$

## Support requirement

Before interpreting routing results, report:

* eligible candidates;
* eligible visits;
* eligible patients;
* patients containing at least one $Y^{PB}=1$ candidate;
* patients containing at least one non-beneficial candidate.

If either beneficial or non-beneficial outcomes are supported by fewer than 50 distinct patients, mark the gate `INSUFFICIENT_SUPPORT`.

Do not compensate by enlarging the test set or changing the candidate definition.

## Uncertainty

Use patient-level clustered bootstrap with 1,000 resamples.

The bootstrap exists to detect whether apparent routing headroom is driven by a small number of repeatedly represented patients. Patient clusters must be enumerated in deterministic original validation traversal order before drawing resamples with the declared PRNG seed, ensuring invariance to pseudonymization keys.

Report 95% intervals for:

* $PBYield_{RiskOnly}(B)$;
* $Gap_{O-R}(B)$;
* $Gap_{O-Risk}(B)$.

The patient is the resampling unit.

## Gate decision

### PASS — routing opportunity exists

Pass the routing-opportunity gate when:

1. support requirements are satisfied; and
2. at both $B=10\%$ and $B=20\%$, the patient-bootstrap 95% interval for

$$
Gap_{O-R}(B)
$$

lies strictly above zero.

Interpretation:

> Candidate-level marginal revision value is heterogeneous enough that budget allocation can matter.

This permits research on predictors of revision value.

### DOWNGRADE — routing exists but RiskOnly is sufficient

If Oracle clearly exceeds Random but RiskOnly is statistically indistinguishable from Oracle over the primary budgets:

$$
Gap_{O-Risk}(B)\approx0,
$$

do not proceed directly to a Tension method.

Interpretation:

> selective review has value, but simple constraint pressure may already capture the useful allocation structure.

The next research question becomes whether predictive support contributes any incremental information beyond RiskOnly.

### FAIL — no useful routing opportunity under $R_0$

Fail when Oracle does not reliably exceed Random at the primary budgets, or when Pareto-beneficial revisions have effectively no usable support.

Interpretation:

> under this frozen backbone, candidate universe, DDI relation and fixed singleton deletion operator, selective routing has insufficient headroom.

Do not implement Tension, a learned trigger, an evidence selector, or sequential allocation from this result.

This failure is scoped to $R_0$. It does not establish that every possible verifier or revision mechanism lacks heterogeneous value.

## Required outputs

Restricted 319-only artifact:

`candidate-revision-values.jsonl`

Minimum fields:

```text
patient_id
visit_id
medication_code
base_jaccard
revised_jaccard
delta_jaccard
base_f1
revised_f1
delta_f1
active_ddi_degree
base_ddi_edges
revised_ddi_edges
delta_violation
pareto_beneficial
harmful_revision
```

Public-safe aggregate artifact:

`gate-summary.json`

It may contain only aggregate counts, policy yields, confidence intervals, frozen public identities and the gate verdict.

It must not contain patient IDs, visit IDs, raw predictions, checkpoint paths, private data paths, or candidate-level rows.

## Stop rule

After `gate-summary.json` is audited, stop.

Do not automatically run Tension, S3, S4, another backbone, or a stronger verifier.

The next research action must be chosen from the Gate 01 result.
