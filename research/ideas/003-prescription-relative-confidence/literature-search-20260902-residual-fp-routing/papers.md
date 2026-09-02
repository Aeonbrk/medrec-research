<!-- markdownlint-disable MD013 -->

# Closest-Work Papers — Residual False-Positive Routing

The table retains papers that materially affect the current candidate hypotheses. Scores are searcher triage aids, not acceptance judgments.

| Work | Venue / year | Type | What it already covers | Relevance to residual routing | Insight | Completeness | Numeric evidence |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| Chen et al., *Advancing Confidence Calibration and Quantification in Medication Recommendation* | KDD 2025 | pure method | medication-level confidence calibration with discernible binning; set-confidence quantification | establishes that raw medication confidence and bin-based calibration are already explicit MedRec research objects; a new idea cannot claim novelty from merely recalibrating score | 4 | 4 | 4 |
| Lv et al., *Awaken the Giant: Activating LLMs via Deep Model Guidance for Boundary-aware Medication Recommendation* | KDD 2026 | method + system | uses deep-model probabilities to identify boundary medications for LLM refinement | makes “uncertain/boundary medication selection” prior art; a new hypothesis must differ from absolute decision-boundary selection | 4 | 4 | 4 |
| Liu et al., *Machine learning-driven decision support for antibiotic optimization in typhoid fever based on patient profiles* | BMC Medical Informatics and Decision Making, 2026 | method + clinical evaluation | reports absolute Top1 confidence and Top1-Top2 probability margin as relative confidence | closest adjacent evidence that relative confidence can be operationalized; task is single-choice antibiotic optimization rather than multi-label medication-level FP routing | 3 | 4 | 4 |
| Yin et al., *HeteroMed: a heterogeneous graph knowledge-enhanced model for medication recommendation* | Health Information Science and Systems, 2026 | pure method | explicit drug expansion/inheritance with temporal factors and heterogeneous knowledge | materially weakens novelty of “continuation vs new medication” as a standalone idea | 4 | 4 | 4 |
| KERL, *Knowledge enhanced representation learning network for drug recommendation* | Information Processing & Management, 2026 | pure method | models historical medications with dual-path visit/drug representations and knowledge-enhanced patient representation | historical-medication semantics are already a central modeling target; a new temporal idea needs a narrower confidence-conditional claim | 4 | 4 | 4 |
| Wu et al., *Conditional Generation Net for Medication Recommendation* | 2022 | pure method | copy-or-predict mechanism chooses between historical medications and new predictions | long-standing direct prior art against treating continuation/new action semantics as novel by itself | 4 | 4 | 4 |
| Li et al., *Debiased medication recommendation through fusing frequent pattern and temporal medical records* | Neural Networks, 2026 | pure method | frequent prescription patterns plus historical-medication recalibration for low-frequency drugs | crowds both co-selection and temporal-history candidates; any new claim must be about conditional error routing, not generic usefulness of patterns/history | 4 | 4 | 4 |
| Wang et al., *Learning Collective Medication Effects via Multi-level Abstraction for Medication Recommendation* (MSAM) | arXiv 2601.19259, 2026 | pure method | models collective medication effects and medication-set abstractions over selected candidates and history | strong overlap for medication-set relational structure; simple PMI compatibility remains only a diagnostic route, not a new “combination modeling” claim | 4 | 4 | 4 |
| Kang et al., *Improving Rare Medication Recommendation with Counterfactual Data Augmentation and Large Language Models* (GenRxR) | RecSys 2026 / arXiv 2607.24829 | pure method | explicitly models relationships among co-recommended medications and rare-med context | further crowds generic co-selection/co-recommendation claims | 4 | 4 | 4 |
| Zhang et al., *HypeMed: Enhancing Medication Recommendations with Hypergraph-Based Patient Relationships* | ACM TOIS 2026 | pure method | hyperedge visit representation plus visit-conditioned retrieval over longitudinal and similar-patient evidence | makes “use patient/history context” too broad; a viable context hypothesis must isolate one target-free observable and its incremental value | 4 | 5 | 4 |
| Sanchez et al., *Multi-LLM Collaboration for Medication Recommendation* | arXiv 2512.05066 | method / preliminary | interaction-aware multi-LLM collaboration aimed at stability and calibration | adjacent to disagreement/corroboration; does not directly test frozen MedRec backbone disagreement conditional on primary score, but raises ordinary-ensemble novelty risk | 3 | 3 | 2 |

## Stable identifiers

- Chen et al. KDD 2025: DOI `10.1145/3690624.3709232`
- GiantMed KDD 2026: DOI `10.1145/3770854.3780297`
- Typhoid confidence study: DOI `10.1186/s12911-026-03528-8`
- HeteroMed: DOI `10.1007/s13755-026-00430-5`, PMID `41567975`
- DMRNet: DOI `10.1016/j.neunet.2026.109168`, PMID `42214931`
- MSAM: arXiv `2601.19259`
- GenRxR: arXiv `2607.24829`, RecSys 2026 DOI `10.1145/3773078.3831753`
- HypeMed: DOI `10.1145/3803851`, arXiv `2603.18459`
- Multi-LLM Collaboration: arXiv `2512.05066`
- COGNet: arXiv `2202.06588`

## Search-scope conclusion

Within the executed search, no retained work directly asks the following multi-label medication-level question:

> Conditional on a frozen medication's own confidence and trivial prescription-size effects, does its relative confidence position among the same visit's predicted medications provide held-out incremental information about false-positive status?

This is a search-scoped novelty delta, not a universal absence claim. The closest adjacent threats are medication-confidence calibration, absolute boundary selection, and Top1-Top2 relative confidence in single-choice antibiotic recommendation.
