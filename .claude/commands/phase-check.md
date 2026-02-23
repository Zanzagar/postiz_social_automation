# Phase Check

Validate prerequisites for the current workflow phase. Reports pass/warn/fail status with actionable fix suggestions.

**Usage:** `/phase-check [phase]` where phase is IDEATION, PLANNING, BUILDING, REVIEW, or SHIPPING.

Arguments: $ARGUMENTS

## Instructions

### Step 1: Detect Phase

If a phase argument is provided, use it directly. Otherwise auto-detect from context:

1. Check `task-master list --status in-progress` — if tasks are in-progress → **BUILDING**
2. Check for PRD files (`ls .taskmaster/docs/prd_*.txt`) without parsed tasks → **PLANNING**
3. Check `git log origin/main..HEAD 2>/dev/null` — if commits exist and no open PR → **SHIPPING**
4. Default → **IDEATION**

### Step 2: Run Phase-Specific Checks

For the detected phase, check these prerequisites and report status using the symbols: PASS, WARN (advisory), FAIL (blocking).

#### IDEATION Phase

| Prerequisite | Check | Expected |
|---|---|---|
| No blockers | Always passes | PASS |

Suggestions: If starting fresh, suggest `/brainstorm`. If requirements already exist, suggest moving to PLANNING.

#### PLANNING Phase

| Prerequisite | Check | Expected |
|---|---|---|
| PRD exists | `ls .taskmaster/docs/prd_*.txt 2>/dev/null` | PASS if files found, FAIL if none |
| Tasks parsed | `task-master list` returns tasks | PASS if tasks exist, FAIL if none |
| Complexity analyzed | Check `.taskmaster/reports/` for complexity report | PASS if found, WARN if missing |

Fix suggestions:
- No PRD: "Create PRD: `/prd-generate <concept>` or write to `.taskmaster/docs/prd_<name>.txt`"
- No tasks: "Parse PRD: `task-master parse-prd --input=<file> --num-tasks=0`"
- No complexity report: "Analyze: `task-master analyze-complexity`"

#### BUILDING Phase

| Prerequisite | Check | Expected |
|---|---|---|
| Task claimed | `task-master list --status in-progress` has results | PASS if found, WARN if none |
| Feature branch | `git branch --show-current` is not main/master | PASS if feature branch, FAIL if main |
| Tests exist | `ls tests/ 2>/dev/null` has files | PASS if found, WARN if empty |

Fix suggestions:
- No task: "Claim task: `task-master set-status <id> in-progress`"
- On main: "Create branch: `git checkout -b feature/<description>`"
- No tests: "Start TDD: Write a failing test first"

#### REVIEW Phase

| Prerequisite | Check | Expected |
|---|---|---|
| Tests passing | `pytest -q --tb=short` exits 0 | PASS if green, FAIL if red |
| Linter clean | `ruff check src/ tests/` exits 0 | PASS if clean, FAIL if errors |
| No debug statements | `grep -rE 'breakpoint\|pdb\.set_trace\|console\.log\|debugger' src/ tests/` | PASS if none found, WARN if found |

Fix suggestions:
- Tests failing: "Fix tests: `pytest -v` to see failures"
- Lint errors: "Fix lint: `ruff check --fix .`"
- Debug statements: "Remove debug statements from listed files"

#### SHIPPING Phase

| Prerequisite | Check | Expected |
|---|---|---|
| Branch pushed | `git rev-parse --abbrev-ref @{u} 2>/dev/null` succeeds | PASS if tracked, WARN if not |
| CHANGELOG updated | `git diff main..HEAD --name-only \| grep -i changelog` | PASS if modified, WARN if not |
| Task status | Check if current task is marked done | PASS if done, WARN if still in-progress |

Fix suggestions:
- Not pushed: "Push branch: `git push -u origin <branch>`"
- No CHANGELOG: "Update changelog: `/changelog`"
- Task not done: "Update status: `task-master set-status <id> done`"

### Step 3: Format Output

Report results in this format:

```
Phase Check: [PHASE]

  Prerequisite          Status    Action
  ─────────────────────────────────────────────
  [Name]                PASS      [detail]
  [Name]                FAIL      [fix command]
  [Name]                WARN      [suggestion]

Result: [PASS | WARN | FAIL] ([N] blocking issues)
```

If any FAIL items exist, show "Fix first: [highest priority fix action]" at the end.

### Implementation Notes

- **Lightweight**: Only read local state (git, filesystem, task-master CLI). No API calls.
- **Fast**: Should complete in under 2 seconds. Use `--tb=no` for pytest, check file existence before running commands.
- **Advisory**: Report but do not block. This is soft enforcement per `workflow-enforcement.md`.
- **Graceful**: If a tool isn't installed (pytest, ruff, task-master), show WARN instead of FAIL.
