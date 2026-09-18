# CCTM closest-work audit — computation-graph boundary

Status: **NOVELTY PLAUSIBLE AT MODEL-LEVEL / NOT PAPER-FROZEN**

This audit does not ask whether any prior work uses trajectories, temporal attention, graphs, GRUs, or medical-code recurrence. Those primitives are occupied. The relevant question is whether the complete computation graph proposed for medication recommendation is already present.

## Proposed computation graph under audit

```text
historical typed code occurrences
  -> group by patient-specific (modality, code) identity
  -> temporally encode each recurrent concept trajectory
  -> trajectory-indexed evidence memory

current diagnosis/procedure evidence
  + trajectory-indexed history memory
  -> static medication-specific late evidence read
  -> medication logits
```

The paper-level object would be the combination of **patient-specific concept-trajectory evidence memory** and **medication-specific late binding**, not any individual temporal encoder or attention layer.

## Closest work

### TRANS — IJCAI 2024

`Predictive Modeling with Temporal Graphical Representation on Electronic Health Records`, DOI `10.24963/ijcai.2024/637`.

TRANS constructs a patient-specific temporal heterogeneous graph with unique diagnosis/procedure/medication code nodes and timestamped visit nodes. Code nodes connect to visits in which they occur, and temporal features are placed on code-to-visit and visit-to-visit edges. This is the strongest collision with the concept-identity axis.

Boundary: TRANS keeps a graph of code and visit nodes and ultimately aggregates information into visit representations for a shared predictor. It does not form one explicit temporal state per typed concept trajectory and then expose those trajectory states as an addressable memory to separate candidate-medication queries.

Consequence: **same-code-across-visits representation is not novel**. A CCTM paper cannot claim that simply grouping repeated concepts or connecting them across visits is new.

### ARCI — CIKM 2024

`Contrastive Learning on Medical Intents for Sequential Prescription Recommendation`, DOI `10.1145/3627673.3679836`.

ARCI uses visit-level and cross-visit Transformers to learn multiple medication-code temporal paths over consecutive visits, regularized by distinct medical intents.

Boundary: ARCI's temporal paths are medication-to-medication dependencies between consecutive prescription visits. They are not typed diagnosis/procedure/medication identity trajectories spanning arbitrary prior visits, and the final recommendation is not produced by one medication-specific query reading a trajectory-indexed patient evidence memory.

### DCGM — Expert Systems with Applications 2026

`Enhanced drug recommendation based on dynamic clinical trajectory aggregation and geometry-enhanced molecular representation`, DOI `10.1016/j.eswa.2026.132225`.

DCGM dynamically selects historically similar disease/medication visits and aggregates them before drug recommendation.

Boundary: its trajectory mechanism is current-state-conditioned historical visit retrieval/selection. It does not create a persistent state for each repeated typed clinical concept, and it does not expose concept trajectories as separately addressable evidence for each candidate medication.

### DMGExNet — Engineering Reports 2026

`DMGExNet: A Dual-Stream Transformer-Guided Multi-Graph Collaborative Explainable Network for Medication Recommendation`, DOI `10.1002/eng2.70899`.

DMGExNet jointly captures longitudinal history and cross-sectional diagnosis/procedure interactions with a dual-stream encoder and fuses them into a patient representation.

Boundary: the longitudinal stream remains patient-level; it does not preserve one patient-specific state per concept identity for medication-specific evidence access.

### GraphDiffMed — AIAI 2026

`GraphDiffMed: Knowledge-Informed Differential Attention with Pharmacological Graph Priors for Medication Recommendation`, DOI `10.1007/978-3-032-30612-8_28`.

GraphDiffMed applies differential attention at intra-visit and inter-visit scales and combines temporal modeling with pharmacological constraints.

Boundary: its temporal structure is visit-scale noise-aware attention rather than identity-indexed concept trajectories followed by medication-specific late evidence binding.

### Med-BERT — npj Digital Medicine 2021

`Med-BERT: pretrained contextualized embeddings on large-scale structured electronic health records for disease prediction`, DOI `10.1038/s41746-021-00455-y`.

Med-BERT visualizations show that attention heads can connect the same code across different visits. This is important prior evidence that same-code recurrence can be useful structure.

Boundary: same-code temporal attention is emergent inside a general Transformer, not an explicit per-concept trajectory memory and not a medication-recommendation late-binding architecture.

## Audit verdict

1. **Primitive novelty: NO.** Longitudinal code relationships, same-code cross-visit structure, temporal paths, and patient graphs are all occupied.
2. **Representation-only novelty: WEAK.** `group same codes -> temporal encoder` by itself would be too close to existing EHR representation work, especially TRANS.
3. **Model-level novelty: PLAUSIBLE.** The full information flow `typed concept trajectory memory -> medication-specific late evidence read -> medication logits` was not identified in the audited closest work.
4. **Claim boundary:** if this direction survives experimentally, the method must be presented as a medication-decision architecture that preserves longitudinal evidence provenance until candidate-specific late binding, not as the invention of concept trajectories.
5. **Next blocker:** data supportability. Do not implement or train the architecture unless the frozen Train-only recurrence audit returns `SUPPORT_CCTM_PREMISE`.

Novelty confidence at this stage: **medium**. A survivor would still require a second closest-work audit before Paper Candidate Freeze.
