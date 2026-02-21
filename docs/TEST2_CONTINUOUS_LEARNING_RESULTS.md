# Test 2: Continuous Learning Results

**Date**: 2026-02-20
**Tester**: Claude Opus 4.6
**Project**: postiz_social_automation

## Summary
| Step | Description | Result | Notes |
|------|-------------|--------|-------|
| 1 | Hook wiring | PASS | Merged Stop (2 hooks) + SessionStart (1 hook) into settings.local.json. Created .claude/instincts/candidates/. Required `git add -f` due to gitignore. |
| 2 | PRD re-parse | SKIP | Tasks already existed from Test 1 under health-monitoring tag (9 tasks, 2 done). No re-parse needed. |
| 3 | TDD implementation (3 tasks) | PASS | Implemented tasks 3, 4, 5 via RED-GREEN-REFACTOR. 28 new tests (13+10+5), all 40 passing. |
| 4 | /learn manual extraction | PASS | Extracted 4 instinct candidates across 4 categories (testing, python-patterns, project-conventions, git-workflow). |
| 5 | /instinct-status display | PASS | Displayed all 4 instincts grouped by category with confidence scores. All at Candidate level (0.4-0.5). |
| 6 | /instinct-export | PASS | Exported to .claude/instincts/export-2026-02-20.json. Note: default filter (>0.7) would export nothing — exported all candidates for demo. |
| 7 | /evolve clustering | SKIP | Only 1 instinct per category (need 3+). Correctly reported "no evolution opportunities." Expected outcome for single session. |
| 8 | Stop hooks fire on exit | PENDING | Hooks wired and verified (Stop hooks: 2). Actual execution can only be confirmed after session restart by checking .claude/sessions/ and .claude/instincts/candidates/. |

## Instincts Generated

| Pattern | Confidence | Category | Source |
|---------|-----------|----------|--------|
| mock-boundary-tdd | 0.50 | testing | session — Mock at module boundary for external service deps |
| dataclass-enum-results | 0.50 | python-patterns | session — @dataclass + Enum for structured result types |
| scripts-pythonpath-pattern | 0.50 | project-conventions | session — PYTHONPATH=scripts for flat module layout |
| gitignored-config-force-add | 0.40 | git-workflow | session — git add -f for gitignored .claude/ files |

## Friction Items Added

- **F11** (MEDIUM): gitignored hook config requires `git add -f`
- **F12** (INFO): tasks.json empty vs tag data persisting
- **F13** (LOW): /learn is purely instructional, no automation
- **F14** (LOW): /instinct-status has no rendering engine
- **F15** (LOW): /instinct-export default filter too restrictive for early projects
- **F16** (INFO): /evolve can't cluster in single session (by design)
- **F17** (INFO): Stop hooks can't be verified until after restart

## Key Findings

### What worked well
- **TDD cycle was smooth**: RED-GREEN-REFACTOR worked cleanly for all 3 tasks. Tests ran fast (<1.2s for all 40).
- **Hook wiring was straightforward**: Merging from settings-example.json into settings.local.json worked first try.
- **Instinct schema is simple and usable**: JSON files with pattern/trigger/action/confidence fields are easy to create and read.
- **Task Master tag persistence**: health-monitoring tag retained all 9 tasks from Test 1, enabling immediate continuation.
- **Mock-based testing**: All 3 modules (checker, notifier, monitor) were fully testable without Docker running.

### What didn't work
- **No automated instinct extraction**: /learn is instructions only — Claude manually creates JSON. No schema validation, no dedup check against existing instincts.
- **Instinct evolution impossible in 1 session**: The /evolve clustering requires 3+ active instincts (>0.7) in the same category. A single session can't reach this threshold because instincts start at 0.4-0.5 and need cross-session reinforcement.
- **Export default filter is too strict**: New projects have only candidates, so `/instinct-export` with default settings produces nothing useful.
- **Stop hooks are fire-and-forget**: No way to test them within the session. Must verify post-restart.

### Surprises
- **Gitignore blocks hook sharing**: The template's .gitignore excludes exactly the files needed for continuous learning (settings.local.json, instincts/). This creates friction for teams wanting to share learned patterns.
- **Skills are purely prompt-based**: /learn, /instinct-status, /instinct-export, and /evolve are all instruction-based skills that rely on Claude interpreting and following them correctly. There's no CLI tool or validation layer. This works but produces inconsistent output across invocations.

## Commits Made This Session

| Hash | Message |
|------|---------|
| f9878fb | chore: wire Stop and SessionStart hooks for continuous learning |
| 9aad98b | feat: implement Docker service health checker with TDD |
| eb280e0 | feat: implement state transition detection and webhook notification |
| c7320e2 | feat: implement main health monitor orchestrator |
| a83c457 | chore: extract 4 instinct candidates from TDD session |

## Test Suite Summary

```
40 passed in 1.18s

Breakdown:
- test_storage.py: 12 tests (from Test 1)
- test_health_checker.py: 13 tests (Task 3)
- test_health_notifier.py: 10 tests (Task 4)
- test_health_monitor.py: 5 tests (Task 5)
```
