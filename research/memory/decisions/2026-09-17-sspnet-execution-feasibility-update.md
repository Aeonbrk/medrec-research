# SSPNet execution-feasibility update

Date: 2026-09-17

Scope: bounded non-evidence source probe after the closest-work audit. This
record does not certify SSPNet fidelity and does not admit a paper-comparison
row.

## Source and environment

- Official checkout: `/root/zhb/sspnet-source-4a2695ec`.
- Source revision: `4a2695ec67e0dc30cd3fa8e67a4f1536f0bfc90d`.
- The checkout's `data/MIMIC_3` and `data/MIMIC_4` directories are empty; the
  frozen project snapshot was used only as a bounded execution fixture.
- The pinned execution environment lacks `matplotlib`, which is imported by
  the model only for the visualization helper.

## Observed source defects

The checked source has the following concrete execution blockers:

1. `src/modules/MoleRec.py:137-140` declares an unused `ddi_mask_H` argument,
   while `src/training.py:28-30` and `:125` call the model with only three
   positional arguments.
2. `src/training.py:161` passes an undeclared global `drug_data` into
   `eval_one_epoch`.
3. `src/modules/MoleRec.py:187-188`, `:260-261`, and `:272-274` invoke the
   t-SNE visualization helper on every multi-visit forward and
   `:376` writes to `/home/wjw/image/output_plot.pdf`.
4. `src/util.py:153-162` tests `union == 0` instead of testing an empty set;
   when both target and prediction are empty, the source evaluator raises
   `ZeroDivisionError`.

## Bounded probe

- With only the plotting helper suppressed at the adapter boundary, a
  multi-visit forward produced finite logits of shape `[1,131]` on the frozen
  vocabulary `(1958,1430,131)`; parameter count was `784323`.
- A one-patient, one-epoch mechanical training/evaluation probe reached the
  source optimizer update and evaluator, then failed at the empty-set Jaccard
  defect above. It produced no terminal evidence artifact and no Test access.
- Probe values are non-evidence diagnostics and are excluded from all result
  tables.

## Follow-up edge-case probe

The frozen core evaluator defines both-empty set metrics as `1.0` and empty
target average precision as `0.0`. Injecting exactly those rules into the
bounded adapter, while suppressing only visualization and threading the
declared DDI adjacency through the unused source argument, allowed a
one-patient/one-epoch source optimizer and evaluation smoke to finish with
finite loss and metrics. This follow-up also produced no terminal evidence
artifact and no Test access.

The successful smoke proves only that the identified call-site and metric
edge-case defects can be isolated mechanically. It does not establish a
frozen-profile adapter, source-metric equivalence, checkpoint/operating-point
selection, or a credible full-budget baseline.

## Decision

`SSPNET_EXECUTION_UNRESOLVED` remains the correct status. The plotting,
argument, and empty-set issues are mechanically isolable, but the resulting
adapter still needs an independent source-fidelity review, explicit frozen
profile/evaluator binding, and a bounded cost decision. No formal SSPNet run,
structured prototype, or SSPNet-inspired substitute is authorized from these
probes.

Required before reconsideration: an independently reviewed adapter that
isolates visualization, threads the declared DDI inputs, removes the undefined
global, and explicitly maps source metric edge cases to the frozen contract;
then rerun only a deterministic correctness probe.
