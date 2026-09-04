# Handoff: Idea 005 Semantic Admission Frozen Design

## Current state

Idea `005-safety-substitution-structure` completed formal Gate 01 with `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION` and `INTEGRITY_PASS`. The next scientific task, Semantic Admission, is now designed and has passed a design-level integrity review. It has not been executed.

- **Idea ID**: `005-safety-substitution-structure`
- **Idea Status**: `GATE_01_PASSED / SEMANTIC_ADMISSION_DESIGNED_NOT_EXECUTED`
- **Primary Method Direction**: safety by substitution, not suppression
- **Gate 01 Protocol**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-output-structure-signature.md`
- **Gate 01 Protocol Commit**: `95966eab6d018e34b6dae4a52271562826bb5b4d`
- **Gate 01 Execution Revision**: `4bb07d3d0050070a811f7a4e307522906470e6f7`
- **Gate 01 Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Gate 01 Public Summary**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-summary.json`
- **Gate 01 Integrity Audit**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-integrity-audit.md` (`INTEGRITY_PASS`)
- **Gate 01 Research Decision**: `research/ideas/005-safety-substitution-structure/research-decision.md`
- **Gate 01 Verdict**: `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`
- **Semantic Admission Protocol**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-protocol.md`
- **Semantic Admission Design Audit**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-design-integrity-audit.md` (`DESIGN_INTEGRITY_PASS`)
- **Semantic Admission Status**: `DESIGNED_NOT_EXECUTED`
- **Gate 02**: `NOT_AUTHORIZED`
- **Test Split**: unindexed, unpredicted, unevaluated, and untouched

## Gate 01 result retained as upstream evidence

Under the frozen validation Audit partition:

- 20 candidate ATC-2 sibling groups had at least 50 eligible Audit patients;
- 338 distinct patients exhibited a raw `AnySignature` across 8 supported ATC-2 parents;
- after Dev-only per-medication F1 calibration, 394 distinct patients exhibited `AnySignature` across 14 supported ATC-2 parents.

The only supported claim is:

> A material ATC-2-sibling output-structure error signature survives Dev-only per-medication threshold calibration under frozen MoleRec validation.

No therapeutic-substitution claim follows from Gate 01.

## Semantic Admission scientific question

$$
\boxed{\begin{aligned}
&\text{Do the empirically supported target-to-sibling relations contain a material subset}\\
&\text{for which independent authoritative evidence supports an alternative-treatment interpretation?}
\end{aligned}}
$$

The null explanation is that the Gate-01 structure is only taxonomy proximity or shared indication.

## Frozen Semantic Admission design

### Candidate relation

Use the existing restricted Gate-01 calibrated `AnySignature` units only. Do not rerun MoleRec.

Each unit contributes exactly one directed relation $y_t\rightarrow a_t$:

- `SplitMassFN`: highest frozen-score non-target sibling;
- `DuplicateSiblingFP`: highest frozen-score emitted non-target sibling;
- ties: ATC-3 code ascending.

Only relations occurring in at least 10 distinct Audit patients enter semantic review.

### Semantic A — relation concentration

Require supported relations to:

- cover at least 50% of the 394 calibrated-signature patients;
- span at least 3 ATC-2 parents.

Otherwise:

`STOP_SEMANTIC_SIGNAL_TOO_DIFFUSE`

### Evidence hierarchy

Strict admission requires authoritative guideline / formulary evidence explicitly positioning the compared treatment classes as alternatives in the same indication and overlapping clinical context.

- WHO ATC / RxNorm: identity and taxonomy only;
- FDA / DailyMed: shared-indication and restriction corroboration only;
- shared indication alone: `NAIVE_SHARED_INDICATION`, never strict admission.

The semantic adjudicator receives relation identities without Gate-01 support counts until labels are frozen.

### Strict labels

Exactly one label per supported relation:

- `ADMIT_ALTERNATIVE_CLASS_RELATION`;
- `REJECT_NOT_ALTERNATIVE`;
- `UNRESOLVED_INSUFFICIENT_EVIDENCE`.

### Semantic B — material strict admission

PASS requires:

- strict admitted relations cover at least 25% of the 394 calibrated-signature patients;
- admitted relations span at least 3 ATC-2 parents;
- each of those parents has at least 10 distinct admitted-relation patients.

If not:

`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`

If yes:

`PASS_SEMANTIC_ADMISSION_FOR_METHOD_DESIGN`

## Next owner

Local execution / evidence-curation agent.

Execute only the frozen Semantic Admission protocol, then run `ccf-integrity-auditor` in `claim-audit + citation-audit + numeric-audit` mode and form the mechanical decision.

Do not:

- access test;
- rerun or retrain MoleRec;
- change relation selection after seeing clinical evidence;
- expose support counts to the semantic adjudicator before labels are frozen;
- treat ATC membership or shared indication as strict admission;
- loosen the 50% / 25% / multi-parent materiality conditions after inspection;
- implement a group-aware decoder or loss;
- begin Gate 02 or publication experiments.
