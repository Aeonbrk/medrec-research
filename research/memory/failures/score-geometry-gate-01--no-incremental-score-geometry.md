<!-- markdownlint-disable MD013 -->

# Failure Record: Score-geometry sufficiency (Gate 01 no incremental score geometry)

Source boundary: `medrec-research` Idea `002-score-geometry-sufficiency`, Gate 01 formal run `gate-01-score-geometry-sufficiency-20260902-174013` on `319-lab` at frozen harness commit `28fc24c64998c81563446f3f8e5bc10340e2b17b`. The independent integrity audit concluded `INTEGRITY_PASS`; the authoritative research decision is `STOP_NO_INCREMENTAL_SCORE_GEOMETRY` / `TERMINATE_IDEA_002`.

- **Status**: Historical Memory (this score-geometry route is terminated under the recorded setting; revisit only when materially different observable information, problem formalization, causal/mechanistic claim, baseline, representation, or evidence source changes the hypothesis)

## Failed hypothesis

A preregistered five-bin, Dev-fitted, low-complexity non-monotone mapping of frozen MoleRec medication confidence would recover incremental false-positive routing information beyond raw `ScoreOnly`.

## What was tested

Under the frozen MoleRec validation setting, the DDI-active predicted-medication candidate universe

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\},
$$

and fixed singleton deletion

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\},
$$

the candidate outcome is

$$
Y^{PB}_{t,m}=\mathbf 1[m\notin M_t].
$$

Gate 01 used the full 1,059-patient validation cohort and created a fresh deterministic patient-disjoint Idea-002 Dev/Audit partition with seed `2002`: 529 Dev patients and 530 Audit patients. All score-map quantities were fit on Dev only. Audit labels were reserved for evaluation.

The formal comparison was restricted to `Random`, unchanged ascending `ScoreOnly`, the preregistered five-bin `ScoreGeometry` map, and retrospective `Oracle`.

## What was observed

1. **Fresh patient-level split and Dev-only fitting held**: 7,422 candidates from 436 eligible Dev patients and 8,127 candidates from 422 eligible Audit patients; patient overlap was zero.
2. **Dev five-bin empirical PB risks were strictly monotonic with score**:
   - B1: `0.581145`
   - B2: `0.462938`
   - B3: `0.317172`
   - B4: `0.179919`
   - B5: `0.053908`
3. **The induced `ScoreGeometry` ordering was exactly `ScoreOnly`**: the Dev diagnostic was `STOP_DEV_ORDER_EQUIVALENT`.
4. **Incremental routing value was exactly zero at every frozen budget**:
   - 10%: `Geometry - Score = 0.000000`
   - 20%: `Geometry - Score = 0.000000`
   - 30%: `Geometry - Score = 0.000000`
5. **Patient-clustered bootstrap intervals were exactly `[0, 0]`** for `Geometry - Score` at 10%, 20%, and 30% budgets over 1,000 replicates.
6. **Residual retrospective outcome heterogeneity remained substantial**: `Oracle - ScoreOnly` was approximately `+0.3879`, `+0.4068`, and `+0.4368` at the 10%, 20%, and 30% budgets respectively.
7. **Independent audit passed**: `ccf-integrity-auditor` reproduced the formal verdict and reported `INTEGRITY_PASS` with zero numeric discrepancy and no Dev/Audit or test leakage.

## Why this route failed

The preregistered five-bin map did not discover a Dev risk ordering different from raw ascending confidence. Because the bin risks were strictly ordered in the same direction as score and within-bin tie-breaking also used ascending score, the candidate ranking collapsed exactly to `ScoreOnly`. The frozen map therefore supplied no incremental ranking information under this gate.

## What did not fail

- **Frozen recommender confidence remains a strong simple selector**: `ScoreOnly` achieved PB yield `0.612069`, `0.593231`, and `0.563167` at the 10%, 20%, and 30% budgets.
- **Residual false-positive heterogeneity remains unresolved**:

$$
\boxed{\text{Residual false-positive heterogeneity remains unresolved.}}
$$

- **Oracle headroom is not mechanism evidence**: the retrospective target-bearing Oracle establishes outcome heterogeneity not explained by the frozen scalar confidence. It does not establish that any target-free signal is observable, learnable, or deployable.
- **Other observable information remains untested by this gate**: the result does not falsify relational, temporal, structural, patient-conditioned, cross-model, or other target-free information sources.

## Reusable residue

- Frozen recommender confidence must remain a mandatory simple control for future selective revision or verification mechanisms.
- Any strictly order-preserving transformation of score cannot create new routing information; a claimed new selector must change information or ordering for a mechanistically justified reason.
- Residual Oracle headroom motivates a question but cannot substitute for a held-out incremental test of a proposed target-free observable.
- The fresh patient-disjoint Dev/Audit pattern and patient-clustered uncertainty procedure remain useful for future validation-only hypothesis-selection gates, subject to each new idea's own preregistration.

## Route boundary

This particular score-geometry route is terminated.

The result must not be enlarged into claims that all confidence-derived functions are universally useless, that all one-dimensional score structure has been exhausted, that target-free residual information is absent, or that relational, temporal, structural, or DDI-derived information is useless.

## Non-revival condition

Changing only the function class while preserving the same scientific premise is not enough to reactivate this route. Replacing five bins with ten bins, a spline, or an MLP is not a materially new hypothesis unless an independent mechanism supplies a reason to expect a different information structure and the new claim is preregistered before outcome inspection.

A future route is scientifically distinct only when materially different observable information, problem formalization, causal/mechanistic claim, baseline, representation, or evidence source changes the failure condition.

## Evidence boundary

This record is scoped to the frozen MoleRec checkpoint, validation-only candidate corpus, DDI-active review universe, singleton deletion operator, preregistered five-bin Dev-fitted mapping, deterministic tie-breaking, and frozen budgets. Historical validation has already been used for route selection across Ideas 001 and 002; later validation-only Audit partitions can support further route selection but are not untouched final generalization evidence. The test split remains untouched.
