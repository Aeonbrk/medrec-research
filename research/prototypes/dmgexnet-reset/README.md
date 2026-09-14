# DMGExNet reset: source and information-budget audit

This bounded prototype stops before canonical training. It is not a model
rewrite and it does not issue a DMGExNet performance verdict.

## Authority and published context

- Paper: [DMGExNet, DOI 10.1002/eng2.70899](https://doi.org/10.1002/eng2.70899)
- Official source: [pc-star123/DMGExNet](https://github.com/pc-star123/DMGExNet)
- Audited source revision: `66b32302947e248d9caeb15ee1bfdb13b50cbdce`
- The paper reports MIMIC-III Jaccard `0.6142 ± 0.0012`, PRAUC
  `0.8296 ± 0.0018`, F1 `0.7442 ± 0.0024`, DDI `0.0443 ± 0.0009`, and
  average medications `19.3911 ± 0.7126`. Those are literature context only;
  they are not this repository's result.

## Decisive auxiliary-resource audit

The official [`data/matrix.py`](https://github.com/pc-star123/DMGExNet/blob/66b32302947e248d9caeb15ee1bfdb13b50cbdce/data/matrix.py)
reads `records.pkl`, allocates one row per
patient, loops over every admission in that patient, and sets diagnosis,
procedure, and medication columns to one. It writes `diag_new.pkl`,
`pro_new.pkl`, and `med131_new.pkl`. The official main program then splits
these patient rows and passes them into the explanation path by patient index.

| Resource | Source data | Construction | Medication labels? | Train-only required? | Available at inference? |
| --- | --- | --- | ---: | ---: | ---: |
| `diag_new.pkl` | full `records.pkl` (6,350 patients) | whole-patient union over all admissions, 1,958 columns | no | yes | no |
| `pro_new.pkl` | full `records.pkl` (6,350 patients) | whole-patient union over all admissions, 1,430 columns | no | yes | no |
| `med131_new.pkl` | full `records.pkl` (6,350 patients) | whole-patient union over all admissions, 131 columns | **yes** | yes | **no** |

`med131_new.pkl` is therefore target-derived, and all three resources include
future visits relative to an individual prediction. They are not canonical
point-in-time inputs. Replacing them with current-visit or Train-only vectors
would change the official aspect mechanism, so this lane does not synthesize
approximations.

## Official execution sanity findings

The pinned source was inspected before any canonical run. Its default entry
point does not establish fresh training: `--Test` is a `store_true` argument
with `default=True` and the default path loads a published checkpoint. The
same commit also has a missing `seed.py`, calls `CrossBiAttention` with two
arguments although its method requires three, feeds 64-wide embeddings to a
128-wide Transformer by default, and mutates `adm[2]` in place. These are
execution defects, not evidence that the architecture is weak. They are
recorded by [`audit.py`](audit.py) and in `audit-report.json`.

The intended official training configuration was recorded without starting a
run: 70 epochs, learning rate `5e-4`, embedding dimension 128, four attention
heads, `target_ddi=0.05`, `kp=0.05`, and `a=0.9`. Because the information-budget
gate failed, there is no learning curve, parameter count, wall-clock, GPU
memory, or canonical metric row for DMGExNet.

The source objective was not simplified: it combines `0.95 * BCE + 0.05 *`
multilabel-margin loss, switches to the conditional DDI loss when the current
predicted DDI rate exceeds the target, and mixes that branch with the
similarity/explanation loss using `a=0.9`. Its inference threshold is sigmoid
`>= 0.5`; neither training nor decoding was executed here.

## Fidelity checks

The audit records source-level stream separation, longitudinal ordering, and
bidirectional cross-stream attention as inspected but not executed. Historical
medication alignment is explicitly marked invalid because the pinned forward
path mutates/consumes target-derived global rows. Drug-index, Train-only graph,
Dev-exclusion, CUDA finite-forward/backward, and deterministic-seed checks were
not executed after the information-budget gate; the pinned source also lacks
its imported `seed.py` module. These statuses are deliberate and prevent an
unrun or inadmissible path from being presented as a faithful result.

## Semantic diff

| Official DMGExNet component | Executed implementation | Exact / Changed | Reason |
| --- | --- | --- | --- |
| Longitudinal diagnosis/procedure Transformer streams | Not executed | Exact source inspected; no model run | Auxiliary-resource information gate failed first |
| Bidirectional diagnosis/procedure cross-attention | Not executed | Exact source inspected; source call is not runnable | Pinned arity defect; no silent repair |
| EHR + DDI GCN and molecular/bipartite path | Not executed | Exact resource contract recorded; no permutation asserted | Canonical run is forbidden after the information gate |
| Aspect/explanation mapping | Audit only | Changed boundary would be required | Material information leak; official aspect rows contain future/target information |
| Recommendation head and piecewise objective | Not executed | Exact source inspected; no simplification made | No scientific result is admissible |

## Results and terminal decision

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec (existing canonical reference) | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK (existing canonical reference) | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 |
| HypeMed (existing canonical reference) | 0.431689 | 0.594725 | 0.721035 | 0.072674 | 13.463850 |
| DMGExNet | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |
| DMGExNet-MoleRecK | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** | **NOT RUN** |

Implementation fidelity: `DMGEXNET_ADAPTATION_FIDELITY_UNRESOLVED`.

Canonical performance: no scientific STOP/HEALTHY verdict is issued because
fidelity is unresolved. Terminal decision: **`DMGEXNET_INFORMATION_BUDGET_MISMATCH`**.
No threshold, layer, learning-rate, epoch, or cardinality rescue was run.

`audit-report.json` is machine-readable and contains no patient rows,
predictions, checkpoints, or held-out resources. No Audit/test resource was
accessed. The audit code is the complete adaptation artifact; no approximate
DMGExNet implementation was created.
