# Verification & Quality Gates

> Mechanical verification before task completion

## Pre-Completion Checklist

Before reporting "done", run these checks:

### 1. Python Code Quality

```bash
# Linting
rtk proxy /opt/homebrew/bin/uv run ruff check .

# Format check
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
```

### 2. Tests

```bash
# Run relevant test suite
rtk proxy /opt/homebrew/bin/uv run pytest tests/unit/test_modified_module.py -v

# Quick smoke test
rtk proxy /opt/homebrew/bin/uv run pytest -q --tb=short
```

### 3. Markdown Integrity

For any modified `.md` files:

```bash
rtk markdownlint '**/*.md' --ignore '.agents/**'
```

**Rule**: Do NOT hard-wrap prose. Let editors handle line wrapping.

## Git Verification

### Before Commit

```bash
# Check what's staged
rtk git diff --staged

# Verify no unintended changes
rtk git status
```

### Commit Message Format

MUST follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:

```text
feat(gamenet): add multi-head attention layer
fix(dataset): handle missing labels in 319-wild
docs(playbook): update MKL conflict workaround
refactor: strip ARIS workflow layer
```

## Security Verification

### Never Commit

- API keys, tokens, credentials
- `.env` files with real values
- `settings.json` with secrets
- AWS/GCP credentials
- Database passwords

### Check Before Commit

```bash
# Scan for potential secrets
rtk git diff --staged | grep -iE '(api[_-]?key|secret|password|token|credential)'
```

## Verification Failure Response

If verification fails:

1. **Don't assume it passed** - Report the actual failure
2. **Show the error** - Include relevant output
3. **Fix before claiming done** - Loop until green
4. **Explain if can't fix** - State why and what's blocking

## Continuous Verification

For long-running tasks, verify incrementally:

```text
1. Implement feature → verify: tests pass
2. Add documentation → verify: markdown lints
3. Commit changes → verify: conventional format
```

Don't wait until the end to discover issues.

## Project-Specific Gates

### GAMENet Experiments

- Model checkpoints saved correctly
- Metrics logged to expected location
- Results reproducible with seed

### Dataset Processing

- Output shape matches expected
- No data leakage between splits
- Preprocessing deterministic

## Verification Tools Quick Reference

| Check | Command |
| ------- | --------- |
| All tests | `rtk proxy /opt/homebrew/bin/uv run pytest` |
| Linting | `rtk proxy /opt/homebrew/bin/uv run ruff check .` |
| Format | `rtk proxy /opt/homebrew/bin/uv run ruff format --check .` |
| Markdown | `rtk markdownlint '**/*.md' --ignore '.agents/**'` |
| Git staged | `rtk git diff --staged` |

---

**Remember**: Verification failures are **normal**. Catch them, fix them, verify again.
