# Workflow Pipeline Test Results

**Date**: 2026-02-20
**Tester**: Claude Opus 4.6
**Project**: postiz_social_automation (bootstrapped from project-template via init-project.sh copy mode)

## Phase Results

### Phase 1: Bootstrap Verification

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1.1 | Rules loaded | **PARTIAL** | 8 core rules auto-loaded. 5 language rules exist in subdirs (`rules/python/`, etc.) but NOT auto-loaded by Claude Code (only top-level `*.md` loaded). Total: 13 files, 8 active. |
| 1.2 | Commands registered | **PASS** | 48 commands found. `/health` executes successfully. |
| 1.3 | Skills available | **PASS** | 39 skills in `.claude/skills/` + Superpowers skills all listed and invocable. |
| 1.4 | Agents visible | **PASS** | 13 agents defined, matches expected count exactly. |
| 1.5 | CLAUDE.md parsed | **PASS** | "Postiz Social Media Automation" recognized in context. |
| 1.6 | CLAUDE.md parent merge | **PASS** | Parent ISKCON-GN CLAUDE.md merges cleanly, both visible in context. |
| 1.7 | Task Master config | **PASS** | Initialized, empty task list, CLI and MCP both functional. |
| 1.8 | MCPs available | **PASS** | task-master-ai + context7 loaded (plus playwright, ide from VS Code). |

**Phase 1: 7 PASS, 1 PARTIAL**

### Phase 2: Commit Bootstrap

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 2.1 | Commit bootstrap files | **PASS** | 146 files, 19,487 insertions. Conventional commit format. |
| 2.2 | Git status clean | **PASS** | No uncommitted files after commit. |

**Phase 2: 2 PASS**

### Phase 3: PRD Parse Pipeline

| # | Step | Result | Notes |
|---|------|--------|-------|
| 3.1 | Create tag | **PASS** (after fix) | Failed initially: `.taskmaster/tasks/` dir missing. Fixed with `mkdir -p`. |
| 3.2 | Switch tag | **PASS** | Worked immediately after tag creation. |
| 3.3 | Parse PRD (CLI) | **PASS** | 9 tasks generated. CLI used successfully (not MCP). |
| 3.4 | Analyze complexity (CLI) | **PASS** (after fix) | Failed initially: `.taskmaster/reports/` dir missing. Fixed with `mkdir -p`. |
| 3.5 | Expand complex tasks | **PASS** | Task 8 expanded to 4 subtasks based on complexity report. |

**Phase 3: 5 PASS (2 required manual directory fixes)**

### Phase 4: TDD Implementation

| # | Step | Result | Notes |
|---|------|--------|-------|
| 4.1 | Pick task | **PASS** | Task 1 (setup) + Task 2 (storage) selected. |
| 4.2 | Set in-progress | **PASS** | `task-master set-status --id=2 --status=in-progress` |
| 4.3 | RED | **PASS** | 12 tests written first, all fail with `ModuleNotFoundError`. |
| 4.4 | GREEN | **PASS** | `health_storage.py` implemented, 12/12 tests pass. |
| 4.5 | REFACTOR | **PASS** | Code already clean, no refactoring needed. Tests still pass. |
| 4.6 | Commit | **PASS** | Conventional commit with RED/GREEN summary. |
| 4.7 | Mark done | **PASS** | Task 2 status set to done. |

**Phase 4: 7 PASS**

### Phase 5: Superpowers Routing Verification

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 5.1 | Brainstorming exit routing | **PASS** | `superpowers-integration.md` rule loaded, overrides brainstorming's default `writing-plans` exit with PRD pipeline. |
| 5.2 | TDD enforced | **PASS** | TDD cycle followed in Phase 4: tests first, then implementation. |
| 5.3 | Verification skill | **PASS** | Tests verified passing before commit/completion claims. |

**Phase 5: 3 PASS**

## Friction Log Summary

| ID | Phase | Severity | Issue |
|----|-------|----------|-------|
| F1 | 1.1 | MEDIUM | Language rules in subdirs not auto-loaded by Claude Code |
| F2 | 1.1 | INFO | No instincts dir at bootstrap (by design) |
| F3 | 1.8 | INFO | 4 MCPs loaded vs expected 2 (IDE extras) |
| F4 | health | LOW | sync-template.sh missing in copy mode |
| F5 | 1.7 | LOW | Dual tasks.json paths (seed vs CLI) |
| F6 | 3.1 | **HIGH** | `.taskmaster/tasks/` dir missing after init -- CLI fails |
| F7 | 3.4 | **HIGH** | `.taskmaster/reports/` dir missing -- analyze-complexity fails |
| F8 | 3.3 | INFO | CLI parse-prd runs AI call twice (token waste) |
| F9 | 4.1 | LOW | First available task is scaffolding, not TDD-friendly |
| F10 | 4.4 | INFO | pyproject.toml needs build-system for scripts-only project |

**Severity breakdown: 0 BLOCKER, 2 HIGH, 1 MEDIUM, 3 LOW, 4 INFO**

See `docs/WORKFLOW_FRICTION.md` for full details and resolutions.

## Key Findings

### What Works Well

1. **Rule system**: 8 core rules loaded reliably, govern behavior throughout the session. Authority hierarchy (rules > instincts > defaults) is clear and enforceable.

2. **Superpowers integration**: The `superpowers-integration.md` override of brainstorming's exit routing works correctly. TDD workflow is enforceable. The decision tree (trivial fix vs TDD vs PRD pipeline) provides clear guidance.

3. **Task Master CLI**: Parse-PRD, analyze-complexity, expand, set-status all work correctly once directory structure is fixed. Dependency chains are well-formed.

4. **Command/skill ecosystem**: 48 commands, 39 skills, 13 agents all available. `/health` demonstrated working command invocation.

5. **TDD cycle**: RED-GREEN-REFACTOR demonstrated cleanly. 12 tests written first (all failing), then implementation making all 12 pass.

6. **Parent CLAUDE.md merge**: Parent project context (ISKCON-GN) merges cleanly with child project context (postiz). No conflicts.

### What Doesn't Work

1. **init-project.sh directory structure**: The two HIGH friction items (F6, F7) both stem from `init-project.sh` not creating the directory structure that `task-master` CLI expects. Fix: add `mkdir -p .taskmaster/tasks .taskmaster/reports` to init-project.sh.

2. **Language rules not auto-loaded**: The 5 language-specific rules in subdirectories are invisible to Claude Code. If they should always be active, they need to be at the top level of `.claude/rules/`.

### Surprises

1. **MCP AI operations work via CLI but require directory pre-creation**: The `claude-code` provider MCP limitation is real (can't spawn nested Claude), but the CLI works fine. However, it doesn't auto-create its own directories.

2. **Token usage**: The PRD parse appears to run the AI call twice, consuming ~688k tokens for what should be ~344k. This is a task-master CLI bug.

3. **Complexity analysis is conservative**: 6 of 9 tasks rated low complexity, 3 medium, 0 high. Only 1 task actually recommended expansion. This seems reasonable for a well-specified PRD.

## Recommendations

### Template Fixes Needed

1. **[HIGH] Fix init-project.sh**: Add these directories to the initialization:
   ```bash
   mkdir -p .taskmaster/tasks .taskmaster/reports
   ```
   And copy the seed tasks.json into the CLI-expected path.

2. **[MEDIUM] Decide on language rules**: Either:
   - Move them to top-level `.claude/rules/` so they auto-load, OR
   - Document that they're opt-in and require explicit invocation via skills

3. **[LOW] /health command**: Add graceful handling for missing `sync-template.sh` in copy-mode bootstraps.

### Task Master CLI Issues

4. **[MEDIUM] Double AI call**: `parse-prd` appears to run the AI call twice. Should be investigated in task-master-ai.

5. **[LOW] Auto-create directories**: `analyze-complexity` should auto-create `.taskmaster/reports/` if it doesn't exist.

### Test Plan Adjustments

6. **[LOW] Clarify rule count**: Change "8 core + 5 language rules present" to "8 core rules auto-loaded + 5 language rules available in subdirs".

7. **[LOW] TDD task selection**: Suggest picking a task with testable logic (not scaffolding) for the TDD phase.

## Session Stats

- **Tool calls**: ~45 (Bash, Read, Write, Edit, Glob, Grep, Skill, MCP)
- **Commits**: 3 (bootstrap, project setup, TDD implementation)
- **Tests written**: 12 (all passing)
- **Tasks completed**: 2 of 9 (tasks #1 and #2)
- **Files created**: ~150 (bootstrap) + 4 (implementation)
- **Friction items logged**: 10 (0 blocker, 2 high, 1 medium, 3 low, 4 info)

## Overall Verdict

**The project-template pipeline works end-to-end** with two required manual fixes (directory creation). Once `init-project.sh` is updated to create the correct Task Master directory structure, the workflow is smooth from bootstrap through PRD parsing through TDD implementation. The superpowers routing overrides work as designed.
