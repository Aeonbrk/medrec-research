<!-- markdownlint-disable MD013 -->

# Papers — Medication-Transition Practice Shift Reset

Search date: 2026-09-08.

Mode: `ccf-literature-searcher / exploratory`, bounded post-Idea-006 reset.

Scope: general medication recommendation under temporal or institutional deployment shift. The search explicitly excludes rescue variants of Idea 006's exposure-safety objective.

## Retained closest work

### 1. HypeMed: Enhancing Medication Recommendations with Hypergraph-Based Patient Relationships

- Year / venue: 2026, ACM TOIS.
- DOI: `10.1145/3803851`.
- Type: pure method.
- Evidence retained: experiments on MIMIC-III, MIMIC-IV, and eICU; eICU is described as a multi-center dataset used to assess generalizability under cross-institutional settings.
- Important detail: the processed eICU task differs substantially from MIMIC: 46 medication codes, no procedure codes, and no DDI graph; reported results are dataset-specific benchmark results.
- Collision: multi-dataset and cross-institution language are already current prior art.
- Remaining delta: the accessible experimental description does not establish source-trained zero-/low-shot adaptation to a future institution or period as the central learning problem.
- Source: https://doi.org/10.1145/3803851

### 2. KATMed: A Knowledge-Augmented Transformer Model for Contraindication-Aware Medication Recommendation in Comorbidities

- Year / venue: 2026, Journal of Biomedical Informatics.
- DOI: `10.1016/j.jbi.2026.104991`.
- Type: pure method.
- Evidence retained: MIMIC-III/MIMIC-IV evaluation with partial external validation on multi-center eICU; authors explicitly note remaining differences in practice patterns, case mix, and coding conventions across hospitals/systems.
- Collision: external validation is not novel by itself.
- Remaining delta: KATMed's mechanism is contraindication-aware knowledge augmentation, not adaptation to prescribing-practice shift.
- Source: https://doi.org/10.1016/j.jbi.2026.104991

### 3. Mixture of Experts Based Medication Recommendation for Multimorbidity (Rx-Expert)

- Year / venue: 2026, Expert Systems with Applications.
- Type: pure method.
- Evidence retained: reports experiments on MIMIC-III, MIMIC-IV, and eICU.
- Collision: another current multi-dataset generalization claim.
- Remaining delta: the method contribution is expert decomposition / molecular fusion, not source-to-target deployment adaptation.
- Source: https://www.sciencedirect.com/science/article/pii/S0957417426022839

### 4. Natural Language-Assisted Multi-modal Medication Recommendation (NLA-MMR)

- Year / venue: 2024, CIKM.
- DOI: `10.1145/3627673.3679529`.
- Type: pure method.
- Evidence retained: multimodal alignment evaluated on three public medication-recommendation datasets.
- Collision: broad multi-dataset evaluation is already standard enough that it cannot be the contribution.
- Remaining delta: no deployment-shift adaptation objective is central to NLA-MMR.
- Source: https://doi.org/10.1145/3627673.3679529

### 5. Developing and Validating a Machine Learning Pharmaceutical Therapy Recommender for US Hospital In-Patients with Schizophrenia Spectrum Disorders

- Year / venue: 2025, BMC Psychiatry.
- DOI: `10.1186/s12888-025-07657-8`.
- Type: narrow clinical recommendation / validation study.
- Evidence retained: true internal, geographic external, and temporal validation are reported. MAP@3 is 0.4901 on MIMIC-IV internal validation, 0.4323 on MIMIC-NW external validation, and 0.3586 on MIMIC-III temporal validation.
- Collision: temporal/external degradation of a medication recommender is not a new phenomenon.
- Remaining delta: the task is narrow antipsychotic therapy and the work is not a general medication-recommendation adaptation method.
- Source: https://doi.org/10.1186/s12888-025-07657-8

### 6. Debiased Medication Recommendation through Fusing Frequent Pattern and Temporal Medical Records (DMRNet)

- Year / venue: 2026, Neural Networks.
- DOI: `10.1016/j.neunet.2026.109168`.
- Type: pure method.
- Evidence retained: explicitly targets skewed medication-frequency / long-tail bias and uses frequent patterns plus historical-drug recalibration.
- Collision: a temporal-shift paper cannot mistake medication marginal-frequency drift or long-tail effects for a new deployment mechanism.
- Role in future gate: motivates a strong simple medication-prior control before any adaptation story.
- Source: https://doi.org/10.1016/j.neunet.2026.109168

### 7. Predicting Inpatient Medication Orders From Electronic Health Record Data

- Year / venue: 2020, Clinical Pharmacology & Therapeutics.
- DOI: `10.1002/cpt.1826`.
- Type: method / prediction task.
- Evidence retained: medication prediction at provider-order time using only previously available EHR information, over a large medication vocabulary.
- Collision: order-time prediction and causal pre-order masking remain prior art.
- Remaining delta: not a temporal deployment-adaptation method.
- Source: https://doi.org/10.1002/cpt.1826

### 8. MIMIC-IV, a Freely Accessible Electronic Health Record Dataset

- Year / venue: 2023, Scientific Data.
- DOI: `10.1038/s41597-022-01899-x`.
- Type: data resource.
- Evidence retained: `anchor_year_group` was added specifically to permit analyses incorporating changes in medical practice over time. MIMIC-IV exposes approximate real-care periods while preserving de-identification.
- Resource relevance: provides a low-infrastructure temporal environment variable for a bounded premise test.
- Source: https://doi.org/10.1038/s41597-022-01899-x

### 9. Patient-Level and Temporal Data Leakage Can Inflate Performance in Medication Recommendation Models

- Year / venue: 2026, Journal of Biomedical Informatics.
- DOI: `10.1016/j.jbi.2026.105016`.
- Type: critical appraisal.
- Evidence retained: explicitly raises patient-level and temporal leakage as a medication-recommendation validity problem.
- Design consequence: any practice-shift gate must be patient-disjoint and chronologically frozen; random split evidence is not sufficient.
- Source: https://doi.org/10.1016/j.jbi.2026.105016

## Search-scoped synthesis

The retained literature supports four conclusions:

1. Multi-dataset evaluation across MIMIC/eICU is already common and cannot be claimed as novelty.
2. Real temporal/external degradation has been observed in a narrow medication recommender, so the phenomenon itself is not novel.
3. Current general MedRec methods found in this search do not make source-to-future-period adaptation to prescribing-practice shift their central method problem.
4. Medication-frequency imbalance is already a known confound; a future shift claim must first survive a simple recent-prior / logit-bias adjustment.

Search-scoped opportunity:

> **General medication recommendation under forward prescribing-practice shift, where the scientific question is whether conditional medication-order behavior changes beyond what can be explained by marginal medication-frequency drift.**

This is not yet Idea 007. A project-local premise gate is required before method optimization.
