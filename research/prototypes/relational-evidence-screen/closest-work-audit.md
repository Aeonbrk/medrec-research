
# Closest-work boundary — medication-conditioned relational evidence

Status: PRE-SCREEN PRIMARY-SOURCE BOUNDARY AUDIT

## CSRec — JMIR Medical Informatics 2025

Hypertension Medication Recommendation via Synergistic and Selective Modeling of Heterogeneous Medical Entities: Development and Evaluation Study of a New Model  
DOI: 10.2196/74170

CSRec constructs heterogeneous and homogeneous graphs over medical entities, uses graph attention to learn interentity synergies, and then applies temporal selection to obtain comprehensive patient representations used for medication recommendation.

Boundary: heterogeneous medical-entity synergy and graph-based diagnosis/procedure/medication interaction are occupied. The proposed candidate differs only if cross-type relations are formed after candidate-medication-specific fine-code selection and remain tied to the candidate decision instead of first forming a shared patient representation.

## DMGExNet — Engineering Reports 2026

DMGExNet: A Dual-Stream Transformer-Guided Multi-Graph Collaborative Explainable Network for Medication Recommendation  
DOI: 10.1002/eng2.70899

DMGExNet uses diagnosis/procedure dual streams and bidirectional cross-attention, then concatenates the interacted streams into a patient health-status representation before medication prediction.

Boundary: diagnosis-procedure cross-attention is occupied. The candidate asks whether relation formation should instead be medication-conditioned before the medication-level decision.

## Carmen — AAAI 2023

Context-Aware Safe Medication Recommendations with Molecular Graph and DDI Graph Embedding  
DOI: 10.1609/aaai.v37i6.25861

Carmen derives medication context from medication-diagnosis, medication-procedure and medication-medication co-occurrence, combines patient context, and injects context into molecular graph learning.

Boundary: medication-specific context and medication-clinical association are occupied. The proposed mechanism differs only if the patient-specific current evidence relation is constructed conditionally for each candidate medication rather than derived from population-level medication context or a shared patient representation.

## Current boundary verdict

~~~text
heterogeneous interaction novelty:        NO
diagnosis-procedure interaction novelty:  NO
medication-specific context novelty:      NO
fine-code access novelty:                 NO
candidate-conditioned relation object:    PLAUSIBLE
whole-model novelty:                      PLAUSIBLE / unverified
~~~

A positive screen establishes only that multiplicative candidate-conditioned clinical conjunction adds predictive signal over a matched additive control. It does not establish final novelty or superiority.
