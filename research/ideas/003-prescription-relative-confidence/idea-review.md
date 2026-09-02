<!-- markdownlint-disable MD013 -->

# Idea Review — Post-Idea-002 Residual Routing

- **CCFA flow**: `ccf-idea-optimizer` exploratory → `ccf-idea-reviewer` standard
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Literature status**: searched; closest-work packet in `literature-search-20260902-residual-fp-routing/`
- **Decision goal**: choose one cheap, falsifiable next hypothesis; no architecture investment yet

## Exploratory candidate set

### Candidate 1 — Prescription-Relative Confidence Residual

- **Parent / operation**: Idea 002 residual opportunity / `refine` with a materially new output-set observable
- **Problem**: identical absolute medication confidence may occur in visits with different local competition among predicted medications.
- **Claim**: conditional on frozen medication confidence, predicted-set size, and a train-only medication-prevalence control, within-prescription relative confidence position provides reproducible incremental information about medication-level false-positive status.
- **New observable information**: for $n_t=|\hat M_t|$ and $n_t\ge2$,

  $$
  r_t(m)=\frac{|\{j\in\hat M_t:s_t(j)>s_t(m)\}|+\tfrac12|\{j\in\hat M_t\setminus\{m\}:s_t(j)=s_t(m)\}|}{n_t-1}.
  $$

  Higher $r_t(m)$ means lower relative confidence inside the same predicted prescription.
- **Why it is not reducible to scalar score**: $r_t(m)$ depends on the scores of the other medications in the same predicted set. Two candidates with the same $s_t(m)$ can have different $r_t(m)$.
- **Mechanistic rationale**: the backbone's absolute score may be visit-conditionally compressed or expanded; local competition can expose whether a candidate is weak relative to the model's other simultaneous commitments.
- **Closest prior-art risk**: KDD'25 confidence calibration, GiantMed absolute boundary selection, and a 2026 single-choice antibiotic study using Top1-Top2 confidence margin.
- **Novelty delta**: multi-label medication-candidate routing; within-prescription relative position; explicit held-out incremental test after strong absolute-score and trivial prescription-context controls.
- **Strongest simple control**: Dev-fitted low-capacity `Score + SetSize + train-only medication prevalence` control, including a frozen score×set-size interaction; candidate model adds only $r_t(m)$.
- **Cheapest falsification**: one validation-only fresh patient split, fit control and rank-augmented selectors on Dev, compare Audit PBYield at frozen budgets with patient-clustered bootstrap.
- **PASS criterion**: support and residual-headroom checks pass and the 95% lower CI for `RankAugmented - StrongControl` is strictly positive at both primary budgets.
- **FAIL criterion**: otherwise, terminate this minimal prescription-relative-confidence route.
- **Leakage boundary**: current target prescription cannot define any selector feature or fit; Audit labels cannot fit features or coefficients; test remains untouched.
- **Prediction-time availability**: yes; $s_t(\cdot)$ and $\hat M_t$ are frozen model outputs, and medication prevalence is computed from training data only.
- **Portability across backbones**: high for multi-label recommenders exposing per-medication scores and a predicted set.
- **Scientific value if PASS**: establishes that prescription-local output context contains incremental target-free error information beyond absolute confidence and trivial set-size/popularity explanations.
- **Scientific value if FAIL**: rules out the cheapest within-output-set context signal before relational/history/ensemble investment.
- **Main confound**: relative rank partly encodes prescription size and medication popularity; both are therefore controlled explicitly.

### Candidate 2 — Train-Only Co-Selection Compatibility Residual

- **Parent / operation**: residual opportunity / `instrument` with train-only set structure
- **Problem**: a predicted medication may be individually confident yet weakly supported by the rest of the predicted medication set under historical co-prescription structure.
- **Claim**: conditional on score, set size, and medication frequency, a transparent train-only co-selection compatibility scalar provides incremental FP-routing information.
- **New observable information**: smoothed average or minimum train-only pair compatibility between $m$ and the other medications in $\hat M_t$, with the exact statistic frozen before Audit.
- **Why it is not reducible to scalar score**: it depends on medication identities and train-only pair structure, not only $s_t(m)$.
- **Mechanistic rationale**: unsupported co-selection may identify a candidate that is inconsistent with the model's simultaneously selected regimen.
- **Closest prior-art risk**: MSAM collective medication effects, DMRNet frequent patterns, and GenRxR co-recommended medication modeling.
- **Novelty delta**: only the confidence-conditional *error-routing* formulation; generic medication-combination modeling is not new.
- **Strongest simple control**: score + predicted set size + train-only medication frequency.
- **Cheapest falsification**: one frozen train-only compatibility statistic; no GNN.
- **PASS criterion**: held-out incremental PBYield over the strong control at both primary budgets.
- **FAIL criterion**: terminate scalar co-selection routing; do not escalate to a graph encoder on the same premise.
- **Leakage boundary**: compatibility uses training prescriptions only; no Dev/Audit/test target prescriptions.
- **Prediction-time availability**: yes.
- **Portability across backbones**: high if medication vocabularies align.
- **Scientific value if PASS**: shows set relations explain residual FP heterogeneity after confidence/popularity controls.
- **Scientific value if FAIL**: removes the strongest simple co-selection mechanism before neural relational modeling.
- **Main confound**: compatibility can collapse to popularity/frequency; controls must absorb that explanation.

### Candidate 3 — Previous-Prescription Membership Residual

- **Parent / operation**: residual opportunity / `refine` temporal semantics to one bit
- **Problem**: continuation candidates and newly proposed medications may have different error profiles at the same confidence.
- **Claim**: previous-prescription membership adds incremental FP-routing information beyond score and train-only medication frequency.
- **New observable information**: $h_t(m)=\mathbf1[m\in M_{t-1}]$.
- **Why it is not reducible to scalar score**: it is a patient-history action-state variable.
- **Mechanistic rationale**: continuation reflects patient-specific treatment inertia/context not fully summarized by the current score.
- **Closest prior-art risk**: COGNet, KERL, HeteroMed, and DMRNet directly operationalize historical medications/continuation.
- **Novelty delta**: narrow confidence-conditional diagnostic only; continuation itself is not novel.
- **Strongest simple control**: score + train-only medication frequency, with history length as a trivial sensitivity control if retained before freezing.
- **Cheapest falsification**: one binary feature.
- **PASS criterion**: held-out incremental PBYield beyond control.
- **FAIL criterion**: no escalation to a history encoder on the same continuation premise.
- **Leakage boundary**: only visits strictly before $t$; never current target membership except for outcome evaluation on Audit.
- **Prediction-time availability**: yes.
- **Portability across backbones**: high for longitudinal datasets.
- **Scientific value if PASS**: a clean action-semantic residual effect.
- **Scientific value if FAIL**: eliminates the simplest history signal.
- **Main confound**: medication popularity and chronic-drug persistence.

### Candidate 4 — Cross-Backbone Corroboration Residual

- **Parent / operation**: residual opportunity / `combine` independent frozen predictors
- **Problem**: primary confidence may be high even when other independently trained/reproduced backbones disagree.
- **Claim**: disagreement among frozen MedRec backbones contains incremental FP-routing information beyond the primary score and the best simple ensemble.
- **New observable information**: vote count or normalized-score dispersion from independent frozen backbones for the same medication.
- **Why it is not reducible to scalar score**: it uses independent model evidence.
- **Mechanistic rationale**: model-specific epistemic disagreement may expose fragile predictions.
- **Closest prior-art risk**: generic ensemble/selective-prediction literature and Multi-LLM Collaboration for Medication Recommendation.
- **Novelty delta**: confidence-conditional medication-level routing across frozen MedRec backbones rather than collaborative generation.
- **Strongest simple control**: primary score + best simple ensemble prediction; otherwise “disagreement” is merely ensemble gain.
- **Cheapest falsification**: reuse frozen outputs from multiple qualified backbones and compare one disagreement statistic.
- **PASS criterion**: disagreement adds held-out routing value beyond the ensemble control.
- **FAIL criterion**: terminate disagreement mechanism.
- **Leakage boundary**: all model outputs must be target-free and generated from the same allowed prediction-time inputs.
- **Prediction-time availability**: yes if multiple backbones are deployed; otherwise operationally expensive.
- **Portability across backbones**: medium.
- **Scientific value if PASS**: evidence that independent model corroboration captures residual error information.
- **Scientific value if FAIL**: prevents expensive verifier/ensemble work.
- **Main confound**: ordinary ensemble quality and model heterogeneity.

## Closest-work deductions

1. **Candidate 1** survives the closest-work subtraction only if its claim remains conditional and within-prescription. Calling it “relative confidence” without that qualification would collide with existing margin/confidence work.
2. **Candidate 2** is scientifically testable but crowded. MSAM, DMRNet, and GenRxR make generic set compatibility/composition a weak novelty story.
3. **Candidate 3** has a high-confidence novelty blocker. Continuation/history is already explicit in multiple MedRec architectures.
4. **Candidate 4** risks collapsing into ordinary ensemble uncertainty unless it beats the best simple ensemble using the same frozen model outputs.

## Strict reviewer scores

Weights follow the standard `ccf-idea-reviewer` rubric.

| Rank | Candidate | Weighted score (1-5) | Confidence | Fatal risks | Current recommendation |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | Prescription-Relative Confidence Residual | **4.26** | 4/5 | no fatal gate; main risk is novelty collapse into calibration/boundary feature engineering | `revise` / develop after strict concretization |
| 2 | Train-Only Co-Selection Compatibility Residual | **3.74** | 4/5 | no fatal gate, but closest-work density is high | `revise` |
| 3 | Cross-Backbone Corroboration Residual | **3.44** | 3/5 | cost and ordinary-ensemble explanation | `pivot-with-rescue-route` |
| 4 | Previous-Prescription Membership Residual | **3.48** | 5/5 | novelty score <=2 with high confidence; fatal-gate cap applies despite slightly higher raw weighted score | `pivot-with-rescue-route` |

The ranking is serious-risk-adjusted rather than a simple sort of weighted score; Candidate 3's continuation route is demoted by the high-confidence novelty fatal gate.

### Winner dimension scorecard

| Dimension | Weight | Score | Confidence | Deduction / evidence basis | Repair condition |
| --- | ---: | ---: | ---: | --- | --- |
| Problem importance | 12 | 4 | 4 | residual error routing is real, but currently shown only on retrospective validation | preserve narrow evidence language |
| Novelty against prior work | 14 | 4 | 4 | calibration, boundary selection, and relative confidence exist; exact conditional multi-label routing test was not found | keep novelty delta on within-prescription conditional information, not “relative confidence” generally |
| Conceptual innovation | 12 | 4 | 4 | one new observable and conditional-information framing are nontrivial but intentionally small | do not inflate into a new architecture claim |
| Method soundness | 14 | 4 | 4 | mechanism is coherent; strongest risk is trivial set-size/popularity encoding | control set size, train-only prevalence, and score×size interaction |
| Elegance and simplicity | 8 | 5 | 5 | one scalar derived from frozen outputs; no retraining | retain one-scalar Gate 01 |
| Feasibility | 8 | 5 | 5 | one frozen MoleRec inference and low-capacity Dev fit | no extra backbone or external model |
| Experimental convincibility | 10 | 5 | 4 | central claim can be killed in one held-out validation-only gate | freeze Audit and patient-cluster bootstrap before execution |
| Venue and audience fit | 8 | 4 | 3 | generic CCF-A assumption; diagnostic contribution needs broader later evidence if Gate passes | treat Gate 01 as hypothesis selection, not paper-ready evidence |
| Timeliness | 6 | 4 | 4 | 2025-2026 confidence/boundary work makes the question timely but also crowded | position as residual-information diagnosis |
| Risk-adjusted acceptance potential | 8 | 4 | 3 | a PASS would still need portability/generalization later | do not claim publication readiness from Gate 01 |

**Weighted final score**: `4.26 / 5` (`8.52 / 10` optional scale).

**Current conference readiness**: medium.

**Development potential**: high.

**Main rejection risk**: a reviewer can say “this is another confidence-calibration/boundary heuristic.” The idea survives only because it asks a different conditional question and faces controls designed to eliminate set-size and popularity explanations.

**Score-change conditions**:

- `+0.3 to +0.5` on novelty/acceptance axes if a broader closest-work search continues to find no direct conditional multi-label routing study and Gate 01 shows reproducible incremental information.
- `-1 or more` on method/novelty if the rank effect disappears after the frozen strong control or if direct prior art is found testing the same observable, decision unit, and evidence path.

## Independent expert-panel synthesis

- **Field expert**: the residual question is specific and scientifically useful; strongest concern is whether an output-relative statistic teaches more than calibration. Repair: conditional held-out test.
- **Method expert**: mechanism is coherent because $r_t(m)$ contains other-score information; strongest concern is confounding by set size/popularity. Repair: include these in the primary control rather than as post-hoc analyses.
- **Experiment expert**: the winner has the cleanest kill test and useful negative result. No architecture is needed before the gate.
- **AC / venue expert**: Gate 01 alone is not a paper contribution; it is a strong research-selection experiment. Broader backbone/test evidence becomes relevant only after a PASS and later authorization.
- **Skeptical prior-art expert**: the wording must explicitly subtract KDD'25 calibration, GiantMed, and relative-margin work; generic “relative confidence” novelty is not defensible.

## Winner

`Prescription-Relative Confidence Residual` is selected for standard concretization.

The selection is not based on expected positive results. It wins because it introduces the smallest genuinely new observable, has the clearest mechanism, survives the strongest trivial explanations by construction, has the lowest execution cost, and produces a useful scientific conclusion under either PASS or FAIL.
