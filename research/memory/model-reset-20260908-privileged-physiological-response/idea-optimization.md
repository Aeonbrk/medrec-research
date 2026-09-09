<!-- markdownlint-disable MD013 -->

# Idea Optimization — Response-Privileged Medication Recommendation

## Target venue and assumptions

- Target: first formal method paper, at least a CCF-A Data/Mining/AI venue family.
- Likely audience: KDD / WWW / AAAI-style machine learning, data mining, recommender, or clinical-AI method tracks; exact venue is not frozen.
- Data resource: raw MIMIC-IV 3.1 plus already admitted causal order-time medication infrastructure.
- Current stage: `PRE_IDEA_PRIVILEGED_RESPONSE_REQUIRED_REVISIONS`.
- Active Idea: none.
- Idea 007: not created / not authorized.

The three lines above are the historical state of this optimizer artifact before
the subsequent strict admission. The current canonical state is
`IDEA_007_GATE_01_DESIGN_FROZEN_AUDITED_TRAINING_NOT_AUTHORIZED`; see
[`research/ideas/007-privileged-physiological-response-supervision/`](../../ideas/007-privileged-physiological-response-supervision/)
for the admitted Idea and audited Gate 01. The R1--R3 contract below remains
frozen and is not reopened by this historical label.

## Mode and development stance

`ccf-idea-optimizer / standard`

Development stance: **promising method seed, strict-review required**.

Do not open another standalone premise-audit stage. Basic response coverage/linkage is a future Gate-01 mechanical preflight; insufficient coverage should stop the method before training.

This bounded optimizer pass freezes R1--R3 below. It does not create Idea 007,
inspect response coverage, design Gate 01, run a model, or authorize local
scientific execution. After this pass the next owner is strict
`ccf-idea-reviewer`.

## Raw idea diagnosis

The weak version is:

> add labs/vitals or future response prediction to a medication recommender.

That version is crowded by REFINE, ChainCare, MedGCN, prior medication+lab-response systems, and broader longitudinal clinical models.

The stronger version changes the information-flow contract:

> future post-administration physiology is privileged training information that teaches a deployable pre-order model a candidate-specific response-associated representation.

This is a supervision / representation-learning method, not a feature addition.

## Optimized idea card

### Task

Strictly causal medication recommendation at a medication-order decision point using only pre-order information at deployment.

### Gap

Current MedRec methods either use monitoring features directly, model historical monitoring-treatment chains, or jointly predict future lab responses. They do not clearly force a deployable candidate-medication representation to internalize information available only from realized post-administration physiology during training.

### Root challenge

The most informative evidence about a patient–medication interaction often appears after the medication is administered, but this information is unavailable at decision time and is observationally confounded.

### Core insight

Use future physiology as **privileged supervision**, not as a deployment feature and not as a causal label. A teacher can summarize the observed medication-in-context monitoring trajectory; a student must anticipate that representation using only pre-order state and candidate medication.

### Proposed mechanism

A response teacher and a deployable candidate student are coupled by response-representation distillation/contrastive alignment in addition to the ordinary recommendation objective.

### Contribution type

Primary: method / supervision / representation learning.

Secondary: leakage-safe information-flow formulation for medication recommendation.

Not a benchmark, survey, causal-effect estimator, or safety method.

### Expected evidence

The method must improve recommendation fidelity over strong causal baselines and, critically, beat capacity-matched controls showing that response semantics matter rather than generic future-state regularization.

### Why now

MIMIC-IV supports fine-grained order, administration, lab, and vital event timing; recent MedRec increasingly exploits monitoring-level data; current privileged-distillation work in clinical prediction provides a mature training primitive; and the project has already built a causal order-time execution pipeline.

### Main risk

Observed future physiology may be too confounded, too sparse, or too generic to provide medication-specific information beyond ordinary future-state auxiliary learning.

## Candidate concretizations

### Route A — Response-Privileged Feature Distillation — primary

For a supported positive medication event `(x_t, m)`:

- `x_t`: strictly pre-order causal patient state;
- `c_t`: observed active/co-administered treatment context;
- `r_{t,m}`: bounded post-administration monitoring trajectory, observed only during training.

Teacher:

$$
z^{resp}_{t,m}=T(x_t,m,c_t,r_{t,m}).
$$

Deployable student candidate interaction:

$$
\hat z^{resp}_{t,m}=S(x_t,m).
$$

Recommendation score:

$$
s_{t,m}=G(x_t,m,\hat z^{resp}_{t,m}).
$$

Training objective conceptually combines:

$$
L=L_{rec}+\lambda L_{resp-align},
$$

with an optional tightly scoped contrastive term only if needed to prevent representation collapse.

The exact encoder, response window, and loss coefficients are **not frozen at optimizer stage**.

#### Mechanistic claim

Training-time response-associated supervision induces a pre-order candidate representation that better separates medications appropriate to the observed prescribing decision than recommendation labels alone.

#### Why this route is preferred

It cleanly preserves deployability, uses a genuinely different supervision source, and supports decisive response-shuffle/generic-future controls.

### Route B — Medication-Conditioned Response Pretraining — fallback only

Pretrain the patient–medication interaction encoder to predict/contrast post-administration monitoring representations, then fine-tune for medication recommendation without teacher-student distillation.

This route is simpler but more crowded by generic clinical pretraining, MedGCN-style multitask learning, REFINE, and current response-modeling work. It is retained only as a reviewer-directed fallback, not as an automatically authorized rescue.

## Method blueprint

### 1. Causal pre-order state

Reuse admitted order-time infrastructure. A future Idea should construct a compact causal state from information available before `t`, potentially including:

- medication-order history;
- active execution-confirmed regimen;
- pre-order labs/vitals and missingness indicators;
- elapsed time / admission context.

The exact modalities must be entitlement-matched across primary baselines.

### 2. Positive medication event anchoring

A training example may use privileged response only when the observed medication recommendation/order can be linked to an actual administration and a valid post-administration monitoring window.

This is a support requirement, not a new standalone research gate.

### 3. Privileged response encoder

The teacher receives the realized medication and contextual treatment state together with post-administration measurements. It outputs a latent response-associated signature rather than a scalar clinical outcome.

The teacher must not be trained or interpreted as estimating an individual causal medication effect.

### 4. Deployable student interaction

The student receives only pre-order state and candidate medication. At inference, no future monitoring, post-order event, teacher, or privileged representation is available.

### 5. Recommendation head

The student's candidate interaction contributes to medication ranking alongside the standard recommendation representation. The mechanism should remain compact enough that the paper's contribution is the privileged supervision, not an oversized architecture.

## Bounded revision freeze: R1--R3

The following contract is frozen for the next strict review. It is a formulation
constraint, not a Gate-01 design or an invitation to inspect data. Every
privileged-response control must receive the same recommendation examples,
supported-event mask, future window, deployable student, and auxiliary
optimization entitlement. A control may remove the claimed semantic signal;
it may not receive less or different training opportunity in a way that makes
the comparison uninterpretable.

Let `E_rec` be the full frozen set of recommendation training examples. Define
the response-support indicator:

```text
A(e) = 1 iff e is an actually administered positive focal-medication event
       with a valid linked future monitoring window; otherwise A(e) = 0.
```

For every privileged variant `v`, the objective is conceptually:

```text
L_v = sum_{e in E_rec} ell_rec^v(e)
      + lambda * sum_{e in E_rec} A(e) * ell_aux^v(e).
```

The recommendation term is therefore evaluated on the same `E_rec` for every
variant. `A(e) = 0` disables only the auxiliary response term; it never drops,
reweights, or changes the normalization of that example in the recommendation
objective. No response target is constructed for an unchosen medication.

### R1 — Medication-specificity subtraction (mandatory)

Freeze **Generic Future-State Auxiliary / Medication-Ablated Future** as a
matched killer control. For every `e` with `A(e) = 1`, the proposed branch may
form a response-associated target from the focal medication and the observed
future physiological window, while the ablated branch must use the same
supported event, administration-time anchor, future window, and observed value
tensor without receiving focal medication identity or any medication-specific
response construction. In particular, the ablated teacher/target may not use a
focal-medication embedding, label, medication-coded event identifier,
medication-conditioned delta, or per-medication response prototype. Non-focal
context is allowed only when it is defined identically for the matched
comparison and cannot recover the focal identity.

The two variants must use the same deployable student architecture and
inference inputs `S(x_t, m)`, the same supported-event mask `A`, future window,
latent/auxiliary dimensionality, comparable teacher parameter budget, auxiliary
loss weight, and optimizer/update entitlement. The exact implementation may be
chosen later, but these quantities cannot be changed to rescue a failed
contrast.

Future Gate stop rule:

> If removing focal medication identity does not materially decrease the
> proposed gain, stop with `STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE` and
> terminate the response-specific mechanism.

### R2 — Monitoring-policy separation (mandatory)

Freeze **Monitoring-Mask-Only** as a mandatory killer control and separate
physiological values from response availability. Let `r_e` denote future
physiological values and `M_e` the corresponding future measurement
availability/missingness mask over the same window. The proposed teacher may
use `(r_e, M_e)` where the mask is structurally required to interpret missing
values, but `M_e` is not itself physiological response evidence. Any
mask-derived availability/frequency representation used by the proposed branch
must be supplied identically to `Monitoring-Mask-Only` and cannot be claimed as
the value contribution.

`Monitoring-Mask-Only` receives `M_e` and the same `A`, future window,
deployable student, auxiliary capacity, and optimization entitlement as the
proposed branch, but no future physiological values or value-derived summary.
Thus the control tests whether measurement availability/frequency alone is
sufficient, while preserving the missing-data structure needed by the task.

Future Gate stop rule:

> If `MonitoringMaskOnly ~= Proposed`, stop with
> `STOP_MONITORING_POLICY_SUFFICIENCY` and terminate the physiological-value
> interpretation.

This failure cannot be rescued by a larger teacher, a different future window,
or an additional modality. Those changes would alter the frozen comparison
rather than identify physiological value.

### R3 — Equal-support, positive-only, and deployment entitlement (mandatory)

Response supervision exists only on actually administered positive medication
events with a valid linked future monitoring window (`A(e) = 1`). Unchosen
medications have no observed response target, and the method must not invent a
counterfactual response for them. Every privileged-response control reuses the
identical `A` support mask and the identical `E_rec` recommendation examples;
unsupported examples stay in the recommendation objective and are not
dropped or reweighted differently by any method.

The deployable student feature and normalization contract is strictly
pre-order. Student construction and all statistics used by it may depend only
on information available before the medication-order decision, such as
pre-order regimen/state, pre-order labs/vitals and their pre-order missingness,
and pre-order timing/context. The following are forbidden on the student path
or in its normalization/statistics: post-order medication, future
administration, future labs/vitals, future monitoring masks, and discharge-coded
or otherwise future-derived information. Normalization parameters must be fit
from strictly pre-order training information only. The teacher, privileged
targets, future values, and future masks are completely absent at inference.

Future Gate validity rule:

> If deployment leakage or unmatched sample/support entitlement is found, the
> Gate result is invalid. It is not repaired and then read as an Audit; the
> proposed mechanism remains unadmitted.

## Strongest simple / mechanism controls

After the R1--R3 freeze, any later Gate 01 must include, at minimum:

1. **Strict Pre-Order Base** — same deployable pre-order inputs, ordinary recommendation objective.
2. **Base + Pre-order Physiology** — proves gains are not just from adding labs/vitals to inference.
3. **Generic Future-State Auxiliary / Medication-Ablated Future** — the R1 control above.
4. **Static Medication Response Prototype** — train-only per-medication average/prototype response signal, testing whether patient-specific privileged response is unnecessary.
5. **Response Shuffle Control** — preserve recommendation labels, `A`, and monitoring amount while disrupting patient--medication--response correspondence.
6. **Monitoring-Mask-Only** — the R2 control above.
7. **Closest reproducible monitoring-aware MedRec baseline** — REFINE/ChainCare-style comparison where compatible with the frozen task, without misrepresenting task mismatch.
8. **Knowledge-distillation control** — if needed, a same-capacity KD variant whose teacher lacks future physiological response, to isolate the knowledge source from KD mechanics.

## Killer decision logic for a future Gate 01

A method-level result is not admitted merely because the proposed model beats
Base. The proposed response-specific gain must survive the frozen support and
deployment contract and materially beat the matched controls that remove the
claimed semantic component. The immediate stop rules are:

- Generic Future-State Auxiliary / Medication-Ablated Future comparable to
  Proposed -> `STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE`;
- Monitoring-Mask-Only comparable to Proposed ->
  `STOP_MONITORING_POLICY_SUFFICIENCY`;
- Response Shuffle, Static Medication Response Prototype, or richer pre-order
  physiology comparable to Proposed -> terminate the response-specific
  mechanism;
- deployment leakage or unmatched support/sample entitlement -> Gate invalid,
  with no repair-and-read-Audit path.

No deeper Transformer/Mamba/GNN, larger teacher, different future window,
extra modality, subgroup mining, or second response definition may rescue one
of these outcomes under the same Idea.

## Evidence challenge

### Challenge 1 — observational confounding

A post-administration trajectory is not an individual drug effect.

**Revision:** make the teacher target explicitly medication-in-context and response-associated; condition on observable concurrent treatment context; prohibit causal/efficacy language.

### Challenge 2 — selective monitoring

Labs/vitals are measured non-uniformly and can encode clinician concern.

**Required evidence:** carry missingness/measurement-process information consistently and report support/concentration. Do not interpret monitoring frequency as physiology itself.

### Challenge 3 — positive-only privileged response

Realized post-administration response exists for observed positive medications, not unchosen alternatives.

**Revision:** the method is representation supervision on observed positives, not counterfactual response prediction. Any contrastive negative construction must avoid pretending unobserved responses are known.

### Challenge 4 — generic regularization

The teacher may simply make optimization easier.

**Required control:** generic future-state auxiliary and response-shuffle are primary killer controls, not optional ablations.

## Innovation claims — strongest honest version

Potential Claim 1:

> Introduce training-time medication-in-context physiological response as privileged supervision for a deployable medication recommender whose inference remains strictly pre-order.

Potential Claim 2:

> Learn candidate-specific response-associated representations by transferring post-administration monitoring structure into a pre-order student.

Potential Claim 3:

> Show through matched future-state, prototype, and response-shuffle controls whether response-specific privileged information provides incremental value beyond generic auxiliary learning.

Do **not** claim:

- causal treatment response estimation;
- personalized drug efficacy;
- clinical outcome improvement;
- first use of labs in MedRec;
- first MedRec knowledge distillation;
- first medication-response modeling.

## Closest-work / novelty unknowns

Current closest-work subtraction is documented in `idea-grounding.md`.

Novelty confidence: `MODERATE / SEARCH-SCOPED`.

The strict reviewer must specifically challenge:

- REFINE;
- ChainCare;
- MedGCN and joint lab-response recommendation;
- DrugDoctor;
- LEADER;
- OC-Distill / learning using privileged information;
- physiological-response representation work such as Wu et al. 2025;
- any 2025–2026 paper found under treatment-response distillation / future-information privileged EHR learning.

## Reviewer-risk register

| Risk | Type | Severity | Required response |
| --- | --- | --- | --- |
| "REFINE/ChainCare already use response events" | design/novelty | high | preserve training-only privileged information delta and response-specific controls |
| "This is just KD" | novelty | high | LEADER/OC-Distill subtraction; isolate physiological response knowledge source |
| "Future labs are confounded" | method soundness | high | non-causal framing, context conditioning, shuffle/prototype controls |
| "Only monitored drugs get supervision" | evidence | high | report support/concentration; mechanical preflight; no favorable subgroup rescue |
| "Future auxiliary task would do the same" | mechanism | critical | matched generic-future control must lose materially |
| "Teacher leaks target medication" | design | high | freeze candidate/positive training semantics; student cannot receive privileged future at inference |
| "131 ATC-L4 is coarse" | limitation | medium | keep action-space claim narrow; do not add simultaneous granularity contribution |
| "Single MIMIC-IV task is narrow" | evidence | medium-high | if Gate 01 survives, later claim-support should test another backbone/setting without consuming quarantined data prematurely |

## Rescue route and pivot policy

Primary route: Route A only.

Fallback Route B is not automatically authorized. If strict review rejects Route A solely because teacher-student distillation is needlessly complex while accepting the response-supervision premise, the reviewer may recommend medication-conditioned response pretraining as a pivot.

If review rejects the response-supervision premise itself, return to `NO_HIGH_VALUE_DIRECTION_YET`. Do not open another response diagnostic series.

## Optional next-module decision

Next owner: **strict `ccf-idea-reviewer`**.

The reviewer should decide whether the current route is strong enough to create Idea 007. No local Agent or experiment execution is authorized before that decision.

## Checklist status

- target venue family: explicit;
- problem/gap/root challenge: explicit;
- current literature grounding: completed, search-scoped;
- mechanism: explicit;
- strongest controls: explicit;
- causal claim boundary: explicit;
- R1--R3 control semantics and stop rules: frozen; full Gate protocol not designed;
- data feasibility: partly known from MIMIC-IV infrastructure; exact response support remains a future Gate-01 preflight;
- novelty: uncertain pending strict review;
- Idea 007: not created.
