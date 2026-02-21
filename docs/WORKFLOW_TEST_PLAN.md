# Workflow Pipeline Test Plan

## Purpose

End-to-end validation that the project-template infrastructure works correctly when bootstrapped onto a standalone project via `init-project.sh` (copy mode). Tests the full pipeline: bootstrap → verify → brainstorm → PRD → parse → analyze → expand → TDD.

## Pre-Conditions (completed by template session)

- [x] `init-project.sh` run successfully (copy mode, 136 files across 6 dirs)
- [x] CLAUDE.md customized for postiz project
- [x] .taskmaster/ initialized with config.json and empty tasks.json
- [x] PRD written at `.taskmaster/docs/prd_health_monitoring.txt`
- [x] .gitignore updated with Claude Code exclusions
- [x] Nothing committed yet (let this session handle it)

## Test Phases

### Phase 1: Bootstrap Verification (non-destructive)

| # | Check | How | Expected |
|---|-------|-----|----------|
| 1.1 | Rules loaded | Check system context for rule mentions | 8 core + 5 language rules present |
| 1.2 | Commands registered | Try `/health` or `/tasks` | Commands execute, not "unknown skill" |
| 1.3 | Skills available | Try `/code-review` or check skill list | Skills listed and invocable |
| 1.4 | Agents visible | Check agent definitions | 13 agents defined |
| 1.5 | CLAUDE.md parsed | Check project identity in context | "Postiz Social Media Automation" recognized |
| 1.6 | CLAUDE.md parent merge | Check for ISKCON-GN parent content | Parent CLAUDE.md merges without conflict |
| 1.7 | Task Master config | `task-master list` | Empty task list, no errors |
| 1.8 | MCPs available | Check MCP tool count | task-master-ai + context7 loaded |

### Phase 2: Commit Bootstrap

- Commit all bootstrapped files (.claude/, .taskmaster/, CLAUDE.md, .gitignore)
- Verify git status clean after commit

### Phase 3: PRD Parse Pipeline

| # | Step | Command | Watch For |
|---|------|---------|-----------|
| 3.1 | Create tag | `task-master tags add health-monitoring` | Tag created |
| 3.2 | Switch tag | `task-master tags use health-monitoring` | Context switched |
| 3.3 | Parse PRD | CLI: `task-master parse-prd .taskmaster/docs/prd_health_monitoring.txt --num-tasks 0` | Tasks generated (MCP will fail — use CLI) |
| 3.4 | Analyze complexity | CLI: `task-master analyze-complexity` | Complexity report generated |
| 3.5 | Expand complex tasks | CLI: `task-master expand --id=<id>` for flagged tasks | Subtasks created |

**CRITICAL**: Steps 3.3-3.5 MUST use CLI, not MCP. The `claude-code` provider tries to spawn a nested Claude subprocess which is blocked.

### Phase 4: TDD Implementation (pick ONE task)

| # | Step | What | Watch For |
|---|------|------|-----------|
| 4.1 | Pick task | `task-master next` | Returns a task with subtasks |
| 4.2 | Set in-progress | `task-master set-status --id <id> --status=in-progress` | Status updated |
| 4.3 | RED | Write failing test first (Superpowers TDD enforced) | Test file created, test fails |
| 4.4 | GREEN | Implement minimum code to pass | Test passes |
| 4.5 | REFACTOR | Clean up if needed | Tests still pass |
| 4.6 | Commit | `/commit` | Conventional commit created |
| 4.7 | Mark done | `task-master set-status --id <id> --status=done` | Status updated |

### Phase 5: Superpowers Routing Verification

| # | Check | What | Expected |
|---|-------|------|----------|
| 5.1 | Brainstorming exits correctly | After brainstorming, does NOT invoke writing-plans | Routes to PRD per superpowers-integration.md rule |
| 5.2 | TDD enforced | Try writing code without test first | Superpowers blocks or warns |
| 5.3 | Verification skill | After implementation, verification-before-completion fires | Evidence before assertions |

## Friction Log Format

Record issues in `docs/WORKFLOW_FRICTION.md` using this format:

```markdown
| ID | Phase | Severity | Issue | Resolution |
|----|-------|----------|-------|------------|
| F1 | 1.2   | HIGH     | /health returns "unknown skill" | [what fixed it or "OPEN"] |
```

Severity: BLOCKER (can't continue), HIGH (workaround needed), MEDIUM (friction but works), LOW (cosmetic), INFO (observation)

## Report-Back Format

When session is done, create `docs/WORKFLOW_TEST_RESULTS.md` with:

1. **Phase results table** (PASS/FAIL/PARTIAL per check)
2. **Friction log** (all issues found)
3. **Key findings** (what works, what doesn't, what surprised you)
4. **Recommendations** (fixes needed in the template)
5. **Session stats** (approximate tool calls, context usage, duration)
