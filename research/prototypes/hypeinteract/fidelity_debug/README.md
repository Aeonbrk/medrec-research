# HypeMed fidelity debug

This debug run checks whether the earlier `0.431689` HypeMed adapter result was
an architecture result or an under-specified adapter result.  The semantic
authority is the official HypeMed checkout at revision
`33339ea973fd1d72908b3f6ae34b578d98fb4ba3` ([source](https://github.com/xansar/HypeMed),
[paper](https://doi.org/10.1145/3803851)).  The component-level comparison is
in [`semantic_diff.md`](semantic_diff.md).

## Protocol

- Seed `20260914`; MIMIC-III setting (`mimic=3`), `dim=64`, four heads, two
  layers, dropout `0.3`, `top_n=10`, `win_sz=3`, batch size `16`.
- Official TriCL pretraining for 3 epochs, followed by 75 recommendation
  epochs with Adam (`lr=1e-3`, weight decay `1e-5`) and
  `CosineAnnealingWarmRestarts(T_0=25, T_mult=2)`.
- Canonical Train: 4,233 patients / 10,489 visits.  Gate01-Dev: 1,004
  patients / 2,130 visits.  The memory is Train-only for both queries; no
  project Audit/test resource was read.
- Parameter count: 2,450,187.  Official retrieval K was 10.  Same-patient
  retrieval was not masked in the official-semantics run; the matched control
  excludes the exact Train query visit only.
- The local PyTorch 1.9 environment required import/runtime shims and five
  compatibility edits (sparse matmul, unbatched attention, and CUDA FAISS
  handling).  They do not change the HypeMed architecture or objectives.

The official-source sanity check passed: the pinned source imported, 3-epoch
pretraining completed, the decoder CUDA forward/backward smoke was finite, and
the 75-epoch canonical run completed.  The literal upstream eval/test split
was intentionally not materialized because it would cross this project's
held-out-resource boundary; this is therefore an execution-health check, not
an exact paper-number reproduction.

## Retrieval audit

| Query split | Exact-self top-1 | Exact-self in top-10 | Same-patient in top-10 |
| --- | ---: | ---: | ---: |
| Train, official semantics (10,489) | 0.366098 | 0.809229 | 0.809324 |
| Gate01-Dev, official semantics (2,130) | — | — | 0.000000 |
| Train, exact-self excluded (10,489) | 0.000000 | 0.000000 | 0.021832 |
| Gate01-Dev, exact-self excluded (2,130) | — | — | 0.000000 |

The Dev same-patient rate is zero as required by the patient-disjoint split.
Dev exact-self columns are not interpreted: the evaluation dataset enumerates
its visits locally, while the memory IDs are Train-global.  The required Dev
diagnostic is the same-patient Train-memory rate.
The exact-self hit rate is high for Train under official semantics, so the
matched control was run without changing the model, optimizer, or epoch count.

## Canonical faithful HypeMed results

Metrics are visit-macro and use the project's 131-medication DDI resource.
MoleRec and GraphRefine-SameK are the existing comparison references.

| Surface | Jaccard | F1 | PRAUC | DDI | AvgMed |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec (reference) | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK (reference) | 0.533650 | 0.687394 | 0.784240 | 0.073328 | — |
| HypeMed-OfficialSemantics, epoch 75 | 0.514256 | 0.670078 | 0.755615 | 0.059559 | 23.5770 |
| HypeMed-LeakageSafe, epoch 75 | 0.512112 | 0.668091 | 0.753822 | 0.059404 | 23.6549 |

Official-semantics learning curve:

| Epoch | Jaccard | F1 | PRAUC | DDI | AvgMed |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 0.436344 | 0.599560 | 0.721632 | 0.060839 | 19.0009 |
| 20 | 0.474977 | 0.636174 | 0.747337 | 0.065218 | 19.2493 |
| 40 | 0.509955 | 0.666231 | 0.757838 | 0.060988 | 23.6498 |
| 60 (best) | 0.514430 | 0.669976 | 0.757484 | 0.059726 | 24.2207 |
| 75 | 0.514256 | 0.670078 | 0.755615 | 0.059559 | 23.5770 |

The exact-self-excluded control is only 0.002144 Jaccard below the official
semantics run (PRAUC −0.001793; DDI −0.000155), so exact-self retrieval does
not explain the whole result.

## Interpretation and terminal decision

The faithful source materially exceeds the previous simplified adapter
(`0.514256` versus `0.431689`, +0.082567 Jaccard), so that adapter result is
invalidated as evidence about canonical HypeMed.  Nevertheless, the faithful
model remains below the Stage-A health threshold of approximately `0.540` and
does not beat the existing MoleRec/GraphRefine accuracy surface.  No
HypeInteract run was performed.

**Official-source sanity:** `OFFICIAL_HYPEMED_REPRO_HEALTHY` (execution health
only; upstream held-out eval/test intentionally omitted).

**Final debug verdict:** `HYPEMED_CANONICAL_WEAK`.

The prior adapter should additionally be recorded as
`HYPEMED_PREVIOUS_ADAPTER_INVALIDATED`; this debug does not create Idea 009 or
alter shared project state.
