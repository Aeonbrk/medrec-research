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

- General medication recommendation research library and Unified Research Protocol
- Registry-driven Reproduction Programs (SafeDrug archived and MoleRec lineages: GAMENet, SafeDrug, RETAIN, LEAP, MoleRec)
- Remote 319 execution plane and public-safe evidence intake

### Quick Navigation

- Documentation: `docs/START_HERE.md`
- Active plans: `docs/PLANS.md`
- Implementation plans: `docs/plans/`
- Playbooks: `docs/playbooks/index.md`
- Architecture: `ARCHITECTURE.md`
- Domain vocabulary: `CONTEXT.md`
- Baseline registry: `baselines/registry.toml`
- Research memory: `research/README.md`

Import additional rules:

- @~/.claude/CLAUDE.md (global conventions)
- @~/.claude/RTK.md (token optimization)
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

### Baseline Programs

- Registry: `baselines/registry.toml`
- Reproduction entrypoints: `baselines/safedrug_archived.py`, `baselines/molerec.py`
- Comparison suite: `baselines/five_model_comparison.py`
- CLI commands: `rtk proxy /opt/homebrew/bin/uv run medrec reproduce <baseline-id> --gpu <id> --dry-run`
- Remote execution: Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` and `docs/playbooks/MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md`

### Dataset Conventions

- Local Data Root: Repository-independent data root on 319, see `docs/playbooks/LOCAL_DATA_ROOT_PLAYBOOK.md`
- Preparation & Preprocessing: See `docs/playbooks/SAFEDRUG_ARCHIVED_PREPARATION_PLAYBOOK.md` and `docs/playbooks/MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md`
- Verification: Pinned SHA-256 and semantic bridge checks prior to snapshot publication

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

| Task         | Command                                                  |
| ------------ | -------------------------------------------------------- |
| Run tests    | `rtk proxy /opt/homebrew/bin/uv run pytest -q`           |
| Train model  | Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` |
| Check status | `rtk git status`                                         |
| Commit       | Ask Claude (auto-uses `ce-commit`)                       |
| Review code  | Ask "review this" (auto-uses `code-review`)              |

---

## Anti-Patterns

❌ Core Python outside the project `uv` environment
❌ Commit without verification
❌ Abstractions for single-use code
❌ Refactor adjacent code during bug fixes
❌ Direct pip usage (use `uv`; remote baselines use their declared Conda environment)

---

=== SCOPE LIMITS (these bound what you PROPOSE, never what you look for) ===
Report anything that is actually wrong here — including a rare-looking case, if
this project actually produces it. Then keep the fix in scope:

1. This is not a security paper. Verification is welcome; over-defense is not.
   Unless this project states otherwise, assume a cooperating operator on their
   own machine; if it has a real adversary, it will say so and that scope wins.
2. Do not add hashes, checksums or fingerprints unless the hash replaces a
   materially more expensive operation AND its result changes what happens next.
3. No defensive scaffolding: no feature flags, migration frameworks, compat
   layers or wrappers for cases that do not occur here.
4. No corner-case obsession: exotic encodings, symlink races, RTL text and
   millisecond races are out of scope unless the case is reachable through this
   project's supported use — its documented inputs, its published interface, its
   real data. Reachable is enough; you do not need a reproduction. Constructible
   in principle is not enough.
5. Where judgement is needed, judge. Do not replace it with a scoring table, a
   checklist, or a re-verification loop over something already settled.
6. None of this overrides security, migration, verification or review that the
   user, this project's own conventions, or a higher-priority rule asked for.
   Those were requested; they are the work, not scope creep.
   Shapes already seen, for calibration. Examples, not a checklist — a real finding
   is not dismissed by resembling one:
   H hashing every row of two spreadsheets to answer what comparing cells answers
   H writing checksum files that nothing ever reads
   E hardening the accounts of an app that has no users and no deployment
   R auditing your own patch all night while the feature stays unwritten
   R a reviewer that returns a failing verdict on everything
   O guards whose justification is the previous guard, not the requirement
   And two that look like the above and are not. Report these:
   ✓ a digest that lets you skip re-reading a large file you already have
   ✓ a rare-looking input this project's own documentation example produces
   Before running any check, answer: what specific failure would this detect, and
   what would I do differently if it occurred? No answer means do not run it.
   Say plainly when something is correct. Do not manufacture findings.
