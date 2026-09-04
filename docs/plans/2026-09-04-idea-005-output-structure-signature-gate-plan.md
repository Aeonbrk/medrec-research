<!-- markdownlint-disable MD013 -->

# Idea 005 Output-Structure Signature Gate Plan

## Goal

Implement and execute one validation-only falsification gate for `research/ideas/005-safety-substitution-structure/`.

The Gate answers only whether a material ATC-2-sibling output-structure signature remains in frozen MoleRec ATC-3 outputs after Dev-only per-medication threshold calibration.

## Scope

Included:

- Idea-local validation staging;
- one frozen MoleRec validation inference;
- deterministic seed-`2005` patient Dev/Audit split;
- ATC-2 sibling candidate-group construction from frozen ATC-3 vocabulary;
- two preregistered signatures;
- Dev-only per-medication threshold killer control;
- public-safe aggregate summary;
- independent post-run integrity audit and research decision.

Excluded:

- model retraining;
- method implementation;
- therapeutic-equivalence mapping;
- ATC-4 reconstruction;
- train co-occurrence group discovery;
- exact-count outcome-seeking variants;
- additional backbones;
- test access;
- Gate 02.

## Work units

### P0 — Protocol and state verification

- Confirm local `origin/main` equals the accepted Gate implementation revision.
- Confirm clean harness checkout.
- Confirm Idea 004 remains terminated and Idea 005 protocol is the active Gate.
- Confirm test split has not been staged or predicted.

### P1 — Local software verification

- Run Idea 005 self-test.
- Run focused unit tests.
- Run repository completion checks required by `AGENTS.md`.
- Fix only implementation defects that violate the frozen Gate; any scientific-protocol change returns to design review.

### P2 — 319 preflight

Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`.

- Try `319-lab`, then only the approved fallback if needed.
- Verify authenticated expected account, clean exact remote checkout, external data root, frozen baseline source/checkpoint/environment, current disk capacity, and admissible GPU state.
- Do not mutate data, baseline source, checkpoint, or environment to force admission.

### P3 — One formal validation-only run

- Use a fresh restricted run directory.
- Stage only validation contexts/targets plus required frozen identity metadata.
- Run the target-free MoleRec Comparison adapter once.
- Fit calibration thresholds on Dev only.
- Evaluate the mechanical Gate on Audit once.
- Do not rerun with changed seeds, thresholds, groups, signatures, or support conditions.

### P4 — Integrity audit

Independently verify:

- no test indexing/prediction/evaluation;
- exact frozen identities;
- raw predicted set equals `score >= 0.5`;
- Dev/Audit patient disjointness and seed `2005`;
- threshold fitting uses Dev labels only;
- Audit labels do not affect threshold/group/signature definitions;
- Gate A/B/C counts mechanically imply the reported verdict;
- public summary contains no restricted patient-level material.

### P5 — Research decision

Record exactly one of:

- `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`;
- `STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE`;
- `STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION`;
- `INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT`.

On PASS, stop. Gate 02 is still not authorized.

On STOP/INCONCLUSIVE, terminate the current route without architecture rescue.

## Accepted Git artifacts after execution

Only public-safe aggregate evidence and final research records may enter Git:

- `experiments/gate-01-summary.json`;
- `experiments/gate-01-integrity-audit.md`;
- `research-decision.md`;
- a failure/reusable-memory record only if the result supports a genuinely cross-idea lesson;
- final `Handoff.md` / `docs/PLANS.md` state update.

Restricted unit rows, Dev threshold maps, target prescriptions, raw predictions, checkpoints, logs, and host-local paths remain outside Git.
