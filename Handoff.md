# Handoff: Idea 005 Semantic Admission Completed Execution & Decision

## Current state

Idea `005-safety-substitution-structure` has completed its formal Semantic Admission execution, underwent an independent integrity audit by `ccf-integrity-auditor` (`claim-audit + citation-audit + numeric-audit`), and formed an authoritative research decision.

- **Idea ID**: `005-safety-substitution-structure`
- **Idea Status**: `TERMINATED / STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **Primary Method Direction**: safety by substitution, not suppression (Terminated)
- **Gate 01 Protocol**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-output-structure-signature.md`
- **Gate 01 Protocol Commit**: `95966eab6d018e34b6dae4a52271562826bb5b4d`
- **Gate 01 Execution Revision**: `4bb07d3d0050070a811f7a4e307522906470e6f7`
- **Gate 01 Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Gate 01 Public Summary**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-summary.json`
- **Gate 01 Integrity Audit**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-integrity-audit.md` (`INTEGRITY_PASS`)
- **Gate 01 Research Decision**: `research/ideas/005-safety-substitution-structure/research-decision.md`
- **Gate 01 Verdict**: `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`
- **Semantic Admission Protocol**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-protocol.md`
- **Semantic Admission Protocol Commit**: `587e3f626cf8c5849553176f8f1fae3aa2eb0d84`
- **Semantic Admission Design Audit**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-design-integrity-audit.md` (`DESIGN_INTEGRITY_PASS`)
- **Candidate Relations**: `research/ideas/005-safety-substitution-structure/experiments/semantic-candidate-relations.json`
- **Evidence Ledger**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-ledger.md`
- **Public Summary**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-summary.json`
- **Integrity Audit**: `research/ideas/005-safety-substitution-structure/experiments/semantic-admission-integrity-audit.md` (`INTEGRITY_PASS`)
- **Research Decision**: `research/ideas/005-safety-substitution-structure/research-decision-semantic-admission.md`
- **Formal Verdict**: `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **Failure Record**: `research/memory/failures/safety-substitution-structure-semantic-admission--atc-structure-not-therapeutically-admissible.md`
- **Gate 02**: `NOT_AUTHORIZED`
- **Test Split**: unindexed, unstaged, unpredicted, unevaluated, and untouched (100% isolated)

## Scientific question & result

$$
\boxed{\begin{aligned}
&\text{Do the empirically supported target-to-sibling relations contain a material subset}\\
&\text{supported by independent authoritative evidence as alternative treatment structure?}
\end{aligned}}
$$

**Result**: **NO**. At the repository's ATC-3 prediction resolution, many high-support relations correspond clinically to complementary combination therapy, disjoint treatment contexts, or coarse taxonomy co-location rather than therapeutic alternatives.

### Mechanical Decision Tree Findings

1. **Phase S0 (Relation Extraction)**:
   - 1,121 calibrated signature units across the 20 high-support sibling groups produced 67 candidate directed relations $y_t \to a_t$.
   - 23 relations occurred in $\ge 10$ distinct Audit patients and formed the supported semantic review set.
2. **Semantic A (Relation Concentration Gate)**: **PASS**
   - Requirement: supported relations cover $\ge 50\%$ of the 394 calibrated-signature patients across $\ge 3$ ATC-2 parents.
   - Observed: 23 supported relations cover 381 distinct patients (96.70% of 394) across 12 ATC-2 parents.
3. **Support-Count-Blinded Evidence Adjudication & Negative Control**:
   - Strict Tier-A alternative treatment evidence at the ATC-3 class resolution was confirmed for only 1 relation:
     - `C09A -> C09C` (ACEi vs ARB in hypertension/HFrEF; ACC/AHA guidelines; 11 patients).
   - Re-audit of the three candidate antibacterial relations (`J01C -> J01D`, `J01D <-> J01M`) under frozen protocol §8.1(4) confirmed that clinical guidelines (IDSA/ATS) support only specific agent/regimen alternatives in select infection contexts, not wholesale class interchangeability between heterogeneous ATC-3 groups. Pursuant to §8.2, they were assigned `REJECT_NOT_ALTERNATIVE`.
   - 22 relations in total were strictly rejected:
     - Complementary combinations: multimodal analgesia (`N02B <-> N02A`), sequential nephron blockade (`C03C -> C03A`);
     - Disjoint disease stages/severity: mucosal healing vs on-demand antacid neutralization (`A02B <-> A02A`);
     - Contraindications / distinct mechanisms: DHP vs non-DHP CCBs (`C08C -> C08D` contraindicated in HFrEF);
     - Disjoint psychiatric domains: psychosis vs anxiety vs sleep (`N05A <-> N05B`, `N05C -> N05A`, `N05C -> N05B`);
     - Heterogeneous antibacterial classes failing class-level interchangeability (`J01C -> J01D`, `J01D <-> J01M`).
   - Strong negative control: Among the 14 supported relations labeled `NAIVE_SHARED_INDICATION`, 13 (92.9%) failed strict semantic admission, confirming that shared indication $\neq$ therapeutic substitution.
4. **Semantic B (Material Strict Alternative Admission)**: **FAIL**
   - Requirement: strict admitted relations cover $\ge 25\%$ of calibrated-signature patients and span $\ge 3$ ATC-2 parents each with $\ge 10$ admitted patients.
   - Observed: admitted relations cover only 11 distinct patients (2.79% < 25.0%) across only 1 parent (`C09` with 11 patients).
   - Terminal Verdict: `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`.

## Strict scope & termination boundaries

- Idea 005 is authoritatively terminated before model implementation.
- Gate 02 remains `NOT_AUTHORIZED`.
- No group-aware decoder, loss function, or substitution model may be trained or implemented.
- Do not rescue the route by post-hoc loosening of criteria, alternative ontologies, or sub-cohort carving.
- Test split remains 100% untouched.

## Preserved artifacts

- Restricted per-unit and support artifacts remain on `319-lab`:
  `/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/`
- Public-safe candidate relations, evidence ledger, summary, audit, and decision are committed to Git.

## Next owner

Workflow planner / exploratory direction scouting (`ccf-pipeline-orchestrator` / `ccf-idea-optimizer`) to formulate new candidate research hypotheses.
