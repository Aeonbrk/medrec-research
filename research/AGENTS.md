# Research subtree instructions

This subtree owns scientific exploration, evidence, formal Ideas, benchmarks, and research memory.

Paper-facing experiment governance is defined by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`

Historical Stage/Gate names remain provenance only. Human-facing current research uses descriptive phases.

## Scientific loop

Default exploratory loop:

```text
step back
→ search broadly
→ choose one mechanism-bearing hypothesis
→ smallest real Train/Dev prototype
→ decisive matched comparison
→ survive / redesign once / kill
```

Early screening normally uses one seed, one main configuration, full intended training budget, Train/Dev only, and the strongest practical equal-information control. A survivor expands to three development seeds when seed stability materially affects the next architecture decision.

Architecture-first means the candidate changes at least one meaningful object, representation, information flow, prediction granularity, decoder/inference process, or supervision structure. Existing primitives are allowed when their composition creates a distinct capability.

## Evidence roles

Use the paper contract's three evidence roles:

- `DEVELOPMENT`: decision evidence; may use Train/Dev selection and one/three seeds as appropriate;
- `PAPER_CANDIDATE`: mechanism and claim are substantially frozen and merit formal confirmation;
- `FINAL_TABLE_ELIGIBLE`: frozen paper contract, declared final seeds, complete traceability, no unresolved correctness issue.

Final-table eligibility is not the same as independent confirmation. Every evaluation surface must carry its historical feedback status. A historically exposed benchmark may be reportable without being an untouched confirmatory population.

## Evidence hierarchy

When records disagree:

1. Run-local aggregate result JSON, audit, source-bound README, and frozen experiment profile describe the run that actually happened.
2. `memory/current-research-state.md` owns current cross-project interpretation and routing.
3. Current specs/docs define active operating rules.
4. Historical Stage/Gate protocols, dated searches, reset packets, failure records, and archived syntheses preserve provenance only.

Never rewrite historical run evidence to make an old conclusion look current. Update the live synthesis or add a new scientific decision note instead.

## Knowledge homes

- `prototypes/`: bounded pre-paper mechanism, architecture, supportability, and calibration screens.
- `ideas/`: historical/formal Ideas and their frozen evidence when such packaging was used.
- `benchmarks/`: dataset/task contracts and public-safe benchmark records.
- `diagnostics/`: bounded diagnostics whose result can change a concrete decision.
- `memory/current-research-state.md`: short live scientific synthesis.
- `memory/decisions/`: append-only scientific belief updates caused by evidence.
- `memory/failures/`: durable falsified-formulation records.
- `memory/archive/`: superseded live syntheses or mixed historical ledgers retained for provenance.

A scientific decision note links to decisive evidence; it does not duplicate raw metrics, logs, or complete experiment narratives.

## Failure and novelty semantics

- A negative result kills the tested formulation, not every primitive used inside it.
- Two bounded weak prototypes in one family normally justify a reset. A third rescue needs a concrete new falsifiable mechanism, not a new name or parameter setting.
- A successful component is a building block, not automatically the mandatory backbone of the next model.
- Primary-source literature is required for novelty, closest-work, SOTA, and benchmark-comparability claims that matter to a survivor or paper.
- Internal X-ray summaries and literature memory are discovery aids only.

## Evaluation boundaries

- Do not use Test, G3/G4, R0 Holdout, or another feedback population for exploratory model selection.
- Freeze task semantics, benchmark profile, evaluator, validation schedule, and joint checkpoint/operating-point rule before interpreting a matched final comparison.
- Report accuracy, DDI, and medication count together when safety/cardinality trade-offs matter.
- NLL improvement alone is not a calibration claim.
- Two surfaces from the same dataset are not independent datasets.
- Patient/record overlap between claimed confirmation populations must be established, disclosed, or left explicitly unknown.

## Scoped prerequisites, not global gates

Do not block all training on unrelated audits. Resolve only the unknowns that can change the interpretation or execution of the experiment being launched.

Examples:

- MIMIC-III SharedPool/DrugQuery seed stability needs the MIMIC-III task/evaluator/selection profile fixed, not MIMIC-IV SSPNet feasibility.
- An external baseline recovery needs that method's source identity, Method Card, benchmark profile, and bounded Dev selection frozen.
- A structured-set prototype needs a clear closest-work computational distinction and minimum model definition before expensive training.

Run a check only when it can detect a failure that changes trust or action.

## Promotion

Spend rigor on survivors. Final baseline breadth, multiple final seeds, untouched/non-feedback confirmation where available, decisive ablations, and formal uncertainty belong after a coherent paper candidate exists.

A mature survivor moves to `papers/` only when a cohesive claim-support package is justified under the paper contract.
