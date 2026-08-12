# SafeDrug main four-model source preflight

The research owner selected `ycq091044/SafeDrug@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` for GAMENet, SafeDrug, RETAIN, and LEAP. The repository contains `src/GAMENet.py`, `src/SafeDrug.py`, `src/Retain.py`, and `src/Leap.py`.

All four entry points use the repository's generated records and vocabulary, partition the ordered records into two-thirds training, then equal test and evaluation partitions, and report the same medication-recommendation metric family. This creates one source-hosted four-model suite. It does not alter MoleRec's independent source identity.

The DMNC dependency is pinned separately at `thaihungle/DMNC@3ce17a9277bbeeb8125b588e86cc8aace67a0924` when the remote environment is created. Source checkouts, MIMIC data, generated artifacts, environments, checkpoints, and logs remain outside Git on 319.
