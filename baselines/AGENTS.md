# Baseline subtree instructions

This subtree owns external baseline identity, Reproduction Programs, and Comparison Mode integration.

## Fidelity first

- Prefer the official upstream source at a pinned immutable revision plus a thin mechanical wrapper.
- Do not reject a published method using a semantically inspired rewrite.
- `baselines/registry.toml` is the authority for baseline identity, declared modes, environment, program, and readiness.
- Keep imported source outside this repository unless license, provenance, and need have been reviewed.

## Scientific modes

Reproduction Mode preserves the baseline's recorded upstream behavior. Comparison Mode evaluates methods under the Unified Research Protocol. Evidence from one mode does not silently support claims in the other.

In Comparison Mode the Baseline Core is frozen. A Prediction Adapter may translate files, identifiers, tensors, and target-free wire payloads, but it must not change model logic, loss, feature availability, thresholding, or checkpoint-selection behavior. A scientific change requires a separate method identity.

## Runtime boundaries

- External baselines run in their declared isolated Conda environment on the 319 Execution Plane.
- Core evaluation remains separate from baseline dependencies.
- Baseline processes emit target-free payloads; core-owned targets stay outside the baseline process.
- Restricted data, patient-level predictions, model weights, and private runtime paths never enter Git.

## Changes

Keep baseline-specific fixes local. Do not introduce generic compatibility layers unless more than one real consumer needs them. When a baseline integration reveals a durable generic capability, promote that capability into `src/medrec_research/` only after its semantics and ownership are stable.
