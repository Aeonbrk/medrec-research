<!-- markdownlint-disable MD013 -->

# Gate 01 — Prescription-Relative Confidence

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

Status:

`DESIGNED_NOT_EXECUTED`

This is a validation-only falsification gate. It is not a publication experiment, not a deployable routing policy, and not authorization for a new model architecture.

---

## 1. Scientific state entering Gate 01

Idea 001 is closed at authoritative commit `194daf4580ca7dfe80497ccfdce89ffcee95f46f` with `TERMINATE_CURRENT_TENSION_ROUTE`.
Idea 002 is closed at authoritative commit `2afeb34452f79ceba1e883914f5792402f3ff145` (memory: `4f1618c48e35d030038981083068b4af7f933e47`, closure correction: `e368bf2221538e0c0a0fc07b6133dfb84a4998ee`) with `STOP_NO_INCREMENTAL_SCORE_GEOMETRY`.

The preserved empirical facts are:

1. Selective routing headroom exists under the fixed singleton deletion operator ($Oracle - ScoreOnly = +38.79\%$ at 10% budget, $+40.68\%$ at 20% budget).
2. Raw MoleRec medication confidence ($s_t(m)$) is already a strong target-free baseline selector.
3. The five-bin score geometry route was 100% order-equivalent to ScoreOnly, establishing that 1D score remapping alone does not unlock the residual Oracle headroom.
4. Output-set context (the relationship between a candidate's confidence and the other medications simultaneously predicted in the same prescription) has not yet been tested under a rigorous conditional control.

Idea 003 tests whether within-prescription relative confidence position provides reproducible incremental false-positive routing information beyond a strong control.

---

## 2. Central scientific question

$$
\boxed{\begin{aligned}
&\text{Among DDI-active medications predicted by frozen MoleRec, does within-prescription} \\
&\text{relative confidence position contain reproducible incremental false-positive routing} \\
&\text{information beyond a strong simple control built from absolute medication score,} \\
&\text{predicted prescription size, and train-only medication prevalence?}
\end{aligned}}
$$

---

## 3. Candidate universe and outcome

The candidate review universe $\mathcal{Q}_t$ is identical to Ideas 001 and 002:

$$
\mathcal{Q}_t = \{m \in \hat{M}_t : d_t(m) > 0\}
$$

where $\hat{M}_t$ is the set of medications predicted by frozen MoleRec at visit $t$ (threshold 0.5), and $d_t(m)$ is the active DDI degree of medication $m$ within $\hat{M}_t$.

The revision operator is fixed singleton deletion:

$$
R_0(\hat{M}_t, m) = \hat{M}_t \setminus \{m\}
$$

Within $\mathcal{Q}_t$, deleting $m$ strictly reduces at least one active DDI edge ($\Delta V_{t,m} = -d_t(m) < 0$).
Therefore, Pareto-beneficial revision reduces to false-positive status:

$$
Y^{PB}_{t,m} = \mathbf{1}[m \notin M_t]
$$

where $M_t$ is the target-bearing core-owned ground-truth medication set.
$M_t$ is evaluation-only ground truth and is **never** an allowed prediction-time feature.

---

## 4. Frozen upstream identities

The scientific setting is frozen to the qualified MoleRec Table 1 Comparison Mode baseline:

- `model_source_revision`: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
- `checkpoint_sha256`: `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
- `baseline_core_sha256`: `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511`
- `adapter_sha256`: `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531`
- `baseline_environment_name`: `medrec-molerec-table1`
- `baseline_environment_sha256`: `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda`
- `dataset_id`: `molerec-table1-comparison-v1-1`
- `dataset_manifest_sha256`: `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712`
- `snapshot_id`: `molerec-table1-c721-www23`
- `snapshot_sha256`: `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58`
- `medication_vocabulary_sha256`: `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08`
- `ddi_asset_sha256`: `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7`
- `feature_availability_sha256`: `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9`

The checkpoint private path is restricted 319 state. It is resolved from existing accepted run provenance and verified by `checkpoint_sha256`. The private path must never be committed to Git.

### Full predicted prescription requirement

Candidate JSONL corpora from Ideas 001 and 002 retain only each DDI-active candidate's own scalar score.
Idea 003 requires the **complete same-visit predicted medication set** $\hat{M}_t$ and its frozen vocabulary scores $s_t$.
Therefore, formal execution regenerates validation-only target-free MoleRec prediction payloads under the frozen identity above.
This is inference only; MoleRec is never retrained.

---

## 5. Exact new observable: Prescription-Relative Confidence

Let $n_t = |\hat{M}_t|$ be the number of medications in the predicted prescription at visit $t$.
Because candidate $m \in \mathcal{Q}_t$ requires $d_t(m) > 0$, there is at least one active DDI pair in $\hat{M}_t$, guaranteeing $n_t \ge 2$.

The within-prescription relative confidence position is defined by normalized mid-rank:

$$
r_t(m) = \frac{|\{j \in \hat{M}_t : s_t(j) > s_t(m)\}| + 0.5 \cdot |\{j \in \hat{M}_t \setminus \{m\} : s_t(j) == s_t(m)\}|}{n_t - 1}
$$

Properties:

- $r_t(m) \in [0, 1]$.
- Higher $r_t(m)$ means lower relative confidence (more co-predicted medications outrank $m$ within the same prescription).
- If $m$ has the uniquely highest score in $\hat{M}_t$, $r_t(m) = 0$.
- If $m$ has the uniquely lowest score in $\hat{M}_t$, $r_t(m) = 1$.
- Exact frozen floating-point equality (`==`) defines score ties. No arbitrary $\epsilon$ is introduced.

---

## 6. Train-only medication prevalence

Prevalence is computed strictly on the training split.
Only eligible training visits with at least one previous visit are counted, matching the prediction-task eligibility rule.

Let:

- $C_{train}(m)$ = number of eligible training visits whose ground-truth target medication set contains $m$.
- $V_{train}$ = total number of eligible training visits.

The smoothed train-only prevalence is frozen as:

$$
p_{train}(m) = \frac{C_{train}(m) + 1}{V_{train} + 2}
$$

The per-medication prevalence table is restricted research data; it must not be committed to Git.

---

## 7. Input boundary

### Allowed selector inputs

- Frozen current-visit MoleRec medication score $s_t(m)$.
- Complete current frozen predicted medication set $\hat{M}_t$.
- Complete current same-visit frozen medication scores $\{s_t(j) : j \in \hat{M}_t\}$.
- Predicted medication count $n_t = |\hat{M}_t|$.
- Frozen train-only medication prevalence $p_{train}(m)$.
- DDI graph (used only to construct the candidate universe $\mathcal{Q}_t$).

### Forbidden selector inputs

- Current target prescription membership ($M_t$).
- Current outcome label ($Y^{PB}$) as a prediction-time feature.
- Future visits or future prescriptions.
- Audit labels for fitting or threshold selection.
- Test data or test predictions (unindexed and untouched).
- Idea 001 Tension features.
- New DDI graph topological features.
- Longitudinal patient history features.
- Co-selection statistics.
- Cross-backbone predictions.
- New learned representations or neural architectures.

---

## 8. Models: StrongControl vs. RankAugmented

For each candidate $m \in \mathcal{Q}_t$, define three base variables:

$$
\begin{aligned}
u &= 1 - s_t(m) \\
c &= \log(1 + n_t) \\
f &= \log\left(\frac{p_{train}(m)}{1 - p_{train}(m)}\right)
\end{aligned}
$$

### StrongControl feature vector

$$
x_{ctrl} = [u,\ c,\ f,\ u \cdot c,\ u \cdot f]^T \in \mathbb{R}^5
$$

### RankAugmented feature vector

$$
x_{rank} = [u,\ c,\ f,\ u \cdot c,\ u \cdot f,\ r_t(m)]^T \in \mathbb{R}^6
$$

`RankAugmented` differs from `StrongControl` by **exactly the single observable $r_t(m)$**.

---

## 9. Dev-only estimator

Both models use the identical deterministic fixed-ridge linear probability estimator fit strictly on the Dev partition:

$$
\min_{\beta_0, \beta} \sum_{i \in \text{Dev}} \left(Y^{PB}_i - \beta_0 - x_i^T \beta\right)^2 + \lambda \|\beta\|^2
$$

with:

- $\lambda = 10^{-6}$ (ridge penalty on slope vector $\beta$ only; intercept $\beta_0$ is unpenalized).
- No feature standardization.
- No cross-validation, no hyperparameter grid, no tuning.
- The fitted output $\hat{y} = \hat{\beta}_0 + x^T \hat{\beta}$ is a ranking risk score, not a calibrated probability.

Dev coefficients are frozen before Audit candidate ranking.

---

## 10. Split discipline

### Source universe

Validation patient universe `patient_order` $0 \dots 1058$ (1,059 patients).

### Partitioning algorithm

```python
patients = sorted(patient_orders)
random.Random(2003).shuffle(patients)
dev_patients = set(patients[:529])  # floor(1059 / 2) = 529 patients
audit_patients = set(patients[529:])  # remaining 530 patients
```

- Seed: `2003` (fixed before outcome inspection).
- Partitioning is strictly patient-disjoint ($Dev \cap Audit = \emptyset$).
- Independent of Idea 001 and Idea 002 partitions.

### Test split isolation

The test split must remain completely untouched:
Do not index it. Do not stage it. Do not predict it. Do not evaluate it. Do not use it for diagnostics.

---

## 11. Deterministic ranking and tie-breaking

Candidates in the Audit partition are ranked by the following deterministic rules:

### StrongControl and RankAugmented

1. Fitted linear risk $\hat{y}$ descending (`reverse=True`).
2. Frozen medication score $s_t(m)$ ascending (`reverse=False`).
3. Medication code integer ascending (`reverse=False`).
4. `patient_order` integer ascending (`reverse=False`).
5. `visit_order` integer ascending (`reverse=False`).

### ScoreOnly baseline

1. Frozen medication score $s_t(m)$ ascending (`reverse=False`).
2. Medication code integer ascending (`reverse=False`).
3. `patient_order` integer ascending (`reverse=False`).
4. `visit_order` integer ascending (`reverse=False`).

### Oracle diagnostic

1. Ground-truth $Y^{PB}_{t,m}$ descending (`reverse=True`).
2. Frozen medication score $s_t(m)$ ascending (`reverse=False`).
3. Medication code integer ascending (`reverse=False`).
4. `patient_order` integer ascending (`reverse=False`).
5. `visit_order` integer ascending (`reverse=False`).

---

## 12. Review budgets and evaluation metrics

### Budgets

- Primary budgets: $B \in \{10\%, 20\%\}$.
- Secondary descriptive budget: $B = 30\%$.

The candidate budget count is:

$$
k(B) = \lfloor B \cdot N_{\text{AuditCandidates}} \rfloor
$$

The 30% secondary budget cannot determine PASS/FAIL.

### Metrics

$$
\text{PBYield@}B = \frac{\sum_{i=1}^{k(B)} Y^{PB}_{\pi(i)}}{k(B)}
$$

Primary incremental metric:

$$
\Delta_{\text{Rank-Control}}(B) = \text{PBYield}_{\text{RankAugmented}}(B) - \text{PBYield}_{\text{StrongControl}}(B)
$$

Diagnostic headroom metrics:

$$
\begin{aligned}
\Delta_{\text{Oracle-Control}}(B) &= \text{PBYield}_{\text{Oracle}}(B) - \text{PBYield}_{\text{StrongControl}}(B) \\
\Delta_{\text{Control-Score}}(B) &= \text{PBYield}_{\text{StrongControl}}(B) - \text{PBYield}_{\text{ScoreOnly}}(B)
\end{aligned}
$$

---

## 13. Audit support rule

The Audit partition must satisfy all of the following:

1. $\ge 50$ distinct Audit patients having at least one $Y^{PB} = 1$ candidate.
2. $\ge 50$ distinct Audit patients having at least one $Y^{PB} = 0$ candidate.
3. $k(10\%) > 0$ and $k(20\%) > 0$.

If any support condition fails:

$$
\text{Verdict} = \texttt{INCONCLUSIVE\_INSUFFICIENT\_AUDIT\_SUPPORT}
$$

Do not alter the split or seed.

---

## 14. Clustered bootstrap inference

- Resampling unit: **Patient** (cluster bootstrap).
- Replicates: $1,000$.
- Random seed: `1203`.
- Confidence interval: 95% percentile interval ($[2.5\%, 97.5\%]$).

Procedure per replicate:

1. Sample Audit patients with replacement.
2. Form the pseudo-audit corpus by including all candidate rows of the drawn patients (duplicated draws remain distinct clusters).
3. Keep Dev-fitted coefficients, feature definitions, and train prevalence **frozen** (no refitting inside bootstrap).
4. Re-rank under each policy, compute $k(B)$, evaluate yields, and evaluate paired differences.

---

## 15. Preregistered decision tree

```text
[Gate A: Support]
  Audit distinct Y_PB=1 patients >= 50 AND Audit distinct Y_PB=0 patients >= 50?
  NO  --> INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT
  YES --> proceed to Gate B

[Gate B: Residual Oracle Headroom]
  LowerCI95(Oracle - StrongControl) > 0 at BOTH 10% and 20% budgets?
  NO  --> STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL
  YES --> proceed to Gate C

[Gate C: Incremental Relative Confidence Signal]
  LowerCI95(RankAugmented - StrongControl) > 0 at BOTH 10% and 20% budgets?
  YES --> PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE
  NO  --> STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE
```

No 30% result, regression coefficient p-value, subgroup finding, or post-hoc alteration may override this tree.

---

## 16. Authorized decision wording

### PASS wording

> "Under the frozen MoleRec validation setting and preregistered controls, within-prescription relative confidence position provided reproducible incremental medication-level false-positive routing information beyond absolute score, predicted prescription size, and train-only medication prevalence."

Do not claim clinical safety, patient benefit, causality, final generalization, optimality, or cross-backbone portability.

### FAIL wording

For incremental failure (`STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`):

> "The preregistered one-scalar prescription-relative-confidence route did not establish incremental routing information beyond the frozen strong control."

Do not claim that all output-set context is useless.

For no residual headroom (`STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL`):

> "The preregistered strong control left no statistically supported residual Oracle headroom at both primary budgets on the Idea-003 Audit partition."

Do not misreport this as a relative-rank falsification.

---

## 17. Historical validation adaptivity notice

Ideas 001 and 002 already used validation data for route selection.
Idea 003 Audit is valid held-out route-selection evidence under a fresh patient partition.
It is **not** untouched final-generalization evidence.
The test split remains unindexed, unpredicted, and untouched.

---

## 18. Scope boundaries and post-hoc prohibitions

After Audit outcomes are generated, the following are strictly prohibited:

- Adding rank margins, rank bins, non-linear splines, interaction expansions, or GNN/LLM/Transformer selectors.
- Modifying regularization $\lambda$, the split seed (`2003`), or bootstrap seed (`1203`).
- Shifting review budgets or post-hoc thresholding.
- Adding historical, DDI graph topological, or co-selection features.

Any modification to these boundaries requires a new formal idea or gate preregistration.
