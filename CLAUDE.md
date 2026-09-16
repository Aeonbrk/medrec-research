# Claude project conventions

Project-wide rules live in `AGENTS.md` and the nearest subtree `AGENTS.md`. Read those first. This file contains Claude-specific interaction and command conventions only.

## Default modes

Apply these project-local Claude modes unless the user explicitly asks otherwise.

### Caveman

Use concise, direct prose with enough technical detail to preserve correctness. Avoid conversational filler.

### Ponytail

Prefer the smallest solution that actually solves the stated problem. Avoid abstractions for one-off work, speculative compatibility layers, and unnecessary dependencies.

### Shuorenhua

For documentation, commit messages, summaries, and other human-facing prose, use natural direct language and remove templated AI phrasing. Do not rewrite code, logs, configs, or command output merely for prose style.

## Navigation

- Project rules: `AGENTS.md`
- Current documentation map: `docs/START_HERE.md`
- Knowledge ownership: `docs/KNOWLEDGE_HOMES.md`
- Architecture: `ARCHITECTURE.md`
- Domain vocabulary: `CONTEXT.md`
- Current research state: `research/memory/current-research-state.md`
- Current handoff: `Handoff.md`

Import local Claude conventions:

- `@~/.claude/CLAUDE.md`
- `@~/.claude/RTK.md`
- `@.claude/rules/verification.md`

## Commands

Core Python commands use the project `uv` environment:

```bash
rtk proxy /opt/homebrew/bin/uv run python script.py
rtk proxy /opt/homebrew/bin/uv run pytest -q
```

Use `rtk` for shell output when available:

```bash
rtk git status
rtk proxy /opt/homebrew/bin/uv run ruff check .
```

Real-data training and GPU work follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`; the repository `AGENTS.md` and subtree rules define the scientific and privacy boundaries.

## Claude skills

Use installed skills when they materially help the task. Common categories include planning, debugging, code review, simplification, and Git workflows. Skill behavior does not override repository rules or scientific evidence boundaries.

## Verification

Use the applicable checks from `@.claude/rules/verification.md` and `AGENTS.md`. Do not run unrelated expensive checks merely because they exist.
