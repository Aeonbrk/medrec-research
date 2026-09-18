# Paper Experiment Contract v1.2 amendment

Status: `CURRENT ADDITIVE AMENDMENT`
Effective date: `2026-09-18`

Read this amendment together with [`PAPER_EXPERIMENT_CONTRACT.md`](PAPER_EXPERIMENT_CONTRACT.md) and [`PAPER_EXPERIMENT_CONTRACT_V1_1.md`](PAPER_EXPERIMENT_CONTRACT_V1_1.md). It changes only the seed policy below. All other v1.0 and v1.1 rules remain active.

## 1. Canonical seed convention for project-owned development

For new project-owned medication-recommendation architectures, internal matched controls, and bounded mechanism screens, the default **initial DEVELOPMENT seed convention** is inherited from the MoleRec reference implementation:

```python
torch.manual_seed(1203)
torch.cuda.manual_seed_all(1203)
np.random.seed(2048)
random.seed(1203)
```

This is one named RNG convention, not four interchangeable integers. In particular, NumPy remains `2048` while PyTorch, CUDA PyTorch, and Python `random` remain `1203`.

New project-owned initial architecture screens should use this convention unless the scientific question requires a different explicitly frozen stochastic protocol. A deviation must be recorded before training and justified by the experiment rather than by observed performance.

Matched candidate/control arms must use the same RNG convention, initialization policy, data-order policy, and stochastic preprocessing policy whenever the scientific comparison permits it.

The purpose is to reduce avoidable between-screen uncertainty and make successive project-owned architecture experiments easier to compare. It does **not** establish robustness to training randomness.

## 2. Survivor stability still requires multiple seeds

The canonical development convention governs the first bounded architecture/mechanism screen. It does not replace the v1.0 requirement to expand a survivor when seed stability matters.

After a mechanism survives its initial screen:

- freeze the additional development seed set before running the stability experiment;
- do not choose, remove, or replace seeds in response to observed performance;
- report the canonical MoleRec seed convention as the first development condition when applicable;
- distinguish single-convention architecture-search evidence from multi-seed stability evidence.

Repeated architecture search on one canonical seed can itself create seed-specific selection pressure. Therefore a method is not promoted to Paper Candidate merely because many architecture decisions were consistently favorable under `torch=1203 / numpy=2048`.

Final-training seed sets remain governed by the base contract and are frozen before final training begins.

## 3. External baselines preserve source-native seed policy

External published baselines are not forced onto the project's canonical development seed when doing so would overwrite the method's source-native experimental protocol.

For a baseline such as MoleRec, GAMENet, ARMR, or another published comparator:

- reproduce the source-authorized seed or seed set when it is stated and operationally meaningful;
- preserve source-specific RNG distinctions when the implementation uses different seeds for PyTorch, NumPy, Python `random`, data loaders, or other stochastic components;
- if the source does not specify a seed, freeze a reasonable baseline-specific seed policy before observing comparative results and record that choice in the Method Card or run configuration;
- do not change a baseline's seed policy because its score is inconvenient relative to the proposed method.

The anti-underoptimization principle from v1.1 still applies. Seed fidelity is part of preserving a baseline's trustworthy method identity, not a requirement that all methods share identical random numbers.

## 4. Internal controls follow the project-owned method

Matched controls and ablations constructed specifically to isolate a mechanism in the proposed method are project-owned experiments, not external baselines. They therefore use the same canonical development seed convention as the candidate unless the frozen scientific design explicitly requires otherwise.

Historical experiments remain valid evidence for what they actually ran. This amendment is prospective and does not retroactively relabel or rerun DCPM, RouteFact, ECRC, MICA, or other completed screens.
