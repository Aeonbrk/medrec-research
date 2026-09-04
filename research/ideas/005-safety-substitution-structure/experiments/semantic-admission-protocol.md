<!-- markdownlint-disable MD013 -->

# Semantic Admission Protocol — Safety-Preserving Substitution Structure

## Mode

`ccf-experiment-designer / design`

Stage:

`Idea / Hypothesis Selection`

Status:

`DESIGNED_NOT_EXECUTED`

This protocol follows the completed Gate 01 result `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`. It does not authorize Gate 02, model training, group-aware decoding, test evaluation, or a clinical substitution claim.

## 1. Purpose

Gate 01 established one output-space fact under frozen MoleRec validation: material ATC-2-sibling output-structure signatures survive Dev-only per-medication threshold calibration.

Semantic Admission asks the next necessary question:

$$
\boxed{\begin{aligned}
&\text{Do the empirically supported target-to-sibling relations contain a material subset}\\
&\text{for which independent clinical evidence supports an alternative-treatment interpretation?}
\end{aligned}}
$$

The null explanation is intentionally strong:

> The observed structure is only taxonomy-level proximity or shared indication, not clinically defensible alternative choice at the repository's ATC-3 prediction resolution.

A failure terminates the substitution route before model development.

## 2. Frozen upstream evidence

Semantic Admission consumes only accepted Idea-005 Gate 01 artifacts:

- Gate 01 protocol commit: `95966eab6d018e34b6dae4a52271562826bb5b4d`;
- Gate 01 execution revision: `4bb07d3d0050070a811f7a4e307522906470e6f7`;
- Gate 01 decision commit: `aeb9b53599c3240ca84f1875a6be501f8ca8eb9d`;
- formal run: `gate-01-output-structure-signature-20260904-155810`;
- public verdict: `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`;
- frozen validation split: seed `2005`, 529 Dev / 530 Audit patients;
- test split: unindexed, unstaged, unpredicted, unevaluated, and untouched.

No new MoleRec inference is required for Semantic Admission.

## 3. Classification semantics

The executable medication vocabulary is the SafeDrug/MoleRec coarse `ATC3` representation obtained by truncating the upstream ATC4 mapping to four characters. The Gate 01 sibling parent is the first three characters, corresponding to the ATC 2nd-level pharmacological/therapeutic subgroup.

This hierarchy is a classification and identity primitive only:

$$
\text{same ATC-2 parent}\not\Rightarrow\text{therapeutic interchangeability}.
$$

WHO ATC documentation is admissible for code identity, hierarchy, and subgroup titles. It is not sufficient evidence for Semantic Admission.

## 4. Semantic candidate universe

Use the existing restricted Gate 01 Audit artifacts. Do not access test and do not rerun the model.

For every calibrated-policy `AnySignature` unit in one of the 20 Gate-01 high-support sibling groups, let $y_t$ be the unique observed ATC-3 target in that sibling group.

Define exactly one primary sibling candidate $a_t$ per unit.

### 4.1 SplitMassFN

Among siblings in the same parent excluding $y_t$, choose the medication with the largest frozen MoleRec score:

$$
a_t=\arg\max_{m\in G\setminus\{y_t\}}p_t(m).
$$

Tie-break by ATC-3 code ascending.

### 4.2 DuplicateSiblingFP

Among non-target siblings emitted by the Dev-frozen calibrated policy, choose the medication with the largest frozen MoleRec score:

$$
a_t=\arg\max_{m\in(\hat M_t^{cal}\cap G)\setminus\{y_t\}}p_t(m).
$$

Tie-break by ATC-3 code ascending.

Each semantic unit therefore contributes one directed class relation:

$$
y_t\rightarrow a_t.
$$

No alternative candidate-selection formula is authorized after semantic evidence is inspected.

## 5. Supported relation set

Aggregate directed relations only; no patient-level material enters Git.

For relation $r=(y\rightarrow a)$, compute:

- distinct Audit patients carrying $r$;
- unit count carrying $r$;
- ATC-2 parent.

A relation enters the semantic review set only if it occurs in at least 10 distinct Audit patients.

Let $P_{supported}$ be the distinct calibrated-signature patients with at least one such supported primary relation.

### Support concentration gate

Require both:

1. supported relations span at least 3 ATC-2 parents;
2. $|P_{supported}| / 394 \ge 0.50$.

If either condition fails:

`STOP_SEMANTIC_SIGNAL_TOO_DIFFUSE`

This is an efficiency and reproducibility gate: a route dominated by one-off class relations does not justify expensive semantic curation or method development.

## 6. Evidence hierarchy

Semantic review is source-based. Relation support counts are hidden from the semantic adjudicator until the evidence label is frozen.

### Tier A — qualifying admission evidence

At least one authoritative clinical source must explicitly position the two ATC-3 pharmacological/therapeutic subgroups, or their represented treatment classes at the same prediction resolution, as alternative treatment options for the same indication and overlapping clinical context.

Qualifying sources include:

- government or national clinical guidance;
- major specialty-society clinical practice guidelines;
- established health-system or professional formulary therapeutic-interchange guidance;
- authoritative evidence-based treatment protocols that explicitly present the compared classes as alternatives.

A Tier-A source must establish alternative positioning, not merely mention both therapies in the same disease chapter.

### Tier B — corroborating indication evidence

FDA labeling / DailyMed Structured Product Labels may establish that therapies share an approved indication and may document contraindications, warnings, route, and population restrictions.

Tier B evidence alone is not sufficient for admission.

### Tier C — identity and taxonomy only

WHO ATC and NLM RxNorm/RxClass may resolve:

- code hierarchy;
- ingredient or concept identity;
- pharmacologic class;
- ATC crosswalks.

Tier C evidence never establishes therapeutic alternatives by itself.

## 7. Naive semantic control

For each supported relation, record a separate `NAIVE_SHARED_INDICATION` label when Tier-B evidence shows at least one shared approved indication, regardless of alternative positioning.

This label is a negative control for semantic inflation.

The following inference is forbidden:

$$
\text{same ATC parent + shared indication}\Rightarrow\text{admissible substitute}.
$$

The final decision uses only strict admission, never the naive label.

## 8. Strict relation adjudication

Each supported directed relation receives exactly one frozen label:

- `ADMIT_ALTERNATIVE_CLASS_RELATION`;
- `REJECT_NOT_ALTERNATIVE`;
- `UNRESOLVED_INSUFFICIENT_EVIDENCE`.

### 8.1 ADMIT

Assign `ADMIT_ALTERNATIVE_CLASS_RELATION` only when all conditions hold:

1. code/class identity is resolved;
2. a Tier-A source explicitly supports alternative treatment positioning for the compared classes in the same indication and overlapping clinical context;
3. the relation is not merely complementary combination therapy, sequential escalation, rescue-after-failure, route-specific non-overlap, or disjoint disease-stage use;
4. the source supports the relation at the class resolution represented by the ATC-3 labels, rather than only one exceptional ingredient pair hidden inside otherwise heterogeneous classes.

### 8.2 REJECT

Assign `REJECT_NOT_ALTERNATIVE` when authoritative evidence shows that the classes are used for materially different indications/contexts, are normally complementary rather than alternative, or when class heterogeneity makes the ATC-3 relation too coarse to support an alternative-choice interpretation.

### 8.3 UNRESOLVED

Assign `UNRESOLVED_INSUFFICIENT_EVIDENCE` when mapping is incomplete or available sources do not support a class-resolution judgment. Unresolved relations do not count as admitted.

## 9. Semantic materiality decision

After all supported relation labels are frozen, restore their Gate-01 aggregate support counts.

Let $P_{admit}$ be distinct calibrated-signature Audit patients with at least one supported primary relation labeled `ADMIT_ALTERNATIVE_CLASS_RELATION`.

For each ATC-2 parent, count distinct Audit patients with at least one admitted primary relation in that parent.

Semantic Admission passes only if both conditions hold:

1. $|P_{admit}| / 394 \ge 0.25$;
2. admitted relations span at least 3 ATC-2 parents, each with at least 10 distinct admitted-relation patients.

### Decision tree

```text
[Semantic A: relation concentration]
  >= 50% of calibrated signature patients covered by supported relations
  AND >= 3 ATC-2 parents?
  NO  -> STOP_SEMANTIC_SIGNAL_TOO_DIFFUSE
  YES -> Semantic B

[Semantic B: strict alternative-treatment admission]
  >= 25% of calibrated signature patients covered by strict ADMIT relations
  AND >= 3 ATC-2 parents each with >= 10 admitted patients?
  NO  -> STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE
  YES -> PASS_SEMANTIC_ADMISSION_FOR_METHOD_DESIGN
```

The 25% floor is a hypothesis-selection materiality requirement, not a clinical prevalence claim and not a final-paper effect-size threshold.

## 10. Public-safe artifacts

The execution may produce the following Git-eligible artifacts after privacy and integrity audit:

```text
research/ideas/005-safety-substitution-structure/experiments/
  semantic-candidate-relations.json
  semantic-admission-ledger.md
  semantic-admission-summary.json
  semantic-admission-integrity-audit.md
```

`semantic-candidate-relations.json` may contain only public ATC codes, ATC titles, aggregate patient/unit counts, and parent codes. It must not contain patient IDs, visit IDs, raw score vectors, targets, or threshold maps.

`semantic-admission-ledger.md` records one row per supported relation with source links, evidence class, naive shared-indication label, strict adjudication, and a concise evidence rationale.

## 11. Integrity audit

After semantic labels are frozen, run `ccf-integrity-auditor` in:

`claim-audit + citation-audit + numeric-audit`

The audit must verify:

- every admitted relation has a qualifying Tier-A source;
- the cited source actually supports alternative positioning in overlapping context;
- WHO ATC / RxNorm evidence is not used as substitution proof;
- DailyMed shared indication alone is not promoted to strict admission;
- support counts reproduce the frozen Gate-01 restricted aggregate extraction;
- the mechanical decision follows the preregistered tree;
- test remains untouched.

## 12. Authorized interpretation

### PASS

`PASS_SEMANTIC_ADMISSION_FOR_METHOD_DESIGN` means only:

> A material, multi-parent subset of the empirically observed ATC-sibling output-structure relations is supported by independent authoritative evidence as alternative treatment structure at the repository's prediction resolution.

PASS authorizes formulation and review of a concrete group-aware method hypothesis. It does not authorize a clinical substitution system, test evaluation, or a claim of patient benefit.

### FAIL

`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE` means:

> The ATC-sibling output-structure phenotype is real, but the first clinically meaningful semantic interpretation required for the substitution method story is not sufficiently supported at the current prediction resolution.

The route terminates before model training. Do not rescue it with looser shared-indication criteria or a different taxonomy after inspecting results.

## 13. Source anchors

- WHO ATC classification: <https://www.who.int/tools/atc-ddd-toolkit/atc-classification>
- NLM RxNorm API: <https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html>
- DailyMed developer resources: <https://dailymed.nlm.nih.gov/dailymed/app-support.cfm>
- ASHP formulary / therapeutic-interchange guidance: <https://www.ashp.org/-/media/assets/policy-guidelines/docs/guidelines/gdl-pharmacy-therapeutics-committee-formulary-system.ashx>

## 14. Stop boundary

Semantic Admission is the only authorized next scientific task.

Do not in the same execution:

- access test;
- run another backbone;
- retrain MoleRec;
- implement hierarchical/group-aware decoding or loss;
- tune semantic thresholds after evidence inspection;
- treat shared indication as therapeutic interchange;
- begin publication experiments.
