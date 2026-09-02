<!-- markdownlint-disable MD013 -->

# Idea 002: Score-Geometry Sufficiency

- **Idea ID**: `002-score-geometry-sufficiency`
- **Status**: Hypothesis selected; experiment not yet designed or authorized
- **Mode**: `ccf-idea-optimizer / exploratory -> hypothesis selection`
- **Source boundary**: Begins after authoritative Idea 001 closure commit `194daf4580ca7dfe80497ccfdce89ffcee95f46f`
- **Previous route**: Idea 001 `TERMINATE_CURRENT_TENSION_ROUTE`
- **Gate 03 under Idea 001**: `NOT_AUTHORIZED`
- **Next CCFA owner**: `ccf-experiment-designer`

## Current audited state

Idea 001 established the following scoped facts under the frozen MoleRec validation setting, DDI-active predicted-medication candidate universe, and fixed singleton deletion operator

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

Within this candidate universe, the retrospective Gate 01 label simplifies to

$$
Y^{PB}_{t,m}=\mathbf 1[m\notin M_t].
$$

The audited lifecycle state entering this idea is:

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

Preserved empirical evidence:

1. Routing opportunity exists under fixed $R_0$.
2. MoleRec medication probability is already a strong predictor of false-positive status.
3. ScoreOnly leaves substantial Oracle headroom:
   - Oracle - ScoreOnly ≈ +38.87 percentage points at 10% budget.
   - Oracle - ScoreOnly ≈ +41.48 percentage points at 20% budget.
4. The preregistered global DDI-degree scalar did not add information:
   - Dev selected $\lambda^*=0$.
   - Scalar = ScoreOnly on Audit.
5. The preregistered support-pressure interaction was unsupported:

$$
I_{Tension}\approx-0.0052
$$

with a 95% confidence interval crossing zero.
6. These results do not imply that every DDI-derived representation, every interaction, or every target-free signal is useless.

Historical failures and reusable lessons remain scoped evidence, not axioms. This idea does not revive Tension.

## Residual research question

$$
\boxed{
\text{What target-free observable information explains false-positive heterogeneity beyond frozen recommender confidence?}
}
$$

Before introducing any new information source, this idea first asks a stricter null question:

$$
\boxed{
\text{Is the apparent residual headroom partly caused by using the existing scalar recommender score too simplistically?}
}
$$

A monotone transformation of $s_t(m)$ cannot improve routing relative to ScoreOnly because it preserves candidate ordering. Temperature scaling, logits, $-s$, and $0.5-s$ therefore do not constitute distinct routing hypotheses. The first meaningful score-only alternative must permit a non-monotone but deliberately low-complexity mapping.

## Candidate hypothesis 1 — score-only residual geometry

### Claim

Conditional on using only the frozen MoleRec score $s_t(m)$, a preregistered low-complexity non-monotone mapping $g(s_t(m))$ contains reproducible ranking structure for $Y^{PB}$ that raw ascending ScoreOnly fails to exploit.

### Observable

Frozen scalar medication probability only:

$$
s_t(m).
$$

Minimal representation: a one-dimensional coarse piecewise or quantile-bin map fitted on development patients. No neural selector.

### Strongest simple control

Raw ScoreOnly.

Monotonic calibration methods are not distinct ranking controls because they preserve ScoreOnly ordering.

### Cheapest falsification test

Use validation only. Create a fresh patient-disjoint Idea-002 Dev/Audit partition. Fit exactly one preregistered low-complexity one-dimensional map from score to empirical false-positive probability on Dev, freeze it, and evaluate routing on Audit against unchanged ScoreOnly at 10% and 20% review budgets using patient-clustered bootstrap.

### PASS criterion

At both primary budgets,

$$
LowerCI_{95\%}
\left[
PBYield_{g(s)}-PBYield_{ScoreOnly}
\right]>0.
$$

### FAIL criterion

If the condition fails at either primary budget, terminate the hypothesis that a low-complexity score-only reordering explains meaningful residual headroom.

### Leakage assessment

The decision-time observable is genuinely target-free. Dev labels may fit $g$; Audit labels may only evaluate it. No current target prescription, test statistic, future visit, or post-outcome information may enter the selector.

### Portability

Very high for score-producing MedRec baselines.

### Scientific value

High falsification priority but low standalone method novelty. A positive result would mean ScoreOnly was a misspecified use of existing confidence rather than evidence for a new information source or mechanism.

## Candidate hypothesis 2 — within-visit relative confidence geometry

### Claim

Conditional on absolute medication score $s_t(m)$, a medication's relative confidence position inside the same predicted prescription contains reproducible incremental information about false-positive status.

### Observable

A minimal statistic such as within-visit rank percentile:

$$
r_t(m)
=
\frac{
|\{m'\in\hat M_t:s_t(m')>s_t(m)\}|
}{
|\hat M_t|-1
}.
$$

A deterministic convention must be preregistered for singleton sets.

### Strongest simple control

Flexible score-only map $g(s)$ plus predicted medication count $|\hat M_t|$, because relative rank partly encodes prescription size.

### Cheapest falsification test

On Dev, fit a simple control using score geometry and set size, then the identical model plus one rank scalar. Freeze both and compare Audit routing yields.

### PASS criterion

The rank-augmented selector must outperform the simple control with a strictly positive 95% confidence interval at both 10% and 20% budgets.

### FAIL criterion

Failure at either primary budget terminates escalation of relative-rank semantics into learned score-geometry architectures.

### Leakage assessment

Target-free. Uses only current-visit recommender outputs and predicted-set context.

### Portability

High across score-producing baselines; structural decoders require an explicitly available equivalent observable.

### Scientific value

Potentially meaningful. A positive result would imply that the same absolute confidence has different error semantics depending on the competing predictions in the same visit.

## Candidate hypothesis 3 — continuation versus new prediction

### Claim

Conditional on frozen score, whether a predicted medication is a continuation from the previous observed prescription or a newly predicted medication contains reproducible incremental false-positive information.

### Observable

$$
h_t(m)=\mathbf1[m\in M_{t-1}].
$$

Use this binary statistic before any longitudinal learned representation.

### Strongest simple control

Score geometry plus train-only medication prevalence, because continuation status may otherwise rediscover chronic-medication popularity or calibration differences.

### Cheapest falsification test

On Dev compare a simple score-plus-frequency control against the identical model plus $h_t(m)$; freeze and evaluate Audit routing yields.

### PASS criterion

Strictly positive lower 95% confidence interval for incremental PBYield at both primary budgets.

### FAIL criterion

Failure at either budget terminates the simple continuation/addition explanation before any richer longitudinal-consistency model is considered.

### Leakage assessment

Target-free only if $M_{t-1}$ is inside the frozen prediction-time feature contract. Current $M_t$, future prescriptions, and future visits are prohibited.

### Portability

High and backbone-independent under the existing longitudinal MedRec task.

### Scientific value

Meaningful if scoped as confidence-conditional residual routing information. It must not be presented as the novel claim that medication history matters.

## Candidate hypothesis 4 — co-selection compatibility

### Claim

Conditional on frozen score and medication popularity, a predicted medication with unusually weak compatibility with the rest of the predicted prescription is more likely to be a false positive.

### Observable

A train-only marginal-frequency-corrected co-selection statistic, for example

$$
c_t(m)
=
\frac{1}{|\hat M_t|-1}
\sum_{m'\in\hat M_t\setminus\{m\}}
PMI_{train}(m,m').
$$

No GNN, hypergraph, or learned medication-set representation is justified before this scalar is tested.

### Strongest simple control

$g(s)$ plus predicted set size and train medication frequency.

### Cheapest falsification test

Precompute pair statistics from training prescriptions only. On Dev compare the frequency/set-size control against the same simple model plus $c_t(m)$; freeze and evaluate on Audit.

### PASS criterion

Positive lower 95% confidence interval for incremental PBYield at both 10% and 20% budgets.

### FAIL criterion

No supported gain at either primary budget terminates escalation to graph or set-encoder mechanisms for this explanation.

### Leakage assessment

Target-free if all pair statistics are estimated from training prescriptions only and candidate context comes from the current predicted set.

### Portability

High and largely model-agnostic.

### Scientific value

Potentially meaningful as a transparent test of whether medication-set compatibility explains residual false positives beyond confidence, set size, and popularity.

## Candidate hypothesis 5 — cross-backbone disagreement

### Claim

Conditional on MoleRec confidence, lack of corroboration from other already-qualified frozen MedRec predictors contains reproducible incremental false-positive information.

### Observable

The simplest candidate representation is a vote count or mean normalized rank across other frozen predictors. No learned ensemble.

### Strongest simple control

Plain ensembling. Disagreement is scientifically interesting only if it beats adding the best alternative score or a simple equal-weight ensemble.

### Cheapest falsification test

Only if aligned frozen validation predictions already exist. Compare MoleRec plus a plain ensemble control with the same control plus one disagreement statistic. Do not train a new backbone.

### PASS criterion

The disagreement statistic must provide strictly positive incremental PBYield with lower 95% confidence interval above zero at both primary budgets.

### FAIL criterion

Otherwise classify any benefit as ordinary ensemble information rather than a disagreement mechanism.

### Leakage assessment

Target-free provided all component predictions were produced without current targets and all selection remains Dev-only.

### Portability

Conceptually high, but operationally more expensive. The five qualified baselines are mechanism carriers from two pinned source lineages rather than five fully independent scientific lineages.

### Scientific value

Moderate unless disagreement itself survives plain ensemble controls.

## Candidate comparison matrix

| Rank | Candidate | Scientific importance | Falsifiability | Incremental-information plausibility | Simple-control strength | Minimal cost | Leakage risk | Portability | Novelty |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Score-only residual geometry | High as null test | Very high | N/A — no new information | Excellent | Lowest | Very low | Very high | Low |
| 2 | Within-visit relative rank | High | Very high | High | Excellent | Very low | Very low | High | Medium |
| 3 | Continuation vs new prediction | High | High | High | Strong | Very low | Low | Very high | Medium-low |
| 4 | Co-selection compatibility | High | High | Medium-high | Strong | Low | Very low | High | Medium |
| 5 | Cross-backbone disagreement | Medium-high | High | Medium | Excellent | Medium | Very low | Medium-high | Low-medium |

## Recommended next hypothesis

**Candidate 1 — score-only residual geometry.**

### Why this one first

Gate 02 established that raw recommender confidence is a strong selector, but it did not establish that ascending score is the best possible use of the scalar score for false-positive routing.

Before importing any new information source, the cheapest scientific challenge is therefore to test whether a deliberately low-complexity non-monotone $g(s)$ captures meaningful residual headroom.

If it does, the correct conclusion is not that a new mechanism was discovered. The conclusion is that ScoreOnly was an unnecessarily restrictive use of already available recommender output.

### Why the others should wait

Candidate 2 introduces the smallest genuinely new information source: the rest of the same current output vector. It should be tested only if score-only residual geometry fails.

Candidate 3 should wait because continuation status may primarily identify different confidence or medication-frequency distributions.

Candidate 4 introduces training-cohort relational information and therefore requires explicit popularity and set-size controls.

Candidate 5 has the highest operational cost and must distinguish disagreement from ordinary ensemble benefit.

No current candidate justifies jumping directly to patient-context neural networks, richer DDI graphs, GNN selectors, or new backbones.

## Proposed Idea 002 one-sentence problem statement

> Determine whether residual false-positive routing headroom among DDI-active predicted medications can first be explained by low-complexity structure in the frozen recommender's own output distribution, before introducing any new evidence source or learned selector.

## Proposed first gate

`Gate 01 — Score-Geometry Sufficiency`

The eventual gate should preserve the same scientific task semantics — DDI-active predicted medications, fixed singleton $R_0$, validation only, and

$$
Y^{PB}=\mathbf1[m\notin M_t].
$$

Its minimal comparison surface should be limited to:

```text
Random
ScoreOnly
Predeclared one-dimensional score-only residual map g(s)
Oracle
```

No DDI feature, history feature, co-selection feature, second model, or architecture belongs in this first gate.

## What this gate would falsify

The gate would test whether remaining Oracle–ScoreOnly headroom is materially attributable to a simple misspecification of how the existing MoleRec scalar confidence is converted into review priority.

A negative result would support the narrower statement:

$$
\boxed{
\text{Residual headroom cannot be explained by the preregistered low-complexity function of }s_t(m)\text{ alone.}
}
$$

Only then would within-visit relative confidence geometry become the next justified information hypothesis.

## Stop boundary

This ideation stage ends at hypothesis selection.

### Do NOT implement

- Do not create Idea 002 runner code.
- Do not create selector architectures.
- Do not create DDI transforms.
- Do not create longitudinal encoders.
- Do not create ensemble infrastructure.
- Do not modify Idea 001.

### Do NOT run

- Do not execute 319.
- Do not use the test split.
- Do not train a model.
- Do not regenerate five-backbone predictions.
- Do not retrospectively probe the old Gate 02 Audit rows to select candidate features.

## Next CCFA owner

`ccf-experiment-designer`

Its next task is limited to preregistering the minimal `Gate 01 — Score-Geometry Sufficiency` experiment. Implementation and execution remain unauthorized until that design is independently reviewed and frozen.
