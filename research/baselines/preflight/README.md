# Active baseline execution preflight

All five scientific baselines are `comparison_ready` under their recorded v1.1 Comparison Scope. See [`five-model-baseline-readiness-report.md`](five-model-baseline-readiness-report.md) and [`molerec-five-model-reproduction-report.md`](molerec-five-model-reproduction-report.md).

| Baseline | Pinned source | Role | Readiness |
| --- | --- | --- | --- |
| GAMENet | `ycq091044/SafeDrug@8deee38` | Archived paper reproduction / URP v1.1 comparison | `comparison_ready` |
| SafeDrug | `ycq091044/SafeDrug@8deee38` | Archived paper reproduction / URP v1.1 comparison | `comparison_ready` |
| RETAIN | `ycq091044/SafeDrug@8deee38` | Archived paper reproduction / URP v1.1 comparison | `comparison_ready` |
| LEAP-SafeDrug | `ycq091044/SafeDrug@8deee38` | Archived paper reproduction / URP v1.1 comparison | `comparison_ready` |
| MoleRec | `yangnianzu0515/MoleRec@dd5afaf` | Table 1 paper reproduction / URP v1.1 comparison | `comparison_ready` |

The five models use two Reproduction Programs (`baselines/safedrug_archived.py` and `baselines/molerec.py`) and seven reproduction lanes bound to the verified `medrec-molerec-table1` environment.

Before any new remote run, the 319 checkout, restricted data root, source checkouts, isolated Conda environments, GPU capacity, and disk capacity must pass the remote execution playbook. Store all patient data, generated datasets, environments, checkpoints, predictions, and logs outside Git.
