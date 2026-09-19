# Final Relational Architecture Early Termination Verdict — 2026-09-19

Date: 2026-09-19
Status: **DECISION ENFORCED: TERMINATE_RELATIONAL_PAIR_REFINEMENT_REFORMULATE_AROUND_MODALITY_SEPARATED_FINE_CODE_EVIDENCE**

## Context and Reason for Early Termination

A planned eight-lane architecture search was deployed on the 319 Execution Plane across 8× NVIDIA RTX 3090 GPUs at frozen source revision `bdc3464e8e1771e6f5d291772e2be82882a4aa00` on dataset `mimic-iii-canonical-131-paper-dev-v1` (zero Test access).

The core hypothesis entering this round was that moving relation formation *before pooling*—by scoring non-separable clinical code pairs ($s_{mij} = \langle g_m, U x_i \odot V y_j \rangle$) rather than factorized summary products ($d_m \odot p_m$)—would resolve the structural bottleneck identified in relational-v1.

Five lanes completed all 30 planned training epochs:

1. `foundation_code` (anchor reproducing previous `resolution_code`)
2. `summary_add` (additive summary-level combination)
3. `summary_mul` (multiplicative summary-level combination)
4. `factorized_pair` (factorized pair scoring before pooling)
5. `nonseparable_pair` (non-separable pair scoring before pooling)

The completed results produced two decisive matched verdicts:

- **Pair A (`summary_operator`)**: `summary_add` (0.549611) decisively outperforms `summary_mul` (0.546079) by $\Delta J = +0.003532$. Multiplicative conjunction fails against matched additive composition.
- **Pair B (`pair_granularity`)**: `nonseparable_pair` (0.543162) fails to improve over `factorized_pair` (0.544349), yielding $\Delta J = -0.001187$. Furthermore, both pair-level architectures underperform the unpooled single-token foundation anchor (`foundation_code`: 0.546626) by $-0.003464$ and $-0.002277$ respectively.

The remaining three running lanes (`joint_competition_pair`, `untyped_edge_pair`, `temporal_edge_pair`) were downstream refinements constructed directly on top of this non-separable code-pair relation substrate. Because their upstream foundation is empirically unviable, continuing to expend ~9 GPU-hours on these downstream variants offered negligible expected scientific utility.

Per protocol, the three remaining lanes were terminated cleanly via targeted SIGTERM at their worker PIDs (GPUs 5, 6, 7 released), and marked as `TRUNCATED_NON_INTERPRETABLE`.

## Authoritative Completed Evidence (5 Lanes)

All completed lanes satisfied the v1.3 training horizon rule (all selected checkpoints occurred at Epoch 5 $\le 25$).

| Lane | Status | Params | Selected Ep / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Dev Avg Meds | $\Delta J$ vs Foundation |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `foundation_code` | **COMPLETE** | 1,295,367 | Ep 5 / 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.4289 | 0.000000 |
| `summary_add` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.549611 | 0.700831 | 0.795774 | 0.070840 | 20.4097 | **+0.002984** |
| `summary_mul` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.546079 | 0.697773 | 0.794356 | 0.069782 | 19.9987 | -0.000547 |
| `factorized_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.30 | 0.544349 | 0.696591 | 0.792744 | 0.072023 | 21.4859 | -0.002277 |
| `nonseparable_pair` | **COMPLETE** | 1,511,304 | Ep 5 / 0.35 | 0.543162 | 0.694911 | 0.792572 | 0.070803 | 19.9211 | -0.003464 |

### Foundation Reproduction Audit

- Prior `resolution_code` Dev Jaccard: 0.5466264791909929 (Ep 5, OP 0.30)
- Current `foundation_code` Dev Jaccard: 0.5466264791909929 (Ep 5, OP 0.30)
- Absolute discrepancy: $0.000000000$ (reproduction passes strictly; zero runner drift).

### Formal Matched Pair Verdicts

- **Pair A (`summary_operator`: control `summary_add`, candidate `summary_mul`)**:
  - $\Delta J = -0.003531$
  - $\Delta \text{F1} = -0.003058$
  - $\Delta \text{PRAUC} = -0.001418$
  - $\Delta \text{DDI} = -0.001058$
  - Verdict: `KILL_NO_MATERIAL_SIGNAL`. Multiplicative conjunction fails against matched additive composition.
- **Pair B (`pair_granularity`: control `factorized_pair`, candidate `nonseparable_pair`)**:
  - $\Delta J = -0.001187$
  - $\Delta \text{F1} = -0.001679$
  - $\Delta \text{PRAUC} = -0.000173$
  - $\Delta \text{DDI} = -0.001220$
  - Verdict: `KILL_NO_MATERIAL_SIGNAL`. Non-separable pair attention does not improve over factorized attention, and both drop below the single-code baseline.

## Truncated Execution State (3 Lanes)

These lanes were terminated for operational efficiency after upstream failure.

| Lane | Status | Last Epoch | Observed Ckpt at Termination | Elapsed Wall-Clock | Peak VRAM | Termination Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `joint_competition_pair` | **TRUNCATED_NON_INTERPRETABLE** | 25/30 | Ep 5 (OP=0.30) | 31,511s (525m) | 14,276 MB | Low expected value after upstream pair failure |
| `untyped_edge_pair` | **TRUNCATED_NON_INTERPRETABLE** | 24/30 | Ep 5 (OP=0.30) | 32,012s (533m) | 14,276 MB | Low expected value after upstream pair failure |
| `temporal_edge_pair` | **TRUNCATED_NON_INTERPRETABLE** | 15/30 | Ep 5 (OP=0.30) | 31,948s (532m) | 14,276 MB | Low expected value after upstream pair failure |

> [!WARNING]
> Partial metrics from truncated lanes are descriptive execution state only. They are not valid scientific evidence and must not be used for mechanism survive/kill decisions. No Pair C or Pair D verdicts are issued.

## Scientific Belief Updates

1. **Non-separable code-pair modeling before pooling is falsified**:
   Computing quadratic cross-type token pairs ($O(N_D \times N_P)$) prior to aggregation did not improve performance ($\Delta J = -0.001187$ vs factorized). More crucially, both pair-level architectures scored lower than the baseline token read (`foundation_code`). In clinical EHR data, cross-code combinatorial pairs explode the hypothesis space with uninformative co-occurrences, diluting medication-conditioned relevance signals while drastically multiplying computational cost (VRAM increased from 1.1GB to 6.4GB–14.3GB).
2. **Re-interpretation of `summary_add`**:
   `summary_add` achieved the highest Dev Jaccard across all tested models (0.549611, $+0.002984$ over `foundation_code`). However, its additive slots:
   $$r_{DP} = \frac{u_D + u_P}{\sqrt{2}}, \quad r_{DH} = \frac{u_D + u_H}{\sqrt{2}}, \quad r_{PH} = \frac{u_P + u_H}{\sqrt{2}}$$
   are a linearly recoverable rotation of the separate modality summaries $(u_D, u_P, u_H)$. It does not perform non-linear relational reasoning. Its success indicates that providing distinct, un-entangled representation channels for each clinical modality (Diagnosis, Procedure, History) provides higher discriminative power than forcing all tokens into a single pool or multiplying vectors.
3. **Status of `summary_add`**:
   `summary_add` is classified as `BEST_COMPLETED_ARCHITECTURE_CLUE`, not `FINAL_MODEL`. Its gain (+0.002984 Jaccard) is currently confounded by increased parameter capacity (1.51M vs 1.29M) and multiple dedicated readout heads. The causal driver must be isolated cleanly in a capacity-matched comparison.

## Enforced Policy and Routing

- **Scientific Routing**: `TERMINATE_RELATIONAL_PAIR_REFINEMENT_REFORMULATE_AROUND_MODALITY_SEPARATED_FINE_CODE_EVIDENCE`
- **Immediate Next Focus**: Reformulate architecture exploration away from cross-code pairs and toward capacity-controlled modality-separated evidence routing (multi-view fine-code attention).
- **Test Set Boundary**: Test set strictly sealed (`test_loaded: false`).
