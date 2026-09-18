# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE SEARCH — POST-PORTFOLIO ARBITRATION
Paper Experiment Contract: v1.0 + v1.1 + v1.2 amendments CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-18-evidence-access-portfolio-screen.md`
- `research/prototypes/evidence-access-portfolio/README.md`

## Current evidence

The 8-lane evidence-access architecture portfolio identified two clean surviving mechanisms over matched controls at equal parameter count (1,295,367) under 60 complete epochs:

1. **Code-level resolution (`resolution_code`)**: $\Delta J = +0.011536$ over within-visit pooling (`resolution_visit`), with improved F1 ($+0.0102$), PR-AUC ($+0.0078$), and lower DDI ($-0.005589$). Survives as `MECHANISM_SIGNAL`.
2. **Iterative evidence re-access (`depth_reread`)**: $\Delta J = +0.004144$ over state-only refinement (`depth_state`), achieving peak Dev Jaccard $0.551259$ with lower DDI ($-0.000731$). Survives as `MECHANISM_SIGNAL`.
3. **Local prediction (`prediction_local`)**: $\Delta J = +0.012976$ over hidden interaction aggregation, but failed DDI safety ($\Delta \text{DDI} = +0.003843 > +0.0020$). Classified as `SIGNAL_WITH_SUPPORTING_METRIC_COST`.
4. **Pre-temporal candidate state (`temporal_med`)**: $\Delta J = +0.000447$ over shared history. Falsified and closed (`KILL_NO_MATERIAL_SIGNAL`).

Previous falsified mechanisms: DCPM ($\Delta J = -0.001403$), RouteFact ($\Delta J = -0.008252$), ECRC ($\Delta J = +0.000341$), and CCTM data supportability (59.3% zero-recurrent visits).

## Terminal Evidence-Access Portfolio Results

Executed on the 319 Execution Plane across physical GPUs 0–7 in parallel at revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3` (60 complete epochs per lane, 1,295,367 parameters in all 8 variants, canonical RNG, Test strictly sealed):

| Pair | Control (Ckpt / OP) | Candidate (Ckpt / OP) | Control J | Candidate J | ΔJ | ΔF1 | ΔPRAUC | ΔDDI | ΔAvgMed | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Temporal** | `temporal_shared` (Ep 3 / 0.30) | `temporal_med` (Ep 3 / 0.30) | 0.544485 | 0.544932 | +0.000447 | +0.000415 | -0.000049 | +0.000292 | -0.0053 | **`KILL_NO_MATERIAL_SIGNAL`** |
| **Resolution** | `resolution_visit` (Ep 7 / 0.35) | `resolution_code` (Ep 5 / 0.30) | 0.535091 | 0.546626 | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | +0.4715 | **`MECHANISM_SIGNAL`** |
| **Depth** | `depth_state` (Ep 5 / 0.35) | `depth_reread` (Ep 4 / 0.35) | 0.547115 | 0.551259 | **+0.004144** | +0.003790 | +0.005406 | -0.000731 | +0.3433 | **`MECHANISM_SIGNAL`** |
| **Prediction** | `prediction_aggregate` (Ep 5 / 0.35) | `prediction_local` (Ep 3 / 0.35) | 0.535935 | 0.548911 | **+0.012976** | +0.011286 | +0.009895 | +0.003843 | -0.3692 | **`SIGNAL_WITH_SUPPORTING_METRIC_COST`** |

Portfolio routing: **`MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION`**.
No automatic compound (A+B) model authorized. Next step is scientific arbitration and primary-source novelty audits between code-level resolution and iterative depth re-access.

## Terminal CCTM Supportability Audit Results

Executed on the 319 Execution Plane against canonical snapshot `molerec-table1-c721-www23` at source revision `fbdcdafdf93aa4d14fa0cea2d19039ff7b02c488` (4,233 Train patients, 10,489 Train visits, 6,256 history-bearing prediction events, zero Dev/Test access):

| Metric | Definition | Observed Value | Threshold | Result |
| :--- | :--- | ---: | ---: | :--- |
| **A. All-history recurrent occurrence coverage** | Recurrent D/P/M tokens / all history tokens | 0.476337 (228,786 / 480,303) | $\ge 0.30$ | **PASS** |
| **B. Non-med recurrent occurrence coverage** | Recurrent D/P tokens / all non-med history tokens | 0.373536 (87,273 / 233,640) | $\ge 0.20$ | **PASS** |
| **C. Event-level recurrent non-med support** | Fraction of history events with $\ge 3$ recurrent D/P | 0.365249 (2,285 / 6,256) | $\ge 0.50$ | **FAIL** |
| **D. Event-level recurrent all-concept support** | Fraction of history events with $\ge 5$ recurrent D/P/M | 0.405850 (2,539 / 6,256) | $\ge 0.50$ | **FAIL** |

Verdict: **`KILL_CCTM_SUPPORTABILITY`**.
Concept trajectories are not a pervasive modeling substrate across the patient population. Over 59% of history-bearing visits have zero recurrent trajectories; the median count is 0.0. The premise is permanently terminated without model implementation, ontology relaxation, or parameter tuning.

## Terminal ECRC Screen Results

Executed on `mimic-iii-canonical-131-paper-dev-v1` at revision `c668a8e4a194c92a8933068e8ff99991d014c185` across 6 lanes (GPUs 0–5 on 319, 60 complete epochs per lane, Test strictly sealed):

| Pair | Arm | Seed | Dev Jaccard (Predicted K) | Dev Jaccard (Oracle K) | Verdict |
| :--- | :--- | :--- | ---: | ---: | :--- |
| Exact Primary A | `kind_exact_a` / `kcond_exact_a` | 20260923 | 0.531435 vs 0.531469 (+0.000033) | 0.553597 vs 0.553793 (+0.000196) | FAILS gate |
| Exact Primary B | `kind_exact_b` / `kcond_exact_b` | 20260924 | 0.533083 vs 0.532068 (-0.001015) | 0.552653 vs 0.553139 (+0.000486) | FAILS gate |
| **Exact Mean** | **Mean Delta** | Both | **-0.000491** | **+0.000341** | **`KILL_ECRC_CHOICE_MECHANISM`** |
| BCE Supporting | `kind_bce_a` / `kcond_bce_a` | 20260923 | 0.534076 vs 0.534389 (+0.000312) | 0.555077 vs 0.557760 (+0.002683) | Supporting only |

### Scientific takeaway

Under the tested rank-8 ECRC formulation and DrugQuery evidence path, cardinality-conditioned medication utilities produced negligible oracle-K re-ranking value. This kills that formulation and does not justify a size-head rescue. It does not establish a universal fixed-ranking theorem for all future medication-recommendation models.

No size-head tuning, rank sweeps, temperature tuning, or HPO is authorized as an ECRC rescue.

## Development seed convention

For all new project-owned initial DEVELOPMENT architecture/mechanism screens, use the MoleRec-derived canonical RNG convention:

```python
torch.manual_seed(1203)
torch.cuda.manual_seed_all(1203)
np.random.seed(2048)
random.seed(1203)
```

Internal matched controls use the same convention. External published baselines preserve source-native seed policies when available. Survivors still require a predeclared multi-seed stability experiment; the canonical seed is not robustness evidence.

Test remained sealed throughout this screen.
