<!-- markdownlint-disable MD013 -->

# Research-space reorientation: architecture-first open search

This document is a directional synthesis, not a novelty gate or authorization checklist. Current numerical/state authority lives in [`current-research-state.md`](current-research-state.md).

## Why the project is stepping back

The project has accumulated enough bounded negative evidence that continuing to optimize local corrections around the current backbone is no longer the best default use of research time.

The important pattern is not `all prior ideas failed`. It is more specific:

- several score/routing/reranking signals were absorbed by strong direct controls;
- fixed-cardinality GraphRefine exposed a small ranking signal but not a paper-scale gain;
- learned medication-medication residual dependence exists statistically, but a frozen-unary W-only Oracle adds only `+0.000257` Jaccard above MoleRec;
- persistent medication states and residual clinical-need feedback did not add mechanism value in their tested formulations;
- two structured-set v0 formulations were weak;
- immediate-next-visit privileged state supplied negligible teacher headroom;
- faithful modern HypeMed and Rx-Expert did not improve the best observed canonical accuracy reference;
- a very high reported DMGExNet score is not comparable under the project's point-in-time information budget.

These results justify an **architecture reset**, not a universal claim that graphs, interactions, retrieval, structured prediction, MoE, or longitudinal modeling are exhausted.

## What should be deprioritized

The following are poor default bets **when repeated with the same scientific role**:

1. `strong MoleRec unary + small residual correction/reranker` as the central contribution;
2. the tested symmetric pairwise medication residual interaction as the claimed missing source of set accuracy, absent a new source of headroom;
3. repeated cardinality/threshold/loss tuning to rescue a weak architecture;
4. the exact NeedCover residual-coverage formulation;
5. the exact persistent MedState formulation;
6. the tested RxDiffSet and TheraCompose v0 formulations;
7. the tested immediate-next-visit FutureGraphKD signal;
8. the unsupported RxUnit `(drug,dose,route)` target under current timing semantics;
9. default hunting for another public backbone solely because recent backbones look more sophisticated.

`Deprioritized` means `do not repeat an equivalent formulation without a new mechanism or new evidence`. It does not mean the vocabulary used by the formulation is prohibited.

## What remains open

The search space remains broad. A next method may use entirely new or familiar primitives if their composition changes capability, information flow, inductive bias, credit assignment, or decision process.

Examples of high-impact search axes:

- model the patient–medication decision at a different granularity;
- let different candidate decisions acquire different clinical evidence;
- represent uncertainty, alternatives, or regimen construction explicitly rather than as a post-hoc correction;
- formulate medication recommendation as a structured sequential/list/set decision when the structure is supported by a real modeling rationale or source of headroom;
- use conditional computation when routing changes information flow rather than only parameter count;
- introduce supportable supervision unavailable to the current unary model but still deployable at inference;
- build a new architecture from scratch without inheriting MoleRec's representation or decoder;
- combine known mechanisms coherently when their interaction produces a different capability or inductive bias.

This list is deliberately non-exhaustive.

## Search discipline

The next search should begin with:

> If MoleRec and all current prototypes did not exist, what is the most natural formulation of this prediction problem under the available EHR information and point-in-time constraint?

Then search both Medication Recommendation and adjacent fields for mechanisms. Do not force the search to preserve a previous successful component.

For each serious candidate, write two short answers before implementation:

1. what capability / object / interaction / information flow / inductive bias / decision process changes;
2. what matched strong control would test whether that change, rather than extra capacity or optimization budget, causes the gain.

If the answer is mainly `more capacity`, `another GNN`, `another loss`, or `another reranker`, the scientific mechanism is not yet clear enough.

## Novelty posture

Novelty matters for publication but should not paralyze early architecture discovery.

Early stage:

- rule out an obvious duplicate;
- identify the strongest nearby control;
- prototype the scientific mechanism cheaply.

After empirical survival:

- verify closest work and novelty from primary sources;
- refine contribution boundaries;
- run strong baselines and decisive ablations;
- invest in multi-seed/statistical claim support.

A combination of known primitives is acceptable when the interaction creates a materially different capability. Do not require every component to be novel.

## Failure-memory posture

Use old failures as **priors**:

- avoid rerunning equivalent methods;
- reuse lessons about cardinality, baseline fidelity, information budget, target supportability, and strong controls;
- do not convert prior failures into global architecture bans;
- revisit a component when it plays a materially different role or when materially new evidence changes the premise.

Historical literature maps and review packets remain valuable discovery aids, but their dated `CLOSED/CROWDED/PRIOR ART` labels are not current admission gates.

## Next execution

Default path:

```text
broad architecture / adjacent-method search
→ one Rank-1 candidate
→ one seed, one main config, Train/Dev
→ strong baseline + decisive matched control/ablation
→ material signal? continue
→ clear hidden implementation/decoding issue? redesign once
→ otherwise kill and reset family
```

A new formal Idea is **not required** merely to test a cheap architecture. It may still be appropriate before training when target semantics, privileged information, or another scientific entitlement must be frozen first.

Do not use held-out evaluation resources for architecture selection.

The goal of the next cycle is not to prove novelty first. It is to discover a mechanism with enough empirical and scientific signal to deserve the cost of a real paper workflow.
