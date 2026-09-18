# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE HYPOTHESIS TESTING — ECRC TERMINATED
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
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
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-verdict.md`
- `research/prototypes/ecrc-cardinality-context/README.md`

## Current evidence

Medication-specific late evidence selection (DrugQuery) remains the strongest repeated positive mechanism.

Three recent bounded mechanism screens are decisively falsified and closed:

1. **DCPM (Precedent Memory)**: $\Delta J = -0.001403$. Closed (`KILL_DCPM_MECHANISM`).
2. **RouteFact (Administration Routes)**: $\Delta J = -0.008252$. Closed (`KILL_ROUTEFACT_MECHANISM`).
3. **ECRC (Cardinality Context)**: Mean exact oracle-K $\Delta J = +0.000341$ (+0.034%, failing the $+0.004$ gate), mean exact predicted-K $\Delta J = -0.000491$ (negative deployable value). Closed (`KILL_ECRC_CHOICE_MECHANISM`).

## Terminal ECRC Screen Results

Executed on `mimic-iii-canonical-131-paper-dev-v1` at revision `c668a8e4a194c92a8933068e8ff99991d014c185` across 6 lanes (GPUs 0–5 on 319, 60 complete epochs per lane, Test strictly sealed):

| Pair | Arm | Seed | Dev Jaccard (Predicted K) | Dev Jaccard (Oracle K) | Verdict |
| :--- | :--- | :--- | ---: | ---: | :--- |
| Exact Primary A | `kind_exact_a` / `kcond_exact_a` | 20260923 | 0.531435 vs 0.531469 (+0.000033) | 0.553597 vs 0.553793 (+0.000196) | FAILS gate |
| Exact Primary B | `kind_exact_b` / `kcond_exact_b` | 20260924 | 0.533083 vs 0.532068 (-0.001015) | 0.552653 vs 0.553139 (+0.000486) | FAILS gate |
| **Exact Mean** | **Mean Delta** | Both | **-0.000491** | **+0.000341** | **`KILL_ECRC_CHOICE_MECHANISM`** |
| BCE Supporting | `kind_bce_a` / `kcond_bce_a` | 20260923 | 0.534076 vs 0.534389 (+0.000312) | 0.555077 vs 0.557760 (+0.002683) | Supporting only |

### Scientific takeaway

Regimen cardinality does not act as an informative decision context for medication preference ($u_m(x, K) \approx u_m(x)$). The fixed ranking Top-$K$ assumption holds; conditioning medication identity preference on hypothesized size produces negligible re-ranking even under oracle cardinality.

No size-head tuning, rank sweeps, temperature tuning, or HPO is authorized.

Test remained sealed throughout this screen.
