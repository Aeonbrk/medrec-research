# Iterative Evidence Survivor Screen

Status: **DESIGN FROZEN / IMPLEMENTED / NOT EXECUTED**

This directory is the bounded survivor-discrimination round following the completed evidence-access architecture portfolio.

It does not search for a new architecture family. It tests whether the surviving `depth_reread` mechanism is stable enough to merit Paper Candidate review and whether fine code-level evidence remains causally important inside the final multi-hop computation graph.

## Starting evidence

The preceding portfolio established:

- `resolution_code - resolution_visit`: ΔJ `+0.011536`, ΔF1 `+0.010238`, ΔPRAUC `+0.007785`, ΔDDI `-0.005589`;
- `depth_reread - depth_state`: ΔJ `+0.004144`, ΔF1 `+0.003790`, ΔPRAUC `+0.005406`, ΔDDI `-0.000731`;
- `depth_reread` absolute Dev Jaccard `0.551259`;
- `temporal_med` was killed;
- `prediction_local` remains quarantined because its accuracy gain violated the frozen DDI guardrail.

Inspection of the committed computation graph shows that `depth_reread` already reads flattened fine-grained code evidence at every hop. Therefore `resolution_code` and `depth_reread` are not two modules awaiting an automatic A+B experiment. The current candidate already contains the fine-code substrate; this round performs final attribution and stability.

## Rank-1 scientific object

The candidate model preserves one decision state per medication and repeatedly acquires evidence from fine-grained longitudinal EHR memory:

```text
fine D/P/history-M evidence tokens
        ↓
static medication identities q_m
        ↓
medication-specific first evidence read
        ↓
131 medication decision states
        ↓
updated states re-query the same fine evidence memory
        ↓
second re-query
        ↓
medication-specific states remain separate until 131 logits
```

The paper-level novelty, if the model survives, is the complete computation graph. It is not a claim to have invented multi-hop memory reading, label-wise attention, or code-level attention.

## Closest-work boundary

Primary-source review before this screen establishes:

- SARMR, IJCAI 2021, DOI `10.24963/ijcai.2021/431`: multi-hop reading on a key-value memory for contextual patient representations. The query is a patient/admission state and the memory stores previous admission representations and medications.
- MRSC, CIKM 2021, DOI `10.1145/3459637.3482278`: selective-coverage multi-hop reading over historical-admission memory to derive patient representations.
- MeSIN, Knowledge-Based Systems 2021, DOI `10.1016/j.knosys.2021.107534`: selective code/sequence modeling with interactive recurrent structure, followed by globally fused patient representation.
- MHLAT, 2023, arXiv `2309.08868`: multi-hop label-wise attention for automatic ICD coding, so multi-hop label-specific attention itself is not new.

The remaining plausible distinction is medication-specific persistent states repeatedly reading fine EHR-code memory and remaining uncollapsed until the medication logits. A survivor requires a second closest-work audit before Paper Candidate Freeze.

## Frozen questions

### Q1 — Final-architecture resolution attribution

Does code-level evidence still matter once both arms use iterative medication-specific re-reading?

Control `reread_visit`:

```text
fine code evidence
→ medication-independent within-visit pooling
→ visit memory
→ medication-specific first read
→ 2 medication-specific re-read hops over visit memory
→ logits
```

Candidate `reread_code`:

```text
same fine code evidence
→ no within-visit pooling
→ code-token memory
→ medication-specific first read
→ 2 medication-specific re-read hops over code-token memory
→ logits
```

The candidate is required to be numerically equivalent to the preceding portfolio's canonical `depth_reread` path before training.

Frozen interpretation:

```text
ΔJ <= +0.002
→ CODE_RESOLUTION_NOT_INCREMENTAL_UNDER_REREAD

+0.002 < ΔJ <= +0.004
→ WEAK_CODE_RESOLUTION_UNDER_REREAD

ΔJ > +0.004 and supporting guardrails pass
→ CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE

ΔJ > +0.004 with guardrail failure
→ CODE_RESOLUTION_SIGNAL_WITH_COST
```

Supporting guardrails:

```text
ΔF1 >= -0.002
ΔPRAUC >= -0.002
ΔDDI <= +0.002
```

### Q2 — Multi-condition depth stability

The canonical condition from the preceding portfolio is retained as condition 0:

```text
canonical:
torch/cuda/python random = 1203
numpy = 2048
```

Three additional conditions are frozen prospectively before training:

```text
stability_1:
torch/cuda/python random = 1204
numpy = 2049

stability_2:
torch/cuda/python random = 1205
numpy = 2050

stability_3:
torch/cuda/python random = 1206
numpy = 2051
```

They are deterministic offsets from the canonical convention, not selected using performance.

For each new condition:

```text
depth_state
vs
depth_reread
```

uses identical information, parameters, optimization and model selection.

`STABLE_DEPTH_REREAD` requires across all four conditions (canonical + 3 new):

```text
4 / 4 ΔJ > 0
at least 3 / 4 ΔJ > +0.002
mean ΔJ > +0.004
mean ΔF1 >= -0.002
mean ΔPRAUC >= -0.002
mean ΔDDI <= +0.002
```

If all four deltas are positive and mean ΔJ is `> +0.002` but the strict criterion is not met:

```text
POSITIVE_BUT_SUBTHRESHOLD_DEPTH_STABILITY
```

Otherwise:

```text
UNSTABLE_DEPTH_REREAD
```

No seed may be added, removed, replaced or rerun based on its observed score.

## Frozen DEVELOPMENT protocol

```text
profile: mimic-iii-canonical-131-paper-dev-v1
Train: 4,233 patients / 10,489 visits
Dev: 1,004 patients / 2,130 visits
Test: SEALED

epochs: 60 complete epochs
batch: 16 visits
optimizer: AdamW
lr: 1e-4
weight decay: 1e-4
betas: 0.9 / 0.999
eps: 1e-8
clip: 5.0
loss: BCE + 0.05 * normalized DDI penalty

selection:
complete Dev after every epoch
threshold grid 0.05 ... 0.95
joint checkpoint / threshold by patient-macro Jaccard
native-default tie-break 0.35
```

No Test, HPO, extra seed, extra epoch, safety reranker, set decoder or compound model is authorized.

## GPU assignment

```text
GPU 0  resolution_visit_canonical
GPU 1  resolution_code_canonical
GPU 2  depth_state_s1
GPU 3  depth_reread_s1
GPU 4  depth_state_s2
GPU 5  depth_reread_s2
GPU 6  depth_state_s3
GPU 7  depth_reread_s3
```

The canonical depth pair is not rerun; it is consumed from the preceding portfolio's committed `result.json`.

## Routing after completion

If depth is strictly stable and fine-code resolution remains material:

```text
PROMOTE_FINE_CODE_REREAD_TO_PAPER_CANDIDATE_REVIEW
```

If depth is strictly stable but code resolution becomes weak/nonincremental under rereading:

```text
PROMOTE_REREAD_WITH_RESOLUTION_SIMPLIFICATION_REVIEW
```

If depth is directionally positive but below the strict stability bar:

```text
HOLD_REREAD_NO_PAPER_PROMOTION
```

If depth is unstable:

```text
RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE
```

Promotion means closest-work review, comparator positioning, decisive ablations and second-surface development. It does not authorize Test.

## Decision-relevant preflight

The preflight must verify:

- clean immutable source revision;
- frozen snapshot/split/target hashes;
- exact parameter and initialization matching within each new pair;
- finite CUDA forward/backward;
- active pairwise mechanism on history-bearing rows;
- exact state and forward equivalence between `reread_code` and the preceding `depth_reread` implementation under the canonical condition.

A scientific run is not launched if preflight fails.
