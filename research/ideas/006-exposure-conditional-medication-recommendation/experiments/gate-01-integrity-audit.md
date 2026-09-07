# Gate 01 Integrity Audit Report — Idea 006

- **Audited Stage**: `IDEA_006_GATE_01`
- **Audited Artifacts**:
  - `gate01_freeze_manifest.json`
  - `gate-01-summary.json`
  - `gate-01-decision.md`
- **Execution Seed**: `260907`
- **Pre-Dev Freeze Manifest SHA256**: `c7d5d7d19640e2aafdb41b98bdf58d4092cb82d4ddb44ae105450385813775c9`
- **Final Verdict**: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`
- **Audit Date**: 2026-09-08
- **Audit Verdict**: `INTEGRITY_AUDIT_PASS`

---

## 1. Quarantine & Non-Leakage Audit

1. **R0 Holdout Split Quarantine**:
   - `R0 Holdout` was strictly preserved in quarantine.
   - Zero patient records, order events, active-regimen states, or target vectors from `R0 Holdout` were read, loaded, or evaluated during Gate 01 execution.
2. **Existing Project Test Split Quarantine**:
   - The historical benchmark test partition in `benchmark_split/` was strictly untouched and unread.
3. **One-Time Dev Access Post-Freeze**:
   - InnerTune model checkpoints (`Base`, `StaticLoss`, `ExposureConditional`), selected hyperparameters ($\lambda_{Static} = 8.0, \lambda_{EC} = 2.0, \gamma = 0.5$), and common safety budget $B = 0.088626$ were serialized and cryptographically hashed into `gate01_freeze_manifest.json` at `2026-09-07T15:22:50Z`.
   - Dev cohort data was loaded and evaluated strictly *after* this manifest was written to disk.

---

## 2. Numeric & Statistical Consistency Audit

1. **Safety Budget Calculation**:
   - $R_{Base}^{Tune} = 0.09847289747342353$.
   - $B = 0.90 \times R_{Base}^{Tune} = 0.08862560772608118$.
   - Consistent across manifest, summary JSON, and decision record.
2. **Selection Rule Adherence**:
   - `StaticLoss`: All 4 $\lambda \in \{0.1, 0.5, 2.0, 8.0\}$ missed budget $B$ ($R \in [0.097565, 0.101129] > B$). Selected $\lambda = 8.0$ by minimum risk rule (`static_budget_miss = True`).
   - `ExposureConditional`: $\lambda \in \{2.0, 8.0\}$ satisfied budget $B$. Selected $\lambda = 2.0$ by maximum Recall@5 rule ($0.502548 > 0.477733$, `ec_budget_miss = False`).
   - `DirectExposureRerank`: $\gamma \in \{0.5, 1.0, 2.0, 4.0, 8.0, 16.0\}$ satisfied budget $B$. Selected $\gamma = 0.5$ by maximum Recall@5 rule ($0.506728$, `rerank_budget_miss = False`).
3. **Dev Point Estimates & 95% Confidence Intervals**:
   - Paired patient-clustered bootstrap (2,000 replicates, seed 260907) produced:
     - $\Delta\text{Risk}(EC - Base) = -0.023513$, 95% CI $[-0.023961, -0.023062]$ (upper bound $< 0$).
     - $\Delta\text{Recall}(EC - Base) = -0.0050$, 95% CI $[-0.0060, -0.0039]$ ($\ge -0.010$).
     - $\Delta\text{Risk}(EC - DirectRerank) = -0.012546$, 95% CI $[-0.012891, -0.012204]$.
     - $\Delta\text{Recall}(EC - DirectRerank) = -0.0044$, 95% CI $[-0.0053, -0.0034]$ (upper bound $< 0$, fails $\ge +0.005$ and CI lower $> 0$).

---

## 3. PASS Rule & Condition Verification

- **Condition 1 (Tune Budget Feasibility)**: `PASS` (`ec_budget_miss = False`).
- **Condition 2 (Safety Over Base)**: `PASS` (Dev risk ratio $0.7607 \le 0.90$, CI upper $< 0$).
- **Condition 3 (Bounded Fidelity Cost)**: `PASS` ($\Delta\text{Recall}_{EC-Base} = -0.0050 \ge -0.010$).
- **Condition 4 (Learned Value Beyond Direct Reranker)**: `FAIL`.
  - Protocol requires $\Delta\text{Recall}_{EC - DirectRerank} \ge +0.005$ and 95% CI lower $> 0$.
  - Observed: $\Delta\text{Recall} = -0.0044$ with 95% CI $[-0.0053, -0.0034]$.
  - The direct exposure-aware reranker strictly achieved higher fidelity than end-to-end exposure learning on Dev Q ($0.5098$ vs $0.5055$).
- **Condition 5 (No Weak Dominance by Simple Controls)**: `PASS`.

---

## 4. Scientific Objectivity & Non-Rescue Audit

- **No Model Rescue**: Zero post-hoc modifications, alternative learning rates, additional epochs, or architectural additions were attempted.
- **No Threshold Relaxation**: The $+0.005$ Recall increment over direct reranker was strictly enforced as defined in the preregistered frozen protocol.
- **Verdict Fidelity**: The protocol conclusively yielded `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`, definitively refuting the hypothesis that exposure conditioning requires end-to-end neural training beyond direct greedy exposure controls.

---

## 5. Audit Conclusion

The execution of Gate 01 satisfies all scientific integrity, split quarantine, cryptographic freeze, and objective reporting requirements.
**Verdict: `INTEGRITY_AUDIT_PASS`.**
