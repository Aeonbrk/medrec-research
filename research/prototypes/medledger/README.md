# MedLedger: Independent vs Normalized Evidence Aggregation

MedLedger is a bounded mechanism screen on the MIMIC-III canonical-131 Dev profile.
It addresses one scientific question:

> After medication-specific evidence reading has been established, should multiple medication-specific evidence units accumulate independently, or should they compete for normalized relevance mass?

## Mechanism Hypothesis

Both arms construct identical target-free clinical evidence tokens:

- Current diagnosis singleton bags (type 1, lag 0)
- Current procedure singleton bags (type 2, lag 0)
- Historical diagnosis, procedure, and medication summary bags (types 3, 4, 5, lag > 0)
- NULL token (type 0, lag 0)
- Sinusoidal temporal lag encodings

Both pass these tokens through the same medication-independent 2-layer clinical Transformer contextualizer ($H = T(X)$).
For medication $m$ and evidence token $k$:

```text
u_mk = GELU(W_h h_k + W_e e_m + W_x (h_k ⊙ e_m) + b)
r_mk = w_r^T u_mk
a_mk = tanh(w_a^T u_mk)
```

Both arms share the exact same explicit count nuisance path:

```text
q(X) = [log1p(num_current_dx), log1p(num_current_proc), log1p(num_history_visits)]
eta_m = v_m^T q(X)    (v initialized to 0)
```

And the final logit:

```text
z_m = prevalence_bias_m + eta_m + softplus(tau) * A_m
```

### Full Arm: MedLedger

Relevance gating is independent across evidence items:

```text
g_mk = sigmoid(r_mk)
c_mk = g_mk * a_mk
```

$\sum_k g_{mk}$ is unconstrained. Multiple evidence items can reinforce each other without penalty.

### Matched Control: NormalizedLedger

Evidence units compete for normalized relevance mass:

```text
alpha_mk = softmax_k(r_mk)
c_mk = alpha_mk * a_mk
```

$\sum_{k \text{ valid}} \alpha_{mk} = 1.0$. Evidence units compete in a zero-sum allocation.

### Common Aggregation

Both arms use identical signed log1p accumulation:

```text
S_pos_m = sum_k relu(c_mk)
S_neg_m = sum_k relu(-c_mk)
A_m = log1p(S_pos_m) - log1p(S_neg_m)
```

## Frozen Experimental Protocol

- **Dataset**: MIMIC-III canonical-131 (`mimic-iii-canonical-131-paper-dev-v1`)
- **Split**: Train (4,233 patients, 10,489 visits) / Dev (1,004 patients, 2,130 visits). Test sealed.
- **Seed**: `20260920`
- **Training**: 60 complete epochs, batch size 16, AdamW, lr = `3e-4`, weight decay = `1e-4`, gradient clip = 5.0, float32.
- **Objective**: Mean `BCEWithLogits` across 131 medications. No auxiliary or DDI losses.
- **Selection**: Joint Dev patient-macro Jaccard over 60 epochs and 19 operating thresholds `[0.05, 0.10, ..., 0.95]`, tie-broken towards native default `0.35`.

## Frozen Decision Rule

```text
ΔJ = Jaccard(MedLedger) - Jaccard(NormalizedLedger)

ΔJ <= +0.002:
    KILL mechanism
+0.002 < ΔJ <= +0.004:
    WEAK signal (do not promote by default)
ΔJ > +0.004:
    MEANINGFUL mechanism signal
ΔJ >= +0.008:
    STRONG signal (reconsider as architecture candidate)
```

## Screen Evidence and Status

> **Caveat**: This is **NOT** a completed 60-epoch protocol result. Both training arms were terminated early after consistent negative Dev trajectory through 51–54 completed epochs.

### Mid-Run Dev Checkpoint Summary (51/60 epochs observed)

| Arm | Mechanism | Selected Epoch | Selected Threshold | Dev Patient-Macro Jaccard |
| --- | --- | ---: | ---: | ---: |
| **MedLedger** (Full) | Independent Sigmoid ($g_{mk}$) | 4 | 0.35 | 0.5347 |
| **NormalizedLedger** (Control) | Softmax Competition ($\alpha_{mk}$) | 5 | 0.30 | 0.5389 |
| **Delta** | Full − Control | − | − | **−0.0042** |

### Decision

- **Status**: `TERMINATED_EARLY_NEGATIVE`
- **Verdict**: `KILL_MEDLEDGER_FAMILY_FOR_FURTHER_RESCUE`
- **Core Scientific Conclusion**: Independent evidence accumulation failed to outperform normalized evidence competition on the canonical MIMIC-III Dev surface ($\Delta J \approx -0.0042$). The hypothesis that removing softmax competition over evidence tokens yields predictive gains is falsified in this formulation.
- **Rule Enforcement**: No MedLedger-v2, no gate-temperature rescue, no alternative saturation, no extra seeds, and no diagnostic expansion.
