
# Fine-Code Stability + Relational Evidence Screen

Status: **COMPLETED / ROUTING ENFORCED: PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN**

This bounded eight-lane DEVELOPMENT round has two purposes:

1. verify whether the strong fine code-level medication-specific access signal is stable across prospective random conditions;
2. test one new architecture hypothesis: candidate-medication-conditioned cross-type clinical evidence relations.

It is not a hyperparameter sweep, not a multi-hop rescue, and does not authorize Test.

## Starting evidence

Canonical matched evidence:

~~~text
single-read:
resolution_code - resolution_visit
Delta J = +0.011536
Delta F1 = +0.010238
Delta PRAUC = +0.007785
Delta DDI = -0.005589

inside multi-hop reread:
reread_code - reread_visit
Delta J = +0.014651
Delta F1 = +0.013301
Delta PRAUC = +0.011395
Delta DDI = -0.002295
~~~

These results repeat across two computation graphs, but both use the canonical RNG convention. Random-condition stability is still unverified.

Iterative rereading is terminated:

~~~text
4-condition mean Delta J = +0.001973
positive conditions = 3/4
conditions > +0.002 = 2/4
mean Delta DDI = +0.002130
verdict = UNSTABLE_DEPTH_REREAD
~~~

No rereading rescue is authorized.

## Part A — Fine-code stability

Frozen RNG conditions:

~~~text
canonical:
torch/cuda/python = 1203
numpy = 2048

stability_1:
torch/cuda/python = 1204
numpy = 2049

stability_2:
torch/cuda/python = 1205
numpy = 2050

stability_3:
torch/cuda/python = 1206
numpy = 2051
~~~

The canonical resolution pair is consumed from the committed evidence-access portfolio and is not rerun.

Each new condition compares resolution_visit versus resolution_code with tensor-identical initialization, identical data order, optimization, checkpoint selection and threshold selection.

Strict stability requires across all four conditions:

~~~text
4 / 4 Delta J > 0
at least 3 / 4 Delta J > +0.002
mean Delta J > +0.004
mean Delta F1 >= -0.002
mean Delta PRAUC >= -0.002
mean Delta DDI <= +0.002
~~~

Pass: STABLE_FINE_CODE_ACCESS.

If all four Jaccard deltas are positive and mean Delta J > +0.002 but strict criteria fail: POSITIVE_BUT_SUBTHRESHOLD_FINE_CODE_ACCESS.

Otherwise: UNSTABLE_FINE_CODE_ACCESS.

## Part B — Relational evidence hypothesis

Scientific question:

> Is fine-code medication prediction limited by treating diagnosis, procedure and historical-medication evidence as unary signals when a medication may depend on their conjunction?

For every candidate medication m, both arms perform separate normalized reads over:

- D: all current and historical diagnosis tokens;
- P: all current and historical procedure tokens;
- H: strictly historical medication tokens.

Current medications are never input.

Medication-specific summaries are d_m, p_m and h_m. They are projected to a low-rank relation space:

~~~text
u_D = LN(A_D d_m)
u_P = LN(A_P p_m)
u_H = LN(A_H h_m)
~~~

The candidate forms:

~~~text
r_DP = u_D elementwise-multiply u_P
r_DH = u_D elementwise-multiply u_H
r_PH = u_P elementwise-multiply u_H
~~~

Because d_m and p_m are attention-weighted sums, their product is a factorized weighted aggregation over cross-type code pairs without explicit O(M N^2) enumeration.

### Matched control — unary_code

The control has exactly the same fine-code encoder, medication embeddings, three medication-specific reads, relation-space projections, normalization, final head, persistence features, parameter count and initialization.

Its relation slots use matched additive composition:

~~~text
a_DP = (u_D + u_P) / sqrt(2)
a_DH = (u_D + u_H) / sqrt(2)
a_PH = (u_P + u_H) / sqrt(2)
~~~

A pair slot is active only when both evidence fields are present.

### Candidate — relational_code

Uses multiplicative relation slots:

~~~text
r_DP = u_D * u_P
r_DH = u_D * u_H
r_PH = u_P * u_H
~~~

The scientific difference is candidate-conditioned additive/unary composition versus candidate-conditioned multiplicative conjunction.

## Closest-work boundary

Primitive novelty is not assumed.

- CSRec, JMIR Medical Informatics 2025, DOI 10.2196/74170, models heterogeneous medical-entity synergies and then produces comprehensive patient representations.
- DMGExNet, Engineering Reports 2026, DOI 10.1002/eng2.70899, models diagnosis-procedure cross-attention and then forms a patient health-status representation before medication prediction.
- Carmen, AAAI 2023, DOI 10.1609/aaai.v37i6.25861, injects patient context and medication-clinical co-occurrence context into medication molecular representation.

This screen does not claim first heterogeneous interaction, first diagnosis-procedure interaction, first medication context, or first feature interaction.

The remaining plausible distinction is narrower: cross-type clinical relations are formed after medication-specific fine-code selection, so the relation representation itself is conditioned on the candidate medication and directly serves that medication decision.

A positive screen is mechanism evidence only.

## Relational decision rule

~~~text
Delta J <= +0.002
=> KILL_RELATIONAL_EVIDENCE

+0.002 < Delta J <= +0.004
=> WEAK_RELATIONAL_EVIDENCE_STOP

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> RELATIONAL_EVIDENCE_SIGNAL

Delta J > +0.004 with guardrail failure
=> RELATIONAL_EVIDENCE_SIGNAL_WITH_COST
~~~

## Frozen DEVELOPMENT protocol

~~~text
profile: mimic-iii-canonical-131-paper-dev-v1
Train: 4,233 patients / 10,489 visits
Dev: 1,004 patients / 2,130 visits
Test: SEALED

epochs: 60
batch: 16 visits
optimizer: AdamW
lr: 1e-4
weight decay: 1e-4
betas: 0.9 / 0.999
eps: 1e-8
gradient clip: 5.0
loss: BCE + 0.05 * normalized DDI penalty

selection:
complete Dev every epoch
threshold grid 0.05 ... 0.95
joint checkpoint / threshold by patient-macro Jaccard
native-default tie-break 0.35
~~~

## GPU assignment

~~~text
GPU 0  resolution_visit_s1
GPU 1  resolution_code_s1
GPU 2  resolution_visit_s2
GPU 3  resolution_code_s2
GPU 4  resolution_visit_s3
GPU 5  resolution_code_s3
GPU 6  unary_code_canonical
GPU 7  relational_code_canonical
~~~

## Terminal routing

If fine-code access is stable and relational evidence survives cleanly:
PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN

If fine-code access is stable but relational evidence is weak/killed:
FREEZE_FINE_CODE_FOUNDATION_CONTINUE_ARCHITECTURE_SEARCH

If relational evidence has an accuracy signal with supporting cost:
QUARANTINE_RELATIONAL_SIGNAL_WITH_COST

If fine-code access is positive but below the strict stability bar:
HOLD_FINE_CODE_FOUNDATION_NO_PROMOTION

If fine-code access is unstable:
REASSESS_FINE_CODE_FOUNDATION

None authorizes Test, MIMIC-IV, paper superiority claims, or an automatic compound model.

## Terminal execution results (2026-09-18)

Executed concurrently on physical GPUs 0–7 on the 319 Execution Plane from clean worktree at revision `18ae6c89dcb6ca52137e18ebeabe36bd5a303002` on `mimic-iii-canonical-131-paper-dev-v1` (4,233 Train patients / 10,489 visits; 1,004 Dev patients / 2,130 visits; all 60 epochs completed; Test strictly sealed with `test_loaded = false`).

### Part A: Fine-Code Stability (4 Conditions)

| Condition | Source | Control Ckpt / OP (Jaccard) | Candidate Ckpt / OP (Jaccard) | $\Delta$ Jaccard | $\Delta$ F1 | $\Delta$ PR-AUC | $\Delta$ DDI Rate | $\Delta$ Avg Meds |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `canonical` | Prior Portfolio (`result.json`) | Ep 7 / 0.35 (0.535091) | Ep 5 / 0.30 (0.546626) | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | +0.4715 |
| `stability_1` | Screen Lane (`results.json`) | Ep 7 / 0.30 (0.534789) | Ep 6 / 0.30 (0.545625) | **+0.010836** | +0.009038 | +0.007899 | +0.004406 | -0.7084 |
| `stability_2` | Screen Lane (`results.json`) | Ep 8 / 0.35 (0.533419) | Ep 6 / 0.35 (0.547681) | **+0.014262** | +0.012560 | +0.008141 | +0.000820 | +0.5093 |
| `stability_3` | Screen Lane (`results.json`) | Ep 6 / 0.30 (0.535859) | Ep 5 / 0.35 (0.546163) | **+0.010303** | +0.008637 | +0.008077 | -0.006196 | -1.3872 |
| **Mean** | **4 Conditions** | — | — | **+0.011734** | **+0.010118** | **+0.007976** | **-0.001640** | **-0.2787** |

Summary Statistics:

- Positive Jaccard conditions: 4 / 4 (passes strict 4/4 requirement);
- Material Jaccard conditions ($> +0.0020$): 4 / 4 (passes strict $\ge 3/4$ requirement);
- Mean $\Delta$ Jaccard: $+0.011734$ (well above the $> +0.0040$ threshold);
- Median $\Delta$ Jaccard: $+0.011186$;
- Std $\Delta$ Jaccard: $0.001759$;
- Range: $[+0.010303, +0.014262]$;
- Mean guardrails pass: `True` (mean $\Delta \text{F1} = +0.010118 \ge -0.002$, mean $\Delta \text{PRAUC} = +0.007976 \ge -0.002$, mean $\Delta \text{DDI} = -0.001640 \le +0.0020$).

Fine-Code Stability Verdict: **`STABLE_FINE_CODE_ACCESS`**

### Part B: Relational Evidence Hypothesis

| Model Variant | Role | Trainable Params | Selected Ckpt / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Avg Med Count |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `unary_code_canonical` | Control (`unary_code`) | 1,427,080 | Ep 7 / 0.35 | 0.538877 | 0.691721 | 0.789186 | 0.075167 | 20.2265 |
| `relational_code_canonical` | Candidate (`relational_code`) | 1,427,080 | Ep 5 / 0.35 | 0.542982 | 0.695092 | 0.790317 | 0.069825 | 20.0954 |
| **Delta ($\Delta$)** | **Gain** | **0** | — | **+0.004105** | **+0.003371** | **+0.001131** | **-0.005341** | **-0.1311** |

Relational Evidence Verdict: **`RELATIONAL_EVIDENCE_SIGNAL`**

- $\Delta \text{Jaccard} = +0.004105 > +0.004000$;
- Guardrails pass: `True` ($\Delta \text{F1} = +0.003371 \ge -0.002$, $\Delta \text{PRAUC} = +0.001131 \ge -0.002$, $\Delta \text{DDI} = -0.005341 \le +0.0020$).

### Final Routing Verdict

~~~text
PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN
~~~

Fine-code evidence access is strictly stable across prospective seed conditions ($\Delta J > +0.010$ across all 4 conditions). Candidate-conditioned cross-type evidence conjunction delivers a clean $+0.004105$ Jaccard increment over matched additive composition while lowering DDI rate by over 0.5%. The mechanism is promoted to multi-seed stability screening.
