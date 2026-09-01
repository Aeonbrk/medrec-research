<!-- markdownlint-disable MD013 -->

# Literature Memory

This is the curated literature input carried from `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. It inventories all 21 canonical paper cards.

## Interpretation Layers & Use Boundary

When reading the entries below, distinguish three conceptual layers:

1. **Source-Supported Fact**: The verifiable content of the external publication (authors, venue, proposed method, documented empirical claims).
2. **Research Interpretation**: The internal conceptual framing and modeling assigned to the paper during the archive's research cycle.
3. **Current Novelty Implication**: The team's provisional judgment regarding how the paper constrains or threatens the novelty of specific internal routes.

> [!IMPORTANT]
> **Novelty Implications are Hypothesis-Dependent**:
> A note that a paper "threatens generic safe-MedRec novelty" represents an internal research judgment at the archive cutoff, **not** an immutable scientific fact about the paper itself. Novelty implications shift as new literature is published and as active research questions are reformulated in `research/ideas/`. All new work requires prospective, up-to-date literature review.

## Conformal, Calibration, and Recommendation Reliability

At New-Search commit `9971464253c556345262b22ed6d44b2cc14c9da8`, each `paper:<slug>` node maps to `research-wiki/papers/<slug>.md`.

| Node | Paper | Year / identifier | Archived relevance |
| --- | --- | ---: | --- |
| `paper:angelopoulos2022_conformal_risk_control` | Conformal Risk Control | 2022; arXiv `2208.02814` | Card relevance is `TODO`; the graph identifies CRC as CRC-PS calibration machinery for bounded monotone risk control. |
| `paper:angelopoulos2023_recommendation_systems_distributionfree` | Recommendation Systems with Distribution-Free Reliability Guarantees | 2023 | Card relevance is `TODO`; the graph identifies recommender-side FDR control as a precursor to calibrated set selection. |
| `paper:chen2025_advancing_confidence_calibration` | Advancing Confidence Calibration and Quantification in Medication Recommendation | 2025 | Card relevance is `TODO`; the graph records it as the closest direct MedRec confidence and set-calibration threat, extending CRC-style ideas. |
| `paper:shen2025_safer_calibrated_riskaware` | SAFER: A Calibrated Risk-Aware Multimodal Recommendation Model for Dynamic Treatment Regimes | 2025 | Card relevance is `TODO`; the graph records it as a nearby conformal, risk-aware clinical treatment-recommendation baseline. |
| `paper:toni2025_you_dont_bring` | You Don't Bring Me Flowers: Mitigating Unwanted Recommendations Through Conformal Risk Control | 2025 | Card relevance is `TODO`; the graph records CRC-based filtering and replacement as an existing decision-time recommender safety layer. |
| `paper:xu2025_selective_conformal_risk` | Selective Conformal Risk Control | 2025 | Card relevance is `TODO`; the graph records accepted-risk and coverage control as a threat to a selective-deployment claim. |

## Boundary Evidence, Constraints, and Evaluation

| Node | Paper | Year / identifier | Archived relevance |
| --- | --- | ---: | --- |
| `paper:lv2026_awaken_giant_activating` | Awaken the Giant: Activating LLMs via Deep Model Guidance for Boundary-aware Medication Recommendation | 2026; DOI `10.1145/3770854.3780297` | Card relevance is `TODO`; the graph identifies GiantMed as the closest boundary-medication refinement prior and overlap threat. |
| `paper:wang2026_saferxagent_knowledgegrounded_multiagent` | SafeRx-Agent: A Knowledge-Grounded Multi-Agent Framework for Safe and Explainable Medication Recommendation | 2026; arXiv `2605.29146` | Card relevance is `TODO`; multi-agent, knowledge-grounded safety verification weakens generic certificate-route novelty. |
| `paper:huh2026_pacerag_patientaware_contextual` | PACE-RAG: Patient-Aware Contextual and Evidence-Constrained RAG for Clinical Drug Recommendation | 2026; arXiv `2603.17356` | Card relevance is `TODO`; the graph identifies it as the closest patient-aware evidence-retrieval and policy-verification prior. |
| `paper:chen2026_rxeval_prescriptionlevel_benchmark` | RxEval: A Prescription-Level Benchmark for Evaluating LLM Medication Recommendation | 2026; arXiv `2605.14543` | Card relevance is `TODO`; the graph identifies its prescription-level evaluation surface as aligned with the certificate route. |
| `paper:ashhad2025_sidekick_semantically_integrated` | SIDEKICK: A Semantically Integrated Resource for Drug Effects, Indications, and Contraindications | 2025; arXiv `2602.19183` | Card relevance is `TODO`; provenance-rich contraindication knowledge narrows the novelty of an evidence-eligibility knowledge resource. |
| `paper:a2026_medicare_medical_collaborative` | MediCARE: Medical Collaborative Agents REasoning over Interpretable Heterogeneous Graphs | 2026; DOI `10.1016/j.artmed.2026.103444` | Card relevance is `TODO`; collaborative-agent explanation already exists, so generic agent novelty is weak. |
| `paper:yang2026_knowledgedriven_neurosymbolic_reasoning` | Knowledge-Driven Neuro-Symbolic Reasoning for Personalized Oncology Treatment Recommendation Based on Multi-Modal Medical Knowledge Graph | 2026; DOI `10.64898/2026.06.01.26354443` | Card relevance is `TODO`; nearby neuro-symbolic safety constraints compress state-conditioned safety-graph novelty. |
| `paper:z2026_katmed_knowledgeaugmented_transformer` | KATMed: A Knowledge-Augmented Transformer for Contraindication-Aware Medication Recommendation in Comorbidities | 2026; DOI `10.1016/j.jbi.2026.104991` | Card relevance is `TODO`; contraindication-aware transformer work occupies part of the safety-constraint space. |
| `paper:saxena2026_graphdiffmed_knowledgeconstrained_differential` | GraphDiffMed: Knowledge-Constrained Differential Attention with Pharmacological Graph Priors for Medication Recommendation | 2026; arXiv `2605.20188` | Card relevance is `TODO`; the graph identifies it as a pharmacological-constraint MedRec prior that threatens DDI-only safety narratives. |

## Action-Level, Adaptation, and Safe-MedRec Alternatives

| Node | Paper | Year / identifier | Archived relevance |
| --- | --- | ---: | --- |
| `paper:x2026_heteromed_heterogeneous_graph` | HeteroMed: A Heterogeneous Graph Knowledge-Enhanced Model for Medication Recommendation | 2026; DOI `10.1007/s13755-026-00430-5` | Direct novelty threat: generic add, continue, and drop modeling is occupied; the archive retains unsafe-omission and continuation auditing under hard controls as distinct remaining concerns. |
| `paper:fan2025_finegrained_listwise_alignment` | Fine-grained List-wise Alignment for Generative Medication Recommendation | 2025; arXiv `2505.20218` | Card relevance is `TODO`; the graph identifies FLAME as a close list-wise LLM prior for drug-by-drug add and remove actions. |
| `paper:han2026_testtime_recommendation_safe` | Test-Time Recommendation for Safe Medication Combination | 2026; DOI `10.1007/978-981-95-7072-0_33` | Direct threat to generic safe-MedRec-under-shift and test-time-adaptation novelty; the archive does not treat it as resolving unsafe omission or continuation auditing. |
| `paper:zhang2026_enhanced_drug_recommendation` | Enhanced Drug Recommendation Based on Dynamic Clinical Trajectory Aggregation and Geometry-Enhanced Molecular Representation | 2026; DOI `10.1016/j.eswa.2026.132225` | Card relevance is `TODO`; the graph treats it as a nearby dynamic-trajectory and drug-representation baseline. |
| `paper:moghaddam2026_useradaptive_metalearning_coldstart` | User-Adaptive Meta-Learning for Cold-Start Medication Recommendation with Uncertainty Filtering | 2026; arXiv `2601.22820` | Card relevance is `TODO`; adjacent adaptation and uncertainty-filtering work informed action-route ranking for sparse patient history. |
| `paper:zhao2025_finegrained_alignment_large` | Fine-grained Alignment of Large Language Models for General Medication Recommendation without Overprescription | 2025; arXiv `2503.03687` | Card relevance is `TODO`; LAMO crowds generic LLM medication-alignment and overprescription-control narratives. |

## Use Boundary

These cards are literature context, not evidence that any archived route is
novel, clinically safe, comparison-ready, or active. New-route work needs its
own current literature review and novelty check. Canonical gap definitions live
in `research-wiki/gap_map.md`; canonical research relationships live in
`research-wiki/graph/edges.jsonl` at the pinned archive commit.
