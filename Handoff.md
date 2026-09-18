# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE HYPOTHESIS TESTING — ECRC CARDINALITY CONTEXT
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-authorization.md`
- `research/prototypes/ecrc-cardinality-context/README.md`

## Current evidence

Medication-specific late evidence selection remains the strongest repeated
positive mechanism. DCPM and RouteFact are falsified and closed.

The post-RouteFact audit identified one narrower unresolved global structure:
regimen cardinality may change **which named medications are preferred**, not
merely how many medications are selected.

Relevant prior project evidence:

- B0 oracle-count: frozen MoleRec ranking with target cardinality changed Dev
  Jaccard by approximately `+0.01285`; B0's original normalized-DDI premise
  remains falsified.
- frozen-unary pairwise oracle headroom: approximately `+0.00026` Jaccard.
- RIME composition minus count-only: approximately `-0.00199` Jaccard.

Closest-work audit does **not** support novelty claims for joint
cardinality/set prediction, random finite sets, conditional Bernoulli
likelihoods, generic set decoding, or medication-count normalization. The only
candidate paper identity is cardinality-conditioned named-medication choice.

## Frozen screen

Implementation:

`research/prototypes/ecrc-cardinality-context/`

Six lanes:

```text
GPU 0  kind_bce    seed 20260923
GPU 1  kcond_bce   seed 20260923
GPU 2  kind_exact  seed 20260923
GPU 3  kcond_exact seed 20260923
GPU 4  kind_exact  seed 20260924
GPU 5  kcond_exact seed 20260924
```

The exact pair is primary. The BCE pair is supporting attribution. The second
exact seed is stability evidence, not HPO.

Before launch:

1. verify a clean checkout at the exact implementation revision;
2. verify six admissible GPUs and map them through `GPU_IDS`;
3. run the committed CUDA preflight;
4. do not access Test.

Launch with `launch_six_lane.sh`. Keep checkpoints, predictions, logs, and
patient-level artifacts only on the 319 Execution Plane. Only
`ecrc-comparison.json` and compact public-safe aggregate results may return
to Git.

## Frozen interpretation

- Oracle-K is privileged mechanism attribution only.
- Predicted-K is deployable evidence.
- If oracle-K exact KCond-vs-KInd is not material, kill the choice mechanism.
- If oracle-K is material but predicted-K is not, exactly one bounded
  size-predictor redesign is authorized.
- Do not promote a count head alone as the method.
- Do not sweep rank, losses, learning rate, K bins, temperatures, or decoders.

Test remains sealed.
