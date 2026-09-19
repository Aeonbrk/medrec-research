# Paper Experiment Contract v1.4 amendment

Status: CURRENT ADDITIVE AMENDMENT  
Effective date: 2026-09-20

Read this amendment together with v1.0–v1.3. It changes only the default training horizon for new project-owned DEVELOPMENT architecture/mechanism screens. Seed policy, Test quarantine, evaluator semantics, external-baseline fidelity, paper-candidate confirmation, and final-table rules remain unchanged.

## 1. Default early DEVELOPMENT horizon

For new project-owned architecture/mechanism screens, the default fixed training horizon is now:

~~~text
15 complete epochs
~~~

This prospectively replaces the 30-epoch default introduced by v1.3.

This is a fixed budget, not early stopping. Every normal screen still trains for all 15 epochs, evaluates complete Dev after every epoch, and applies the frozen joint checkpoint/operating-point selection rule. Partial training curves must not be used for scientific survive/kill decisions.

## 2. Empirical basis

The reduction is evidence-driven rather than convenience-driven.

Across the recent project-owned architecture screens inspected before this amendment:

- evidence-access portfolio arms selected checkpoints no later than Epoch 7;
- iterative-evidence stability conditions selected checkpoints no later than Epoch 8;
- final relational complete lanes selected Epoch 5;
- MHEF lanes selected Epoch 5;
- MSED lanes selected Epochs 3–8;
- MEMB lanes selected Epochs 3–7.

No inspected recent matched architecture arm required a selected checkpoint later than Epoch 8. The additional tail to 30 epochs repeatedly failed to change routing while consuming roughly twice the training compute of a 15-epoch screen.

Historical 30- and 60-epoch experiments remain valid evidence for the protocols they actually ran.

## 3. Horizon-censoring safeguard

A normal 15-epoch matched comparison may support a scientific verdict only when the selected checkpoint for every arm satisfies:

~~~text
selected_epoch <= 10
~~~

This preserves a five-epoch safety margin, matching the logic of v1.3.

If either arm selects Epochs 11–15, the comparison is:

~~~text
HORIZON_CENSORED_15_TO_30
~~~

No survive/kill verdict is issued from the 15-epoch result. The exact same comparison must be extended unchanged to a total of 30 epochs.

For that 30-epoch extension, the existing v1.3 rule remains active:

~~~text
selected_epoch <= 25
=> interpretable

selected_epoch in 26–30
=> HORIZON_CENSORED_30_TO_60
=> extend exact comparison unchanged to 60 epochs
~~~

A horizon extension is not a rescue, retune, or new experiment. Architecture, optimizer, loss, RNG convention, data semantics, information budget, evaluator, and model-selection procedure remain unchanged.

## 4. Scope

The 15-epoch default applies to:

- initial project-owned architecture screens;
- bounded project-owned mechanism comparisons;
- matched controls and anchors used inside those screens;
- project-owned survivor stability screens only when prior runs show no evidence of late convergence.

It does not automatically apply to:

- external published baselines whose source-faithful protocol requires a different horizon;
- methods with prior evidence of late convergence;
- PAPER_CANDIDATE or FINAL_TABLE_ELIGIBLE confirmation runs whose frozen method card declares another horizon;
- exact historical reproductions that require preserving the original training budget.

A longer horizon may be predeclared when there is concrete evidence it is necessary. It must not be chosen post hoc because a result was disappointing.

## 5. Matched-pair integrity

Horizon interpretation is pairwise. If one arm in a decisive matched comparison is censored, the scientific comparison is censored.

Do not compare a 15-epoch selected model with a 30-epoch selected control as if the horizons were matched. Extend the exact affected pair together unless a historical anchor is used purely as an immutable reference and its selected checkpoint is reproduced exactly within the shorter horizon.

## 6. Research objective

The purpose of this amendment is to increase:

~~~text
decisive architecture hypotheses tested per unit wall-clock and GPU time
~~~

without replacing real Train/Dev experiments with toy, partial, or prematurely stopped runs.

The normal early loop is therefore:

~~~text
15 complete epochs
-> interpret if every matched arm selects <= Epoch 10
-> otherwise exact pair to 30
-> if still censored at 26–30, exact pair to 60
~~~
