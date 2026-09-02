# Handoff: Idea 003 Gate 01 Active State (Prescription-Relative Confidence)

## Current state

The active research focus is Idea `003-prescription-relative-confidence`, Gate 01:

- **Idea ID**: `003-prescription-relative-confidence`
- **Idea Status**: `SELECTED`
- **Gate 01 Status**: `Gate 01 DESIGNED / FROZEN` (Execution Status: `NOT EXECUTED`)
- **Protocol**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md`](file:///Users/oian/Codes/master/medrec-research/research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md)
- **Design Integrity Audit**: [`research/ideas/003-prescription-relative-confidence/experiments/gate-01-design-integrity-audit.md`](file:///Users/oian/Codes/master/medrec-research/research/ideas/003-prescription-relative-confidence/experiments/gate-01-design-integrity-audit.md) (`INTEGRITY_PASS`)
- **Scientific question**: Among DDI-active medications predicted by frozen MoleRec, does within-prescription relative confidence position contain reproducible incremental false-positive routing information beyond a strong simple control built from absolute medication score, predicted prescription size, and train-only medication prevalence?
- **Next CCFA owner / Phase**: P0 State & Protocol Verification, followed by P1 Idea-Local Implementation.

## Preserved Historical States

- **Idea 001**: Closed and terminated (`TERMINATE_CURRENT_TENSION_ROUTE`); Gate 01 `pass`, Gate 02 `STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL`, Gate 03 `NOT_AUTHORIZED`.
- **Idea 002**: Closed and terminated (`TERMINATE_IDEA_002`); Gate 01 `STOP_NO_INCREMENTAL_SCORE_GEOMETRY` (Dev order-equivalent), Gate 02 `NOT_AUTHORIZED`. Failure memory recorded in `research/memory/failures/score-geometry-gate-01--no-incremental-score-geometry.md`.
- **Test Split**: Strictly unindexed, unpredicted, and untouched.

## Gate 01 Scientific Contract

1. **Candidate Universe**: $\mathcal{Q}_t = \{m \in \hat{M}_t : d_t(m) > 0\}$. Revision operator $R_0(\hat{M}_t, m) = \hat{M}_t \setminus \{m\}$. Outcome $Y^{PB}_{t,m} = \mathbf{1}[m \notin M_t]$.
2. **Observable**: Mid-rank within predicted prescription $r_t(m) = \frac{|\{j \in \hat{M}_t : s_t(j) > s_t(m)\}| + 0.5 \cdot |\{j \in \hat{M}_t \setminus \{m\} : s_t(j) == s_t(m)\}|}{n_t - 1}$. Guaranteed $n_t \ge 2$.
3. **Train Prevalence**: Smoothed $p_{train}(m) = (C_{train}(m) + 1) / (V_{train} + 2)$ using eligible training visits only. Restricted data, never committed.
4. **Controls & Models**:
   - $u = 1 - s_t(m)$, $c = \log(1 + n_t)$, $f = \log(p_{train}(m) / (1 - p_{train}(m)))$.
   - `StrongControl`: $[u, c, f, u \cdot c, u \cdot f]$.
   - `RankAugmented`: $[u, c, f, u \cdot c, u \cdot f, r_t(m)]$.
5. **Estimator**: Ridge linear probability model $\min_{\beta_0, \beta} \sum_{dev} (Y^{PB} - \beta_0 - x^T \beta)^2 + 10^{-6} \|\beta\|^2$ fit strictly on Dev.
6. **Split Discipline**: Seed `2003` shuffle over validation patients $0 \dots 1058$. Dev: 529 patients, Audit: 530 patients. Patient-disjoint.
7. **Ranking Tie-Breakers**:
   - `StrongControl` & `RankAugmented`: (1) linear risk $\downarrow$, (2) frozen score $\uparrow$, (3) medication code $\uparrow$, (4) `patient_order` $\uparrow$, (5) `visit_order` $\uparrow$.
   - `ScoreOnly`: (1) frozen score $\uparrow$, (2) medication code $\uparrow$, (3) `patient_order` $\uparrow$, (4) `visit_order` $\uparrow$.
8. **Budgets & Inference**: Primary budgets 10%, 20%; secondary 30%. Patient-cluster bootstrap (1,000 replicates, seed `1203`, 95% CI).
9. **Decision Tree**:
   - Gate A: Audit support ($\ge 50$ $Y^{PB}=1$ patients, $\ge 50$ $Y^{PB}=0$ patients).
   - Gate B: LowerCI95(Oracle - StrongControl) > 0 at both 10% and 20%. If fail $\to$ `STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL`.
   - Gate C: LowerCI95(RankAugmented - StrongControl) > 0 at both 10% and 20%. If pass $\to$ `PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`, else $\to$ `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`.

## Immediate Execution Workflow

- **P0**: State & protocol verification, remote 319 preflight.
- **P1**: Idea-local implementation of `stage_gate01_inputs.py` and `run_prescription_relative_confidence_gate.py`.
- **P2**: Focused synthetic verification (`pytest`, lint, format).
- **P3**: Commit implementation and record `FORMAL_HARNESS_REVISION`.
- **P4**: Single formal 319 execution, generating restricted run data and public-safe `gate-01-summary.json`.
- **P5**: Independent CCFA integrity audit (`gate-01-integrity-audit.md`).
- **P6**: Authoritative research decision (`research-decision.md`).
