<!-- markdownlint-disable MD013 -->

# Failure Record: Privileged Physiological Response Supervision — Gate 01 P1 Support

## Status

```text
TERMINATED
Idea: 007-privileged-physiological-response-supervision
Gate: Gate 01 P1
Decision: STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT
```

The P1 public-safe report and integrity audit are authoritative:

- `../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-mechanical-preflight.json`
- `../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-p1-integrity-audit.md`

## Tested premise

Training-only privileged physiological response supervision requires a sufficiently
large and distributed set of actually administered positive recommendation events
with valid linked future physiological monitoring.

## Frozen operationalization

The check used the existing causal order-time recommendation universe, the first
actual positive eMAR administration in the same admission within six hours of the
decision time, the future window `(a(e), a(e)+24h]`, and the six-channel physiology
source specification. `A(e)` was one only for an administered positive focal event
with a valid linked window containing at least two observed physiological timestamps
and at least one valid canonical-channel value. The preregistered global and
partition support floors and medication/patient concentration floors were applied
without tuning.

## Result

| Scope | `E_rec` | `N_A` | Coverage | Supported patients | Supported meds | Min events/med |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Global | 5,553,455 | 163,610 | 0.029461 | 12,372 | 116 | 1 |
| Gate01-Train | 3,907,607 | 114,350 | 0.029263 | 8,686 | 114 | 1 |
| Gate01-Dev | 826,301 | 25,091 | 0.030365 | 1,796 | 103 | 1 |
| Gate01-Audit | 819,547 | 24,169 | 0.029491 | 1,890 | 103 | 1 |

## What failed

1. Response coverage failed the frozen global floor (`0.10`) and partition floor
   (`0.05`) in every scope.
2. The minimum supported-events-per-counted-medication floor failed globally
   (`25`) and in every partition (`10`).
3. Dev and Audit also failed both frozen patient-concentration checks: maximum
   patient share (`0.01`) and top-20 patient share (`0.10`).

## What did not fail

- The total recommendation universe size was not the blocker.
- The total absolute supported-event count alone was not the blocker.
- Medication concentration passed globally and in every partition.
- No model was tested and no mechanism comparison was run.

## Scientific conclusion

> Under the frozen Idea-007 MIMIC-IV response definition, realized physiological
> response supervision is too sparse relative to the recommendation universe and
> insufficiently distributed under the preregistered support contract to justify
> model training.

This is a supportability failure for the frozen supervision object. It is not a
model failure, an optimization failure, evidence that physiology has no predictive
information, evidence that physiological response is universally useless, or causal
evidence against medication response.

## Non-revival boundary

Idea 007 must not be revived by widening the response window, adding or substituting
channels, lowering a coverage floor, removing sparse medications, mining subgroups,
redefining valid monitoring, changing the administration anchor, changing the
response target, or using a larger model. Each would change the frozen premise.

This record is not a permanent ban on response-related research. A future route
would require a materially different scientific object, supervision source, data
setting, or independently motivated response definition, followed by fresh
literature grounding, supportability reasoning, and review.

## Route boundary

Idea 007 is closed. Full V1--V8 implementation, model training, recommendation-
outcome evaluation, rescue work, and access to quarantined data were not performed.
