# Current research state — 2026-09-18

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current position

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Human-facing phase: ARCHITECTURE SEARCH — POST-ECRC RESET
Paper Experiment Contract: v1.0 + v1.1 + v1.2 amendments CURRENT
Paper claim: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Historical `Stage -1*`, Gate, Reproduction Mode, and Comparison Mode names remain provenance only. New paper-facing work is governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`

The active execution-routing decision is:

- `research/memory/decisions/2026-09-17-evidence-first-execution-sequencing.md`

## Development philosophy

The proposed method may receive substantially greater Train/Dev research effort than external baselines. Equal cumulative architecture/HPO budgets are not a fairness requirement.

Fairness requires that a competitor is not weakened by our execution choices: trustworthy method identity, required assets, legal information budget, reasonable training horizon, declared Dev-only checkpoint/operating-point selection, and source-informed investigation of obvious failures. Baseline tuning is an anti-underoptimization safeguard, not a symmetric-search requirement.

Central ablations and matched controls also need reasonable Dev selection when mechanically reusing the full model's recipe would materially disadvantage them.

For new project-owned initial DEVELOPMENT screens, the canonical RNG convention is inherited from MoleRec: `torch=1203`, CUDA PyTorch `1203`, Python `random=1203`, and NumPy `2048`. Internal matched controls share that convention. External published baselines instead preserve their source-native seed policy when available. A survivor must still expand to a predeclared multi-seed stability experiment; the canonical seed is not stability evidence.

## Valid development evidence

Medication-specific evidence selection remains the strongest surviving mechanism.

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV native | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Current interpretation:

> In the tested Train/Dev comparisons, medication-specific evidence selection moved accuracy in the same favorable direction on MIMIC-III and MIMIC-IV surfaces. Two new matched MIMIC-III seed pairs reproduce the favorable Jaccard/F1/PRAUC and lower-DDI direction; medication cardinality is mixed. This remains development evidence, not a final superiority or safety claim.

These results are `DEVELOPMENT` evidence. They are not final-table superiority, SOTA, universal safety improvement, or a calibration claim. The fixed-131/generalized MICA implementation passed exact no-training equivalence on the 131-medication path.

MICA remains a possible building block and mechanism control, not a mandatory backbone or permission gate for a distinct architecture.

### Terminated mechanism screens

- **Drug-Conditioned Precedent Memory (DCPM)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seed `20260921`, 60 complete epochs, 1,079,428 parameters in both arms, zero Test access). Tested whether candidate-specific query attention over cross-patient Train precedents improves prediction over a shared patient query. Result: $\Delta J = -0.001403$ (DCPM 0.542203 vs SharedPrecedent control 0.543606), $\Delta \text{DDI} = +0.002181$. Falsified and terminated per the frozen decision boundary (`KILL_DCPM_MECHANISM`); no post-hoc tuning or re-test authorized. Decision note: `research/memory/decisions/2026-09-18-dcpm-mechanism-screen-falsification.md`.
- **Route-Factored Medication Recommendation (RouteFact)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seed `20260922`, 60 complete epochs, 914,497 parameters in both arms, source revision `8eee27ad88b63990cc8f1c5355b4a47bd84c7923`, zero Test access). Tested whether forcing medication prediction through a noisy-OR over Train-supported multi-hot administration routes improves prediction over direct medication prediction with identical auxiliary route supervision. Result: $\Delta J = -0.008252$ (RouteFact 0.534931 vs RouteAux control 0.543183), $\Delta \text{F1} = -0.006919$, $\Delta \text{PR-AUC} = -0.005145$, $\Delta \text{DDI} = -0.001539$, $\Delta \text{AvgMed} = +0.115149$. Falsified and terminated per the frozen decision boundary (`KILL_ROUTEFACT_MECHANISM`); no post-hoc tuning, taxonomy merging, loss sweeps, or re-test authorized. Decision note: `research/memory/decisions/2026-09-18-routefact-mechanism-screen-falsification.md`.
- **Exact-Cardinality Regimen Choice (ECRC)**: Evaluated on `mimic-iii-canonical-131-paper-dev-v1` (seeds `20260923` and `20260924`, 60 complete epochs across 6 lanes, 437,571 parameters in all four variants, source revision `c668a8e4a194c92a8933068e8ff99991d014c185`, zero Test access). Tested whether regimen cardinality acts as an informative decision context that changes named-medication preference utilities ($u_m(x, K)$) under exact fixed-cardinality and BCE formulations. Result: mean exact oracle-K $\Delta J = +0.000341$ (+0.034%, failing the $+0.004$ gate), mean exact predicted-K $\Delta J = -0.000491$ (negative deployable value), mean candidate Jaccard $0.531769$ (below the $0.537316$ floor). Falsified and terminated per the frozen decision boundary (`KILL_ECRC_CHOICE_MECHANISM`); no size-head tuning, rank sweeps, or re-tests authorized. Decision note: `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-verdict.md`.

## Benchmark strategy

Default paper routing remains:

- **MIMIC-III canonical-131**: main literature-facing comparison surface.
- **MIMIC-IV harmonized/common-131**: default main MIMIC-IV literature-facing comparison surface, pending canonical-lineage identity audit.
- **MIMIC-IV native-173**: broader-target validation surface.

`Literature-facing` does not mean identical benchmark identity. Equal medication count does not establish equal cohort, preprocessing, split, eligibility, input semantics, or evaluator.

Before Paper Candidate Freeze, benchmark roles may change only for structural reasons such as faithful-baseline feasibility, missing scientific assets, target-space relevance, or the final mechanism's dependence on long-tail/cardinality structure. They may not change because one observed surface is easier to win.

The harmonized-131 audit is now split into:

- **run-critical checks now**: exact coordinate identity, target/DDI alignment, projection semantics, zero-support handling, and empty-target/eligibility rules;
- **paper-claim checks asynchronously**: how far this surface actually matches named literature lineages and what terminology is defensible.

MIV harmonized131 and native173 are target-space views of the same underlying MIMIC-IV population, not independent datasets. Native173 with only internal controls supports an internal broader-target/mechanism claim; competitive superiority there requires at least one credible external comparator relevant to the claim.

## Competitive baseline fidelity state

Temporary project-side MoleRec, GAMENet, and RETAIN outputs from the former Stage -1G path remain diagnostic only and must not support method ranking or paper superiority claims. The current ARMR lane is separate and source-pinned.

MoleRec remains the first recovery priority. The released source-native training lane is still running and has no terminal artifact; because that entrypoint uses its own source split, partial or source-split values cannot enter the frozen paper-profile table. A separate source-faithful adapter now binds the canonical MIMIC-III profile: its one-epoch smoke completed as non-evidence with no Test access, and its 50-epoch formal lane is running detached under the same pinned source and environment. Until the formal lane reaches a terminal artifact and independent audit, its partial values remain excluded.

- ARMR current-profile formal recovery is complete and passed an independent integrity audit. It is a credible DEVELOPMENT external anchor, not a Paper Candidate or final superiority claim;
- promote SSPNet when structured/set prediction becomes the active hypothesis, SSPNet is confirmed as the closest relevant comparator, and a trustworthy execution path exists. Bounded probes now reach finite forward and one-patient source training/evaluation after explicit mechanical edge-case isolation; they remain non-evidence and the frozen-profile adapter still requires independent source-fidelity review.
- otherwise keep SSPNet as a bounded source/CPU recovery task while the closest-work distinction remains unresolved.

SafeDrug rises in priority only if safety/molecular claims become central. GAMENet, RETAIN, and HypeMed are added only when they fill a distinct scientific role.

Architecture work does not wait for baseline completion, but Paper Candidate Freeze requires credible external positioning.

## Architecture status

### Terminated screen: ECRC cardinality context (2026-09-18)

The bounded DEVELOPMENT screen for **cardinality-conditioned named-medication choice** (ECRC) completed all 60 epochs across 6 lanes on physical GPUs 0–5 on 319.

Result:

- Exact primary oracle-K $\Delta J = +0.000341$ (failing the $+0.004$ mechanism gate; triggering $\le +0.002$ kill rule).
- Exact primary predicted-K $\Delta J = -0.000491$ (negative deployable value; Seed B $\Delta J = -0.001015$).
- Absolute candidate Jaccard: $0.531769$ (below the $0.537316$ anchor floor).
- Verdict: `KILL_ECRC_CHOICE_MECHANISM`.

Under the tested rank-8 ECRC formulation and DrugQuery evidence path, conditioning named-medication utilities on regimen cardinality produced negligible oracle-K re-ranking value. That formulation is closed and receives no rescue. The result is strong negative evidence for this mechanism, not a universal proof that every future model containing a cardinality variable must fail.

Artifact: `research/prototypes/ecrc-cardinality-context/ecrc-comparison.json`.
Decision note: `research/memory/decisions/2026-09-18-ecrc-cardinality-context-screen-verdict.md`.

Direct Partial Regimen Assignment / structured-set prediction remains an untested candidate, not an admitted paper method.

If pursued, its question must be framed around explicit set-level competition, variable cardinality, and uniqueness in training/decoding—not the false claim that independent-label models contain no medication dependence, and not an unsupported claim that anonymous slots are clinical regimen roles.

Expensive structured training may start before baseline recovery or MICA stability finishes once all of the following are true:

- legal input/output semantics are fixed;
- the candidate has a falsifiable computation-level distinction from the closest known work;
- the minimum model and strongest matched independent-label control are defined;
- a valid end-to-end run can execute without adding unrelated modules.

If the closest-work audit cannot explain the computational distinction by approximately 2026-09-21, pause expensive structured training rather than training first and inventing novelty later.

The first full architecture screen should answer only whether the structured model beats a credible matched independent-label control, whether cardinality/operating-point effects explain the gain, and whether the gain is worth the complexity. Add one cardinality-aware control only when it can falsify the mechanism. Do not force a confounded 2×2.

## Near-term evidence routing

The current sequencing is dependency-driven rather than stage-serial.

### MIMIC-III common contract

Before the next MIII runs, freeze only what can change their interpretation: patient split, legal information budget, target/eligible-event semantics, core evaluator, and joint Dev checkpoint/operating-point selection.

### MICA stability

The default two new paired MIII seeds per arm under the frozen profile are now complete:

```text
SharedPool seed A / DrugQuery seed A
SharedPool seed B / DrugQuery seed B
```

Add a third paired seed only when MICA remains a central component/control, the two pairs disagree and change routing, or otherwise-ready GPU capacity makes completion cheaper than another decision boundary. The current two-pair direction is stable for accuracy/PRAUC/DDI but not medication cardinality, so it supports continued development without forcing a third pair now.

Historical single-seed evidence remains separate unless it exactly satisfies the new run contract.

### Early cross-surface falsification

Do not wait for complete MIII three-seed evidence before testing a promising new architecture on MIV.

After the first valid MIII full/control result and at least one additional paired check show a signal worth pursuing, start sentinel full/control pairs on:

- MIV harmonized/common-131;
- MIV native-173.

If a known implementation/mechanism fault is already visible on MIII, fix or kill it before propagating the faulty model across surfaces.

## GPU and human-bandwidth policy

Treat eight GPUs as a ready-task queue, not fixed phase slots.

Priority order:

1. matched full/control pairs that can change architecture routing;
2. closest/strong external comparator recovery;
3. early second-surface falsification;
4. additional paired seeds needed for a live decision;
5. secondary analyses.

GPU occupancy is not an objective. Keep human implementation bandwidth narrow: at most one actively changing architecture and one baseline recovery requiring heavy code modification at the same time. Additional finished implementations may train concurrently.

## Decision boundaries and management targets

Continue a formulation when matched controls show a worthwhile effect/trade-off, repeated paired evidence does not expose clear instability, cardinality/operating-point controls do not explain the result away, closest-work distinction remains valid, and complexity is commensurate with value.

Allow one bounded scientific redesign only for a concrete observed failure with a pre-written expected fix. Preventable implementation bugs do not consume the scientific redesign allowance.

Kill the tested formulation when full-budget repeated evidence does not support value, a reasonable cardinality control explains the gain, the result depends on unfair information/control choices, added cost is unjustified, or the one evidence-driven redesign fails.

Reset the architecture family when closest work already occupies the core computation, failure points to the structured-set hypothesis itself, or continuation degenerates into unrelated retrieval/DDI/refinement patches. Allow at most one family reset in this research cycle.

Management targets, not scientific pass criteria:

- **2026-10-05**: current architecture route decision — continue, bounded redesign, or kill/reset;
- **2026-10-09 to 2026-10-13**: normal-path target for a credible Paper Candidate;
- **2026-10-16**: hard stop for this architecture-search cycle;
- **2026-10-26 to 2026-11-04**: target frozen-confirmation window only if prerequisites are complete;
- **2026-11-11 to 2026-11-18**: target first complete manuscript/evidence package.

If no survivor exists by 2026-10-16, stop the current architecture search and reassess the paper route rather than opening another rescue sequence.

## Final evidence boundary

A Paper Candidate requires more than internal repeatability: the method difference must be experimentally identifiable; the core effect cannot be a single-seed event; both main paper surfaces need credible external reference positioning; obvious cardinality/leakage/capacity/control-quality explanations must be addressed; DDI/cardinality/efficiency costs must be known; and the closest comparator relevant to the final claim cannot remain an unresolved conceptual omission.

Stable small internal gains do not automatically justify a Paper Candidate when credible external methods remain clearly stronger unless a different evidence-backed safety/efficiency/robustness contribution supports the claim.

MIMIC-IV Test remains sealed throughout reference setup and architecture search. Harmonized131 and native173 derived from the same MIMIC-IV population must be handled inside one frozen confirmation cycle; observing one Test surface cannot be used to redesign the other and still call it untouched.

## Next action

Return to architecture-family search after ECRC termination. Do not rescue ECRC by changing rank, size head, loss weighting, temperature, or decoder. The next project-owned initial architecture screen uses the canonical MoleRec development RNG convention from contract v1.2 and a strong matched control under the same convention. Search should change representation, information flow, prediction granularity, supervision, or decision process rather than another cardinality-conditioned correction. Detached baseline recovery may continue independently. Test remains sealed.
