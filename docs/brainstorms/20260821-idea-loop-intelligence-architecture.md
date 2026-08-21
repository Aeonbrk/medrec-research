# Brainstorm: Idea Loop Intelligence Architecture

**Date**: 2026-08-21  
**Context**: Post first end-to-end mock run (Phase 1-6 completed with template logic)  
**Goal**: Design the intelligence layer that turns mock templates into real scientific reasoning

---

## Current State Snapshot

### What Works ✅
- **Orchestration skeleton**: 6-phase flow with HITL gates executes correctly
- **Remote execution**: SSH to 319-lab, collect results, persist artifacts
- **Decision tracking**: Every HITL gate logs structured JSON decisions
- **File conventions**: Hypotheses, reviews, contracts, evidence all land in correct directories

### What's Mock 🎭
- **Phase 2**: Hypothesis generation returns 3 hardcoded templates
- **Phase 3**: Review scores are fixed (novelty: 8.5, feasibility: 9.0, evidence: 8.0)
- **Phase 4**: Contract generation uses placeholder success criteria
- **Phase 5**: Execution returns fake metrics (no actual training)
- **Phase 6**: Evidence analysis is rule-based pass/fail check

### The Intelligence Gap
**Current**: Template strings with variable substitution  
**Needed**: Causal reasoning, literature synthesis, adversarial review, falsifiable predictions

---

## First Principles: What Does "Real Intelligence" Mean Here?

### Phase 2: Hypothesis Generation
**Mock does**: Returns 3 hardcoded ideas with placeholder mechanisms  
**Real intelligence must**:
1. **Analyze baseline failure modes** from error distribution (not just metrics)
2. **Retrieve relevant papers** that solved similar problems
3. **Identify causal bottlenecks** in current model architecture
4. **Generate mechanistic hypotheses** with falsifiable predictions
5. **Rank by feasibility × impact** (not arbitrary order)

**First-principle question**: Is this pattern matching (retrieval + template) or reasoning (causal inference)?

### Phase 3: Review
**Mock does**: Returns fixed scores regardless of hypothesis content  
**Real intelligence must**:
1. **Novelty**: Search literature for similar ideas (vector DB + citation graph)
2. **Feasibility**: Estimate compute cost, data requirements, implementation complexity
3. **Evidence strength**: Judge if predictions are specific enough to falsify

**First-principle question**: Can we decompose "good hypothesis" into measurable dimensions?

### Phase 4: Contract Design
**Mock does**: Fixed success thresholds (Jaccard >= 0.535)  
**Real intelligence must**:
1. **Calibrate thresholds** from baseline variance + hypothesis claim magnitude
2. **Design ablations** that isolate the proposed mechanism
3. **Specify failure signals** beyond "metrics didn't improve"

**First-principle question**: Is a "research contract" a formal specification we can verify?

### Phase 6: Evidence Analysis
**Mock does**: `if actual >= target: PASSED`  
**Real intelligence must**:
1. **Statistical significance**: Is improvement above noise?
2. **Mechanism validation**: Did the claimed component actually activate?
3. **Failure mode shift**: Did we fix the targeted errors or just shift the distribution?

**First-principle question**: What's the difference between "metrics improved" and "hypothesis confirmed"?

---

## Architecture Options for Intelligence Layer

### Option 1: Direct API Calls (Claude/OpenAI)
```python
def generate_hypotheses(baseline_result: dict) -> list[Hypothesis]:
    prompt = build_hypothesis_prompt(baseline_result)
    response = anthropic_client.messages.create(
        model="claude-opus-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_hypotheses(response.content)
```

**Pros**:
- Simple, no infrastructure
- Access to latest models
- Easy to iterate on prompts

**Cons**:
- API cost per run (Phase 2-6 = 5 LLM calls × long contexts)
- No local control (rate limits, downtime)
- Prompt drift over time (model updates)
- Hard to version/reproduce (model snapshots change)

---

### Option 2: Embedded Agent Framework (PocketAI/MiniAgent)
```python
from pocket_agent import Agent, Tool

hypothesis_agent = Agent(
    model="local-llama3-70b",
    tools=[literature_search, error_analysis, causal_graph],
    memory=conversation_buffer
)

hypotheses = hypothesis_agent.run(
    "Analyze this baseline and generate 3 competing hypotheses"
)
```

**Pros**:
- Composable tools (literature search, code analysis, metrics)
- Local execution (no API costs after setup)
- Reproducible (fixed model checkpoint)

**Cons**:
- Need local GPU for 70B models (or use 7B with quality loss)
- Framework overhead (learning curve, maintenance)
- Tool integration burden (need to build search/analysis tools)

---

### Option 3: Codex/Claude Code as Intelligence Backend
```python
# medrec-research/src/medrec_research/intelligence/codex_backend.py

def invoke_codex_for_hypotheses(baseline_result: dict) -> list[Hypothesis]:
    """Delegate hypothesis generation to Codex via stdin protocol."""
    prompt = (
        "You are a scientific research assistant. Given this baseline result:\n"
        f"{json.dumps(baseline_result, indent=2)}\n\n"
        "Generate 3 competing hypotheses that could improve performance. "
        "Each hypothesis must include: causal mechanism, falsifiable prediction, "
        "and expected metric changes."
    )
    
    # Send to Codex via stdio or local socket
    response = codex_client.send(prompt)
    return parse_hypotheses(response)
```

**Pros**:
- Leverage user's existing Claude Code setup
- No separate API billing (uses user's Claude subscription)
- Integration with user's workflow (they already use it for coding)
- Can call back into repo context (files, git history)

**Cons**:
- Dependency on external tool (what if user doesn't have Codex?)
- Protocol complexity (stdin? socket? HTTP?)
- Unclear separation: is Codex the *orchestrator* or a *worker*?

---

### Option 4: Hybrid: Codex for Deep Reasoning, Local for Mechanics
```python
# Phase 2: Hypothesis Generation
# - Use Codex for causal reasoning (expensive, deep)
# - Use local embedding search for literature retrieval (cheap, fast)
# - Use rule-based scoring for feasibility (deterministic)

def generate_hypotheses_hybrid(baseline_result: dict) -> list[Hypothesis]:
    # 1. Fast local analysis
    error_modes = analyze_errors_locally(baseline_result)
    similar_papers = search_arxiv_embeddings(error_modes)
    
    # 2. Deep reasoning via Codex
    ideas = codex_client.brainstorm(
        errors=error_modes,
        literature=similar_papers,
        constraints={"budget": "6 GPU hours", "dataset": "MIMIC-III"}
    )
    
    # 3. Local feasibility filtering
    feasible = [h for h in ideas if estimate_cost(h) < MAX_COST]
    return ranked_by_impact(feasible)
```

**Pros**:
- Optimize cost/quality tradeoff per step
- Keep fast operations local (don't waste LLM tokens on arithmetic)
- Use LLM for what it's good at (synthesis, judgment)

**Cons**:
- Complexity: multiple backends to maintain
- Unclear boundaries: when to use which backend?

---

## Critical Questions (Grill Me)

### Q1: What's the primary bottleneck we're solving?
**Options**:
- A. Speed (run idea loop in < 1 hour)
- B. Cost (run 100 hypotheses for < $50)
- C. Quality (generate ideas a human scientist would pursue)
- D. Reproducibility (same inputs → same hypotheses)

**My guess**: **C** (Quality). Speed/cost matter, but a fast cheap loop that generates bad ideas is worthless.

**Grill**: Is "quality" measurable? How do we know if a hypothesis is good *before* running the experiment?

---

### Q2: Who is the "intelligence" for?
**Options**:
- A. The researcher (augment their thinking, they make final decisions)
- B. The system (autonomous loop, human only approves contracts)
- C. The PI (batch mode, review results at end of week)

**My guess**: **A** (Augment researcher). HITL gates imply human-in-loop design.

**Grill**: If we're augmenting humans, why do we need *smart* agents? Why not just well-structured prompts they fill in?

---

### Q3: What's the threat model for "bad hypotheses"?
**Options**:
- A. Unfalsifiable (no way to disprove)
- B. Trivial (already tried in literature)
- C. Infeasible (requires 100 GPUs or unobtainable data)
- D. Misleading (happens to improve metrics but wrong mechanism)

**My guess**: **D** is most dangerous. A/B/C waste time but don't corrupt knowledge.

**Grill**: Can an LLM detect "misleading" hypotheses? Or do we need adversarial simulation?

---

### Q4: Where does "literature search" live?
**Options**:
- A. External API (Semantic Scholar, arXiv)
- B. Local vector DB (pre-indexed papers)
- C. LLM's training data (just prompt "what papers address X?")
- D. Manual (user provides relevant papers)

**My guess**: **A or B**. C is unreliable (hallucination, outdated). D breaks automation.

**Grill**: If we use A, how do we prevent prompt injection via paper abstracts? (e.g., malicious paper with "ignore previous instructions" in abstract)

---

### Q5: Is "baseline runner" part of "intelligence" or "infrastructure"?
**Context**: We need `run_baseline.py` to train GAMENet/SafeDrug.

**Options**:
- A. Intelligence (agent decides *how* to run, adapts hyperparams)
- B. Infrastructure (fixed script, agent just triggers it)

**My guess**: **B**. Baseline reproduction should be deterministic, not adaptive.

**Grill**: If baselines are fixed, why do we need agents at all in Phase 1? Just run a script.

---

### Q6: What's the MVP for "real intelligence"?
**Options**:
- A. Phase 2 only (rest stay mock)
- B. Phase 2 + 3 (generate + review)
- C. Phase 2 + 6 (generate + evidence analysis)
- D. All phases (2-6)

**My guess**: **C**. Generating good ideas is useless without knowing if they worked.

**Grill**: Why not B? If we can review hypotheses *before* running, we save GPU hours on bad ideas.

---

## Proposed First-Pass Architecture

### Tier 1: Keep Deterministic (No LLM)
- **Phase 1**: Baseline execution (fixed script)
- **Phase 4**: Contract generation (rule-based from hypothesis claims)
- **Phase 5**: Experiment execution (fixed training script)

### Tier 2: LLM-Assisted (Codex/Claude API)
- **Phase 2**: Hypothesis generation
  - Local: Error analysis, literature embedding search
  - LLM: Causal reasoning, mechanism synthesis
- **Phase 3**: Hypothesis review
  - Local: Compute feasibility estimate, literature deduplication
  - LLM: Novelty judgment, falsifiability check
- **Phase 6**: Evidence analysis
  - Local: Statistical tests, metric delta calculation
  - LLM: Mechanism validation, failure mode diagnosis

### Intelligence Backend Decision Matrix

| Phase | Local (Free) | LLM (Paid) | Rationale |
|-------|--------------|------------|-----------|
| P2: Hypothesis Gen | Error stats, paper search | Causal synthesis | LLM for creative leap |
| P3: Review | Cost estimate, dedup | Novelty, falsifiability | LLM for judgment |
| P6: Evidence | Significance test | Mechanism check | LLM for interpretation |

**Recommendation**: Start with **direct API calls** (Option 1) for MVP:
- Use Claude API for P2, P3, P6
- Keep prompts in version control
- Measure cost per loop iteration
- Migrate to local/hybrid if cost > $5/loop

---

## Open Questions for Next Brainstorm

1. **Prompt engineering**: How do we structure prompts for Phase 2/3/6?
2. **Tool integration**: Do LLMs get tools (literature search, code analysis)?
3. **Memory**: Do agents remember across phases? (e.g., Phase 6 recalls Phase 2 reasoning)
4. **Fallback**: What if API call fails? Retry? Mock? Human takeover?
5. **Evaluation**: How do we test if "intelligent" version is better than mock?

---

## Next Steps

1. **Review this brainstorm** with grill-me lens
2. **Prototype Phase 2** with direct Claude API
3. **Measure cost/quality** on 5 baselines
4. **Decide**: Keep API vs migrate to local/hybrid

