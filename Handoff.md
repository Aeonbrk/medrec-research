# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE SEARCH — RELATIONAL EVIDENCE STABILITY PREPARATION
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
- `research/memory/decisions/2026-09-18-relational-evidence-screen.md`
- `research/prototypes/relational-evidence-screen/README.md`

## Current evidence

The 8-lane relational-evidence architecture screen on `mimic-iii-canonical-131-paper-dev-v1` at revision `18ae6c89dcb6ca52137e18ebeabe36bd5a303002` evaluated fine-code stability and candidate-conditioned relational evidence:

1. **Fine-Code Stability (4 Conditions)**: Medication-specific fine-code selection is strictly stable across 4 independent random seed conditions (`canonical`, `stability_1`, `stability_2`, `stability_3`). All 4/4 conditions exceed $+0.0100$ Jaccard gain (mean $\Delta J = +0.011734$, mean $\Delta \text{F1} = +0.010118$, mean $\Delta \text{PRAUC} = +0.007976$) with favorable safety (mean $\Delta \text{DDI} = -0.001640$). Verdict: `STABLE_FINE_CODE_ACCESS`. Fine-code clinical memory access is confirmed as a durable foundation.
2. **Relational Evidence Hypothesis (`relational_code` vs `unary_code`)**: Multiplicative cross-type evidence conjunction ($u_D \odot u_P$, $u_D \odot u_H$, $u_P \odot u_H$) outperforms matched additive/unary composition at equal parameters (1,427,080): $\Delta J = +0.004105$, $\Delta \text{F1} = +0.003371$, $\Delta \text{PRAUC} = +0.001131$, and substantial DDI safety gain ($\Delta \text{DDI} = -0.005341$, dropping DDI rate from 7.52% to 6.98%). Verdict: `RELATIONAL_EVIDENCE_SIGNAL`.
3. **Enforced Routing**: **`PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN`**. Relational cross-type evidence conjunction qualifies for multi-seed stability testing.

## Terminal Relational Evidence Screen Results

Executed on the 319 Execution Plane across physical GPUs 0–7 in parallel at revision `18ae6c89dcb6ca52137e18ebeabe36bd5a303002` (60 complete epochs per lane, Test strictly sealed with `test_loaded = false`):

| Comparison | Control (Ckpt / OP) | Candidate (Ckpt / OP) | Control J | Candidate J | ΔJ | ΔF1 | ΔPRAUC | ΔDDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **FC: Cond 0 (Canonical)** | `resolution_visit` (Ep 7 / 0.35) | `resolution_code` (Ep 5 / 0.30) | 0.535091 | 0.546626 | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | Portfolio prior |
| **FC: Cond 1 (Stability 1)** | `resolution_visit_s1` (Ep 7 / 0.30) | `resolution_code_s1` (Ep 6 / 0.30) | 0.534789 | 0.545625 | **+0.010836** | +0.009038 | +0.007899 | +0.004406 | Stable gain |
| **FC: Cond 2 (Stability 2)** | `resolution_visit_s2` (Ep 8 / 0.35) | `resolution_code_s2` (Ep 6 / 0.35) | 0.533419 | 0.547681 | **+0.014262** | +0.012560 | +0.008141 | +0.000820 | Peak gain |
| **FC: Cond 3 (Stability 3)** | `resolution_visit_s3` (Ep 6 / 0.30) | `resolution_code_s3` (Ep 5 / 0.35) | 0.535859 | 0.546163 | **+0.010303** | +0.008637 | +0.008077 | -0.006196 | Stable gain |
| **FC: 4-Condition Mean** | — | — | — | — | **+0.011734** | **+0.010118** | **+0.007976** | **-0.001640** | **`STABLE_FINE_CODE_ACCESS`** |
| **Part B: Relational** | `unary_code` (Ep 7 / 0.35) | `relational_code` (Ep 5 / 0.35) | 0.538877 | 0.542982 | **+0.004105** | +0.003371 | +0.001131 | -0.005341 | **`RELATIONAL_EVIDENCE_SIGNAL`** |

Enforced routing: **`PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN`**.

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
