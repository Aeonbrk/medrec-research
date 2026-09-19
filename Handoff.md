# Handoff

Updated: 2026-09-19.

```text
Current phase: MSED_EVIDENCE_DISTRIBUTION_SCREEN_IMPLEMENTED_PENDING_319_EXECUTION
Working branch: prototype/msed-evidence-distribution-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Previous terminal routing: KILL_MHEF_NORMALIZATION_HYPOTHESIS
```

## Authoritative starting point

This branch is created from the completed MHEF branch revision:

```text
627f1c5c1a89785733af2f8a99aa4a0e2cfb645d
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-mhef-normalization-screen-verdict.md`
- `research/memory/decisions/2026-09-19-msed-evidence-distribution-screen-design.md`
- `research/prototypes/msed-evidence-distribution-screen/README.md`
- `research/prototypes/msed-evidence-distribution-screen/closest-work-audit.md`

## Why this family

MHEF falsified modality-specific normalization as the missing mechanism. The next family is driven by a different structural clue: `PredictionLocal` improved Dev Jaccard by `+0.012976` over its matched aggregate control. Exact code inspection shows that the pair is approximately a comparison between the mean and normalized log-sum-exp of the same medication-token local support potentials.

The new Rank-1 hypothesis is therefore:

> For each candidate medication, the complete empirical distribution of longitudinal FineCode support potentials carries decision information beyond the strong single `logmeanexp` statistic.

The working architecture is Medication-Specific Evidence Distribution (MSED).

## Cloud-side work already complete

Implemented under:

`research/prototypes/msed-evidence-distribution-screen/`

The package contains:

- `msed_model.py`
- `run_msed.py`
- `preflight_msed.py`
- `summarize_msed.py`
- `launch_8gpu.sh`
- `README.md`
- `closest-work-audit.md`

Cloud static syntax checks passed before push. The real CUDAoprivate-data preflight and full Train/Dev execution remain local-agent work.

## Local-agent task

Do not redesign the model before the frozen preflight.

1. Fetch this branch and verify a clean checkout at its pushed HEAD.
2. Run repository-native lint/tests that can detect implementation failures relevant to the screen.
3. Set:

```text
SNAPSHOT_ROOT
TRAIN_DEV_ROOT
OUT_ROOT
PYTHON_BIN  # optional if the correct environment is already active
```

4. Run `preflight_msed.py` on CUDA/private data. It must verify:

```text
correct frozen MIMIC-III Train/Dev profile
no current-medication target leakage
exact stable FineCode global-context preservation
exact PredictionLocal raw local-score preservation
exact PredictionLocal LME preservation
same parameter graph/count/init across the six MSED variants
primary pair identical before E[phi(r)] vs phi(LME(r))
finite forward/backward/no-history execution
historical anchor identity
Test not loaded
```

5. If and only if preflight passes, launch:

```bash
research/prototypes/msed-evidence-distribution-screen/launch_8gpu.sh
```

## Frozen 8-GPU allocation

```text
GPU0  msed_ecf_global
GPU1  point_lme_global
GPU2  point_mean_global
GPU3  point_max_global
GPU4  msed_ecf_only
GPU5  point_lme_only
GPU6  prediction_local_anchor
GPU7  foundation_code_anchor
```

Run all eight lanes for the complete 30 epochs. No early stopping and no interpretation from partial metrics.

The primary comparison is:

```text
msed_ecf_global - point_lme_global
```

This pair has the same raw local medication-token scores, the same raw LME statistic, the same global FineCode context, the same feature dimensionality, decoder, parameter count, initialization, optimizer, RNG, and training horizon. It differs only in whether the nonlinear spectrum summarizes the empirical local-support distribution or the scalar LME point.

## Decision rules

Use the frozen rules in `README.md` and `summarize_msed.py`.

Do not rescue a negative/weak result with kernel/frequency sweeps, learned pooling grids, temperatures, top-k, hidden-size/head sweeps, dynamic queries, extra hops, DDI weights, threshold tuning, or rerankers.

If a relevant 30-epoch comparison selects epoch 26--30, extend that exact affected pair unchanged to 60 epochs under contract v1.3. Do not alter architecture or optimization.

After complete interpretable lanes exist, run `summarize_msed.py`, preserve public-safe aggregate evidence, update decision memory/current state/Handoff according to the real routing, commit, and push.

Do not automatically run multi-seed stability, MIMIC-IV, or Test. Test remains sealed.
