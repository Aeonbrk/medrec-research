# ARIS Research Workflow

ARIS is the control plane for every first-party research route. The workflow is idea-agnostic: a route may change, but it must cross the same evidence gates and use the same MedRec Research Library.

## Workflow

1. Refine the question. Use ARIS discovery and literature skills to state the falsifiable question, novelty threat, causal mechanism, and cheapest disconfirming test. Store draft work in ignored ARIS runtime paths.
2. Freeze the protocol. In Reproduction Mode, record the upstream data, split, feature, selection, and evaluation semantics without forcing the Unified Research Protocol onto them. In Comparison Mode, create the Dataset Manifest and declare feature timing, metrics, controls, Adaptation Budget, seeds, and stopping rules. No experiment begins without this gate.
3. Plan and execute. Freeze an immutable source revision on the Mac harness, submit the run to 319, and use registered baseline process adapters inside their remote Conda environments. Baseline processes emit target-free payloads; the core owns targets and real Prediction Records. Keep Prediction Records, checkpoints, logs, and restricted outputs under the 319 Local Data Root.
4. Audit integrity. Check data leakage, test-set selection, missing runs, adapter completeness, source identity, environment identity, eligible-visit coverage, and independent metric recomputation in the Core Evaluator Environment. A successful process exit is not a scientific pass.
5. Convert results to claims. Match every claim to audited evidence. Calibration, retrospective DDI, and label agreement cannot be promoted to clinical-safety claims.
6. Preserve memory. Accept concise Comparison Mode Run Records, aggregate results, audits, Failure Records, and claims into Git. Protocol Check Records may document harness health but cannot support claims. Leave Workflow Traces, prompts, scratch notes, and timestamped logs local.

## Gate rules

Each stage consumes only accepted artifacts from the preceding stage. Any change to cohort, split, target, metric, adaptation budget, or selection rule invalidates downstream comparison evidence and returns the route to the protocol gate.

Negative evidence is first-class. A failed route becomes a Failure Record with mechanism, evidence anchor, scope, and reusable constraint. It must not become a permanent code hierarchy.

Test data is evaluation-only. When an ARIS workflow uses test results to choose a route, threshold, seed, prompt, checkpoint, or post-processing rule, label the run exploratory and create an untouched confirmatory test before making a Comparison Mode claim.

## Git acceptance

Git may contain public-safe protocols, Dataset Manifests, synthetic fixtures, registry metadata, accepted aggregate Run Records, Protocol Check Records, audits, claims, and Failure Records. Git may not contain EHR rows, split membership, patient-level outputs, checkpoints, credentials, private host details, ARIS traces, or raw workflow logs.

## Recommended ARIS routing

Use project-local skills under `.agents/skills/`. Typical routing is `research-refine-pipeline` or `idea-discovery`, then `experiment-plan`, `run-experiment`, `experiment-audit`, `result-to-claim`, and the relevant writing or review workflow. Skill choice does not waive protocol gates.

Use the MacBook Air as the ARIS terminal and `319-wild` as the execution plane. Follow the [remote execution playbook](REMOTE_319_EXECUTION_PLAYBOOK.md) before `run-experiment`; local synthetic execution proves harness behavior only.
