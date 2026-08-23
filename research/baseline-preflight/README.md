# Active baseline execution preflight

Every active baseline remains `registered`. No archived result is Comparison Mode evidence.

| Baseline | Pinned source | Role |
| --- | --- | --- |
| GAMENet | `ycq091044/SafeDrug@8deee38` | Archived paper-reproduction implementation |
| SafeDrug | `ycq091044/SafeDrug@8deee38` | Archived paper-reproduction implementation |
| RETAIN | `ycq091044/SafeDrug@8deee38` | Archived paper-reproduction implementation |
| LEAP-SafeDrug | `ycq091044/SafeDrug@8deee38` | Archived paper-reproduction implementation |

The four SafeDrug-family entries use one archived preprocessing, split, and evaluation suite. They are distinct model lanes, not four source authorities. No second external baseline lineage participates in the active registry.

Before a real run, the 319 checkout, restricted data root, source checkouts, isolated Conda environments, GPU capacity, and disk capacity must pass the remote execution playbook. Store all patient data, generated datasets, environments, checkpoints, predictions, and logs outside Git.
