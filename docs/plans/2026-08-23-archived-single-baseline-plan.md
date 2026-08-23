---
title: SafeDrug Archived Single-Baseline Program
type: feat
date: 2026-08-23
status: accepted
execution: remote
---

# SafeDrug Archived Single-Baseline Program

## Decision

SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the sole active SafeDrug-family source. Existing IDs `gamenet`, `safedrug`, `retain`, and `leap-safedrug` remain because they name distinct models, but they share one source lineage, preprocessing contract, split, and evaluation authority. No parallel SafeDrug-main identities or future main-branch lanes will be maintained.

SafeDrug `main@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` remains only as historical provenance for three completed source-native runs. Those artifacts are not rewritten, deleted, or admitted into future paper reproduction or Comparison Mode.

## Critical finding

The archived branch is the upstream paper-reproduction branch, but it is not directly trainable from its checked-in CLI defaults. `GAMENet.py`, `SafeDrug.py`, `Retain.py`, and `Leap.py` all declare `--Test` as `store_true` with `default=True`; none exposes a CLI flag that selects training. The repository includes one SafeDrug checkpoint but no complete checkpoint set for all four models.

Therefore exact archived source identity and byte-for-byte unmodified execution are different claims. Future runs must preserve archived model, data, split, optimizer, selection, and evaluation behavior while declaring one minimal mechanical adaptation that makes training mode selectable. Importing the SafeDrug-main entrypoints would reintroduce the lineage being removed and is prohibited.

## Claims

- **Primary claim**: archived preprocessing plus archived four-model semantics can reproduce SafeDrug Table 2 within reported test-bootstrap variation and recorded hardware/software deviations.
- **Supporting claim**: the archived SafeDrug result preserves the paper's relative SafeDrug-versus-GAMENet Jaccard/F1 and SafeDrug-versus-LEAP DDI claims.
- **Anti-claim**: matching a paper number from main-branch inputs, a bundled checkpoint, or test-only execution does not constitute paper reproduction.

## Must-run blocks

### B0: Archived source and data gate

- Regenerate archived preprocessing from authorized MIMIC-III inputs on 319.
- Require exactly 6,350 patients, 14,995 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures before any training launch.
- Record public-safe aggregate counts and restricted input identities. Do not transfer patient rows, split membership, or generated pickle files into Git.
- Fail the batch if any count differs. Investigate preprocessing or mapping lineage; do not compensate inside model code.

### B1: Mechanical training-mode adaptation

- Add one harness-owned, reviewed mechanism that selects the existing training branch in each archived entrypoint.
- Preserve model code, data paths, seed behavior, learning rates, loss functions, 50 epochs, validation-Jaccard checkpoint selection, prediction threshold, ten test bootstraps, and metric computation.
- Record the patched source or wrapper revision separately from upstream revision.
- Prove with a no-training smoke check that default archived execution remains Test mode and the adaptation selects training without importing SafeDrug-main code.

Implemented locally on `2026-08-23` in `baselines/adapters/safedrug_archived.py`. One shared adapter covers GAMENet, SafeDrug, RETAIN, and LEAP. It creates a run-scoped source copy and replaces exactly one audited token sequence, `default=True` with `default=False`, in the archived `--Test` declaration. Source drift or any non-reversible change fails before training. Test execution still uses the original archived entrypoint with explicit `--Test`.

The same adapter now enforces B0 counts, keeps checkpoints and logs under the repository-external run root, selects the zero-based best checkpoint, validates ten test rounds against the upstream summary, writes terminal `status.json` before assembling `result.json`, and records the archived source and adapted-entrypoint digests. Local synthetic tests pass without importing Torch, NumPy, or dill.

This implementation does not advance readiness. Archived dataset generation, the 319 environment lock, import smoke, adapter digest, and explicit `RemoteExecutor` launcher remain unverified and therefore unregistered.

### B2: Four-model archived reproduction

- Launch SafeDrug, GAMENet, RETAIN, and LEAP concurrently, one idle physical GPU per model.
- Keep lanes independent; one failure does not cancel successful lanes.
- Require one validated best checkpoint and ten complete test rounds for every model.
- Treat ten bootstraps as test-subset variability, not independent training-seed evidence.

### B3: Paper comparison

- Compare DDI, Jaccard, F1, PRAUC, and average medication count with SafeDrug Table 2.
- Test the paper's SafeDrug-versus-GAMENet Jaccard and F1 relative improvements and SafeDrug-versus-LEAP DDI reduction.
- Report exact environment deviations: paper Python 3.7, PyTorch 1.4.0, and V100 versus the verified 319 stack and RTX 3090 hardware.
- A failed headline claim remains a valid reproduction result; do not retune after seeing test results.

## Run order

1. Freeze archived source and audit entrypoint/input differences.
2. Regenerate data and pass B0 counts.
3. Implement and test B1 locally with synthetic fixtures; verify archived environment imports on 319.
4. Run a short 319 smoke that reaches the training loop without producing research metrics.
5. Launch four full GPU lanes.
6. Validate terminal artifacts before comparing results.
7. Run experiment integrity audit, then write claim conclusions.

## Stop conditions

- Any B0 count mismatch blocks all four lanes.
- Any adaptation that changes scientific behavior blocks the affected lane.
- Source, adapter, environment, or input drift blocks launch.
- A terminal status without complete metrics or checkpoint evidence is failure, not success.
- No main-branch fallback is allowed. A blocked archived lane stays blocked until repaired within archived semantics.

## Public-safe outputs

- Aggregate preprocessing counts.
- Immutable upstream and adapter revisions.
- Environment identity and explicit deviations.
- Opaque run IDs, terminal states, aggregate metrics, and failure summaries.
- Table 2 deltas and relative-claim calculations.

Raw EHR data, patient membership, predictions, checkpoints, pickle files, and raw logs remain on 319 outside Git.

## Definition of done

- Registry and Comparison Protocol name only the archived SafeDrug lineage for future work.
- Main-branch runs are labeled historical and excluded from future baseline selection.
- Archived data passes all paper aggregate-count gates.
- All four archived models have validated completed runs or explicit irreducible failure records.
- Table 2 deltas and three headline relative claims are reported without treating bootstrap rounds as training-seed replication.
- Local tests, Ruff, Markdownlint, and whitespace checks pass; real-data/GPU work is performed only on 319.
