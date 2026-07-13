# Classic-six baseline execution preflight

This index is a public, read-only execution preflight. It records what official source and maintainer evidence establish before an environment is built or a model sees restricted data. `registered` is the only supported registry status for every candidate.

An Issue comment can explain a repository's intent. It does not fill a missing license, dependency pin, training invocation, split proof, checkpoint rule, or data manifest.

The current project policy records each source's seed behavior but does not require deterministic execution, a user-configurable seed, or a multi-seed stability result before a source-native reproduction attempt.

## Status matrix

| Candidate | Fixed official source | License | Queue decision |
| --- | --- | --- | --- |
| GAMENet | `sjy1203/GAMENet@da695b4` | MIT | Faithful Reproduction Mode blocked; source-compatible characterization candidate only. |
| SafeDrug | `ycq091044/SafeDrug@8deee38` (`archived`) | None found | Blocked. |
| MICRON | `ycq091044/MICRON@8a8676c` | None found | Blocked. |
| MoleRec | `yangnianzu0515/MoleRec@dd5afaf` | MIT | Candidate after restricted preflight and environment lock. |
| RETAIN | `mp2893/retain@9fd39c4` | BSD-3-Clause | Blocked for medication recommendation. |
| LEAP-SafeDrug | `ycq091044/SafeDrug@8deee38` | None found | Blocked. |

## GAMENet

- The source has no author-attributed environment or `dnc` revision. The API-matched PyTorch `dnc` candidate is not evidence that the authors used it.
- Native training fixes Torch and NumPy seed `1203`, trains on the first two thirds of the ordered patient records, validates on the final sixth, and evaluates a selected checkpoint on the middle sixth.
- The source prints a validation-Jaccard `best_epoch`; an external restricted wrapper may select only the uniquely matching source checkpoint before invoking test evaluation.
- The data distributed in the repository differs from the paper data. The owner points to `EDA.ipynb` and notes the first-24-hour distinction. No data variant may be silently selected.

See [the GAMENet Failure Record](../failures/gamenet-reproduction-2026-07-13.md).

## SafeDrug

- The owner designates `archived@8deee38` as the paper-reproduction branch. `main` changes molecular-data processing and must not replace it.
- The archived README gives reference versions, but no license, environment file, lockfile, CUDA version, `dnc` revision, or DDI-file checksum.
- `SafeDrug.py` fixes Torch `1203` and NumPy `2048`; its ordered sequence split is two thirds train, then test, then evaluation. The published `--Test` option defaults to true and exposes no false-setting, so source-native training cannot be invoked from its CLI.
- The source-defined lane is evaluation of its fixed checkpoint with bootstrap reporting. A new training lane has no official checkpoint-selection invocation.

See [the SafeDrug and MICRON audit](safedrug-micron-source-audit.md) and [the LEAP-SafeDrug audit](leap-safedrug-source-audit.md).

## MICRON

- The fixed official source has no license. Its requirements file leaves all packages unpinned; the final README and an older README describe incompatible historical environment candidates.
- The source fixes Torch and NumPy seed `1203`, shuffles patient records, and then uses a patient-level `60/20/20` train/test/evaluation split.
- Its bundled `Epoch_39` evaluation first fits two medication thresholds on evaluation data, then evaluates on test data. That sequence is source-defined for the bundled checkpoint only.
- A new training run needs license clearance, a validated environment lock, resolution of the unmodified `sample_counter` risk, and a pre-registered checkpoint rule. `best_epoch` output alone does not select a checkpoint.

See [the SafeDrug and MICRON audit](safedrug-micron-source-audit.md).

## MoleRec

- The fixed official source and its MIT license pass the source/license gate. `MoleRec.yml` declares a Linux Conda stack: Python 3.8.16, PyTorch 1.9.0, CUDA 10.2.89, PyG 2.0.3, matching extensions, and RDKit 2022.09.1.
- The source fixes Torch `1203` and NumPy `2048`; it exposes neither as a parameter and does not seed Python `random`. The owner says PyG prevents guaranteed reproducibility even when a seed is fixed. This is recorded, not an execution stop under the current policy.
- It retains SafeDrug-derived processing, splits ordered patient records into two thirds train, middle sixth test, and final sixth evaluation. Data and visit eligibility must follow the pinned processor exactly.
- Training records strict evaluation-Jaccard improvements in `best.txt` and saves every epoch. A wrapper may use only the final `best.txt` entry and a unique matching checkpoint before test evaluation.

See [the MoleRec and RETAIN audit](molerec-retain-source-audit.md).

## RETAIN

- The canonical author repository is licensed, but it is a Python 2.7/Theano 0.8 sequence-classification and mortality-prediction implementation, not a medication-combination model.
- It has no complete environment lock or executable reproducibility seed policy. Its validation-selected checkpoint behavior logs test AUC on each improvement and cannot define an untouched-test medication-combination lane.
- GAMENet's separate PyTorch `Retain` comparison code does target medication recommendation, but no author evidence establishes equivalence to canonical RETAIN. It has no CLI or automatic selection rule and imports GAMENet's unresolved `dnc` at module load.

See [the MoleRec and RETAIN audit](molerec-retain-source-audit.md).

## LEAP-SafeDrug

- This derivative must use the SafeDrug archived source and therefore fails the same license and unpinned-`dnc` gates.
- Its `Leap.py` defaults to test mode; the fixed default checkpoint is absent. The source's training path cannot be entered through the published CLI.
- The decoder uses greedy `topk(1)`. GAMENet's owner says only GAMENet LEAP with added beam search can equal AutoPrescribe; that does not prove SafeDrug LEAP equivalence or authorize a core change.

See [the LEAP-SafeDrug audit](leap-safedrug-source-audit.md).

## Required gate before any launch

Each candidate needs an execution-specific, immutable source and license; a source-compatible resolved environment and explicit lock; source-native training semantics; validation-only checkpoint selection; and a restricted proof of required inputs, patient-level split disjointness, vocabulary, and record ordering. Seed behavior remains documented but is not an execution gate. Failure at any other gate creates a public-safe Failure Record. It does not justify a substitute dependency, split, data representation, checkpoint, or implementation.

## Primary evidence

- [SafeDrug owner, Issue 23](https://github.com/ycq091044/SafeDrug/issues/23#issuecomment-1570715548): `archived` is the paper-reproduction code.
- [MoleRec owner, Issue 5](https://github.com/yangnianzu0515/MoleRec/issues/5#issuecomment-2314810135): PyG does not guarantee reproduction after fixing a seed.
- [GAMENet owner, Issue 7](https://github.com/sjy1203/GAMENet/issues/7#issuecomment-562848153): repository and paper training data differ.
- [GAMENet owner, Issue 8](https://github.com/sjy1203/GAMENet/issues/8#issuecomment-562928511): LEAP equivalence claim requires beam search in GAMENet's implementation.
