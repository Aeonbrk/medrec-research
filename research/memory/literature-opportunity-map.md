<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Purpose

This is a compact cross-idea literature refresh for the current pre-Idea premise stage. It supplements the user-maintained `xray-papers-innovation-summary.md` 64-paper prior; it is not a standalone novelty verdict and does not authorize a method.

Search mode: `ccf-literature-searcher / quick`.

Refresh date: 2026-09-05.

Source policy: primary publisher/proceedings pages, PubMed/DBLP, and stable arXiv pages. MDPI sources are excluded by CCFA source policy.

## High-value current papers

| Work | Type | What it covers | Implication for this project |
| --- | --- | --- | --- |
| FineMed, *Information Sciences* 2026, DOI `10.1016/j.ins.2026.123930` | pure method | Reformulates visit-level set prediction into diagnosis-aware sub-recommendations; uses medication mapping and diagnosis enhancement | Fine-grained action/supervision is already an active method direction. Any action-space pivot must exceed "map drugs to diagnoses" and must avoid circular weak supervision. |
| Beyond Accuracy, *Journal of Biomedical Informatics* 2026, DOI `10.1016/j.jbi.2026.105072` | other / evaluation guidance | Shows that aggregate accuracy/safety metrics can hide untreated conditions when drugs are stopped to avoid interactions | Strong motivation for the count/coverage premise, but it is evaluation evidence, not a method novelty claim. |
| Time-aware Medication Recommendation via Intervention of Dynamic Treatment Regimes, WWW 2025, DOI `10.1145/3696410.3714533` | pure method | Explicit time-aware longitudinal medication recommendation via dynamic treatment regimes | Generic "model treatment trajectory/history better" is crowded and is not a sufficiently sharp new premise. |
| DrugDoctor, *Briefings in Bioinformatics* 2024 | pure method | Visit-level representation learning, longitudinal health-condition matching, cold-start medication recommendation | Further weakens generic history-aware or patient-state retrieval novelty. |
| HeteroMed, 2026, DOI `10.1007/s13755-026-00430-5` | pure method | Heterogeneous graph and temporal medication modeling including introduction/retention structure | Add/retain temporal structure is already represented in current literature. |
| DAPSNet, *Bioinformatics* 2023, DOI `10.1093/bioinformatics/btad003` | pure method | Reports standard accuracy, DDI, and average-number-of-drugs metrics; ablations show DDI regularization changes both DDI and medication count | Supports treating medication count as a confound/control in safety comparisons, but does not answer the current B0 causal attribution question. |
| HypeMed, *ACM TOIS* 2026, DOI `10.1145/3803851` | pure method | Reports Jaccard/F1/PRAUC, DDI rate, and average medication count and explicitly treats prescription compactness as an evaluation dimension | Count is visible in current method evaluation, so a future paper cannot claim novelty from merely reporting it; the opportunity would have to be a method that resolves a demonstrated count-safety-fidelity mechanism. |

## Axis A update

Recent counterfactual clinical-AI evaluation already studies failure to update recommendations when patient state changes. This reduces the novelty of the phenomenon itself. More importantly, the current repository lacks an admitted independent positive treatment target after a contraindication becomes inactive.

Therefore the current blocker is semantic/methodological, not missing broad literature coverage:

> What learned target exists beyond direct current-state rule application?

Until that is answered, additional Axis A episode counting or generic counterfactual search has low expected value.

If the axis is ever reopened, counterfactual evaluation must include a meaning-preserving or clinically irrelevant null perturbation baseline so general model instability is not misread as targeted path dependence.

## Axis B update

The literature supports the concern that lower interaction burden can coexist with treatment omission, while current medication-recommendation papers commonly report average medication count alongside DDI and fidelity metrics. The closest current method collision is not a paper that performs the exact B0 intervention; rather, the field already exposes all ingredients separately.

The remaining falsifiable premise is therefore narrow:

> Under this repository's frozen predictions, does restoring target cardinality with the unchanged ranking recover enough fidelity while worsening normalized DDI rate enough to justify a new allocation mechanism?

This answer is in project-local data, not in literature. Literature search should not replace B0.

## Action-space granularity

FineMed strengthens the hypothesis that visit-level set prediction may be too coarse for clinically meaningful correspondence, but it also raises the collision bar. A new action-space route would need a materially different supervision or decision unit and an independently grounded mapping; simply decomposing the prescription by diagnosis is no longer sufficient positioning.

Idea 005 supplies a complementary local warning: ATC-3 sibling structure is not automatically therapeutic interchangeability.

## Current opportunity judgment

- Generic longitudinal modeling: `CROWDED / LOW PRIOR`.
- Generic rule/KG/RAG safety injection: `CROWDED / LOW PRIOR`.
- Generic diagnosis-aware fine-graining: `CROWDED`; FineMed is direct close work.
- Path-dependent rule refresh: `BLOCKED` until an independent positive target is admitted.
- Count-controlled treatment-preserving safety: `ACTIVE PREMISE`, but only B0 is authorized.
- Action-space granularity: `OPEN PREMISE`, not yet an Idea.

The literature does not currently justify creating Idea 006. The next evidence owner remains the bounded local B0 premise audit.

## Stable source links

- FineMed: https://doi.org/10.1016/j.ins.2026.123930
- Beyond Accuracy: https://doi.org/10.1016/j.jbi.2026.105072
- MR-DTR: https://doi.org/10.1145/3696410.3714533
- HeteroMed: https://doi.org/10.1007/s13755-026-00430-5
- DAPSNet: https://doi.org/10.1093/bioinformatics/btad003
- HypeMed: https://doi.org/10.1145/3803851
