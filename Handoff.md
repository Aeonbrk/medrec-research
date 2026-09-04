# Handoff: Idea 005 Gate 01 Completed Execution & Verdict

## Current state

Idea `005-safety-substitution-structure` has completed its formal validation-only Gate 01 execution on `319-lab`, underwent an independent integrity audit by `ccf-integrity-auditor`, and formed an authoritative research decision.

- **Idea ID**: `005-safety-substitution-structure`
- **Idea Status**: `GATE_01_PASSED / SEMANTIC_ADMISSION_PENDING`
- **Primary Method Direction**: safety by substitution, not suppression
- **Gate Protocol**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-output-structure-signature.md`
- **Protocol Commit**: `95966eab6d018e34b6dae4a52271562826bb5b4d`
- **Execution Revision**: `4bb07d3d0050070a811f7a4e307522906470e6f7`
- **Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Execution Host**: `319-lab` under `medrec-core-evaluator`
- **Public Summary**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-summary.json`
- **Design Audit**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-design-integrity-audit.md` (`DESIGN_INTEGRITY_PASS`)
- **Integrity Audit**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-integrity-audit.md` (`INTEGRITY_PASS`)
- **Research Decision**: `research/ideas/005-safety-substitution-structure/research-decision.md`
- **Formal Verdict**: `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`
- **Gate 02**: `NOT_AUTHORIZED`
- **Test Split**: unindexed, unpredicted, unevaluated, and untouched (100% isolated)

## Scientific question & result

$$
\boxed{\begin{aligned}
&\text{In frozen MoleRec ATC-3 validation outputs, does a material sibling-group}\\
&\text{mass-allocation error signature remain after Dev-only per-medication}\\
&\text{threshold calibration?}
\end{aligned}}
$$

**Result**: **YES**. A material ATC-2-sibling output-structure error signature survives Dev-only per-medication threshold calibration under frozen MoleRec validation.

### Mechanical Decision Tree Findings

1. **Gate A (ATC-3 Group Support)**: **PASS**
   - Requirement: $\ge 3$ sibling groups each represented by $\ge 50$ distinct Audit patients with eligible singleton-target units.
   - Observed: 20 candidate groups meet this criterion out of 31 candidate groups with $|G| \ge 2$.
2. **Gate B (Raw Signature Materiality)**: **PASS**
   - Requirement: $\ge 50$ signature patients overall and $\ge 3$ parents each with $\ge 10$ signature patients.
   - Observed: 338 distinct Audit patients with `AnySignature`; 8 distinct ATC-2 parents each with $\ge 10$ signature patients.
   - Breakdown: Raw SplitMassFN: 65 patients (71 units); Raw DuplicateSiblingFP: 326 patients (680 units); AnySignature: 338 patients (751 units).
3. **Gate C (Killer Control: Dev-Only Per-Medication Calibration)**: **PASS**
   - Requirement: Same materiality conditions hold under Dev-frozen F1-optimal per-medication thresholds.
   - Observed: 394 distinct Audit patients with `AnySignature`; 14 distinct ATC-2 parents each with $\ge 10$ signature patients.
   - Breakdown: Calibrated SplitMassFN: 46 patients (50 units); Calibrated DuplicateSiblingFP: 391 patients (1,122 units); AnySignature: 394 patients (1,172 units).

## Strict scope boundaries

The Gate 01 PASS does **not** prove or imply:

- ATC siblings are therapeutic substitutes;
- observed prescriptions are clinically optimal;
- the signatures are caused by DDI training;
- safety optimization causes undertreatment;
- a group-aware decoder or loss will improve recommendation;
- clinical safety or patient benefit;
- cross-backbone or test-set generalization.

## Preserved artifacts

- Restricted per-unit and threshold artifacts remain outside Git on `319-lab`:
  `/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/`
- Public-safe aggregate summary and audit documents are committed in repository.

## Next owner

CCFA workflow planner / protocol designer.

The next stage is strictly:

- Designing a **Semantic Admission Protocol** for independent review to test whether high-support ATC-2 sibling groups contain clinically defensible alternatives.
- **Gate 02 remains NOT_AUTHORIZED**.
- Do not access test split.
- Do not train or implement group-aware decoders/models before semantic admission is formally designed, reviewed, and audited.
