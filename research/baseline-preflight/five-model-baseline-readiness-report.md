# Five-Model Baseline Readiness Report

## Overall conclusion

- `engineering_ready = false`
- `reproduction_complete = false`
- `research_baseline_ready = false`

The suite has reusable, identity-pinned training evidence and a locally corrected continuation controller, but it does not have a complete Reproduction Mode audit or any Unified Research Protocol v1.1 Comparison Qualification. Paper fidelity and Comparison qualification remain separate axes; neither may be inferred from the other.

## Per-model readiness

| Model | Pinned source / scientific identity | Reproduction Mode | Comparison Mode | Mechanism experiments | Sole current blocking gate |
| --- | --- | --- | --- | --- | --- |
| RETAIN | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, profile `retain` | `formal_incomplete`: finalized `failed` / `test_failed`; no test metrics | Not qualified; registry state `registered` | No | `phase_a_legal_five_pair_audit` |
| LEAP | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, profile `leap-safedrug` | `formal_incomplete`: not claimed after RETAIN terminal failure | Not qualified; registry state `registered` | No | `phase_a_legal_five_pair_audit` |
| GAMENet | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, profile `gamenet` | `formal_incomplete`: not claimed after RETAIN terminal failure | Not qualified; registry state `registered` | No | `phase_a_legal_five_pair_audit` |
| SafeDrug | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, validation-selected `5e-4` lane | `formal_incomplete`: selected lane not claimed; `1e-5` and `1e-4` remain `not_tested_by_design` | Not qualified; registry state `registered` | No | `phase_a_legal_five_pair_audit` |
| MoleRec | MoleRec `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, profile `molerec-embedding` | `formal_incomplete`: not claimed after RETAIN terminal failure | Not qualified; registry state `registered` | No | `phase_a_legal_five_pair_audit` |

The named gate is the deterministic first blocker shared by all five models: the readiness plan requires a legal five-pair Phase A audit with execution integrity and artifact completeness before Phase B may start. It is not a claim that all later Comparison gates would pass.

## Comparison Mode assessment

The repository currently contains identity and validation skeletons for Comparison Mode, but no five-model qualification evidence:

- all five target baselines are still `registered` and have no current-scope `ComparisonQualification`;
- no shared five-model v1.1 scope/protocol packet or five method-profile packet has been admitted;
- the existing process adapter validates target-free requests and visit coverage, but has no admitted five-model full-vocabulary score-surface path;
- the existing evaluator does not yet provide the required target-free core-owned join, DDI rate, PRAUC, and declared ten-round uncertainty path for qualification.

These are known future engineering units, not evidence-based per-model failures, because Phase B admission was never reached. They must be implemented and qualified under one exact Comparison Scope after a legal Phase A terminal audit exists.

## Interpretation

`completed_mismatch` would remain a valid scientific outcome and would not mechanically block Comparison qualification. It is not the outcome here: incomplete execution prevents both paper-point interpretation and Phase B admission.

No model is ready for downstream mechanism experiments under the common Comparison Scope. The suite must not be labeled `research_baseline_ready` until all five current-scope qualification packets exist and agree on the shared protocol, manifest, cohort, eligible visits, vocabulary, features, DDI asset, lineage, and Adaptation Budget identities.
