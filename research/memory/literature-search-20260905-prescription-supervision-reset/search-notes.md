<!-- markdownlint-disable MD013 -->

# Search Notes

## Search Mode

`ccf-literature-searcher / exploratory`

This was the single bounded reset authorized after B0 failure. It was not a broad 'latest medication recommendation' search.

## Safe Queries Used

Representative public queries:

- `medication recommendation positive-unlabeled prescription 2023 2024 2025 2026`
- `medication recommendation partial label missing medication labels`
- `KRAM medication recommendation label noise 2026`
- `CEHMR medication recommendation hierarchical multi-label`
- `Physician-RAG CORE ALT AVOID medication recommendation 2026`
- `medication recommendation imbalanced medication distribution temporal history 2026`
- `FineMed medication mapping diagnosis-level supervision 2026`
- `unbiased recommender learning missing-not-at-random implicit feedback WSDM 2020`
- `Counterfactual Implicit Feedback Modeling NeurIPS 2025`
- `Correct and Weight implicit feedback false negatives 2026`

## Sources Checked

Primary/high-confidence sources included:

- ScienceDirect / Elsevier paper pages;
- PubMed;
- official WSDM pages and DOI metadata;
- official NeurIPS proceedings;
- stable arXiv pages;
- the user-maintained 64-paper `xray-papers-innovation-summary.md` as the project's primary literature prior.

## Screened Clusters

1. MedRec noisy-label robustness: KRAM.
2. MedRec hierarchical/multi-label objective design: CEHMR.
3. Medication-frequency and historical-recurrence debiasing: DMRNet.
4. Diagnosis-aware fine-grained supervision: FineMed.
5. Clinically grounded non-exhaustive medication evaluation: Physician-RAG and SafeRx-Agent case analysis.
6. Generic PU/MNAR recommendation: WSDM 2020, NeurIPS 2025 Counterfactual Implicit Feedback Modeling, and current false-negative loss work.

Broader longitudinal, KG/RAG/agent, rule-safety, and action-change families were not re-expanded because the repository reorientation already marks them crowded or conditionally closed and B0 supplied no evidence that reopens them.

## Excluded Sources

- Policy-excluded venue/domain sources, including MDPI, were omitted from the final report.
- Search-engine mirrors, scraped copies, and ResearchGate were not used as primary provenance when a publisher/proceedings/arXiv source was available.
- Generic recommendation papers were retained only when they establish a mechanism that creates a direct novelty/control risk for the candidate supervision route.

## Unknowns

- No exhaustive theorem-level search proves that no MedRec paper has ever used a PU objective. The targeted 2023--2026 search found no close MedRec method whose central premise is that unprescribed medications are structurally heterogeneous unlabeled outcomes under a selective prescribing process.
- Current MIMIC labels do not identify the complete clinically acceptable medication set. That is precisely the supervision problem; it also limits direct clinical validation of any method using only retrospective set overlap.
- It remains unknown whether a MedRec-specific observation mechanism can be identified from the existing structured pipeline strongly enough to beat generic PU/MNAR losses without importing expensive new annotations.

## Handoff Notes

### For idea optimization

Optimize exactly one hypothesis family:

`PRESCRIPTION_SUPERVISION_ASYMMETRY / SELECTIVE_PRESCRIBING_OBSERVATION`

The optimizer must answer:

1. What is the MedRec-specific observation mechanism that makes a prescription vector scientifically different from generic implicit-feedback clicks?
2. What learned objective or supervision mechanism follows from that observation model?
3. What makes the method non-equivalent to nnPU, propensity correction, asymmetric/focal loss, label smoothing, KRAM-style label refinement, or Correct-and-Weight?
4. What can be evaluated with the current MIMIC pipeline without claiming that unobserved drugs are clinically correct?
5. What is the cheapest method-premise kill test, and what result terminates the family rather than triggering feature rescue?

If these questions cannot be answered with a domain-specific mechanism and a CCF-A-level contribution shape, return `NO_HIGH_VALUE_DIRECTION_YET` and do not create Idea 006.

### For direction scouting

Do not reopen B0/cardinality, generic post-hoc routing, ATC sibling substitution, generic longitudinal modeling, or generic KG/RAG/agent safety from this reset.

### For experiment design

No new empirical diagnostic is authorized by the search itself. Experiment design begins only after idea optimization/review admits a method hypothesis.
