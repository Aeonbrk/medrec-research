<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Audit — Idea 008

## Audit status

- **Audit owner**: `ccf-integrity-auditor`
- **Audit mode**: pre-execution design / entitlement / leakage / decision-rule integrity
- **Starting revision**: `5476ae66458a29fdca21bd75c153a162d91fc5b9`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Idea**: [`../README.md`](../README.md)
- **Protocol state audited**: `DESIGNED_NOT_EXECUTED`
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact
- **Verdict**: `DESIGN_INTEGRITY_FAIL`

No Gate-01 result exists at audit time. This audit asks only whether the frozen protocol is an executable, leakage-safe, equal-entitlement falsification test of the admitted BudgetSet mechanism.

The protocol is not execution-ready. The blockers below are bounded protocol-definition defects; none requires a new architecture, solver family, loss, dataset, backbone, budget sweep, or scientific rescue.

## Blocking findings

### B1 — The frozen BudgetSet update dropped the admitted explicit base-score residual anchor

**Protocol location**: Section 5.2, `BudgetSet definition -> Learned heads`.

The admitted formulation for this audit is

$$
\Delta_i^{(t)}=u_i-\lambda_i^{(t)}c_i^{(t)},
$$

$$
z_i^{(t+1)}=s_i+\Delta_i^{(t)}.
$$

The Gate protocol instead freezes

$$
z_i^{(t+1)}=u_i-\lambda_i^{(t)}c_i^{(t)}.
$$

This is a material mechanism change. The frozen backbone score is no longer an explicit residual anchor; the learned utility head becomes the complete recommendation utility score. A Gate outcome could therefore reflect learning a replacement recommendation scorer rather than refining the frozen backbone score under residual-budget marginal DDI pricing.

**Failure caused**: a BudgetSet gain or failure would no longer have the admitted interpretation, and comparison to the frozen-score Greedy killer would mix residual set refinement with learned utility replacement.

**Minimum correction**: restore the explicit residual anchor in the learned score update,

$$
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)}.
$$

Apply the same deterministic `+s_i` anchor to the Independent learned control so the learned-family comparison retains equal score anchoring. No other architecture change is required.

### B2 — `e_i` is not the backbone quantity described by the protocol

**Protocol location**: Sections 2.1, 5.2, and 8.

The protocol states that `e_i` is a frozen per-medication embedding tensor already consumed by the `molerec-embedding` predictor and read from the qualified checkpoint. The pinned MoleRec implementation does not contain such a medication-embedding parameter. Its `self.embeddings` are diagnosis/procedure embeddings; the medication representation consumed by `score_extractor` is `molecule_embeddings`, generated during each forward pass. That tensor depends on the patient query through `substruct_weight`. The repository Comparison adapter exports final vocabulary probabilities, not that internal representation.

**Failure caused**: an implementation could choose materially different tensors as `e_i`—for example global molecular embeddings, substructure embeddings, or the patient-conditioned final molecule representation—while all still appear superficially compatible with the prose. Learned capacity and patient information would differ, so the killer comparison would not have one frozen information entitlement.

**Minimum correction**: freeze one exact backbone quantity and extraction point. The smallest correction is to define `e_i(x)` as the frozen pinned MoleRec `molecule_embeddings[i]` tensor immediately before `score_extractor` for visit `x`, captured from the same no-gradient forward pass that produces `s_i`, and supplied identically to BudgetSet and Independent. No other MoleRec internal representation may be substituted after results are observed.

### B3 — The Gate01-Dev / Gate01-Audit partition is not mechanically reproducible

**Protocol location**: Section 2.2.

The protocol freezes salt `idea008-gate01-v1` and a lower-half / upper-half hash split, but it does not freeze the hash function, serialized patient identifier, byte/string construction, or boundary computation.

**Failure caused**: different legitimate implementations can create different Dev/Audit memberships, changing checkpoint/hyperparameter selection and the one-shot Audit result.

**Minimum correction**: freeze one exact patient-only formula, analogous to existing project split contracts, including the precise identifier, hash algorithm, string construction, numeric conversion, and `u < 0.5` versus `u >= 0.5` boundary. Preserve patient-disjointness and do not inspect target/model outcomes while constructing the split.

### B4 — Greedy+1Swap is undefined for reachable `K_x < 2` cases

**Protocol location**: Sections 3 and 7.

Section 3 correctly defines pairwise risk and marginal DDI as zero when `K_x < 2`, but Section 7 defines Greedy construction only for `K_x >= 2`. The protocol nevertheless requires exact `K_x` output for every method and every visit.

**Failure caused**: implementation behavior for `K_x=0` or `K_x=1` is left open, so exact-cardinality compliance and composition statistics can differ across implementations.

**Minimum correction**: freeze `K_x=0 -> empty set`; freeze `K_x=1 -> highest frozen s_i candidate`, with medication-code ascending as final tie-break. Budget feasibility is automatic because pairwise DDI is zero.

### B5 — Learned checkpoint selection and patience semantics are not uniquely executable

**Protocol location**: Section 6.

The protocol freezes a 30-epoch ceiling, patience 5, four configurations, three seeds, and a seed-mean lexicographic Dev rule. It does not specify whether checkpoint epoch is selected independently per seed or jointly across matched seeds, what constitutes one patience event, or how checkpoint selection is nested relative to configuration selection.

**Failure caused**: two implementations can select different checkpoints and therefore different Audit models while both following the stated grid and lexicographic criteria.

**Minimum correction**: freeze one checkpoint-selection procedure with evaluation cadence, seed aggregation, patience counter, checkpoint tie-breaking, and the ordering between checkpoint and configuration selection. BudgetSet and Independent must use exactly the same procedure.

### B6 — Gate-level aggregation, frontier bootstrap, and seed semantics are not fully frozen

**Protocol location**: Sections 10.2, 10.3, 11, and 12.

The following quantities can materially change PASS/KILL but do not yet have one executable definition:

- whether target-compliance means are visit-weighted, patient-weighted, seed-mean, or visit-by-seed pooled;
- how `R_L`, `R_M`, and `R_H` aggregate the three learned seeds;
- whether composition-change denominator includes `K_x=0` visits;
- how composition-change rates aggregate learned seeds;
- whether each patient-cluster bootstrap replicate recomputes all operating-point utilities/risks and re-evaluates the frontier `max`, or freezes the full-Audit comparator before resampling;
- for Independent, whether seed-specific frontier gaps use matched Independent seed `k` or the three-seed aggregate control frontier;
- whether "favorable sign" in the `2/3` seed rule means `G_{C,k}>0` or material `G_{C,k}>=0.005`.

**Failure caused**: the same stored predictions can produce different target-compliance, responsiveness, composition-response, CI, and seed-fragility verdicts depending on implementation choices made after seeing data.

**Minimum correction**: freeze one common aggregation contract before execution. It must name the mean unit, learned-seed aggregation, composition denominator, exact set-change predicate, full bootstrap statistic including within-replicate frontier recomputation or a predeclared fixed comparator, matched-seed semantics for Independent, and the exact numeric definition of a favorable seed.

### B7 — Primary terminal-verdict precedence is not explicit

**Protocol location**: Sections 4 and 13.

The protocol defines `STOP_NO_BASE_DDI_HEADROOM` plus multiple ordered-looking kill/stop rules, but it does not explicitly state that Section 13 is evaluated top-to-bottom or otherwise freeze precedence when multiple conditions hold. `INCONCLUSIVE_STOP` can also coexist with a later killer on another comparison.

**Failure caused**: one run can legitimately satisfy multiple terminal labels, allowing the primary verdict to be chosen after results are known.

**Minimum correction**: freeze a single primary precedence order covering mechanical invalidation, no-headroom stop, target semantics, budget response, composition response, Greedy killer, Independent killer, seed fragility, inconclusive evidence, and PASS. Secondary triggered reasons may still be reported.

## Scientific-identity audit

`FAIL` because of B1.

The admitted scientific object remains narrow and otherwise preserved:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

The protocol must test that object without replacing the frozen recommendation utility scorer.

## Iterative-mechanism audit

`PASS`.

With `T=2`, the written recurrence computes `q^(1)` from iteration 0 and then iteration 1 recomputes both `c_i(q^(1))` and `rho^(1)` before producing `z^(2)`. The second step is not stale with respect to the initial composition.

## Mathematical-domain audit

`PASS`.

For `K_x < 2`, the protocol defines hard-set DDI, relaxed pair-risk, and marginal DDI as zero. For `K_x >= 2`, the derivative identity

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q)
$$

is correct for symmetric `D` under the frozen normalization. The protocol does not claim arbitrary relaxed `R_DDI(q)` lies in `[0,1]`, and `rho` is consistently called relaxed surrogate constraint slack.

## Backbone / interface audit

`FAIL` because of B2.

The registry correctly pins MoleRec at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, marks it Comparison-ready, and registers the `molerec-embedding` lane. The pinned model can provide the 131 pre-threshold logits and uses the repository DDI asset. The unresolved interface defect is only the exact definition/extraction of `e_i`.

Backbone weights remain frozen; no Gate-01 backbone tuning is authorized.

## Candidate-pool / cardinality audit

`FAIL` only for the `K_x < 2` Greedy execution gap in B4.

The common 131-medication candidate universe, Frozen-Base-derived `K_x`, prohibition on ground-truth count, exact Top-K requirement, and deterministic score tie-break are otherwise correctly frozen. No method receives candidate retrieval or method-specific filtering.

## Budget-construction audit

`PASS`.

`r_train` and `{b_L,b_M,b_H}` use Gate01-Train only. No Dev/Audit statistic selects budgets, and no post-result target expansion is allowed. The combination of no-headroom stop, achieved-DDI reporting, target-compliance kill, and Greedy minimum-violation fallback is sufficient for this bounded Gate; no exact feasibility solver is required before execution.

## Killer 1 fairness audit

`PASS_WITH_BLOCKER_B4`.

Greedy receives the same `s`, `D`, 131-candidate pool, `b`, and `K_x`; the construction, violation-reduction phase, feasible utility-improvement phase, and final tie hierarchy are deterministic for `K_x >= 2`. The protocol does not artificially weaken the control by requiring a non-equivalent solver family. Execution still requires the explicit `K_x=0/1` branch in B4.

## Killer 2 fairness audit

`PASS_WITH_BLOCKERS_B1_B2`.

Independent receives the same frozen patient-conditioned score, requested budget, candidate pool, cardinality, medication representation, optimizer/objective, grid, and seeds, plus Train-only static DDI summaries. It is expressly denied `q^(t)`, current-set marginal cost, relaxed residual slack, and iterative feedback. Its static scalar inputs make the control no weaker in learned input capacity. The learned-family score anchor and `e_i` identity must first be corrected by B1/B2.

## Fixed-lambda audit

`PASS`.

The six-value lambda support is frozen, calibration is Train-only for each requested target, Dev/Audit never selects lambda, and support cannot expand after seeing results. It remains supporting evidence rather than a replacement for either primary killer.

## Objective / tuning audit

`FAIL` because of B5.

The common BCE-with-logits objective, DDI hinge term, cardinality penalty, Train labels, LR/eta grid, three matched seeds, AdamW settings, and no-rescue-loss boundary are otherwise fair and sufficiently narrow. Audit data are not authorized for selection.

## Frontier / statistics audit

`FAIL` because of B6.

The practical margins and patient-clustered bootstrap are appropriate for a hypothesis-selection Gate, but the statistic must be made unique before Audit is opened. Deterministic controls must remain deterministic and may not be duplicated as artificial seeds.

## Target / composition-response audit

`FAIL` because of B6.

The numerical compliance tolerances and adjacent responsiveness margins are frozen, but the aggregation unit, learned-seed aggregation, and composition-change denominator must be explicit before they can support a mechanical PASS/KILL decision.

## PASS / KILL determinism audit

`FAIL` because of B7.

All intended terminal categories are present, but the primary-verdict precedence must be explicit before execution.

## Quarantine audit

`PASS`.

The protocol neither requires nor authorizes G3/G4, R0 Holdout, or the historical project test. Gate01-Audit is an Idea-local split of the canonical Validation partition and remains unopened until Train/Dev selection is frozen.

## Verdict

`DESIGN_INTEGRITY_FAIL`

The design should not be executed in its current form. The minimum correction is a protocol-only amendment that closes B1-B7 without changing the admitted mechanism, adding methods, or expanding the experiment.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.0: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: bounded protocol correction for B1-B7 only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
