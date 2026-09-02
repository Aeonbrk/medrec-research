<!-- markdownlint-disable MD013 -->

# Gate 01 — Score-Geometry Sufficiency

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

Status:

`DESIGNED_NOT_EXECUTED`

This is a validation-only falsification gate. It is not a publication experiment, not a deployable routing policy, and not authorization for a new model architecture.

---

## 1. Scientific state entering Gate 01

Idea 001 is closed at authoritative commit:

`194daf4580ca7dfe80497ccfdce89ffcee95f46f`

with:

```text
Idea 001:
TERMINATE_CURRENT_TENSION_ROUTE

Gate 01:
PASS / AUDIT_PASS

Gate 02:
STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL / INTEGRITY_PASS

Gate 03:
NOT_AUTHORIZED
```

The preserved empirical facts are:

1. selective routing headroom exists under the fixed singleton deletion operator;
2. MoleRec medication probability is already a strong target-free selector;
3. ScoreOnly still leaves substantial Oracle headroom;
4. the preregistered global DDI-degree scalar supplied zero incremental signal beyond ScoreOnly;
5. the preregistered support-pressure interaction was unsupported;
6. none of those results establishes that every target-free signal or every richer DDI representation is useless.

Idea 002 does not revive Tension.

---

## 2. Central hypothesis

Under the frozen MoleRec setting and the same DDI-active predicted-medication candidate universe, raw ascending medication score may be an unnecessarily restrictive use of the existing scalar recommender output.

The falsifiable hypothesis is:

> A preregistered low-complexity non-monotone mapping of the frozen MoleRec medication score contains reproducible false-positive ranking structure that raw ScoreOnly fails to exploit.

Formally, among eligible candidates,

$$
Y^{PB}_{t,m}=\mathbf 1[m\notin M_t].
$$

Let raw ScoreOnly rank candidates by

$$
s_t(m)\uparrow.
$$

Gate 01 tests whether a fixed low-complexity score-only map

$$
g(s_t(m))
$$

can rank $Y^{PB}=1$ candidates better than ScoreOnly on an untouched Idea-002 Audit partition.

This gate does not ask whether a new information source helps. The proposed map uses only information already contained in $s_t(m)$.

---

## 3. Why this gate comes before richer hypotheses

A strictly monotone transformation of $s_t(m)$ cannot change candidate ordering. Therefore logits, temperature scaling, $-s_t(m)$, $1-s_t(m)$, and fixed threshold margins are not distinct routing hypotheses.

Before introducing within-visit rank, history, co-selection structure, external evidence, or cross-backbone disagreement, the project must first test whether a deliberately low-capacity non-monotone use of the existing score explains any reproducible part of the residual Oracle headroom.

If this gate fails, the next research question may introduce genuinely new observable information. If it passes, the correct interpretation is that raw ScoreOnly was misspecified as a routing rule, not that a new mechanism has been discovered.

---

## 4. Venue and evidence assumptions

Evidence standard:

`CCF-A-style AI/ML hypothesis-selection discipline`

Exact publication venue is not frozen.

Therefore this gate prioritizes:

- strongest simple control;
- patient-disjoint development and audit partitions;
- a single preregistered low-capacity score map;
- patient-clustered uncertainty;
- explicit negative stopping rules;
- no test split;
- no architecture search;
- no post-hoc feature expansion.

---

## 5. Frozen scientific setting

Reuse the exact audited Idea 001 scientific identities.

### Backbone

- method: `MoleRec`
- source revision: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
- profile: `molerec-embedding`
- checkpoint SHA256: `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
- baseline core SHA256: `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511`
- adapter SHA256: `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531`
- prediction threshold: `0.5`

### Dataset / protocol identities

- dataset ID: `molerec-table1-comparison-v1-1`
- snapshot ID: `molerec-table1-c721-www23`
- Dataset Manifest SHA256: `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712`
- snapshot SHA256: `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58`
- DDI asset SHA256: `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7`
- feature availability SHA256: `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9`
- medication vocabulary SHA256: `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08`
- medication vocabulary size: `131`

### Environment

- environment: `medrec-molerec-table1`
- environment SHA256: `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda`

### Split boundary

`validation only`

Test patients, visits, targets, scores, statistics, or metrics must not participate in this gate.

---

## 6. Upstream candidate source

The formal Gate 01 input should reuse the complete audited candidate corpus produced by Idea 001 Gate 02 formal run:

`gate-02-confidence-sufficiency-20260902-155433`

The upstream corpus contains all 15,549 eligible validation candidates and has already passed independent row-level integrity audit with zero invariant failures and zero partition leakage.

For Idea 002:

- reuse the complete candidate corpus;
- ignore the historical `gate02_partition` field completely;
- do not use the old Dev/Audit assignment in fitting, evaluation, tie-breaking, stratification, or reporting;
- create a fresh Idea-002 patient split defined below;
- do not rerun or retrain MoleRec merely to reproduce already-audited candidate rows.

The historical Gate 02 partition is dead metadata for this experiment.

The required candidate fields are:

```text
patient_order
visit_order
medication_code
model_score
active_ddi_degree
pareto_beneficial
delta_jaccard
delta_violation
```

Patient/visit identifiers and raw candidate rows remain restricted and must not be committed to Git.

---

## 7. Candidate universe and label

Use exactly the Idea 001 candidate rule:

$$
\mathcal Q_t
=
\{
m\in\hat M_t:d_t(m)>0
\}.
$$

No policy may alter $\mathcal Q$.

For each candidate:

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

Because every candidate has positive active DDI degree,

$$
\Delta V_{t,m}<0.
$$

Within this frozen setting,

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

This is a retrospective false-positive label under the fixed benchmark semantics. It is not a clinical safety, treatment benefit, or clinician-intent label.

---

## 8. Fresh Idea-002 Dev / Audit split

Use the complete validation patient universe, including patients with no eligible candidate rows, so seeded shuffling does not depend on eligibility.

The authoritative validation patient count is the same staged count used by Idea 001 Gate 02.

Procedure:

1. construct the complete ordered patient index universe;
2. shuffle with Python `random.Random(2002)`;
3. first half -> `Idea002-Dev`;
4. remainder -> `Idea002-Audit`;
5. all visits and candidate rows from one patient remain in exactly one partition.

Split seed:

`2002`

The split is frozen before any Idea-002 outcome analysis.

Do not move patients after observing support or results.

### Support rule

On Idea002-Audit, require at least 50 distinct patients with $Y^{PB}=1$ candidate support and at least 50 distinct patients with $Y^{PB}=0$ candidate support.

If either side has fewer than 50 patients:

`INSUFFICIENT_SUPPORT`

and stop without changing the split.

---

## 9. Preregistered score-only map

This gate permits exactly one learned score-only representation.

### 9.1 Dev quintile cutpoints

Let the eligible Idea002-Dev candidate scores sorted ascending be

$$
z_{(1)}\leq z_{(2)}\leq\dots\leq z_{(N_D)}.
$$

For

$$
q\in\{0.2,0.4,0.6,0.8\},
$$

define the nearest-rank Dev cutpoint

$$
c_q=z_{(\lceil qN_D\rceil)}.
$$

These four cutpoints define five score bins:

```text
B1: s <= c_0.2
B2: c_0.2 < s <= c_0.4
B3: c_0.4 < s <= c_0.6
B4: c_0.6 < s <= c_0.8
B5: s > c_0.8
```

Do not tune the number of bins.

Do not compare equal-width, decile, spline, polynomial, isotonic, kernel, logistic, neural, or alternative histogram variants inside this gate.

### 9.2 Dev bin risk

For each bin $B_j$, compute only on Idea002-Dev:

$$
\hat p_j
=
\frac{
\sum_{(t,m)\in B_j}Y^{PB}_{t,m}
}{
|B_j|
}.
$$

No smoothing parameter is fitted or tuned.

Freeze:

- four Dev cutpoints;
- five Dev empirical bin risks.

Define

$$
g(s)=\hat p_{b(s)}.
$$

Higher $g(s)$ means higher review priority.

### 9.3 Deterministic ordering

`ScoreGeometry` sorts Audit candidates by:

1. $g(s)$ descending;
2. raw $s$ ascending;
3. medication code ascending;
4. patient traversal order;
5. visit traversal order.

The raw score tie-break is intentional. If the fitted bin risks are monotone non-increasing with score, `ScoreGeometry` becomes order-equivalent to ScoreOnly rather than manufacturing differences inside bins.

### 9.4 Dev-only early stop

If the frozen five-bin map induces exactly the same complete candidate ordering as ScoreOnly on Idea002-Dev, record:

`STOP_DEV_ORDER_EQUIVALENT`

and do not inspect Idea002-Audit outcomes.

This is a valid falsification because the proposed map has failed to instantiate a distinct score-only routing rule.

Do not change the bin count or mapping after this stop.

---

## 10. Baseline matrix

### Random

Uniform candidate review expectation on Idea002-Audit:

$$
P(Y^{PB}=1).
$$

No Monte Carlo simulation is needed for the point estimate.

### ScoreOnly — strongest simple control

Rank:

$$
s_t(m)\uparrow.
$$

Tie-break:

1. medication code ascending;
2. patient traversal order;
3. visit traversal order.

### ScoreGeometry — only proposed selector

Use the frozen five-bin $g(s)$ defined above.

No other feature is permitted.

### Oracle — analysis-only upper bound

Use the same retrospective ordering semantics as Idea 001:

1. $Y^{PB}$ descending;
2. $\Delta J$ descending;
3. $-\Delta V$ descending;
4. medication code ascending;
5. patient traversal order;
6. visit traversal order.

Oracle is not a predictor and must never be presented as deployable.

### Explicitly excluded from Gate 01

Do not include:

- DDI degree as a ranking feature;
- within-visit rank;
- predicted medication count;
- previous-prescription membership;
- medication frequency;
- co-selection / PMI;
- embeddings;
- patient context;
- calibration networks;
- ensemble/disagreement signals;
- second backbones;
- MLPs, GNNs, transformers, LLMs, or learned selectors beyond the five-bin map.

Those belong to later hypotheses only if this gate fails.

---

## 11. Budgets

Use the inherited routing budgets:

$$
B\in\{10\%,20\%,30\%\}.
$$

For Idea002-Audit candidate count $N_A$:

$$
k(B)=\lfloor BN_A\rfloor.
$$

Primary decision budgets:

$$
10\%,20\%.
$$

The 30% budget is secondary consistency evidence only.

---

## 12. Primary metrics

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

Primary incremental quantity:

$$
Gap_{Geometry-Score}(B)
=
PBYield_{Geometry}(B)-PBYield_{Score}(B).
$$

Residual-headroom check:

$$
Gap_{Oracle-Score}(B)
=
PBYield_{Oracle}(B)-PBYield_{Score}(B).
$$

Remaining headroom after the map:

$$
Gap_{Oracle-Geometry}(B)
=
PBYield_{Oracle}(B)-PBYield_{Geometry}(B).
$$

Also report:

$$
Gap_{Score-Random}(B)
=
PBYield_{Score}(B)-PBYield_{Random}(B).
$$

### Residual-capture diagnostic

Report, but do not gate on a post-hoc threshold:

$$
RC_{Geometry}(B)
=
\frac{
PBYield_{Geometry}(B)-PBYield_{Score}(B)
}{
PBYield_{Oracle}(B)-PBYield_{Score}(B)
}
$$

whenever the denominator is positive.

This quantifies what fraction of ScoreOnly's residual Oracle headroom is captured by the low-complexity map.

Do not invent a "good enough" cutoff after observing the result.

---

## 13. Uncertainty

Use patient-clustered bootstrap on Idea002-Audit.

Frozen configuration:

- resamples: `1000`
- seed: `1203`
- resampling unit: Audit patient

The score map is frozen from Dev and must not be refit inside Audit bootstrap replicates.

Report 95% percentile intervals for:

- ScoreOnly yield;
- ScoreGeometry yield;
- ScoreOnly - Random;
- ScoreGeometry - ScoreOnly;
- Oracle - ScoreOnly;
- Oracle - ScoreGeometry;
- residual-capture diagnostic when defined.

---

## 14. Formal decision tree

### Gate 01-A — support

If Audit support fails the 50-patient-per-outcome rule:

`INSUFFICIENT_SUPPORT`

Stop.

### Gate 01-B — does residual headroom still exist on the fresh Audit partition?

At both primary budgets require:

$$
LowerCI_{95\%}[Gap_{Oracle-Score}(B)]>0.
$$

If this does not hold at both 10% and 20%:

`STOP_NO_RELIABLE_RESIDUAL_HEADROOM`

Interpretation:

> The fresh Idea-002 Audit split does not independently retain reliable Oracle headroom beyond ScoreOnly, so no new residual explanation should be pursued from this gate.

### Gate 01-C — does the fixed low-complexity score map beat ScoreOnly?

If at both primary budgets:

$$
LowerCI_{95\%}[Gap_{Geometry-Score}(B)]>0,
$$

verdict:

`PASS_INCREMENTAL_SCORE_GEOMETRY`

Interpretation:

> A preregistered low-complexity non-monotone use of the existing MoleRec score captures reproducible false-positive ranking information that raw ascending ScoreOnly does not exploit.

This does not establish a new information source, a clinical policy, or a novel architecture.

If the condition fails at either primary budget:

`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`

Interpretation:

> Under the preregistered five-bin score-only map, residual routing headroom is not reproducibly explained by a low-complexity function of the frozen scalar recommender score alone.

After this stop, the next scientific owner may formulate a new hypothesis around genuinely additional observable information, with within-visit relative score geometry as the first candidate from Idea 002. That later hypothesis is not automatically authorized for implementation.

---

## 15. Claim-evidence matrix

| Claim | Evidence | Baselines | Metric | Decision use |
| --- | --- | --- | --- | --- |
| Raw score remains a strong selector on fresh Idea-002 Audit | held-out Audit ranking | Random, ScoreOnly | PBYield, Score-Random | context only |
| Residual routing headroom remains | held-out Audit Oracle comparison | ScoreOnly, Oracle | Oracle-Score | prerequisite |
| Low-complexity score geometry adds reproducible information | frozen Dev map evaluated once on Audit | ScoreOnly, ScoreGeometry | Geometry-Score | primary gate |
| Any gain is still only a partial explanation | Audit upper-bound comparison | ScoreGeometry, Oracle | Oracle-Geometry, residual capture | scope control |

---

## 16. Result tables to emit

No result may be invented. Use `TBD` until formal execution.

### Dev map

| Bin | Frozen score interval | Dev candidates | Dev distinct patients | Dev $P(Y^{PB}=1)$ | Priority rank |
| --- | --- | ---: | ---: | ---: | ---: |
| B1 | TBD | TBD | TBD | TBD | TBD |
| B2 | TBD | TBD | TBD | TBD | TBD |
| B3 | TBD | TBD | TBD | TBD | TBD |
| B4 | TBD | TBD | TBD | TBD | TBD |
| B5 | TBD | TBD | TBD | TBD | TBD |

### Audit policy yields

| Policy | 10% PBYield | 20% PBYield | 30% PBYield |
| --- | ---: | ---: | ---: |
| Random | TBD | TBD | TBD |
| ScoreOnly | TBD | TBD | TBD |
| ScoreGeometry | TBD | TBD | TBD |
| Oracle | TBD | TBD | TBD |

### Audit gaps and uncertainty

| Quantity | 10% | 20% | 30% | 95% CI available |
| --- | ---: | ---: | ---: | --- |
| Score - Random | TBD | TBD | TBD | yes |
| Geometry - Score | TBD | TBD | TBD | yes |
| Oracle - Score | TBD | TBD | TBD | yes |
| Oracle - Geometry | TBD | TBD | TBD | yes |
| Geometry residual capture | TBD | TBD | TBD | yes |

---

## 17. Implementation scope

The implementation owner may add only the smallest code required for this gate.

Expected idea-local files:

```text
research/ideas/002-score-geometry-sufficiency/experiments/
  gate-01-score-geometry-sufficiency.md
  run_score_geometry_sufficiency_gate.py
  gate-01-summary.json              # only after accepted formal execution
```

One focused synthetic/unit test file is permitted under `tests/unit/` if needed to verify changed scientific logic.

Do not promote code to `src/medrec_research/` unless an independently demonstrated multi-experiment reusable capability emerges later.

### Minimum changed-path tests

Synthetic verification should cover only failures that would change scientific interpretation:

1. fresh patient split is patient-disjoint and uses seed 2002;
2. Dev-only quintile map never reads Audit labels;
3. deterministic ScoreGeometry ordering matches the frozen tie-break rules;
4. the PASS/STOP decision tree behaves correctly for controlled synthetic positive and null cases.

Do not add broad regression suites or repeated smoke tests unrelated to these changed paths.

---

## 18. Formal execution and artifact boundaries

Formal execution belongs on the repository's registered remote execution plane under the existing research workflow.

Required sequence:

```text
P0  protocol frozen in Git
P1  idea-local runner implemented
P2  minimal synthetic verification passes
P3  implementation revision frozen
P4  one formal validation-only remote execution
P5  ccf-integrity-auditor independently recomputes evidence
P6  research decision: continue / kill
```

A successful process exit is not a scientific pass.

Formal evidence is not accepted until P5 integrity audit verifies:

- upstream candidate identity and row invariants;
- fresh Idea-002 split reproduction;
- no patient overlap;
- Dev-only map fitting;
- exact cutpoints and bin risks;
- exact policy ordering;
- exact yields and gaps;
- patient-cluster bootstrap intervals;
- final verdict.

### Git-safe outputs

May be committed after acceptance:

- this protocol;
- implementation code;
- synthetic tests;
- public aggregate `gate-01-summary.json`;
- integrity audit report;
- final research decision.

Must remain restricted:

- candidate-level rows;
- patient or visit identifiers;
- split membership lists;
- raw prediction records;
- checkpoints;
- private execution paths;
- raw traces or logs.

---

## 19. Prohibited post-hoc rescue

After formal Audit evaluation, do not rescue this gate by changing:

- split seed;
- Dev/Audit ratio;
- candidate universe;
- budgets;
- number of score bins;
- quantile definition;
- smoothing;
- tie-breaks;
- bootstrap seed or replicate count;
- PASS criterion;
- additional score transforms;
- new features.

Any such change is a new preregistered hypothesis, not a repair of Gate 01.

---

## 20. What this gate must never claim

Even after `PASS_INCREMENTAL_SCORE_GEOMETRY`, do not claim:

- clinical safety;
- medication correctness;
- patient benefit;
- clinician intent;
- prospective prescribing validity;
- causal error explanation;
- new information beyond recommender confidence;
- that score geometry exhausts Oracle headroom;
- that the five-bin map is a deployable selector;
- that Idea 001 Tension is revived.

The strongest allowed positive claim is:

> Under the frozen MoleRec validation setting, DDI-active predicted-medication universe, and fixed singleton deletion operator, a preregistered five-bin non-monotone mapping of the frozen medication score provided reproducible held-out routing information beyond raw ascending ScoreOnly.

---

## 21. Execution priority

| Priority | Experiment / action | Claim defended | Cost | Dependency | Stop condition |
| --- | --- | --- | --- | --- | --- |
| P0 | Freeze this protocol | prevents post-hoc redesign | low | Idea 002 selected hypothesis | protocol committed |
| P1 | Implement score-map runner | executable semantics | low | P0 | implementation complete |
| P2 | Minimal synthetic tests | scientific logic wiring | low | P1 | any changed-path failure |
| P3 | Freeze implementation revision | provenance | low | P2 | clean committed revision |
| P4 | Formal validation-only execution | primary evidence | low | P3 | formal verdict produced |
| P5 | Independent integrity audit | evidence acceptance | low | P4 | audit block or pass |
| P6 | Research decision | continue / kill route | low | P5 | stop after decision |

---

## 22. No-fabrication status

No Gate 01 experimental result has been generated in this document.

All result cells remain `TBD` until formal execution. Historical Idea 001 values are context only and must not be copied into Idea 002 result tables as if they were Idea 002 evidence.

---

## 23. Next CCFA owner

For actual execution coordination:

`ccf-pipeline-orchestrator`

Implementation remains idea-local. After formal execution, evidence must go to:

`ccf-integrity-auditor`

before any scientific continuation decision.
