# Drug-Conditioned Precedent Memory (DCPM) mechanism screen falsification

Date: 2026-09-18

## Evidence

A bounded, two-arm Train/Dev mechanism screen evaluated Drug-Conditioned Precedent Memory (DCPM) against an exactly parameter-matched SharedPrecedent control on `mimic-iii-canonical-131-paper-dev-v1` at source revision `98f334fef9af6c78d8b8ad8701819e7eb9805bfd` (seed `20260921`, 60 complete epochs, NVIDIA RTX 3090).

Both arms shared identical target-free clinical encoder representations ($d=128$, 2 clinical attention blocks), identical DrugQuery local reads $l_{im}$, identical Train-only memory pools with query-patient exclusion, identical precomputed coarse peer pools ($L=256$, TF-IDF over diagnoses, procedures, and history codes), identical common readout/head architecture, exact parameter count (1,079,428 parameters), and identical AdamW optimization and loss (BCE + 0.05 normalized DDI). Neither arm accessed Test data.

| Arm | Checkpoint | Threshold | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Dev AvgMed |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| SharedPrecedent (Control) | Epoch 3 | 0.40 | 0.543606 | 0.696129 | 0.792335 | 0.072298 | 19.9901 |
| DCPM (Candidate-Conditioned) | Epoch 3 | 0.35 | 0.542203 | 0.694874 | 0.792684 | 0.074479 | 21.9982 |
| **Delta (DCPM − Control)** | - | - | **-0.001403** | **-0.001255** | **+0.000349** | **+0.002181** | **+2.008113** |

## Interpretation and Decision

1. **Falsification of candidate-conditioned precedent relevance**: Conditioning precedent retrieval queries on individual candidate medications ($q_{im} = \text{LN}(W_h h_i + W_l l_{im} + W_d d_m)$) yielded no predictive gain ($\Delta J = -0.001403$) over a single patient-level precedent query ($q_i = \text{LN}(W_h h_i + W_l \bar{l}_i + W_d \bar{d})$). Under identical peer pools and representations, precedent relevance is dominated by global patient state rather than per-drug queries.
2. **Safety override inapplicable**: The candidate-conditioned model slightly increased DDI rate (+0.002181) alongside higher average prescription count (+2.008 medications/visit), ruling out any trade-off safety justification.
3. **Verdict**: `KILL_DCPM_MECHANISM`. Per the frozen protocol, $\Delta J \le +0.002$ triggers termination. No post-hoc modifications (DCPM-v2, temperature sweeps, peer pool size variations, auxiliary contrastive losses) or extra seeds are authorized. This cross-patient precedent retrieval direction is closed.
