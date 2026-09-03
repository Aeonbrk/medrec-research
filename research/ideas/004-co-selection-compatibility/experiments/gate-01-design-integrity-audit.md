<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Audit — Co-Selection Compatibility

- **Mode**: `ccf-integrity-auditor / claim-audit`
- **Artifact audited**: `gate-01-co-selection-compatibility.md`
- **Idea**: `004-co-selection-compatibility`
- **Audit scope**: design integrity only; no real-data execution and no result audit
- **Verdict**: `DESIGN_INTEGRITY_PASS`

## Claim-evidence matrix

| Design claim | Evidence / protocol binding | Verdict |
| --- | --- | --- |
| Gate question matches selected Idea 004 | Idea asks whether one train-only frequency-corrected co-selection statistic adds medication-level FP-routing information beyond the strongest simple control; Gate tests exactly that | supported |
| New observable is materially different from Ideas 001--003 | Uses medication identities plus train-only pair co-selection relations, not DDI degree/Tension, score remapping, or relative score rank | supported |
| Observable is available at prediction time | Uses frozen current predicted set/scores and aggregates computed only from training prescriptions | supported |
| Co-selection does not stand in for marginal popularity | Primary control includes candidate prevalence and peer-set mean prevalence plus fixed score interactions | supported |
| Candidate universe and revision semantics are unchanged | $\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\}$ and singleton deletion are frozen | supported |
| Outcome remains benchmark FP status | $Y^{PB}_{t,m}=\mathbf1[m\notin M_t]$ is evaluation-only and never an input | supported |
| PASS rule tests incremental information | Requires lower 95% CI of `CoSelectionAugmented - StrongControl` to be strictly positive at both 10% and 20% budgets | supported |
| FAIL rule preserves exact falsification boundary | Failure terminates only the preregistered one-scalar empirical-NPMI representation and forbids same-information rescue | supported |
| Residual-headroom diagnostic cannot substitute for mechanism evidence | Oracle headroom is a separate prerequisite Gate B and cannot create a PASS | supported |
| Train / Dev / Audit firewall is explicit | Train builds aggregates; Dev fits fixed selectors; Audit evaluates frozen selectors only | supported |
| Historical validation adaptivity is explicit | Idea-004 Audit is described as held-out route-selection evidence, not untouched final-generalization evidence | supported |
| Test is untouched | Protocol explicitly prohibits indexing, staging, prediction, evaluation, and diagnostics on test | supported |
| No target leakage is authorized | Current target/future visits/validation-derived pair statistics/Audit fitting are forbidden | supported |
| No post-hoc rescue path exists | Formula, seed, control, budgets, relation statistic, and architecture are frozen before Audit | supported |
| No unnecessary architecture is introduced | Gate uses one scalar and fixed low-capacity ridge linear ranking estimator | supported |
| Literature delta matches novelty wording | Closest work already covers co-prescription/relation modeling; novelty is restricted to frozen-score-controlled medication-level FP routing | supported |

## Statistical-definition integrity

The exact pair statistic is empirical NPMI. Zero co-selection count is fixed to `-1`, matching the limiting NPMI semantics for zero joint occurrence; full joint support is fixed to `+1`. No data-dependent smoothing, support threshold, shrinkage, clipping, or choice among relation formulas is permitted.

This preserves the intended interpretation that never-observed pairs are not treated as strongly compatible merely because both marginals are rare.

## Control integrity

`StrongControl` contains frozen candidate risk (`1-score`), predicted-set size, train-only candidate prevalence, peer-set mean prevalence, and only their predeclared score interactions. These variables address the actual trivial explanations for a co-selection statistic: individual confidence, set-size composition, candidate popularity, and popularity of the surrounding regimen.

`CoSelectionAugmented` differs by exactly one scientific feature, $A_t(m)$. No additional relation feature is hidden in the control.

## Split and inference integrity

- Idea-seed convention is deterministic and outcome-independent: `2004` for the Idea-004 Dev/Audit patient split.
- Bootstrap seed is fixed: `1204`.
- Bootstrap unit is patient, with 1000 percentile replicates.
- Dev coefficients and train-only aggregates remain frozen inside bootstrap.
- Audit support failure yields an inconclusive verdict; it does not authorize a new split.

## No-invention status

No Gate result, expected direction, expected coefficient, expected PASS probability, candidate-level real-data record, or test statistic is present. The protocol remains `DESIGNED_NOT_EXECUTED`.

## Design verdict

`DESIGN_INTEGRITY_PASS`

The protocol is internally aligned with the selected Idea, closest-work boundary, strongest-control requirement, prediction-time/leakage contract, held-out route-selection semantics, and exact PASS/FAIL decision tree. No further design iteration is required before implementation freeze.

## Next CCFA owner

Local execution agent, beginning at P0 state/protocol verification. The agent may implement and execute only the frozen P0--P6 workflow and must stop after P6.
