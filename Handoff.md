# Handoff: Idea 003 Gate 01 Closure and Next Direction

## Current state

Idea `003-prescription-relative-confidence` Gate 01 has completed formal execution on `319-lab`, passed independent integrity audit, and reached the authoritative research decision to terminate:

- **Idea ID**: `003-prescription-relative-confidence`
- **Idea Status**: `CLOSED (Gate 01 Falsified)`
- **Gate 01 Status**: `EXECUTED / FALSIFIED`
- **Formal Verdict**: `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE` (`TERMINATE_IDEA_003`)
- **Protocol**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md`](research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md)
- **Design Audit**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-design-integrity-audit.md`](research/ideas/003-prescription-relative-confidence/experiments/gate-01-design-integrity-audit.md) (`INTEGRITY_PASS`)
- **Integrity Audit**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-integrity-audit.md`](research/ideas/003-prescription-relative-confidence/experiments/gate-01-integrity-audit.md) (`INTEGRITY_PASS`)
- **Research Decision**: [`research/ideas/003-prescription-relative-confidence/research-decision.md`](research/ideas/003-prescription-relative-confidence/research-decision.md)
- **Failure Record**: [`research/memory/failures/prescription-relative-confidence-gate-01--no-incremental-relative-confidence.md`](research/memory/failures/prescription-relative-confidence-gate-01--no-incremental-relative-confidence.md)
- **Public Summary**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-summary.json`](research/ideas/003-prescription-relative-confidence/experiments/gate-01-summary.json)
- **Formal Run ID**: `gate-01-prescription-relative-confidence-20260902-233128`
- **Harness Revision**: `ac9dfe860bbce7a9a9620cf21836931136582055`
- **Test Split**: Strictly unindexed, unpredicted, and untouched.

## Executed 319 Run Summary

Formal execution was carried out on `319-lab-via-server` under `medrec-core-evaluator`:

- **Audit Cohort Support**: 7,740 candidates from 423 eligible patients ($N_{PB=1}=417$, $N_{PB=0}=423$, both $\ge 50$; $k(10\%)=774$, $k(20\%)=1,548$). Gate A passed.
- **Audit Policy Yields**:
  - `Random`: 31.37% (0.313695)
  - `ScoreOnly`: 56.85% (10%), 55.88% (20%), 54.87% (30%)
  - `StrongControl`: 57.49% (10%), 57.17% (20%), 55.30% (30%)
  - `RankAugmented`: 57.24% (10%), 56.91% (20%), 55.00% (30%)
  - `Oracle`: 100.0% across all budgets
- **Gaps & Bootstrap 95% CIs (1,000 patient-cluster replicates, seed `1203`)**:
  - `Oracle - StrongControl` (Gate B): $+42.51\%$ (10%, CI $[+39.04\%, +46.15\%]$); $+42.83\%$ (20%, CI $[+40.34\%, +45.78\%]$). Lower bounds strictly $> 0$; Gate B passed.
  - `RankAugmented - StrongControl` (Gate C): $-0.26\%$ (10%, CI $[-1.37\%, +1.19\%]$); $-0.26\%$ (20%, CI $[-0.65\%, +0.80\%]$). Lower bounds strictly $\le 0$; Gate C **FAILED**.

## Cumulative Knowledge Across Ideas 001, 002, 003

1. **Idea 001**: Direct DDI degree / tension pressure interaction adds zero incremental signal over recommender score ($Scalar - Score = 0.0\%$).
2. **Idea 002**: 1D score geometry quintile bin mapping collapses identically to monotonic score sorting ($Geometry - Score = 0.0\%$).
3. **Idea 003**: Within-prescription relative confidence ranking adds zero incremental signal beyond absolute score, prescription size, and train-only prevalence ($Rank - Control \le 0$).
4. **Core Insight**: Single-visit static prediction-time observables ($s, n_t, r_t, d_t$) and static marginal train prevalence ($p_{train}$) have been thoroughly falsified as sources of incremental false-positive signal.
5. **Unresolved Core Problem**: Substantial retrospective Oracle headroom ($>+42\%$) proves false positives are highly concentrated.

## Next Recommended Step (Idea 004 Direction)

- **Recommended Direction**: `004-longitudinal-prescription-novelty` (or `004-longitudinal-transition-verification`).
- **Rationale**: Investigate whether **patient-specific longitudinal history** (i.e. distinguishing repeat prescriptions previously administered to this specific patient vs novel drug initiations) provides reproducible incremental false-positive routing information beyond the `StrongControl` benchmark. Patient history is target-free, clinically grounded, and completely unexploited by static single-visit selectors.
- **Workflow**: Initialize Idea 004 scaffolding, perform literature grounding, draft preregistered Gate 01 protocol, conduct design audit, and freeze before execution.
