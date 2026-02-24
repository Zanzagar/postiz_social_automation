# Session Handoff — 2026-02-24 (Phase 6 Implementation + Architecture Discussion)

## What Was Done This Session

### Task 1: Infrastructure Verification — DONE
- Postiz v2.18.0 at sethpc.xyz: dashboard, API (148 endpoints), n8n all healthy
- API key verified working (no Bearer prefix, just raw key in Authorization header)
- Postiz has Swagger docs at `/api/docs`, MCP server, and payload wizard
- Health check script: `scripts/postiz-health-check.sh`
- Commit: `ded866b`

### Task 8: Content Calendar Schema — DONE
- Google Apps Script: `scripts/setup-content-calendar.gs` (auto-configures sheet)
- Sample data: `data/sample-content-calendar.csv` (8 Gita Valley rows)
- `.env.example` updated with automation layer vars
- Commit: `ff9f2a8`

### Tasks 2-7: Platform Connections — BLOCKED
- Marked `blocked` — waiting on temple president for social media credentials
- Postiz "Add Channel" UI explored: supports 30+ platforms including all 5 targets

### Research: n8n + Postiz Ecosystem — 3 docs created
- `docs/research/n8n-workflow-patterns.md` — 488 templates analyzed, top matches identified
- `docs/research/postiz-n8n-integration.md` — API reference, rate limits, node bugs
- `docs/research/content-generation-strategy.md` — 3-layer content gen approach
- Commit: `75b2d36`

### Dogfood Checklist: Phase 6 Updated
- Findings #9-11 logged (TDD N/A for config tasks, missing research step, external deps)
- Phase 6 checks: 12 pass, 3 fail, 12 skip
- Commit: `2e0faf7`

## Current State

- **Branch**: `feature/postiz-mvp` (4 commits ahead of main)
- **Tag**: `master` (postiz-mvp tag creation failed earlier)
- **Tasks**: 1 done, 8 done, 2-7 blocked, rest pending
- **Postiz login**: coreyhoydic@gmail.com (password in conversation history, NOT saved to files)

## Critical Research Findings (must inform architecture discussion)

1. **Postiz n8n custom node is buggy** — Instagram fails with 400 errors (Issue #7). USE HTTP Request nodes.
2. **Rate limit: 30 requests/hour** — batch all platforms in single POST /posts call
3. **Postiz has MCP server** — Claude could schedule posts directly, bypassing n8n for simple flows
4. **n8n template #11996** is closest architecture match (Sheets → multi-platform via API)
5. **Content pattern extraction possible** via Apify scraping (Template #9100, ~$49/mo)
6. **No Claude templates exist** — all n8n social media templates use OpenAI
7. **Postiz payload wizard** available in Settings > Public API for building correct JSON payloads

## Architecture Discussion Needed (NEXT SESSION PRIORITY)

The user wants to discuss architecture before continuing implementation. Key questions:

### 1. n8n vs Postiz MCP vs Direct API
- **n8n**: Visual workflow builder, good for complex multi-step pipelines, version-controllable JSON
- **Postiz MCP**: Claude schedules directly, simpler, no n8n dependency for basic flows
- **Direct API**: Python/Node scripts, most control, least visual
- **Hybrid**: n8n for complex flows (sheet reading, AI generation), Postiz MCP for simple scheduling

### 2. HTTP Request vs Custom Node
- Already decided: HTTP Request (custom node is buggy)
- But: should we build workflow JSON locally and import, or build in n8n UI?
- Research says: JSON export/import for version control, build initially in UI for prototyping

### 3. Content Generation Simplification
- User wants to reduce farm staff workload
- Current: staff writes raw text + selects pillar + selects platforms
- Could be simpler: staff takes photo + writes 1 sentence, AI does everything else
- Pattern extraction from competitor accounts could inform AI prompts

### 4. Rate Limit Strategy
- 30 req/hour = ~15 content pieces/hour with media
- Batch posting (all platforms in one API call) is essential
- Pre-fetch and cache integrations list
- Schedule posts in advance rather than posting immediately

## Key Files

- Research: `docs/research/n8n-workflow-patterns.md`, `postiz-n8n-integration.md`, `content-generation-strategy.md`
- Infrastructure: `docs/INFRASTRUCTURE_STATUS.md`
- Design doc: `docs/plans/2026-02-23-social-automation-pipeline-design.md`
- PRD: `.taskmaster/docs/prd_social_automation.txt`
- Tasks: `.taskmaster/tasks/tasks.json` (30 tasks, 41 subtasks)
- Dogfood: `docs/DOGFOOD_CHECKLIST.md`

## Resume Instructions

```
Read .claude/sessions/handoff-20260224-phase6-architecture.md and MEMORY.md

Then: Let's discuss the architecture questions from the handoff before continuing implementation.
```
