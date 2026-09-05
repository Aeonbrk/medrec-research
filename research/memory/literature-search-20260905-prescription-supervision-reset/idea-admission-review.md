<!-- markdownlint-disable MD013 -->

# Pre-Idea Admission Review — Selective Prescription Supervision

## Verdict

`PIVOT_WITH_RESCUE_ROUTE / DO_NOT_CREATE_IDEA_006`

The supervision-asymmetry problem is scientifically plausible, but the current project cannot yet turn it into a CCF-A-ready method claim without either collapsing into generic PU/noisy-label learning or introducing an unvalidated latent clinical target.

**Weighted score**: `3.54 / 5.00`

**Confidence**: medium-high. Closest MedRec noise/debiasing work and generic PU/MNAR recommendation were searched; the exact future-as-privileged-supervision variant remains a narrower novelty uncertainty.

**Development potential**: medium, conditional on a materially stronger supervision/evaluation source.

## Normalized candidate after optimizer refinement

### Task

Standard longitudinal medication recommendation under the current structured EHR pipeline.

### Gap

A retrospective prescription vector records medications that were selected, but its zero entries need not constitute an exhaustive set of clinically negative alternatives. Standard multi-label objectives nevertheless apply negative gradients to all unprescribed medications.

### Strongest optimized mechanism

Use **training-only future trajectory as privileged information** to estimate which negative labels are inconsistent with surrounding longitudinal medication/state patterns. A deployable current/past-only student would selectively attenuate negative gradients judged low-reliability. The method would never use future visits at inference and would not hard-relabel an unprescribed medication as clinically correct.

### Intended contribution type

Learning objective / supervision mechanism, not a new encoder and not post-hoc reranking.

## Closest-work subtraction

| Prior | What is already covered | Remaining delta after subtraction |
| --- | --- | --- |
| KRAM (ESWA 2026) | MedRec label-noise robustness, co-denoising, label refinement | Endogenous selective prescription observation is different from injected random replacement/addition, but the practical objective can still look like another noisy-label reweighting method |
| DMRNet (Neural Networks 2026) | Frequency imbalance and historical drug recurrence | Future-as-privileged reliability is not the same as rarity/history recalibration, but a history-driven implementation could collapse into this cluster |
| FineMed (Information Sciences 2026) | Diagnosis-level supervision / fine-grained subrecommendation | Prescription-observation semantics remain different, but generic 'better supervision' is not enough |
| WSDM 2020 + NeurIPS 2025 implicit-feedback work | PU/MNAR formulation and counterfactual observation modeling | Generic unobserved-not-negative and propensity correction are fully prior art |
| Correct-and-Weight 2026 | Simple PU-style uncertain-negative correction | Any loss-only uncertain-negative weighting must beat this idea class as a killer simple control |

## Strict reviewer panel

### Field expert

**Best argument**: the target-label assumption is upstream of architecture and potentially affects the whole MedRec field.

**Rejection-grade concern**: the project has evidence that one historical set may under-specify acceptable therapy, but no cohort-level ground truth for the latent acceptable-treatment set. The paper could diagnose a target mismatch it cannot validate.

**Repair condition**: obtain an independently grounded multi-valid treatment or negative-reliability signal at meaningful scale, without recreating Idea 005's taxonomy-semantic shortcut.

### Method expert

**Best argument**: future trajectory as training-only privileged information is a coherent way to alter supervision without deployment leakage.

**Rejection-grade concern**: future medication occurrence is not evidence that the medication should have been prescribed at the earlier visit. A future-derived reliability target can confound real treatment changes with label unreliability. Soft weighting reduces but does not remove this identification problem.

**Repair condition**: introduce an identifiable observation model or independently justified anchor that separates prescribing-policy variation from genuine state-dependent treatment change.

### Experiment expert

**Best argument**: the current structured pipeline makes the mechanism cheap to implement, and generic loss/noise/history controls are available.

**Rejection-grade concern**: standard MIMIC F1/Jaccard can only show improved agreement with the same observed prescription labels; they cannot demonstrate recovery of clinically valid hidden positives. If the claim is narrowed to benchmark agreement, the method risks becoming ordinary regularization.

**Repair condition**: add a compatible evaluation source that distinguishes acceptable alternatives from true negatives, or reformulate the claim so the new supervision target is directly observable and still scientifically nontrivial.

### AC / venue expert

**Best argument**: a principled supervision problem with architecture-agnostic gains could fit KDD/WWW/AAAI-family CCF-A venues.

**Rejection-grade concern**: under the current evidence package, reviewers can reasonably describe the submission as 'PU/noisy-label learning applied to MIMIC medication recommendation' with no independently validated latent target.

**Repair condition**: the mechanism must create a clear MedRec-specific learning problem and a decisive evaluation unavailable to generic PU baselines.

### Skeptical prior-art expert

**Best argument**: the exact combination of selective prescription labels and trajectory-privileged reliability was not found as a central MedRec method in the bounded search.

**Rejection-grade concern**: the conceptual components are individually established by KRAM, DMRNet/history-aware MedRec, PU/MNAR recommendation, and false-negative weighting. Naming their intersection is not enough.

**Repair condition**: show a non-obvious interaction or identifiability result that generic PU and history-aware baselines cannot express.

## Rubric

| Dimension | Weight | Score | Confidence | Main deduction | Repair condition |
| --- | ---: | ---: | ---: | --- | --- |
| Problem importance | 12 | 4 | 4 | Important upstream assumption, but clinical target mismatch is not yet quantified in this cohort | Cohort-level admissible supervision evidence |
| Novelty against likely prior work | 14 | 3 | 4 | Strong collision from KRAM + generic PU/MNAR + current false-negative losses | Domain-specific observation mechanism beyond loss transfer |
| Conceptual innovation | 12 | 4 | 3 | Privileged future reliability is interesting, but may reduce to temporal denoising | Identifiable mechanism and nontrivial interaction |
| Method soundness | 14 | 3 | 4 | Future prescription does not establish earlier appropriateness | Reliable anchor / observation-model assumption |
| Elegance and simplicity | 8 | 4 | 4 | Potentially small architecture footprint | Preserve objective-level simplicity |
| Feasibility under resources | 8 | 4 | 4 | Current data suffice for implementation, but stronger validation may not | Low-cost compatible ground truth or external validation |
| Experimental convincibility | 10 | 3 | 4 | Existing labels cannot validate the latent clinical claim | Multi-valid target / reliable-negative evaluation |
| Venue and audience fit | 8 | 4 | 3 | Potential KDD/WWW/AAAI fit if mechanism matures | Raise soundness and evidence |
| Timeliness and topic heat | 6 | 4 | 4 | Label quality, debiasing, and prescribing evaluation are active | Keep framing precise |
| Risk-adjusted acceptance potential | 8 | 3 | 4 | Current likely reviewer framing is incremental PU/noise adaptation | Resolve identifiability and evaluation before investing |

Weighted score:

$$
\frac{354}{100}=3.54/5.
$$

## Why no Idea 006 is created

The project's current policy is to create a new Idea only when a research hypothesis deserves a bounded unit of research time toward a method paper. Here, the next decisive missing input is not another model experiment on the same labels; it is an admissible supervision/evaluation source or an observation model that makes the latent target identifiable.

Creating an Idea and running a sandwich-gap / future-return diagnostic would risk restarting the diagnostic treadmill without resolving the reviewer-grade objection.

## Salvageable ingredient

Keep only this reusable insight:

> **Medication-recommendation supervision should distinguish the observed prescribing action from claims about exhaustive clinical treatment relevance.**

This is a research-space constraint, not yet an Idea.

## Reopen condition

Reopen this family only if at least one of the following becomes available without disproportionate infrastructure cost:

1. a material expert- or guideline-grounded multi-valid treatment target compatible with the action space;
2. an observable reliable-negative / selective-label mechanism with defensible clinical semantics;
3. a new formal objective whose target is identifiable from current longitudinal EHR data and whose novelty survives KRAM plus generic PU/MNAR controls.

Until then the project state remains `NO_HIGH_VALUE_DIRECTION_YET`.
