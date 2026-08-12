# Final-five baseline execution preflight

Every active candidate remains `registered`. No baseline has executed on 319, and no result is Comparison Mode evidence.

| Candidate | Pinned source | Source-hosted role |
| --- | --- | --- |
| GAMENet | `ycq091044/SafeDrug@88ce5c3` | SafeDrug-main implementation |
| SafeDrug | `ycq091044/SafeDrug@88ce5c3` | SafeDrug-main implementation |
| MoleRec | `yangnianzu0515/MoleRec@dd5afaf` | Official implementation |
| RETAIN | `ycq091044/SafeDrug@88ce5c3` | SafeDrug-main implementation |
| LEAP-SafeDrug | `ycq091044/SafeDrug@88ce5c3` | SafeDrug-main implementation |

The four SafeDrug-main entries use one preprocessing, split, and evaluation suite. DMNC is pinned separately at `thaihungle/DMNC@3ce17a9`. MoleRec keeps its own source-native preprocessing and environment.

Before a real run, the 319 checkout, restricted data root, source checkouts, isolated Conda environments, GPU capacity, and disk capacity must pass the remote execution playbook. Store all patient data, generated datasets, environments, checkpoints, predictions, and logs outside Git.
