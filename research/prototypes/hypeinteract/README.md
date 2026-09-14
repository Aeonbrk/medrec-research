# HypeMed / HypeInteract v0 (superseded adapter screen)

Bounded Train/Gate01-Dev prototype screen. This is not an Idea, CCFA Gate,
audit record, or paper claim. The adapter metrics in this file are historical
only; the faithful-source results and current canonical comparison surface are
in [`fidelity_debug/README.md`](fidelity_debug/README.md).

## Source and protocol

- Official HypeMed semantic reference: [GitHub](https://github.com/xansar/HypeMed),
  source revision `33339ea973fd1d72908b3f6ae34b578d98fb4ba3`.
- Primary paper: [HypeMed (ACM TOIS)](https://doi.org/10.1145/3803851).
- One seed: `20260914`; one fixed configuration; CUDA run in
  `medrec-molerec-table1`.
- Canonical `records_final.pkl`, vocabulary, DDI/EHR matrices, and the existing
  Train/Gate01-Dev MoleRec artifact were used.  Held-out Audit/test resources
  were not read.
- Train: 4,233 patients / 10,489 visits.  Gate01-Dev: 1,004 patients / 2,130
  visits.

## Architecture

Stage A adapts the official mechanism rather than substituting a generic GNN:
separate diagnosis/procedure/medication visit-as-hyperedge incidence graphs;
two-layer KHGE-style local hypergraph message passing plus code-prefix global
attention bias; TriCL-style node, visit-edge, and membership contrastive
pretraining; a longitudinal three-visit medication-history channel; Train-only
visit-conditioned similar-visit retrieval; and a dot-product medication
scorer.  The bounded screen uses official dimensions/heads/dropout/top-k/window
(`64 / 4 / 0.3 / 10 / 3`) and reduces the impractical paper epoch counts to
three pretraining epochs and eight recommendation epochs for this one-seed
screen.  Parameter count (encoders plus scorer): `2,538,438`.

All retrieval neighbors are Train visits (`K=10`), and every query excludes
all visits from the same patient.  Dev medication labels are never retrieval
evidence.  Current-visit medication targets are used only as labels; medication
history is shifted to prior visits.

Stage B (HypeInteract) is a two-layer patient-conditioned relation-aware
medication interaction module over the HypeMed medication representations,
with EHR co-prescription and DDI relations.  It was not executed because Stage
A did not pass the health criterion.

## Historical adapter result (superseded)

The initial adapter was not faithful to the official HypeMed implementation.
Its result is retained for provenance but must not be read as canonical HypeMed
performance:

| surface | Jaccard | F1 | PRAUC | DDI | mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| HypeMed adapter | 0.431689 | 0.594725 | 0.721035 | 0.072674 | 13.463850 |
| HypeMed-SameK adapter | 0.431689 | 0.594725 | 0.721035 | 0.072674 | 13.463850 |

Status: `SUPERSEDED_NON_FAITHFUL_HYPEMED_ADAPTER`.

HypeMed-SameK uses the HypeMed threshold prediction's per-visit cardinality;
therefore its cardinality matches the standalone HypeMed surface exactly.

The old Stage-A health result is superseded by the fidelity audit. No
interaction-module metrics or set-change diagnostics are claimed.

## Focused validation

Passed before the real-data run:

- Train-only retrieval assertion with same-patient exclusion;
- current-target medication leakage boundary;
- hypergraph/visit alignment and SameK cardinality check;
- medication-interaction permutation/shape check;
- finite CUDA forward/backward smoke.

## Superseded decision and current terminal interpretation

- Prior adapter decision: `STOP_HYPEMED_BACKBONE_RESET` (superseded).
- Current fidelity interpretation: `HYPEMED_PREVIOUS_ADAPTER_INVALIDATED`.
- Faithful-source terminal verdict: `HYPEMED_CANONICAL_WEAK`.
