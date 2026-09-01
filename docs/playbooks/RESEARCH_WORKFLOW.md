# Research Workflow

This workflow guides research routes through evidence gates using the MedRec Research Library. The workflow is organized around the fundamental unit of an **idea**: `Idea → Minimal Experiment → Evidence → Decision → revise / kill / continue → Mature to Paper`.

## Directory Philosophy

- **`research/ideas/<idea-name>/`**: Each idea has its own directory. Idea-specific hypotheses, minimal experiments, evidence, failures, and verdicts live here. Do not pre-create complex structures; grow them organically.
- **`research/baselines/`**: Infrastructure and baseline reproductions live outside scientific ideas. Baseline execution failures (e.g., mismatching Table 2) are not scientific idea failures.
- **`research/memory/`**: Cross-idea reusable lessons and terminal global failures go here. Do not clutter this with idea-specific iterations.
- **`papers/<paper-name>/`**: Once an idea is fully mature (evidence is solid, decision is to publish), it is promoted to a paper directory to manage the manuscript lifecycle (`ccfa.yaml`, `experiments/`, `manuscript/`). Do not duplicate this structure for early-stage ideas.

## Core Governance Rules

### 1. Code Promotion: Idea-Local Prototype → Reusable Capability → `src/`

- Unproven experiment scripts and exploratory probes remain local to `research/ideas/<idea>/` (or runtime scratch).
- Code is promoted to `src/medrec_research/` **only** when a capability survives falsification and is reused across multiple experiments or ideas. Never dump speculative idea logic into `src/`.

### 2. Experiment Scope: Hypothesis Selection vs. Claim Support

- **Idea Experiments (`research/ideas/<idea>/experiments/`)**: Designed strictly for *hypothesis selection*. The goal is falsification via the cheapest disconfirming test ("Should we continue or kill this idea?").
- **Paper Experiments (`papers/<paper>/experiments/`)**: Designed strictly for *claim support*. Includes full-scale multi-backbone benchmarking, exhaustive ablations, stress tests, bootstrap confidence intervals, and reviewer-requested verification for frozen paper claims.

### 3. Knowledge Retention: Idea-Specific Evidence vs. Cross-Idea Memory

- Idea-specific outcomes and failures stay inside `research/ideas/<idea>/`.
- Findings are promoted to `research/memory/` **only** when they represent cross-idea reusable methodology lessons (e.g. baseline traps, scalar reranking dominance) that constrain future research directions.

## Workflow

1. **Refine the question (Idea)**: Create a new directory under `research/ideas/`. State the falsifiable question, novelty threat, causal mechanism, and the cheapest disconfirming test.
2. **Freeze the protocol (Minimal Experiment)**: In Reproduction Mode, record the upstream data, split, feature, selection, and evaluation semantics without forcing the Unified Research Protocol onto them. In Comparison Mode, create the Dataset Manifest and declare feature timing, metrics, controls, Adaptation Budget, seeds, and stopping rules. No experiment begins without this gate.
3. **Plan and execute**: Freeze an immutable source revision on the Mac harness, submit the run to 319, and use registered baseline process adapters inside their remote Conda environments. Baseline processes emit target-free payloads; the core owns targets and real Prediction Records. Keep Prediction Records, checkpoints, logs, and restricted outputs under the 319 Local Data Root.
4. **Audit integrity (Evidence)**: Check data leakage, test-set selection, missing runs, adapter completeness, source identity, environment identity, eligible-visit coverage, and independent metric recomputation in the Core Evaluator Environment. A successful process exit is not a scientific pass. Record evidence in the idea's folder.
5. **Convert results to claims (Decision)**: Match every claim to audited evidence. Decide to revise the hypothesis, kill the idea, or continue. Idea-specific failures stay in the idea's folder.
6. **Preserve memory**: Promote genuinely reusable lessons or complete terminal failures to `research/memory/`. Accept concise Comparison Mode Run Records, aggregate results, audits, Failure Records, and claims into Git. Protocol Check Records may document harness health but cannot support claims. Leave scratch notes and timestamped logs local.

## Gate rules

Each stage consumes only accepted artifacts from the preceding stage. Any change to cohort, split, target, metric, adaptation budget, or selection rule invalidates downstream comparison evidence and returns the route to the protocol gate.

Negative evidence is first-class. A failed route becomes a Failure Record with mechanism, evidence anchor, scope, and reusable constraint. It must not become a permanent code hierarchy.

Test data is evaluation-only. When a workflow uses test results to choose a route, threshold, seed, prompt, checkpoint, or post-processing rule, label the run exploratory and create an untouched confirmatory test before making a Comparison Mode claim.

## Git acceptance

Git may contain public-safe protocols, Dataset Manifests, synthetic fixtures, registry metadata, accepted aggregate Run Records, Protocol Check Records, audits, claims, and Failure Records. Git may not contain EHR rows, split membership, patient-level outputs, checkpoints, credentials, private host details, traces, or raw workflow logs.

## Execution model

Use the MacBook Air as the harness terminal and `319-wild` as the execution plane. Follow the [remote execution playbook](REMOTE_319_EXECUTION_PLAYBOOK.md); local synthetic execution proves harness behavior only.
