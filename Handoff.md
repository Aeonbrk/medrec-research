# Handoff: Idea 001 Research Lifecycle Closure (P6 Final Decision)

## Current state

The research lifecycle for Idea `001-tension-guided-verification` is formally **closed**.
Following the preregistered stop rule in Gate 02 and independent P5 integrity verification, the current Tension route is **terminated** (`TERMINATE_CURRENT_TENSION_ROUTE`). Gate 03 is **not authorized**.

- **Gate 01**: Formally executed on 319 (`pass`); P0 Integrity Audit: **`AUDIT_PASS`** ([gate-01-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-01-integrity-audit.md)).
- **Gate 02**: Formally executed on 319 (`STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`); P5 Integrity Audit: **`INTEGRITY_PASS`** ([gate-02-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-02-integrity-audit.md)).
- **P6 Final Research Decision**: Completed with verdict **`TERMINATE_CURRENT_TENSION_ROUTE`** ([research-decision.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/research-decision.md)).
- **Gate 03 Authorization**: **`NOT_AUTHORIZED`**.
- **Failure Record**: Preserved in [`tension-gate-02--recommender-confidence-sufficiency.md`](file:///Users/oian/Codes/master/medrec-research/research/memory/failures/tension-gate-02--recommender-confidence-sufficiency.md).
- **Residual Routing Opportunity**: Preserved as **`UNRESOLVED_RESEARCH_OPPORTUNITY`** (Oracle - ScoreOnly headroom: +38.87% at 10% budget, +41.48% at 20% budget).
- **Next Owner**: Operator / Research Ideation (`ccf-idea-optimizer`) for formulating new research directions from first principles.
- **Strict Boundary**: No Gate 03 designed, no Tension model trained, no post-hoc rescue attempted.

## What exists

All prototype files are strictly confined to `research/ideas/001-tension-guided-verification/experiments/`:

1. [gate-01-routing-opportunity.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-01-routing-opportunity.md)
   - The preregistered hypothesis-selection protocol.
   - Fixed singleton deletion operator $R_0(\hat M_t, m) = \hat M_t \setminus \{m\}$.
   - Review universe $\mathcal Q_t = \{m \in \hat M_t : d_t(m) > 0\}$ with canonical unordered DDI semantics $\{m, j\} \in C$.
   - Three policies: Random ($P(Y^{PB}=1)$), RiskOnly ($d_t(m) \downarrow$, med code $\uparrow$, validation traversal order), Oracle ($Y^{PB} \downarrow, \Delta J \downarrow, -\Delta V \downarrow$, med code $\uparrow$, validation traversal order).
   - Budgets $B \in \{10\%, 20\%, 30\%\}$ with integer floor rule $k(B) = \lfloor B \times |\mathcal Q| \rfloor$.
   - Minimum 50-patient support requirement for both beneficial and non-beneficial outcomes.
   - 1,000-replicate patient-clustered bootstrap with seed 1203.
   - Clear test split boundary: test split must never be indexed, inspected, scored, evaluated, or used for selection/configuration.
   - Restricted artifact format: `candidate-revision-values.jsonl` with `patient_order` and `visit_order` allowing independent auditor recomputation.
   - Public-safe artifact format: `gate-summary.json`.

2. [stage_validation_cohort.py](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/stage_validation_cohort.py)
   - Python 3.8-compatible helper executed in `medrec-molerec-table1` (with `dill`).
   - Isolates validation patient split from `records_final.pkl`.
   - Computes raw DDI asset SHA256 (`dcb20789...`) and canonical unordered DDI semantics SHA256.
   - Computes authoritative medication vocabulary SHA256 matching `DatasetManifest._ordered_digest`.
   - Generates `features.pkl` (for `molerec_comparison.py`) and standard JSON `validation-meta.json` (consumed by Python 3.11 runner).

3. [run_routing_opportunity_gate.py](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/run_routing_opportunity_gate.py)
   - Python 3.11 orchestration runner executed in `medrec-core-evaluator`.
   - Enforces clean checkouts for both `medrec-research` and `MoleRec` before inference.
   - Verifies frozen MoleRec source revision (`dd5afaf...`), baseline core SHA256 (`516b7b5f...`), adapter SHA256 (`9bb5d114...`), and Conda explicit package specification SHA256 (`6a01d313...`).
   - Verifies dataset manifest (`82d4efc2...`), dataset ID, snapshot ID (`molerec-table1-c721-www23`), snapshot checksum, vocabulary SHA256, DDI asset SHA256, and feature availability SHA256 (`9e403591...`).
   - Uses `ProcessPredictionAdapter.predict_comparison` (target-free comparison seam).
   - Evaluates policies and bootstrap invariant to pseudonyms.
   - Implements fail-closed non-crashing behavior for low-support samples ($k=0$ yields $0.0$ and verdict `insufficient_support`).
   - Enforces new `output_root` (`exist_ok=False`).
   - Contains `--self-test` (and `test_synthetic_gate_01()` for pytest) covering all 8 hardened invariants.

## Authoritative records

- `research/baselines/preflight/five-model-comparison-qualification.json` — frozen baseline identities.
- `baselines/registry.toml` — frozen Comparison Mode baseline registry.
- `src/medrec_research/dataset.py` — authoritative `DatasetManifest` and `_ordered_digest` implementation.
- `research/ideas/001-tension-guided-verification/experiments/gate-01-routing-opportunity.md` — Gate 01 protocol.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` — 319 remote execution preflight contract.

## Executed 319 run record

Formal execution was carried out on `319-lab-via-server`:

```bash
export MEDREC_DATA_ROOT=/root/zhb/medrec-data
export MOLEREC_ROOT=/root/zhb/MoleRec
export DATASET_MANIFEST="$MEDREC_DATA_ROOT/comparison/five-model-v1-1-fe7e526/dataset-manifest.json"
export MOLEREC_CHECKPOINT="$MEDREC_DATA_ROOT/runs/molerec/medrec-baseline-molerec-embedding-20260828-081052-82b84a1f/work/saved/MoleRec_medrec-baseline-molerec-embedding-20260828-081052-82b84a1f/Epoch_44_TARGET_0.06_JA_0.5327_DDI_0.0723.model"
export GATE_RUN_ID="gate-01-routing-opportunity-20260902-010537"
export GATE_RUN_ROOT="$MEDREC_DATA_ROOT/runs/ideas/001-tension-guided-verification/$GATE_RUN_ID"

# Execution completed in ~3 minutes on GPU 6.
# gate-summary.json retrieved to local research/ideas/001-tension-guided-verification/experiments/
# candidate-revision-values.jsonl preserved under $GATE_RUN_ROOT on 319.
```

## Gate 01 Audit & Verdict

- **Decision**: **`pass`**
- **Empirical findings**:
  1. **Base Prevalence**: Within the review universe $\mathcal Q$ (15,549 candidate revisions across 1,219 visits and 858 validation patients), only **31.67%** of singleton deletions are Pareto-beneficial ($Y^{PB}=1$), while **68.33%** reduce visit-level Jaccard under singleton deletion ($\Delta J < 0$, non-beneficial revisions under $R_0$).
  2. **Random Policy**: Constant at base prevalence **31.67%**.
  3. **RiskOnly Policy**: Yields **37.07%** (10% budget), **35.64%** (20% budget), **32.87%** (30% budget). Simple DDI-degree sorting fails to isolate Pareto-beneficial revisions under $R_0$ and results in >62% non-beneficial revisions (revisions that reduce visit-level Jaccard).
  4. **Oracle Policy**: Achieves **100.0%** Pareto-beneficial revisions across 10%, 20%, and 30% review budgets.
  5. **Statistical Headroom**:
     - Oracle - Random: **+68.33%** (95% CI: [67.33%, 69.38%])
     - Oracle - RiskOnly: **+62.93%** at 10% (95% CI: [59.88%, 65.61%]), **+64.36%** at 20% (95% CI: [62.18%, 66.74%])
  6. **Support**: 844 beneficial patients, 857 non-beneficial patients (both >> 50 required threshold).

## Scientific Lifecycle Summary & Final Decision (P6)

- **Gate 01 Status**: Formally executed on 319 (`pass`); P0 Integrity Closure completed: **`AUDIT_PASS`** ([gate-01-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-01-integrity-audit.md)).
- **Gate 02 Status**: Formally executed on 319 (`STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`); P5 Integrity Audit completed: **`INTEGRITY_PASS`** ([gate-02-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-02-integrity-audit.md)).
  - Dev selection: $\lambda^* = 0.0$ ($D_{\max}^{\text{Dev}} = 12.0$, score median $\tau_s = 0.92499$).
  - Audit evaluation: Random 31.03%, RiskOnly 36.48%/35.76%/33.43%, ScoreOnly 61.13%/58.52%/55.26%, Scalar ($\lambda^*=0.0$) 61.13%/58.52%/55.26%, Oracle 100.0%.
  - Gaps: Score - Random (+30.10%/+27.48%/+24.22%), Score - Risk (+24.65%/+22.75%/+21.83%), Scalar - Score (0.0% across all budgets; 95% CI: [0.0, 0.0]), Oracle - Score (+38.87%/+41.48%/+44.74%).
  - Interaction diagnostic: $I_{\text{Tension}} = -0.0052$ (95% CI: [-0.0457, 0.0364], includes 0; support 408-417 patients per cell $\ge 50$).
  - Audit support: 423 beneficial patients, 428 non-beneficial patients (both >> 50 required threshold).
- **Completed Lifecycle Queue**:
  - `P0`: Done — Gate 01 Integrity Closure completed with `AUDIT_PASS`.
  - `P1-P3`: Done (preregistration, implementation, synthetic verification).
  - `P4`: Done — Formal 319 execution completed.
  - `P5`: Done — Gate 02 Integrity Audit completed: **`INTEGRITY_PASS`** ([gate-02-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/experiments/gate-02-integrity-audit.md)).
  - `P6`: Done — Final research decision executed: **`TERMINATE_CURRENT_TENSION_ROUTE`** ([research-decision.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/001-tension-guided-verification/research-decision.md)).
- **Terminal Decision**: Current Tension route terminated. Gate 03 is **`NOT_AUTHORIZED`**.
- **Residual Opportunity**: Retained as `UNRESOLVED_RESEARCH_OPPORTUNITY`:
  $$\boxed{\text{What target-free observable information explains residual revision-value heterogeneity beyond frozen recommender confidence?}}$$
- **Next CCFA Owner**: `ccf-idea-optimizer` / Research Operator (Stage: Research Ideation / Problem Formulation).
- **Strict Prohibition**: Not authorized for `ccf-paper-writer` or Tension implementation. No post-hoc rescue attempts allowed.
