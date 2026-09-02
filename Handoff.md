# Handoff: Idea 002 Research Lifecycle Closure (Gate 01 Decision)

## Current state

The research lifecycle for Idea `002-score-geometry-sufficiency` is formally **closed**.
Following the preregistered stop rule in Gate 01 and independent P5 integrity verification, Idea 002 is **terminated** (`TERMINATE_IDEA_002`). Gate 02 is **not authorized**; Candidate 2 is **not authorized**.

- **Idea 001**: Closed and terminated (`TERMINATE_CURRENT_TENSION_ROUTE`); Gate 03 `NOT_AUTHORIZED`.
- **Idea 002 Gate 01**: Formally executed on `319-lab` (`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`); P5 Integrity Audit: **`INTEGRITY_PASS`** ([gate-01-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/gate-01-integrity-audit.md)).
- **Idea 002 Research Decision**: Completed with verdict **`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`** ([research-decision.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/research-decision.md)).
- **Gate 02 Authorization**: **`NOT_AUTHORIZED`**.
- **Candidate 2 Authorization**: **`NOT_AUTHORIZED`**.
- **Residual Routing Opportunity**: Preserved as **`UNRESOLVED_RESEARCH_OPPORTUNITY`** (Oracle - ScoreOnly headroom: +38.79% at 10% budget, +40.68% at 20% budget on fresh Idea-002 Audit partition).
- **Next Owner**: Operator / Research Ideation (`ccf-idea-optimizer`) for formulating new research directions from first principles (exploring representations beyond 1D score geometry).
- **Strict Boundary**: No Gate 02 designed, no Candidate 2 ad-hoc rescue attempted, no test split touched, no model retrained.

## What exists

### Idea 002 Artifacts

All prototype and execution files for Idea 002 are strictly confined to `research/ideas/002-score-geometry-sufficiency/`:

1. [gate-01-score-geometry-sufficiency.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/gate-01-score-geometry-sufficiency.md)
   - Preregistered hypothesis-selection protocol.
   - 5-quintile score map fit strictly on Dev partition.
   - Preregistered Dev early stop rule: `STOP_DEV_ORDER_EQUIVALENT`.
   - Fresh patient-level 50/50 split with standard library `random.Random(2002)` over 1,059 validation universe.
   - Preregistered decision tree requiring $LowerCI_{95\%}[Gap_{Oracle-Score}] > 0$ and $LowerCI_{95\%}[Gap_{Geometry-Score}] > 0$ at 10% and 20% review budgets.
2. [run_score_geometry_sufficiency_gate.py](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/run_score_geometry_sufficiency_gate.py)
   - Executed under `medrec-core-evaluator` on `319-lab`.
   - Frozen harness revision: `28fc24c64998c81563446f3f8e5bc10340e2b17b`.
   - Contains `--self-test` covering split determinism, Dev firewall, deterministic ordering, and decision tree verdicts.
3. [gate-01-summary.json](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/gate-01-summary.json)
   - Public-safe artifact containing all empirical yields, gaps, bootstrap intervals, and frozen identities.
   - SHA256: `ee2ef10ffb9bd9b4e52135f6062e2e4375c6dabc7c53799f436117a39b476a58`.
4. [gate-01-integrity-audit.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/gate-01-integrity-audit.md)
   - Independent P5 integrity audit report with status `INTEGRITY_PASS`.
   - 15,549 rows verified, 0 invariant failures, 0 partition leaks.
5. [research-decision.md](file:///Users/oian/Codes/master/medrec-research/research/ideas/002-score-geometry-sufficiency/research-decision.md)
   - Authoritative P6 research decision terminating Idea 002.

### Historical Idea 001 Artifacts

Preserved under `research/ideas/001-tension-guided-verification/`:

- `experiments/gate-01-routing-opportunity.md` (`pass`)
- `experiments/gate-02-confidence-sufficiency.md` (`STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`)
- `experiments/gate-02-integrity-audit.md` (`INTEGRITY_PASS`)
- `research-decision.md` (`TERMINATE_CURRENT_TENSION_ROUTE`)

## Authoritative records

- `research/baselines/preflight/five-model-comparison-qualification.json` — frozen baseline identities.
- `baselines/registry.toml` — frozen Comparison Mode baseline registry.
- `research/ideas/002-score-geometry-sufficiency/experiments/gate-01-score-geometry-sufficiency.md` — Gate 01 protocol.
- `research/ideas/002-score-geometry-sufficiency/experiments/gate-01-summary.json` — Gate 01 public summary.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` — 319 remote execution preflight contract.

## Executed 319 run record

Formal execution was carried out on `319-lab`:

```bash
export MEDREC_DATA_ROOT=/root/zhb/medrec-data
export GATE_RUN_ID="gate-01-score-geometry-sufficiency-20260902-174013"
export GATE_RUN_ROOT="$MEDREC_DATA_ROOT/runs/ideas/002-score-geometry-sufficiency/$GATE_RUN_ID"
export CANDIDATES_IN="$MEDREC_DATA_ROOT/runs/ideas/001-tension-guided-verification/gate-02-confidence-sufficiency-20260902-155433/gate-02-candidates.jsonl"
export SUMMARY_OUT="/root/zhb/medrec-research/research/ideas/002-score-geometry-sufficiency/experiments/gate-01-summary.json"

conda run -n medrec-core-evaluator python3 research/ideas/002-score-geometry-sufficiency/experiments/run_score_geometry_sufficiency_gate.py \
  --candidate-corpus "${CANDIDATES_IN}" \
  --output-root "${GATE_RUN_ROOT}" \
  --summary-output "${SUMMARY_OUT}" \
  --expected-harness-revision "28fc24c64998c81563446f3f8e5bc10340e2b17b"
```

## Gate 01 Audit & Verdict

- **Decision**: **`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`** (Dev diagnostic: `STOP_DEV_ORDER_EQUIVALENT`)
- **Empirical findings**:
  1. **Cohort & Split**: Full 1,059 validation universe partitioned via seed 2002. Dev: 529 patients (7,422 candidates). Audit: 530 patients (8,127 candidates). 0 patient overlap.
  2. **Dev Map Fitting**: Nearest-rank cutpoints $c_q \in \{0.758362, 0.890841, 0.949205, 0.979460\}$. Empirical risks strictly decrease: $B_1 (0.5811) \to B_2 (0.4629) \to B_3 (0.3172) \to B_4 (0.1799) \to B_5 (0.0539)$.
  3. **Dev Order Equivalence**: Because bin risk decreases monotonically with score and within-bin tie-breaking sorts score ascending, `ScoreGeometry` ordering is 100% order-equivalent to `ScoreOnly` on both Dev and Audit (`STOP_DEV_ORDER_EQUIVALENT`).
  4. **Audit Performance**:
     - Random: 31.46%
     - ScoreOnly: 61.21% (10% budget), 59.32% (20% budget), 56.32% (30% budget)
     - ScoreGeometry: 61.21% (10% budget), 59.32% (20% budget), 56.32% (30% budget)
     - Oracle: 100.0% across all budgets
  5. **Gaps & Residual Capture**:
     - $Geometry - Score = 0.000000$ (95% CI: $[0.0, 0.0]$ across all budgets).
     - $Oracle - Score = +38.79\%$ (10% budget), $+40.68\%$ (20% budget). Both lower CIs $> 0$.
     - $ResidualCapture_{Geometry} = 0.000000$.
  6. **Support**: 419 beneficial patients, 421 non-beneficial patients (both >> 50 required threshold).
