# MSED Closest-Work Boundary Audit

Status: **PRE-SCREEN CLAIM BOUNDARY — NOT A FINAL NOVELTY VERDICT**

This file records occupied conceptual territory so the screen does not confuse a known primitive with a contribution. Final novelty/closest-work claims require a post-survival primary-source audit.

## Generic set and MIL aggregation is occupied

**Deep Sets** — Zaheer et al., NeurIPS 2017.  
Primary source: https://papers.nips.cc/paper/6931-deep-sets  
It establishes generic permutation-invariant learning over sets. MSED therefore cannot claim novelty from treating evidence as a set/bag or from using a permutation-invariant aggregator.

**Attention-based Deep Multiple Instance Learning** — Ilse, Tomczak, Welling, ICML 2018.  
Primary source: https://proceedings.mlr.press/v80/ilse18a.html  
Attention MIL learns bag representations from weighted instance aggregation. MSED cannot claim label-aware/attention-style MIL pooling itself as new.

## Distribution pooling is occupied

**Distribution based MIL pooling filters: Experiments on a lymph node metastases dataset** — Oner et al., Medical Image Analysis 2023.  
DOI: `10.1016/j.media.2023.102813`  
The method explicitly estimates marginal distributions of instance features to retain distribution information lost by point estimates such as mean/max pooling. MSED cannot claim that representing an MIL bag by a distribution rather than a point statistic is new.

**Kernel Mean Embedding of Instance-wise Predictions in Multiple Instance Regression** — Uriot, 2019.  
arXiv: `1904.10583`  
This work first obtains instance-wise predictions and then embeds the distribution of those predictions with a kernel mean embedding before bag-level regression. This is a particularly close conceptual boundary: MSED cannot claim novelty from "instance predictions -> distribution embedding -> bag prediction" by itself.

The empirical characteristic spectrum used in the screen is therefore treated as a reusable distribution-embedding primitive, not a contribution.

## Medication-specific label-instance modeling is occupied

**LEAP: Learning to Prescribe Effective and Safe Treatment Combinations for Multimorbidity** — Zhang et al., KDD 2017.  
DOI: `10.1145/3097983.3098109`  
LEAP uses content-based attention for label-instance mapping and sequential medication decoding. Medication labels attending to disease/clinical instances is therefore established territory. MSED cannot claim the first medication-specific evidence selection or the first MIML-style treatment recommender.

## Fine-grained medication subdecisions are occupied

**Medication mapping and diagnosis enhancement for fine-grained medication recommendation (FineMed)** — Li et al., Information Sciences 2026.  
DOI: `10.1016/j.ins.2026.123930`  
FineMed decomposes visit-level recommendation into diagnosis-level sub-recommendations and explicitly models drug-disease correspondences. MSED cannot claim the first fine-grained medication recommendation, first clinical sub-recommendation, or first explicit medication-diagnosis correspondence.

## Current permissible scientific object

The screen tests a narrower computation graph:

> For every candidate medication, first produce scalar support potentials over the complete legal longitudinal FineCode evidence; treat those medication-specific support values as an empirical distribution; encode distribution shape while preserving the already-validated global FineCode context; and predict the medication from both views.

The decisive experiment does not compare distribution modeling against a weak mean baseline. It compares against an identical-capacity control that already receives the exact strong `logmeanexp` statistic and the same nonlinear feature dimension. The only difference is `E[phi(r)]` versus `phi(LME(r))`.

If that comparison fails, the project should not attempt to rescue the family by changing kernels, frequency counts, temperatures, pooling grids, or decoder widths.

If it survives strongly, the next literature audit must specifically search for:

- label-conditioned distribution regression / distribution pooling in MIML;
- class-specific kernel/distribution embeddings of instance responses;
- medication-specific evidence-response distributions in EHR recommendation;
- characteristic-function or random-Fourier set representations used per output label;
- 2024--2026 MIL/distribution-learning work that may subsume the complete graph.
