# MedState Dynamics — Persistent Medication Identity States

MedState is one throwaway pre-Idea architecture screen. It is not Idea 009,
does not create or modify a formal CCFA Gate, and makes no novelty or
paper-readiness claim. The candidate hypothesis is that carrying a separate
latent trajectory for each of the 131 medication identities adds information
that a matched stateless reader cannot absorb.

## Boundary

- The only scientific surfaces are the existing canonical Train and
  Gate01-Dev split, with seed `20260914`.
- Current visits provide diagnosis and procedure code sets only.
- Medication history is causal: previous-visit membership, historical
  prescription frequency, and recency are materialized before the current
  row. The current target is used only after prediction and loss computation.
- The relation prior is the canonical Train-derived EHR co-prescription graph
  combined with the DDI graph. MoleRec is a comparison surface, not a required
  input or backbone.
- Heldout, test, Audit, G3, G4, historical-test, future-visit, oracle-cardinality,
  and Dev-threshold resources are not read.

## Surfaces

All three learned surfaces use the same 64-dimensional identity/state space,
small diagnosis/procedure encoder, medication-specific current cross-attention,
three explicit causal history features, one BCE objective, AdamW controls, and
the frozen per-medication logit threshold `0.0`.

- `StatelessRelational`: initialize every visit from the shared medication
  identity state, then use one patient-conditioned EHR/DDI relation layer.
- `PersistentIndependent`: carry the medication states and assimilate the
  observed prescription after each prediction; relation messages are zero.
- `PersistentRelational`: carry and assimilate the states and use the same
  single relation layer.

The loop order is fixed: current evidence → pre-prescription state → logits →
current BCE → post-prescription assimilation for the next visit. The runner
detaches after each visit, equally for all variants.

## Execution

Run the targeted synthetic contracts first in the approved `medrec-molerec-table1`
environment:

```bash
PYTHONPATH=research/prototypes/medstate \
  python research/prototypes/medstate/smoke.py
```

The real-data command is intentionally explicit and should be launched on
319 only after the remote execution preflight:

```bash
CUDA_VISIBLE_DEVICES=0 \
  python research/prototypes/medstate/run_medstate.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913 \
  --source-revision <clean-commit> \
  --output /root/zhb/medrec-data/prototypes/medstate/screen.json
```

The aggregate JSON is the only result copied back to the Mac harness. It
contains the four required metric rows, mechanism deltas, medication-count
deltas, and the bounded state-dynamics diagnostics.

## Decision

The primary comparison is `best(PersistentIndependent, PersistentRelational)`
against `StatelessRelational`. A mechanism gain at or below `0.002` Jaccard is
an immediate `KILL_PERSISTENT_MED_STATE`; a weak gain below `0.004` also does
not survive. A surviving mechanism must additionally clear the requested
GlobalStrong accuracy/safety bar. No tuning or rescue is permitted.

### Result record

The single configured run and its terminal recommendation will be recorded
here after execution. No Idea 009 or formal Gate will be created.
