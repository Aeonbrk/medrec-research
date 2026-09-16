# Separate current facts, engineering causality, and scientific evidence

## Context / Trigger

The repository had good local sources of truth, but several live files accumulated multiple responsibilities. Root `AGENTS.md` mixed research strategy, baseline semantics, execution rules, privacy, and engineering conventions. `Handoff.md`, `docs/PLANS.md`, and `research/memory/current-research-state.md` had also accumulated historical narratives alongside current routing. Engineering ADRs lived under `docs/`, which made current documentation and historical causality share the same home.

The project is entering a stage with dual-dataset experiments, new model prototypes, baseline comparison work, and multiple agents. Leaving these responsibilities mixed would increase context load and make old routing language easier to mistake for current authority.

## Decision

Adopt repository-specific knowledge homes rather than copying a software-only documentation layout:

- current system facts stay in `docs/`, `ARCHITECTURE.md`, and `CONTEXT.md`;
- engineering causality moves to append-only `.agents/notes/`;
- run-local scientific evidence stays with the owning research artifact;
- scientific belief updates use append-only `research/memory/decisions/`;
- `research/memory/current-research-state.md` remains the stable path for a short live synthesis;
- `Handoff.md` remains a replaceable current-work pointer;
- root rules become routing/invariants, while subtree `AGENTS.md` files own local execution rules.

Legacy `docs/adr/` files are moved to `.agents/notes/architecture/` without changing their historical meaning. Superseded live ledgers are preserved under `research/memory/archive/` before the live files are shortened.

## Rejected Alternatives

- **Copy the DeepSeek-style layout literally.** Rejected because this repository has first-class scientific evidence and scientific belief history that should not be mixed with engineering decisions.
- **Move all research memory into `.agents/notes/`.** Rejected because experiment evidence and research interpretation have different authority and update semantics.
- **Add a global notes index.** Rejected because directory structure and semantic filenames are sufficient and a shared index would become a merge-conflict hotspot.
- **Apply one hard word-count limit to every Markdown file.** Rejected because protocols, source-bound experiment records, and paper evidence may legitimately require detail. Live coordination files should stay small by responsibility instead.
- **Rename the existing `specs/`, `playbooks/`, `guides/`, and `plans/` taxonomy to match another project.** Rejected because the current domain-specific taxonomy is already useful and renaming would create churn without improving ownership.

## Consequences / Invariants

- Future agents read the root rules and the nearest subtree rules instead of loading every project rule up front.
- Current docs must not become chronological decision logs.
- Engineering notes do not become scientific evidence, and scientific decision notes do not replace source-bound results.
- Historical negative results stay scoped to their tested formulation.
- Live synthesis and handoff files may be rewritten as state changes; archived snapshots and decision notes are not rewritten to follow the latest narrative.
- This migration changes knowledge organization only. It does not change any dataset, model, training result, scientific verdict, held-out boundary, or experiment authorization.
