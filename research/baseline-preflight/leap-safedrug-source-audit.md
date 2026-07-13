# LEAP-SafeDrug Source Audit

**Audit date:** 2026-07-13  
**Scope:** public, read-only provenance and execution preflight for the `leap-safedrug` registry candidate. This is not a run record, a license grant, or a qualification decision.

## Decision

`leap-safedrug` remains blocked. There is adequate evidence to identify a SafeDrug paper-reproduction source revision, but not to execute or qualify the candidate:

- The SafeDrug repository has no license file at either the author-designated paper-reproduction revision or current `main`; public availability is not permission to copy, install, or run the code.
- The paper-reproduction revision has no complete executable LEAP environment: its LEAP entry point imports a module that imports unpinned `dnc`, while its dependency list does not declare `dnc` or a lock file.
- The paper-reproduction LEAP command defaults to test mode and has no command-line switch to train. Its default LEAP checkpoint path is absent from the fixed source tree.
- No author statement found establishes that SafeDrug's `Leap.py` is equivalent to the original AutoPrescribe LEAP. The only direct equivalence statement found concerns GAMENet's LEAP implementation and is conditional on adding beam search; SafeDrug's LEAP decoder is greedy `topk(1)`.

Do not substitute the current SafeDrug branch, the GAMENet `dnc` candidate, an AutoPrescribe checkout, a source edit, or a hand-selected checkpoint to make this candidate appear ready.

## Fixed Sources

| Role | Immutable evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| AutoPrescribe historical source | [commit `a6188e9189df727320448a368f6e70036472ede4`](https://github.com/neozhangthe1/AutoPrescribe/tree/a6188e9189df727320448a368f6e70036472ede4) | The tree contains the Theano/Lasagne LEAP implementation and MIMIC configuration. | Its tree contains no license file, requirements file, or lock file. It cannot supply an execution license or a pinned environment. |
| GAMENet owner attestation | [GAMENet Issue #8 owner comment](https://github.com/sjy1203/GAMENet/issues/8#issuecomment-562928511) | The GAMENet owner says that adding beam search makes the *GAMENet repository's* LEAP implementation equal to AutoPrescribe's implementation. | This is not an assertion that SafeDrug's independently hosted `Leap.py` is equivalent, nor does it select beam-search parameters. |
| SafeDrug paper-reproduction source | [archived commit `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`](https://github.com/ycq091044/SafeDrug/tree/8deee38cfdb2a38882377ff95cce5922d6d9e8d6) | The SafeDrug owner's `reproduce IJCAI paper` commit fixes the source tree, including `src/Leap.py`. | Its complete file tree has no license or environment lock. Its published sample data and checkpoint do not authorize restricted-data use. |
| SafeDrug owner attestation | [SafeDrug Issue #23 owner comment](https://github.com/ycq091044/SafeDrug/issues/23#issuecomment-1570715548) | The owner explicitly identifies the `archived` branch as the exact paper-reproduction code after explaining that current code differs in its molecular-data pipeline. | It identifies the branch, not a LEAP equivalence claim, a license, an approved `dnc` implementation, or a checkpoint-selection protocol. |

The `archived` branch currently resolves to `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`; its commit message is `reproduce IJCAI paper`. Future branch movement must not replace this SHA.

## LEAP Provenance

The evidence supports a narrow lineage claim only:

1. AutoPrescribe's fixed source is an original Theano/Lasagne LEAP implementation: [its LEAP source](https://github.com/neozhangthe1/AutoPrescribe/blob/a6188e9189df727320448a368f6e70036472ede4/models/leap.py) imports `theano` and `lasagne`; [its MIMIC configuration](https://github.com/neozhangthe1/AutoPrescribe/blob/a6188e9189df727320448a368f6e70036472ede4/exp/coverage/config_mimic.py) fixes `model_seed = 13` and the associated training settings.
2. GAMENet's owner says the GAMENet LEAP code becomes equal to AutoPrescribe only after beam search is added. This is direct author evidence that greedy GAMENet LEAP alone is insufficient for that equivalence claim.
3. SafeDrug's archived source calls its baseline `Leap`, but [the decoder](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/src/models.py) emits each next token with `topk(1)`. That is greedy decoding, not the beam-search condition in the GAMENet owner statement.

Therefore, SafeDrug's LEAP may be recorded as a separately implemented, source-hosted LEAP-named baseline, but it cannot be labeled an exact AutoPrescribe or GAMENet-equivalent LEAP reproduction from the evidence above. Adding beam search would change the SafeDrug Baseline Core and requires independent source, license, and semantic approval.

## SafeDrug Execution Evidence

The author-designated SafeDrug revision is the only appropriate starting point for a SafeDrug paper reproduction. Its [README](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/README.md) specifies Python 3.7, SciPy 1.5.2, pandas 1.1.3, PyTorch 1.4.0, NumPy 1.19.2, `dill`, and RDKit, and names MIMIC-III preprocessing plus a separate DDI download. It does not provide a requirements file, Conda YAML, lock file, or `dnc` version.

This omission is execution-significant even for `Leap.py`: [the entry point](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/src/Leap.py) imports `Leap` from `models`, and [that module](https://github.com/ycq091044/SafeDrug/blob/8deee38cfdb2a38882377ff95cce5922d6d9e8d6/src/models.py) imports `DNC` at module load. No evidence connects this source to the `dnc` implementation candidate identified for GAMENet, so that candidate cannot be reused by inference.

The archived LEAP entry point creates `argparse` option `--Test` with `action='store_true'` and `default=True`. Its training code is reached only when `args.Test` is false, but the published CLI exposes no false-setting flag. The same entry point defaults to `saved/Leap/Epoch_49_JA_0.4603_DDI_0.07427.model`; the fixed tree contains no such LEAP checkpoint, although it contains a SafeDrug-model checkpoint. Patching the default, importing the module to mutate global arguments, or supplying an unproven external checkpoint would not be source-native reproduction.

For completeness, the source's unmodified training path has these protocol-relevant properties:

- It fixes only `torch.manual_seed(1203)`; NumPy and Python `random` are not seeded before the bootstrap test loop.
- It uses the first two thirds of the loaded record sequence for training, half of the remainder as `data_test`, and the final quarter as `data_eval`. The evaluator runs on `data_eval` after each epoch; patient ordering and non-overlap are not established by this audit.
- It saves every epoch with evaluation metrics in the filename, prints a Jaccard-based `best_epoch`, but provides no automatic mapping from that printed epoch to the `--resume_path` used by test mode. A manual path is therefore a selection decision, not a reproducible source rule.

The current [`main` revision `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`](https://github.com/ycq091044/SafeDrug/tree/88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a) changes data processing and permits LEAP training by changing the default test setting. The owner says those changes alter the pipeline and paper results in [Issue #23](https://github.com/ycq091044/SafeDrug/issues/23#issuecomment-1523665061), so `main` cannot silently replace the archived source for paper reproduction. It is also unlicensed and retains an unpinned `dnc` installation instruction.

## Required Evidence To Reopen

All conditions below are required before source download, environment creation, or execution under the controlled-baseline policy:

1. An explicit license grant from the SafeDrug copyright holder covering the proposed source use. AutoPrescribe needs a separate license review if it is proposed as a source rather than a historical reference.
2. A fixed, author-supported `dnc` implementation and revision for the SafeDrug archived source, or a source revision that eliminates the unconditional import with documented equivalent behavior.
3. Author-supported, source-compatible training invocation for archived `Leap.py`, including a checkpoint-selection rule independent of held-out test evaluation and an available or reproducibly trainable LEAP checkpoint.
4. An explicit scientific declaration of the intended target: SafeDrug's greedy LEAP derivative, or an original-LEAP equivalence claim. The latter additionally requires the beam-search implementation, its parameters, and provenance evidence; Issue #8 alone does not supply them.
5. A restricted preflight that independently establishes MIMIC-III input mapping, patient-level split semantics, and the exact non-public artifacts required by the selected source. No replacement with MIMIC-IV, RxNorm, or an alternate molecular mapping is implicit in this record.

Until then, the valid registry status is `registered`; neither `smoke_ready` nor `comparison_ready` is supported.
