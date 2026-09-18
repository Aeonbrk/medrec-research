# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE SEARCH — POST-SURVIVOR RESET
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
- `research/memory/decisions/2026-09-18-iterative-evidence-survivor-screen.md`
- `research/prototypes/iterative-evidence-survivor/README.md`

## Current evidence

The 8-lane iterative-evidence survivor screen on `mimic-iii-canonical-131-paper-dev-v1` at revision `82fb054abefe3a4b6560c9a3a2fd8640a32bc944` evaluated final-architecture resolution attribution and 4-condition depth stability:

1. **Resolution Attribution (`reread_code` vs `reread_visit`)**: $\Delta J = +0.014651$, $\Delta \text{F1} = +0.013301$, $\Delta \text{PRAUC} = +0.011395$, $\Delta \text{DDI} = -0.002295$. Code-level evidence memory remains a primary structural driver. Verdict: `CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE`.
2. **Four-Condition Depth Stability (`depth_reread` vs `depth_state`)**: Evaluated across canonical + 3 prospective seed offsets (`stability_1`, `stability_2`, `stability_3`). Results: `canonical` $\Delta J = +0.004144$; `stability_1` $\Delta J = -0.000650$; `stability_2` $\Delta J = +0.001365$; `stability_3` $\Delta J = +0.003033$. Fails stability requirements: 3/4 positive conditions, 2/4 material ($> +0.0020$), mean $\Delta J = +0.001973 < +0.0040$, mean $\Delta \text{DDI} = +0.002130 > +0.0020$. Verdict: `UNSTABLE_DEPTH_REREAD`.
3. **Enforced Routing**: **`RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE`**. Iterative re-reading is not promoted to Paper Candidate review. The project returns to architecture search. Future candidate architectures should build on fine code-level evidence selection while seeking more robust inductive structures than recurrent re-reading.

## Terminal Iterative Evidence Survivor Screen Results

Executed on the 319 Execution Plane across physical GPUs 0–7 in parallel at revision `82fb054abefe3a4b6560c9a3a2fd8640a32bc944` (60 complete epochs per lane, 1,295,367 parameters in all 8 variants, Test strictly sealed with `test_loaded = false`):

| Comparison | Control (Ckpt / OP) | Candidate (Ckpt / OP) | Control J | Candidate J | ΔJ | ΔF1 | ΔPRAUC | ΔDDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Q1: Resolution** | `reread_visit` (Ep 8 / 0.35) | `reread_code` (Ep 4 / 0.35) | 0.536608 | 0.551259 | **+0.014651** | +0.013301 | +0.011395 | -0.002295 | **`CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE`** |
| **Q2: Cond 0 (Canonical)** | `depth_state` (Ep 5 / 0.35) | `depth_reread` (Ep 4 / 0.35) | 0.547115 | 0.551259 | **+0.004144** | +0.003790 | +0.005406 | -0.000731 | Portfolio prior |
| **Q2: Cond 1 (Stability 1)** | `depth_state_s1` (Ep 4 / 0.35) | `depth_reread_s1` (Ep 5 / 0.35) | 0.551534 | 0.550884 | **-0.000650** | -0.000863 | +0.003052 | +0.004964 | Negative gain |
| **Q2: Cond 2 (Stability 2)** | `depth_state_s2` (Ep 6 / 0.35) | `depth_reread_s2` (Ep 6 / 0.35) | 0.547138 | 0.548502 | **+0.001365** | +0.000824 | +0.002637 | +0.002049 | Subthreshold |
| **Q2: Cond 3 (Stability 3)** | `depth_state_s3` (Ep 5 / 0.40) | `depth_reread_s3` (Ep 5 / 0.35) | 0.546843 | 0.549875 | **+0.003033** | +0.002590 | +0.003085 | +0.002240 | Modest gain |
| **Q2: 4-Condition Mean** | — | — | — | — | **+0.001973** | **+0.001585** | **+0.003545** | **+0.002130** | **`UNSTABLE_DEPTH_REREAD`** |

Enforced routing: **`RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE`**.

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
