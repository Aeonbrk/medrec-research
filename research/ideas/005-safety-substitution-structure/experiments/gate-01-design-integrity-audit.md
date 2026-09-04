<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Audit — Output-Structure Signature

## Verdict

`DESIGN_INTEGRITY_PASS`

The Gate design is internally consistent with the repository research workflow and is sufficiently narrow for hypothesis selection.

## Claim-to-evidence alignment

The Gate does not claim therapeutic substitution. Its only prospective claim is that a material ATC-2-sibling output-structure error signature either does or does not remain after a strong per-medication calibration control.

The eligible unit, two signatures, support conditions, killer control, and decision tree directly measure that claim.

## Strongest simple control

The design includes the most dangerous cheap explanation identified during review: per-medication threshold calibration on a patient-disjoint Dev partition.

If that control removes materiality, the route terminates. No group-aware method is authorized.

## Leakage boundary

- Group construction uses only the frozen medication vocabulary.
- Threshold fitting uses Dev scores and Dev targets only.
- Audit targets are used only for the preregistered evaluation.
- Test is forbidden from staging, prediction, support counting, and diagnostics.

## Semantic boundary

ATC-2 siblings are explicitly named candidate groups rather than therapeutic substitutes. The protocol states that same-parent ATC structure does not establish interchangeability. This prevents a structural diagnostic from silently becoming a clinical claim.

## Adaptivity control

The protocol freezes:

- seed `2005`;
- ATC-2 prefix grouping;
- group size floor of two vocabulary members;
- singleton-target eligibility;
- noisy-OR diagnostic formula;
- `0.5` group-mass threshold;
- exactly two signatures;
- per-medication F1 threshold fitter and tie-breaking;
- Gate A/B/C support and decision conditions.

No result-dependent rescue is authorized.

## Data-support logic

Gate A separates lack of representational support from absence of the output phenotype. The three-group requirement prevents one pharmacological family from carrying a method-paper premise. The 50-patient support floor reuses an established project convention rather than inventing a significance claim.

## Implementation placement

The runner and staging code remain Idea-local because the hypothesis is unproven. No `src/medrec_research/` promotion is justified.

## Execution boundary

Local execution is limited to software/synthetic verification. Real-data staging and frozen MoleRec inference must occur on 319 after the repository remote-execution preflight.

## Stop rule audit

The stop states are scientifically meaningful and change subsequent work:

- insufficient multi-group support stops the first-paper route under ATC-3;
- no raw material signature stops the mechanism premise;
- calibration-explained signature stops the structured-method story;
- PASS authorizes only later semantic admission, not method training.

No paper experiment or Gate 02 is implied by this audit.
