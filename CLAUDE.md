# Project: Postiz Social Media Automation

Automation layer for Gita Valley (ISKCON Gita Nagari) social media scheduling using Postiz, Docker infrastructure with PostgreSQL, Redis, and Temporal.

## Tech Stack

- Python 3.11+
- Docker Compose (Postiz, PostgreSQL, Redis, Temporal)
- n8n (workflow automation, separate host)
- Postiz API (self-hosted social media scheduler)

## Structure

```
api/                  # FastAPI backend
  routes/             # Endpoint modules (content, media, calendar_plan, drive, etc.)
  models.py           # SQLAlchemy models (19 tables)
  schemas.py          # Pydantic request/response schemas
  repositories/       # Data access layer
frontend/             # React SPA (Vite + Tailwind + shadcn/ui)
  src/pages/          # Page components (Dashboard, Create, Calendar, Media, etc.)
  src/components/     # Reusable components (ContentEditor, CalendarPlanDialog, etc.)
  src/lib/api.ts      # Typed API client
src/content_engine/   # Content generation engine + CLI scripts
data/                 # SQLite DB + ISKCON festival calendar
docker-compose.yaml   # Postiz + PostgreSQL + Redis + Temporal
.taskmaster/          # Task Master data (tasks, PRDs, reports)
```

## Development Commands

```bash
# Docker infrastructure
docker compose up -d                # Start all services
docker compose ps                   # Check service status
docker compose logs postiz           # View Postiz logs

# Python automation layer (when built)
pip install -e ".[dev]"
pytest
ruff check . --fix
```

## Key Decisions & Constraints

- **Postiz API is in beta** — rate limits and endpoints may change
- **n8n runs on separate host** — communication via HTTP/webhooks
- **Platform app approvals needed** — Facebook, Instagram require business verification
- **Content pillars**: 40% spiritual education, 25% farm/community, 15% events, 10% behind-scenes, 5% seasonal, 5% collaborative
- **Content mix**: 70% value-add, 20% engagement, 10% promotional
- **Rebranding in progress** — "Gita Nagari" → "Gita Valley" across all platforms

## Task Tracking

Task Master is retired (2026-08-31). Historical PRDs and task data live in `.taskmaster/` as an archive. Phase work is tracked in Current Focus below; new multi-step efforts use `.scratch/` ticket files or a tasks.md.

## Current Focus

- [x] Phase 1: Content Creation Power (20/20 tasks, merged PR #5)
- [x] Phase 2: Intelligence Layer (20/20 tasks, merged PR #6)
- [x] Phase 3: Media & Planning (20/20 tasks, on feature/phase3-media-planning)
- [ ] Phase 4: Platform & Users
- [ ] Phase 5: Polish & Mobile

## Phase 3 New Endpoints

```
# Media catalog
POST   /api/media/upload              # Upload with AI tagging
POST   /api/media/import-url          # Import from URL
GET    /api/media                     # Browse with filters (tag, pillar, source, sort)
GET    /api/media/{id}                # Detail with tags, usage, performance
PUT    /api/media/{id}/tags           # Add/remove tags
DELETE /api/media/{id}                # Delete with file cleanup
GET    /api/media/suggest             # AI media suggestions for content
POST   /api/media/{id}/adapt          # Platform-specific image versions
PUT    /api/content/{id}/attach-media # Attach media to content (auto-adapts)
PUT    /api/content/{id}/detach-media # Detach media from content

# Google Drive
GET    /api/media/drive/browse        # Browse Drive folder
POST   /api/media/import-drive        # Batch import from Drive

# Calendar planning
POST   /api/calendar/plan             # AI-generate content calendar (Claude CLI)
GET    /api/calendar/plan/{id}        # View plan
GET    /api/calendar/plans            # List plans (filter by status)
POST   /api/calendar/plan/{id}/approve # Convert slots to content rows
DELETE /api/calendar/plan/{id}        # Delete draft plan

# Festivals
GET    /api/festivals                 # ISKCON festival calendar
```

## CLI Scripts

```bash
# Social media import (requires META_PAGE_ACCESS_TOKEN)
python -m content_engine.scripts.import_social_media
```

## Superpowers (Required)

This template requires the [Superpowers](https://github.com/obra/superpowers) plugin for workflow enforcement:

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

**Task Master + Superpowers = Complete Workflow:**
- **Task Master** (MCP) = WHAT to work on (task tracking, dependencies, status)
- **Superpowers** (Plugin) = HOW to work on it (TDD enforcement, debugging discipline)
