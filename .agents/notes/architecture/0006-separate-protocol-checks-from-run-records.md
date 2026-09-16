# Separate protocol checks from accepted run records

The synthetic train-frequency harness emits a Protocol Check Record, not Reproduction Mode or Comparison Mode evidence. An accepted Run Record is currently Comparison Mode only and must bind authoritative baseline, adapter, environment, Dataset Manifest, eligible-visit, Adaptation Budget, evaluation, and artifact identities.

The repository will add a Reproduction Mode record only after a pinned baseline has completed upstream-semantics characterization. Designing that record from the Unified Research Protocol would erase the distinction recorded in ADR-0003.
