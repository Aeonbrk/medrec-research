<!-- markdownlint-disable MD013 -->

# Gate 01 — Output-Structure Signature

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

Status:

`DESIGNED_NOT_EXECUTED`

This is a validation-only falsification gate. It is not a publication experiment, not a clinical substitution study, and not authorization for a group-aware model.

---

## 1. Scientific state entering Gate 01

Ideas 001--004 are formally closed. Their scoped negative evidence supports a research-prioritization change: another low-dimensional candidate-level reranking observable is low expected value relative to a mechanism that changes prediction formation or output structure.

Candidate C, medication-conditioned state-transition representation, is not retained because its method space is crowded by longitudinal and treatment-response work and the current code-level state transition is difficult to interpret clinically.

The retained primary direction is safety by substitution rather than suppression. Before any method is built, Gate 01 asks whether the existing frozen ATC-3 output contains a material sibling-group mass-allocation error signature that survives the strongest cheap calibration control.

---

## 2. Central scientific question

$$
\boxed{\begin{aligned}
&\text{In frozen MoleRec ATC-3 validation outputs, does a material sibling-group}\\
&\text{mass-allocation error signature remain after Dev-only per-medication}\\
&\text{threshold calibration?}
\end{aligned}}
$$

---

## 3. Frozen upstream scope

Gate 01 reuses the already qualified MoleRec Table 1 Comparison Mode identities:

- `model_source_revision`: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
- `checkpoint_sha256`: `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
- `baseline_core_sha256`: `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511`
- `adapter_sha256`: `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531`
- `baseline_environment_name`: `medrec-molerec-table1`
- `baseline_environment_sha256`: `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda`
- `dataset_id`: `molerec-table1-comparison-v1-1`
- `dataset_manifest_sha256`: `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712`
- `snapshot_id`: `molerec-table1-c721-www23`
- `snapshot_sha256`: `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58`
- `medication_vocabulary_sha256`: `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08`
- `ddi_asset_sha256`: `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7`
- `feature_availability_sha256`: `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9`

Private checkpoint and dataset paths remain restricted 319 state and must not enter Git.

Gate execution may regenerate validation-only target-free MoleRec predictions under these identities. It must not retrain MoleRec and must not access test.

---

## 4. Validation split

Use the frozen validation patient universe only.

A fresh deterministic patient-disjoint Dev/Audit split is preregistered from the Idea-number convention:

```python
patients = sorted(patient_orders)
random.Random(2005).shuffle(patients)
mid = len(patients) // 2
dev_patients = set(patients[:mid])
audit_patients = set(patients[mid:])
```

- split unit: patient;
- seed: `2005`;
- expected source validation patients: `1059`;
- Dev/Audit are patient-disjoint;
- do not change the seed if support is weak.

Validation has already participated in route selection for prior Ideas. Audit here is held-out hypothesis-selection evidence, not untouched final-generalization evidence.

### Test isolation

Do not index test. Do not stage test. Do not predict test. Do not inspect test support. Do not use test for diagnostics.

---

## 5. Candidate sibling groups

The frozen medication vocabulary consists of ATC-3 codes. Define the ATC-2 parent deterministically as the first three characters of an ATC-3 code.

For parent $a$, define

$$
G_a=\{m:\operatorname{ATC2}(m)=a\}.
$$

Retain candidate groups with

$$
|G_a|\ge2.
$$

No train co-occurrence, indication mapping, DDI relation, guideline relation, or learned grouping may alter this candidate-group definition after outcome inspection.

### Semantic boundary

`ATC-2 sibling candidate group` is an output-space grouping only.

Gate 01 does not assert:

$$
\text{same ATC-2 parent}\Rightarrow\text{therapeutic substitutability}.
$$

---

## 6. Eligible group-visit unit

For visit $t$ and candidate group $G$, let $M_t$ be the observed target prescription.

The unit is eligible iff:

$$
|M_t\cap G|=1.
$$

This singleton-target condition gives one observed group member without claiming that other group members would have been clinically acceptable.

The evaluation unit is `(patient, visit, ATC-2 parent)`.

---

## 7. Frozen raw policy and score contract

For every vocabulary medication $m$, let frozen MoleRec emit score $p_t(m)$.

Gate execution must verify:

$$
0\le p_t(m)\le1
$$

and that the adapter's frozen predicted set is exactly

$$
\hat M_t^{raw}=\{m:p_t(m)\ge0.5\}.
$$

Any mismatch blocks the Gate as an implementation/protocol error. The threshold is not reinterpreted after inspection.

---

## 8. Diagnostic group mass

For eligible group $G$, define

$$
S_t(G)=1-\prod_{m\in G}(1-p_t(m)).
$$

`GroupMass` is a noisy-OR-style diagnostic aggregation only. It is not a calibrated probability and has no clinical-equivalence semantics.

The preregistered diagnostic threshold is the frozen decision threshold:

$$
S_t(G)\ge0.5.
$$

No alternative aggregate or cutpoint is authorized after Audit inspection.

---

## 9. Two prespecified signatures

Let $m_t^*$ be the unique observed target member in $M_t\cap G$.

### 9.1 SplitMassFN

`SplitMassFN` is true iff:

$$
m_t^*\notin\hat M_t,
$$

$$
\hat M_t\cap G=\varnothing,
$$

and

$$
S_t(G)\ge0.5.
$$

Interpretation is limited to score dispersion: group-level score mass is high while no sibling crosses the decision threshold and the observed member is missed.

### 9.2 DuplicateSiblingFP

`DuplicateSiblingFP` is true iff:

$$
m_t^*\in\hat M_t
$$

and

$$
|(\hat M_t\cap G)\setminus\{m_t^*\}|\ge1.
$$

Interpretation is limited to redundant sibling emission relative to the observed benchmark label.

The two signatures are mutually exclusive by construction.

Define `AnySignature = SplitMassFN OR DuplicateSiblingFP`.

No third signature is authorized at Gate 01.

---

## 10. Strongest simple killer control: Dev-only per-medication thresholds

For each medication $m$, fit one threshold $\tau_m$ using all Dev visits only. The binary target is

$$
y_t(m)=\mathbf1[m\in M_t].
$$

Candidate thresholds are deterministic:

$$
\{0,0.5,1+10^{-12}\}\cup\{p_t(m):t\in Dev\}.
$$

For each candidate threshold, predict $\mathbf1[p_t(m)\ge\tau]$ and compute medication-level F1 on Dev.

Choose threshold by:

1. maximum F1;
2. minimum absolute distance to `0.5`;
3. larger threshold if still tied.

No cross-validation, grid expansion, subgroup tuning, or Audit labels are allowed.

Freeze all $\tau_m$ before Audit. Define

$$
\hat M_t^{cal}=\{m:p_t(m)\ge\tau_m\}.
$$

Recompute the same two signatures on Audit using $\hat M_t^{cal}$ while leaving $S_t(G)$ unchanged.

If this control removes materiality, the structural route terminates.

---

## 11. Gate A — dataset support

Audit must contain at least three distinct ATC-2 sibling candidate groups, each represented by at least 50 distinct Audit patients with one or more eligible singleton-target units.

If not:

`INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT`

Do not alter group granularity, split, or eligibility to rescue support.

The `50`-patient support floor reuses the project's established Gate support convention. The three-group requirement prevents a single pharmacological group from defining the route.

---

## 12. Gate B — raw signature materiality

Under the frozen raw threshold `0.5`, require both:

1. at least 50 distinct Audit patients with at least one `AnySignature` unit;
2. at least three distinct ATC-2 parents, each with at least 10 distinct Audit patients with `AnySignature`.

If either condition fails:

`STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE`

The 50-patient criterion reuses the existing project support convention. The three-parent / ten-patient criterion is a route-admission condition to reject single-group case-study behavior; it is not a claimed prevalence threshold.

---

## 13. Gate C — calibration killer control

Apply the Dev-frozen per-medication thresholds to Audit and recompute the exact same materiality conditions.

If calibrated signatures fail either Gate B materiality condition:

`STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION`

If the same conditions still hold:

`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`

---

## 14. Mechanical decision tree

```text
[Gate A: ATC-3 sibling-group support]
  >=3 groups with >=50 eligible Audit patients each?
  NO  -> INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT
  YES -> Gate B

[Gate B: raw structural signature]
  >=50 signature patients overall
  AND >=3 parents with >=10 signature patients each?
  NO  -> STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE
  YES -> Gate C

[Gate C: per-medication calibration killer control]
  same materiality conditions still hold on Audit?
  NO  -> STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION
  YES -> PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION
```

No descriptive subgroup, alternative threshold, alternative grouping, exact-count result, or extra error signature may override this tree.

---

## 15. Public-safe outputs

Gate execution writes restricted per-unit and Dev-threshold artifacts only under the 319 run root. They must not enter Git.

The public-safe summary may contain only aggregate values needed to audit the decision:

- frozen identities;
- Dev/Audit patient counts;
- number of sibling candidate groups;
- Gate A group-support count;
- eligible Audit unit count and patient count;
- raw SplitMassFN, DuplicateSiblingFP, and AnySignature unit/patient counts;
- number of raw signature parents meeting the 10-patient criterion;
- calibrated versions of the same aggregate counts;
- mechanical verdict.

Do not publish patient IDs, visit IDs, per-patient rows, score vectors, target prescriptions, or the per-medication threshold map.

---

## 16. PASS semantics

PASS means only:

> Under the frozen MoleRec ATC-3 validation setting, a material ATC-2-sibling output-structure error signature remained after Dev-only per-medication threshold calibration.

PASS does not authorize a method implementation. It authorizes only a later semantic-admission protocol after independent integrity audit.

---

## 17. FAIL / INCONCLUSIVE semantics

### `STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE`

The preregistered sibling-group split-mass / duplicate-sibling phenotype was not sufficiently material on the frozen raw output to justify a structured method route.

### `STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION`

The raw phenotype was sufficiently material, but a simple Dev-only per-medication threshold control removed materiality. The output-structure method story is unnecessary under the current setting.

### `INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT`

The current ATC-3 representation does not provide enough multi-group support for this route. For the current first-paper setting, do not rescue by changing vocabulary granularity after inspection.

---

## 18. Non-revival boundary

Any non-PASS outcome stops this route under the current representation. Do not rescue it by:

- rebuilding ATC-4 labels;
- defining groups from low co-occurrence;
- adding indication maps;
- adding DDI-derived grouping;
- trying alternative group-mass formulas;
- changing the `0.5` diagnostic threshold;
- adding more signatures;
- fitting group-specific thresholds;
- training a sequential/hierarchical/group-aware decoder;
- running another backbone or the test split.

A materially different future problem formulation would require a new literature review and new preregistration.
