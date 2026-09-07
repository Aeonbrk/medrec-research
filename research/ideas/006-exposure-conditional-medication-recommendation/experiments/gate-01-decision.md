# Gate 01 Decision Record — Exposure-Conditioned Learning vs Direct Exposure Controls

## Verdict: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

- **Gate ID**: `GATE01_EXPOSURE_CONDITIONED_LEARNING`
- **Authoritative Stage**: `IDEA_006_GATE_01`
- **Active Idea**: `006-exposure-conditional-medication-recommendation`
- **Execution Timestamp**: `2026-09-07T16:05:29.589992+00:00`
- **Frozen Batch Size**: `2048`
- **Freeze Manifest SHA256**: `c7d5d7d19640e2aafdb41b98bdf58d4092cb82d4ddb44ae105450385813775c9`
- **Next CCFA Owner**: `ccf-pipeline-orchestrator`

---

## 1. Decision Question Answered

> Under the frozen leakage-safe provider-order-time task, does end-to-end exposure-conditioned DDI learning create incremental safety/fidelity value beyond a direct exposure-aware reranker that receives exactly the same active-regimen state and DDI matrix?

**Result**: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

### Conditions Evaluation Matrix

| Condition | Description | Threshold | Observed Value | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Condition 1** | Tune Budget Feasibility | No `TUNE_BUDGET_MISS` | Budget Miss: `False` | **PASS** |
| **Condition 2** | Safety over Base | $R_{EC} \le 0.90 R_{Base}$ & CI upper < 0 | Ratio: `0.7607`, CI: `[-0.023961, -0.023062]` | **PASS** |
| **Condition 3** | Bounded Fidelity Cost | $\Delta\text{Recall}_{EC-Base} \ge -0.010$ | $\Delta\text{Recall} = -0.0050$ | **PASS** |
| **Condition 4** | Beyond Direct Reranker | $R_{EC} \le R_{Rerank} + 0.001$, $\Delta\text{Recall} \ge +0.005$, CI lower > 0 | $\Delta R = -0.012546$, $\Delta\text{Recall} = -0.0044$, CI: `[-0.0053, -0.0034]` | **FAIL** |
| **Condition 5** | No Weak Dominance | Controls do not weakly dominate | Static dom: `False`, Hard dom: `False` | **PASS** |

---

## 2. Dev Evaluation Metrics (K=5 Primary)

| Method | Selected Param | Recall@5 | IncrementalExposureDDI@5 | ActiveDDI@5 | NewDDI@5 | NDCG@5 | Hit@5 | MRR | micro-PRAUC |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GlobalFrequency** | N/A | 0.3781 | 0.062930 | 0.081087 | 0.000000 | 0.2583 | 0.4436 | N/A | N/A |
| **Base** | N/A | 0.5104 | 0.098269 | 0.100562 | 0.094230 | 0.3847 | 0.5754 | 0.4019 | 0.1672 |
| **StaticLoss** | $\lambda = 8.0$ | 0.5085 | 0.097290 | 0.098930 | 0.094010 | 0.3836 | 0.5733 | 0.4012 | 0.1663 |
| **DirectExposureRerank** | $\gamma = 0.5$ | 0.5098 | 0.087302 | 0.091574 | 0.075465 | 0.3842 | 0.5749 | N/A | N/A |
| **ExposureHardConstraint** | N/A | 0.3097 | 0.000000 | 0.000000 | 0.000000 | 0.2413 | 0.3707 | N/A | N/A |
| **ExposureConditional** | $\lambda = 2.0$ | 0.5055 | 0.074756 | 0.078464 | 0.060806 | 0.3805 | 0.5704 | 0.3984 | 0.1647 |

---

## 3. Secondary Evaluation Metrics (K=10)

| Method | Recall@10 | IncrementalExposureDDI@10 | ActiveDDI@10 | NewDDI@10 | NDCG@10 | Hit@10 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GlobalFrequency** | 0.5874 | 0.085454 | 0.097391 | 0.066667 | 0.3253 | 0.6543 |
| **Base** | 0.6971 | 0.100743 | 0.101702 | 0.097589 | 0.4462 | 0.7505 |
| **StaticLoss** | 0.6973 | 0.101281 | 0.101777 | 0.099154 | 0.4457 | 0.7507 |
| **DirectExposureRerank** | 0.6968 | 0.090915 | 0.094432 | 0.084353 | 0.4458 | 0.7506 |
| **ExposureHardConstraint** | 0.3935 | 0.000000 | 0.000000 | 0.000000 | 0.2675 | 0.4552 |
| **ExposureConditional** | 0.6942 | 0.080345 | 0.081498 | 0.073540 | 0.4426 | 0.7480 |

---

## 4. Quarantine and Scientific Integrity Verification

1. **Quarantine Adherence**:
   - `R0 Holdout` was strictly uninspected (0 clinical events, 0 predictions, 0 targets accessed).
   - Existing project test split remains untouched.
   - `R0 Dev` was accessed only after all models, hyperparameter configurations, safety budget $B$, and task code were frozen.
2. **Equal Entitlement**:
   - `ExposureConditional`, `DirectExposureRerank`, and `ExposureHardConstraint` received the identical active-regimen state $A_t$ and frozen DDI matrix $D$.
   - All learned models (`Base`, `StaticLoss`, `ExposureConditional`) used the identical architecture, inputs, optimizer, and early stopping rules.
3. **Interpretation Boundary**:
   - `IncrementalExposureDDI` is an operational DDI surrogate, not ADE, clinical harm, or clinical safety.
   - eMAR administration is execution evidence, not treatment appropriateness.

---

## 5. Next Routing

- **Next Owner Skill**: `ccf-pipeline-orchestrator`
