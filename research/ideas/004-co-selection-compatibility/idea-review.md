<!-- markdownlint-disable MD013 -->

# Idea Review — Post-Idea-003 Residual False-Positive Routing

- **CCFA flow**: `ccf-idea-optimizer / exploratory` -> `ccf-idea-reviewer / standard`
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Literature cutoff entering review**: 2026-09-03
- **Fresh monitor window**: 2026-09-02 through 2026-09-03; no decision-changing new work found
- **Closest-work packet**: `literature-search-20260903-co-selection-fp-routing/`
- **Decision goal**: select one materially new observable for the cheapest decisive validation-only Gate; no architecture investment

## Exploratory candidate set

The exploratory pass deliberately produced competing information families without scoring or ranking. Scores appear only in the strict-review section.

### Candidate 1 — Frequency-Corrected Co-Selection Compatibility

- **Problem**: a medication can be individually confident yet atypical relative to the identities of the other medications simultaneously predicted.
- **Falsifiable claim**: conditional on frozen medication score, predicted set size, candidate prevalence, and peer-set popularity, one train-only frequency-corrected co-selection statistic adds reproducible medication-level false-positive routing information.
- **New observable information**: mean train-only pairwise NPMI between candidate $m$ and all peers in $\hat M_t$.
- **Why materially different from Ideas 001--003**: it uses medication identities and train-only pair relations rather than DDI degree, a function of the candidate score, or relative score position.
- **Why not reducible to frozen recommender score**: equal-score candidates can have different peer identities and different train-only pair relations.
- **Mechanistic rationale**: residual false positives may be enriched among candidates whose simultaneous regimen context is statistically atypical after marginal popularity is removed.
- **Closest prior-art risk**: HI-DR weighted EHR Graph+, DMRNet frequent patterns, MSAM collective medication effects, GenRxR co-recommended medication modeling, GRAIN EHR co-prescription graph, CRHP collaborative relation graphs.
- **Novelty delta**: conditional medication-level error routing beyond a frozen score and trivial set/popularity controls; neither co-prescription modeling nor NPMI itself is claimed as new.
- **Strongest simple control**: frozen score + predicted set size + train-only candidate prevalence + mean train-only peer prevalence + minimal score interactions.
- **Cheapest falsification**: one train-only relation matrix, one scalar per candidate, two low-capacity Dev fits, one held-out Audit comparison.
- **PASS criterion**: support and residual-headroom gates pass; lower 95% patient-clustered bootstrap CI for `CoSelectionAugmented - StrongControl` is strictly positive at both primary budgets.
- **FAIL criterion**: otherwise terminate the one-scalar co-selection route; no graph/attention rescue on the same evidence.
- **Prediction-time availability**: yes; current frozen predicted set plus training-only aggregates.
- **Leakage boundary**: no validation/test targets in pair statistics; no Audit fitting; test untouched.
- **Portability**: high for aligned multi-label medication vocabularies.
- **Scientific value if PASS**: establishes that explicit medication-set relation information survives compression into the backbone score and explains held-out residual FP heterogeneity.
- **Scientific value if FAIL**: rules out the cheapest frequency-corrected relation statistic before any relational architecture investment.
- **Main confound**: marginal medication popularity and peer-set popularity.
- **Architecture explicitly not justified**: GNN, hypergraph encoder, Transformer/Mamba relation module, LLM verifier.

### Candidate 2 — Immediate Previous-Prescription Membership

- **Problem**: continuation and newly proposed medications can have different error profiles at the same frozen score.
- **Falsifiable claim**: $\mathbf1[m\in M_{t-1}]$ adds medication-level FP-routing information beyond score, popularity, set size, and medication-specific train-only persistence propensity.
- **New observable information**: one patient-specific historical bit.
- **Why materially different from Ideas 001--003**: uses observed patient history strictly before visit $t$.
- **Why not reducible to frozen recommender score**: equal-score candidates can differ in previous-prescription membership.
- **Mechanistic rationale**: patient-specific continuation state can provide evidence not perfectly preserved in the current output score.
- **Closest prior-art risk**: COGNet copy-or-predict, KERL reusable historical-drug path, HeteroMed expansion/inheritance, DMRNet historical drug recalibration, DrugDoctor historical-prescription learning.
- **Novelty delta**: only a narrow confidence-conditional error-routing diagnostic; continuation semantics are established prior art.
- **Strongest simple control**: frozen strong control + train-only medication-specific persistence propensity.
- **Cheapest falsification**: one binary feature.
- **PASS criterion**: held-out incremental routing yield at both primary budgets.
- **FAIL criterion**: terminate the immediate-continuation route; no history encoder rescue.
- **Prediction-time availability**: yes for follow-up visits.
- **Leakage boundary**: only visits strictly before $t$; no current target as feature; test untouched.
- **Portability**: high on longitudinal EHR tasks, unavailable for true first visits.
- **Scientific value if PASS**: clean evidence that patient-specific transition state explains residual errors.
- **Scientific value if FAIL**: kills the cheapest longitudinal hypothesis before richer temporal modeling.
- **Main confound**: population chronicity/persistence of each medication.
- **Architecture explicitly not justified**: history encoder, retrieval model, RNN/Transformer/Mamba.

### Candidate 3 — Current Clinical-Code Association Support

- **Problem**: the backbone score may compress current diagnosis/procedure evidence in a way that hides whether a candidate has explicit empirical support from the current clinical codes.
- **Falsifiable claim**: one train-only diagnosis/procedure-to-medication association scalar adds FP-routing information beyond score, set size, medication prevalence, and current code count.
- **New observable information**: transparent train-only code-medication association derived from current diagnoses/procedures.
- **Why materially different from Ideas 001--003**: reads patient-conditioned current clinical codes rather than DDI degree or output-score geometry.
- **Why not reducible to frozen recommender score**: multiple code configurations can map to equal output scores while differing in explicit association support.
- **Mechanistic rationale**: explicit evidence mismatch may reveal fragile predictions after model compression.
- **Closest prior-art risk**: CRHP disease-drug relations, DrugDoctor disease-medication association modeling, HI-DR health-status-aware medication evidence, HypeMed current-visit combinatorial semantics.
- **Novelty delta**: only conditional error diagnosis; current clinical evidence is standard MedRec input.
- **Strongest simple control**: frozen strong control + current diagnosis/procedure counts and train-only medication prevalence.
- **Cheapest falsification**: one train-only association table and one scalar.
- **PASS criterion**: held-out incremental routing yield at both primary budgets.
- **FAIL criterion**: terminate the explicit-association scalar route.
- **Prediction-time availability**: yes.
- **Leakage boundary**: current diagnoses/procedures only; no current medications except frozen prediction outputs; test untouched.
- **Portability**: medium-high where code vocabularies align.
- **Scientific value if PASS**: evidence that transparent current evidence retains residual information after the frozen score.
- **Scientific value if FAIL**: removes an obvious handcrafted projection before more patient-conditioned machinery.
- **Main confound**: code-count and medication-prevalence effects.
- **Architecture explicitly not justified**: heterogeneous GNN, retrieval encoder, LLM evidence model.

### Candidate 4 — Active-DDI Local Clustering Residual

- **Problem**: Idea 001 tested active DDI degree but not whether equal-degree candidates occupy different local topology inside the predicted prescription's induced DDI graph.
- **Falsifiable claim**: candidate-local DDI clustering adds FP-routing information beyond frozen score and active DDI degree.
- **New observable information**: fraction of interacting pairs among the candidate's active DDI neighbors in the predicted set.
- **Why materially different from Idea 001**: degree counts neighbors; clustering observes edges among those neighbors. Equal-degree candidates can differ in clustering.
- **Why not reducible to frozen recommender score**: depends on external DDI topology and peer identities.
- **Mechanistic rationale**: a candidate embedded in a densely conflicting local subcombination may mark a structurally incoherent prediction beyond simple conflict count.
- **Closest prior-art risk**: broad DDI graph encoding is established in SafeDrug-family work, Carmen, GraphDiffMed, GRAIN, and many safety-aware recommenders.
- **Novelty delta**: narrow conditional FP-routing statistic after degree control.
- **Strongest simple control**: frozen strong control + active DDI degree.
- **Cheapest falsification**: one topology scalar from the already frozen DDI graph.
- **PASS criterion**: held-out incremental routing yield at both primary budgets.
- **FAIL criterion**: terminate this local-topology scalar; no GNN rescue.
- **Prediction-time availability**: yes.
- **Leakage boundary**: frozen DDI graph and predicted set only; no target.
- **Portability**: medium-high if DDI vocabularies align.
- **Scientific value if PASS**: shows degree-insufficient topology carries residual correctness information.
- **Scientific value if FAIL**: removes the cheapest topology refinement of the failed degree route.
- **Main confound**: active DDI degree.
- **Architecture explicitly not justified**: DDI GNN or learned topology encoder.

### Candidate 5 — Cross-Model Corroboration / Disagreement

- **Problem**: a MoleRec prediction may be fragile when independently frozen recommenders do not corroborate it.
- **Falsifiable claim**: disagreement-specific information adds FP-routing value beyond MoleRec score and the best simple ensemble.
- **New observable information**: aligned outputs from independent frozen baselines.
- **Why materially different from Ideas 001--003**: uses independent model evidence.
- **Why not reducible to frozen MoleRec score**: other models can disagree at equal MoleRec confidence.
- **Mechanistic rationale**: model-specific epistemic disagreement may expose fragile predictions.
- **Closest prior-art risk**: generic ensemble/selective-prediction literature and Multi-LLM Collaboration for Medication Recommendation.
- **Novelty delta**: medication-level routing conditional on a best-simple-ensemble control.
- **Strongest simple control**: MoleRec strong control + best simple ensemble built from the same aligned model outputs.
- **Cheapest falsification**: only cheap if already frozen, visit-aligned validation outputs exist for multiple qualified backbones.
- **PASS criterion**: a disagreement statistic adds held-out value beyond the ensemble control.
- **FAIL criterion**: terminate disagreement-specific routing.
- **Prediction-time availability**: only with multiple deployed/frozen backbones.
- **Leakage boundary**: every contributing output must be target-free and validation-only; test untouched.
- **Portability**: medium.
- **Scientific value if PASS**: evidence for independent-model corroboration beyond ensemble mean quality.
- **Scientific value if FAIL**: prevents an expensive verifier/ensemble route.
- **Main confound**: ordinary ensemble gain.
- **Architecture explicitly not justified**: learned ensemble, gating network, verifier model.

## Closest-work deductions

1. **Co-selection compatibility** survives only as a conditional error-routing question. HI-DR already makes weighted co-prescription strength explicit; DMRNet/MSAM/GenRxR/GRAIN further crowd generic relation modeling.
2. **Previous-prescription membership** faces a high-confidence novelty blocker. COGNet directly introduced copy-or-predict, while KERL, HeteroMed, DMRNet, and DrugDoctor all operationalize historical medication reuse. A binary diagnostic remains testable but is not the strongest successor idea.
3. **Current code association** uses information already central to MedRec models and risks being a handcrafted re-expression of backbone input rather than a distinct scientific source.
4. **DDI local clustering** is genuinely different from active degree but has the weakest mechanism-to-label link: DDI topology describes conflict structure, while the Gate label is medication false-positive status.
5. **Cross-model disagreement** is not currently cheap enough. In the MoleRec-positive candidate universe, binary corroboration tends to collapse toward ensemble support, so a disagreement-specific claim requires richer aligned scores and a best-simple-ensemble control. The repository does not currently expose an authoritative aligned validation artifact establishing that prerequisite.

## Strict reviewer ranking

Weights and fatal-gate semantics follow the standard `ccf-idea-reviewer` rubric. Scores are reviewer judgments under the generic CCF-A venue assumption, not empirical outcomes.

| Rank | Candidate | Weighted score (1-5) | Confidence | Fatal / dominant risk | Recommendation |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | Frequency-Corrected Co-Selection Compatibility | **4.12** | 4/5 | closest-work density; novelty collapses if framed as generic co-prescription modeling | `revise / select for concretization` |
| 2 | Immediate Previous-Prescription Membership | **3.67** | 5/5 | high-confidence novelty blocker from copy/continuation prior art | `pivot-with-rescue-route` |
| 3 | Current Clinical-Code Association Support | **3.61** | 4/5 | may be only a handcrafted projection of standard backbone inputs | `pivot-with-rescue-route` |
| 4 | Active-DDI Local Clustering Residual | **3.52** | 3/5 | weak mechanistic bridge from DDI topology to FP status | `pivot-with-rescue-route` |
| 5 | Cross-Model Corroboration / Disagreement | **3.34** | 3/5 | ordinary-ensemble explanation plus unverified aligned-validation prerequisite | `pivot-with-rescue-route` |

## Winner scorecard

| Dimension | Weight | Score | Confidence | Main deduction |
| --- | ---: | ---: | ---: | --- |
| Problem importance | 12 | 4.5 | 5 | residual FP heterogeneity is real but retrospective |
| Novelty against prior work | 14 | 3.5 | 4 | relation modeling is crowded; only conditional routing delta survives |
| Conceptual innovation | 12 | 4.0 | 4 | new information relative to tested controls, intentionally not a new architecture |
| Method soundness | 14 | 4.5 | 4 | frequency correction plus explicit popularity controls make the claim sharp |
| Elegance and simplicity | 8 | 5.0 | 5 | one bounded transparent relation statistic |
| Feasibility | 8 | 5.0 | 5 | training-only aggregates plus frozen validation inference |
| Experimental convincibility | 10 | 4.8 | 5 | decisive held-out incremental test with useful negative outcome |
| Venue and audience fit | 8 | 3.8 | 3 | Gate 01 is research selection, not paper-ready evidence |
| Timeliness | 6 | 4.2 | 4 | active 2025--2026 relation/history work makes the question timely and crowded |
| Risk-adjusted acceptance potential | 8 | 3.8 | 3 | later portability/generalization would still be required after PASS |

**Weighted final score**: `4.12 / 5`.

**Confidence**: `4 / 5`.

**Fatal risks**: none at Idea-selection level if the novelty wording remains conditional and the primary control includes peer popularity. A direct paper testing the same frozen-score-controlled medication-level FP-routing question would create a novelty fatal gate.

**Repairable risks**:

- co-selection can proxy medication popularity -> control candidate and peer-set prevalence;
- co-selection can proxy prescription size -> control predicted set size;
- pair statistics can be noisy for rare medications -> freeze one smoothed bounded statistic rather than selecting among relation formulas on validation outcomes;
- MoleRec already consumes EHR information -> claim residual explicit-statistic information, not a new raw data source.

**Score-change conditions**:

- increase novelty/method confidence if broader closest-work search continues to find no direct conditional FP-routing study and Gate 01 produces reproducible incremental held-out evidence;
- decrease novelty to fatal if direct prior art tests essentially the same decision unit, control stack, and target-free statistic;
- decrease method score if the proposed statistic is changed post hoc after Audit inspection or if peer popularity is omitted from the primary control.

## Winner

`Frequency-Corrected Co-Selection Compatibility` is selected for `ccf-idea-optimizer / standard` concretization as Idea `004-co-selection-compatibility`.

It is not selected because a positive result is expected. It wins because it introduces materially different information relative to Ideas 001--003, has a sharper mechanism than generic “use relations,” can face its strongest trivial explanation in a low-capacity control, and can be killed with one validation-only Gate before any relational architecture is justified.
