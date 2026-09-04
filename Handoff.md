# Handoff: Idea 005 Gate 01 Frozen Design & Implementation

## Current state

Idea `005-safety-substitution-structure` is selected for one minimal validation-only hypothesis gate after independent literature review and adversarial direction arbitration. Gate 01 has a frozen protocol, Idea-local implementation, focused synthetic verification, and a design-level integrity audit. It has **not** been executed on real data.

- **Idea ID**: `005-safety-substitution-structure`
- **Idea Status**: `SELECTED / GATE_01_DESIGNED_NOT_EXECUTED`
- **Primary Method Direction**: safety by substitution, not suppression
- **Gate Protocol**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-output-structure-signature.md`
- **Protocol Commit**: `95966eab6d018e34b6dae4a52271562826bb5b4d`
- **Grounding / Plan Commit**: `33132719d714da726454ca584deb13302a3f5936`
- **Implementation Commit**: `ddd1a2ce9f36110977d053fbc9ac4b0411a4422c`
- **Design Audit**: `research/ideas/005-safety-substitution-structure/experiments/gate-01-design-integrity-audit.md` (`DESIGN_INTEGRITY_PASS`)
- **Execution Plan**: `docs/plans/2026-09-04-idea-005-output-structure-signature-gate-plan.md`
- **Gate 02**: `NOT_AUTHORIZED`
- **Test Split**: unindexed, unpredicted, and untouched for Idea 005
- **ccfa.yaml**: absent per repository conventions

## Scientific question

$$
\boxed{\begin{aligned}
&\text{In frozen MoleRec ATC-3 validation outputs, does a material sibling-group}\\
&\text{mass-allocation error signature remain after Dev-only per-medication}\\
&\text{threshold calibration?}
\end{aligned}}
$$

This is a premise Gate for the possible downstream method story:

$$
\text{unsafe action} \rightarrow \text{acceptable alternative}
$$

rather than

$$
\text{unsafe action} \rightarrow \varnothing.
$$

Gate 01 does **not** claim ATC siblings are therapeutic substitutes and does not test a safety-aware method.

## Frozen Gate 01 design

### Candidate groups

The current executable vocabulary is ATC-3. Gate 01 groups ATC-3 codes by their three-character ATC-2 prefix and retains parents with at least two vocabulary members.

This is output-space geometry only:

$$
\text{same ATC-2 parent}\not\Rightarrow\text{clinical substitutability}.
$$

### Eligible unit

For visit $t$ and sibling group $G$, evaluate only when the observed prescription contains exactly one member of $G$:

$$
|M_t\cap G|=1.
$$

### Two prespecified signatures

For frozen scores $p_t(m)$ define

$$
S_t(G)=1-\prod_{m\in G}(1-p_t(m)).
$$

`SplitMassFN`: the unique observed member is missed, no sibling is predicted, and $S_t(G)\ge0.5$.

`DuplicateSiblingFP`: the unique observed member is predicted and at least one additional non-target sibling is also predicted.

No third signature is authorized.

### Strongest simple killer control

Each medication receives one threshold fitted on Dev only to maximize medication-level F1. Thresholds are frozen before Audit. If the calibrated policy removes the preregistered signature materiality, the structural route stops.

### Split

- source: validation only;
- patient-disjoint Dev/Audit;
- seed: `2005`;
- expected validation patients: `1059`;
- test access: forbidden.

## Mechanical decision tree

```text
Gate A: >=3 sibling groups with >=50 eligible Audit patients each?
  NO  -> INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT
  YES -> Gate B

Gate B: raw threshold has >=50 signature patients overall
        AND >=3 parents with >=10 signature patients each?
  NO  -> STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE
  YES -> Gate C

Gate C: same materiality survives Dev-only per-medication calibration?
  NO  -> STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION
  YES -> PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION
```

A PASS authorizes only later semantic admission after independent integrity audit. It does not authorize a group-aware decoder/loss, Gate 02, additional backbones, or test evaluation.

## Implementation surface

Idea-local files:

```text
research/ideas/005-safety-substitution-structure/experiments/
  gate-01-output-structure-signature.md
  gate-01-design-integrity-audit.md
  stage_gate01_inputs.py
  run_output_structure_signature_gate.py

tests/unit/
  test_gate_01_output_structure_signature.py
```

The runner reuses the frozen MoleRec Comparison identities, stages only validation inputs on 319, obtains complete vocabulary scores through the existing target-free Comparison adapter, verifies the raw adapter set equals `score >= 0.5`, fits thresholds on Dev only, and writes restricted per-unit artifacts only under the 319 run root.

The only Git-eligible execution output is the public-safe aggregate summary after integrity audit. Patient/visit rows, score vectors, threshold maps, targets, predictions, checkpoints, and logs remain outside Git.

## Next owner

Local execution agent.

Execute only the P0--P5 workflow in `docs/plans/2026-09-04-idea-005-output-structure-signature-gate-plan.md` and the frozen Gate protocol.

The next owner must:

1. synchronize to the accepted clean harness revision and run local software checks;
2. perform the 319 preflight from `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`;
3. run exactly one formal validation-only Gate 01 in a fresh restricted run directory;
4. independently audit the result against the frozen protocol;
5. record the public-safe summary, integrity audit, and research decision;
6. stop after the Gate 01 verdict.

Do not redesign the Gate, access test, change seed/grouping/signatures/support thresholds, run outcome-seeking variants, begin semantic admission, or implement the downstream method in the same execution.
