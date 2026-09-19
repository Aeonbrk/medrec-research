# EBRA Closest-Work Boundary Audit

Status: **PRE-SCREEN CLAIM BOUNDARY — NOT A FINAL NOVELTY VERDICT**

This document defines what EBRA may and may not claim before the matched Train/Dev screen. If the mechanism survives, a broader primary-source novelty audit remains mandatory before Paper Candidate freeze.

## SSPNet is the closest current MedRec boundary

**SSPNet: Leveraging Robust Medication Recommendation with History and Knowledge** — Zhang et al., IJCAI 2025.  
Primary source: <https://www.ijcai.org/proceedings/2025/1052>  
PDF: <https://www.ijcai.org/proceedings/2025/1052.pdf>

SSPNet explicitly frames medication recommendation as set-to-set prediction, uses permutation-consistent set processing, models interactions among medication representations with self-attention, conditions them on diagnosis/procedure sets, and reports MIMIC-III/MIMIC-IV experiments.

However, the published prediction head remains a named-medication multi-label classifier: the paper applies sigmoid outputs per medication, thresholds those values into a multi-hot vector, and states that optimization is treated as a multi-label binary classification problem with BCE, multi-label margin, and DDI losses.

Therefore EBRA cannot claim:

- first set-to-set medication recommendation;
- first permutation-consistent medication decoder;
- first parallel medication-set prediction;
- first medication-dependency modeling;
- first Transformer set decoder for MedRec.

The unresolved computational distinction is narrower: SSPNet retains one score/probability per named medication and threshold decoding, whereas EBRA tests medication-or-NULL latent decision elements with one-to-one target assignment and native set decoding.

## Direct set prediction primitives are occupied

**End-to-End Object Detection with Transformers (DETR)** — Carion et al., ECCV 2020.  
Primary source: <https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/832_ECCV_2020_paper.php>

DETR establishes the conjunction of learned parallel queries, Transformer decoding, bipartite matching, unique predictions, and a no-object class for direct set prediction.

EBRA therefore cannot claim learned set queries, Hungarian/bipartite matching, uniqueness constraints, NULL/no-object prediction, or parallel direct-set decoding as new primitives.

**Deep Set Prediction Networks (DSPN)** — Zhang et al., NeurIPS 2019.  
Primary source: <https://proceedings.neurips.cc/paper_files/paper/2019/hash/6e79ed05baec2754e25b4eac73a332d2-Abstract.html>

DSPN establishes general permutation-respecting set prediction and explicitly motivates avoiding fixed output responsibility/order artifacts. EBRA cannot claim the general responsibility problem of ordered/fixed outputs as a new discovery.

## Project-local negative boundaries

EBRA is not a rescue of previously killed formulations:

- ECRC showed that conditioning named-medication utilities on regimen cardinality has negligible oracle and negative predicted-cardinality value.
- MEMB showed that cross-medication competition at the evidence-binding stage does not materially improve FineCode/PredictionLocal.
- MSED showed that richer local-support distribution shape is not the missing signal.
- MHEF showed that modality-specific normalization is unnecessary after a strong capacity control.
- RouteFact showed that forcing prediction through administration-route factors degrades accuracy.
- output-side reranking/repair remains low-prior.

EBRA moves the structural constraint into the native training target and decoder rather than predicting a count, modifying evidence allocation, or repairing a completed score vector.

## Current permissible scientific question

The first screen asks only:

> With the same medication-specific FineCode proposal bank, learned query bank, Transformer decision block, score function, information budget, and parameter budget, does free permutation-invariant medication-or-NULL assignment outperform fixed slot-to-medication binary responsibility?

That question is falsifiable without claiming a new primitive.

## Novelty risk

Current novelty risk is **moderate**.

A targeted primary-source search did not identify a medication-recommendation paper using this exact evidence-bound proposal -> latent medication-or-NULL slots -> bipartite supervision -> one-to-one native regimen decoding computation graph. That absence is not a firstness proof.

If the screen survives, search specifically for:

- medication recommendation with Hungarian/bipartite matching;
- DETR-style medication or treatment set generation;
- latent medication-set elements with NULL/no-treatment state;
- direct partial assignment over drug identities;
- permutation-invariant prescription generation;
- set prediction methods whose decoder produces unique labels through matching rather than thresholded multi-label scores.

## Prohibited novelty language

Do not claim:

- first structured medication recommendation;
- first set-to-set MedRec;
- first set decoder for medications;
- first drug-dependency model;
- first permutation-invariant prescription model;
- first bipartite matching method in healthcare;
- first direct set prediction model.

A future claim must be about the complete computation graph and must be supported by post-survival closest-work verification.
