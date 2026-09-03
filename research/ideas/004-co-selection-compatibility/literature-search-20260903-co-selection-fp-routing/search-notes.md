<!-- markdownlint-disable MD013 -->

# Search Notes — 2026-09-03 Residual FP Routing

## CCFA mode

`ccf-literature-monitor` followed by `ccf-literature-searcher / standard`.

## Fresh monitor

- **Repository literature cutoff**: `2026-09-02`
- **Monitor as-of date**: `2026-09-03`
- **Fresh window searched**: `2026-09-02` through `2026-09-03`
- **Signal**: `NO_DECISION_CHANGING_NEW_WORK`

Searches targeted newly indexed medication/drug recommendation work on arXiv, ACM/official proceedings, PubMed/publisher pages, and OpenReview/venue surfaces. No work found in the one-day monitored window changed the candidate-family judgment. Older or previously known 2025--2026 works remain the decisive closest work.

## Deep-search scope

The closest-work search deliberately covered more than the fresh window and screened work relevant to five information families:

1. patient-specific longitudinal transition / recurrence;
2. medication-set relational and co-prescription structure;
3. patient-conditioned current clinical evidence;
4. DDI structure beyond active degree;
5. cross-model corroboration/disagreement.

The search also retained confidence-calibration work because frozen recommender confidence is the mandatory base control.

## Preferred sources

Primary or high-confidence sources were prioritized:

- ACM proceedings / DOI landing pages;
- AAAI official proceedings;
- PubMed and publisher article pages;
- arXiv for current preprints;
- official author/project pages when needed for code/status confirmation.

Low-quality paper aggregators were not used as novelty authority. Search-engine snippets and project literature memory were used only to locate primary sources.

## Decision-changing closest-work findings

### 1. Longitudinal history is crowded at the action-semantic level

COGNet already uses copy-or-predict from historical prescriptions. KERL models reusable historical drugs. HeteroMed explicitly models drug expansion and inheritance. DMRNet recalibrates recommendations using temporal prescription records. This blocks any novelty claim based only on “previous prescription membership,” “repeat versus novel,” or “history matters.”

A one-bit continuation diagnostic remains scientifically falsifiable, but its novelty delta is only the conditional medication-level error-routing test.

### 2. Co-prescription relations are also crowded, but the conditional error question remains distinct

HI-DR is the strongest subtraction because its EHR Graph+ explicitly represents the degree to which medications are prescribed together. DMRNet uses frequent patterns, MSAM models collective medication effects, GenRxR models co-recommended medication relationships, and GRAIN includes an EHR-derived co-prescription graph.

The viable delta is therefore not relation modeling. It is whether a **single frequency-corrected train-only relation statistic** contains held-out FP-routing information after frozen score and trivial popularity/set-composition controls.

### 3. Current-code association is plausible but not clearly new information

CRHP, HI-DR, HypeMed, and visit-level disease-medication models already make current clinical evidence central. A handcrafted code-medication association can differ from the backbone score, but it reprojects standard inputs rather than introducing a clearly independent evidence source.

### 4. DDI topology is logically open but mechanistically weak for the current label

Idea 001 did not exhaust topology beyond active degree. However, DDI graph topology primarily expresses interaction structure. The current outcome is false-positive medication status under singleton deletion. No closest work found gives a sufficiently sharp reason that local clustering, after degree control, should explain correctness rather than only safety structure.

### 5. Cross-model disagreement lacks the cheap-gate prerequisite

The project has qualified multiple baselines for Comparison Mode, but the authoritative public research state does not establish an existing frozen, visit-aligned **validation** prediction artifact across those models. In the current MoleRec-positive candidate universe, binary corroboration also tends to be ordinary ensemble support. A disagreement-specific test would need a best-simple-ensemble control and richer aligned scores, increasing cost before the central mechanism is even established.

## Searcher handoff

The literature supports carrying `Frequency-Corrected Co-Selection Compatibility` into strict review, with four constraints:

1. do not claim co-prescription relations or NPMI are novel;
2. keep frozen MoleRec confidence mandatory;
3. control candidate prevalence, peer-set prevalence, and predicted set size;
4. use one preregistered scalar before any learned relation architecture.

No literature result justifies automatic selection of longitudinal history.
