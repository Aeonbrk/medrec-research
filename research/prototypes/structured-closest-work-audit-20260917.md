# Structured closest-work audit

Date: 2026-09-17

Scope: time-boxed primary-source audit before any slot/matching prototype or
structured full training. This is a development decision record, not a
novelty certification.

## Sources checked

- [SSPNet, IJCAI 2025 proceedings](https://www.ijcai.org/proceedings/2025/1052)
  and its [official implementation](https://github.com/ResearchGroupHdZhang/SSPNet)
  at source revision `4a2695ec67e0dc30cd3fa8e67a4f1536f0bfc90d` (the current
  `main` revision when checked).
- [Set Transformer, ICML 2019](https://proceedings.mlr.press/v97/lee19d.html)
  as the primary source for permutation-invariant attention blocks.
- The local MICA computation and its primary-source collision notes in
  [`research/prototypes/mica/README.md`](mica/README.md).

## CLOSEST_METHOD

`SSPNet` is the closest work for the proposed structured medication output. The
paper explicitly describes a set-based diagnosis/procedure encoder, a
personalized historical-medication representation, and a permutation-consistent
decoder that predicts the medication combination in parallel. It is therefore
closer than a sequential decoder or a medication-independent multilabel head.

## CLOSEST_COMPUTATION_GRAPH

The verified paper/code graph is:

```text
current diagnosis/procedure sets
  -> separate SAB set encoders
  -> current set representations

all prior visits' diagnosis/procedure sets
  -> PMA per visit -> dual RNN over visits
  -> attention against current health representation
  -> weighted historical medication multi-hot vector (PDRM)

medication embeddings + EHR co-occurrence graph + DDI graph
  -> GCN medication representations
  -> personalized medication representations
  -> medication self-attention
  -> cross-attention to current diagnosis/procedure sets
  -> sigmoid score for each of the 131 candidate medications
  -> thresholded multi-hot set
```

The output is a fixed medication-coordinate vector. The source does not expose
latent medication slots, a medication-or-NULL output, or a target permutation
matching loss. Its set claim comes from order-free set encoders/attention and
parallel candidate scoring. The paper reports threshold `0.5`, BCE plus
multi-label-margin and DDI losses, and a 4:1:1 split; those facts are not
silently substituted into the current MIII paper profile.

## OUR_COMPUTATIONAL_DIFFERENCE

A candidate structured model would emit a bounded set of latent elements,
where each element chooses one medication or an explicit NULL, train with a
permutation-invariant matching objective, and resolve duplicate medications
with a uniqueness-aware decoder. Clinical evidence would remain target-free
and the output score adapter would aggregate slot evidence into one score per
medication.

This is a computation-level difference from SSPNet's fixed-coordinate
multi-label decoder, but it is not yet a novelty finding: set attention,
parallel set prediction, and permutation consistency are established
components and are already central to SSPNet.

## TARGETED_FAILURE_MODE

The falsifiable target is a limitation of independent fixed-coordinate
medication decisions: inability to represent a variable-size combination as a
set with explicit competition/uniqueness, order-invariant supervision, and
controlled cardinality. The claim is about the output factorization, not about
DDI or a generic attention improvement.

## WHY_DIFFERENCE_MAY_HELP

Matching can remove arbitrary label-order supervision and make combination-level
competition explicit. A NULL option can model variable cardinality without
using target size at inference. These are hypotheses only; a strong
coordinate-wise model or a simpler cardinality control may reproduce the same
gain at lower cost.

## FALSIFYING_EXPERIMENT

On the frozen MIII canonical-131 Train/Dev profile, compare one full slot model
against a parameter- and information-matched independent-label control. Freeze
before training:

- medication-level score aggregation from slots;
- final uniqueness/NULL decoder and its legal operating point;
- matching loss and empty-set/cardinality behavior;
- slot capacity from Train-only target-cardinality evidence;
- patient-macro Jaccard selection and the shared evaluator contract.

Record Jaccard, F1, PRAUC/AP, DDI, predicted/target medication counts, NULL and
duplicate rates, target-over-capacity fraction, parameter count, runtime, and
inference latency. A simpler cardinality-aware control is optional only if it
can falsify the structured mechanism.

## EXECUTION_FEASIBILITY

`SSPNET_EXECUTION_UNRESOLVED`. The official repository is inspectable, but the
checked source is not yet a trustworthy execution path:

- its `SSPNetModel.forward` calls a plotting/t-SNE routine for multi-visit
  inputs and writes to a hard-coded maintainer-home image path;
- its training function calls `eval_one_epoch(..., drug_data, ...)` although
  `drug_data` is not a training-function parameter in the checked source.

Repairing these may be mechanical, but source-faithful behavior and the
resulting adaptation boundary must be audited before GPU work. No SSPNet run,
repair, or guessed missing behavior was performed in this session.

## VERDICT

`NOVELTY_UNRESOLVED` and `SSPNET_EXECUTION_UNRESOLVED`.

The difference is substantive enough to define a falsifiable experiment, but
the closest method already covers the broad set-to-set claim and the official
execution path has unresolved defects. Per the execution contract, pause
expensive structured training until an independent review resolves whether the
slot/matching distinction is publication-worthy and whether a source-faithful
SSPNet path can be repaired without changing its scientific identity.
