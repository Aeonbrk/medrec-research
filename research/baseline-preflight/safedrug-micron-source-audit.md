# SafeDrug and MICRON source preflight audit

## Scope and outcome

This is a read-only audit of the two official GitHub repositories on 2026-07-13. It uses only commit-pinned source files, repository metadata, and comments written by the repository owner. It does not clone source, build an environment, access MIMIC, inspect bundled data, or run a model. Links to source files contain the exact commit SHA; issue-comment links are permanent comment permalinks, but are not source revisions and may be edited by their author.

| Baseline | Fixed source candidate | Reproduction lane supported by current evidence | Blocking evidence gap |
| --- | --- | --- | --- |
| SafeDrug | [`archived` `8deee38`](https://github.com/ycq091044/SafeDrug/tree/8deee38cfdb2a38882377ff95cce5922d6d9e8d6) | Evaluate the supplied fixed checkpoint under its source-defined bootstrap procedure, after restricted input and environment preflight. | No lockfile and no exposed way to enter the archived training path. A new training run cannot be called source-faithful without further maintainer evidence. |
| MICRON | [`main` `8a8676c`](https://github.com/ycq091044/MICRON/tree/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35) | Evaluate the supplied fixed checkpoint using validation-derived thresholds and the held-out test partition, after restricted input and environment preflight. | No fully pinned official environment. From-scratch checkpoint selection needs an explicit pre-registered rule. |

Neither finding advances registry readiness or supports a Comparison Mode claim. Current classic-six V2 selection records the absence of a recognized license but does not use it as an execution blocker.

## SafeDrug

### Source and branch choice

The repository exposes no GitHub-recognized license, and the fixed archived tree has no `LICENSE`, environment file, lockfile, or requirements file. The absence is recorded rather than used as a current V2 execution blocker. The only archived-branch history is the initial code plus [`8deee38`, "reproduce IJCAI paper"](https://github.com/ycq091044/SafeDrug/commit/8deee38cfdb2a38882377ff95cce5922d6d9e8d6). The owner states that the exact reproduction code is in `archived` in [issue #23](https://github.com/ycq091044/SafeDrug/issues/23#issuecomment-1570715548). That is the only viable paper-reproduction candidate.

The later [`main` `88ce5c3`](https://github.com/ycq091044/SafeDrug/tree/88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a) is not a silent substitute. Its [README](https://github.com/ycq091044/SafeDrug/blob/88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a/README.md) says that its DrugBank-based SMILES mapping and processing produce different data statistics, and directs paper reproduction to `archived`. The owner independently attributed the result difference to the changed molecule mapping in [issue #23](https://github.com/ycq091044/SafeDrug/issues/23#issuecomment-1523665061).

### Environment and inputs

The archived [README](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/README.md) lists only reference versions: Python 3.7, SciPy 1.5.2, pandas 1.1.3, PyTorch 1.4.0, NumPy 1.19.2, plus unpinned `dill` and RDKit. It does not specify CUDA, a package resolver result, hashes, or transitive dependencies. The newer main README lists a different reference stack, but it belongs to the changed processing branch and cannot complete an archived reproduction lock.

The archived preprocessing script requires MIMIC-III v1.4 prescription, diagnosis, and procedure tables plus an external DDI CSV; it creates the vocabulary, patient records, and DDI matrix. It filters the 300 most common medication codes and 2,000 most common diagnosis codes, while the procedure-frequency filter is commented out in [processing.py](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/data/processing.py). The external DDI file has no commit-pinned checksum. A restricted preflight must therefore verify the exact source-required categories and record a restricted checksum manifest before any run.

The same script orders rows by `SUBJECT_ID` and `HADM_ID`, not by an admission-time column. The owner says that this ordering preserves visit order in [issue #5](https://github.com/ycq091044/SafeDrug/issues/5#issuecomment-974744334), but the follow-up counterexample received no owner response. Chronological equivalence is not established by the available evidence. Preserve this source behavior for Reproduction Mode and separately test the resulting patient-level sequence and split non-overlap; do not replace it with a new time-ordering rule.

### Training, split, and selection semantics

[`SafeDrug.py`](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/src/SafeDrug.py) fixes Torch seed `1203` and NumPy seed `2048`; it exposes neither seed as an argument. It treats each record as a patient sequence, uses the first two thirds as training, the next half of the remainder as test, and the final half as evaluation. The owner confirms that SafeDrug predicts each visit's drug set from diagnosis and procedure features through that visit in [issue #25](https://github.com/ycq091044/SafeDrug/issues/25#issuecomment-1563479915). Real-data preflight must still confirm that reconstructed records are patient-disjoint across these list slices.

The archived CLI declares `--Test` with `store_true` and `default=True`; there is no negative flag. Thus both `python SafeDrug.py` and `python SafeDrug.py --Test` enter checkpoint evaluation, loading the fixed `Epoch_49_TARGET_0.06_JA_0.5183_DDI_0.05854.model` path. This lane performs ten 80%-with-replacement samples of `data_test` and reports their mean and standard deviation. It is a source-defined checkpoint characterization, not a from-scratch training run.

The unreachable training branch evaluates `data_eval` after every epoch, saves every epoch checkpoint, and prints a `best_epoch` when Jaccard improves. It does not load that epoch or specify how to choose a saved checkpoint. Altering `default=True`, adding a seed flag, or manually selecting an epoch would alter Baseline Core behavior. Reopen an archived training lane only with maintainer-authored evidence of the intended training invocation and checkpoint rule, or with an immutable official training revision that exposes them.

## MICRON

### Source and historical environment evidence

[`main` `8a8676c`](https://github.com/ycq091044/MICRON/tree/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35) is the repository head and its only branch. The tree has no `LICENSE`, and GitHub reports no recognized license. It does contain [requirements.txt](https://github.com/ycq091044/MICRON/blob/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35/requirements.txt), but it names only unpinned `scikit-learn`, `torch`, `dill`, `pandas`, and `numpy`. The current [README](https://github.com/ycq091044/MICRON/blob/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35/README.md) misspells that filename as `requirments.txt` and gives a PyTorch 1.8.0 CUDA 11.1 command only for RTX 3090.

An earlier official [README at `b3034e9`](https://github.com/ycq091044/MICRON/blob/b3034e926639d27624857c2bb7debf423965e3d5/README.md) lists Python 3.7, SciPy 1.1.0, pandas 0.25.3, PyTorch 1.4.0, NumPy 1.16.5, and `dill` as reference versions. This is useful historical evidence, not a lock for the final source: [`6b0cbc`](https://github.com/ycq091044/MICRON/commit/6b0cbcbe6af72f9e469bc331021e3ac7c27dd1b8) subsequently changed `MICRON.py` data paths and added explicit CUDA selection. No owner-authored issue resolves the version choice; the historical stack and the final-source requirement file remain competing candidates rather than merged assumptions.

### Independent environment reproduction evidence

[`yuheng222/CS598-DL4H-MICRON@201df22cd61902c337f3ba91f705246645b67936`](https://github.com/yuheng222/CS598-DL4H-MICRON/tree/201df22cd61902c337f3ba91f705246645b67936) describes itself as a University of Illinois CS598 reproducibility-study project. It says that it refactored and modified code referenced from the official MICRON repository. GitHub search found no MICRON-author comment or official-repository reference endorsing it, so it is not an official source or a Baseline Core substitute.

Its README reports a tested environment of Ubuntu 20.04.4, Python 3.8.10, CUDA 11.6, PyTorch 1.10.1, `dill==0.3.4`, `numpy==1.17.4`, `pandas==0.25.3`, and `scikit-learn==0.22.2.post1`. Its `config.ini` exposes seed `1203`, a train/test mode, and checkpoint paths. Treat that as an independent, fixed compatibility candidate alongside the official README's PyTorch `1.8.0+cu111` command. Do not combine their versions or replace the official MICRON source with its refactored scripts.

### Data and preprocessing semantics

The final [README](https://github.com/ycq091044/MICRON/blob/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35/README.md) requires MIMIC-III v1.4 prescription, diagnosis, and procedure tables, GAMENet-derived mapping inputs, and an externally downloaded DDI CSV. That DDI file is not commit-pinned or checksummed. The source [processing.py](https://github.com/ycq091044/MICRON/blob/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35/data/processing.py) groups visits into patient records after sorting by `SUBJECT_ID` and `HADM_ID`, retains patients with more than one visit, keeps the 300 most common medication codes and 2,000 diagnoses, and leaves its procedure-frequency filter commented out. Preserve those transformations exactly for Reproduction Mode; verify the restricted output's expected vocabulary and patient-level disjointness without publishing those artifacts.

### Training, split, threshold, and checkpoint semantics

[`MICRON.py`](https://github.com/ycq091044/MICRON/blob/8a8676c0e5a19bebf845e690ae2b1b3dd8d95d35/src/MICRON.py) fixes Torch and NumPy seeds to `1203`, then shuffles the patient-record list. It assigns 60% to training, 20% to test, and the remaining 20% to evaluation. It trains for 40 epochs with RMSProp, learning rate `2e-4`, weight decay `1e-5`, and embedding dimension `64`; all checkpoints are saved. Seeds and epoch count are not CLI controls.

The test path defaults to the bundled `Epoch_39_JA_0.5209_DDI_0.06952.model`. It first derives ROC-based upper and lower medication thresholds from `data_eval`, then evaluates `data_test`; it does not use test labels for threshold selection. For a supplied-checkpoint characterization, this is a complete source-defined selection sequence. For a new training run, the script merely prints `best_epoch` from evaluation Jaccard and does not load it. The fixed default checkpoint implies a final-epoch candidate, but the owner never states that it is the intended from-scratch selection rule. Pre-register either the literal final `Epoch_39` rule or a maintainer-provided alternative before a new run; do not choose a checkpoint after seeing test metrics.

The training path also initializes `sample_counter` to zero and leaves its increment commented out before a division by that counter. No maintainer issue explains whether this is intentional. A restricted, non-evidentiary source smoke must record whether the unmodified historical dependency candidate completes. Do not uncomment or otherwise repair the Baseline Core during a reproduction lane.

## Required closure before execution

Both repositories retain unresolved license status, but current classic-six V2 selection does not block execution on that fact. SafeDrug additionally needs an official training invocation and checkpoint-selection rule for any from-scratch claim. MICRON needs an explicit environment lock validated against one declared source candidate and a pre-registered choice between its source-default final epoch and a maintainer-provided selection rule. In both cases, keep external source, restricted data, manifests, environment locks, model files, logs, and predictions outside Git.
