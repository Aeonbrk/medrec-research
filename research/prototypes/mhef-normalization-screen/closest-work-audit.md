# Closest-work boundary — MHEF normalization-domain screen

Status: **PRE-SCREEN PRIMARY-SOURCE CLAIM BOUNDARY**

This file constrains claims before execution. It does not establish final novelty.

## Adjacent label-specific evidence selection

### CAML — NAACL 2018

**Explainable Prediction of Medical Codes from Clinical Text**  
DOI: `10.18653/v1/N18-1100`

CAML uses a separate attention distribution to select relevant clinical-text evidence for each predicted ICD code.

Boundary:

- per-label / label-specific attention is occupied;
- a different evidence representation per output label is occupied.

MHEF cannot claim novelty from medication-specific attention alone.

### Query2Label — multi-label classification

**Query2Label: A Simple Transformer Way to Multi-Label Classification**  
arXiv: `2107.10834`

Query2Label uses label embeddings as Transformer-decoder queries to extract label-specific features before binary classification.

Boundary:

- label embeddings as queries are occupied;
- query-conditioned feature pooling is occupied.

The relevant MHEF distinction, if it survives, must be the heterogeneous clinical normalization boundary in the complete EHR-to-medication computation graph.

## Medication-recommendation work

### DMRNet — Neural Networks 2026

**Debiased Medication Recommendation through Fusing Frequent Pattern and Temporal Medical Records**  
ScienceDirect PII: `S0893608026006295`

DMRNet combines temporal prescription information with a cross-view drug-prediction mechanism. The public implementation contains separate diagnosis-side and procedure-side medication-score paths before final score fusion.

Boundary:

- multi-view drug prediction is occupied;
- diagnosis/procedure-specific prediction streams are occupied;
- combining temporal and token-level views is occupied.

MHEF therefore must not claim `first multi-view medication recommendation` or `first diagnosis/procedure-specific drug prediction`.

### DMGExNet — Engineering Reports 2026

**DMGExNet: A Dual-Stream Transformer-Guided Multi-Graph Collaborative Explainable Network for Medication Recommendation**  
DOI: `10.1002/eng2.70899`

DMGExNet processes diagnosis and procedure streams in parallel, applies bidirectional cross-attention, and concatenates the interacted streams into a comprehensive patient representation before medication recommendation.

Boundary:

- preserving diagnosis/procedure streams is occupied;
- diagnosis-procedure cross-attention is occupied;
- heterogeneous clinical-view modeling is occupied.

The current MHEF object is narrower: candidate-medication-specific fine-code scores are shared, but softmax normalization is factorized by heterogeneous clinical evidence type and those candidate-specific contexts remain separate until medication-level prediction.

## Adjacent shared/private and expert routing

### Multi-gate Mixture-of-Experts — KDD 2018

**Modeling Task Relationships in Multi-task Learning with Multi-gate Mixture-of-Experts**

MMoE shares experts while learning task-specific gates.

Boundary:

- shared/private computation and task-specific allocation are established primitives;
- an additional gate is not itself a contribution.

For this reason the initial MHEF screen intentionally does **not** add a learned cross-view gate. It first tests whether the normalization-domain constraint itself carries signal.

## Current claim boundary

Do not claim:

```text
first label-specific attention
first target-aware evidence selection
first multi-view medication recommendation
first diagnosis/procedure-specific prediction
first dual-stream clinical modeling
first shared/private architecture
first mixture-of-experts routing
```

The scientific object under test is:

> For each candidate medication, use one shared medication-to-token relevance function over longitudinal fine EHR codes, preserve the validated global FineCode read, and additionally factorize the D/P/historical-medication softmax normalization domains so heterogeneous evidence sources do not enter zero-sum competition before medication-level prediction.

Whole-model novelty remains **plausible / unverified** until the computation survives matched-capacity controls and receives a post-survival primary-source audit.
