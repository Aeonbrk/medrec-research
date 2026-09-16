# Handoff

Updated: 2026-09-17.

```text
Current phase: CREDIBLE REFERENCE SETUP
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`
- `research/memory/current-research-state.md`

The active paper-facing philosophy is now explicit: proposed-method development may be substantially larger than baseline tuning. Fairness means credible method identity, necessary assets, reasonable training/Dev selection, and no result-driven baseline neglect—not equal cumulative search budgets. Central ablations/controls also need reasonable Dev selection when a shared recipe would materially disadvantage them.

Default benchmark routing after the v1.1 amendment:

- MIMIC-III canonical-131: main literature-facing surface;
- MIMIC-IV harmonized/common-131: main MIMIC-IV literature-facing surface, pending canonical-lineage identity audit;
- MIMIC-IV native-173: broader-target validation. Competitive claims there require an external comparator; internal-only runs support only mechanism/broader-target claims.

Still valid development evidence:

- MICA DrugQuery vs SharedPool single-seed Train/Dev gains on MIMIC-III and MIMIC-IV;
- fixed-131/generalized-MICA equivalence;
- frozen MIMIC-IV native-173 materialization;
- MIMIC-IV common-131 harmonized materialization;
- earlier qualified five-model MIMIC-III rows as historical references only.

Do not use the temporary former Stage -1G ARMR/MoleRec/GAMENet/RETAIN outputs for method ranking and do not resume those runners.

Immediate bounded work is scoped, not globally gated:

1. freeze the MIMIC-III evaluator/selection profile needed for the SharedPool-vs-DrugQuery stability test;
2. audit how closely MIV harmonized/common-131 matches the canonical 131 medication lineage: exact codes, ATC semantics, mapping, zero-support codes, eligibility, target projection/cardinality, and DDI identity;
3. create source-backed Method Cards and recover credible MoleRec and ARMR comparison paths;
4. continue prediction-time and historical Test-feedback audits only where they affect an upcoming experiment;
5. keep structured-set/RSM training blocked until the closest-work computational distinction and minimal model definition are clear.

Once item 1 is complete, MIMIC-III SharedPool × 3 seeds and DrugQuery × 3 seeds may run without waiting for unrelated MIV/SSPNet work. The two remaining GPUs may run credible baseline recovery only when each baseline's Method Card and execution contract are ready.

Do not access MIMIC-IV Test, choose benchmark roles based on which surface gives a larger advantage, treat equal medication count as equal benchmark identity, silently replace failed final seeds, or add selection opportunities after observing final-run trajectories.
