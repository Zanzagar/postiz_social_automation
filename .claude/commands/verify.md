Run a structured verification pipeline across test, lint, type-check, and security stages.

Usage: `/verify [scope]`

Arguments: $ARGUMENTS

## Scope Options

- `all` (default): Run all stages
- `test`: Tests only
- `lint`: Linting only
- `types`: Type checking only
- `security`: Security scanning only
- `pre-commit`: Tests + lint (fast check)

## Pipeline Stages

Run each stage in order. If a tool is not installed, mark as SKIP (not FAIL).

### Stage 1: Tests
```bash
# Detect test runner
if command -v pytest &>/dev/null; then
    pytest --tb=short -q
elif [ -f "package.json" ] && grep -q '"test"' package.json; then
    npm test
elif command -v go &>/dev/null && ls *_test.go &>/dev/null 2>&1; then
    go test ./...
else
    echo "SKIP: No test runner detected"
fi
```

### Stage 2: Lint
```bash
# Detect linter
if command -v ruff &>/dev/null; then
    ruff check .
elif [ -f ".eslintrc*" ] || [ -f "eslint.config.*" ]; then
    npx eslint .
elif command -v golangci-lint &>/dev/null; then
    golangci-lint run
else
    echo "SKIP: No linter detected"
fi
```

### Stage 3: Type Check
```bash
# Detect type checker
if command -v mypy &>/dev/null; then
    mypy src/ --ignore-missing-imports
elif [ -f "tsconfig.json" ]; then
    npx tsc --noEmit
else
    echo "SKIP: No type checker detected"
fi
```

### Stage 4: Security
```bash
# Detect security scanner
if command -v bandit &>/dev/null; then
    bandit -r src/ -q
elif [ -f "package.json" ]; then
    npm audit --production
elif command -v gosec &>/dev/null; then
    gosec ./...
else
    echo "SKIP: No security scanner detected"
fi
```

## Output Format

```markdown
# Verification Report

| Stage    | Tool     | Result | Details            |
|----------|----------|--------|--------------------|
| Tests    | pytest   | PASS   | 42 passed, 0 failed |
| Lint     | ruff     | WARN   | 3 warnings         |
| Types    | mypy     | PASS   | No errors          |
| Security | bandit   | FAIL   | 2 issues found     |

**Overall: WARN** (1 failure, 1 warning)

## Details
[Expand any FAIL or WARN stages with specifics]
```

## Result Levels

| Level | Meaning |
|-------|---------|
| PASS  | Stage completed with no issues |
| WARN  | Non-blocking issues found |
| FAIL  | Blocking issues that need fixing |
| SKIP  | Tool not installed (not a failure) |

**Overall** = worst individual result (FAIL > WARN > PASS)

## Relationship to Other Commands

- `/test` — Runs only pytest (quick feedback loop)
- `/lint` — Runs only ruff (quick style check)
- `/verify` — Runs ALL stages (comprehensive pre-commit/pre-PR check)
- `/security-audit` — Deep code-level OWASP analysis (heavier than Stage 4)

## When to Use

- Before creating a commit (quick: `/verify pre-commit`)
- Before creating a PR (full: `/verify`)
- After major refactoring (full: `/verify`)
- CI pipeline equivalent for local development
