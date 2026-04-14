Save a manual checkpoint of current session state for recovery or context switching.

Usage: `/checkpoint [create|verify|list] [label]`

Arguments: $ARGUMENTS

## What Gets Saved

A checkpoint captures the current working context:

```markdown
# Checkpoint: [label or auto-generated]
**Saved:** 2024-01-15 14:30:00
**Branch:** feature/add-auth

## Current Task
- Task ID: 7
- Title: Implement JWT authentication
- Status: in-progress

## Recent Commits (last 3)
- `abc1234` feat: Add token generation utility
- `def5678` test: Add token validation tests
- `ghi9012` refactor: Extract auth middleware

## Active Reasoning
[Summary of current approach, decisions made, and why]

## Files Recently Modified
- `src/auth/tokens.py` — JWT generation/validation
- `src/auth/middleware.py` — Auth middleware
- `tests/test_tokens.py` — Token tests

## Next Steps
1. [Immediate next action]
2. [Following action]
3. [After that]

## Open Questions
- [Any unresolved decisions]
```

## Saved Location

`.claude/sessions/checkpoint-YYYYMMDD-HHMMSS.md`

## Use Cases

| Situation | Why Checkpoint |
|-----------|---------------|
| Before risky operation | Rollback reference if something breaks |
| At milestone | Mark progress before moving to next phase |
| Before context switch | Save state so you can resume later |
| Before suggesting fresh session | Capture what matters before context resets |
| End of work session | Quick state dump for tomorrow |

## Integration with session-init.sh

The `session-init.sh` hook automatically detects checkpoints:
- Scans `.claude/sessions/checkpoint-*.md` for files < 24 hours old
- Displays most recent checkpoint in "Last Session" section
- Helps Claude resume context in new sessions

## Relationship to Other Session Tools

| Tool | Trigger | Content |
|------|---------|---------|
| `session-end.sh` | Auto (on Stop) | Detailed session transcript summary |
| `session-init.sh` | Auto (on Start) | Loads recent session/checkpoint context |
| `/checkpoint` | Manual | Intentional state save at key moments |
| Work log | Manual | Decision rationale and research notes |

`/checkpoint` fills the gap between automatic session hooks and the manual work log — it's a quick, structured state dump you trigger when it matters.

## Timestamp Consistency

Uses the same format as `session-end.sh`: `YYYYMMDD-HHMMSS`
This ensures alphabetical sorting equals chronological sorting in `.claude/sessions/`.

## When to Use

- "I'm about to try something risky" → `/checkpoint before-risky-refactor`
- "This is a good stopping point" → `/checkpoint milestone-auth-complete`
- "Switching to a different task" → `/checkpoint pausing-task-7`
- "Context getting heavy, need fresh session" → `/checkpoint pre-refresh`

## Verify Against Checkpoint

`/checkpoint verify <label>`

Compare current state against a named checkpoint:

1. Find the checkpoint file matching the label
2. Compare:
   - Files added/modified/deleted since checkpoint
   - Test pass rate now vs then (run `/verify quick`)
   - Git commits since checkpoint
3. Report:

```
CHECKPOINT COMPARISON: milestone-auth-complete
===============================================
Since checkpoint (2h 15m ago):
  Files changed:  +3 added, 2 modified, 0 deleted
  Commits:        4 new commits
  Tests:          42 passed (was 38) — +4 new tests
  Build:          PASS

Verdict: PROGRESSING (no regressions detected)
```

## List Checkpoints

`/checkpoint list`

Show all checkpoints with name, timestamp, age, and git SHA.
