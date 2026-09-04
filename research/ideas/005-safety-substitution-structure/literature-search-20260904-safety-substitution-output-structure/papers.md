<!-- markdownlint-disable MD013 -->

# Literature Set — Safety Substitution and Output Structure

Search cutoff: 2026-09-04.

This file records the closest-work set used to bound Idea 005. It is not a field survey.

| Work | Directly relevant content | Boundary for Idea 005 |
| --- | --- | --- |
| LEAP, KDD 2017, *Learning to Prescribe Effective and Safe Treatment Combinations for Multimorbidity* | Sequential decoder models medication-label dependencies and uses safety knowledge in reward design. | Idea 005 cannot claim first dependency-aware or safety-aware set decoding. |
| MSAM, arXiv:2601.19259, 2026, *Learning Collective Medication Effects via Multi-level Abstraction for Medication Recommendation* | Builds higher-level medication abstractions to capture collective effects. | Generic medication grouping / hierarchy is crowded. |
| FineMed, Information Sciences 2026, DOI `10.1016/j.ins.2026.123930` | Diagnosis-aware sub-recommendations, drug-disease correspondence, diagnosis enhancement; partially relies on LLM-assisted mapping. | Idea 005 must not reduce to diagnosis-specific medication mapping. |
| RES-MR, SIGIR 2026, DOI `10.1145/3805712.3809604` | Risk-aware reasoning for explainable and safe medication recommendation. | Generic personalized safety / efficacy trade-off is not enough. |
| Beyond Accuracy, JBI 2026, DOI `10.1016/j.jbi.2026.105072` | Argues that safety evaluation must consider treatment goals and undertreatment rather than only low adverse-interaction rates. | Motivates suppression-vs-treatment-preservation analysis; does not establish the proposed mechanism. |
| KATMed, 2026 | Uses positive clinical associations and negative contraindication knowledge as differentiable constraints. | Generic positive/negative knowledge injection is not new. |
| HeteroMed / KERL family | Models medication-set expansion, continuation, relations, and longitudinal reuse. | Generic set relation or history modeling is not the novelty delta. |

## Stable source links

- LEAP: <https://kdd.org/kdd2017/papers/view/leap-learning-to-prescribe-effective-and-safe-treatment-combinations-for-mu>
- MSAM: <https://arxiv.org/abs/2601.19259>
- FineMed: <https://doi.org/10.1016/j.ins.2026.123930>
- RES-MR: <https://doi.org/10.1145/3805712.3809604>
- Beyond Accuracy: <https://doi.org/10.1016/j.jbi.2026.105072>

## Retained novelty question

The retained question is deliberately narrower than medication dependency, hierarchy, diagnosis-aware recommendation, or safety-aware loss:

> When safety pressure removes confidence from one action, is there a repeated output-structure failure in which decision mass should be reallocated rather than simply suppressed, and can a later method exploit externally defensible alternative-choice structure?

Gate 01 addresses only the first clause.
