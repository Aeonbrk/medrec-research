<!-- markdownlint-disable MD013 -->

# Gate 01 implementation / mechanical preflight Verification: Idea 008

## Verification status

- **Verifier role**: independent implementation/protocol verifier
- **Implementation revision verified**: `0e2dbbc60ed046e306da8d5f8f42a77ba30af5f2`
- **Implementation base**: `82ef244780d84f0264ce539f695563642f580f21`
- **Authoritative protocol**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Protocol revision**: `v1.2`
- **Implementation authorization**: [`gate-01-implementation-authorization.md`](gate-01-implementation-authorization.md)
- **Canonical mechanical record**: [`gate-01-mechanical-preflight.json`](gate-01-mechanical-preflight.json)
- **Formal recommendation-model training**: `NOT_RUN / NOT_AUTHORIZED`
- **Formal Gate execution**: `NOT_RUN / NOT_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact
- **Verdict**: `IMPLEMENTATION_INTEGRITY_PASS`

This verification is limited to the implementation/mechanical-preflight surface authorized after the v1.2 design-integrity pass. It does not execute Gate 01, inspect Gate01-Audit, generate scientific utility/DDI evidence, or authorize recommendation-model training.

## Revision scope

The correction range `82ef244780d84f0264ce539f695563642f580f21..0e2dbbc60ed046e306da8d5f8f42a77ba30af5f2` changes only:

- `experiments/gate01_mechanical_preflight.py`;
- `experiments/gate-01-mechanical-preflight.json`;
- `tests/unit/test_idea008_gate01_mechanical_preflight.py`.

No protocol, design-audit, baseline-registry, quarantined-data, scientific-result, or project-test artifact changed in this range.

## Frozen scientific contract verification

The implementation preserves the v1.2 residual recurrence and performs the required state sequence:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
-> exact TopK(K_x)
```

The second update recomputes `q`, marginal DDI cost, and relaxed residual slack rather than reusing stale state. BudgetSet and Independent retain the explicit frozen-score `+s_i` residual anchor. Independent's scorer interface excludes current-set `q`, `c`, `rho`, provisional-set, pair-to-current-set, and iterative-feedback inputs.

The deterministic patient split implements the exact v1.2 namespace, decimal serialization, SHA-256 first-eight-byte unsigned big-endian mapping, and `0.5` boundary. Low-cardinality `K_x=0/1` behavior, exact fixed cardinality, deterministic Greedy+1Swap, fixed-lambda support, ordinary frontier comparison, v1.2 empty-frontier total comparator, matched Independent seeds, deterministic-control seed handling, patient-cluster bootstrap multiplicity/frontier recomputation, checkpoint/patience/configuration ordering, and terminal precedence remain consistent with the frozen protocol.

## Frozen MoleRec integration verification

The previous blocker is closed.

Synthetic hook fixtures no longer satisfy the two real-backbone checks. The mechanical record builder separates the synthetic checks from:

```text
same_frozen_no_grad_forward
embedding_candidate_dimension
```

A missing, blocked, incomplete, or unvalidated integration cannot produce `MECHANICAL_PREFLIGHT_PASS`; it produces `MECHANICAL_PREFLIGHT_INCOMPLETE` once synthetic checks pass. Malformed or contradictory integration evidence produces `STOP_IMPLEMENTATION_MISMATCH`.

The canonical record contains one validated real integration result using only:

- MoleRec upstream revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- profile `molerec-embedding`;
- frozen checkpoint SHA-256 `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`;
- dataset identity `molerec-table1-comparison-v1-1`;
- canonical Comparison Train only.

The record establishes `eval()` mode, no-gradient execution, one-forward provenance for score and candidate representation, score dimension `131`, candidate-embedding shape `[131, 64]`, rank `2`, and consistency with the `score_extractor` output. The pinned upstream MoleRec source confirms that `molecule_embeddings` is produced by `self.aggregator(...)` and immediately consumed by `self.score_extractor(molecule_embeddings)`, so the implementation's pre-hook captures the protocol-frozen `e_i(x)` tensor rather than a static/global substitute.

The committed record contains only identity, shape, boolean check state, and mechanical verdict metadata. It contains no patient identifiers, split membership, raw clinical rows, logits, candidate embeddings, checkpoints, or scientific metrics.

## Mechanical result

All 15 required implementation-critical checks are true in the canonical record. Its verdict is:

```text
MECHANICAL_PREFLIGHT_PASS
```

The synthetic-only self-check remains non-passing by construction:

```text
MECHANICAL_PREFLIGHT_INCOMPLETE
```

This distinction closes the prior false-PASS path.

The local execution handoff reports `24` targeted tests passed, `400` repository tests passed, and Ruff check/format verification passed. The repository has no GitHub Actions/status result attached to the verified revision, so those execution counts are recorded as local execution evidence rather than independently reproduced CI evidence. The committed test code independently covers the synthetic-only incomplete state, validated integration PASS, wrong frozen identity, malformed shapes, malformed booleans, and non-boolean mechanical checks.

## Boundary after verification

This pass certifies only the implementation/mechanical-preflight surface authorized for this phase. It is not scientific Gate evidence and does not itself authorize BudgetSet/Independent training or Gate01-Audit access.

If a later formal-execution phase introduces execution-specific training runner code beyond this verified surface, that new code must satisfy protocol v1.2 before it is used for scientific Gate evidence.

## Verdict

```text
IMPLEMENTATION_INTEGRITY_PASS
```

No implementation mismatch remains within the authorized mechanical-preflight scope. Protocol v1.2 remains unchanged. Gate01-Audit remains unopened, and G3/G4, R0 Holdout, and the historical project test remain quarantined.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Implementation/mechanical preflight: COMPLETE / MECHANICAL_PREFLIGHT_PASS
Independent implementation verification: IMPLEMENTATION_INTEGRITY_PASS
Formal training: NOT_AUTHORIZED
Formal Gate execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
Next task: decide whether a separate formal Gate-execution authorization may be issued; do not execute Gate 01 automatically
```
