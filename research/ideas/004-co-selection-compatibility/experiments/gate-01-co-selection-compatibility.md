<!-- markdownlint-disable MD013 -->

# Gate 01 — Co-Selection Compatibility

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

Status:

`DESIGNED_NOT_EXECUTED`

This is a validation-only falsification gate. It is not a publication experiment, not a deployable routing policy, and not authorization for a new model architecture.

---

## 1. Scientific state entering Gate 01

Ideas 001--003 are closed. Their scoped negative evidence is preserved without extrapolation:

- Idea 001 did not establish incremental routing information from the preregistered active-DDI-degree/Tension route beyond frozen recommender confidence.
- Idea 002's preregistered five-bin score map induced the same ordering as `ScoreOnly` and provided zero incremental routing information.
- Idea 003's preregistered within-prescription mid-rank feature did not establish incremental routing information beyond its frozen `StrongControl`.

Substantial retrospective `Oracle - StrongControl` headroom remains on Idea 003 Audit, but Oracle uses the target. It establishes unresolved outcome heterogeneity, not target-free observability or a specific mechanism.

Idea 004 asks whether one transparent train-only medication-set relation statistic provides reproducible incremental information beyond the strongest simple score/set/popularity control.

---

## 2. Central scientific question

$$
\boxed{\begin{aligned}
&\text{Among DDI-active medications predicted by frozen MoleRec, does mean train-only}\\
&\text{frequency-corrected co-selection compatibility contain reproducible incremental}\\
&\text{false-positive routing information beyond frozen score, predicted-set size,}\\
&\text{candidate prevalence, peer-set popularity, and their predeclared score interactions?}
\end{aligned}}
$$

---

## 3. Candidate universe, revision operator, and outcome

The candidate universe is unchanged:

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\},
$$

where $\hat M_t$ is the frozen MoleRec predicted medication set at threshold `0.5`, and $d_t(m)$ is candidate $m$'s active DDI degree inside $\hat M_t$.

The revision operator is singleton deletion:

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

For $m\in\mathcal Q_t$, deletion removes at least one active DDI edge. The retrospective Pareto-beneficial outcome therefore remains

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

$M_t$ is core-owned evaluation ground truth. It is never an allowed selector feature.

---

## 4. Frozen upstream identities

Gate 01 is frozen to the qualified MoleRec Table 1 Comparison Mode baseline already used by Idea 003:

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

Private checkpoint and dataset paths remain restricted 319 state and must not enter Git.

Gate execution may identity-verify an existing complete validation-only frozen prediction payload or regenerate validation-only target-free MoleRec predictions under these identities. It must not retrain MoleRec and must not access test.

---

## 5. Train-only quantities

Use only eligible training visits under the frozen task eligibility rule. Let the eligible training-visit universe be $\mathcal T_{train}$ with size $V_{train}$.

For each medication $m$ and unordered medication pair $(m,j)$:

$$
C(m)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v],
$$

$$
C(m,j)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v\land j\in M_v].
$$

Training prevalence is

$$
p_{train}(m)=\frac{C(m)}{V_{train}}.
$$

The pair relation is empirical normalized pointwise mutual information with fixed zero/full-support boundaries:

$$
\operatorname{NPMI}_{train}(m,j)=
\begin{cases}
-1,&C(m,j)=0,\\
1,&C(m,j)=V_{train},\\
\frac{\log\frac{C(m,j)V_{train}}{C(m)C(j)}}{-\log\frac{C(m,j)}{V_{train}}},&\text{otherwise.}
\end{cases}
$$

No smoothing constant, minimum-support threshold, shrinkage coefficient, clipping rule, alternative association measure, or formula choice may be selected from Dev/Audit outcomes.

The medication prevalence table, pair-count table, and pairwise NPMI table are restricted real-data artifacts and must not be committed.

---

## 6. Exact new observable

For candidate $m\in\mathcal Q_t$ and $n_t=|\hat M_t|$:

$$
A_t(m)=\frac{1}{n_t-1}\sum_{j\in\hat M_t\setminus\{m\}}\operatorname{NPMI}_{train}(m,j).
$$

`CoSelectionCompatibility` is exactly $A_t(m)$.

The candidate universe guarantees $n_t\ge2$. Higher $A_t(m)$ means stronger average train-only frequency-corrected co-selection association with the current frozen peer set. The estimator may learn either coefficient sign on Dev.

No other medication-relation statistic is authorized.

---

## 7. Strongest simple control

Define:

$$
u=1-s_t(m),
$$

$$
c=\log(1+n_t),
$$

where $s_t(m)$ is the frozen MoleRec candidate score.

Candidate popularity uses Jeffreys-smoothed log odds only as a finite control transform:

$$
f=\log\frac{C(m)+0.5}{V_{train}-C(m)+0.5}.
$$

Peer-set popularity is the mean train-only prevalence of all other predicted medications:

$$
q_t(m)=\frac{1}{n_t-1}\sum_{j\in\hat M_t\setminus\{m\}}p_{train}(j),
$$

with finite log odds

$$
g=\log\frac{q_t(m)+\epsilon}{1-q_t(m)+\epsilon},\qquad \epsilon=\frac{0.5}{V_{train}+1}.
$$

The epsilon is fixed solely to keep the logit finite; it is not tuned.

### StrongControl

$$
x_{ctrl}=[u,c,f,g,u\cdot c,u\cdot f,u\cdot g]^T.
$$

### CoSelectionAugmented

$$
x_{aug}=[u,c,f,g,u\cdot c,u\cdot f,u\cdot g,A_t(m)]^T.
$$

`CoSelectionAugmented` differs from `StrongControl` by exactly one scientific feature, $A_t(m)$.

---

## 8. Allowed and forbidden inputs

### Allowed

- frozen current-visit MoleRec score $s_t(m)$;
- complete frozen current predicted medication set $\hat M_t$;
- predicted medication count $n_t$;
- train-only medication counts/prevalence;
- train-only medication-pair co-selection counts and frozen empirical NPMI;
- DDI graph only to reproduce $\mathcal Q_t$;
- Dev outcome labels only for fitting the two preregistered low-capacity selectors.

### Forbidden

- current target prescription membership as a selector feature;
- current outcome label as a selector feature;
- future visits or future prescriptions;
- validation-derived medication prevalence or pair statistics;
- Audit labels for fitting, formula selection, feature selection, coefficient selection, cutpoints, or hyperparameters;
- any test data, test targets, test predictions, test membership, test-derived statistics, or test diagnostics;
- Idea 001 Tension features;
- Idea 002 score-bin/geometry variants;
- Idea 003 relative-rank or cosmetic transformations;
- alternative co-selection formulas after outcome inspection;
- GNN, hypergraph, Transformer, Mamba, LLM verifier, learned ensemble, or new backbone.

---

## 9. Dev-only estimator

Both selectors use the same deterministic fixed-ridge linear probability model fit only on Dev:

$$
\min_{\beta_0,\beta}\sum_{i\in Dev}(Y^{PB}_i-\beta_0-x_i^T\beta)^2+10^{-6}\|\beta\|_2^2.
$$

- Intercept is unpenalized.
- No feature standardization.
- No cross-validation.
- No hyperparameter grid.
- No coefficient-sign constraint.
- Fitted output is a ranking risk score, not a calibrated probability.

Dev coefficients are frozen before any Audit ranking.

---

## 10. Validation Dev/Audit split

Source universe: the frozen validation patient universe used by the qualified MoleRec setting.

The repository has established a deterministic Idea-number seed convention: Ideas 001, 002, and 003 used `2001`, `2002`, and `2003`. Idea 004 therefore preregisters seed `2004`, chosen from the Idea ID before outcome inspection.

Partition algorithm:

```python
patients = sorted(patient_orders)
random.Random(2004).shuffle(patients)
mid = len(patients) // 2
dev_patients = set(patients[:mid])
audit_patients = set(patients[mid:])
```

- Split unit: patient.
- Dev/Audit are strictly patient-disjoint.
- The split is fresh relative to Ideas 001--003.
- Do not change the seed if support is weak.

### Historical validation adaptivity

Validation data already participated in route selection for Ideas 001--003. This new Audit partition is held-out route-selection evidence only. It is not untouched final-generalization evidence.

### Test isolation

Do not index test. Do not stage test. Do not predict test. Do not evaluate test. Do not use test for diagnostics.

---

## 11. Deterministic ranking and tie-breaking

### StrongControl and CoSelectionAugmented

1. fitted Dev-frozen risk score descending;
2. frozen medication score ascending;
3. medication code integer ascending;
4. `patient_order` ascending;
5. `visit_order` ascending.

### ScoreOnly diagnostic baseline

1. frozen medication score ascending;
2. medication code ascending;
3. `patient_order` ascending;
4. `visit_order` ascending.

### Oracle diagnostic

1. $Y^{PB}$ descending;
2. frozen medication score ascending;
3. medication code ascending;
4. `patient_order` ascending;
5. `visit_order` ascending.

No random tie-breaking is allowed.

---

## 12. Review budgets and metrics

Primary review budgets:

$$
B\in\{10\%,20\%\}.
$$

Secondary descriptive budget:

$$
B=30\%.
$$

The 30% budget cannot determine PASS/FAIL.

For an Audit corpus of $N$ candidate rows:

$$
k(B)=\lfloor BN\rfloor.
$$

Primary metric:

$$
\operatorname{PBYield@}B=\frac{1}{k(B)}\sum_{i=1}^{k(B)}Y^{PB}_{\pi(i)}.
$$

Primary incremental metric:

$$
\Delta_{Aug-Control}(B)=\operatorname{PBYield}_{CoSelectionAugmented}(B)-\operatorname{PBYield}_{StrongControl}(B).
$$

Diagnostics:

$$
\Delta_{Oracle-Control}(B)=\operatorname{PBYield}_{Oracle}(B)-\operatorname{PBYield}_{StrongControl}(B),
$$

$$
\Delta_{Control-Score}(B)=\operatorname{PBYield}_{StrongControl}(B)-\operatorname{PBYield}_{ScoreOnly}(B).
$$

---

## 13. Audit support requirement

Audit must satisfy all of:

1. at least 50 distinct Audit patients with one or more $Y^{PB}=1$ candidates;
2. at least 50 distinct Audit patients with one or more $Y^{PB}=0$ candidates;
3. $k(10\%)>0$ and $k(20\%)>0$.

If any condition fails:

`INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT`

Do not alter the split, seed, candidate universe, or observable.

---

## 14. Patient-clustered bootstrap

- Resampling unit: patient.
- Replicates: `1000`.
- Bootstrap seed: `1204`, preregistered by the same Idea-number convention used previously (`1203` for Idea 003).
- Interval: 95% percentile CI, `[2.5%, 97.5%]`.

Per replicate:

1. sample Audit patients with replacement;
2. include all candidate rows for each sampled patient, preserving duplicate cluster draws as separate bootstrap clusters;
3. keep train-only quantities, Dev coefficients, feature definitions, and ranking rules frozen;
4. rerank each policy within the bootstrap corpus;
5. recompute $k(B)$, yields, and paired differences.

No refitting occurs inside bootstrap.

---

## 15. Preregistered decision tree

```text
[Gate A: Audit support]
  support conditions all pass?
  NO  -> INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT
  YES -> Gate B

[Gate B: Residual retrospective headroom]
  LowerCI95(Oracle - StrongControl) > 0 at BOTH 10% and 20%?
  NO  -> STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL
  YES -> Gate C

[Gate C: Incremental co-selection information]
  LowerCI95(CoSelectionAugmented - StrongControl) > 0 at BOTH 10% and 20%?
  YES -> PASS_INCREMENTAL_CO_SELECTION_COMPATIBILITY
  NO  -> STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY
```

No 30% result, Dev coefficient, subgroup observation, unregistered statistic, or alternative formula may override this tree.

---

## 16. Authorized decision wording

### PASS

> Under the frozen MoleRec validation setting and preregistered controls, mean train-only frequency-corrected co-selection compatibility provided reproducible incremental medication-level false-positive routing information beyond frozen score, predicted-set size, candidate prevalence, peer-set popularity, and their predeclared score interactions.

### Incremental FAIL

> The preregistered one-scalar train-only co-selection-compatibility route did not establish incremental medication-level false-positive routing information beyond the frozen strongest simple control.

### No-headroom STOP

> The preregistered strongest simple control left no statistically supported residual retrospective Oracle headroom at both primary budgets on the Idea-004 Audit partition.

No wording may claim clinical safety, patient benefit, therapeutic compatibility, causal mechanism, prospective prescribing validity, untouched final generalization, universal portability, or novelty of co-prescription modeling itself.

---

## 17. No-post-hoc-rescue boundary

After Audit labels are inspected, do not:

- replace NPMI with PMI, lift, Jaccard, cosine, conditional probability, frequent-pattern support, embeddings, graph scores, or any other relation statistic;
- add support thresholds, shrinkage, clipping, bins, splines, nonlinear transforms, or extra interactions;
- change `2004`, `1204`, ridge penalty, budgets, control variables, or tie-breaks;
- add longitudinal, current-code, DDI-topology, cross-model, or learned features to rescue this Gate;
- start Gate 02 or Idea 005 automatically.

Any materially different information hypothesis requires a new CCFA selection cycle.

---

## 18. Implementation scope

Implementation remains Idea-local:

```text
research/ideas/004-co-selection-compatibility/experiments/
  run_co_selection_compatibility_gate.py
```

A small staging helper may be added only if required to regenerate/identity-verify frozen validation prediction inputs without test access.

Do not promote code to `src/medrec_research/` unless real cross-Idea reuse later exists.

Synthetic verification must cover only scientific-interpretation critical paths:

- empirical NPMI boundaries and aggregation;
- patient-disjoint deterministic split seed `2004`;
- exact control vs augmented feature vectors;
- deterministic ranking/tie-breaking;
- patient-cluster bootstrap keeps Dev fits frozen;
- forbidden test access is not part of the execution path.

Synthetic checks are harness verification, not scientific evidence.

---

## 19. Restricted and public-safe artifacts

Restricted only:

- patient/visit identifiers or membership lists;
- real candidate-level records;
- raw EHR rows;
- train prevalence/pair-count/NPMI tables;
- Prediction Records and target-bearing payloads;
- checkpoints/weights;
- private paths, host details, credentials, environment variables, raw logs.

Public-safe after formal execution and audit:

- frozen protocol;
- Idea-local runner and focused synthetic tests;
- aggregate Gate summary without identifiers;
- integrity audit;
- research decision;
- scoped Failure Memory/reusable lesson if the result warrants them;
- `docs/PLANS.md` and `Handoff.md` state updates.

---

## 20. Formal P0--P6 execution workflow

### P0 — State and protocol verification

- verify `origin/main` equals the frozen protocol commit;
- verify clean worktree;
- verify this protocol is unchanged;
- verify all frozen upstream identities;
- verify no test data/predictions are staged or accessed;
- verify 319 preflight and required environment without executing the scientific Gate.

### P1 — Implement exactly

Implement the Idea-local runner and only necessary staging helper. No redesign, formula substitution, extra feature, or architecture.

### P2 — Minimal synthetic verification

Run only focused tests that can detect a scientific-semantics implementation error listed in Section 18. Do not substitute smoke output for real evidence.

### P3 — Freeze implementation revision

Commit the exact implementation and tests. Record the implementation commit SHA. No scientific execution may precede this freeze.

### P4 — One formal validation-only 319 execution

Run exactly one formal Gate 01 on validation-only data using the frozen protocol and implementation revision. Do not run test. Do not rerun for a more favorable result.

### P5 — Independent `ccf-integrity-auditor`

Audit restricted evidence independently for source identity, train/Dev/Audit firewall, no test access, candidate-universe identity, exact observable/control implementation, deterministic split/ranking, bootstrap semantics, aggregate recomputation, and decision-tree application.

### P6 — Research decision

Apply the preregistered decision tree mechanically, write the scoped decision using Section 16 wording, update public-safe state artifacts, and stop.

`STOP` after P6. Do not begin Gate 02, Idea 005, architecture work, or test evaluation.

---

## 21. Integrity-audit requirements

The post-run audit must explicitly verify:

- frozen protocol commit and frozen implementation commit;
- MoleRec source/checkpoint/core/adapter/environment/dataset identities;
- training-only origin of medication prevalence and pair statistics;
- empirical NPMI boundary semantics;
- patient-disjoint seed-2004 Dev/Audit split;
- Audit labels never used for fitting or feature/formula selection;
- test remained untouched;
- candidate universe and singleton deletion unchanged;
- StrongControl and CoSelectionAugmented differ by exactly $A_t(m)$;
- deterministic ranking and ties;
- bootstrap seed `1204`, 1000 patient-cluster replicates, no refitting;
- all preregistered budgets and aggregate values independently recomputed;
- no fabricated or selectively omitted run;
- final verdict follows Section 15 exactly.

---

## 22. Stop boundary

This protocol authorizes design and future frozen execution of Gate 01 only. During the current ChatGPT design session, formal 319 execution is prohibited and test remains untouched.
