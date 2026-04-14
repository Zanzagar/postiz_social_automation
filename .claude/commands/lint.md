---
description: Run linting and code quality checks for the project
allowed-tools: Bash, Read, Glob
---

# Lint

Run the project's linting and code quality tools. Detect which tools are available and run them.

## Workflow

1. **Detect available linters** by checking which tools are installed:

```bash
command -v ruff &>/dev/null && echo "ruff: available" || echo "ruff: not found"
command -v mypy &>/dev/null && echo "mypy: available" || echo "mypy: not found"
command -v eslint &>/dev/null && echo "eslint: available" || echo "eslint: not found"
command -v golangci-lint &>/dev/null && echo "golangci-lint: available" || echo "golangci-lint: not found"
```

2. **Detect project type** from files present:
   - `pyproject.toml` or `setup.py` → Python project
   - `package.json` → Node/TypeScript project
   - `go.mod` → Go project

3. **Run detected linters** (Python example, adapt for detected type):

For Python projects:
```bash
# Lint check (report issues)
ruff check src/ tests/ scripts/ 2>/dev/null || ruff check . 2>/dev/null

# Type checking (if mypy available and configured)
mypy src/ 2>/dev/null
```

For auto-fix mode (if `$ARGUMENTS` contains "fix"):
```bash
ruff check --fix src/ tests/ scripts/ 2>/dev/null || ruff check --fix . 2>/dev/null
```

4. **Report results clearly**:
   - If all checks pass: "All lint checks passed."
   - If issues found: List them grouped by severity, suggest `ruff check --fix` for auto-fixable issues
   - If no linters detected: Suggest installing appropriate linters for the project type

## Arguments

- `/lint` — Run lint checks (report only)
- `/lint fix` — Run lint checks and auto-fix where possible
