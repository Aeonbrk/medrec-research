<!-- markdownlint-disable MD013 -->

# MICA-v2 screen: accuracy and safe-decision extensions

Status: implementation, primary-source collision screen, preflight, and the
six complete Train/Dev lanes are finished.  Public-safe aggregate evidence is
in [`result.json`](result.json).
This is an additive exploratory prototype.  It does not alter the frozen
`research/prototypes/mica/` attribution experiment, create Idea 009, open a
formal Gate, or make a novelty claim.

## Frozen starting point

The authoritative starting revision is fetched from GitHub `origin/main` before
implementation.  The expected starting revision is
`dc6a7f2f9084ff51902be6674650ce36947ea6e8`; the actual value and the immutable
implementation revision are recorded in `result.json` after execution.

The validated MICA-Core anchor is DrugQuery:

```text
Dev Jaccard = 0.5422441561
F1          = 0.6950055191
PRAUC       = 0.7927301263
DDI         = 0.0762996360
AvgMed      = 19.9535
```

The prior attribution conclusion remains frozen:
`PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY`.  Early conditioning
and late FiLM are not revisited here.

## Literature collision boundary

This is a short primary-source mechanism check, not an exhaustive novelty
review.  The checked sources establish the following occupied neighboring
families:

| Source | Mechanism observed | Boundary for this screen |
| --- | --- | --- |
| [DrugDoctor, Briefings in Bioinformatics 2024](https://academic.oup.com/bib/article/25/6/bbae464/7765457) | Visit-level disease/medication cross-attention and historical prescription use | FineHistory and DualEvidence are empirical MICA controls, not claims of inventing drug-aware attention. |
| [SSPNet, IJCAI 2025](https://www.ijcai.org/proceedings/2025/1052) | Set-structured clinical encoding and permutation-consistent medication-set decoding | Set handling and set prediction are established. |
| [KERL, Information Processing & Management 2025](https://www.sciencedirect.com/science/article/pii/S0306457325001050) | Knowledge-enhanced patient representation and dual-path drug representation | No external knowledge or molecular branch is introduced here. |
| [FLAME, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/44a1f7e0a1fe7867f586b10739a0c26a-Abstract-Conference.html) | Sequential add/remove list generation, GRPO, and DDI reward shaping | SafeRank is simultaneous fixed-cardinality SafeSwap plus pairwise ranking, not sequential generation or GRPO. |
| [HeteroMed, Health Information Science and Systems 2026](https://pubmed.ncbi.nlm.nih.gov/41567975/) | Heterogeneous medical graph, expansion/inheritance decoder, expected DDI regularizer | No heterogeneous graph, copy/add decoder, or expected-DDI regularizer is imported. |
| [GraphDiffMed, arXiv 2605.20188](https://arxiv.org/abs/2605.20188) | Differential attention with pharmacological graph priors | No graph prior or differential-attention block is introduced. |
| [GRAIN, arXiv 2608.00098](https://arxiv.org/abs/2608.00098) | Ingredient-level DDI/co-prescription modeling and proportional safety control | The screen keeps the exact 131 drug-code vocabulary and static DDI matrix. |
| [Decision-Focused Learning through Learning-to-Rank, ICML 2022](https://proceedings.mlr.press/v162/mandi22a.html) | Pointwise, pairwise, and listwise ranking surrogates for decision-focused learning | SafeRank uses this established adjacent paradigm with a new bounded medication candidate construction. |
| [DFF, AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/34891) | Decision-focused fine-tuning with a trust-region bias correction | SafeRank does not copy DFF's trust-region fine-tuning. |
| [FSNet, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/3874e2be479a9d4e94d4514046c1f934-Abstract-Conference.html) | Feasibility-seeking neural optimization step | SafeSwap is a deterministic discrete decoder, not FSNet. |

Medication-specific attention, fine-grained history, current/history paths,
generic set prediction, DDI losses, and decision-focused ranking are therefore
treated as prior art or adjacent primitives.  The purpose here is to test a
coherent synthesis around the already validated DrugQuery base.

## Canonical data and entitlement

Use only the existing MoleRec-compatible snapshot
`molerec-table1-c721-www23` and Train/Dev root
`gate01-train-dev-5752596a-20260913a`:

```text
Train: 4233 patients, 10489 visits
Dev:   1004 patients,  2130 visits
Vocabulary: exact canonical 131 medication IDs (0..130)
```

Current diagnosis/procedure codes are inputs.  Current medication labels are
loss/evaluation targets only.  History is the strict prefix of preceding
observed visits.  No future visits, target-derived features, molecular data,
retrieval, persistent medication state, or held-out data are used.

## Frozen common configuration

All six lanes use one seed (`20260914`), 131 medications, width 128, two
clinical attention blocks, four heads, FFN width 256, batch 16, and 60 complete
epochs.  Training is AdamW with learning rate `3e-4`, weight decay `1e-4`,
betas `(0.9, 0.999)`, epsilon `1e-8`, global gradient clipping `5.0`, and
`BCE + 0.05 * normalized DDI penalty`.  The ordinary decoder is probability
`>= 0.35`; SafeRank uses SafeSwap.  Checkpoint selection is highest complete-Dev
Jaccard with strict improvement and earliest exact tie.  All arithmetic is
float32, TF32 is off, and cuDNN is deterministic.

## Six lanes

The single runner accepts exactly:

```text
--variant core
--variant fine_history
--variant dual_evidence
--variant safe_rank
--variant self_only
--variant set_context
```

### Core

Re-runs the exact DrugQuery computation from the completed MICA implementation:

```text
X → T → medication-specific query pooling → existing conditioner → head
```

The new Core is a common-revision anchor.  If its Dev Jaccard differs from the
historical DrugQuery by more than `0.002`, absolute downstream comparisons are
not interpreted as clean.

### FineHistory

Only preceding-visit token granularity changes.  Every distinct historical
diagnosis, procedure, and medication code is one typed token with its ordinal
visit lag.  Empty modalities retain an explicit zero-code typed token.  Current
D/P tokens, the shared encoder, medication query, conditioner, head, objective,
decoder, and update budget are unchanged.  No history or code truncation is
allowed, and the parameter count must equal Core.

### DualEvidence

Current and historical coarse-token streams are encoded separately by the same
`T` instance.  Each medication queries both streams with the existing Q/K/V
readout, then one shared `384 → 1` gate fuses the contexts.  First visits have
zero history context and gate exactly one.  The target never enters either
stream, and no auxiliary loss or second encoder is present.

### SafeRank and SafePTO

SafeSwap preserves the ordinary threshold cardinality `K`.  It starts at exact
top-`K` logits with canonical medication-order tie breaking, then greedily
performs deterministic 1-for-1 swaps to reach

```text
B(K) = floor(0.065 * K * (K - 1) / 2)
```

unsafe pairs, followed by utility-improving budget-feasible swaps.  If no
reducing swap exists, it returns the minimum-DDI set reached by that path.  The
budget, threshold, and cardinality are fixed; no fallback or Dev tuning exists.

SafePTO is Lane-0 Core's selected checkpoint decoded with SafeSwap.  SafeRank
keeps the same model and decoder but adds `0.1 * L_rank` to the base objective.
For each Train example, detached logits produce the observed target set,
ordinary threshold set, and SafeSwap set.  Candidate pairs are ranked by

```text
Q(S,Y) = Jaccard(S,Y) - max(0, DDI_rate(S) - 0.065)
Gθ(S) = mean_m [1[m∈S] log σ(u_m) + 1[m∉S] log σ(-u_m)]
```

Only pairs with strictly ordered `Q` contribute logistic softplus ranking loss.
SafeSwap itself is never differentiated through, and inference has no target.

### SelfOnly and SetContext

Both expose the existing medication state

```text
h_m = GELU(Linear_384_to_128([c_m, e_m, c_m ⊙ e_m]))
```

and add one identical pre-norm four-head self-attention/FFN block with width
128, FFN 256, LayerNorm epsilon `1e-5`, no attention dropout, and the existing
dropout `0.1` before the final scalar layer.  SelfOnly masks every
cross-medication edge; SetContext permits all 131 medications to attend to one
another.  No medication-order positions or DDI edges are used.  The two lanes
must have identical names, shapes, initial values, and parameter counts.

## Minimum preflight and execution

`preflight_mica_v2.py` checks only invalidating conditions: target-free finite
forward, finite backward for every genuinely new path, Core/FineHistory/
SafeRank parameter equality, SelfOnly/SetContext equality and mask behavior,
FineHistory no-truncation packing, strict-prefix DualEvidence behavior,
SafeSwap determinism/cardinality, and the tied DualEvidence encoder.  The real
data runner separately verifies the immutable source, canonical snapshot,
vocabulary, split, and target alignment.

After those checks pass, use one clean isolated 319 checkout and six independent
detached processes.  Assign the first six currently admissible RTX 3090 GPUs in
the order Core, FineHistory, DualEvidence, SafeRank, SelfOnly, SetContext and
record the actual physical IDs.  Keep checkpoints, predictions, targets, split
membership, and logs private on 319.  Only aggregate public-safe rows belong in
`result.json`.

## Completed execution and outcome

The authoritative starting `origin/main` was
`dc6a7f2f9084ff51902be6674650ce36947ea6e8`.  The baseline six-lane launch used
`RUN_REVISION=9aba7ba1070bda24be5541723c4870e64ee3fa77`.  A scoped runtime fix
(`6d8d3fd473569a9b6425954bc0fb263657b284c9`) was proven equivalent for SafeSwap
and used only to rerun the invalid Core and SafeRank attempts; unaffected lanes
remain bound to the baseline revision.  The mixed-revision provenance is
explicit in `result.json` and is not relabeled as one source revision.

The approved fallback host was `319-lab-via-server`, using the isolated remote
checkouts `/root/zhb/medrec-research-mica-v2-3cb5f75` (baseline) and
`/root/zhb/medrec-research-mica-v2-6d8d3fd` (scoped rerun).  The environment was
Python `3.8.16`, PyTorch `1.9.0+cu111`, and NumPy `1.23.5`.  Actual GPU mapping
was Core→0, FineHistory→1, DualEvidence→2, SafeRank→3, SelfOnly→4, and
SetContext→6; GPU 5 was occupied by an unrelated process and was not touched.
The required preflight was `PASS`, including target-free finite forward and
backward, canonical split/vocabulary checks, parameter checks, five SafeSwap
equivalence trials, and three vectorized ranking-loss equivalence trials.

Selected-checkpoint and final-epoch public-safe rows are below.  `result.json`
also records the complete Train/Dev precision, recall, count standard
deviation, NLL, wall time, peak memory, source revision, and runtime metadata.

| Arm | Params | Selected epoch | Dev J | Dev F1 | Dev PRAUC | Dev precision | Dev recall | Dev DDI | Dev AvgMed | Dev StdMed | Dev NLL | Epoch-60 Dev J | Wall s | Peak MB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 848900 | 3 | 0.542244156 | 0.695005519 | 0.792730126 | 0.702829904 | 0.711926450 | 0.076299636 | 19.9535 | 7.3448 | 0.202483 | 0.474090260 | 1591.826 | 419.755 |
| FineHistory | 848900 | 3 | 0.545571259 | 0.698012548 | 0.793580091 | 0.697115527 | 0.724617377 | 0.076861089 | 20.4568 | 7.2738 | 0.201844 | 0.474567144 | 2302.053 | 4170.571 |
| DualEvidence | 849285 | 3 | 0.541726823 | 0.694895597 | 0.790286786 | 0.693028408 | 0.722212573 | 0.075270373 | 20.5211 | 7.3309 | 0.203168 | 0.471593672 | 2171.346 | 498.200 |
| SafePTO | 848900 | 3 | 0.530585641 | 0.684883786 | 0.792730126 | 0.692547844 | 0.701637631 | 0.054273453 | 19.9535 | 7.3448 | 0.202483 | 0.465547732 | - | - |
| SafeRank | 848900 | 3 | 0.529318395 | 0.683672466 | 0.792415427 | 0.693806893 | 0.698106292 | 0.054160684 | 19.8300 | 7.3674 | 0.202427 | 0.466505052 | 7152.467 | 418.742 |
| SelfOnly | 981380 | 4 | 0.540036756 | 0.692749231 | 0.790218582 | 0.698974006 | 0.711374540 | 0.077534246 | 19.8662 | 6.5460 | 0.205359 | 0.472723310 | 1572.713 | 451.940 |
| SetContext | 981380 | 4 | 0.539562262 | 0.692592812 | 0.789016459 | 0.704655031 | 0.705205222 | 0.078843891 | 19.4488 | 6.1504 | 0.205355 | 0.471958603 | 1562.282 | 451.940 |

The frozen comparisons are:

```text
ΔJ_fine                 = +0.003327103  → WEAK_FINE_HISTORY
ΔJ_dual                 = -0.000517333  → KILL_DUAL_EVIDENCE
SafePTO − Core          = ΔJ -0.011658515, ΔDDI -0.022026183
SafeRank − Core         = ΔJ -0.012925762, ΔDDI -0.022138952
SafeRank − SafePTO      = ΔJ -0.001267247, ΔDDI -0.000112769
SetContext − SelfOnly   = ΔJ -0.000474494, ΔDDI +0.001309645
```

SafePTO has no useful accuracy-preserving safe headroom (`NO_MICA_SAFE_DECISION_HEADROOM`),
SafeRank fails project survival and adds no incremental value, and SetContext is
`KILL_SET_CONTEXT`.  Because both history variants fail to survive, the history
refinement family is reset.  The single cross-lane route is
`KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH`.

The excluded runtime-only attempts (legacy Core postprocessing and two early
SafeRank attempts) are retained in `result.json` and do not contribute metrics.
No held-out evaluation, additional seed, formal Gate, Audit, G3/G4, R0 Holdout,
historical project test, Idea 009, rescue, or extra ablation was performed.

## Frozen decisions

Use selected complete-Dev rows.  FineHistory and DualEvidence survive only with
`ΔJ > 0.004`, DDI no worse than Core by `0.002`, and F1/PRAUC no worse by
`0.002`; otherwise classify them as kill or weak, resetting the family when
both fail.  SafePTO headroom requires DDI at least `0.005` below Core with no
more than `0.005` Jaccard loss.  SafeRank survival requires no Jaccard loss,
DDI at least `0.005` below Core, F1/PRAUC within `0.002`, and AvgMed within
`1.0`.  SetContext is a mechanism signal only above `0.004` Jaccard over
SelfOnly, and is preserved only if it also beats Core by `0.004` without the
specified DDI/F1/PRAUC penalties.

The result is exploratory single-seed Train/Dev evidence.  A surviving lane is
not automatically combined, formalized, audited, or evaluated on held-out data.
