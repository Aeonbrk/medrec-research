# Bounded structured-set experiment

This directory owns one development-only MIMIC-III canonical-131 architecture
experiment. It is not Idea 009, a formal Gate, an SSPNet recovery, or a Test
run.

The model uses the frozen MICA DrugQuery medication-specific clinical path,
then maps the 131 medication representations to 131 learned anonymous slots.
Each slot has 131 medication logits and one NULL logit. The control trains
`BCEWithLogits(max_slot(u), target)` and uses strict threshold decoding. The
full arm trains categorical cross-entropy after deterministic Hungarian
matching with cost `-u` and uses exact positive-edge maximum-weight injective
assignment at inference.

`preflight_structured_set.py` runs the decision-relevant checks, including the
complete-CE matching fixture, target permutation invariance, empty and full
cardinality behavior, target leakage, initialization equality, finite
forward/backward, exact-zero NULL decoding, duplicate rejection, the fixed
`U,beta` subset invariant, raw score preservation, and cached-`U` semantics.

`run_structured_set.py` performs one arm of the 60-epoch run. Run the timing
preflight first and use its frozen schedule for both arms. It writes checkpoints,
progress, and selected utilities only to the restricted remote output root.

`summarize_structured_set.py` consumes both restricted arm outputs and emits a
public-safe aggregate evidence packet with the B/T and M/A primary comparison,
fixed-anchor decoder crossover, set-change diagnostics, selected-checkpoint
curves, and the Full-anchor mean-cardinality diagnostic.

The output score for PRAUC is the finite raw `max_s u[s,m]` value. No sigmoid,
DDI term, NULL reweighting, cardinality loss, retrieval, reranking, post-hoc
repair, HPO, additional seed, or Test artifact is used.
