# MoleRec method card

`METHOD_ID`: `molerec`

`DISPLAY_NAME`: MoleRec (substructure-aware molecular representation)

`SCIENTIFIC_ROLE`: external molecular-knowledge baseline; current paper-profile
lane is development-only until it is rerun under the MIMIC-III canonical-131
contract.

## SOURCE

- Paper: [MoleRec: Combinatorial Drug Recommendation with Substructure-Aware
  Molecular Representation Learning](https://doi.org/10.1145/3543507.3583872),
  The Web Conference 2023, pp. 4075--4085.
- Official implementation: [yangnianzu0515/MoleRec](https://github.com/yangnianzu0515/MoleRec).
- Pinned source revision: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`.
- The repository is MIT licensed. The source pin and historical integration
  identity remain recorded in [`baselines/registry.toml`](../registry.toml).

## SCIENTIFIC_CORE

MoleRec embeds the diagnosis and procedure sets supplied in each visit and
uses two GRUs to form a longitudinal patient representation. The pinned
`MoleRecModel.forward` reads only those two channels; the medication list in a
source-shaped admission is used by the training loop as the current target and
is not consumed as a patient feature. In parallel, a global molecular GNN and a
substructure
  GNN substructure representation is combined with a learned
patient-conditioned substructure relation. An adjacency-aware attention
aggregator produces one representation per medication, followed by a scalar
medication score. The official forward path is implemented in
`src/modules/MoleRec.py` at the pinned revision.

- Objective: binary cross-entropy plus a multi-label margin term; when the
  current DDI rate exceeds the target, the official annealing rule mixes that
  term with the differentiable DDI loss. The exact loss and branch are in
  `src/training.py`.
- Optimizer: Adam with the source defaults (`lr=5e-4`, `coef=2.5`, dropout
  `0.7`, target DDI `0.06`, 50 epochs in the released entry point).
- Update semantics: the released training loop calls the model and performs
  `zero_grad → backward → step` for **each admission/visit**, inside each
  patient sequence. This visit-granularity optimizer update is part of the
  source identity; a batched replacement is not source-faithful.
- Decoder: independent sigmoid medication scores thresholded at `0.5` by the
  official evaluator. DDI is a training penalty and a reported pooled-pair
  metric; it is not an inference-time filter.
- Required molecular assets: `idx2SMILES.pkl`, `substructure_smiles.pkl`,
  `ddi_mask_H.pkl`, and the DDI matrix `ddi_A_final.pkl`. Required source data
  also include `records_final.pkl`, `voc_final.pkl`, `ehr_adj_final.pkl`, and
  `idx2drug.pkl` for the canonical snapshot validation.

## BENCHMARK_PROFILE

- Benchmark: MIMIC-III canonical-131, patient-disjoint Train/Dev profile
  [`research/benchmarks/mimiciii-medrec/profile.json`](../../research/benchmarks/mimiciii-medrec/profile.json).
- Vocabulary: the source `med_voc` order, 131 ATC4 coordinates; DDI is the
  aligned `131 × 131` binary symmetric matrix with 448 unordered pairs.
- Input budget: current diagnosis/procedure sets plus the source-shaped
  chronological prefix. The released forward path consumes diagnosis and
  procedure channels only; medication history is retained for source
  compatibility but is not consumed by this pinned model.
- History: source admission order is chronological; current medications are
  labels only and are never passed as forward features.
- Output: a medication set over all 131 coordinates, with continuous scores
  retained for the paper evaluator.
- Evidence role: `DEVELOPMENT`; no Test rows, targets, or Test-derived choice.

## ADAPTATION

- Mechanical: isolate the pinned source, bind the canonical snapshot assets,
  preserve the molecular/substructure assets, and translate outputs to the
  paper evaluator's full-vocabulary score schema.
- The current-profile entrypoint is
  [`baselines/molerec_profile.py`](../molerec_profile.py); it imports the pinned
  source model and keeps the released per-visit optimizer update path intact.
- Benchmark-specific: use the frozen canonical-131 Train/Dev patient split,
  complete-Dev patient-macro selection, and the declared global operating-point
  set. These choices do not claim to reproduce the paper's source split.
- Scientific changes: `NONE` for the source-faithful baseline. Any change to
  optimizer update granularity, molecular representation, loss, history
  semantics, or decoder is a named variant and cannot be called official
  MoleRec.

## SOURCE_SANITY

- Reference condition: the released Table 1 values in
  [`molerec-table1-reference.json`](../preflight/molerec-table1-reference.json)
  and the historical five-model reproduction report are sanity evidence only.
- The official README documents the same SafeDrug preprocessing lineage and
  warns that BRICS substructure order affects the supplied molecular assets.
  The source's `buildPrjSmiles` path and the supplied asset hashes must be
  checked before execution.
- Historical reproduction completed execution-integrity checks but was
  `completed_mismatch` on paper point/directional checks. It does not certify
  the current paper-profile row and must not drive tuning.
- Required admission checks: all legal inputs are present and used, molecular
  assets are consumed, visit-level updates are preserved, loss/optimizer and
  validation behavior are source-bound, logits are finite, predictions do not
  collapse, and medication cardinality is not pathological.
- Verdict: `FIDELITY_UNRESOLVED` until one current-profile run passes these
  checks. A badly degraded result permits at most one targeted fidelity
  investigation in this session; it is not permission for broad HPO or a
  threshold chase.

## DEVELOPMENT_ENTITLEMENT

- Candidate configuration is declared before screening: the released default
  MoleRec GNN path at its source training budget; no embedding-table variant,
  broad learning-rate, molecular-asset, or decoder sweep is authorized in this
  lane.
- Screening seeds: the current paper profile may use its declared development
  seeds only; historical seeds are not relabeled.
- Selection: choose checkpoint and global operating point jointly by Dev
  patient-macro Jaccard, with the profile's native-default and declaration-order
  tie-break. Do not inspect Test.
- If the source path fails to converge or is materially degraded, preserve the
  failure and stop after the single targeted fidelity check.

## VALIDATION_AND_DECODING

- Maximum budget: the frozen profile's complete training budget.
- Validation: evaluate the complete Dev surface at every declared checkpoint.
- Patience: none unless explicitly frozen in the profile.
- Operating points: the profile's global set `0.05, 0.10, …, 0.95`; source
  default `0.50` is retained as a reference, not silently substituted.
- Selection metric: Dev patient-macro Jaccard. Report F1, precision, recall,
  AP/PRAUC, predicted/target medication counts, and pooled unordered-pair DDI
  together.

## FINAL_CONFIRMATION

- Final configuration and seed count: not nominated; this card remains
  development-only.
- Failure handling: incomplete, non-converged, or fidelity-unresolved runs are
  quarantined and excluded from published-method ranking. No Test replay or
  mismatch-driven rescue is allowed.

## OUTPUTS

- Continuous output: one finite sigmoid score for each of the 131 medication
  coordinates in canonical vocabulary order; retain all coordinates for AP.
- Set decoder: include every coordinate whose score is at least the selected
  global operating point; no top-k, target-cardinality, or DDI post-filter.
- Parameter count and runtime: record from the executed source/environment;
  they are not inferred from the paper table.
- Inference path: source molecular GNN/substructure path plus patient GRU path;
  no solver or retrieval stage.

## STATUS

`DEVELOPMENT_ONLY`

## LIMITATIONS

- The current profile changes split, aggregation, validation, and operating
  point relative to the released source evaluator; numerical paper-table
  comparison is therefore sanity-only until semantics are aligned.
- The released evaluator uses visit-macro metrics and a fixed `0.5` threshold,
  whereas the current paper contract uses patient-macro selection and a frozen
  global operating-point set.
- Source fidelity of the required molecular assets and visit-granularity update
  path must be demonstrated by a current run; unresolved semantics are not
  filled by assumption.
