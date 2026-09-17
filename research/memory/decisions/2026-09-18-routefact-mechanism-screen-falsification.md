# RouteFact mechanism screen falsification — 2026-09-18

Date: 2026-09-18

## Evidence

A bounded, two-arm Train/Dev mechanism screen evaluated Route-Factored Medication Recommendation (RouteFact) against an exactly parameter-matched auxiliary-supervision control (RouteAux) on `mimic-iii-canonical-131-paper-dev-v1` at source revision `8eee27ad88b63990cc8f1c5355b4a47bd84c7923` (seed `20260922`, 60 complete epochs, NVIDIA RTX 3090, Train/Dev only, zero Test access).

Both arms shared identical target-free clinical encoder representations ($d=128$, 2 clinical attention blocks), identical DrugQuery local reads, identical medication embeddings, identical route embeddings ($d=128$, 63 route coordinates: 62 real Train-observed routes plus 1 unspecified route fallback), identical medication-route projection and route biases, exact parameter count (914,497 parameters), identical Train-only route vocabulary and per-medication support mask (856 legal medication-route coordinates, 13 medications with unspecified fallback enabled, 12 Train fallback positive pairs), identical loss weights (medication BCE + 0.10 route BCE + 0.05 normalized DDI), and identical AdamW optimization. Dev raw route labels were not read (`no dev_route_targets.npy`).

| Arm | Checkpoint | Threshold | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Dev AvgMed |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| RouteAux (Matched Control) | Epoch 6 | 0.35 | 0.543183 | 0.695431 | 0.789858 | 0.076354 | 20.059969 |
| RouteFact (Candidate) | Epoch 5 | 0.35 | 0.534931 | 0.688512 | 0.784713 | 0.074816 | 20.175118 |
| **Delta (RouteFact − Control)** | - | - | **-0.008252** | **-0.006919** | **-0.005145** | **-0.001539** | **+0.115149** |

## Interpretation and Decision

1. **Falsification of route-level decision factorization**: Forcing medication presence through a noisy-OR over Train-supported administration routes ($P(y_{im}=1|X_i) = 1 - \prod_{r \in R_m}(1 - \sigma(a_{imr}))$) severely degraded predictive fidelity ($\Delta J = -0.008252$, $\Delta \text{F1} = -0.006919$, $\Delta \text{PR-AUC} = -0.005145$) relative to direct medication scoring with identical auxiliary route supervision.
2. **Intermediate vs decision representation**: The RouteAux control reached $J = 0.543183$, matching typical DrugQuery baseline performance and demonstrating that intermediate route supervision does not harm the direct head. However, making the noisy-OR route aggregation the mandatory decision bottleneck forces an uncalibrated independent-cause assumption across administration routes that degrades medication-set calibration.
3. **Safety override inapplicable**: While Dev DDI decreased slightly ($\Delta \text{DDI} = -0.001539$), average medication count slightly increased (+0.115 medications/visit), and no safety override was authorized for this non-safety mechanism screen.
4. **Verdict**: `KILL_ROUTEFACT_MECHANISM`. Under the frozen decision boundary ($\Delta J \le +0.002$), RouteFact is terminated immediately. No route taxonomy merging, route-loss sweeps, temperature tuning, route-count/K sweeps, dose extension, second seed, RouteFact-v2, or Test evaluation is authorized. This route factorization formulation is closed.
