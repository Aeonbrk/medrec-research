<!-- markdownlint-disable MD013 -->

# Literature Search Notes — Residual False-Positive Routing

- **Date**: 2026-09-02
- **CCFA owners**: `ccf-literature-monitor` + `ccf-literature-searcher`
- **Purpose**: ground post-Idea-002 hypothesis selection; not a broad Related Work survey
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target because no venue was specified
- **Private-material policy**: searches used only public-safe concepts, public paper names, and public method families; no private repository text or unpublished result wording was copied into web queries
- **Source policy**: primary proceedings, arXiv, PubMed, ACM, Springer/Elsevier paper pages, DBLP, and official project/author pages were preferred. Policy-excluded sources were not used as evidence.

## Recent monitoring window

```text
2026-08-26 through 2026-09-02
```

The monitoring pass searched recent medication-recommendation, confidence/uncertainty, history, set-structure, and ensemble/disagreement terms across arXiv-oriented web indexes and primary paper databases. No newly surfaced paper in this exact window was found to directly test the current residual question at the medication-candidate level.

**Monitor signal**: `RELAX`, with an explicit limitation: this is a bounded monitoring result, not proof that no paper exists.

The fresh window did not change the main prior-art risks. The decisive overlaps come from 2025-2026 work already available before the window, especially medication-confidence calibration, boundary-aware refinement, historical-medication modeling, and medication-set/co-recommendation modeling.

## Public-safe query families

Representative query families included:

```text
medication recommendation confidence calibration individual medication
medication recommendation boundary uncertainty confidence
medication recommendation relative confidence rank output set
medication recommendation continuation new medication history
medication recommendation co-prescription frequent pattern medication set
medication recommendation ensemble disagreement uncertainty
medication recommendation false positive selective prediction
```

Named-paper verification was then performed for the strongest overlaps.

## Screening decisions

The deep pass screened more than fifteen distinct results/paper records and retained the sources that changed a design or review decision. Search snippets were used only for discovery; claims retained in the grounding packet were tied to stable paper/proceedings/publisher records when available.

Key exclusions from the final grounding set:

- generic clinical uncertainty papers that did not change a MedRec-specific design choice;
- drug recommendation papers whose only overlap was the application label;
- low-quality aggregation pages when a primary or archival source was available;
- policy-excluded sources.

## Evidence boundary

`Source-supported observation` means the linked paper/source explicitly describes the stated problem, mechanism, or evaluation.

`Optimizer inference` means a cross-paper deduction used to shape a new hypothesis. It is not attributed to any paper.

`Search-scope uncertainty` means no direct work was found in the executed search, but absence is not proven.

No literature result in this folder is an experimental fact about `medrec-research`.
