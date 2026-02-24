# Social Media Automation Pipeline — Design Document v2

**Date:** 2026-02-24
**Status:** Approved
**Supersedes:** 2026-02-23-social-automation-pipeline-design.md (v1, n8n-based)
**Client:** Gita Valley (ISKCON eco-farm, Port Royal, PA)

## Problem

Gita Valley has compelling daily content (85 cows, farm operations, community events, cooking, retreats) but no system for consistent social media posting. Multi-month gaps between posts result in 0.2-0.4% engagement vs. 3-6% benchmarks for farm accounts. One intern's viral TikTok generated 1,200 applications — proving demand exists when content is posted.

Farm staff are busy with operations. They need a system that **minimizes their creative burden** while maintaining brand consistency.

## Solution

Three-tool pipeline: Google Sheets (content input) → Python Content Engine with Claude Code CLI (AI generation, learning, suggestions) → Postiz (review, edit, schedule, publish).

**Architecture principle:** Claude = brain, Postiz = hands, Sheets = input.

## Key Architecture Decision: Why Not n8n

The original design used n8n for orchestration. We dropped it because:

1. **Claude via OAuth constraint** — Using Claude subscription (no API costs). n8n can't call Claude without API key = per-token billing.
2. **Staff don't need workflow visibility** — They need to see *posts*, not automation pipelines. Postiz provides that.
3. **Fewer moving parts** — 3 tools instead of 4. Less to maintain on Seth's server.
4. **n8n's Postiz custom node is buggy** — Instagram 400 errors (GitHub Issue #7). HTTP Request nodes work but add complexity for what becomes a simple API call from Python.

## Architecture

### Two-Mode Pipeline

The system operates in two modes:

**Mode 1: Staff-Initiated (Enhance)**
Staff adds content to Sheet → AI enhances per platform → Drafts appear in Postiz → Staff reviews/approves

**Mode 2: AI-Suggested (Suggest)**
System proactively generates content ideas → Suggestions appear in Sheet → Staff picks/edits → Drafts pushed to Postiz

### Data Flow — Mode 1 (Enhance)

```
Farm staff fills Google Sheets row:
  photo URL + 1-sentence caption + target date
  Sets status → "ready"
        │
        ▼
Content Engine (Python, runs via cron or manual trigger)
  Reads rows where status = "ready"
  Validates: caption exists, media URL valid
  Invalid → marks row "error" with error_msg
        │
        ▼
AI Caption Generator (Claude Code CLI, OAuth — $0 cost)
  Reads content intelligence context (past performance, brand rules)
  Generates 1 caption per target platform
  Infers content pillar from photo/caption
        │
        ▼
Google Sheets Update
  Writes generated captions back to Sheet
  Sets status → "pending_approval"
        │
        ▼
Postiz Draft Creation (via HTTP API)
  Creates draft post in Postiz for each platform
  Staff sees drafts in Postiz calendar/dashboard
        │
        ▼
Staff reviews in Postiz OR Sheet
  Edits text, adjusts scheduling
  Approves → post scheduled for publishing
        │
        ▼
Postiz publishes on schedule to all platforms
  Content Engine updates Sheet: status → "posted", postiz_ids, posted_at
```

### Data Flow — Mode 2 (Suggest)

```
Content Intelligence Layer (runs weekly or on-demand)
  Analyzes:
    - Content calendar gaps ("no farm content in 5 days")
    - Pillar balance ("spiritual at 15%, target is 5%")
    - Upcoming events/festivals ("Ekadashi in 3 days")
    - Past post performance ("cow photos at 9am get 3x engagement")
    - Content repository (scriptures, quotes, farm photo archive)
        │
        ▼
AI Suggestion Generator (Claude Code CLI, OAuth — $0 cost)
  Generates 5-7 content ideas with:
    - Suggested caption per platform
    - Recommended content pillar
    - Suggested media type/theme
    - Rationale ("this fills a farm ops gap + Ekadashi timing")
        │
        ▼
Google Sheets "Suggestions" tab
  New rows with status "suggested"
  Staff reviews, picks favorites, edits
  Moves to "approved" → Content Engine creates Postiz drafts
```

### Content Intelligence Layer

This is the learning system that improves over time:

```
┌──────────────────────────────────────────────┐
│            Content Intelligence               │
│                                               │
│  Inputs:                                      │
│  ├── Past posts + engagement data (Postiz API)│
│  ├── Content repository (local files)         │
│  │   ├── ISKCON scripture/teachings            │
│  │   ├── Farm photo archive index              │
│  │   ├── Festival/event calendar               │
│  │   └── Curated quotes collection             │
│  ├── Social media best practices (in prompts)  │
│  └── Current content calendar state (Sheet)    │
│                                               │
│  Outputs:                                     │
│  ├── Learning context file                    │
│  │   (what works, patterns, timing insights)  │
│  ├── Enhanced generation prompts              │
│  └── Content suggestions                      │
└──────────────────────────────────────────────┘
```

The learning context file (`data/learning-context.json`) accumulates:
- Top-performing content types by platform
- Best posting times by day of week
- Hashtag performance data
- Pillar distribution tracking
- Engagement trends over time

This file is included as context in every Claude Code CLI generation call, making each new post benefit from all prior performance data.

### Google Sheets Schema

**"Content" tab (staff input + AI output):**

| Column | Type | Who fills it |
|--------|------|-------------|
| date | Date | Staff (or AI in suggestion mode) |
| photo_url | URL (Google Drive link) | Staff |
| caption | Text (1 sentence) | Staff (minimal input) |
| platforms | Checkboxes (IG, FB, TikTok, Threads, LinkedIn) | Staff (or AI default: all) |
| status | Dropdown | Automated + staff |
| content_pillar | Text | AI-inferred (staff can override) |
| caption_ig | Text | AI-generated |
| caption_fb | Text | AI-generated |
| caption_tt | Text | AI-generated |
| caption_th | Text | AI-generated |
| caption_li | Text | AI-generated |
| feedback | Text | Staff (optional: "make it more casual") |
| postiz_ids | Text | Automated |
| posted_at | DateTime | Automated |
| error_msg | Text | Automated |
| source | Text | "staff" or "suggested" |

**Status values:** draft → ready → pending_approval → approved → posted → error

**"Suggestions" tab (AI-generated ideas):**

| Column | Type |
|--------|------|
| suggested_date | Date |
| content_idea | Text (description of suggested content) |
| suggested_pillar | Text |
| rationale | Text (why this suggestion) |
| media_suggestion | Text (what kind of photo/video) |
| status | suggested → accepted → dismissed |

**Staff workflow (Mode 1):** Add photo URL + 1-sentence caption + date. Set status to "ready". Everything else is automated.

**Staff workflow (Mode 2):** Open "Suggestions" tab. Pick ideas you like, set to "accepted". Content Engine generates full platform captions and creates Postiz drafts.

## AI Caption Generation

### System Prompt Structure

```
You are a social media manager for Gita Valley, a 430-acre
regenerative eco-farm and cow sanctuary in Port Royal, PA.

BRANDING RULES:
- Always use "Gita Valley" (never "Gita Nagari")
- Website: gitavalley.org
- Tagline: "Cultivating Soil and Soul"
- Key claim: "Only USDA Certified Slaughter-Free Dairy Farm
  in North America"

VOICE: Warm, welcoming, grounded. Lead with cows and farm,
not religion. Never preachy.

PERFORMANCE CONTEXT:
{learning_context_summary}

PLATFORM: {platform_name}
PLATFORM RULES: {platform_specific_instructions}
CONTENT PILLAR: {inferred_or_specified_pillar}

Generate a caption for this content: {caption_from_sheet}
Photo context: {photo_description_if_available}
```

### Platform-Specific Instructions

| Platform | Style |
|----------|-------|
| Instagram | Visual focus, 5-10 hashtags, emoji-rich, 150-200 words, CTA in last line |
| Facebook | Storytelling, 200-300 words, question to spark comments, link to gitavalley.org |
| TikTok | Short hook (first 3 words grab attention), trending language, 2-3 hashtags, under 100 words |
| Threads | Conversational, no hashtags, 1-2 sentences, thought-provoking |
| LinkedIn | Professional, impact-focused, university partnership angles, 100-150 words |

### Content Pillar Tone Adjustments

| Pillar | Target Weight | Tone Guidance |
|--------|--------------|---------------|
| Cow personalities & daily life | 40% | Personality-driven, name specific cows (Tabby, Dennis, Sparkle, Daring Denise, Brisham), emotional connection, parasocial relationship building |
| Farm operations & sustainability | 25% | Educational, sustainability focus, behind-the-scenes, regenerative agriculture expertise |
| Community & people | 15% | Spotlight format, gratitude, warmth, volunteer/intern stories |
| Kitchen & food | 10% | Recipe teasers, farm-to-table narrative, sattvic cuisine, head chef Madhupan |
| Spiritual dimension | 5% | Gentle, invitational, not doctrinal. Morning routines, festival celebrations |
| Calls to action | 5% | Clear ask, impact framing, urgency without pressure. Donate, visit, volunteer, adopt-a-cow |

### AI Provider

Claude via OAuth/Max subscription through Claude Code CLI — no per-API-call cost. The CLI is authenticated once and reused for all generation calls.

### Staff Re-Prompting

The `feedback` column in the Sheet allows staff to request changes:
- "make it more casual"
- "emphasize the spiritual angle"
- "add a donation CTA"

Next Content Engine run picks up feedback, re-generates with the feedback as additional context, and updates the draft in Postiz.

## Content Repository

Local files that give Claude Gita Valley-specific knowledge:

| Source | File | What It Provides |
|--------|------|-----------------|
| Festival calendar | `data/festivals.json` | Seasonal content triggers (Janmashtami, Gaura Purnima, Ekadashi, etc.) |
| Scripture quotes | `data/quotes.json` | Curated Bhagavad Gita verses, Prabhupada quotes |
| Cow profiles | `data/cow-profiles.json` | Names, personalities, photos of the 85 cows |
| Farm facts | `data/farm-facts.json` | Key stats, history, programs, partnerships |
| Post history | `data/post-performance.json` | Pulled from Postiz API — engagement, timing, content type |
| Brand guidelines | `data/brand-guide.md` | Full branding rules, voice examples, do/don't |

Claude already knows ISKCON philosophy and social media best practices from training. The local repository adds **Gita Valley-specific context** — your farm, your community, your voice.

## Content Strategy (Baked Into Prompts)

### Mix Rule: 70/20/10

- 70% value content (education, entertainment, farm life)
- 20% community content (testimonials, spotlights, partnerships)
- 10% ask content (donations, sales, recruitment)

### Posting Cadence (configurable defaults, finalized at temple president meeting)

| Platform | Default Frequency |
|----------|------------------|
| Instagram | 4-5 posts/week + daily Stories |
| Facebook | 3-4 posts/week |
| TikTok | 3-5 short videos/week |
| Threads | Mirror Instagram |
| LinkedIn | 1-2 posts/week |

## Approval Workflow

Manual approval by default. Configurable per-platform or per-pillar auto-publish as a future option.

1. Content Engine generates AI captions, writes to Sheet, creates draft in Postiz
2. Staff opens Postiz dashboard → sees drafts in calendar view
3. Staff edits text, adjusts scheduling, approves
4. Postiz publishes on schedule
5. Content Engine updates Sheet status

**Two review surfaces:**
- **Postiz dashboard** — primary review UI (rich editor, multi-platform preview, drag-and-drop calendar)
- **Google Sheet** — secondary (for quick status checks, batch operations)

## Media Handling

- **Source:** Google Drive shared folder as media library + direct URL in Sheet
- **Images:** JPEG, PNG, WebP. Content Engine downloads from Drive URL before passing to Postiz API
- **Video:** MP4. Platform-specific dimension/length validation (TikTok, Instagram Reels)
- **AI media suggestions:** In suggestion mode, Claude suggests media type/theme. Staff uploads the actual photo/video.

## Error Handling

| Failure | Response |
|---------|----------|
| Google Sheets API unreachable | Retry 3x with exponential backoff, log error |
| Claude Code CLI fails | Mark row "error", log reason, continue other rows |
| Postiz API rate limit (30/hr) | Queue with delay, max 3 attempts |
| Postiz API auth failure | Log error, mark "error", stop processing |
| Media URL invalid | Post text-only or mark "error" (configurable) |
| Platform not connected in Postiz | Skip that platform, post to connected ones |
| OAuth token expired | Alert user to re-authenticate `claude login` |

## Infrastructure

| Service | Location | Purpose |
|---------|----------|---------|
| Postiz | https://postiz.sethpc.xyz | Review, edit, schedule, publish |
| Content Engine | Docker service on Seth's server (future) / local (dev) | AI generation, learning, suggestions |
| Google Sheets | Google Workspace | Content input + calendar |
| Google Drive | Google Workspace | Media library |

### Deployment Path

```
Phase 1 (NOW): Local development
  - Python scripts on developer's machine
  - Claude Code CLI authenticated locally via OAuth
  - Calls Postiz API remotely at sethpc.xyz
  - Calls Google Sheets API
  - Fast iteration, no server access needed

Phase 2 (DEPLOY): Docker service on Seth's server
  - Add `content-engine` service to docker-compose.yaml
  - Mount ~/.claude/ volume for OAuth token persistence
  - Cron or Temporal worker for scheduled runs
  - One-time `claude login` on server to authenticate

Phase 3 (IF NEEDED): Claude API fallback
  - Only if OAuth token headless refresh proves unreliable
  - Small API budget with hard spending cap
  - Same Python code, swap CLI call for SDK call
```

## Meta-Learning System

The content intelligence layer improves over time:

1. **Collect** — After posts publish, pull engagement data from Postiz API (likes, comments, shares, reach)
2. **Analyze** — Identify patterns: what content types, pillars, times, and tones perform best
3. **Learn** — Update `data/post-performance.json` with new insights
4. **Apply** — Include learning context in every generation prompt
5. **Suggest** — Use patterns to proactively suggest content that's likely to perform well

This creates a flywheel: more posts → more data → better suggestions → better engagement → more data.

## Decisions for Temple President Meeting

- Posting frequency per platform (defaults provided above)
- Platform priority order for initial rollout
- Whether to add automated brand consistency validation beyond AI prompts
- Who is the designated content reviewer
- Facebook page rebrand authorization (still "Gita Nagari Farm" with 5.7K followers)
- Access to Google Drive photo archive for content repository
- Budget for optional Apify scraping of competitor accounts ($49/mo)
