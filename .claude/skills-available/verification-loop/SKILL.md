---
name: verification-loop
description: 6-phase verification system with build, types, lint, test, security, and diff review stages. Continuous verification mode for long sessions.
---
# Verification Loop Skill

## 6-Phase Verification Pipeline

Run verification in order — each phase gates the next:

```
Phase 1: BUILD ──► Phase 2: TYPES ──► Phase 3: LINT ──►
Phase 4: TEST ──► Phase 5: SECURITY ──► Phase 6: DIFF REVIEW

Result: READY | NOT READY | PARTIAL (some phases skipped)
```

### Phase 1: Build
Verify the project compiles/builds without errors.

| Language | Command | What It Catches |
|----------|---------|-----------------|
| Python | `python -m py_compile src/**/*.py` | Syntax errors, encoding issues |
| TypeScript | `tsc --noEmit` | Type errors, missing imports |
| Go | `go build ./...` | Compilation errors, unresolved deps |
| Java | `mvn compile` / `gradle build` | Compilation, dependency resolution |
| Rust | `cargo check` | Borrow checker, type errors |

### Phase 2: Types
Static type checking catches errors before runtime.

| Language | Command | Key Flags |
|----------|---------|-----------|
| Python | `mypy src/` | `--strict` for full checking |
| TypeScript | `tsc --noEmit --strict` | Already in Phase 1 for TS |
| Go | `go vet ./...` | Catches suspicious constructs |
| Java | Built into compile | Inherent in Java |

### Phase 3: Lint
Style and quality enforcement.

| Language | Command | Auto-fix |
|----------|---------|----------|
| Python | `ruff check .` | `ruff check . --fix` |
| TypeScript | `eslint .` | `eslint . --fix` |
| Go | `golangci-lint run` | Some linters auto-fix |
| Java | `spotbugs` / `checkstyle` | Manual fixes |
| General | `prettier --check .` | `prettier --write .` |

### Phase 4: Test
Run the full test suite with coverage.

| Language | Command | Coverage |
|----------|---------|----------|
| Python | `pytest --cov=src --cov-report=term-missing` | 80%+ target |
| TypeScript | `jest --coverage` or `vitest --coverage` | 80%+ target |
| Go | `go test -cover ./...` | 80%+ target |
| Java | `mvn test jacoco:report` | 80%+ target |

### Phase 5: Security
Scan for known vulnerabilities and insecure patterns.

| Scope | Tool | What It Finds |
|-------|------|---------------|
| Python code | `bandit -r src/` | Hardcoded secrets, SQL injection, unsafe deserialization |
| Python deps | `pip-audit` or `safety check` | Known CVEs in dependencies |
| Node deps | `npm audit` | Known CVEs in node_modules |
| Go deps | `govulncheck ./...` | Go vulnerability database |
| Config | `npx ecc-agentshield scan` | CLAUDE.md secrets, hook injection, MCP misconfig |

### Phase 6: Diff Review
Review the actual changes before committing.

```bash
# What changed?
git diff --stat

# Review each file
git diff -- src/

# Check for:
# - Debug statements left in (print, console.log)
# - Hardcoded credentials or paths
# - TODOs that should be resolved
# - Files that shouldn't be committed (.env, credentials)
```

## Phase Results

Each phase produces one of:

| Result | Meaning | Action |
|--------|---------|--------|
| **PASS** | Phase succeeded | Proceed to next phase |
| **FAIL** | Phase found issues | Fix before proceeding |
| **SKIP** | Tool not installed | Note and proceed (not a blocker) |
| **WARN** | Non-critical issues | Proceed but review findings |

**SKIP is not FAIL.** If a project doesn't use TypeScript, the types phase is SKIP — that's fine. The pipeline adapts to the project's actual toolchain.

## Continuous Verification Mode

For long implementation sessions, run lightweight verification after every significant change:

```
After each function/method:
  └─ Run: test (just the relevant test file)

After each feature:
  └─ Run: lint + test (full suite)

Before each commit:
  └─ Run: ALL 6 phases

Before PR:
  └─ Run: ALL 6 phases + manual diff review
```

### Quick Verification Commands

```bash
# Python — single file test
pytest tests/test_specific.py -x -q

# Python — full verification
pytest && ruff check . && mypy src/

# Go — single package
go test ./internal/kriging/ -v

# TypeScript — single file
npx jest path/to/test.ts

# Universal — full pipeline
/verify
```

## Integration with TDD

The verification loop and TDD cycle are complementary:

```
TDD Cycle (per feature):
  RED → write failing test
  GREEN → make it pass
  REFACTOR → clean up
  └─ Quick verify: test + lint

Verification Loop (per milestone):
  All 6 phases
  └─ Commit if READY
```

## Troubleshooting

| Symptom | Likely Phase | Fix |
|---------|-------------|-----|
| Import errors at runtime | Build | Check PYTHONPATH, virtual env |
| "Type X is not assignable" | Types | Fix type annotations or add casts |
| Style warnings flood | Lint | Run auto-fix first, then manual |
| Tests pass locally, fail in CI | Test | Check env differences, test isolation |
| Known CVE in dependency | Security | Update dependency or add exception |
