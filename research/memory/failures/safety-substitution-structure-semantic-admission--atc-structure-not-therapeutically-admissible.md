<!-- markdownlint-disable MD013 -->

# Failure Record: Safety-Preserving Substitution Structure (Semantic Admission: ATC structure not therapeutically admissible)

Source boundary: `medrec-research` Idea `005-safety-substitution-structure`, Gate `semantic-admission` based on frozen Gate 01 run `gate-01-output-structure-signature-20260904-155810`. The independent integrity audit concluded `INTEGRITY_PASS`; the authoritative research decision is `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE` / `TERMINATE_IDEA_005`.

- **Status**: Historical Memory (this substitution-structure route is terminated under the recorded setting; revisit only if a finer prediction resolution, fundamentally different clinical ontology, or external explicit substitution guidance redefines the action space).

## Failed hypothesis

The material ATC-2-sibling mass-allocation error phenotype observed empirically in frozen MoleRec validation outputs represents clinically admissible alternative-treatment choice structure that can support a safety-by-substitution method direction at the repository's ATC-3 prediction resolution.

## What was tested

Under the frozen Semantic Admission protocol (`experiments/semantic-admission-protocol.md`):

1. For each calibrated-policy `AnySignature` unit in the 20 high-support sibling groups ($\ge 50$ distinct Audit patients in Gate 01), exactly one primary directed relation $y_t \to a_t$ was extracted deterministically:
   - `SplitMassFN`: $a_t = \arg\max_{m \in G \setminus \{y_t\}} p_t(m)$
   - `DuplicateSiblingFP`: $a_t = \arg\max_{m \in (\hat M_t^{cal} \cap G) \setminus \{y_t\}} p_t(m)$
   - Tie-break: ATC-3 code ascending.
2. Supported relations with $\ge 10$ distinct Audit patients underwent support-count-blinded clinical evidence adjudication using external authoritative clinical guidelines (Tier A), FDA labeling (Tier B), and WHO ATC (Tier C).
3. `NAIVE_SHARED_INDICATION` was tracked as a strong negative control.
4. Preregistered decision tree:
   - **Semantic A (Concentration)**: supported relations cover $\ge 50\%$ of 394 calibrated signature patients across $\ge 3$ ATC-2 parents.
   - **Semantic B (Materiality)**: strict Tier-A admitted relations cover $\ge 25\%$ of 394 calibrated signature patients across $\ge 3$ ATC-2 parents with $\ge 10$ admitted patients per parent.

## What was observed

1. **Semantic A passed**: 23 supported relations covered 381 patients (96.70% $\ge 50\%$) across 12 ATC-2 parents ($\ge 3$).
2. **Evidence adjudication revealed severe semantic rejection**:
   - Strict Tier-A alternative treatment evidence at the ATC-3 class resolution was confirmed for only 1 relation: `C09A -> C09C` (ACEi vs ARB, 11 patients).
   - Re-audit of the three antibacterial candidate relations (`J01C -> J01D`, `J01D <-> J01M`) under frozen protocol §8.1(4) confirmed that clinical guidelines (IDSA/ATS) support only specific agent/regimen alternatives in select infection contexts, not wholesale class interchangeability between heterogeneous ATC-3 groups. Pursuant to §8.2, they were assigned `REJECT_NOT_ALTERNATIVE`.
   - 22 relations in total were rejected: high-frequency sibling pairs clinically corresponded to complementary combinations (e.g. `N02B <-> N02A` acetaminophen + opioids in multimodal analgesia; `C03C -> C03A` loop + thiazide in sequential nephron blockade), disjoint disease stages/severity (`A02B <-> A02A` mucosal healing PPI vs on-demand antacid), or non-substitutable contraindications (`C08C -> C08D` where non-DHP CCBs are contraindicated in HFrEF).
   - Among the 14 supported relations labeled `NAIVE_SHARED_INDICATION`, 13 (92.9%) failed strict semantic admission.
3. **Semantic B failed**: Admitted relations covered only 11 patients (2.79% < 25.0%) across only 1 ATC-2 parent (`C09` with 11 patients; $1 < 3$).
4. **Mechanical Verdict**: `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`.

## Mechanism of failure

The empirical multi-label sibling correlation observed in deep recommender outputs is characterized clinically by:

1. **Complementary combination regimens**: In clinical practice, therapies frequently appear together in EHR visits as part of multimodal regimens (e.g. pain regimens, sequential nephron blockade), meaning joint co-occurrence rather than alternative mass allocation dominates sibling pairs.
2. **Coarse taxonomy co-location**: WHO ATC-2 groupings cluster drugs by broad anatomical organ system rather than therapeutic interchangeability. At the ATC-3 level, subgroups often represent disjoint severity strata (mild episodic vs severe chronic).
3. **Narrow scope of class-level substitution**: At the ATC-3 prediction resolution, true class-wide therapeutic alternatives are exceedingly rare (only ACEi vs ARB in `C09` satisfied class-level criteria), while other candidate domains (e.g. antibacterials) are limited to narrow, agent-specific regimens and fail class-wide interchangeability.

## Reusable constraints

A reproducible output-space structure is not evidence of a clinically meaningful action structure; semantic admission must precede architecture design when the proposed method assigns clinical meaning to taxonomy-derived groups.

Idea-local evidence:

- output-structure phenotype survived per-label calibration;
- semantic concentration was high;
- strict alternative-treatment admission was not materially broad enough;
- therefore architecture design was stopped before training.

General guidance:

- **Do not equate empirical taxonomy sibling errors with clinical substitution**: Deep multi-label recommenders produce sibling false positives in training co-occurrence contexts without implying that clinicians consider the drug classes interchangeable.
- **Do not treat shared approved indication as therapeutic equivalence**: Shared indication is an unreliable proxy for substitution; in hospital medicine, drugs sharing an indication are frequently complementary combination partners or sequential escalation steps.
- **Do not develop substitution decoders without prior semantic admission**: Designing group-aware or substitution-based decoders without verifying clinical interchangeability leads to optimizing an artifactual, clinically invalid loss surface.
