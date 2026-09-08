<!-- markdownlint-disable MD013 -->

# Closest-Work Verification — Privileged Physiological Response Supervision

## Search boundary

- **Search date**: 2026-09-08
- **Primary time window**: 2023--2026, with emphasis on 2025--2026
- **Older anchor retained when directly relevant**: MedGCN (2022)
- **Primary provenance preference**: publisher/proceedings, PubMed, ACM/IEEE, arXiv original
- **Novelty question**: whether prior work already uses actual post-administration physiological observations only as training-time privileged supervision for a strictly pre-order deployable medication-recommendation student

This review is a bounded closest-work verification, not a universal novelty proof.

## Query families

The search covered the following functional-equivalence families rather than relying on title keywords alone:

1. medication recommendation + laboratory response / physiological response / post-administration monitoring;
2. medication recommendation + monitoring-event chains / medication injection + follow-up labs;
3. medication recommendation + future-state or lab-response auxiliary prediction;
4. medication recommendation + teacher-student / knowledge distillation;
5. EHR / clinical prediction + training-only privileged modality / cross-modal distillation;
6. medication-conditioned physiological-response representation;
7. future-observation privileged supervision / future-to-current distillation outside healthcare;
8. 2025--2026 time-aware / longitudinal MedRec methods for potential functional collision.

## Closest works

| Work | Year / venue | Stable identifier | What it already covers | Exact collision with candidate | Surviving delta | Provenance strength |
| --- | --- | --- | --- | --- | --- | --- |
| REFINE: Recommendation with multi-level representation learning and trend-informed learning | 2023 / NeurIPS | DOI `10.52202/075280-1043` | lab-test responses and dosage-titration trends used to characterize patient health for fine-grained medication recommendation | kills novelty from `lab response in MedRec` and response-trend representations | current-instance post-administration physiology is not retained as an inference input/history feature; candidate uses it only as privileged training supervision for a pre-order student | HIGH — NeurIPS proceedings |
| ChainCare: Clinical prediction via bidirectional monitoring event chains and multi-event time series modeling | 2026 / Information Processing & Management | DOI `10.1016/j.ipm.2026.104739` | jointly models lab tests and medication injections; explicitly models lab-first and injection-first event chains, including medication effects associated with follow-up labs; evaluates MedRec and disease prediction | strongest MedRec scientific-object collision; monitoring execution logic and medication→follow-up-lab representation are prior art | ChainCare models monitoring events as longitudinal predictive inputs/records; the searched source does not make the current post-administration trajectory a training-only privileged target for a strictly pre-order student | HIGH — Elsevier publisher |
| Integrating Medication Recommendation and Lab Test Response Prediction for Enhanced Clinical Decision Support | 2023 / AAAI Symposium Series | DOI `10.1609/aaaiss.v1i1.27489` | unified medication recommendation and lab-test response prediction | kills novelty from joint MedRec + future/lab response prediction; provides a direct conceptual baseline for Generic Future-State Auxiliary | candidate must show that paired medication-in-context privileged response representation adds value beyond generic future-state/lab prediction | HIGH — AAAI proceedings |
| MedGCN: Medication recommendation and lab-test imputation via graph convolutional networks | 2022 / Journal of Biomedical Informatics | DOI `10.1016/j.jbi.2022.104000` | multitask medication recommendation and lab-test imputation | kills generic lab auxiliary / multitask novelty | training-only post-administration response supervision with strict pre-order student remains different | HIGH — peer-reviewed journal / PubMed |
| DrugDoctor: A personalized medication recommendation system based on historical medical records | 2024 / Briefings in Bioinformatics | DOI `10.1093/bib/bbae464` | historical medication information is paired with nearest downstream historical health condition to encode effectiveness-aware history | covers downstream health-state-after-medication as ordinary historical response evidence | candidate uses the current realized future trajectory only during training and removes it entirely at inference | HIGH — peer-reviewed journal / PubMed |
| MR-DTR: Time-aware Medication Recommendation via Intervention of Dynamic Treatment Regimes | 2025 / The Web Conference (WWW) | DOI `10.1145/3696410.3714533` | time-aware medication recommendation under dynamic treatment-regime framing | compresses generic temporal / treatment-dynamics novelty | no identified collision with current-instance future physiology as privileged-only supervision | HIGH — ACM proceedings |
| LEADER: Large Language Model Distilling Medication Recommendation Model | 2024 / arXiv | arXiv `2402.02803` | feature-level knowledge distillation for medication recommendation | kills novelty from teacher-student/KD mechanics in MedRec | knowledge source would need to be medication-in-context future physiology, with evidence that it matters beyond generic KD | MEDIUM — original preprint |
| OC-Distill: Ontology-aware Contrastive Learning with Cross-Modal Distillation for ICU Risk Prediction | 2026 / arXiv | arXiv `2604.16878` | extra modality available during training transfers into a reduced-modality clinical prediction student | establishes generic clinical training-time privileged modality distillation | candidate remains MedRec-specific only if response semantics, not generic multimodal privilege, explain the gain | MEDIUM — original preprint |
| Learning Patient Health Conditions From Physiological Responses to Vasoactive Agents | 2025 / IEEE EMBC | DOI `10.1109/EMBC58623.2025.11254154`; PMID `41336312` | medicine-aware representation of transient physiological responses to vasoactive infusions for patient health-state monitoring/downstream prediction | establishes medication-conditioned physiological-response representation as a primitive | not a general medication-recommendation student and not a training-only privileged-response deployment contract | HIGH — IEEE / PubMed |
| Privileged Foresight Distillation: Zero-Cost Future Correction for World Action Models | 2026 / arXiv | arXiv `2604.25859` | true future observations available to a training-time teacher are distilled into a current-only student; controlled experiments distinguish future-conditioned correction from generic regularization | kills novelty from `future observation teacher -> current-only deployable student` as a generic method idea | only the MedRec-specific response learning object and its matched mechanism evidence can remain novel | MEDIUM — original preprint |

## Closest-work subtraction

The current candidate cannot claim any of the following as novel:

- using labs/vitals or lab responses in medication recommendation;
- modeling medication administration followed by physiological monitoring;
- joint medication recommendation and lab/future-state prediction;
- learning a medication-aware physiological-response representation;
- knowledge distillation for medication recommendation;
- training-time privileged clinical modalities with reduced-modality inference;
- using actual future observations to teach a current-only student.

The only search-scoped residual delta is:

> **paired medication-in-context post-administration physiological values as training-only privileged supervision for a strictly pre-order candidate-medication recommender, where matched controls establish that the incremental value depends on focal medication identity, patient-medication-response correspondence, individualized physiological values, and not merely generic future prediction, monitoring availability, static medication priors, or KD mechanics.**

This delta is credible enough for one bounded revision/re-review cycle. The
bounded optimizer packet now freezes the mechanism-identification controls in
`idea-optimization.md`; it is still not strong enough for Idea 007 creation
until strict re-review accepts the frozen contract.

## Collision classes

### A — Labs/vitals as ordinary inference input

Not equivalent to the candidate. REFINE and ChainCare nevertheless make generic monitoring/lab novelty unavailable.

### B — Future-state prediction auxiliary task

Highly relevant and potentially mechanism-killing. Bhoi et al. and MedGCN establish that lab-response/lab auxiliary learning is not novel. A matched Generic Future-State Auxiliary / Medication-Ablated Future control is mandatory.

### C — Historical treatment-response encoding

Highly relevant but not equivalent. DrugDoctor and REFINE show that downstream/historical response evidence can be represented and reused. The candidate's remaining distinction is current-instance future information used only during training.

### D — Generic privileged-information / cross-modal distillation

Direct prior art. OC-Distill and broader LUPI/KD work make `teacher sees more information` non-novel.

### E — MedRec-specific teacher/student distillation

Direct prior art through LEADER. KD mechanics cannot be the paper contribution.

### F — Generic future-to-current distillation

Direct 2026 prior art outside MedRec through Privileged Foresight Distillation. The information-flow pattern itself is no longer sufficient novelty.

### G — Causal treatment-effect / counterfactual outcome learning

Not the candidate's admissible claim. Observed post-administration trajectories in retrospective EHR do not identify individual medication effects under the current design. Any effect/efficacy/counterfactual language would create a soundness failure rather than a novelty gain.

## Novelty verdict

`MODERATE / SEARCH-SCOPED / REQUIRED-REVISIONS-BEFORE-IDEA`

No exact direct general-MedRec collision was found in the retained search. The method family therefore should not be rejected solely for prior-art identity.

However, the combination is close to a composition of established primitives. CCF-A-level novelty depends on demonstrating a non-obvious, medication-specific information object through killer controls. A standard `Ours > Base` result would not survive closest-work subtraction.

## Required literature-aware controls

Any later Gate 01 must include, with matched support/window/capacity where applicable:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Generic KD when needed to isolate KD mechanics;
- a compatible monitoring-aware MedRec baseline such as REFINE/ChainCare when task alignment makes the comparison scientifically valid.

## Provenance notes

Publisher/proceedings/PubMed records were preferred for peer-reviewed works. arXiv records are retained when the closest relevant method is currently a preprint; those entries are marked `MEDIUM` rather than treated as peer-reviewed evidence.

Absence of a direct collision in this bounded search is not evidence that no such paper exists. The review conclusion is therefore intentionally phrased as a search-scoped novelty delta.
