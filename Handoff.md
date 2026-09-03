# Handoff: Idea 004 Gate 01 Frozen Design

## Current state

Idea `004-co-selection-compatibility` is selected after literature-grounded exploratory ideation and strict CCFA review. Gate 01 has been designed and passed design-level integrity audit. It has not been executed.

- **Idea ID**: `004-co-selection-compatibility`
- **Idea Status**: `SELECTED / GATE_01_DESIGNED_NOT_EXECUTED`
- **Gate**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-co-selection-compatibility.md`
- **Design Audit**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-design-integrity-audit.md`
- **Design Verdict**: `DESIGN_INTEGRITY_PASS`
- **Idea Selection Commit**: `f29c9db61f001d88efe7c789b6f0793378add5af`
- **Test Split**: unindexed, unpredicted, and untouched
- **ccfa.yaml**: absent; per `ccf-pipeline-orchestrator`, project-state tracking remains unavailable and no file should be created solely for this workflow

## Scientific question

$$
\boxed{\text{Does one train-only frequency-corrected co-selection statistic explain medication-level false-positive heterogeneity beyond the strongest simple frozen control?}}
$$

The candidate universe and revision operator remain:

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\},
$$

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

The retrospective outcome remains:

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

## Exact observable

`CoSelectionCompatibility` is the mean empirical train-only NPMI between candidate $m$ and every other medication in the same frozen predicted prescription. For pair count zero, NPMI is fixed to `-1`; for full joint support, it is fixed to `+1`; otherwise empirical NPMI is used.

No alternative co-selection formula is authorized after Audit inspection.

## Strongest simple control

`StrongControl` contains:

- frozen MoleRec candidate risk `1-score`;
- log predicted-set size;
- train-only candidate-prevalence log odds;
- train-only peer-set mean-prevalence log odds;
- score-by-size, score-by-candidate-prevalence, and score-by-peer-prevalence interactions.

`CoSelectionAugmented` adds exactly one feature: `CoSelectionCompatibility`.

## Split and inference

- patient-disjoint validation Dev/Audit split;
- split seed `2004`, derived from the established Idea-number convention before outcome inspection;
- fixed ridge linear probability ranking estimator, penalty `1e-6`;
- primary budgets 10% and 20%; 30% descriptive only;
- patient-clustered bootstrap, 1000 replicates, seed `1204`;
- PASS requires lower 95% CI of `CoSelectionAugmented - StrongControl` to be strictly positive at both primary budgets, after Audit-support and Oracle-headroom gates pass.

## Evidence boundary

Ideas 001--003 support only scoped negative conclusions for their tested routes. They do not establish exhaustion of static, relational, longitudinal, structural, patient-conditioned, or cross-model information. Retrospective Oracle headroom does not prove target-free observability.

Idea 004's closest-work neighborhood is dense: HI-DR, DMRNet, MSAM, GenRxR, GRAIN, CRHP, COGNet, KERL, and HeteroMed already cover medication relations and/or longitudinal reuse for recommendation. The novelty delta is restricted to conditional medication-level false-positive routing beyond a frozen score and explicit trivial controls.

## Next owner

Local execution agent only.

Execute exactly:

```text
P0 state/protocol verification
P1 exact Idea-local implementation
P2 minimal synthetic scientific-semantics verification
P3 freeze implementation revision
P4 one formal validation-only 319 execution
P5 independent ccf-integrity-auditor audit
P6 research decision
STOP
```

Do not redesign the Idea or Gate, access test, run multiple outcome-seeking attempts, add features, begin Gate 02, begin Idea 005, or invest in a relational architecture.
