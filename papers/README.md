<!-- markdownlint-disable MD013 -->

# Paper Stage Projects

This directory contains mature, publication-facing research packages.

## Purpose & Scope

When a scientific hypothesis from `research/ideas/<idea>/` survives minimal falsification and earns a `graduate` verdict, it transitions into a dedicated paper project in this directory (e.g. `papers/medrec-safety-kdd26/`).

Do not create paper projects for early-stage or speculative ideas. Early-stage ideas belong in `research/ideas/`.

## Experiment Boundary: Idea vs. Paper

| Stage | Location | Primary Purpose | Scope & Nature |
| :--- | :--- | :--- | :--- |
| **Idea Stage** | `research/ideas/<idea>/experiments/` | **Hypothesis Selection** | "Should we kill, revise, or advance this idea?" Cheapest disconfirming tests, proxy checks, minimal mechanism probes. |
| **Paper Stage** | `papers/<paper>/experiments/` | **Claim Support** | "How thoroughly does the evidence support our candidate paper claims?" Full-scale multi-backbone benchmarks, comprehensive ablations, robustness stress tests, bootstrap confidence intervals, and reviewer-requested verification. |

### Claim Evolution vs. Protocol Freezing

Entering Paper stage means committing to a cohesive storyline and candidate claim set, **not** that scientific claims are permanently frozen:

- **What is frozen**: The confirmation protocol, evaluation contract, and analysis plan — preventing cherry-picking, post-hoc threshold tuning, or metric shifts.
- **What evolves**: The candidate scientific claims themselves. Full-scale experiments, multi-backbone runs, or reviewer scrutiny may force claims to be narrowed, reframed, or qualified. If the candidate mechanism fails under full testing, the paper storyline must be honestly downgraded.

Each paper directory conforms to the CCFA paper lifecycle and contains:

- `ccfa.yaml`: Paper lifecycle metadata, stage gates, and artifact manifest.
- `manuscript/`: LaTeX source (`main.tex`), figures, and BibTeX references (`references.bib`).
- `experiments/`: Claim-support experiment scripts, configuration, and audited tabular outputs.
- `tables/` & `figures/`: Rendered publication-ready assets.
- `reviews/`: Reviewer reports, AC meta-reviews, and revision ledgers.
- `submission/`: Anonymized submission bundles, camera-ready packages, and compliance checks.
