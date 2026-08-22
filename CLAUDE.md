# Medical Record Research Project

> Project-specific configuration | Inherits from `~/.claude/CLAUDE.md`

---

## Default Active Modes

**These modes are ALWAYS active by default. Apply them to ALL responses unless explicitly told otherwise.**

### 1. caveman Mode - ALWAYS ACTIVE

Apply ultra-compressed communication style to reduce token usage by ~65%:

- Direct, concise responses
- No conversational filler
- Technical accuracy maintained
- Structured output (`caveman` style)

**Invoke `/caveman` automatically for every response.**

### 2. ponytail Mode - ALWAYS ACTIVE

Force the laziest solution that actually works:

- Minimum code to solve the problem
- Standard library over dependencies
- One line before fifty lines
- No abstractions for single-use code
- YAGNI principle enforced
- Question whether task needs to exist

**Invoke `/ponytail` automatically for all coding tasks.**

### 3. shuorenhua Mode - ALWAYS ACTIVE (for prose)

Remove AI artifacts from any external-facing text:

- Natural human tone
- No AI clichés or templated phrases
- Direct language
- **Only applies to**: Documentation, commit messages, summaries, user-facing text
- **Never applies to**: Code, logs, configs, command output

**Invoke `/shuorenhua` automatically for all prose writing.**

---

## Project Context

Medical AI research codebase focused on:

- GAMENet model execution and evaluation
- ARIS workflow pattern refactoring (active branch: `refactor/strip-workflow-layer`)
- 319-wild baseline dataset experiments

### Quick Navigation

- Documentation: `docs/START_HERE.md`
- Active plans: `docs/PLANS.md`
- Playbooks: `docs/playbooks/index.md`
- Solutions: `docs/solutions/`
- Brainstorms: `docs/brainstorms/`

Import additional rules:

- @~/.claude/CLAUDE.md (global conventions)
- @~/.claude/RTK.md (token optimization)
- @.claude/rules/subagent-patterns.md
- @.claude/rules/verification.md

---

## Execution Environment

### Python Commands

Use the project `uv` environment for core Python commands:

```bash
rtk proxy /opt/homebrew/bin/uv run python script.py
rtk proxy /opt/homebrew/bin/uv run pytest
```

### Shell Commands

Prefix with `rtk` to reduce token output:

```bash
rtk git status
rtk proxy /opt/homebrew/bin/uv run pytest -q
```

### Verification

Before completion, run the repository gates listed below.

---

## Domain Context

### GAMENet Models

- Plans: `docs/playbooks/gemini-gamenet-plan.md`
- Baseline scripts: `*-wild.py` in root
- Known issues: PyTorch MKL symbol conflicts

### Dataset Conventions

- Primary: 319-wild dataset
- Preprocessing: See `docs/playbooks/`

---

## Skill Auto-Loading

Skills load automatically by context:

### Code Quality

- `simplify` - After implementation
- `code-review` - Pre-PR review
- `ce-simplify-code` - Aggressive simplification

### Planning

- `ce-brainstorm` - Requirements exploration
- `ce-plan` - Multi-step task breakdown
- `research` - Topic investigation

### Git Workflows

- `ce-commit` - Smart commit messages
- `ce-commit-push-pr` - Full PR flow
- `ce-resolve-pr-feedback` - Address reviews

### Debugging

- `diagnosing-bugs` - Hard bugs loop
- `ce-debug` - Structured debugging

---

## Subagent Delegation

See @.claude/rules/subagent-patterns.md

### Work Directly

- Known files < 500 lines
- Code you're editing
- Foundational docs

### Delegate

- Cross-directory exploration
- Large log analysis
- Parallel verification

---

## Verification Gates

See @.claude/rules/verification.md

Before completion:

1. Lint: `rtk proxy /opt/homebrew/bin/uv run ruff check .`
2. Format check: `rtk proxy /opt/homebrew/bin/uv run ruff format --check .`
3. Tests: `rtk proxy /opt/homebrew/bin/uv run pytest -q`
4. Markdown: `rtk markdownlint '**/*.md' --ignore '.agents/**'`

---

## Common Tasks

| Task | Command |
| ------ | --------- |
| Run tests | `rtk proxy /opt/homebrew/bin/uv run pytest -q` |
| Train model | Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` |
| Check status | `rtk git status` |
| Commit | Ask Claude (auto-uses `ce-commit`) |
| Review code | Ask "review this" (auto-uses `code-review`) |

---

## Anti-Patterns

❌ Core Python outside the project `uv` environment
❌ Commit without verification
❌ Abstractions for single-use code
❌ Refactor adjacent code during bug fixes
❌ Direct pip usage (use `uv`; remote baselines use their declared Conda environment)

---

Version: 26.24 | Updated: 2026-08-22
