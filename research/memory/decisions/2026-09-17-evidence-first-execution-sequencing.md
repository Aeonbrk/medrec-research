# Evidence-first execution sequencing

Date: 2026-09-17

## Decision

Adopt an evidence-first, dependency-driven execution plan rather than a serial `reference recovery -> MICA stability -> architecture -> cross-dataset -> baselines` pipeline.

The governing rule is:

> Make the evidence most capable of killing or redirecting the paper arrive early, while keeping only experiment-specific prerequisites blocking execution.

This decision does not amend the Paper Experiment Contract. It defines current research routing under v1.0 + v1.1.

## Immediate dependencies

Before the next MIMIC-III runs, freeze only the minimum common contract that can change their interpretation: patient split, legal input budget, target/eligible-event semantics, core evaluator, and joint Dev checkpoint/operating-point selection.

In parallel:

- recover MoleRec as the first external comparison lane;
- choose the second recovery lane conditionally: ARMR by default when ready, but promote SSPNet if structured-set prediction becomes the active hypothesis and a trustworthy execution path is available;
- perform a time-bounded closest-work computation audit for structured/set prediction;
- separate the harmonized-131 audit into run-critical identity/alignment checks versus paper-claim lineage checks.

No global audit completion is required before unrelated work starts.

## MICA stability routing

Do not make six new MICA jobs a mandatory architecture prerequisite.

Default next evidence is two new paired MIMIC-III runs per arm:

```text
SharedPool seed A / DrugQuery seed A
SharedPool seed B / DrugQuery seed B
```

Use matched declared seed IDs and the same frozen MIMIC-III evaluation/selection profile. Existing historical single-seed evidence remains separate unless it exactly satisfies the new run contract.

Add the third paired seed when one of these conditions holds:

- MICA remains a core component or central mechanism control;
- the first two new pairs disagree and the result changes architecture routing;
- otherwise-ready GPU capacity makes completing the third pair faster than creating another decision boundary.

MICA stability is evidence about a possible building block, not permission required to implement a distinct architecture.

## Architecture routing

A new structured-set implementation may begin before baseline recovery or MICA stability finishes when all of the following are true:

- the legal input/output contract is fixed;
- the candidate has one falsifiable computation-level difference from the closest known work;
- the minimum model and its strongest matched independent-label control are defined;
- a quick valid end-to-end run is possible without adding unrelated modules.

Do not start expensive structured training if the closest-work audit cannot explain the computational difference by approximately 2026-09-21. Do not protect the MICA story by forcing the new architecture to use MICA when a cleaner matched control exists.

The first full architecture screen should answer only:

1. Does the structured model beat a credible matched independent-label control?
2. Is the difference mostly explained by predicted set cardinality / operating point?
3. Is the gain worth the added complexity and cost?

Add one cardinality-aware control only when it can falsify the claimed mechanism. Do not create a module zoo or force a confounded 2x2.

## Early cross-surface falsification

Do not require three MIMIC-III seeds before touching MIMIC-IV.

After the first valid MIMIC-III full/control result and at least one additional paired check show a signal worth pursuing, start early sentinel pairs on:

- MIMIC-IV harmonized/common-131;
- MIMIC-IV native-173.

These two surfaces are the same underlying dataset under different target spaces, not independent replications. The native-173 sentinel asks whether the mechanism depends on the narrower projected medication space.

If a known implementation/mechanism fault is already visible on MIMIC-III, fix or kill it before propagating the faulty model across surfaces.

## Baseline priority

MoleRec is the fixed first recovery lane because it is a strong established reference and previous temporary execution was clearly degraded.

The second lane is conditional:

- ARMR when it is ready and structured-set prediction is not yet the active paper hypothesis;
- SSPNet when structured/set prediction becomes the active hypothesis, SSPNet is confirmed as the closest relevant comparator, and a trustworthy execution path exists;
- otherwise ARMR may proceed while SSPNet remains a bounded CPU/source-recovery task.

SafeDrug rises in priority only if safety/molecular claims become central. GAMENet, RETAIN, and HypeMed are added only when they fill a distinct scientific role rather than baseline count.

Architecture work does not wait for baseline completion, but Paper Candidate Freeze requires credible external positioning.

## GPU scheduling

Treat eight GPUs as a ready-task queue, not fixed phase slots.

Priorities:

1. matched full/control pairs that can change architecture routing;
2. closest/strong external comparator recovery;
3. early second-surface falsification;
4. additional paired seeds needed for a live decision;
5. secondary analyses.

When MICA stability is the only ready work, running all six paired stability jobs in parallel is acceptable. When higher-value ready tasks exist, do not consume six GPUs merely to complete a ceremonial three-seed packet.

Keep human implementation bandwidth narrow: at most one actively changing architecture and one baseline recovery that requires heavy code modification at the same time. Additional finished implementations may train concurrently.

## Decision milestones

Dates are management targets, never scientific pass criteria.

- **2026-10-05:** current architecture route decision — continue, one bounded redesign, or kill/reset.
- **2026-10-09 to 2026-10-13:** normal-path target for a credible Paper Candidate.
- **2026-10-16:** hard stop for the current architecture-search cycle. Do not extend it by adding unrelated modules.
- **2026-10-26 to 2026-11-04:** target window for frozen confirmation only if candidate/final-training prerequisites are complete.
- **2026-11-11 to 2026-11-18:** target window for a first complete manuscript/evidence package.

Missing evidence narrows the claim or delays confirmation; it does not justify premature Test access.

## Continue / redesign / kill / reset

**Continue** when matched controls show a worthwhile effect/trade-off, repeated paired evidence does not expose clear instability, cardinality/operating-point controls do not explain the result away, closest-work distinction remains valid, and complexity is commensurate with value.

**One bounded redesign** is allowed only for a concrete observed failure with a pre-written expected fix, such as NULL collapse, slot-ceiling truncation, or train/decode uniqueness mismatch. Fixes for preventable implementation mistakes do not consume the scientific redesign allowance.

**Kill the formulation** when full-budget repeated evidence does not support value, a reasonable cardinality control explains the gain, the result depends on unfair information/control choices, added cost is unjustified, or the one evidence-driven redesign fails.

**Reset the architecture family** when closest work already occupies the core computation, failure points to the structured-set hypothesis rather than a local implementation issue, or continuation degenerates into unrelated retrieval/DDI/refinement patches.

Allow at most one family reset in this research cycle. If no survivor exists by 2026-10-16, stop the current architecture search and reassess the paper route rather than opening another rescue sequence.

## Paper-candidate boundary

A candidate requires more than internal repeatability. Before freeze:

- the method difference and mechanism claim are experimentally identifiable;
- the core effect is not a single-seed event;
- both main paper surfaces have credible external reference positioning;
- obvious cardinality, leakage, capacity, or control-quality explanations are addressed;
- DDI/cardinality/efficiency costs are known;
- the closest comparator relevant to the final claim is no longer an unresolved conceptual omission.

Stable `+0.003` internal gain while credible external methods remain clearly stronger is not automatically a Paper Candidate unless a different, evidence-backed safety/efficiency/robustness contribution justifies the paper claim.

## Test boundary

MIMIC-IV Test remains sealed throughout reference setup and architecture search. Harmonized-131 and native-173 derived from the same MIMIC-IV patients must be treated inside one frozen confirmation cycle; observing one Test surface cannot be used to redesign the other and still call it untouched.
