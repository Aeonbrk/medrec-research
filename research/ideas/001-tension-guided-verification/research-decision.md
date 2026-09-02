<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 001 Tension-Guided Verification

- **Idea**: `001-tension-guided-verification`
- **Decision date**: 2026-09-02
- **Decision Stage**: P6 — Final Research Decision
- **Lifecycle Transition**: `TERMINATE_CURRENT_TENSION_ROUTE`
- **Gate 03 Authorization**: `NOT_AUTHORIZED`
- **Residual Headroom Status**: `UNRESOLVED_RESEARCH_OPPORTUNITY`
- **Next CCFA Owner**: `ccf-idea-optimizer` / Research Operator (Ideation Stage)

---

## 1. Evidence Inputs

This decision is governed exclusively by the frozen, independently audited experimental evidence lifecycle:

1. **Gate 01 Preregistration Protocol**:
   [`gate-01-routing-opportunity.md`](experiments/gate-01-routing-opportunity.md)
2. **Gate 01 Formal Public Summary**:
   [`gate-summary.json`](experiments/gate-summary.json)
   - Formal run: `gate-01-routing-opportunity-20260902-010537` on `319-wild`
   - Harness revision: `c6fc35bce97637a2eddc6319cdec768256abdccb`
3. **Gate 01 Integrity Audit**:
   [`gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md)
   - Audit Status: `P0 Status: AUDIT_PASS`
   - Row-level invariant check: 15,549 rows verified, 0 invariant failures, exact numeric reproduction.
4. **Gate 02 Preregistration Protocol**:
   [`gate-02-confidence-sufficiency.md`](experiments/gate-02-confidence-sufficiency.md)
5. **Gate 02 Formal Public Summary**:
   [`gate-02-summary.json`](experiments/gate-02-summary.json)
   - Formal run: `gate-02-confidence-sufficiency-20260902-155433` on `319-wild`
   - Harness revision: `ef40f288fbf64f499d3f9967a7b2783ee3fe090b`
   - Public-result commit: `91642f3f49229f3bba82295298a36d9d33540915`
   - Checkpoint SHA256: `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
   - Summary SHA256: `9f0e54ff484de7e935f62300e5a0016ed2042eb052ae8dcb86b2f7c3bd844e28`
6. **Gate 02 Integrity Audit**:
   [`gate-02-integrity-audit.md`](experiments/gate-02-integrity-audit.md)
   - Audit Status: `P5 Status: INTEGRITY_PASS`
   - Row-level invariant check: 15,549 rows verified, 0 partition leaks, exact numeric reproduction.

---

## 2. Gate 01 Audited State

```text
Gate 01 verdict: pass
P0 Status: AUDIT_PASS
```

### Empirical Meaning

Under the frozen MoleRec validation setting, candidate review universe $\mathcal Q$ ($d_t(m) > 0$), and singleton deletion operator $R_0(\hat M_t, m) = \hat M_t \setminus \{m\}$:

- Base prevalence of Pareto-beneficial revisions is **31.67%** (Random policy).
- Simple DDI-degree sorting (RiskOnly) achieves **37.07%** (10% budget) and **35.64%** (20% budget).
- The retrospective Oracle policy achieves **100.0%** Pareto-beneficial yield across all budget tiers.
- Oracle vs Random headroom: **+68.33%** (95% CI: [67.33%, 69.38%]).
- Oracle vs RiskOnly headroom: **+62.93%** at 10% (95% CI: [59.88%, 65.61%]), **+64.36%** at 20% (95% CI: [62.18%, 66.74%]).
- Beneficial patient support: 844 patients ($\gg 50$ required threshold).

### Boundary

Gate 01 established that selective routing opportunity / Oracle headroom exists under $R_0$. It did **not** establish that decision tension is the mechanism capturing that headroom.

---

## 3. Gate 02 Audited State

```text
Formal Gate 02 verdict: STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL
P5 Status: INTEGRITY_PASS
```

### Empirical Findings

Evaluated on the 7,959 Audit-partition candidates across 428 eligible patients (disjoint from the 430-patient Dev partition):

1. **Recommender confidence is a strong simple predictor**:
   - Random: **31.03%**
   - RiskOnly: **36.48%** (10% budget), **35.76%** (20% budget), **33.43%** (30% budget)
   - ScoreOnly: **61.13%** (10% budget), **58.52%** (20% budget), **55.26%** (30% budget)
   - Score - Random: **+30.10%** at 10% (95% CI: [26.77%, 33.23%])
   - Score - RiskOnly: **+24.65%** at 10% (95% CI: [19.59%, 29.33%])
2. **Current preregistered DDI-pressure explanation failed**:
   - Dev parameter selection over 13 candidate grid values chose $\lambda^* = 0.0$.
   - On the Audit partition, Scalar ($\lambda^* = 0.0$) reduced identically to ScoreOnly:
     $$\text{Scalar} - \text{ScoreOnly} = 0.0\% \quad (95\%\ \text{CI: } [0.0\%, 0.0\%]) \quad \text{across all budgets}.$$
   - Preregistered support-pressure interaction diagnostic:
     $$I_{\text{Tension}} = (p_{HH} - p_{HL}) - (p_{LH} - p_{LL}) = -0.005237 \quad (95\%\ \text{CI: } [-0.04575, +0.03645]).$$
     The confidence interval contains zero and spans negative values, providing no supported positive interaction evidence.
3. **Residual Oracle headroom survives**:
   - Oracle - ScoreOnly at 10% budget: **+38.87%** (95% CI: [35.43%, 42.61%])
   - Oracle - ScoreOnly at 20% budget: **+41.48%** (95% CI: [39.00%, 44.40%])
   - Recommender confidence does not exhaust the routing headroom under $R_0$.

---

## 4. Final Route Decision

```text
Decision: TERMINATE_CURRENT_TENSION_ROUTE
Gate 03 Authorization: NOT_AUTHORIZED
```

### Scientific Meaning

> Under the frozen MoleRec validation setting, fixed candidate universe, fixed singleton revision operator $R_0$, frozen recommender confidence signal, preregistered global DDI-degree scalar control, and preregistered support-pressure interaction diagnostic, the current Tension hypothesis route did not establish incremental constraint-pressure signal beyond MoleRec confidence.

### Enforcement of the Stop Rule

Per the preregistered decision rule (§8 of `gate-02-confidence-sufficiency.md`), the leaf `STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL` mandates an immediate and unconditional stop of the Tension route:

- No Gate 03 is authorized under Idea 001.
- No model training or architecture scaling is permitted.
- Post-hoc rescue attempts—including changing lambda grids, revising score thresholds, re-binning interaction groups, transforming DDI degree, or seeking alternative constraint features after seeing negative results—are strictly prohibited.

---

## 5. Supported Conclusions

The following conclusions are grounded in the audited empirical records:

1. **Selective routing opportunity exists under $R_0$**: Substantial heterogeneity and headroom exist in retrospective candidate revisions over trivial baselines (Gate 01: Oracle yield 100%, +68.33% over Random).
2. **Recommender confidence is an effective simple selector**: The base recommender's own output probability (`ScoreOnly`) captures substantial false-positive ranking structure (+30.10% over Random at 10% budget).
3. **The preregistered Tension mechanism failed**: Adding external constraint pressure via the preregistered global additive DDI scalar or interaction diagnostic yielded zero incremental predictive signal over recommender confidence.
4. **Residual routing headroom is preserved**: Oracle allocation outperforms ScoreOnly by +38.87% to +41.48%, demonstrating that recommender confidence explains only part of the retrospective revision opportunity.

---

## 6. Unsupported Conclusions (Strictly Forbidden Claims)

To maintain scientific integrity, the following claims are explicitly barred from repository records, manuscripts, or presentations:

- **Do NOT claim Tension is universally false**: The failure is scoped to the preregistered formulation, frozen MoleRec checkpoint, and singleton operator $R_0$.
- **Do NOT claim DDI information can never help**: The experiment tested specific representations (active DDI degree scalar and high/low support-pressure bins) in retrospective singleton deletion.
- **Do NOT claim every DDI-derived representation or graph structure is useless**.
- **Do NOT claim every conceivable nonlinear interaction has been disproven**.
- **Do NOT claim no observable signal can explain residual Oracle headroom**.
- **Do NOT claim ScoreOnly solves the routing problem or is a finished clinical policy**: ScoreOnly remains a retrospective ranking control on validation data.
- **Do NOT claim Oracle headroom is clinically actionable**.
- **Do NOT make clinical safety, efficacy, patient benefit, or causal claims**: Retrospective Jaccard changes and DDI violation counts under synthetic $R_0$ deletion do not measure real patient outcomes.

---

## 7. Residual Open Question

```text
Status: UNRESOLVED_RESEARCH_OPPORTUNITY
```

The residual Oracle headroom is preserved as an empirical observation without an assigned mechanism:

$$
\boxed{
\text{What target-free observable information explains residual revision-value heterogeneity beyond frozen recommender confidence?}
}
$$

### Explicit Boundary

- Frozen MoleRec medication confidence explains a substantial portion of candidate false-positive ranking structure, but does not exhaust the Oracle allocation headroom under $R_0$.
- **No speculative mechanism may be attributed to this residual headroom**. It must not be presumed to originate from richer DDI graphs, clinical diagnoses, procedures, patient longitudinal history, latent embeddings, epistemic uncertainty, probability calibration, causal structure, LLM reasoning, or alternative selector architectures without independent, preregistered empirical proof.

---

## 8. Boundary Between Route Closure and a Future Idea

- This decision formally **closes** the current Tension route under Idea 001.
- Future investigation into the residual open question must be initiated as a **new research Idea** with a distinct problem formulation, independent hypothesis, and fresh preregistration.
- Future work must not be treated as a continuation or "Gate 03" of the failed Tension route.
- Any future line of inquiry must restart from first principles and adhere to strongest-simple-control discipline from inception.

---

## 9. Revisit Conditions

The current route may only be reopened if there is a **materially different scientific basis**, such as:

- A genuinely different problem formulation (not singleton retrospective deletion $R_0$).
- A fundamentally different external evidence source or constraint definition.
- A new theoretical hypothesis with distinct causal assumptions.
- Different candidate universe or revision action semantics.
- A different model family or baseline regime.

### Prohibited Post-Hoc Adjustments

The following do **not** constitute sufficient justification to reopen or revise the current route:

- Altering the $\lambda$ search grid or range.
- Modifying budget thresholds (e.g. 5%, 15%, 25%).
- Adjusting score cutoff thresholds or quantile binning rules.
- Applying alternative nonlinear or logarithmic transforms to DDI degree.
- Adjusting random seeds or split ratios.
- Introducing complex selector networks (MLPs, GNNs) on the same feature set.

---

## 10. Next Owner & Stage Handoff

```text
Next CCFA Owner: ccf-idea-optimizer / Research Operator
Stage: Research Ideation / Problem Formulation
```

- **Not authorized for `ccf-paper-writer`**: Idea 001 is a negative route closure, not a positive method contribution ready for manuscript drafting.
- **Not authorized for implementation or training**: No engineering or GPU training workflows may be dispatched under Idea 001.
- The next step is for the research operator to evaluate whether to formulate a new research question around the unresolved opportunity from first principles.
