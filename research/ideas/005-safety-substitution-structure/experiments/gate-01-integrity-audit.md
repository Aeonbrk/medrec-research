<!-- markdownlint-disable MD013 -->

# Gate 01 Integrity Audit Report — Output-Structure Signature

- **Idea**: `005-safety-substitution-structure`
- **Gate**: `gate-01-output-structure-signature`
- **Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Harness Revision**: `4bb07d3d0050070a811f7a4e307522906470e6f7`
- **Audit Date**: 2026-09-04
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`numeric-audit`, `claim-audit`, `citation-audit`)
- **Integrity Verdict**: `INTEGRITY_PASS`

---

## Output Contract Summary

```text
Mode: full (numeric-audit, claim-audit, citation-audit)
Artifacts checked:
  - research/ideas/005-safety-substitution-structure/experiments/gate-01-output-structure-signature.md (protocol commit: 95966eab6d018e34b6dae4a52271562826bb5b4d)
  - research/ideas/005-safety-substitution-structure/experiments/run_output_structure_signature_gate.py (execution revision: 4bb07d3d0050070a811f7a4e307522906470e6f7)
  - research/ideas/005-safety-substitution-structure/experiments/stage_gate01_inputs.py (execution revision: 4bb07d3d0050070a811f7a4e307522906470e6f7)
  - research/ideas/005-safety-substitution-structure/experiments/gate-01-summary.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/gate-01-summary.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/dev-thresholds.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/gate-01-units.jsonl
Claim-evidence matrix: See Section 1 below (all empirical claims supported; 0 overstatements; scope bounds respected)
Numeric consistency findings: Pass (0 invariant failures, 0 partition leaks, 0 split mismatches, exact agreement on Gate A, B, and C criteria)
Citation metadata findings: Pass (Frozen baseline, snapshot, and benchmark identities conform to registry authority)
Citation-context findings: Pass (Protocol scope strictly validation-only hypothesis selection; no clinical substitution claims)
Severity: NONE (all checks passed with exact numeric agreement)
Safe edit suggestions: None required
Next CCFA owner: execution agent / research decision
No-invention status: Verified (100% independently derived from restricted run artifacts and frozen protocol)
```

```text
Integrity Status: INTEGRITY_PASS
Formal Gate 01 verdict independently reproduced: yes
Research decision unlocked: yes
```

---

## 1. Claim-Evidence Matrix

| Claim Location | Claim Statement | Evidence Status | Finding / Category | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `gate-01-output-structure-signature.md` §2 | "In frozen MoleRec ATC-3 validation outputs, does a material sibling-group mass-allocation error signature remain after Dev-only per-medication threshold calibration?" | Evaluated on 3,919 eligible units across 440 Audit patients from 530 total Audit patients (seed `2005`). | **Supported as Empirically Observed** | Preregistered materiality conditions survived Dev-only calibration. |
| `gate-01-summary.json` §Gate A | Audit contains $\ge 3$ candidate groups each represented by $\ge 50$ distinct Audit patients. | Observed: 20 candidate groups (out of 31 eligible candidate groups) meet the $\ge 50$ distinct Audit patients criterion ($20 \ge 3$). | **Supported** | Gate A PASSED unconditionally. |
| `gate-01-summary.json` §Gate B | Under raw threshold `0.5`, $\ge 50$ signature patients overall and $\ge 3$ parents each with $\ge 10$ signature patients. | Observed: 338 distinct Audit patients with `AnySignature` ($\ge 50$), and 8 distinct ATC-2 parents each with $\ge 10$ signature patients ($\ge 3$). | **Supported** | Gate B PASSED. Raw SplitMassFN: 65 patients (71 units); raw DuplicateSiblingFP: 326 patients (680 units). |
| `gate-01-summary.json` §Gate C | Under Dev-only per-medication F1 thresholds, the exact same materiality conditions hold on Audit. | Observed: 394 distinct Audit patients with `AnySignature` ($\ge 50$), and 14 distinct ATC-2 parents each with $\ge 10$ signature patients ($\ge 3$). | **Supported** | Gate C PASSED. Calibrated SplitMassFN: 46 patients (50 units); calibrated DuplicateSiblingFP: 391 patients (1,122 units). |
| `gate-01-summary.json` §Verdict | Mechanical verdict is `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`. | Direct mechanical consequence of Gate A = True, Gate B = True, Gate C = True. | **Supported** | Verdict matches frozen decision tree exactly. |

### Explicitly Disallowed Claims Check

The audit confirmed that none of the forbidden claims are made:

- **No clinical substitution claim**: ATC-2 siblings are strictly output-space candidate groupings; no claim of therapeutic interchangeability, indication equivalence, or prescriber acceptability.
- **No safety-by-substitution claim**: No claim that substitution improves safety, that DDI training causes the phenotype, or that undertreatment is prevented.
- **No method superiority claim**: No claim that a group-aware decoder, loss function, or proposed architecture would improve recommendation metrics.
- **No generalization claim**: Findings are strictly confined to frozen MoleRec ATC-3 validation outputs under the Unified Research Protocol.
- **No post-hoc rescue or adjustment**: Zero parameter tuning, zero alternate seeds, zero regrouping, zero vocabulary granularity alterations.

---

## 2. Frozen Identity Audit

The formal public summary records exactly the frozen identities, verified against registry authority and execution environment:

| Identity Field | Expected Frozen Target | Recorded in `gate-01-summary.json` | Audit Status |
| :--- | :--- | :--- | :--- |
| `protocol_commit` | `95966eab6d018e34b6dae4a52271562826bb5b4d` | `95966eab6d018e34b6dae4a52271562826bb5b4d` | Exact match |
| `harness_revision` | `4bb07d3d0050070a811f7a4e307522906470e6f7` | `4bb07d3d0050070a811f7a4e307522906470e6f7` | Exact match |
| `model_source_revision` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | Exact match |
| `checkpoint_sha256` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | Exact match |
| `baseline_core_sha256` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | Exact match |
| `adapter_sha256` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | Exact match |
| `baseline_environment_name` | `medrec-molerec-table1` | `medrec-molerec-table1` | Exact match |
| `baseline_environment_sha256` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | Exact match |
| `dataset_id` | `molerec-table1-comparison-v1-1` | `molerec-table1-comparison-v1-1` | Exact match |
| `dataset_manifest_sha256` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | Exact match |
| `snapshot_id` | `molerec-table1-c721-www23` | `molerec-table1-c721-www23` | Exact match |
| `snapshot_sha256` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | Exact match |
| `medication_vocabulary_sha256` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | Exact match |
| `ddi_asset_sha256` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | Exact match |
| `feature_availability_sha256` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | Exact match |

---

## 3. Test Isolation Audit

1. **Staging Isolation**: `stage_gate01_inputs.py` partitioned records by `_split_ranges(6350)`: `train` range(0, 4233), `test` range(4233, 5291), `validation` range(5291, 6350). The staging loop strictly iterates `validation_patient_indices` only.
2. **Context Count**: Exactly 1,220 validation visits from 1,059 validation patients were staged to `features.pkl`.
3. **Inference Isolation**: The Comparison adapter received only the 1,220 validation visits.
4. **Evaluation Isolation**: `run_output_structure_signature_gate.py` evaluated only the validation cohort.
5. **Untouched Boundary**: Test split patients ($N=1,058$) and test visits ($N=1,206$) were never indexed, never staged, never predicted, never evaluated, and remain 100% untouched.

---

## 4. Cohort Partition & Split Audit

- Split unit: patient
- Seed: `2005` (deterministic shuffle over validation indices $0 \dots 1058$)
- Total validation patients: 1,059
- Dev allocated patients: 529
- Audit allocated patients: 530
- Patient disjointness: `dev_patients & audit_patients == empty` (0 overlapping patients)
- Audit eligible patients: 440 distinct Audit patients had at least one singleton-target eligible unit ($|M_t \cap G| = 1$)

---

## 5. Calibration Leakage Audit

- **Threshold Fitting Split**: Thresholds $\tau_m$ were fitted on Dev visits only ($N_{Dev} = 529$ patients).
- **Objective**: Maximize per-medication binary F1 on Dev with candidate set $\{0.0, 0.5, 1.0 + 10^{-12}\} \cup \{p_t(m) : t \in Dev\}$ and tie-break: highest F1, closest to 0.5, larger threshold.
- **Audit Target Isolation**: Audit targets $M_t$ and Audit scores $p_t(m)$ were not read during threshold selection.
- **Threshold Freezing**: Thresholds $\tau_m$ were written to `dev-thresholds.json` before Audit evaluation commenced.
- **Leakage Status**: ZERO leakage detected.

---

## 6. Raw-Set Invariant Audit

The comparison adapter predicted set was verified on every visit against the raw decision threshold:

$$
\hat M_t^{raw} = \{m : p_t(m) \ge 0.5\}
$$

Every prediction record in `batch.predictions` satisfied `set(prediction.predicted_medications) == {m for m, s in scores.items() if s >= 0.5}`. Zero invariant violations occurred.

---

## 7. Numerical Verification & Decision Tree Recomputation

| Evaluation Metric | Preregistered Requirement | Observed Value | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Gate A: Multi-Group Support** | $\ge 3$ groups with $\ge 50$ eligible Audit patients each | 20 groups with $\ge 50$ eligible Audit patients (out of 31 candidate groups) | **PASS** |
| **Gate B: Raw AnySignature Patients** | $\ge 50$ distinct Audit patients | 338 patients | **PASS** |
| **Gate B: Raw Signature Parents** | $\ge 3$ parents with $\ge 10$ patients each | 8 parents | **PASS** |
| **Gate C: Calibrated AnySignature Patients** | $\ge 50$ distinct Audit patients | 394 patients | **PASS** |
| **Gate C: Calibrated Signature Parents** | $\ge 3$ parents with $\ge 10$ patients each | 14 parents | **PASS** |

### Breakdown of Preregistered Signatures

| Signature Policy | SplitMassFN Units | SplitMassFN Patients | DuplicateSiblingFP Units | DuplicateSiblingFP Patients | AnySignature Units | AnySignature Patients | Parents with $\ge 10$ Patients |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Raw ($0.5$)** | 71 | 65 | 680 | 326 | 751 | 338 | 8 |
| **Calibrated (Dev-F1)** | 50 | 46 | 1,122 | 391 | 1,172 | 394 | 14 |

### Decision Tree Path

```text
[Gate A: ATC-3 sibling-group support]
  >=3 groups with >=50 eligible Audit patients each? (20 >= 3) -> YES
  -> Proceed to Gate B

[Gate B: Raw structural signature]
  >=50 signature patients overall (338 >= 50) AND >=3 parents with >=10 patients (8 >= 3)? -> YES
  -> Proceed to Gate C

[Gate C: Dev-only per-medication calibration killer control]
  same materiality conditions still hold on Audit? (394 >= 50 patients, 14 >= 3 parents) -> YES
  -> Final Mechanical Verdict: PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION
```

The reported summary verdict matches the mechanical recomputation with zero discrepancy.

---

## 8. Conclusion

The execution of Gate 01 satisfies all protocol, execution, identity, isolation, calibration, and numerical invariants.

Integrity Verdict: **`INTEGRITY_PASS`**.
Proceed to research decision.
