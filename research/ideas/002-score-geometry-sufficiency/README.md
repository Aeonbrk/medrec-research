<!-- markdownlint-disable MD013 -->

# Idea 002: Score-Geometry Sufficiency

- **Idea ID**: `002-score-geometry-sufficiency`
- **Status**: `TERMINATED_AT_GATE_01`
- **Formal verdict**: `STOP_NO_INCREMENTAL_SCORE_GEOMETRY`
- **Integrity audit**: `INTEGRITY_PASS`
- **Gate 02**: `NOT_AUTHORIZED`
- **Source boundary**: begins after authoritative Idea 001 closure commit `194daf4580ca7dfe80497ccfdce89ffcee95f46f`
- **Frozen protocol commit**: `e70c50e8f7afc4b9a0c8cc7a4792cf639642b61a`
- **Implementation commit**: `28fc24c64998c81563446f3f8e5bc10340e2b17b`
- **Research decision**: [`research-decision.md`](research-decision.md)
- **Failure memory**: [`../../memory/failures/score-geometry-gate-01--no-incremental-score-geometry.md`](../../memory/failures/score-geometry-gate-01--no-incremental-score-geometry.md)

## Research question

Under the frozen MoleRec validation setting, DDI-active predicted-medication candidate universe, and singleton deletion operator

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\},
$$

does a preregistered five-bin, Dev-fitted, low-complexity non-monotone mapping of the frozen medication confidence recover reproducible false-positive routing information beyond raw ascending `ScoreOnly`?

Within this candidate universe,

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

## Gate 01 result

The validation cohort was repartitioned at patient level with frozen seed `2002`. The five Dev quintile empirical PB risks were

```text
B1  0.581145
B2  0.462938
B3  0.317172
B4  0.179919
B5  0.053908
```

They were strictly monotonic with the frozen recommender score. With the preregistered ascending-score tie-break, the induced `ScoreGeometry` ordering was exactly identical to `ScoreOnly`.

On the Audit partition (`8,127` candidates across `422` eligible patients):

| Budget | ScoreOnly PBYield | Geometry - Score | Oracle - Score |
| ---: | ---: | ---: | ---: |
| 10% | 0.612069 | 0.000000 | +0.387931 |
| 20% | 0.593231 | 0.000000 | +0.406769 |
| 30% | 0.563167 | 0.000000 | +0.436833 |

The 95% patient-clustered bootstrap interval for `Geometry - Score` was exactly `[0, 0]` at all three budgets. The independent audit reproduced the result with zero numeric discrepancy.

## Supported scientific statement

> The preregistered five-bin low-complexity score-only mapping did not provide reproducible ranking information beyond raw ScoreOnly.

The gate does not establish that every possible one-dimensional score function is useless. It does not establish that target-free residual information is absent. The retrospective Oracle gap establishes unresolved outcome heterogeneity, not the existence of any particular observable mechanism.

## Route boundary

This Idea is terminated. Replacing the same five-bin premise with more bins, a spline, or an MLP is not an authorized continuation. A new hypothesis requires a materially different observable, problem formalization, mechanism, baseline, representation, or evidence source and its own preregistration.

The test split remains untouched.

## Next research state

The unresolved question is narrower than the original Tension route and broader than score geometry:

$$
\boxed{\text{What target-free observable information, not reducible to }s_t(m),\text{ explains residual false-positive heterogeneity?}}
$$

Historical candidates listed before Gate 01 execution were exploratory lineage only. None, including the former Candidate 2, is automatically authorized as the next Idea.
