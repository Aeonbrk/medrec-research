# CLAUDE Global Configuration

> Maintainer: oian | Version: 26.23 | Updated: 2026-08-20  
> Read `~/.claude/RTK.md` before executing shell commands.

---

## Core Philosophy & Coding Principles

Behavioral guidelines to eliminate common LLM coding mistakes:

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what is confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Ask: _"Would a senior engineer say this is overcomplicated?"_ If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- When your changes create orphans: remove imports/variables/functions that YOUR changes made unused. Don't remove pre-existing dead code unless asked.
- The test: Every changed line must trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- Transform tasks into verifiable goals (e.g., "Add validation" → "Write tests for invalid inputs, then make them pass").
- For multi-step tasks, state a brief plan:

  ```
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
  3. [Step] → verify: [check]
  ```

- Strong success criteria let you loop independently.
- **Success indicator:** Fewer unnecessary diff changes, fewer rewrites due to overcomplication, and clarifying questions asked upfront before implementation rather than after mistakes.

---

## Core Behavior

- **Challenging over confirming**: Test edge cases and counter-premises before agreeing.
- **State genuine unknowns**: Ask directly; never fill gaps with guesses. Challenge incorrect premises directly and explain why.
- **Root-cause focus**: Identify the hidden critical question and causal mechanisms; avoid empty abstraction and excessive hierarchical structures.
- **Response delivery**: Direct, concise, structured (`caveman` style, avoid conversational filler).
- **Token optimization**: Leverage `rtk` (Rust Token Killer) for shell commands to reduce output tokens (e.g., `rtk git status`, `rtk cargo test`, `rtk pytest -q`).

## Precedence & Operating Model

- **Map, not manual**: Progressive disclosure; repo-local versioned artifacts as the system of record.
- **Precedence hierarchy**:
  1. Runtime safety, system, and developer instructions.
  2. Explicit user requests in the current turn.
  3. Nearest applicable `CLAUDE.md` / `AGENTS.md` in the working tree.
  4. Global `~/.claude/CLAUDE.md`.
  5. Companion documentation and generated projections.
- Policy keywords: `MUST` is mandatory, `SHOULD` is default, `MAY` is optional.

## Documentation Map

- Durable knowledge lives in `docs/`: shallow root (`CLAUDE.md` / `AGENTS.md` for policy, `ARCHITECTURE.md` for orientation).
- Navigation starts at `docs/START_HERE.md`; playbook compatibility index at `docs/playbooks/index.md`.
- Multi-step work tracking: `docs/PLANS.md`.
- Disambiguation:
  - `docs/PLANS.md`: Accepted/active multi-step work tracking.
  - `docs/plans/`: Technical plans from `ce-plan`.
  - `docs/brainstorms/`: Requirements and option framing docs from `ce-brainstorm`.
  - `docs/solutions/`: Durable solutions, learnings, and troubleshooting memory from `ce-compound`.
- Treat runtime inventory and status files as generated snapshots, never authored truth.

## Skill and Tool Routing

- **Priority**: Explicitly named skills take precedence. Skills follow progressive disclosure (injected on-demand when relevant).
- **File Operations**: Prefer surgical native tool edits over full-file rewrites. Always provide clickable links with the `file://` scheme (e.g., `[utils.py](file:///path/to/utils.py#L10-L20)`).
- **Search & Discovery Hierarchy**:
  1. **CodeGraph** (`codegraph_explore` / `codegraph explore`): For code understanding, call paths, and symbol relationships when indexed (`.codegraph/` exists).
  2. **Semble** (`mcp__semble__search`, `mcp__semble__find_related` or `semble search`): For semantic code, docs (`--content docs`), and config (`--content config`).
  3. **Native Search** (`grep`, `glob`, file view): For exact literal string matches across the entire codebase.

### Domain Routing

- **Document Parsing vs. Editing**:
  - Use `convert-documents-to-markdown` (via Firecrawl anydoc) to convert DOCX, PPTX, XLSX, PDF, CSV, EPUB, RTF to GitHub-Flavored Markdown.
  - Use `officecli` specifically for creating, modifying, or manipulating DOCX, PPTX, and XLSX files (binary authoring/editing).
  - `modern-web-guidance`: Mandatory check for modern HTML/CSS/JS APIs, layouts, and animations.
  - `chrome-extensions`: Manifest V3 extension architecture, storage, and publishing.
  - `frontend-design`: Art direction, typography, and distinctive visual execution.
  - `beautiful-mermaid`: Diagram visualization in Markdown.
- **Language Best Practices**:
  - **Python**: `python-project-structure`, `python-code-style` (ruff, mypy/pyright), `python-testing-patterns`, `async-python-patterns` (Default execution: `conda run -n base python ...` unless repo specifies otherwise).
  - **Go**: `golang-patterns`, `go-concurrency-patterns`.
  - **Rust**: `rust-best-practices`, `rust-async-patterns`.
  - **Shell & Infra**: `bash-defensive-patterns`, `supabase-postgres-best-practices`.
- **Language and Tone**:
  - For rewriting tasks aimed at natural, human tone without AI clichés, follow `shuorenhua` guidelines (applied primarily to external-facing text; never use on code, logs, configs, or command output).
  - For response delivery, maintain concise, direct, and structured output (`caveman`).

## Subagent Scout Doctrine

Subagents are scouts for broad, heavy reading, parallel verification, and exploration. Dispatch to reduce main-thread context pollution, increase parallelism, and provide independent verification.

### When to Work Directly

- Small files at known locations, limited code, or a single fact.
- The exact code you are about to modify.
- Tasks whose dispatch/verification cost is no lower than reading directly.
- **Foundational documents** (architecture docs, design specs, handoff memos) that establish global context — translating them through subagents introduces distortion.

### When to Delegate

- Very large non-foundational files, cross-file/cross-directory exploratory searches.
- Independent explorations or verifications running in parallel.
- Reading producing large volumes of logs, search results, or peripheral output.

### Delegation & Verification Contract

- Every subagent brief MUST be self-contained: state search scope, concrete question, and expected output.
- Require `file:line` handles and verbatim excerpts for verification.
- **Verification rule**: Verify only cited `file:line` locations and key excerpts. Do not reread entire sources.
- The main agent owns all file edits, design decisions, and final integration.

---

## Safety, Verification & Git

- **Mechanical Verification**: Mechanically verify all changes before completion (`./scripts/verify`, linters, test suites). Do not assume success.
- **Markdown Integrity**: Run `markdownlint` on modified markdown; do not hard-wrap prose.
- **Security**: Never expose keys, credentials, tokens, or private data from `.env`, `settings.json`, environment variables, or config files. Explain irreversible risks before destructive actions.
- **Commit Messages**: MUST follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/#specification).

<!-- CODEGRAPH_START -->

## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision (or run `codegraph init`).
<!-- CODEGRAPH_END -->

<!-- SEMBLE_START -->

## Semble Code Search

A `semble` MCP server is available with two tools:

- `mcp__semble__search` — search the codebase with a natural-language or code query.
- `mcp__semble__find_related` — find code similar to a specific file and line.

Use `mcp__semble__search` to find where something is implemented — instead of using Grep or Glob to discover files. After semble returns the file and line, navigate there directly and read that file. Do not grep for the same content again.

Pass `--content docs` to search documentation and prose, `--content config` for config files, or `--content all` to search code, docs, and config together.

For CLI fallback or sub-agents without MCP access, use:

```bash
semble search "authentication flow" ./my-project --max-snippet-lines 10
semble search "deployment guide" ./my-project --content docs
semble search "database host port" ./my-project --content config
semble find-related src/auth.py 42 ./my-project
semble search "save model to disk" ./my-project --top-k 10
```

The index is built on first run and cached automatically. If `semble` is not on `$PATH`, use `uvx --from "semble[mcp]" semble`.

### Workflow

1. Call `mcp__semble__search` with a query describing what the code does or its name. The tool returns results with 10 lines of context each (function/class signature + first body lines, enough to confirm the location).
2. Navigate directly to the top result's file and line. Read only the function or class at that location.
3. Make the edit. Do not re-search or grep for the same content.
4. Use `--content docs` for documentation, `--content config` for config files, or `--content all` for everything.
5. Optionally use `mcp__semble__find_related` with `file_path` and `line` to discover similar code elsewhere.
6. Use Grep only when you need every occurrence of a literal string across the whole repo (e.g., all callers of a renamed function).

<!-- SEMBLE_END -->

<!-- context7 -->

## Context7 Documentation Lookup

Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service — even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer — your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

### Steps

1. Always start with `resolve-library-id` using the library name and what to look up in the library's documentation, unless the user provides an exact library ID in `/org/project` format.
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries. Use version-specific IDs when the user mentions a version.
3. `query-docs` with the selected library ID and what to look up in the library's documentation (not single words), scoped to a single concept. If the question spans multiple distinct concepts, make separate `query-docs` calls.
4. Answer using the fetched docs.

<!-- context7 -->
