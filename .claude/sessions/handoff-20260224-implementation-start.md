# Session Handoff — 2026-02-24 (Implementation Start)

## What Was Done This Session

### Architecture Revision
- Dropped n8n entirely (Claude OAuth incompatible with n8n AI nodes)
- New stack: Streamlit Content Hub + Python Content Engine + Claude CLI (OAuth) + Postiz
- Two-mode pipeline: Mode 1 (Enhance — staff input) + Mode 2 (Suggest — AI proactive)
- Content intelligence layer with meta-learning from post performance
- Streamlit = staff-facing UI (free, open source, Apache 2.0)

### Documents Written
- Design doc v2: `docs/plans/2026-02-24-social-automation-pipeline-design-v2.md`
- PRD v2: `.taskmaster/docs/prd_social_automation_v2.txt` (7 phases, includes Streamlit)
- Both supersede v1 documents (v1 still in repo for reference)

### Task Master Setup
- Tag: `content-engine-v2` (MUST switch to this tag before any task operations)
- 25 tasks, 10 expanded into 53 subtasks
- Complexity: 10 medium (all expanded), 15 low
- Task 1 (Initialize Python Project Structure) is first

### Dogfood Findings #12-15
- #12: Claude attempted `expand --all` (rule violation)
- #13: Perplexity `--research` produces incomplete results for >10 tasks
- #14: Parsed into wrong tag (master instead of new tag)
- #15: `--num=0` misinterpreted as "no expansion" (means "float")

### Commits (5 this session)
- `ba9326e` docs: Add v2 architecture — drop n8n, add Python content engine
- `ddef5f1` docs: Add Streamlit Content Hub to v2 architecture
- `e6a20e0` chore: Parse v2 PRD into content-engine-v2 tag with complexity analysis
- `3c7624c` chore: Expand remaining score-5 tasks (11, 13, 16, 25)
- `3cb7445` docs: Add dogfood finding #15

## Current State

- **Branch**: `feature/postiz-mvp` (10 commits ahead of main)
- **Tag**: `content-engine-v2` (active)
- **All tasks**: pending (none started)
- **Dogfood mode**: Light — build normally, check off dogfood items as they occur, ensure all items eventually marked

## Stale Data to Clean Up

- `master` tag has stale v1 tasks (1-30) + incorrectly-parsed v2 tasks (31-58). Not blocking but should be cleaned eventually.

## Next Steps (ordered)

1. `task-master tags use content-engine-v2`
2. `task-master next` → Task 1: Initialize Python Project Structure
3. Build with TDD (superpowers:test-driven-development)
4. Follow task dependency order: 1 → 2 → 3,4,5,6,7 → 8,9 → 10-14 → 15-17 → 18 → 19-24 → 25
5. Commit after each task completion
6. Check off dogfood items as they naturally occur during implementation

## Key Gotchas (from MEMORY.md)

- **Tag**: Always `task-master tags use content-engine-v2` before any task operation
- **CLI for AI ops**: Use CLI (not MCP) for parse-prd, expand, analyze-complexity, update-subtask
- **CLI AI flags**: `--force` (no interactive prompt), long Bash timeout (900000ms), no `2>&1`
- **NEVER**: `expand --all`, `--research` with analyze-complexity, parse into wrong tag
- **`--num=0`**: Means "float" not "zero" — always expand score >= 5 tasks

## Resume Instructions

```
Read .claude/sessions/handoff-20260224-implementation-start.md and MEMORY.md

Then: Start implementation. task-master tags use content-engine-v2, then task-master next.
Dogfood-light mode: build normally, log findings when something surprising happens.
```
