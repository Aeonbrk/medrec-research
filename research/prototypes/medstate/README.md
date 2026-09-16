# MedState dynamics: persistent medication identity states

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
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
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
not survive. A surviving mechanism must also clear the requested
GlobalStrong accuracy/safety bar. No tuning or rescue is permitted.

### Result record

- Run-code revision: `b2ec9ece7b42816ba60d8bf7daf65221fdfcbde0`
- Device: CUDA GPU 0, seed `20260914`
- Train: 4,233 patients / 10,489 visits
- Gate01-Dev: 1,004 patients / 2,130 visits

| Surface | Jaccard | F1 | PRAUC | Precision | Recall | DDI rate | Mean count | Count std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GlobalStrong (MoleRec) | 0.529174 | 0.683480 | 0.773576 | 0.661221 | 0.736513 | 0.072223 | 21.545070 | 5.762196 |
| StatelessRelational | 0.482689 | 0.640719 | 0.757210 | 0.749771 | 0.588991 | 0.080348 | 15.402347 | 5.873238 |
| PersistentIndependent | 0.459072 | 0.619027 | 0.746542 | 0.759243 | 0.549090 | 0.073197 | 14.048826 | 5.003141 |
| PersistentRelational | 0.475019 | 0.634257 | 0.752642 | 0.748652 | 0.575903 | 0.082448 | 15.047887 | 5.393489 |

PersistentRelational is the best persistent surface. Its Jaccard deltas are
`-0.007670` versus StatelessRelational and `-0.054155` versus GlobalStrong.
The PersistentIndependent DDI delta versus GlobalStrong is `+0.000974`; the
PersistentRelational delta is `+0.010225`. Mean medication counts are lower
than GlobalStrong by `6.142723` (StatelessRelational), `7.496244`
(PersistentIndependent), and `6.497183` (PersistentRelational), so the result
is not a prescription-size inflation effect. Relative to StatelessRelational,
the DDI deltas are `-0.007152` (PersistentIndependent) and `+0.002100`
(PersistentRelational). The permitted small-positive-delta diagnostic was not
run because the best persistent mechanism delta is already below the `0.002`
kill boundary.

### State dynamics

| Surface | Mean `||s_pre-s_prev||` | Std | Consecutive cosine mean | Cosine std | Active change | Never-prescribed change | Near-zero fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| StatelessRelational | 6.210677 | 1.572081 | 1.000000 | 0.000000 | 8.395403 | 5.995529 | 0.000000 |
| PersistentIndependent | 3.327794 | 1.656173 | 0.719075 | 0.123486 | 2.013642 | 3.457210 | 0.000000 |
| PersistentRelational | 4.308252 | 1.639575 | 0.669727 | 0.163641 | 2.966901 | 4.440346 | 0.000000 |

The PersistentRelational-versus-StatelessRelational per-visit Jaccard delta is
mean `-0.007670`, std `0.075093`, positive on `40.0%` of the 2,130 visits.
Persistent diagnostics contain 147,506 consecutive medication-state
transitions; no state changes were at or below the `1e-3` near-zero threshold.

The targeted contracts all passed before the data run: current-target leakage,
previous-visit causal effect, stateless reset, persistent identity carry,
medication-index permutation equivariance, and finite CUDA forward/backward.
The aggregate scope flags are all false for heldout, test, Audit, G3, and G4
resources. No Idea 009 or formal Gate was created, and no push was performed.

Terminal recommendation: `KILL_PERSISTENT_MED_STATE`
