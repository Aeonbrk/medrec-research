# Handoff

Updated: 2026-09-19.

```text
Current phase: POST_RELATIONAL_PAIR_FAILURE_MULTI_VIEW_REFORMULATION
Paper Experiment Contract: v1.0 + v1.1 + v1.2 + v1.3 amendments CURRENT
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
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-final-relational-architecture-early-termination.md`
- `research/prototypes/final-relational-architecture/README.md`
- `research/prototypes/final-relational-architecture/result.json`

## Current evidence

The 8-lane final relational architecture search on `mimic-iii-canonical-131-paper-dev-v1` at revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00` tested whether non-separable pair relations formed before pooling improve medication recommendation. Five upstream lanes ran to full 30-epoch completion; following decisive upstream failure, three downstream lanes were terminated early to conserve compute:

1. **Foundation Anchor Reproduction**: `foundation_code` at Ep 5 / 0.30 achieves Dev Jaccard = **0.546626**, replicating prior `resolution_code` down to $10^{-9}$ (PASS).
2. **Pair A (`summary_operator`)**: Multiplicative conjunction fails against additive composition (`summary_add` 0.549611 vs `summary_mul` 0.546079, $\Delta J = -0.003532$, verdict `KILL_NO_MATERIAL_SIGNAL`).
3. **Pair B (`pair_granularity`)**: Non-separable code-pair attention fails to improve over factorized attention (`nonseparable_pair` 0.543162 vs `factorized_pair` 0.544349, $\Delta J = -0.001187$, verdict `KILL_NO_MATERIAL_SIGNAL`). Both pair-level formulations fall below the single-code baseline `foundation_code` (0.546626).
4. **Truncated Downstream Lanes**: `joint_competition_pair` (stopped Ep 25), `untyped_edge_pair` (stopped Ep 24), `temporal_edge_pair` (stopped Ep 15) marked `TRUNCATED_NON_INTERPRETABLE`.
5. **Key Architecture Clue**: `summary_add` achieved the highest completed Dev Jaccard (0.549611, $+0.002984$ vs foundation). Because its additive slots are a linear rotation of $(u_D, u_P, u_H)$, it indicates that modality-separated medication-specific evidence channels provide a promising direction. Classified as `BEST_COMPLETED_ARCHITECTURE_CLUE` pending capacity-matched isolation.
6. **Enforced Routing**: `TERMINATE_RELATIONAL_PAIR_REFINEMENT_REFORMULATE_AROUND_MODALITY_SEPARATED_FINE_CODE_EVIDENCE`.

## Terminal Final Relational Architecture Search Results (2026-09-19)

Executed on the 319 Execution Plane across physical GPUs 0–7 at revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00` (Test strictly sealed with `test_loaded = false`):

| Lane | Status | Params | Selected Ckpt / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Dev Avg Meds | $\Delta J$ vs Foundation |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `foundation_code` | **COMPLETE** | 1,295,367 | Ep 5 / 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.4289 | 0.000000 |
| `summary_add` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.549611 | 0.700831 | 0.795774 | 0.070840 | 20.4097 | **+0.002984** |
| `summary_mul` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.546079 | 0.697773 | 0.794356 | 0.069782 | 19.9987 | -0.000547 |
| `factorized_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.30 | 0.544349 | 0.696591 | 0.792744 | 0.072023 | 21.4859 | -0.002277 |
| `nonseparable_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.543162 | 0.694911 | 0.792572 | 0.070803 | 19.9211 | -0.003464 |
| `joint_competition_pair` | **TRUNCATED** | 1,511,304 | Ep 5 / 0.30* | N/A* | N/A* | N/A* | N/A* | N/A* | TRUNCATED (Ep 25) |
| `untyped_edge_pair` | **TRUNCATED** | 1,511,304 | Ep 5 / 0.30* | N/A* | N/A* | N/A* | N/A* | N/A* | TRUNCATED (Ep 24) |
| `temporal_edge_pair` | **TRUNCATED** | 1,511,304 | Ep 5 / 0.30* | N/A* | N/A* | N/A* | N/A* | N/A* | TRUNCATED (Ep 15) |

\* Partial metrics from truncated lanes are descriptive execution state only and are not valid scientific evidence.

### Matched Comparisons

- **Pair A (`summary_operator`: control `summary_add`, candidate `summary_mul`)**: $\Delta J = -0.003531$. Verdict: `KILL_NO_MATERIAL_SIGNAL`.
- **Pair B (`pair_granularity`: control `factorized_pair`, candidate `nonseparable_pair`)**: $\Delta J = -0.001187$. Verdict: `KILL_NO_MATERIAL_SIGNAL`.

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
