<!-- markdownlint-disable MD013 -->

# Idea-Grounding Packet

## Scope And Evidence Boundary

- **Topic / seed**: retrospective medication prescriptions as selective/partial supervision rather than exhaustive positive/negative clinical labels.
- **Search date**: 2026-09-05.
- **Source-supported facts**:
  - KRAM is a 2026 MedRec method for noisy-label robustness and evaluates synthetic random replacement/addition noise.
  - DMRNet addresses medication-frequency imbalance and historical drug recurrence.
  - FineMed adds diagnosis-level medication supervision.
  - Physician-RAG constructs expert CORE / ALT / AVOID medication categories rather than treating one historical set as the entire acceptable treatment space.
  - SafeRx-Agent reports at least one case where a prediction outside current-visit ground truth is interpreted as a clinically reasonable continuation.
  - Generic recommender research has established PU/MNAR implicit-feedback objectives and recent counterfactual formulations.
- **Searcher inference**: a MedRec-specific opportunity may remain in modeling the prescription-generation/observation process, but only if it produces a domain-specific method beyond generic PU or false-negative weighting.
- **Unknowns**: whether the existing structured MIMIC pipeline contains enough information to identify that observation mechanism without new clinician labels, notes, labs, or external treatment ontologies.

## Evidence Cards

| Source | Supported observation | Reported limitation / boundary | Mechanism primitive | Protocol anchor | Transfer condition | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| KRAM (ESWA 2026) | MedRec performance is vulnerable to label noise; co-denoising and label refinement are viable baselines | Evaluation noise is induced by random replacement/addition | noisy-label sample selection / label refinement | MIMIC-III; MedRec metrics | New route must differ from synthetic symmetric corruption | direct |
| DMRNet (Neural Networks 2026) | Medication-frequency skew and historical recurrence materially affect recommendations | Focus is imbalance/rarity rather than uncertain negative semantics | prevalence debiasing / historical recalibration | MIMIC-III/IV | New route must survive frequency/history controls | direct |
| FineMed (Information Sciences 2026) | Diagnosis-level medication supervision and fine-grained subrecommendations are already method territory | Mapping is a different supervision target from prescription observation | supervision decomposition | MIMIC-III/IV + external dataset | Do not claim novelty for diagnosis-aware labels alone | direct |
| Physician-RAG (IJMI 2026) | Expert medication references distinguish CORE, ALT, AVOID categories | 800-case retrospective expert evaluation is not the current training pipeline | multi-valid treatment reference semantics | real-world expert reference | Supports problem semantics, not direct training labels | direct |
| SafeRx-Agent (2026 preprint) | At least one current-ground-truth false positive was clinically interpreted as reasonable continuation | Case-level existence evidence only | ground-truth incompleteness example | case analysis | Cannot estimate prevalence from one case | direct |
| WSDM 2020 MNAR implicit feedback | Unobserved interaction is not necessarily a negative; PU and MNAR require explicit handling | Consumer exposure/click model differs from clinician prescribing | unbiased PU/MNAR risk | implicit-feedback recommendation | Clinical observation model must be justified separately | direct |
| Counterfactual Implicit Feedback Modeling (NeurIPS 2025) | Joint PU/MNAR can be formulated through counterfactual estimation | General recommendation, not clinical prescribing | counterfactual observation model | implicit-feedback benchmarks | Strong generic prior-art/control risk | direct |
| Correct-and-Weight (2026 preprint) | Uncertain negatives can be down-weighted using PU-style correction and confidence weighting | Generic implicit-feedback loss; current preprint | negative decontamination / weighting | sparse recommendation benchmarks | Simple killer control for loss-only ideas | direct |

## Cross-Source Relations

| Source pair / cluster | Relation | Open gap or conflict | Why it matters | Evidence needed next |
| --- | --- | --- | --- | --- |
| Physician-RAG + SafeRx-Agent | supports | Historical/current-visit medication set need not exhaust clinically acceptable choices | Makes exact set labels scientifically narrower than treatment relevance | A method formulation that does not require pretending all unlabeled drugs are positive |
| KRAM vs proposed supervision family | leaves-open | KRAM denoises injected label corruption; selective prescribing may be structured one-sided missingness | Defines closest MedRec baseline while preserving a different premise | Optimizer must state identifiable difference and killer control |
| DMRNet vs proposed supervision family | leaves-open | Frequency bias/history recurrence can mimic apparent uncertain-negative gains | Prevents relabeling long-tail correction as a new supervision mechanism | Frequency-stratified and history-aware controls |
| Generic PU/MNAR vs proposed supervision family | conflicts-with | Generic false-negative correction is already mature prior art | A plug-in PU loss would not carry CCF-A novelty | Domain-specific prescribing observation mechanism and objective |
| FineMed vs proposed supervision family | leaves-open | Finer supervision is crowded, but its target is diagnosis-to-drug correspondence rather than choice observation | Prevents a generic 'fine-grained labels' story | Keep existing 131-label action space unless mechanism requires otherwise |

## Idea Constraints

### Already covered central claims

- `unobserved item != negative` is generic recommender prior art.
- `MedRec labels can be noisy` is covered by KRAM.
- `medication distribution is imbalanced` and history can rescue rare drugs are covered by DMRNet.
- `diagnosis-level supervision improves fine-grained recommendation` is covered by FineMed.

### Transferable mechanism primitives

- PU/MNAR risk correction as a baseline/control family, not novelty by itself.
- structured label refinement from KRAM as a MedRec-specific comparator.
- clinically multi-valid reference semantics from Physician-RAG as motivation for the observation model.
- longitudinal prescription history only if used to identify supervision reliability rather than as another inference-time feature.

### Protocols suitable for direct comparison

- Existing MIMIC-III comparison pipeline and 131-medication vocabulary.
- Existing comparison-ready backbones, after a single-backbone premise survives.
- Current standard Jaccard/F1/PRAUC/DDI metrics for benchmark comparability, with claim language explicitly separating retrospective label agreement from clinical correctness.

### Stale or overcrowded routes

- generic PU/nnPU/CW loss transplant;
- class-balanced or focal/asymmetric loss presented as the method contribution;
- diagnosis-to-medication mapping without a new supervision premise;
- historical medication copying/recalibration;
- another post-hoc selector over frozen scores;
- new KG/RAG/LLM pipeline to infer hidden positives without independent semantic admission.

### Minimum viable research question

> Can the retrospective prescription-generation process be modeled as **selective medication supervision**—where observed prescriptions are positive actions but unprescribed candidates have heterogeneous negative reliability—and can a MedRec-specific training objective exploit that structure beyond generic PU/MNAR and noisy-label controls using the current structured EHR pipeline?

This question is ready for `ccf-idea-optimizer`, not for experiment execution. The optimizer must reject it if the only implementable mechanism is a generic loss substitution or if evaluation becomes circular without new ground truth.
