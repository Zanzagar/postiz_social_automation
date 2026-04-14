Trigger the doc-updater agent to update documentation for recently changed files.

Usage: `/update-docs [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| `recent` (default) | Files changed since last commit (`git diff --name-only`) |
| `all` | All source files in the project |
| `<path>` | Specific file or directory |

## Workflow

### 1. Identify Sources of Truth

| Source | Generates |
|--------|-----------|
| Code changes (git diff) | Docstring and API doc updates |
| `pyproject.toml` / `package.json` | Available commands reference |
| `.env.example` | Environment variable documentation |
| Route files / OpenAPI spec | API endpoint reference |
| `Dockerfile` / `docker-compose.yml` | Infrastructure setup docs |

### 2. Identify Changed Files

```bash
# Recent (default)
git diff --name-only HEAD
git diff --name-only --cached

# Filter out non-code files
# Exclude: *.md, *.json, *.yaml, *.yml, *.toml, .gitignore, etc.
# Keep: *.py, *.ts, *.js, *.go, *.java, *.rs, etc.
```

### 3. Analyze What Changed

For each changed file, detect:
- New/modified public functions or classes → docstring updates needed
- New/modified API endpoints → README/API docs update needed
- New features or fixes → CHANGELOG entry needed
- New dependencies → installation docs update needed
- New environment variables → .env documentation update needed
- New scripts/commands → commands reference update needed

### 4. Spawn doc-updater Agent

Delegate documentation work to the `doc-updater` agent (haiku model for lightweight operation):

**Agent updates:**
- **Docstrings** — For new/modified functions and classes
- **README.md** — If public API surface changed
- **API docs** — If endpoints were added/modified
- **CHANGELOG** — If new features or bug fixes detected

### 5. Staleness Check

Find documentation files not modified in 90+ days, cross-reference with recent source changes, and flag potentially stale docs for manual review.

### 6. Report Changes

```markdown
Documentation Update
──────────────────────────────
Updated:  src/auth/tokens.py (docstrings for 3 functions)
Updated:  README.md (API section — new /auth/refresh endpoint)
Updated:  CHANGELOG.md (entry under "Added")
Flagged:  docs/DEPLOY.md (142 days stale)
Skipped:  src/config.py (no public API changes)
──────────────────────────────
```

### Generated Content Markers

When updating generated sections of documentation, wrap them with markers:

```markdown
<!-- AUTO-GENERATED: START -->
| Command | Description |
|---------|-------------|
| `pytest` | Run test suite |
<!-- AUTO-GENERATED: END -->
```

This preserves hand-written prose while allowing safe regeneration of generated sections.

## Integration with /pr

The proactive steering rule suggests running `/update-docs` before `/pr`:

```
Before creating a PR, ensure docs are current.
Run /update-docs to check for stale documentation.
```

This can also be added to the `/verify` pipeline as an optional stage.

## Model Usage

Uses the **doc-updater agent** which runs on **haiku** — the lightest model.
Documentation doesn't need deep reasoning, so haiku keeps token costs minimal.

## When to Use

- Before creating a PR (`/update-docs` → `/pr`)
- After implementing a feature
- After significant refactoring
- During code review to ensure docs match code
- Weekly maintenance check
