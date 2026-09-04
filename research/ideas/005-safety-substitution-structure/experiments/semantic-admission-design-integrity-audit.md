<!-- markdownlint-disable MD013 -->

# Semantic Admission Design Integrity Audit

- **Idea**: `005-safety-substitution-structure`
- **Artifact**: `experiments/semantic-admission-protocol.md`
- **Mode**: design-level scientific integrity review
- **Verdict**: `DESIGN_INTEGRITY_PASS`
- **Execution**: not authorized by this audit

## 1. Question alignment

The protocol tests the exact unresolved premise left by Gate 01:

> whether empirically supported ATC-sibling output structure contains a material subset that can be defended as alternative-treatment structure using independent clinical evidence.

It does not treat the Gate 01 output-geometry PASS as evidence of therapeutic substitution.

## 2. Strong negative explanation

The protocol explicitly retains the strongest cheap semantic alternative explanation:

`same ATC parent + shared approved indication`

is recorded only as `NAIVE_SHARED_INDICATION` and cannot determine PASS.

This prevents the semantic stage from succeeding merely because two classes are taxonomically close or appear in the same disease area.

## 3. Prediction-resolution alignment

The downstream model predicts coarse ATC-3 labels, so strict admission requires evidence at the represented class resolution. A guideline-supported relation between one exceptional ingredient pair cannot automatically validate the whole ATC-3 class relation.

This is necessary. Ingredient-level existential evidence would otherwise create a semantic mismatch between the claimed alternative structure and the actual prediction action.

## 4. Evidence hierarchy

The source roles are correctly separated:

- WHO ATC / RxNorm: identity and taxonomy only;
- DailyMed / FDA labeling: indication and restriction corroboration only;
- authoritative guideline or formulary evidence: required for strict alternative-treatment admission.

This matches the clinical meaning of therapeutic interchange more closely than ATC membership alone.

## 5. Candidate-selection freeze

Each calibrated Gate-01 signature unit yields exactly one deterministic primary sibling candidate before semantic evidence inspection.

- `SplitMassFN`: highest-scoring non-target sibling;
- `DuplicateSiblingFP`: highest-scoring emitted non-target sibling;
- ties: ATC-3 code ascending.

No semantic source can change candidate selection.

## 6. Support concentration

The supported-relation threshold of at least 10 distinct Audit patients prevents the semantic workload from being dominated by one-off relations.

The first decision condition additionally requires supported relations to cover at least 50% of calibrated-signature patients across at least 3 ATC-2 parents. If the empirical structure is too diffuse for reproducible semantic characterization, the route stops before expensive curation.

## 7. Semantic materiality

Strict admission must cover at least 25% of the 394 calibrated-signature Audit patients and span at least 3 ATC-2 parents with at least 10 admitted-relation patients per parent.

The 25% floor is a prospective idea-selection materiality threshold chosen before semantic labels are observed. It is not represented as a clinical prevalence estimate, publication effect size, or universal standard.

## 8. Adaptivity boundary

Semantic Admission is explicitly downstream of Gate 01 and therefore uses validation-derived Gate-01 structure to define its candidate universe. This is acceptable for Idea / Hypothesis Selection, but the resulting semantic PASS is not untouched final-generalization evidence.

Test remains outside the entire semantic stage.

## 9. Blinding boundary

The semantic adjudicator receives supported ATC relation identities without their Gate-01 support counts. Counts are restored only after relation labels are frozen.

This prevents high-frequency relations from receiving looser semantic treatment merely because they would help the route pass.

## 10. Stop semantics

The protocol has two scientifically meaningful terminal failures:

- `STOP_SEMANTIC_SIGNAL_TOO_DIFFUSE`;
- `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`.

Neither failure authorizes looser shared-indication criteria, alternate taxonomy rescue, a finer ATC representation, or model training after evidence inspection.

## 11. Scope check

The protocol contains no:

- test evaluation;
- new model inference requirement;
- method implementation;
- architecture search;
- LLM-as-clinician adjudication;
- claim of clinical safety or patient benefit.

## 12. Final design verdict

`DESIGN_INTEGRITY_PASS`

The Semantic Admission protocol is sufficiently falsifiable, source-grounded, resolution-aligned, and cheap to execute as the next Idea-005 hypothesis-selection step.

This audit authorizes only independent execution of the frozen Semantic Admission protocol after the protocol revision is recorded. It does not authorize Gate 02 or method development.
