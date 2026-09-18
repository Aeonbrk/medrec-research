# Closest-work boundary — final relational architecture search

Status: **PRE-SCREEN CLAIM BOUNDARY**

This note constrains the scientific claims before training. It does not establish final novelty.

## Medication-recommendation work

### CSRec — JMIR Medical Informatics 2025

DOI: 10.2196/74170

CSRec constructs heterogeneous/homogeneous medical-entity graphs, captures interentity synergies with graph attention, and then forms comprehensive patient representations for medication recommendation.

Boundary:

- heterogeneous clinical interaction is occupied;
- diagnosis/procedure/medication synergy is occupied;
- graph attention over medical entities is occupied.

The current candidate is distinct only if its relation object remains a fine-code pair selected in the perspective of each candidate medication and directly contributes to that medication decision rather than first becoming one shared patient representation.

### DMGExNet — Engineering Reports 2026

DOI: 10.1002/eng2.70899

DMGExNet explicitly models diagnosis-procedure interaction with bidirectional cross-attention and then concatenates the interacted streams into a patient health-status representation.

Boundary:

- diagnosis-procedure cross-attention is occupied;
- preserving two clinical streams is occupied.

The proposed pair-relation model must therefore be positioned around medication-indexed fine relation evidence and the absence of a shared patient bottleneck, not around the generic existence of D-P interaction.

### Carmen — AAAI 2023

DOI: 10.1609/aaai.v37i6.25861

Carmen uses patient context and medication-clinical co-occurrence context to shape medication molecular representations.

Boundary:

- medication-specific context is occupied;
- medication-clinical association is occupied.

The candidate cannot claim first candidate-aware medication context.

## Adjacent interaction-modeling primitives

### Bilinear Attention Networks — NeurIPS 2018

BAN explicitly models pairwise interactions between two groups of input channels with low-rank bilinear pooling and bilinear attention maps.

Boundary:

- bilinear pair attention is an established primitive;
- low-rank pair interaction is an established primitive.

The project may reuse this primitive. Novelty must reside in the complete EHR-to-medication computation graph and validated medication-specific relation object.

### Attentional Factorization Machines — IJCAI 2017

AFM constructs element-wise pairwise feature interactions and uses attention to weight their contribution.

Boundary:

- element-wise pair products are established;
- attention over pairwise feature interactions is established.

### DeepFM — IJCAI 2017

DeepFM demonstrates the general value of explicitly combining lower-order feature interactions with learned higher-order representation in recommendation.

Boundary:

- retaining a unary/main path alongside an interaction path is established architecture practice.

## Current claim boundary

Do not claim:

~~~text
first pairwise feature interaction
first bilinear attention
first diagnosis-procedure interaction
first heterogeneous EHR interaction
first medication-specific context
first relation-aware recommendation
~~~

The scientific object under test is narrower:

> A medication-specific decision preserves direct access to fine clinical codes while also selecting non-separable cross-type relations among those codes before any shared patient-level compression.

The final paper novelty remains unverified until a surviving complete architecture receives a post-stability primary-source closest-work audit.
