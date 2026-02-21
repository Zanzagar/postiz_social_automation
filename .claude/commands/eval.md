Evaluate code quality with feature-level eval definitions and project-wide metrics.

Usage: `/eval [define|check|report|list|metrics] [feature-name]`

Arguments: $ARGUMENTS

## Subcommands

### `/eval define <feature-name>`

Create a new eval definition for a specific feature:

1. Create `.claude/evals/<feature-name>.md`:

```markdown
## EVAL: <feature-name>
Created: $(date)

### Capability Evals
- [ ] [Specific capability 1 that should work]
- [ ] [Specific capability 2 that should work]
- [ ] [Edge case that should be handled]

### Regression Evals
- [ ] [Existing behavior 1 still works]
- [ ] [Existing behavior 2 still works]

### Success Criteria
- pass@3 > 90% for capability evals
- pass^3 = 100% for regression evals
```

2. Prompt user to fill in specific criteria for their feature.

**Eval Metrics Explained:**
- `pass@k`: At least one success in k attempts (capability — "can it do this?")
- `pass^k`: All k attempts succeed (regression — "does this always work?")

### `/eval check <feature-name>`

Run evals for a feature:

1. Read eval definition from `.claude/evals/<feature-name>.md`
2. For each **capability eval**:
   - Attempt to verify the criterion (run test, manual check, or code inspection)
   - Record PASS/FAIL
   - Log attempt in `.claude/evals/<feature-name>.log`
3. For each **regression eval**:
   - Run relevant tests
   - Compare against baseline behavior
   - Record PASS/FAIL
4. Report:

```
EVAL CHECK: <feature-name>
========================
Capability: X/Y passing (pass@1: Z%)
Regression: X/Y passing (pass^1: Z%)
Status: IN PROGRESS / READY / BLOCKED
```

### `/eval report <feature-name>`

Generate comprehensive eval report:

```
EVAL REPORT: <feature-name>
===========================
Generated: $(date)

CAPABILITY EVALS
────────────────
[eval-1]: PASS (pass@1)
[eval-2]: PASS (pass@2) — required retry
[eval-3]: FAIL — see notes

REGRESSION EVALS
────────────────
[test-1]: PASS (pass^3)
[test-2]: PASS (pass^3)
[test-3]: PASS (pass^3)

METRICS
───────
Capability pass@1: 67%
Capability pass@3: 100%
Regression pass^3: 100%

NOTES
─────
[Issues, edge cases, or observations]

RECOMMENDATION
──────────────
[SHIP / NEEDS WORK / BLOCKED]
```

### `/eval list`

Show all eval definitions:

```
EVAL DEFINITIONS
================
feature-auth      [3/5 passing] IN PROGRESS
feature-search    [5/5 passing] READY
feature-export    [0/4 passing] NOT STARTED
```

### `/eval metrics`

Run project-wide quality metrics (the quick health check):

```bash
# Test coverage
pytest --cov=src --cov-report=term-missing -q 2>/dev/null   # Python
npx jest --coverage 2>/dev/null                              # JS/TS
go test -cover ./... 2>/dev/null                             # Go

# Lint score
ruff check . --output-format=json 2>/dev/null                # Python
npx eslint . --format json 2>/dev/null                       # JS/TS

# Type coverage
mypy src/ --txt-report /dev/stdout 2>/dev/null               # Python
npx tsc --noEmit 2>&1 | tail -1                              # TS

# Complexity
radon cc src/ -a -nc 2>/dev/null                             # Python
```

Output:

```markdown
| Metric              | Current | Previous | Trend |
|---------------------|---------|----------|-------|
| Test Coverage       | 82%     | 78%      | +4% ↑ |
| Lint Score          | 0.3/kloc | 0.5/kloc | +40% ↑ |
| Type Coverage       | 91%     | 91%      | — |
| Avg Complexity      | 6.2     | 7.1      | +13% ↑ |

Overall Health: GOOD (all metrics trending positive)
```

If `--save` flag: Save to `.claude/evals/metrics_YYYYMMDD_HHMMSS.json`

### `/eval clean`

Remove old eval logs (keeps last 10 runs per feature).

## Saved Metrics Format

```json
{
  "timestamp": "2026-02-13T14:30:00Z",
  "metrics": {
    "test_coverage": 82.0,
    "lint_score": 0.3,
    "type_coverage": 91.0,
    "avg_complexity": 6.2
  },
  "details": {
    "tests": { "passed": 42, "failed": 0, "skipped": 2 },
    "lint_issues": [ { "file": "src/utils.py", "line": 42, "message": "..." } ]
  }
}
```

## Integration with /health

The `/health` command checks for recent evals:
- If last eval > 7 days ago → recommend running `/eval metrics`
- Shows latest metrics in health report summary

## Graceful Degradation

Missing tools are handled gracefully:
- No pytest-cov → skip coverage, note in output
- No radon → skip complexity, note in output
- No previous eval → skip comparison, show current only

## When to Use

| Subcommand | When |
|------------|------|
| `define` | Starting a new feature — define what "done" means |
| `check` | During development — track progress toward done |
| `report` | Before PR — prove feature readiness |
| `list` | Sprint planning — see what's ready vs in progress |
| `metrics` | Weekly cadence, before releases, after refactoring |
