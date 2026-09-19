# MEMB Closest-Work Boundary Audit

Status: **PRE-SCREEN CLAIM BOUNDARY — NOT A FINAL NOVELTY VERDICT**

This audit prevents a known matching primitive from being mislabeled as the paper contribution. It is intentionally conservative. A formal closest-work/novelty audit is required only if the family survives the matched Train/Dev screen.

## Competitive normalization is occupied

**Object-Centric Learning with Slot Attention** — Locatello et al., NeurIPS 2020.  
Primary source: https://proceedings.neurips.cc/paper/2020/hash/8511df98c02ab60aea1b2356c013bc0f-Abstract.html

Slot Attention uses competitive attention over slots so different latent slots compete to explain inputs. MEMB therefore cannot claim competitive normalization or “evidence chooses among slots/labels” as a new primitive. A major difference is that MEMB's competing entities are fixed semantic medication identities rather than exchangeable anonymous object slots, but this difference must be evaluated at the complete computation-graph level.

**LoFTR: Detector-Free Local Feature Matching with Transformers** — Sun et al., CVPR 2021.  
Primary source: https://openaccess.thecvf.com/content/CVPR2021/html/Sun_LoFTR_Detector-Free_Local_Feature_Matching_With_Transformers_CVPR_2021_paper.html

LoFTR explicitly uses a dual-softmax operator: a score matrix is softmax-normalized along both matching dimensions and the two probabilities are multiplied to obtain soft mutual matching probabilities. MEMB's `mutual_code` is algebraically in this family. This is why `scale2_code` is mandatory: the product introduces score sharpening in addition to the cross-axis specificity term.

## Label-specific representations are occupied

**Label-Specific Document Representation for Multi-Label Text Classification** — Xiao et al., EMNLP-IJCNLP 2019.  
Primary source: https://aclanthology.org/D19-1044/

LSAN constructs label-specific document representations using label semantic information and attention. Medication-specific FineCode reading is therefore not novel merely because each output label has its own evidence representation.

## Token/region-to-label assignment is occupied

**OT-CLASS: Optimal Transport-Enhanced Multi-label Text Classification** — 2026 OpenReview submission/preprint; acceptance status not assumed here.  
Primary source: https://openreview.net/pdf?id=UCiDbOtHUb

OT-CLASS introduces an auxiliary word-to-label alignment task using optimal transport in multi-label text classification. It is particularly relevant conceptually because it explicitly aligns input tokens to output labels. It also illustrates that hard assignment assumptions can be too restrictive in multi-label settings. MEMB therefore cannot claim token-to-label alignment as a new learning object.

**Recover and Match: Open-Vocabulary Multi-Label Recognition through Knowledge-Constrained Optimal Transport** — Tan et al., CVPR 2025.  
Primary source: https://openaccess.thecvf.com/content/CVPR2025/html/Tan_Recover_and_Match_Open-Vocabulary_Multi-Label_Recognition_through_Knowledge-Constrained_Optimal_Transport_CVPR_2025_paper.html

RAM models region-to-label matching with knowledge-constrained optimal transport. It further occupies the general idea that irrelevant local evidence can induce spurious multi-label predictions and that explicit label–region matching can mitigate this.

## Fine-grained medication mapping is occupied

**Medication mapping and diagnosis enhancement for fine-grained medication recommendation (FineMed)** — Li et al., Information Sciences 2026.  
DOI: `10.1016/j.ins.2026.123930`

FineMed decomposes visit-level medication recommendation into diagnosis-aware sub-recommendations and establishes fine-grained drug–disease correspondences. MEMB cannot claim the first fine-grained medication–clinical-evidence mapping or first diagnosis-aware medication assignment.

**Debiased medication recommendation through fusing frequent pattern and temporal medical records (DMRNet)** — Li et al., Neural Networks 2026.  
DOI: `10.1016/j.neunet.2026.109168`

DMRNet includes cross-view drug prediction and mechanisms for frequent-pattern / temporal-prescription recalibration. Generic “cross-view patient-drug interaction” language is therefore not a defensible novelty boundary for MEMB.

## Current permissible scientific question

The bounded screen asks only:

> Given an already-validated medication-specific FineCode affinity matrix, does penalizing evidence that is generically compatible with many competing medication identities materially improve medication decisions beyond an exact score-sharpening control?

That question is scientifically useful even if the primitive is known because a negative result kills an entire assignment/competition family cheaply, while a strong positive result justifies designing a larger architecture around evidence-to-regimen assignment.

## What is not claimed

Do not claim:

- first competitive attention;
- first dual-softmax matching;
- first token-to-label alignment;
- first label-specific attention;
- first optimal-transport multi-label matching;
- first fine-grained medication mapping;
- first cross-view medication prediction.

If the mechanism survives, the follow-up novelty audit must search specifically for medication-semantic competitive evidence assignment over longitudinal EHR codes, partial/unbalanced assignment for multi-drug decisions, and medication-set architectures that jointly couple evidence allocation and regimen prediction.
