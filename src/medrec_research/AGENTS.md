# Reusable core instructions

`src/medrec_research/` contains idea-agnostic reusable research capability. It is not the default home for prototype code.

## Promotion rule

Promote code into the core only after:

```text
prototype or baseline-local use
→ demonstrated reuse
→ stable semantics
→ clear ownership
→ reusable interface
```

A scientific idea may fail while leaving a useful reusable component. Promote the component only when the reuse is real.

## Dependency direction

- The core package must not depend on external baseline frameworks.
- Baseline-specific CUDA stacks, Conda packages, working-directory assumptions, and source layouts stay outside the core.
- Prefer standard-library modules. Add dependencies only when they remove real complexity.
- Keep CLI handlers thin; deterministic reusable transformations belong in owned modules.

## Interfaces and tests

- Deep modules own invariants so callers do not reimplement them.
- Public interfaces are the primary test surface.
- Prefer behavior tests through the public seam over tests of incidental internal structure.
- Do not keep parallel legacy interfaces after the supported seam is established unless a real current consumer requires them.

## Scope

Do not promote one-off experiment logic, architecture variants, training scripts, or paper-specific code here merely to make them look permanent. Their natural home remains under the owning research or paper package until reuse is demonstrated.
