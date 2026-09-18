# Closest-work audit — fine-grained medication-specific iterative evidence reading

Status: **PRE-SCREEN BOUNDARY AUDIT**

This note records claim boundaries only. It does not assert final novelty.

## SARMR — IJCAI 2021

**Self-Supervised Adversarial Distribution Regularization for Medication Recommendation**  
DOI: `10.24963/ijcai.2021/431`

SARMR performs multi-hop reading over a key-value memory after encoding patient representations. Historical patient/admission representations are used as keys and corresponding medications as values; the multi-hop result updates a patient query/context representation.

Boundary: multi-hop medication-recommendation memory reading is occupied. The current candidate instead carries one state per candidate medication, reads fine-grained clinical-code evidence rather than an admission→medication KV memory, and keeps those candidate-specific states separate through the output.

## MRSC — CIKM 2021

**Multi-hop Reading on Memory Neural Network with Selective Coverage for Medication Recommendation**  
DOI: `10.1145/3459637.3482278`

MRSC uses selective coverage to improve multi-hop reading over a memory of previous admissions and derives informative patient representations.

Boundary: neither multi-hop reading nor selective repeated history reading can be claimed as new. The distinction must remain the medication-indexed state/evidence interface and code-level memory.

## MeSIN — Knowledge-Based Systems 2021

**MeSIN: Multilevel selective and interactive network for medication recommendation**  
DOI: `10.1016/j.knosys.2021.107534`

MeSIN models heterogeneous temporal sequences with an interactive LSTM and attentional selection, then globally fuses learned embeddings into a comprehensive patient representation.

Boundary: selective fine-grained medical evidence and recurrent interaction are occupied primitives. The candidate does not claim either primitive; its state remains indexed by medication rather than collapsing to one patient representation before output.

## MHLAT — 2023

**MHLAT: Multi-hop Label-wise Attention Model for Automatic ICD Coding**  
arXiv: `2309.08868`

MHLAT applies repeated label-wise attention for automatic ICD coding.

Boundary: multi-hop label-specific attention is occupied in adjacent clinical prediction. Paper-level novelty, if any, must come from the complete MedRec computation graph and demonstrated mechanism, not from the generic label-wise multi-hop primitive.

## Current boundary verdict

```text
primitive novelty:              NO
multi-hop novelty:              NO
label-wise attention novelty:   NO
fine-code attention novelty:    NO
whole MedRec computation graph: PLAUSIBLE / requires post-survival audit
```

Candidate claim under review:

> fine-grained longitudinal EHR evidence is repeatedly acquired by persistent medication-specific decision states that remain uncollapsed until medication-level outputs.

A positive stability screen is necessary but not sufficient for a paper-level novelty claim.
