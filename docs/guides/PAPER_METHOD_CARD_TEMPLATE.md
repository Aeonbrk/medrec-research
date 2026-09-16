# Paper Method Card Template

Use one Method Card for every external or internal method that may enter a paper-facing comparison. The card is concise current configuration, not a historical diary.

```text
METHOD_ID
DISPLAY_NAME
SCIENTIFIC_ROLE

SOURCE
paper / primary source
official or strongest trustworthy implementation
pinned source revision
license / provenance note if relevant

SCIENTIFIC_CORE
one-paragraph computation graph / mechanism
core objective / supervision
prediction factorization / decoder
required external knowledge or molecular assets

BENCHMARK_PROFILE
benchmark / split / vocabulary
input information budget
history semantics
output-space semantics
feedback-status role

ADAPTATION
mechanical changes
benchmark-required asset reconstruction
scientific changes = NONE, or explicit variant identity

SOURCE_SANITY
reference condition used
why numerically comparable or not
source-path / update-semantics checks
known paper-vs-code discrepancies
sanity verdict

DEVELOPMENT_ENTITLEMENT
candidate configs declared before screening
screening seed
second development seed for top candidates
config-selection rule
predeclared non-convergence / budget-extension rule

VALIDATION_AND_DECODING
maximum training budget
validation checkpoints / frequency
patience if any
operating-point set
native default operating point
joint checkpoint + operating-point rule
selection metric = Dev patient-macro Jaccard unless candidate contract states otherwise

FINAL_CONFIRMATION
final config
final seed count
exact seed set
nominated scientific comparisons
failure handling

OUTPUTS
continuous medication-score semantics for PRAUC/AP
set decoder semantics
parameter count
online inference path, including solver if any

STATUS
DEVELOPMENT_ONLY | PAPER_CANDIDATE | FINAL_TABLE_ELIGIBLE

LIMITATIONS
known incompatibilities
unsupported metrics
unresolved scientific ambiguity
```

## Rules

- Do not fill missing upstream semantics by guessing. Record `UNKNOWN` and resolve only if it changes the experiment.
- A paper/code discrepancy is not automatically disqualifying. State which behavior the paper experiment executes and why.
- Do not use a Method Card to relabel a scientifically changed implementation as the published method.
- Historical `Reproduction Mode` and `Comparison Mode` records may be cited as provenance or sanity evidence, but they do not substitute for the current card.
- The configuration list and search stopping rule must be written before that method's Dev configuration screening begins.
