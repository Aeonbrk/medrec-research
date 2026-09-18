# ECRC cardinality-context mechanism screen verdict — 2026-09-18

Date: 2026-09-18
Status: **DECISION ENFORCED: KILL_ECRC_CHOICE_MECHANISM**

## Evidence

A bounded, six-lane Train/Dev mechanism screen evaluated Exact-Cardinality Regimen Choice (ECRC) on `mimic-iii-canonical-131-paper-dev-v1` at source revision `c668a8e4a194c92a8933068e8ff99991d014c185` (60 complete epochs per lane, batch size 16, AdamW lr 1e-4, wd 1e-4, grad clip 5.0, MICA float32 deterministic policy, physical GPUs 0–5 on 319, Train/Dev only, zero Test access).

All variants share identical target-free clinical encoder representations ($d=128$, 2 clinical attention blocks), identical DrugQuery medication reads, identical size heads (LayerNorm + Linear + GELU + Linear to $K_{\max}+1=54$), identical rank-$r=8$ choice projections, exact parameter matching (437,571 parameters in all four variants), and identical paired initialization and sample order.

### Deployable Evaluation (`predicted_k`, native argmax size head decoder)

| Pair | Arm | Seed | Selected Epoch | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Dev AvgMed | Visit Count MAE |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BCE Supporting | `kind_bce_a` (Control) | 20260923 | Epoch 4 | 0.534076 | 0.688026 | 0.789880 | 0.083644 | 18.7496 | 3.9516 |
| BCE Supporting | `kcond_bce_a` (Candidate) | 20260923 | Epoch 4 | 0.534389 | 0.688349 | 0.790694 | 0.082988 | 18.8266 | 4.0047 |
| **BCE Delta** | **KCond − KInd** | 20260923 | - | **+0.000312** | **+0.000323** | **+0.000814** | **-0.000655** | **+0.0770** | **+0.0531** |
| Exact Primary A | `kind_exact_a` (Control) | 20260923 | Epoch 4 | 0.531435 | 0.685587 | 0.788413 | 0.084173 | 18.8544 | 4.1131 |
| Exact Primary A | `kcond_exact_a` (Candidate) | 20260923 | Epoch 4 | 0.531469 | 0.685620 | 0.788232 | 0.084457 | 18.8087 | 4.1099 |
| **Exact Delta A** | **KCond − KInd** | 20260923 | - | **+0.000033** | **+0.000034** | **-0.000181** | **+0.000284** | **-0.0457** | **-0.0033** |
| Exact Primary B | `kind_exact_b` (Control) | 20260924 | Epoch 4 | 0.533083 | 0.687122 | 0.788022 | 0.086308 | 19.4603 | 4.1779 |
| Exact Primary B | `kcond_exact_b` (Candidate) | 20260924 | Epoch 4 | 0.532068 | 0.686217 | 0.787800 | 0.086659 | 19.4319 | 4.1700 |
| **Exact Delta B** | **KCond − KInd** | 20260924 | - | **-0.001015** | **-0.000905** | **-0.000223** | **+0.000351** | **-0.0284** | **-0.0080** |
| **Exact Mean** | **Mean Delta** | Both | - | **-0.000491** | **-0.000435** | **-0.000202** | **+0.000318** | **-0.0370** | **-0.0056** |

### Privileged Diagnostic Evaluation (`oracle_k`, ground-truth target cardinality)

| Pair | Arm | Seed | Selected Epoch | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Dev AvgMed |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| BCE Supporting | `kind_bce_a` (Control) | 20260923 | Epoch 4 | 0.555077 | 0.705100 | 0.789880 | 0.083657 | 19.4882 |
| BCE Supporting | `kcond_bce_a` (Candidate) | 20260923 | Epoch 4 | 0.557760 | 0.707341 | 0.791294 | 0.082945 | 19.4882 |
| **BCE Delta** | **KCond − KInd** | 20260923 | - | **+0.002683** | **+0.002242** | **+0.001414** | **-0.000712** | **0.0000** |
| Exact Primary A | `kind_exact_a` (Control) | 20260923 | Epoch 4 | 0.553597 | 0.703839 | 0.788413 | 0.083942 | 19.4882 |
| Exact Primary A | `kcond_exact_a` (Candidate) | 20260923 | Epoch 4 | 0.553793 | 0.704004 | 0.788353 | 0.083857 | 19.4882 |
| **Exact Delta A** | **KCond − KInd** | 20260923 | - | **+0.000196** | **+0.000165** | **-0.000060** | **-0.000085** | **0.0000** |
| Exact Primary B | `kind_exact_b` (Control) | 20260924 | Epoch 4 | 0.552653 | 0.703161 | 0.788022 | 0.085799 | 19.4882 |
| Exact Primary B | `kcond_exact_b` (Candidate) | 20260924 | Epoch 4 | 0.553139 | 0.703587 | 0.788111 | 0.085927 | 19.4882 |
| **Exact Delta B** | **KCond − KInd** | 20260924 | - | **+0.000486** | **+0.000426** | **+0.000089** | **+0.000128** | **0.0000** |
| **Exact Mean** | **Mean Delta** | Both | - | **+0.000341** | **+0.000295** | **+0.000014** | **+0.000021** | **0.0000** |

## Interpretation and Decision

1. **Falsification of cardinality-conditioned choice mechanism**: Even under privileged oracle cardinality ($K^* = |Y|$), conditioning medication utilities on cardinality ($u_m(x, K)$) changes predictive ranking by a negligible $+0.000341$ Jaccard (+0.034%) under the primary exact formulation. This is an order of magnitude below the pre-registered mechanism gate threshold ($+0.004000$). Per the frozen protocol, a mean oracle-K delta $\le +0.002$ triggers unconditional termination (`KILL_ECRC_CHOICE_MECHANISM`).
2. **Deployable value is negative**: Under native predicted-K inference, the exact candidate underperformed its matched control on average ($\Delta J = -0.000491$), with Seed B strictly negative ($\Delta J = -0.001015$). Mean candidate Jaccard ($0.531769$) fell well below the minimum anchor floor ($0.537316$).
3. **No size-head bottleneck justification for this formulation**: The pre-authorized condition for a size-head redesign was a strong oracle-K mechanism ($\Delta J > +0.004$) paired with a weak predicted-K head. Because the oracle mechanism itself is negligible (+0.00034), the size head is not the bottleneck in the tested rank-8 ECRC formulation. This falsifies the tested cardinality-conditioned re-ranking mechanism; it does not prove that every possible use of regimen cardinality is universally irrelevant.
4. **Attribution check**: Under the unregularized independent BCE formulation, the oracle delta is $+0.002683$, but deployable predicted-K delta collapses to $+0.000312$. Cardinality context does not carry robust predictive value in either formulation.
5. **Verdict**: `KILL_ECRC_CHOICE_MECHANISM`. The tested ECRC cardinality-conditioned medication-choice formulation is terminated immediately. No rank sweeps, loss-weight sweeps, size-head redesign, temperature tuning, or Test evaluation is authorized as a rescue of this formulation. Future work should treat this result as strong negative evidence against this specific mechanism, not as a permanent ban on every model that contains a cardinality variable.
