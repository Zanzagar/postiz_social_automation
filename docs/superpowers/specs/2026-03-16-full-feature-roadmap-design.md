# Gita Valley Social Automation — Full Feature Roadmap Design

**Date:** 2026-03-16
**Scope:** 17 features across 5 phases (from 20 original, 3 merges, 1 drop)
**Architecture:** React SPA → FastAPI → SQLite (source of truth) → Content Engine → Claude CLI + Postiz + Sheets (import/export)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1 — Content Creation Power](#phase-1--content-creation-power)
3. [Phase 2 — Intelligence Layer](#phase-2--intelligence-layer)
4. [Phase 3 — Media & Planning](#phase-3--media--planning)
5. [Phase 4 — Platform & Users](#phase-4--platform--users)
6. [Phase 5 — Polish & Mobile](#phase-5--polish--mobile)
7. [Feature Consolidation Summary](#feature-consolidation-summary)
8. [SQLite Schema (Complete)](#sqlite-schema-complete)
9. [API Endpoints (Complete)](#api-endpoints-complete)
10. [Design Decisions Log](#design-decisions-log)

---

## Architecture Overview

### Current Stack (What Exists)

```
React SPA (:3000, Docker nginx)
  ↓
FastAPI (:8000, host)
  ↓
Content Engine (host)
  ↓
Claude CLI (OAuth)  +  Google Sheets  +  Postiz API (sethpc.xyz)
```

- 7 React pages: Login, Dashboard, Create, Drafts, Calendar, Suggestions, Health
- 13 FastAPI endpoints
- 3 pipeline modes: Enhance, Suggest, Learn
- 111 tests (49 backend, 62 frontend Playwright E2E)
- Docker Compose: Postiz, PostgreSQL, Redis, Temporal, Streamlit, React frontend

### Revised Stack (After All Phases)

```
React SPA (:3000, Docker nginx) — PWA-capable
  ↓
FastAPI (:8000, host)
  ↓
SQLite (data/gvsa.db) ← source of truth for ALL content
  ↓
Content Engine (host)
  ↓
Claude CLI    Postiz API    Google Sheets    WordPress MCP    Meta Graph API
(generation)  (scheduling)  (import/export)  (gitavalley.com) (social history)
                            Web Scraper
                            (iskcongitanagari.org)
```

### Key Architectural Shift: SQLite as Source of Truth

Google Sheets is no longer the primary data store. SQLite becomes the source of truth for all content, metadata, analytics, and configuration. Sheets becomes an import/export adapter.

**Rationale:**
- Eliminates sync issues between SQLite and Sheets as features grow
- Enables relational integrity (media → content, templates → content, iterations → captions)
- Removes Sheets API rate limits as a bottleneck for analytical queries
- Provides reliable status tracking for auto-publish workflows
- Single database for all queries — no cross-system joins

**Sheets adapter behavior:**
- **Import:** Poll Sheet for new rows → insert into SQLite → mark as imported in Sheet
- **Export:** Push status updates back to Sheet (optional, for anyone still watching it)
- **Configurable:** Can be disabled entirely once team is fully on the dashboard

### Shared Infrastructure

**SQLite + Alembic migrations:** Schema grows incrementally per phase. Each phase adds tables. `alembic upgrade head` on deploy.

**Unified ContentEditor component:** Shared React modal used by Drafts, Calendar, Suggestions, and Create pages. Supports three modes:
- `create` — from suggestion or template (generates new captions)
- `refine` — iterate on draft/scheduled content
- `repurpose` — create new content inspired by a posted piece

**Magic MCP + frontend-design pipeline:** All new or modified pages go through `frontend-design` skill → `component_inspiration` → `component_builder` → `component_refiner`. Enforced by `.claude/rules/frontend-workflow.md`.

---

## Phase 1 — Content Creation Power

**Features:** AI Content Iteration & Editing (#16), Content Templates (#8), Auto-Publish (#2)
**Pages rebuilt via Magic MCP:** Create, Calendar/Drafts
**Infrastructure introduced:** SQLite database, Alembic migrations, unified ContentEditor

### AI Content Iteration & Editing (#16)

Unified click-to-iterate model across all content views. The ContentEditor modal opens on any content item, with behavior adapted to content state:

| Content State | Where | Click Action | AI Context |
|---------------|-------|-------------|------------|
| Suggestion | Suggestions page | Generate captions from idea (in-place) | Pillar, idea, rationale, knowledge base |
| Draft | Drafts page | Refine existing captions | Original text, captions, iteration history, knowledge base |
| Scheduled | Calendar page | Edit before publish | Same as draft + scheduled date/platform |
| Posted | Calendar page | Repurpose into new content | Original + performance data + knowledge base |

**ContentEditor capabilities:**
- Displays per-platform caption cards (Instagram, Facebook, TikTok, Threads, LinkedIn)
- Refinement input per caption: "Make it more casual", "Add a call to action", "Shorten this"
- Submits to `POST /api/iterate` → Claude regenerates just that platform's caption
- Full iteration history: every version saved, rollback-capable
- Mode-aware: `create` mode shows generate button, `refine` shows iterate button, `repurpose` creates a new content row

**API endpoints:**
- `POST /api/iterate` — regenerate a single platform caption with refinement instructions. Fields: `content_row_id`, `platform`, `instruction`, `mode` (create|refine|repurpose)
- `GET /api/iterations/{content_id}` — fetch iteration history for a content row

### Content Templates (#8)

Reusable templates for recurring content types with variable substitution.

**Built-in starter templates:**
- Sunday Feast Announcement — pillar: Community, schedule: every Sunday
- Weekly Bhagavad Gita Verse — pillar: Spiritual, schedule: every Wednesday
- Farm Update — pillar: Farm Ops, schedule: every Friday
- Event Promotion Series — pillar: varies, schedule: manual

**Template structure:**
- Name, pillar, platform-specific instructions (JSON)
- Raw text template with `{{variables}}` (e.g., "Join us for {{event_name}} on {{date}}")
- Variable definitions with types (text, date, select)
- Optional schedule pattern for calendar AI planning (Phase 3)
- Optional default audience segment (Phase 4)

**Dashboard integration:**
- Template manager page: create, edit, delete, preview
- Create page: "Use Template" dropdown → pre-fills form, user fills variables
- ContentEditor: template badge shows which template was used

**API endpoints:**
- `GET /api/templates` — list all templates
- `POST /api/templates` — create template
- `GET /api/templates/{id}` — get template details
- `PUT /api/templates/{id}` — update template
- `DELETE /api/templates/{id}` — delete template
- `POST /api/templates/{id}/generate` — fill variables and generate captions

### Auto-Publish (#2)

Configurable per-platform auto-publish with optional delay window.

**Configuration:**
- Per-platform rules: auto-publish yes/no, delay window in hours
- Content pillar overrides: e.g., "auto-publish Farm Ops, but require review for Spiritual"
- Per-content override: any individual post can be flagged "require manual approval" regardless of config

**Delay window behavior:**
- "Auto-publish after 2 hours unless manually rejected"
- Staff gets a review window — if they don't intervene, post proceeds to Postiz
- Dashboard shows countdown timer on auto-publish content

**Flow:**
1. Captions generated → approved (or auto-approved)
2. Check publish_config for target platforms
3. If all platforms auto-publish enabled → schedule with Postiz after delay window
4. If any platform requires review → hold in PENDING_APPROVAL for that platform
5. Per-content override: "require review" flag stops auto-publish regardless of config

**API endpoints:**
- `GET /api/settings/publish` — read auto-publish configuration
- `PUT /api/settings/publish` — update auto-publish configuration

### Phase 1 SQLite Schema

```sql
-- Users (lightweight, no RBAC)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Content rows (replaces Google Sheets as source of truth)
CREATE TABLE content_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    pillar TEXT,
    raw_text TEXT,
    media_url TEXT,
    platforms JSON,           -- ["instagram", "facebook", ...]
    status TEXT DEFAULT 'draft',
    captions JSON,            -- {"instagram": "...", "facebook": "...", ...}
    postiz_ids JSON,          -- {"instagram": "postiz-id-1", ...}
    posted_at TIMESTAMP,
    feedback TEXT,
    source TEXT,              -- "manual", "template", "suggestion", "import"
    template_id INTEGER REFERENCES templates(id),
    created_by INTEGER REFERENCES users(id),
    media_catalog_ids JSON,   -- nullable, unused until Phase 3 (no FK constraint)
    audience_segment_id INTEGER, -- nullable, unused until Phase 4 (no FK constraint)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Iteration history
CREATE TABLE content_iterations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_row_id INTEGER NOT NULL REFERENCES content_rows(id),
    platform TEXT NOT NULL,
    old_caption TEXT,
    new_caption TEXT NOT NULL,
    refinement_instruction TEXT,
    mode TEXT DEFAULT 'refine',  -- create, refine, repurpose
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Templates
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    pillar TEXT,
    platform_instructions JSON,  -- {"instagram": "...", "facebook": "..."}
    raw_text_template TEXT,      -- "Join us for {{event_name}} on {{date}}"
    variables JSON,              -- [{"name": "event_name", "type": "text"}, ...]
    schedule_pattern TEXT,       -- "weekly:sunday", "monthly:1", null for manual
    default_segment_id INTEGER,  -- nullable, unused until Phase 4 (no FK constraint)
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Auto-publish config
CREATE TABLE publish_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    delay_hours INTEGER DEFAULT 2,
    pillar_overrides JSON,       -- {"spiritual": false, "farm_ops": true}
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 2 — Intelligence Layer

**Features:** Web Presence Intelligence (#1), Analytics (#3/18 merged), Hashtag & SEO Intelligence (#10)
**Pages rebuilt via Magic MCP:** Dashboard
**Infrastructure introduced:** WordPress MCP crawler, web scraper, Meta Graph API importer, analytics pipeline

### Web Presence Intelligence (#1 — reframed as "Web Presence Intelligence")

Three intelligence sources crawled into a unified knowledge base:

| Source | Method | Content |
|--------|--------|---------|
| gitavalley.com | WordPress MCP | Pages, programs, events, store, visit info, brand language |
| iskcongitanagari.org | Web scraper (BeautifulSoup) | Spiritual programs, teachings, ISKCON community content |
| Facebook + Instagram | Meta Graph API | Historical posts, captions, media, engagement data, hashtag usage |

**Crawl pipeline:**
1. **Initial crawl** — pull all pages/posts from all three sources
2. **Extract and classify** — AI categorizes each piece by content pillar, extracts facts/quotes/programs/events/links
3. **Store in SQLite** — `web_pages` (raw content) and `web_knowledge` (extracted facts)
4. **Periodic re-crawl** — weekly for websites, daily for social media (new posts)

**Error handling:** Each source is crawled independently. If one source fails (e.g., iskcongitanagari.org is down), the others still complete. Partial failures within a source (e.g., Meta Graph API rate-limits mid-import) save what was fetched and resume from the last checkpoint on the next run. AI classification failures for individual pages are logged and the page is stored without classification for manual review. The `/api/knowledge/status` endpoint reports per-source success/failure/partial status.

**How the AI uses the knowledge base:**
- **Brand voice calibration:** "Based on gitavalley.com's tone and past Instagram captions, this temple describes itself as..."
- **Content ideas:** "The education page mentions a new Bhakti Sastri course — suggest a social post about it"
- **Cross-promotion links:** "Link to gitavalley.org/visit for farm visit posts"
- **Pillar-aware context:** When generating Spiritual Education posts, inject relevant content from iskcongitanagari.org
- **Style learning from social history:** "Past Instagram posts use 5-8 hashtags, conversational tone, and end with a question"
- **Performance-informed suggestions:** "Posts about cow protection get 3x engagement — generate more of these"

**Social history import (Meta Graph API):**
- Requires the Meta developer app (already on the parallel platform setup track)
- One-time historical import of all past posts + media + engagement
- Each imported post auto-classified by pillar via Claude
- Media from social history feeds into the media catalog (Phase 3)
- Engagement data feeds into analytics (this phase)

**API endpoints:**
- `POST /api/knowledge/crawl` — trigger a re-crawl of websites
- `POST /api/knowledge/import-social` — trigger Meta Graph API import
- `GET /api/knowledge/status` — last crawl time, page count, knowledge entry count per source
- `GET /api/knowledge/search?q=` — search knowledge base (used by AI during generation and by dashboard)

### Analytics (#3/18 merged)

Pull engagement data from Postiz API + correlate with our content metadata.

**Data sources:**
- **Postiz API:** `GET /analytics/:integration` (platform-level), `GET /analytics/post/:postId` (post-level)
- **Social history import:** historical engagement from Meta Graph API
- **Our SQLite:** content pillar, template used, iteration count, media type, posting time

**Analytics pipeline:**
1. **Daily pull** — fetch engagement data from Postiz for all posted content
2. **Correlation engine** — join Postiz metrics with content metadata:
   - Which pillars get the most engagement per platform?
   - What posting times work best?
   - Do iterated posts (refined 2-3 times) outperform first-draft posts?
   - Which templates drive the most engagement?
   - (Phase 3) Which media types/tags correlate with higher engagement?
3. **Inject into learning context** — update learning insights in SQLite, inject into Claude prompts for future generation
4. **Display on Dashboard** — analytics widgets

**Dashboard analytics widgets:**
- Engagement over time (line chart, per platform)
- Pillar performance breakdown (bar chart)
- Best posting times heatmap
- Top performing posts (table with metrics)
- Content pipeline stats (drafts, scheduled, posted counts — existing, enhanced)

**API endpoints:**
- `GET /api/analytics/overview` — dashboard summary data (total engagement, post count, trend)
- `GET /api/analytics/pillars` — pillar performance breakdown
- `GET /api/analytics/timing` — best time analysis per platform
- `GET /api/analytics/posts?sort=engagement` — posts ranked by performance
- `POST /api/analytics/refresh` — trigger a Postiz data pull

### Hashtag & SEO Intelligence (#10)

Tied into the analytics + generation pipeline.

**Tracking:**
- Parse hashtags from all posted content (our captions + social history import)
- Correlate hashtag usage with engagement metrics
- Track per hashtag: platform, times used, avg engagement, trend (up/down/stable)

**Generation integration:**
- During caption generation, inject top-performing hashtags into Claude prompt
- Platform-specific limits enforced: Instagram max 30, Facebook 3-5, TikTok 3-5, Threads 0, LinkedIn 3-5
- Hashtag suggestions surface in the ContentEditor during iteration

**API endpoints:**
- `GET /api/hashtags?platform=` — top hashtags by platform with performance data

### Phase 2 SQLite Schema

```sql
-- Web presence knowledge base
CREATE TABLE web_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    site TEXT NOT NULL,            -- "gitavalley", "iskcon"
    title TEXT,
    body_text TEXT,
    pillar TEXT,
    content_hash TEXT,             -- detect changes on re-crawl
    last_crawled TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE web_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    web_page_id INTEGER REFERENCES web_pages(id),
    fact_type TEXT NOT NULL,       -- "program", "event", "quote", "link", "description"
    content TEXT NOT NULL,
    pillar TEXT,
    keywords JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Social history import
CREATE TABLE social_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,        -- "facebook", "instagram"
    external_id TEXT NOT NULL,     -- platform's post ID
    post_text TEXT,
    media_urls JSON,
    hashtags JSON,
    posted_at TIMESTAMP,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    pillar TEXT,                   -- AI-classified
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, external_id)
);

-- Analytics cache
CREATE TABLE analytics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_row_id INTEGER REFERENCES content_rows(id),
    platform TEXT NOT NULL,
    postiz_post_id TEXT,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hashtag tracking
CREATE TABLE hashtag_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hashtag TEXT NOT NULL,
    platform TEXT NOT NULL,
    times_used INTEGER DEFAULT 0,
    total_engagement INTEGER DEFAULT 0,
    avg_engagement REAL DEFAULT 0,
    trend TEXT DEFAULT 'stable',   -- "up", "down", "stable"
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hashtag, platform)
);
```

---

## Phase 3 — Media & Planning

**Features:** Media Intelligence (#7/19 merged), Content Calendar AI Planning (#11), Media Adaptation (#12)
**Pages rebuilt via Magic MCP:** Suggestions
**Infrastructure introduced:** Media processing (Pillow), Google Drive API, ISKCON calendar data

### Media Intelligence (#7/19 merged)

Full media catalog with metadata, tags, performance tracking. Postiz as storage backend.

**Media sources (ingestion):**

| Source | Method | When |
|--------|--------|------|
| Dashboard upload | File upload or URL | User action |
| Google Drive | Browse linked folder, import selected | User action |
| Social history | Phase 2 Meta Graph API import | Automatic (Phase 2) |
| Content creation | Media attached to content row | Automatic |

**Catalog features:**
- Every file gets: thumbnail (generated on import), AI-classified tags, pillar, source, dimensions, file size
- AI auto-tags: "farm", "cows", "kitchen", "outdoor", "people", "event", "food", "landscape", "building", "deity", etc.
- Performance tracking: link media to content rows → correlate with engagement → "farm landscape photos get 2x engagement on Instagram"
- Usage tracking: how many posts used this media, on which platforms

**Storage flow:**
```
Source → local media/ directory → upload to Postiz (POST /upload)
       → generate thumbnail (Pillow)
       → AI classify tags/pillar (Claude CLI)
       → insert into media_catalog table
```

**Error handling:** Media is always cataloged locally first, regardless of Postiz upload status. If Postiz upload fails (network error, rate limit), the media is stored locally with `postiz_media_id = null` and flagged for retry. A background job retries failed uploads periodically. Media with failed uploads can still be used in content creation — the Postiz upload happens before the post is sent to Postiz for scheduling, not at import time.

**Dashboard media browser:**
- Grid view with thumbnails
- Filter by: tag, pillar, performance tier, source, date range
- Sort by: date, engagement, usage count
- Click: full-size view, metadata, usage history, performance data
- "Suggest for content" — AI picks best media from catalog for a given post
- Attach to content: click or drag-and-drop from browser into ContentEditor

**Google Drive integration:**
- Configure Drive folder ID in Settings
- Browse folder contents in dashboard (Google Drive API, same service account as Sheets)
- Import selected files → normal catalog flow
- Periodic scan for new files (configurable)

**API endpoints:**
- `GET /api/media?tag=&pillar=&sort=&page=` — browse catalog with filters, paginated
- `POST /api/media/upload` — upload file (replaces current `/api/upload`)
- `POST /api/media/import-url` — import from URL
- `POST /api/media/import-drive` — import from Google Drive folder
- `GET /api/media/{id}` — full metadata, usage history, performance
- `PUT /api/media/{id}/tags` — update tags
- `GET /api/media/suggest?content_row_id=` — AI-suggested media for a content row

### Content Calendar AI Planning (#11)

AI generates a full content calendar based on multiple signals.

**Inputs to the planner:**
- Content pillar distribution targets (Cow Life 40%, Farm Ops 25%, Community 15%, Kitchen 10%, Spiritual 5%, CTA 5%)
- Upcoming ISKCON festivals and events (from `data/iskcon_calendar.json`)
- Engagement patterns from analytics (Phase 2 data)
- Gaps in recent posting history
- Template availability — recurring templates auto-populate their schedule slots
- Web knowledge — new programs or events from website crawls
- Seasonal context — spring farm content, winter kitchen content
- Media catalog — available high-performing media to reuse

**ISKCON calendar:**
- JSON file: `data/iskcon_calendar.json`
- Contains: festival name, date (lunar calendar, updated annually), significance, suggested content angles, content pillar
- Key festivals: Janmashtami, Ratha Yatra, Gaura Purnima, Rama Navami, Govardhan Puja, Diwali, etc.
- AI uses for planning: "Janmashtami is in 3 weeks — schedule a 5-post series leading up to it"

**Planning flow:**
1. User clicks "Plan Week" or "Plan Month" on Calendar page
2. Select date range and target platforms
3. AI generates proposed calendar: one content row per slot with suggested pillar, topic, recommended media, and optimal posting time
4. User reviews in calendar view — click any slot to edit/iterate (unified ContentEditor)
5. Approve individual slots or approve all → creates content rows in DRAFT status
6. From there: generate captions → iterate → approve → publish

**Calendar views:**
- **Monthly view** — grid (7 cols x 5-6 rows), day cells show content dots/thumbnails color-coded by pillar. Click day to expand. Big picture: spot gaps, see pillar distribution.
- **Weekly view** — day columns with time slots, content cards stacked per day showing platform icons, pillar badge, thumbnail, status. Detail view. "Plan Week" lives here.
- **List view** — existing view, kept for quick scanning and bulk actions.
- Toggle between views via tabs at top. All views support click-to-edit via ContentEditor.

**API endpoints:**
- `POST /api/calendar/plan` — generate a content plan for a date range
- `GET /api/calendar/plan/{id}` — view a generated plan
- `POST /api/calendar/plan/{id}/approve` — approve plan slots → creates content rows
- `GET /api/festivals?from=&to=` — upcoming ISKCON festivals in date range

### Media Adaptation (#12)

Resize and crop media for platform-specific dimensions. Optional text overlay.

**Platform dimensions:**

| Platform | Post | Story/Reel | Carousel |
|----------|------|------------|----------|
| Instagram | 1080x1080 (square), 1080x1350 (portrait) | 1080x1920 | 1080x1080 |
| Facebook | 1200x630 | 1080x1920 | 1200x630 |
| TikTok | — | 1080x1920 | — |
| LinkedIn | 1200x627 | — | 1200x627 |

**Adaptation flow:**
- When media is attached to a content row, auto-generate platform-specific crops
- Smart crop: detect subject/focus area (Pillow center-of-mass or face detection), crop preserving subject
- Optional text overlay: caption text or CTA positioned at bottom with semi-transparent background
- Store adapted versions linked to original in `media_adapted` table

**Implementation:** Pillow (PIL) for image processing. No ffmpeg — image cropping/resizing only.

**API endpoints:**
- `POST /api/media/{id}/adapt` — generate platform-specific versions
- `GET /api/media/{id}/adapted?platform=&format=` — get adapted version

### Phase 3 SQLite Schema

```sql
-- Media catalog
CREATE TABLE media_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_url TEXT,
    local_path TEXT NOT NULL,
    postiz_media_id TEXT,
    thumbnail_path TEXT,
    mime_type TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    tags JSON,                     -- ["farm", "cows", "outdoor"]
    pillar TEXT,
    source TEXT NOT NULL,          -- "upload", "drive", "social_import"
    usage_count INTEGER DEFAULT 0,
    avg_engagement REAL DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE media_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES media_catalog(id),
    tag TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'ai',      -- "ai", "manual"
    UNIQUE(media_id, tag)
);

CREATE TABLE media_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES media_catalog(id),
    content_row_id INTEGER NOT NULL REFERENCES content_rows(id),
    platform TEXT NOT NULL,
    engagement_score REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE media_adapted (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL REFERENCES media_catalog(id),
    platform TEXT NOT NULL,
    format TEXT NOT NULL,           -- "post", "story", "carousel"
    adapted_path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    has_text_overlay BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Calendar planning
CREATE TABLE calendar_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_range_start DATE NOT NULL,
    date_range_end DATE NOT NULL,
    platforms JSON,
    plan_data JSON,                -- [{date, pillar, topic, media_id, time, platform}, ...]
    status TEXT DEFAULT 'draft',   -- "draft", "approved", "partial"
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 4 — Platform & Users

**Features:** Multi-User (#6), Audience Segmentation (#13), Postiz MCP (#14), Embedded Postiz Admin (#20)
**Pages rebuilt via Magic MCP:** None (no existing pages fundamentally change)
**Infrastructure introduced:** Audit logging, audience-aware prompts, Postiz MCP config

### Multi-User (#6 — lightweight)

Named accounts with optional approval workflow. No RBAC.

**Scope:**
- `users` table exists from Phase 1
- Login page upgrade: username/password instead of single shared password
- Every content row, iteration, template, and action gets `created_by` / `updated_by`
- Audit trail: `audit_log` table records who did what and when

**Optional approval workflow:**
- Default: auto-approve (same as today, just with a name attached)
- Setting toggle: "Require approval from another user before publishing"
- When enabled: creator sets status to PENDING_APPROVAL → any other user can approve
- No role distinction — any user can create, any user can approve (just not your own if approval is required)
- Configurable in Settings page

**API endpoints:**
- `POST /api/users` — create user
- `GET /api/users` — list users
- `PUT /api/users/{id}` — update profile
- `GET /api/audit?from=&to=&user=` — audit log with filters

### Audience Segmentation (#13)

Different messaging for different audience segments, integrated into content generation prompts.

**Built-in segments:**

| Segment | Tone | Vocabulary | Platform Affinity |
|---------|------|-----------|-------------------|
| Devotee community | Warm, familial, Sanskrit welcome | "prasadam", "darshan", "Srila Prabhupada" | Instagram, Facebook |
| Local community | Friendly, accessible, farm-focused | "farm visit", "CSA share", "family program" | Facebook, Instagram |
| General public | Professional, wellness-oriented | "sustainable living", "animal welfare", "mindfulness" | LinkedIn, TikTok |

**Integration:**
- Each content row can optionally specify a target audience segment
- If set: Claude prompt gets audience-specific tone/vocabulary/emphasis instructions
- If not set: defaults to the platform's natural audience
- Templates can have a default segment
- Calendar AI planning considers audience mix balance
- Segments are editable in Settings (add, modify, delete)

**UI:** Segment dropdown in ContentEditor and Create page. No new pages needed.

**API endpoints:**
- `GET /api/segments` — list audience segments
- `POST /api/segments` — create segment
- `PUT /api/segments/{id}` — update segment
- `DELETE /api/segments/{id}` — delete segment

### Postiz MCP Integration (#14 — scoped)

Optional MCP path for Claude CLI conversational scheduling. HTTP remains primary.

**Scope:**
- Configure Postiz's built-in MCP server (`/mcp` on sethpc.xyz) as a tool available to Claude CLI
- During content generation, Claude can schedule directly via MCP in one step
- HTTP (`postiz.py`) remains primary for all programmatic operations
- Feature flag: `POSTIZ_MCP_ENABLED=true` — off by default

**Implementation:** Configuration + prompt update only. Add Postiz MCP server to Claude CLI's MCP settings, update generation prompt to optionally include scheduling instructions.

### Embedded Postiz Admin (#20)

Deeper Postiz admin integration in the dashboard.

**Default approach: API replicas** (assume iframe is blocked). Build lightweight admin screens using Postiz API:
- Connected accounts list (`GET /integrations`) — show platform, name, status
- Account connection flow (`GET /social/:integration`) — link to connect new platform
- Post queue view (`GET /posts`) — upcoming scheduled posts

If iframe embedding is later confirmed to work (test `X-Frame-Options` on sethpc.xyz), an iframe-based approach can replace the replicas — but the API replicas are the planning assumption for PRD and task decomposition.

**API endpoints:**
- `GET /api/postiz/integrations` — proxy to Postiz integrations list
- `GET /api/postiz/connect/:platform` — get OAuth URL for connecting
- `GET /api/postiz/queue` — upcoming scheduled posts

### Phase 4 SQLite Schema

```sql
-- Audience segments
CREATE TABLE audience_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    tone_instructions TEXT,
    vocabulary JSON,               -- ["prasadam", "darshan", ...]
    avoid_terms JSON,              -- ["preach", "convert", ...]
    platform_affinity JSON,        -- {"instagram": 0.8, "linkedin": 0.3}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,           -- "create", "update", "delete", "approve", "publish"
    entity_type TEXT NOT NULL,      -- "content_row", "template", "media", "settings"
    entity_id INTEGER,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 5 — Polish & Mobile

**Features:** Dark Mode (#4), Notifications (#5), PWA (#9), UI upgrade (remaining pages)
**Pages rebuilt via Magic MCP:** Login, Health
**Infrastructure introduced:** Service worker, email digest job

### Dark Mode (#4)

- Theme toggle in sidebar (sun/moon icon)
- Store preference in `localStorage`
- Respect system preference (`prefers-color-scheme`) as default
- CSS variables for all colors — components rebuilt in earlier phases already use them
- Purely frontend, no API changes

### Notifications (#5 — in-app toasts + email digest)

**In-app toasts:**
- shadcn/ui Toast component for real-time feedback
- Triggers: generation complete, post published, publish failed, crawl complete, new suggestion
- Uses existing TanStack Query polling — no WebSocket infrastructure
- Notification bell icon in header with unread count

**Email digest:**
- Configurable frequency: daily, weekly, or off
- Content: posts published since last digest, drafts awaiting review, engagement highlights, errors
- Lightweight sending: Python `smtplib` with configured SMTP relay
- Cron trigger: content engine scheduler runs digest job

**API endpoints:**
- `GET /api/settings/notifications` — user notification preferences
- `PUT /api/settings/notifications` — update preferences
- `POST /api/notifications/test-email` — send a test digest

### PWA (#9)

- `manifest.json`: app name ("Gita Valley Social"), icons, theme colors
- Service worker: cache app shell, show cached content when offline
- "Add to Home Screen" prompt on mobile
- Offline draft editing: save to IndexedDB, sync when online
- Implementation: `vite-plugin-pwa`
- No new API endpoints

### UI Upgrade (remaining pages)

Pages not rebuilt in earlier phases:
- **Login page** — rebuild via Magic MCP pipeline
- **Health page** — rebuild via Magic MCP pipeline

All other pages (Create, Calendar/Drafts, Dashboard, Suggestions) already rebuilt during their respective phases.

### Phase 5 SQLite Schema

```sql
-- Notification preferences
CREATE TABLE notification_prefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    email TEXT,
    digest_frequency TEXT DEFAULT 'off',  -- "daily", "weekly", "off"
    enabled_types JSON,                    -- ["publish", "error", "suggestion"]
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email digest log
CREATE TABLE email_digest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT,
    post_count INTEGER DEFAULT 0,
    draft_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);
```

---

## Feature Consolidation Summary

| # | Original Feature | Disposition | Phase |
|---|-----------------|-------------|-------|
| 1 | Website Content Syndication | **Reframed** → Web Presence Intelligence (crawl sites + social history) | 2 |
| 2 | Auto-Publish Mode | Unchanged | 1 |
| 3 | Content Analytics Dashboard | **Merged** with #18 → pull Postiz + our analysis | 2 |
| 4 | Dark Mode | Unchanged | 5 |
| 5 | Real-Time Notifications | **Scoped down** → in-app toasts + email digest (no WebSocket, no WhatsApp) | 5 |
| 6 | Multi-User Support | **Scoped down** → named accounts, optional approval, no RBAC | 4 |
| 7 | Media Library | **Merged** with #19 → Media Intelligence (our catalog, Postiz storage) | 3 |
| 8 | Content Templates | Unchanged | 1 |
| 9 | PWA / Mobile Install | Unchanged | 5 |
| 10 | Hashtag & SEO Intelligence | Unchanged | 2 |
| 11 | Content Calendar AI Planning | Unchanged (+ monthly/weekly/list views) | 3 |
| 12 | Cross-Platform Repurposing | **Scoped down** → media adaptation (resize/crop/overlay, no video extraction) | 3 |
| 13 | Audience Segmentation | Unchanged | 4 |
| 14 | Postiz MCP Integration | **Scoped down** → optional MCP for Claude CLI scheduling, HTTP stays primary | 4 |
| 15 | WhatsApp Integration | **Dropped** | — |
| 16 | AI Content Iteration & Editing | **Expanded** → unified ContentEditor across all views | 1 |
| 17 | UI Component Upgrade | **Distributed** across phases (pages rebuilt when modified) | 1-5 |
| 18 | Postiz Analytics Integration | **Merged** with #3 | 2 |
| 19 | Postiz Media Library Integration | **Merged** with #7 | 3 |
| 20 | Embedded Postiz Admin | Unchanged | 4 |

**Net: 20 features → 17 (3 merges, 1 drop). All 17 designed to full depth.**

---

## SQLite Schema (Complete)

All tables across all phases, in dependency order:

### Phase 1
- `users` — named accounts
- `content_rows` — replaces Google Sheets as content source of truth
- `content_iterations` — caption version history
- `templates` — reusable content templates
- `publish_config` — per-platform auto-publish rules

### Phase 2
- `web_pages` — crawled website pages
- `web_knowledge` — extracted facts/knowledge entries
- `social_history` — imported Facebook/Instagram posts
- `analytics_cache` — Postiz engagement data
- `hashtag_performance` — hashtag tracking

### Phase 3
- `media_catalog` — media files with metadata
- `media_tags` — AI and manual tags on media
- `media_performance` — media-engagement correlation
- `media_adapted` — platform-specific crops
- `calendar_plans` — AI-generated content plans

### Phase 4
- `audience_segments` — audience targeting definitions
- `audit_log` — user action tracking

### Phase 5
- `notification_prefs` — per-user notification settings
- `email_digest_log` — digest send history

**Total: 19 tables across 5 phases.**

### Migration Strategy

Forward-reference columns (`media_catalog_ids`, `audience_segment_id`, `default_segment_id`) are added as nullable columns without FOREIGN KEY constraints in Phase 1. They remain unused until their target tables are created in later phases. When the target tables arrive, an Alembic migration adds the FK constraints. This avoids schema changes to existing tables in later phases while keeping the schema extensible.

Each phase gets its own Alembic migration script. Deployment: `alembic upgrade head`. Rollback: `alembic downgrade -1` per phase.

### Scheduling & Background Jobs

Features requiring periodic execution (analytics daily pull, website re-crawl, email digest, Google Drive scan) use the existing `scheduler.py` module in the content engine, extended with new job definitions. Jobs are registered with configurable intervals and run as part of the content engine process on the host. No new infrastructure (e.g., Celery, cron) is introduced.

### ISKCON Calendar Maintenance

The `data/iskcon_calendar.json` file contains ISKCON festival dates based on the lunar calendar. Dates change annually. The file is manually updated once per year when ISKCON publishes the Vaishnava calendar (typically available months in advance). A dashboard settings section shows the current calendar year and a reminder when an update is needed.

### SMTP Configuration

Email digest (Phase 5) uses Python `smtplib`. SMTP settings are stored as environment variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. These are configured in `.env` alongside existing service credentials.

---

## API Endpoints (Complete)

### Existing (kept, actual endpoint paths)
- `POST /api/auth/login` — JWT authentication
- `GET /api/auth/me` — current user info
- `POST /api/generate` — SSE streaming caption generation
- `POST /api/generate-sync` — non-streaming generation
- `POST /api/reprompt` — regenerate captions
- `GET /api/drafts` — pending approval content
- `POST /api/drafts/{row_number}/approve` — approve a draft
- `POST /api/drafts/{row_number}/edit` — edit a draft
- `GET /api/calendar` — calendar content
- `GET /api/suggestions` — AI content ideas
- `POST /api/send-to-postiz` — send to Postiz scheduler
- `POST /api/upload` — file upload
- `GET /api/content/{row_number}` — get specific content row
- `GET /api/integrations` — connected Postiz integrations
- `GET /api/health` — service health

### Phase 1 (new)
- `POST /api/iterate` — unified caption iteration (create/refine/repurpose)
- `GET /api/iterations/{content_id}` — iteration history
- `CRUD /api/templates` — template management
- `POST /api/templates/{id}/generate` — generate from template
- `GET/PUT /api/settings/publish` — auto-publish config

### Phase 2 (new)
- `POST /api/knowledge/crawl` — trigger website re-crawl
- `POST /api/knowledge/import-social` — trigger Meta Graph API import
- `GET /api/knowledge/status` — crawl status
- `GET /api/knowledge/search?q=` — search knowledge base
- `GET /api/analytics/overview` — dashboard summary
- `GET /api/analytics/pillars` — pillar breakdown
- `GET /api/analytics/timing` — best time analysis
- `GET /api/analytics/posts?sort=` — posts by performance
- `POST /api/analytics/refresh` — trigger Postiz pull
- `GET /api/hashtags?platform=` — hashtag performance

### Phase 3 (new)
- `GET /api/media?tag=&pillar=&sort=&page=` — browse media catalog
- `POST /api/media/upload` — upload file
- `POST /api/media/import-url` — import from URL
- `POST /api/media/import-drive` — import from Google Drive
- `GET /api/media/{id}` — media detail
- `PUT /api/media/{id}/tags` — update tags
- `GET /api/media/suggest?content_row_id=` — AI media suggestions
- `POST /api/media/{id}/adapt` — generate platform crops
- `GET /api/media/{id}/adapted?platform=` — get adapted version
- `POST /api/calendar/plan` — generate AI content plan
- `GET /api/calendar/plan/{id}` — view plan
- `POST /api/calendar/plan/{id}/approve` — approve plan
- `GET /api/festivals?from=&to=` — ISKCON festivals

### Phase 4 (new)
- `CRUD /api/users` — user management
- `GET /api/audit?from=&to=&user=` — audit log
- `CRUD /api/segments` — audience segments
- `GET /api/postiz/integrations` — Postiz connected accounts
- `GET /api/postiz/connect/:platform` — connection OAuth URL
- `GET /api/postiz/queue` — Postiz post queue

### Phase 5 (new)
- `GET/PUT /api/settings/notifications` — notification preferences
- `POST /api/notifications/test-email` — test email digest

**Total: ~40 new endpoints across 5 phases (plus ~10 existing).**

---

## Design Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Source of truth | SQLite (not Google Sheets) | Eliminates sync issues, enables relational integrity, removes API rate limits as bottleneck |
| Database | SQLite (not PostgreSQL) | Zero infrastructure, adequate for single-temple scale, migratable later |
| Media storage | Our catalog + Postiz as backend | Postiz lacks bulk import, Drive integration, and media intelligence; we need our own metadata layer |
| Analytics | Postiz pull + our analysis | Avoid duplicating Postiz's data collection; add pillar/timing/media correlation |
| Website intelligence | WordPress MCP + web scraper | gitavalley.com has WordPress MCP access; iskcongitanagari.org needs scraping |
| Social history | Meta Graph API (not scraping) | Structured data, includes engagement, legitimate page-owner API access |
| Media library consolidation | #7 + #19 merged | Postiz media API too basic (can't list/browse); our layer wraps it |
| Analytics consolidation | #3 + #18 merged | Single analytics system pulling from Postiz + adding our own analysis |
| Multi-user | Named accounts, no RBAC | Small team (3-5), permission tiers add complexity without value |
| Notifications | In-app toasts + email digest | WebSocket/WhatsApp are overengineered for a small team |
| WhatsApp | Dropped | Requires separate Meta Business API approval; low value for small team |
| Cross-platform repurposing | Media adaptation only | Video extraction is heavy infrastructure; image crop/resize covers actual need |
| Postiz MCP | Optional, Claude CLI only | HTTP is battle-tested; MCP adds value only for conversational scheduling |
| UI upgrade | Distributed across phases | Pages rebuilt when modified for new features; avoids double-touching |
| Calendar views | Monthly + weekly + list | Monthly for big picture, weekly for detail, list for bulk actions |
| Feature phasing | Value-first (Approach B) | Phase 1 delivers immediate workflow improvement; infra introduced when needed |
| JSON columns in SQLite | Intentional denormalization | `platforms`, `captions`, `postiz_ids`, `media_catalog_ids` are stored as JSON for simplicity; not queried with SQL JSON operators in performance-sensitive paths |
| Embedded Postiz Admin | API replicas (default) | Assume iframe blocked; build API proxy screens. Simpler than testing X-Frame-Options and maintaining two code paths |

---

*Design validated through brainstorming session 2026-03-16.*
