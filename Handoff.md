# Handoff

Updated: 2026-09-19.

```text
Current phase: MHEF_NORMALIZATION_DOMAIN_SCREEN_IMPLEMENTED_PENDING_319_EXECUTION
Working branch: prototype/mhef-normalization-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
```

## Authoritative starting point

This branch was created from:

```text
d957fa37a057b76f6abee75906c5351b9bb82e9e
```

which records the completed evidence and early termination of the final relational architecture search.

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/decisions/2026-09-19-final-relational-architecture-early-termination.md`
- `research/memory/decisions/2026-09-19-mhef-normalization-screen-design.md`
- `research/prototypes/mhef-normalization-screen/README.md`
- `research/prototypes/mhef-normalization-screen/closest-work-audit.md`

## What is already done

Cloud-side design and implementation are complete:

- Rank-1 architecture narrowed to Medication-Conditioned Heterogeneous Evidence Factorization (MHEF);
- decisive `IndependentBudget` vs `CoupledBudget` causal control frozen;
- all eight GPU lanes implemented with one shared parameter graph;
- capacity, fusion-head, global-path, and two semantic-partition controls implemented;
- 30-epoch runner and v1.3 horizon-censoring semantics implemented;
- optional exact 60-epoch runner mode exists only for a triggered censoring extension;
- CUDA/data preflight and aggregate scientific routing scripts implemented;
- Test remains sealed by construction.

Cloud static checks completed:

```text
python -m py_compile research/prototypes/mhef-normalization-screen/*.py
bash -n research/prototypes/mhef-normalization-screen/launch_8gpu.sh
```

`ruff` is not installed in the cloud environment, so repository Ruff/format checks remain local-agent work.

## Local agent task

Do not redesign the model before executing the frozen preflight.

1. Fetch this branch and verify clean HEAD.
2. Run the applicable repository syntax/lint checks.
3. Set the private execution-plane environment variables required by `launch_8gpu.sh`:

```text
SNAPSHOT_ROOT
TRAIN_DEV_ROOT
OUT_ROOT
PYTHON_BIN   # optional; defaults to python
```

4. Run the CUDA/private-data preflight only. It checks:

```text
correct snapshot / Train-Dev profile
no current-target leakage
exact preservation of the stable global FineCode context
one common parameter budget and initialization across all eight lanes
finite forward/backward/no-history execution
behaviorally active matched mechanisms
hash partitions preserve typed evidence support and per-example D/P/H bucket sizes
```

5. If preflight passes, launch the eight fixed 30-epoch lanes with:

```bash
research/prototypes/mhef-normalization-screen/launch_8gpu.sh
```

6. Do not stop lanes based on partial metrics. Do not use Test.
7. If the frozen v1.3 censoring rule triggers, extend the exact affected comparison unchanged with `run_mhef.py --epochs 60`; do not tune anything.
8. After complete interpretable lanes exist, run `summarize_mhef.py` and record the real result/routing. Do not authorize multi-seed stability automatically.

## Eight lanes

```text
GPU 0  mhef_independent_add
GPU 1  coupled_budget_add
GPU 2  wide_global_add
GPU 3  mhef_independent_concat
GPU 4  coupled_budget_concat
GPU 5  private_only_add
GPU 6  hash_partition_a_add
GPU 7  hash_partition_b_add
```

## Primary falsification

The main scientific comparison is:

```text
mhef_independent_add - coupled_budget_add
```

Interpret using the frozen screen thresholds in the README.

If this comparison is not material, kill the normalization-domain hypothesis. Do not rescue it with a gate, query adapter, DDI correction, another attention block, or HPO.
