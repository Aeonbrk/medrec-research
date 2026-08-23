# Plans

## Completed: Active Tree Consolidation

- **Status**: completed on `2026-08-23`; the checked-out tree now retains only current protocol, archived-lineage identity, generic remote execution, and durable research evidence.
- **Plan**: `docs/plans/2026-08-23-active-tree-consolidation-plan.md`.
- **Scope**: removed SafeDrug-main runners and environments, MoleRec-only APIs, and retired HITL, Project Status, UI, review, and authority-control documentation. Git history remains the recovery layer.
- **Boundary**: historical SafeDrug-main run summaries and scientific failure records remain; no remote environment, data, checkpoint, or run artifact was deleted.

## Completed: SafeDrug Family Reproduction (SafeDrug, RETAIN, LEAP-SafeDrug) on 319

- **Status**: completed on `2026-08-23` as historical SafeDrug `main@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` Reproduction Mode evidence; concurrent 3-GPU execution completed for `safedrug` (GPU 2), `retain` (GPU 3), and `leap-safedrug` (GPU 4).
- **Historical implementation**: preserved in Git history. It repaired the shared `medrec-gamenet` environment on 319 (`971ad2bf...`), executed 50 training epochs, selected best checkpoints, ran 10 test rounds, and validated aggregate result artifacts for all three lanes.
- **Evidence**:
  - `safedrug`: Run `medrec-baseline-safedrug-20260822-132448-0bfb210f` (best epoch: 41), DDI $0.0589 \pm 0.0005$, Jaccard $0.5122 \pm 0.0031$, F1 $0.6687 \pm 0.0028$, PRAUC $0.7653 \pm 0.0027$, Avg Meds $20.5825 \pm 0.1611$.
  - `retain`: Run `medrec-baseline-retain-20260822-132548-abcbd1ce` (best epoch: 49), DDI $0.0851 \pm 0.0017$, Jaccard $0.4818 \pm 0.0025$, F1 $0.6425 \pm 0.0023$, PRAUC $0.7587 \pm 0.0019$, Avg Meds $19.6382 \pm 0.3093$.
  - `leap-safedrug`: Run `medrec-baseline-leap-safedrug-20260822-132647-545ede8a` (best epoch: 44), DDI $0.0705 \pm 0.0005$, Jaccard $0.4442 \pm 0.0030$, F1 $0.6068 \pm 0.0031$, PRAUC $0.6506 \pm 0.0035$, Avg Meds $18.9097 \pm 0.0782$.
- **Boundary**: these runs used 15,032 visits and a 112-medication vocabulary, not the paper's 14,995 visits and 131 medications. They remain truthful historical provenance but do not participate in future baseline selection, paper reproduction, or Comparison Mode.

## Accepted: SafeDrug Archived Single-Baseline Program

- **Status**: accepted on `2026-08-23`; SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the only active SafeDrug-family source and the common baseline for future innovation.
- **Plan**: `docs/plans/2026-08-23-archived-single-baseline-plan.md`.
- **Scope**: reuse the existing `gamenet`, `safedrug`, `retain`, and `leap-safedrug` IDs under one archived lineage; regenerate paper-matching preprocessing, add only the mechanical training-mode adaptation required by the archived entrypoints, run four independent GPU lanes, and compare aggregate results with SafeDrug Table 2.
- **Execution boundary**: no archived run is launchable until the exact paper aggregate counts pass, the training-mode adaptation is audited, and the archived environment succeeds. SafeDrug `main` receives no new registry identity or future run lane.
