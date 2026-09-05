<!-- markdownlint-disable MD013 -->

# Literature Search: Prescription Supervision Semantics in Medication Recommendation

Date: 2026-09-05

Search purpose: one bounded exploratory reset after `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`, feeding pre-Idea optimization rather than establishing a final novelty verdict.

Target venue/family: first formal method paper, at least CCF-A venue family.

Source-quality policy: applied. Primary publisher/proceedings pages, PubMed, and stable archival pages were preferred; policy-excluded sources were not used in the final set.

## Summary

- **Closest-work clusters**: MedRec label-noise robustness; long-tail/debiasing; fine-grained supervision; clinically non-exhaustive prescription evaluation; generic positive-unlabeled/MNAR recommendation.
- **Opportunity map**: the strongest remaining candidate is not another encoder but a change in supervision semantics: observed prescriptions are positive treatment actions, while an unprescribed medication is not automatically a reliable clinical negative.
- **Strongest baseline families**: standard BCE/multi-label objectives; KRAM-style noisy-label refinement; class-balanced/asymmetric/focal or label-smoothed losses; generic PU/MNAR recommenders; temporal/history recalibration such as DMRNet.
- **Novelty risk**: a direct transplant of nnPU, MNAR correction, or a generic false-negative weighting loss is insufficient. The method must identify a MedRec-specific observation mechanism or supervision structure and show value beyond these controls.
- **Recommended next action**: `ccf-idea-optimizer` on exactly one hypothesis family, followed by `ccf-idea-reviewer`. Do not create Idea 006 unless the optimizer can produce a domain-specific, falsifiable mechanism rather than a generic loss substitution.

## Paper Table

| # | Title | Year | Venue/source | Stable link | Type | Insight | Completeness | Numeric evidence | Overall | Relevance |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | KRAM: Knowledge-driven robust training against label noise for medication recommendation | 2026 | Expert Systems with Applications | https://doi.org/10.1016/j.eswa.2026.131330 | pure method | 5 | 5 | 5 | high | Closest MedRec noise paper. It uses co-denoising/label refinement and evaluates simulated random replacement/addition noise; this raises the baseline bar but does not directly model structurally one-sided unprescribed labels. |
| 2 | Debiased medication recommendation through fusing frequent pattern and temporal medical records | 2026 | Neural Networks | https://doi.org/10.1016/j.neunet.2026.109168 | pure method | 4 | 5 | 5 | high | Directly addresses medication-frequency imbalance and uses historical medication recurrence. Any supervision route must separate itself from long-tail/popularity correction and simple history-based recalibration. |
| 3 | FineMed: Medication mapping and diagnosis enhancement for fine-grained medication recommendation | 2026 | Information Sciences | https://doi.org/10.1016/j.ins.2026.123930 | pure method | 5 | 5 | 5 | high | Introduces diagnosis-level medication supervision and reformulates visit-level prediction. Generic diagnosis-aware supervision is therefore crowded. |
| 4 | Real-world evaluation of medication recommendation workflows: Retrieval augmentation, physician-RAG collaborative workflow, and prescribing quality | 2026 | International Journal of Medical Informatics | https://doi.org/10.1016/j.ijmedinf.2026.106598 | other / evaluation | 5 | 5 | 5 | high | Expert references separate CORE, ALT, and AVOID drugs, supporting the premise that prescribing quality is not exhausted by exact historical-set matching. It is evidence for the problem boundary, not a method template. |
| 5 | SafeRx-Agent: A Knowledge-Grounded Multi-Agent Framework for Safe and Explainable Medication Recommendation | 2026 | arXiv 2605.29146 | https://arxiv.org/abs/2605.29146 | system/tool | 4 | 4 | 4 | medium-high | Case analysis explicitly notes a clinically reasonable continuation outside the current visit ground-truth set. This is supporting evidence that some benchmark false positives need not be clinical errors, not proof that arbitrary unprescribed drugs are positives. |
| 6 | CEHMR: Curriculum learning enhanced hierarchical multi-label classification for medication recommendation | 2023 | Artificial Intelligence in Medicine | https://doi.org/10.1016/j.artmed.2023.102613 | pure method | 4 | 5 | 5 | medium-high | Treats MedRec as hierarchical multi-label classification and changes training difficulty/order, providing a strong non-PU objective control and prior on label-structure learning. |
| 7 | Unbiased Recommender Learning from Missing-Not-At-Random Implicit Feedback | 2020 | WSDM | https://doi.org/10.1145/3336191.3371783 | pure method | 5 | 5 | 5 | high | Canonical warning that unobserved interactions are not reliable negatives and that PU alone is insufficient under MNAR exposure. A MedRec paper cannot claim novelty for this generic principle. |
| 8 | Counterfactual Implicit Feedback Modeling | 2025 | NeurIPS | https://proceedings.neurips.cc/paper_files/paper/2025/hash/1436e87a58b3e6ac177450bd10721726-Abstract-Conference.html | pure method | 5 | 5 | 5 | high | Recent CCF-A-level implicit-feedback work jointly treats PU and MNAR through counterfactual modeling. It is the strongest generic recommender collision for any prescribing-policy/observation-process formulation. |
| 9 | Correct and Weight: A Simple Yet Effective Loss for Implicit Feedback Recommendation | 2026 | arXiv 2601.04291 | https://arxiv.org/abs/2601.04291 | pure method / preprint | 4 | 4 | 4 | medium-high | Explicitly down-weights uncertain false negatives with PU-style correction. It is a killer simple baseline for any proposed uncertain-negative MedRec loss. |

## Clusters

### Cluster 1: MedRec label noise and supervision robustness

- **Representative papers**: KRAM, CEHMR.
- **Already solved**: robust training under noisy labels, collaborative denoising, hierarchical label structure, curriculum over example difficulty.
- **Remaining gap**: these works do not establish that the zeros in a retrospective prescription vector are trustworthy clinical negatives, nor do they directly model physician choice as a selective observation process over multiple acceptable therapies.
- **Differentiation requirement**: a new route must formalize a structurally asymmetric observation mechanism rather than inject synthetic noise and then denoise it.

### Cluster 2: Frequency bias and longitudinal medication reuse

- **Representative papers**: DMRNet; related history-aware families already recorded in the project prior.
- **Already solved**: long-tail/popularity correction, frequent-pattern signals, and historical medication recalibration.
- **Remaining gap**: label absence versus negative treatment relevance is not the same problem as medication rarity or recurrence.
- **Differentiation requirement**: the proposed mechanism cannot reduce to prevalence weighting, class balancing, or copying/recalibrating prior medications.

### Cluster 3: Finer supervision and clinically acceptable alternatives

- **Representative papers**: FineMed, Physician-RAG, SafeRx-Agent.
- **Already solved**: diagnosis-aware subrecommendation is a current method direction; expert evaluation can represent essential, acceptable-alternative, and avoid sets; case analysis shows that exact visit labels can under-specify clinically reasonable continuations.
- **Remaining gap**: the current MIMIC-style training target still supplies only the observed prescription, not a complete acceptable-treatment set.
- **Differentiation requirement**: do not manufacture alternative-treatment labels from ATC taxonomy or weak mappings. Idea 005 already closed that semantic shortcut.

### Cluster 4: Generic PU/MNAR implicit recommendation

- **Representative papers**: WSDM 2020 unbiased MNAR learning, NeurIPS 2025 Counterfactual Implicit Feedback Modeling, Correct-and-Weight 2026.
- **Already solved**: generic recommender theory that unobserved items can be false negatives, propensity/MNAR correction, and uncertainty-aware negative weighting.
- **Remaining gap**: whether the clinical prescribing process induces a MedRec-specific observation structure that requires a different objective or identifiability assumption.
- **Differentiation requirement**: generic PU loss transfer is not enough for a CCF-A MedRec method paper.

## Opportunity Map

| Cluster | Status | Open gap | Possible direction | Evidence needed | Risk |
| --- | --- | --- | --- | --- | --- |
| Label-noise robustness | crowded but open | Real prescription missingness is not synthetic symmetric corruption | Prescribing-observation-aware supervision | Formal observation model and strong KRAM/noise-loss controls | Medium-high |
| Long-tail/debiasing | crowded | Popularity is distinct from uncertain negative semantics | Use prevalence only as control, not contribution | Show gain persists after DMRNet/class-balancing controls | High collision |
| Fine-grained supervision | crowded | Exact prescription is narrower than acceptable therapy set | Partial positive supervision at existing action resolution | Must avoid external annotation/KG build unless necessary | Medium-high |
| Generic PU/MNAR | central generic claim covered | Clinical choice process may differ from click exposure | Domain-specific selective-label mechanism | Show why user-item exposure estimators are scientifically mismatched or incomplete | High novelty risk |

## Benchmark And Dataset Candidates

The current frozen MIMIC pipeline remains the preferred development setting because the candidate direction changes training supervision rather than requiring labs, notes, or a new ontology. A future method should first extend across existing comparison-ready backbones rather than introduce a new data pipeline.

Expert-labeled resources such as Physician-RAG can support problem motivation and external semantics but are not currently part of the executable pipeline and should not become a required annotation dependency without a separate admission decision.

## Citation And Positioning Cautions

- Do not state that every unprescribed medication is a hidden positive. The defensible claim is that `unprescribed` is a heterogeneous observation whose clinical-negative status is not guaranteed.
- Do not use SafeRx-Agent's single case as prevalence evidence; it is a concrete existence example only.
- Do not call historical prescriptions 'implicit feedback' without explaining the clinical differences from click/exposure systems.
- KRAM is a direct reviewer collision for label noise; DMRNet is a direct collision for frequency/history debiasing; FineMed is a direct collision for finer supervision.
- WSDM 2020 and NeurIPS 2025 make generic PU/MNAR correction prior art. The idea must earn novelty through the prescribing observation mechanism, objective, or identifiability structure.
