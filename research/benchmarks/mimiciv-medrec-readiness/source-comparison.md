<!-- markdownlint-disable MD013 -->

# Primary-source comparison for dual-dataset medication recommendation

The papers below were checked as primary publisher, DOI, PubMed, proceedings,
or author full-text sources. `UNKNOWN` means that the accessible primary text
did not expose the requested preprocessing detail; it is not an inference.
Reported paper statistics are not treated as comparable project results.

Most cited papers use older MIMIC-IV releases (often v2.0 or v2.2) and a
filtered 9,000-patient-scale cohort, whereas the present resource check is on
raw v3.1 and a much larger candidate rebuild. Release and cohort differences
are another reason to freeze a fresh manifest rather than copy paper counts.

| Work (primary source) | MIMIC-IV preprocessing / visit construction | Medication mapping / ATC | Split protocol | Vocabulary / DDI | Metrics | MICA-IV compatibility |
| --- | --- | --- | --- | --- | --- | --- |
| [KATMed](https://pubmed.ncbi.nlm.nih.gov/41621768/) | MIMIC-III/IV and eICU are used; accessible record says a SafeDrug-like preprocessing pipeline. Exact visit-row and chronology details: UNKNOWN. | NDC → ATC level 3 is stated. | Train/validation/test are stated; ratio and patient assignment: UNKNOWN. | Vocabulary size and DDI construction: UNKNOWN. | Accuracy, F1, DDCC-VR, and number of medications are reported. | INCOMPATIBLE as a direct contract: ATC3 and undisclosed split/visit rules; useful mapping/safety precedent only. |
| [RaVSNet](https://pubmed.ncbi.nlm.nih.gov/40679883/) | MIMIC-III/IV are used with relevance-aware visit similarity and longitudinal/transversal visit modeling; exact row construction: UNKNOWN. | Mapping level and source: UNKNOWN. | Split assignment: UNKNOWN in accessible abstract. | Vocabulary/DDI details: UNKNOWN. | Exact metric set: UNKNOWN in accessible abstract. | INCOMPATIBLE until full preprocessing is recovered; mechanism paper, not a protocol source. |
| [DPID](https://www.sciencedirect.com/science/article/pii/S095741742501406X) | MIMIC-III/IV are used with a dual-perspective encoder and iterative denoising; exact visit construction: UNKNOWN. | Drug graph is stated; mapping level/source: UNKNOWN. | Split protocol: UNKNOWN. | Vocabulary and DDI source: UNKNOWN. | Exact metric details: UNKNOWN in accessible record. | INCOMPATIBLE as a benchmark definition; retain as a method comparator only. |
| [HypeMed](https://doi.org/10.1145/3803851) ([full text](https://arxiv.org/html/2603.18459)) | MIMIC-III/IV/eICU; SafeDrug-style low-frequency filtering and a fewer-than-two-visits filter are stated. The reported MIMIC-IV surface is 9,036 patients, 20,616 visits, 1,892 diagnosis codes, and 4,939 procedure codes. | Standardized ICD/ATC is stated; exact ATC level and NDC mapping: UNKNOWN. | Train/validation/test assignment: UNKNOWN. Evaluation uses ten 80%-of-test bootstrap rounds with replacement, not a replacement for the split. | 131 MIMIC-IV medication concepts are reported; DDI ground-truth rate is 7.24%, while the DDI graph source/build is not specified in the cited passage. | Jaccard, F1, PRAUC, DDI, and number of medications; metrics are averaged across patients. | Partially reusable metric family and cohort evidence; INCOMPATIBLE as a frozen protocol until mapping/split details are independently implemented. |
| [Rx-Expert](https://www.sciencedirect.com/science/article/pii/S0957417426022839) | MIMIC-III/IV/eICU; multi-label D/P/history → medication task is stated, but exact visit construction: UNKNOWN. | Molecular/text drug features are used; normalization/ATC: UNKNOWN. | Split protocol: UNKNOWN. | Drug graph/DDI details: UNKNOWN. | Exact metric protocol: UNKNOWN in accessible record. | INCOMPATIBLE for MICA's no-extra-information benchmark; useful as a strong architecture reference. |
| [NLA-MMR, CIKM 2024](https://www1.se.cuhk.edu.hk/~hccl/publications/pub/CIKM%2724.pdf) | Full text states it follows DrugRec processing and uses MIMIC-III/IV visit records. | Target medication is ATC Third Level; DrugBank descriptions are added. | Full text states Train/Val/Test = 2/3, 1/6, 1/6. | MIMIC-III has 112 and MIMIC-IV 121 medication concepts in its processed surface; DDI source/fit is not specified in the cited preprocessing passage. | F1, Jaccard, PRAUC. | REUSABLE split-role and metric precedent; INCOMPATIBLE target/mapping because ATC3 plus extra drug text are not MICA-Core entitlement. |
| [ARMR, IJCAI 2025](https://www.ijcai.org/proceedings/2025/0871.pdf) | Full text says MIMIC-III/IV follow Chen et al. preprocessing; exact row mechanics are delegated to that source. | 131 medications at ATC Third Level. | Exact patient assignment is not specified in the cited passage. | DDI asset details are not specified in the cited passage. | Jaccard, F1, PRAUC averaged across patients. | REUSABLE metric and dual-dataset precedent; INCOMPATIBLE mapping level and insufficient split provenance. |

## What this comparison establishes

Recent papers confirm that MIMIC-IV is used for medication-set recommendation
and that 2/3–1/6–1/6 roles and Jaccard/F1/PRAUC are common precedents. They do
not establish one canonical MIMIC-IV preprocessing contract: ATC3 versus ATC4,
drug text/molecular inputs, cohort filters, split assignment, DDI assets, and
visit construction vary or are not exposed in the accessible primary text.

Therefore the project protocol deliberately freezes the MICA semantics itself:
current D/P plus strictly previous D/P/M visits, prescription-derived current
targets, patient-level split, dataset-native vocabularies, fixed MICA metrics,
and strict best-Dev-Jaccard selection. Literature rows are comparators and
implementation leads, not permission to splice incompatible artifacts.

## Sources and access notes

- [Official MIMIC-IV v3.1 resource](https://physionet.org/content/mimiciv/3.1/)
  defines the current credentialed release and hospital modules.
- [MIMIC-IV Scientific Data description](https://doi.org/10.13026/kpb9-mt58)
  is the release-level primary description.
- Exact details marked `UNKNOWN` require obtaining and reviewing the complete
  primary implementation or supplement; they are intentionally not guessed.
