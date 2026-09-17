# Drug-Conditioned Precedent Memory (DCPM) vs SharedPrecedent

Drug-Conditioned Precedent Memory (DCPM) is a bounded mechanism screen on the canonical MIMIC-III Dev profile (`mimic-iii-canonical-131-paper-dev-v1`).

It addresses one central scientific question:

> Does candidate-medication-specific relevance over cross-patient Train precedents improve prediction over one shared patient-level precedent weighting, when both arms receive identical local evidence, memory cases, peer labels, parameters, and optimization?

## Shared Foundation

Both arms share:

- Legal target-free clinical encoder reused from MICA/DrugQuery ($d=128$, two clinical attention blocks).
- Input packing: current diagnoses (type 1, lag 0), current procedures (type 2, lag 0), historical summary bags (types 3, 4, 5, lag > 0), NULL token (type 0, lag 0), sinusoidal temporal lag encodings.
- Shared patient state $h_i \in \mathbb{R}^{128}$ via masked mean pooling over assembled clinical tokens.
- DrugQuery local read $l_{im} \in \mathbb{R}^{128}$ via chunked attention pooling conditioned on candidate medication embedding $d_m \in \mathbb{R}^{128}$.
- Train memory containing target-free patient states $h_j$ and Train medication labels $y_j$.
- Dev memory is strictly Train-only.
- Same-patient memory visit exclusion during Train: for query visit $i$, every visit from the same patient is strictly masked out.
- Common coarse peer pool $C_i$ of $L=256$ constructed strictly from legal target-free clinical inputs (TF-IDF cosine similarity over diagnoses, procedures, and history codes) and never from current target medications.
- Common Precedent Memory modules: $W_h, W_l, W_d, \text{LN}_q, W_k, \text{LN}_k, W_v$, precedent MLP, and head.
- Exact parameter-count equality.

## Mechanism Contrast

### Full Arm: DCPM (Drug-Conditioned Precedent Memory)

For candidate medication $m$ and peer $j \in C_i$:

```text
q_im = LN(W_h h_i + W_l l_im + W_d d_m)
s_ijm = (q_im^T LN(W_k h_j)) / sqrt(128)
beta_ijm = softmax_j(s_ijm),  j in C_i
```

Precedent relevance weights $\beta_{ijm}$ are specific to each candidate medication $m$.

### Matched Control: SharedPrecedent

Replaces medication-specific inputs with patient-level averages across medications:

```text
l_bar_i = mean_m(l_im)
d_bar = mean_m(d_m)
q_i = LN(W_h h_i + W_l l_bar_i + W_d d_bar)
s_ij = (q_i^T LN(W_k h_j)) / sqrt(128)
beta_ij = softmax_j(s_ij),  j in C_i
```

Uses the identical peer weights $\beta_{ijm} = \beta_{ij}$ for every medication.

### Common Readout & Head

Both arms construct:

```text
pi+_im = sum_{j in C_i} beta_ijm y_jm
mu+_im = weighted mean W_v h_j over y_jm=1
mu-_im = weighted mean W_v h_j over y_jm=0
r_im = MLP([mu+_im, mu-_im, mu+_im - mu-_im, pi+_im])
```

And evaluate the identical prediction head:

```text
head([l_im, d_m, r_im, l_im * d_m]) -> z_im
```

## Frozen Experimental Protocol

- **Benchmark Profile**: `mimic-iii-canonical-131-paper-dev-v1`
- **Split**: Train (4,233 patients, 10,489 visits) / Dev (1,004 patients, 2,130 visits). Test sealed.
- **Seed**: `20260921`
- **Horizon**: 60 complete epochs, batch size 16.
- **Optimizer**: AdamW, lr `3e-4`, weight decay `1e-4`, gradient clip `5.0`.
- **Policy**: float32 deterministic CUDA numeric policy.
- **Loss**: MICA BCE + 0.05 normalized DDI only (no auxiliary ranking/retrieval loss).
- **Selection**: Joint Dev checkpoint + threshold selection over 19 operating points `[0.05, 0.10, ..., 0.95]`, tie-broken towards native default `0.35`. Primary metric: patient-macro Jaccard.

## Frozen Decision Rule

```text
Primary delta: ΔJ = Jaccard(DCPM) - Jaccard(SharedPrecedent)

ΔJ > +0.004:
    MEANINGFUL mechanism signal
ΔJ ~ +0.010 (>= +0.008):
    STRONG mechanism signal
ΔJ <= +0.002:
    KILL mechanism

Safety override:
Accept genuine ~-0.010 DDI improvement with J loss <= 0.005,
provided medication count does not explain it.

Enforcement:
No DCPM-v2, K search, temperature search, extra loss, or extra seed
if the mechanism is negative.
```

## Empirical Results

Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seed `20260921`, 60 complete epochs, 319 NVIDIA RTX 3090):

| Metric | SharedPrecedent (Control) | DCPM (Candidate-Conditioned) | Delta (DCPM - Control) |
| :--- | :--- | :--- | :--- |
| **Dev Jaccard (Primary)** | **0.543606** | 0.542203 | **-0.001403** |
| Dev F1 | 0.696129 | 0.694874 | -0.001255 |
| Dev PR-AUC | 0.792335 | 0.792684 | +0.000349 |
| Dev DDI Rate | 0.072298 | 0.074479 | +0.002181 |
| Dev Avg Med Count | 19.9901 | 21.9982 | +2.008113 |
| Selected Checkpoint | Epoch 3 @ threshold 0.40 | Epoch 3 @ threshold 0.35 | - |
| Parameter Count | 1,079,428 | 1,079,428 | 0 (exact match) |
| Test Access | None (Dev only) | None (Dev only) | - |

## Verdict and Decision

```text
VERDICT: KILL_DCPM_MECHANISM
REASON: ΔJ = -0.001403 <= +0.002: drug-conditioned precedent relevance falsified
```

### Scientific Takeaways

1. **Precedent relevance is patient-level, not drug-level**: Conditioning precedent retrieval queries on individual candidate medications ($q_{im}$) yielded no predictive gain ($\Delta J = -0.001403$) compared to a single shared patient-level precedent query ($q_i$).
2. **Safety did not improve**: DDI rate slightly increased (+0.002181) alongside higher average prescription count (+2.008 medications/visit), ruling out any safety override.
3. **Strict Protocol Compliance**: No post-hoc hyperparameter search, no K/temperature tuning, no auxiliary loss addition, and zero Test set access. Per the frozen research boundary, the DCPM mechanism is terminated without iteration.
