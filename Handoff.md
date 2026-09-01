# Handoff: Idea 001 Gate 01 Routing Opportunity Implementation

## Current state

Gate 01 (**Routing Opportunity Under a Fixed Revision Operator**) for Idea `001-tension-guided-verification` is fully implemented, doubly hardened, statically and synthetically verified, committed, and pushed to `origin/main`. The working tree is clean.

The actual 319 remote GPU execution has **not** been started and is paused awaiting explicit operator authorization.

- **Repository HEAD**: `c6fc35bce97637a2eddc6319cdec768256abdccb` on `main`.
- **Remote state**: In sync with `origin/main`.
- **Test suite**: 333 core unit/integration tests passing; 8-stage synthetic self-test passing; `ruff` check and format passing; `markdownlint` clean.
- **Scientific role**: Idea-stage hypothesis selection, not a baseline comparison qualification. Do not use `accept-comparison`.

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

## Remote 319 launch protocol

When authorized to run on `319-wild` (`319-lab` or `319-lab-via-server`):

```bash
# 1. Preflight check
# Ensure GPU utilization <= 10%, free memory adequate, worktrees clean

# 2. Paths and environment variables
export MEDREC_DATA_ROOT=/root/zhb/medrec-data
export MOLEREC_ROOT=/root/zhb/MoleRec
export DATASET_MANIFEST="$MEDREC_DATA_ROOT/snapshots/molerec-table1-c721-www23/dataset-manifest.json"
export MOLEREC_CHECKPOINT="$MEDREC_DATA_ROOT/runs/molerec/formal-20260828-a09fcab-u8-b/lanes/molerec-embedding/saved/MoleRec/best_model.pt"

export GATE_RUN_ID="gate-01-routing-opportunity-$(date +%Y%m%d-%H%M%S)"
export GATE_RUN_ROOT="$MEDREC_DATA_ROOT/runs/ideas/001-tension-guided-verification/$GATE_RUN_ID"

# 3. Launch execution
cd /root/zhb/medrec-research
git pull origin main
source /root/anaconda3/etc/profile.d/conda.sh

conda run -n medrec-core-evaluator \
  python research/ideas/001-tension-guided-verification/experiments/run_routing_opportunity_gate.py \
  --dataset-manifest "$DATASET_MANIFEST" \
  --dataset-root "$MEDREC_DATA_ROOT/snapshots/molerec-table1-c721-www23" \
  --molerec-root "$MOLEREC_ROOT" \
  --checkpoint "$MOLEREC_CHECKPOINT" \
  --output-root "$GATE_RUN_ROOT" \
  --expected-harness-revision "c6fc35bce97637a2eddc6319cdec768256abdccb"

# 4. Ingest aggregate-only public summary
# Copy $GATE_RUN_ROOT/gate-summary.json to local repository
# Leave candidate-revision-values.jsonl under $MEDREC_DATA_ROOT on 319
```

## Next steps & stop rule

1. **Do not run Gate 01 without user confirmation.**
2. **Execute remote Gate 01**: After operator launches on 319, collect `gate-summary.json`.
3. **Audit Gate 01 verdict**:
   - `pass`: Oracle 95% CI > Random at 10% & 20% budgets, Oracle > RiskOnly. Confirms selective routing has headroom under $R_0$; unlocks designing predictive Tension triggers.
   - `downgrade_risk_only`: Oracle > Random, but Oracle statistically indistinguishable from RiskOnly. Route pivots to testing whether Tension adds any incremental value over simple DDI degree sorting.
   - `fail`: Oracle fails to reliably beat Random under $R_0$. Route stops; do not implement Tension.
   - `insufficient_support`: Fewer than 50 distinct beneficial or non-beneficial validation patients. Inconclusive under current data support.
4. **Stop rule**: Do not train a Tension policy, implement sequential multi-step revision, or proceed past Gate 01 until the public summary verdict has been inspected.

## Suggested skills

- `ccf-experiment-designer`: Inspect Gate 01 results, audit decision criteria, and design the next hypothesis-selection or allocation step.
- `ccf-idea-optimizer`: Concretize or pivot the Tension idea if Gate 01 yields `downgrade_risk_only` or requires adjusting problem scope.
- `ce-handoff`: Manage session transitions and cross-agent continuity.
