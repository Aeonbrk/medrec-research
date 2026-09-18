# Evidence-access architecture portfolio screen verdict — 2026-09-18

Date: 2026-09-18
Status: **DECISION ENFORCED: MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION**

## Evidence

A bounded, eight-lane 60-epoch architecture portfolio screen evaluated four orthogonal evidence-access bottlenecks on `mimic-iii-canonical-131-paper-dev-v1` at execution revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3` (starting authoritative revision `ecf32d7737f855e3ac713c5e3b694a8b3d845f49`, preflight bug fixed in `aec07f311c5fc2f137d07bb172b67e12a89eeee3`).

All eight variants ran concurrently on physical GPUs 0–7 on the 319 Execution Plane from a clean detached worktree (`/root/zhb/medrec-research-evidence-access`). Every lane completed all 60 epochs under the canonical RNG convention (`torch=1203`, `cuda=1203`, `random=1203`, `numpy=2048`). All variants instantiate exactly 1,295,367 trainable parameters and passed strict tensor-identical paired initialization. Test remained strictly sealed (`test_loaded = false`).

### Matched-Pair Results

| Pair | Control (Ckpt / OP) | Candidate (Ckpt / OP) | Control J | Candidate J | ΔJ | ΔF1 | ΔPRAUC | ΔDDI | ΔAvgMed | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Temporal** | `temporal_shared` (Ep 3 / 0.30) | `temporal_med` (Ep 3 / 0.30) | 0.544485 | 0.544932 | +0.000447 | +0.000415 | -0.000049 | +0.000292 | -0.0053 | **`KILL_NO_MATERIAL_SIGNAL`** |
| **Resolution** | `resolution_visit` (Ep 7 / 0.35) | `resolution_code` (Ep 5 / 0.30) | 0.535091 | 0.546626 | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | +0.4715 | **`MECHANISM_SIGNAL`** |
| **Depth** | `depth_state` (Ep 5 / 0.35) | `depth_reread` (Ep 4 / 0.35) | 0.547115 | 0.551259 | **+0.004144** | +0.003790 | +0.005406 | -0.000731 | +0.3433 | **`MECHANISM_SIGNAL`** |
| **Prediction** | `prediction_aggregate` (Ep 5 / 0.35) | `prediction_local` (Ep 3 / 0.35) | 0.535935 | 0.548911 | **+0.012976** | +0.011286 | +0.009895 | +0.003843 | -0.3692 | **`SIGNAL_WITH_SUPPORTING_METRIC_COST`** |

### Absolute Candidate Evaluation

| Candidate | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Avg Med Count |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `temporal_med` | 0.544932 | 0.697154 | 0.788846 | 0.078785 | 20.8596 |
| `resolution_code` | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.4289 |
| `depth_reread` | 0.551259 | 0.702581 | 0.796649 | 0.071966 | 20.7648 |
| `prediction_local` | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.9647 |

## Interpretation and Scientific Takeaways

1. **Pair 1: Pre-temporal medication identity is not a material bottleneck**: Candidate-specific longitudinal GRU states (`temporal_med`) yielded an indistinguishable $+0.000447$ Jaccard gain over a shared longitudinal representation (`temporal_shared`). When explicit medication persistence features (previous-visit presence, historical frequency, visits-since-last-use) are provided equally to both arms, pre-temporal candidate tracking adds no predictive value. The hypothesis is decisively falsified and terminated (`KILL_NO_MATERIAL_SIGNAL`).
2. **Pair 2: Code-level evidence resolution is a genuine mechanism signal**: Allowing medication-specific queries to select directly over fine clinical code tokens (`resolution_code`) beats within-visit pooled representations (`resolution_visit`) by $+0.011536$ Jaccard (+1.15%), accompanied by uniform gains in F1 ($+0.0102$), PR-AUC ($+0.0078$), and lower DDI rate ($-0.005589$). Code-level attention is a validated mechanism (`MECHANISM_SIGNAL`).
3. **Pair 3: Iterative evidence re-access outperforms state refinement**: Re-querying clinical evidence memory with updated medication states (`depth_reread`) outperforms equal-depth and equal-parameter state-only transformation (`depth_state`) by $+0.004144$ Jaccard. Supporting metrics all improve ($\Delta \text{F1} = +0.0038$, $\Delta \text{PR-AUC} = +0.0054$, $\Delta \text{DDI} = -0.000731$). `depth_reread` attained the highest absolute Dev Jaccard in the portfolio ($0.551259$). Iterative evidence re-access is a validated mechanism (`MECHANISM_SIGNAL`).
4. **Pair 4: Local potential aggregation incurs safety penalty**: Computing scalar local potential scores per token and pooling via log-mean-exp (`prediction_local`) delivered $+0.012976$ Jaccard gain over hidden interaction aggregation (`prediction_aggregate`), but violated the frozen DDI guardrail ($\Delta \text{DDI} = +0.003843$, exceeding the $\le +0.0020$ threshold). Classified as `SIGNAL_WITH_SUPPORTING_METRIC_COST`.

## Decision and Routing

- **Verdict**: `MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION`.
- **Survivors**: `resolution` (`resolution_code`) and `depth` (`depth_reread`).
- **Policy Enforcement**: Per the frozen scientific contract, having multiple surviving mechanisms does **NOT** authorize an automatic compound model (no automatic $A+B$, no $A+B+C$). The project must arbitrate between code-level evidence selection and iterative evidence re-access (or determine whether their computation graph can be unified coherently with a primary-source closest-work novelty audit) before any compound training is scheduled.
- **Test Set**: Strictly sealed; no Test access authorized.

Artifact: `research/prototypes/evidence-access-portfolio/result.json`.
