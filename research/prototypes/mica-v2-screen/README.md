<!-- markdownlint-disable MD013 -->

# MICA-v2 Screen — Accuracy and Safe-Decision Extensions

Status: implementation and primary-source collision screen are complete; the
six full Train/Dev lanes are launched only after the required remote preflight.
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
coherent synthesis around the already validated DrugQuery substrate.

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
