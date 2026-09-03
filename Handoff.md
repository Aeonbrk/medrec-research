# Handoff: Idea 004 Gate 01 Execution & Decision

## Current state

Idea `004-co-selection-compatibility` has completed formal Gate 01 validation execution, independent integrity audit, and research decision. The preregistered decision tree resulted in an authoritative termination: `STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`.

- **Idea ID**: `004-co-selection-compatibility`
- **Idea Status**: `REJECTED / TERMINATED_AT_GATE_01`
- **Gate Protocol**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-co-selection-compatibility.md`
- **Design Audit**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-design-integrity-audit.md` (`DESIGN_INTEGRITY_PASS`)
- **Protocol Commit**: `a5f964be67f66852aba8dbfdbf2121b112046ae0`
- **Implementation Commit**: `8640ce521a942bd34daa2a5547c2e2db1febca6a`
- **Formal Run ID**: `gate-01-co-selection-compatibility-20260903-154343` on `319-lab`
- **Integrity Audit**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-integrity-audit.md` (`INTEGRITY_PASS`)
- **Research Decision**: `research/ideas/004-co-selection-compatibility/research-decision.md` (`STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`)
- **Failure Record**: `research/memory/failures/co-selection-compatibility-gate-01--no-incremental-co-selection-compatibility.md`
- **Public Summary**: `research/ideas/004-co-selection-compatibility/experiments/gate-01-summary.json`
- **Test Split**: strictly unindexed, unpredicted, and untouched
- **ccfa.yaml**: absent per repository conventions

## Scientific question & findings

$$
\boxed{\text{Does one train-only frequency-corrected co-selection statistic explain medication-level false-positive heterogeneity beyond the strongest simple frozen control?}}
$$

Under the frozen MoleRec validation setting, evaluating on 7,787 Audit candidates across 426 eligible patients (seed `2004` patient-disjoint split):

1. **Gate A (Audit Support)**: **PASS** ($N_{PB=1}=417 \ge 50$, $N_{PB=0}=426 \ge 50$, $k(10\%)=778$, $k(20\%)=1557$).
2. **Gate B (Oracle Headroom over Strong Control)**: **PASS** (Oracle achieves 100.0% yield; `Oracle - StrongControl` is $+38.43\%$ at 10% budget with 95% CI $[+33.87\%, +42.93\%]$; $+40.46\%$ at 20% budget with 95% CI $[+37.18\%, +43.61\%]$; both lower bounds $> 0$). Substantial retrospective headroom remains unexplained.
3. **Gate C (CoSelectionAugmented Incremental Yield over Strong Control)**: **FAIL** (`CoSelectionAugmented - StrongControl` is $+0.77\%$ at 10% budget with 95% CI $[-1.16\%, +2.50\%]$; $+0.06\%$ at 20% budget with 95% CI $[-0.68\%, +0.78\%]$; both lower bounds $\le 0$).

`StrongControl` ($u, c, f, g, u \cdot c, u \cdot f, u \cdot g$) again showed positive incremental headroom over raw score at the 20% budget ($+1.16\%$, 95% CI $[+0.14\%, +2.07\%]$), replicating the finding from Idea 003 that candidate prevalence and set size refine scores at broader review depths. However, adding train-only empirical NPMI co-selection compatibility $A_t(m)$ provided no statistically detectable incremental false-positive routing value.

## Scope & Non-Revival Boundary

- **Idea 004 is formally TERMINATED at Gate 01**.
- Gate 02 is `NOT_AUTHORIZED`.
- No alternative co-selection formula (PMI thresholds, Jaccard, lift, embedding cosine similarity, graph neural networks) is authorized to revive this hypothesis under the same information source.
- The failure is localized to the preregistered one-scalar train-only empirical NPMI co-selection compatibility observable under the frozen MoleRec setting and strong control.
- This result does not establish that multi-visit longitudinal patient history, structural graph information, patient-conditioned clinical covariates, or cross-model evidence are useless.

## Next CCFA Owner & Recommended Sequence

Execution agent work is complete. The next owner is `ccf-pipeline-orchestrator` to plan exploratory direction scouting.

Recommended sequence:

```text
ccf-pipeline-orchestrator
-> ccf-literature-monitor / ccf-literature-searcher
-> ccf-idea-optimizer (exploratory)
-> ccf-idea-reviewer (standard, explicit ranking)
-> ccf-idea-optimizer (standard, winner only)
-> ccf-experiment-designer
```
