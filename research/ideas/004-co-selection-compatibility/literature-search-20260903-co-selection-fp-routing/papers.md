<!-- markdownlint-disable MD013 -->

# Closest-Work Papers — Post-Idea-003 Residual FP Routing

Search date: `2026-09-03`.

The table retains primary or high-confidence sources that materially change candidate novelty, mechanism, control, or feasibility judgments. Literature memory from the project X-Ray summary was used as a recall aid, not as novelty proof.

| Work | Venue / year | Stable identifier | Information family | What it already covers | Consequence for Idea 004 selection |
| --- | --- | --- | --- | --- | --- |
| Yang et al., *MoleRec: Combinatorial Drug Recommendation with Substructure-Aware Molecular Representation Learning* | WWW 2023 | DOI `10.1145/3543507.3583872` | frozen upstream backbone | molecular substructure-aware medication recommendation over longitudinal EHR | a successor selector must add held-out information beyond the frozen medication score; it cannot claim a new recommendation backbone |
| Chen et al., *Advancing Confidence Calibration and Quantification in Medication Recommendation* | KDD 2025 | DOI `10.1145/3690624.3709232` | confidence | medication-level confidence calibration and combination confidence quantification | score/confidence-only novelty remains crowded; supports retaining confidence as a mandatory control |
| Wu et al., *Conditional Generation Net for Medication Recommendation* (COGNet) | WWW 2022 | DOI `10.1145/3485447.3511936`, arXiv `2202.06588` | longitudinal transition | explicit copy-or-predict from historical prescriptions versus new medications | previous-prescription membership is not a novel action semantic by itself |
| Kim et al., *HI-DR: Exploiting Health Status-Aware Attention and an EHR Graph+ for Effective Medication Recommendation* | AAAI 2025 | DOI `10.1609/aaai.v39i11.33301` | co-prescription relation / patient-conditioned evidence | health-status-aware medication evidence plus an EHR Graph+ that distinguishes the strength/degree of co-prescribing one medication with another | strongest direct novelty threat to a transparent co-selection statistic; forces novelty onto conditional FP routing beyond a frozen score and marginal controls |
| Li et al., *Knowledge enhanced representation learning network for drug recommendation* (KERL) | Information Processing & Management 2025 | DOI `10.1016/j.ipm.2025.104164` | longitudinal history | dual-path historical medication modeling and selection of reusable past drugs | materially weakens longitudinal recurrence novelty |
| Yin et al., *HeteroMed: a heterogeneous graph knowledge-enhanced model for medication recommendation* | Health Information Science and Systems 2026 | DOI `10.1007/s13755-026-00430-5`, PMID `41567975` | longitudinal transition / heterogeneous relations | collaborative drug expansion and inheritance with temporal factors and heterogeneous graph knowledge | continuation/new semantics and rich relation modeling are established prior art |
| Li et al., *Debiased medication recommendation through fusing frequent pattern and temporal medical records* (DMRNet) | Neural Networks 2026 | DOI `10.1016/j.neunet.2026.109168`, PMID `42214931` | co-selection + longitudinal history | frequent medication pattern mining plus historical-medication recalibration | crowds both generic co-selection and generic history hypotheses; a successor must ask a narrower conditional error question |
| Wang et al., *Learning Collective Medication Effects via Multi-level Abstraction for Medication Recommendation* (MSAM) | arXiv 2026 | arXiv `2601.19259` | medication-set relation | collective medication effects and multi-level abstractions over selected candidates and historical prescriptions | generic “model medication combinations/relations” is not novel; relation architecture is premature before a scalar gate |
| Zhang et al., *HypeMed: Enhancing Medication Recommendations with Hypergraph-Based Patient Relationships* | ACM TOIS 2026 | DOI `10.1145/3803851` | patient-conditioned / relational / history | visit-level hyperedge semantics plus visit-conditioned historical/similar-patient retrieval | broad “use patient context/history/relations” hypotheses are too vague; one observable is required |
| Kang et al., *Improving Rare Medication Recommendation with Counterfactual Data Augmentation and Large Language Models* (GenRxR) | RecSys 2026 | DOI `10.1145/3773078.3831753`, arXiv `2607.24829` | co-recommended medication relation | models relationships among co-recommended medications while addressing rare-med data scarcity | further narrows any relation novelty claim to conditional FP routing rather than recommendation gain |
| Li et al., *Collaborative Relation Augmentation With Hierarchical Prescription Inference for Medication Recommendation* (CRHP) | IEEE JBHI 2025/2026 volume | DOI `10.1109/JBHI.2025.3582393`, PMID `40549530` | disease-drug / collaborative relation | covariance knowledge graphs, high-order relation augmentation, current and historical prescription inference | current-code association and generic relation graphs are crowded |
| Fan et al., *GRAIN: Molecules Are Not the Right Granularity -- Active-Ingredient Modeling for Safe Medication Recommendation* | arXiv 2026 | arXiv `2608.00098` | co-prescription + DDI | drug-level DDI, ingredient-level DDI, and EHR-derived co-prescription graph | co-prescription is an established modeling source; frequency-corrected scalar must be framed as a diagnostic rather than a new relation source |
| Saxena and Shibata, *GraphDiffMed: Knowledge-Constrained Differential Attention with Pharmacological Graph Priors for Medication Recommendation* | arXiv 2026 | arXiv `2605.20188` | DDI structure / longitudinal history | DDI graph priors plus intra/inter-visit differential attention | rich DDI/history architecture is established; a local-topology candidate needs a much sharper mechanism and degree control |
| Sanchez et al., *Multi-LLM Collaboration for Medication Recommendation* | arXiv 2025 | arXiv `2512.05066` | model collaboration / ensemble | interaction-aware multi-LLM collaboration for stability and calibration | cross-model candidate must distinguish disagreement-specific information from ordinary ensemble improvement |

## Closest-work adjudication by candidate family

### Longitudinal transition

COGNet directly formalizes copy-versus-new medication generation. KERL explicitly selects reusable historical medications. HeteroMed models expansion/inheritance, and DMRNet recalibrates recommendations from temporal prescription records. These works support the plausibility that history matters for recommendation, but they also make “history matters” or “continuation is useful” non-novel.

Within the retained search, none directly tests a frozen-backbone medication-level false-positive routing question with `previous-prescription membership` as one added target-free bit after a strongest simple confidence/chronicity control. That narrow diagnostic remains testable, but its prior-art risk is materially higher than the selected co-selection route.

### Medication-set relational / co-selection

HI-DR is the most important prior-art subtraction because it explicitly strengthens medication co-prescription edges rather than treating the EHR medication graph as binary. DMRNet mines frequent drug combinations; MSAM models collective effects; GenRxR models co-recommended medication relationships; GRAIN includes an EHR co-prescription graph.

Therefore the selected route does **not** claim a new co-prescription statistic or a new way to improve medication recommendation. Its search-scoped delta is the held-out conditional question: whether one frozen frequency-corrected relation scalar explains candidate FP risk beyond frozen score, set size, candidate prevalence, and peer-set popularity.

### Patient-conditioned current evidence

CRHP, HI-DR, HypeMed, and DrugDoctor-family work make current clinical evidence and disease-medication relations standard inputs/mechanisms. A transparent current-code association diagnostic remains feasible, but it is at substantial risk of being a handcrafted re-expression of information the backbone already uses.

### DDI topology

DDI graph encoding is mature prior art. Idea 001 only tested active degree, so local topology is not logically exhausted, but the closest-work search does not provide a sharp reason why local DDI clustering should predict **false-positive status** rather than merely safety/conflict structure. This lowers mechanistic priority despite cheap feasibility.

### Cross-model corroboration

The retained medication-specific work concerns collaboration/ensembling rather than a strict disagreement-after-best-ensemble test. The scientific distinction is valid in principle, but the current project does not expose an authoritative public record of already-frozen, visit-aligned validation outputs for multiple qualified backbones. The cheap-gate prerequisite is therefore not established.

## Search-scoped novelty conclusion

No retained work directly matches all of the following elements simultaneously:

1. frozen MoleRec medication-level candidates;
2. false-positive routing under the fixed DDI-active singleton-deletion formalization;
3. frozen confidence plus set-size and marginal-popularity controls;
4. one train-only frequency-corrected co-selection scalar added as the only scientific feature;
5. patient-disjoint Dev/Audit fitting and held-out incremental review yield.

This is a bounded closest-work conclusion, not proof that no such paper exists.
