# Paper Experiment Contract v1.3 amendment

Status: CURRENT ADDITIVE AMENDMENT  
Effective date: 2026-09-19

Read this amendment together with v1.0, v1.1 and v1.2. It changes only the early project-owned DEVELOPMENT training horizon policy below. Seed policy, Test quarantine, evaluator semantics, external-baseline fidelity and final-confirmation rules remain unchanged.

## 1. Default DEVELOPMENT exploration horizon

For new project-owned architecture/mechanism screens, the default fixed training horizon is now:

~~~text
30 complete epochs
~~~

This replaces the previous routine use of 60 epochs for early architecture exploration.

The change is prospective. Historical 60-epoch experiments remain valid evidence for the protocols they actually ran.

The motivation is empirical and decision-focused: across recent project-owned architecture screens, selected Dev checkpoints for both successful and failed matched arms have consistently occurred within the first 3–8 epochs. The additional 30–50 epochs have not changed routing, while substantially reducing architecture hypotheses tested per wall-clock day.

This is a fixed budget, not early stopping. Every normal 30-epoch screen still performs complete Dev evaluation after every epoch and applies the frozen joint checkpoint/operating-point selection rule.

## 2. Horizon-censoring safeguard

A 30-epoch result may support a scientific verdict only when the selected checkpoint for every arm in the matched comparison satisfies:

~~~text
selected_epoch <= 25
~~~

If either arm selects a checkpoint in epochs 26–30, the comparison is:

~~~text
HORIZON_CENSORED
~~~

No scientific survive/kill verdict is issued from the 30-epoch run.

The exact same configuration, initialization convention, data semantics, optimizer and model-selection protocol must then be extended to a total of 60 epochs before the comparison is interpreted.

This extension is not a rescue or hyperparameter change. It is a predeclared check that the shorter horizon did not truncate a still-improving training trajectory.

## 3. Scope

The 30-epoch default applies to:

- initial project-owned architecture screens;
- bounded project-owned mechanism comparisons;
- project-owned survivor stability screens when the architecture has no prior evidence of late convergence.

It does not automatically apply to:

- source-faithful external baselines whose published/source protocol uses another budget;
- final Paper Candidate training;
- final frozen confirmation;
- any method with observed late convergence under an already-frozen protocol.

Those budgets are frozen separately according to source fidelity and final paper requirements.

## 4. No performance-conditioned budget selection

Do not compare a 30-epoch result against a 60-epoch result because the latter happened to look better.

Within one matched comparison, both arms share the same frozen horizon. If horizon censoring triggers, both arms are extended under the same unchanged protocol.

The shorter horizon exists to improve hypothesis throughput, not to create another tuning dimension.
