# Handoff

Updated: 2026-09-19.

```text
Current phase: MEMB_MUTUAL_BINDING_SCREEN_IMPLEMENTED_PENDING_319_EXECUTION
Working branch: prototype/memb-mutual-binding-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Previous terminal routing: KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS
```

Frozen execution revision:

```text
f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2
```

## Current task

Execute the frozen Medication–Evidence Mutual Binding (MEMB) family screen. Do not redesign the model before execution.

The screen tests whether cross-medication evidence specificity adds decision value beyond exact score-sharpening controls while preserving the historical FineCode / PredictionLocal parameter graph.

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-memb-mutual-binding-screen-design.md`
- `research/prototypes/memb-mutual-binding-screen/README.md`
- `research/prototypes/memb-mutual-binding-screen/closest-work-audit.md`

## Frozen lanes

```text
GPU0  mutual_code
GPU1  scale2_code
GPU2  specificity_code
GPU3  foundation_code_anchor
GPU4  mutual_local
GPU5  scale2_local
GPU6  specificity_local
GPU7  prediction_local_anchor
```

Four commonness comparisons are pre-registered:

```text
specificity_code  - foundation_code_anchor
mutual_code       - scale2_code
specificity_local - prediction_local_anchor
mutual_local      - scale2_local
```

The `scale2_*` lanes are mandatory because mutual matching algebraically sharpens raw scores. They prevent score sharpening from being misattributed to cross-medication specificity.

## Local execution

1. Fetch the branch and checkout exact revision `f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2`.
2. Verify a clean checkout and actual availability of all 8 RTX 3090 GPUs.
3. Run repository-native checks that can detect relevant implementation failures.
4. Set `SNAPSHOT_ROOT`, `TRAIN_DEV_ROOT`, `OUT_ROOT`, and optionally `PYTHON_BIN`.
5. Run `preflight_memb.py`. It must pass target-leakage, exact shared initialization/parameter count, historical raw-affinity/potential identity, exact commonness formula attribution, finite forward/backward/no-history execution, and historical anchor identity.
6. Only after preflight PASS, run `launch_8gpu.sh` for all eight complete 30-epoch lanes.
7. Do not inspect partial metrics for scientific decisions.
8. If a relevant matched pair is horizon-censored at epoch 26–30, extend only that exact pair unchanged to 60 epochs under contract v1.3.
9. After all interpretable lanes complete, run `summarize_memb.py`, preserve public-safe aggregate evidence, update decision/current-state/Handoff according to the actual routing, commit, and push.

Do not tune score exponents, temperatures, top-k competition, Sinkhorn/OT iterations, marginals, DDI weights, thresholds, sparse activations, query adapters, or rerankers to rescue a weak result.

No multi-seed stability, MIMIC-IV, or Test is automatically authorized. Test remains sealed.
