# Social Media Automation Pipeline — Design Document

**Date:** 2026-02-23
**Status:** Approved
**Client:** Gita Valley (ISKCON eco-farm, Port Royal, PA)

## Problem

Gita Valley has compelling daily content (85 cows, farm operations, community events, cooking, retreats) but no system for consistent social media posting. Multi-month gaps between posts result in 0.2-0.4% engagement vs. 3-6% benchmarks for farm accounts. One intern's viral TikTok generated 1,200 applications — proving demand exists when content is posted.

## Solution

Automated pipeline: Google Sheets (content calendar) → n8n (orchestration + AI captions via Claude) → Postiz (scheduling + publishing) → all platforms.

**Architecture principle:** n8n = brain, Postiz = hands.

## Architecture

### Approach

Monolithic n8n workflow for Phase 1, supporting all platforms from the start. Platform-specific workflows can be split out in Phase 4 as the system matures.

### Data Flow

```
Farm staff fills Google Sheets row:
  date, content pillar, raw text, media (Drive URL or filename), target platforms
  Sets status → "ready"
        │
        ▼
n8n Cron Trigger (daily, configurable time)
  Reads rows where: date = today AND status = "ready"
        │
        ▼
Content Validator (n8n IF node)
  Checks: text exists, media URL valid, platforms specified
  Invalid → marks row "error", optionally notifies via WhatsApp
        │
        ▼
AI Caption Generator (Claude via OAuth/Max subscription)
  Generates 1 caption per target platform
  Brand voice rules baked into system prompt
  Content pillar context shapes tone
        │
        ▼
Google Sheets Update
  Writes generated captions back to Sheet
  Sets status → "pending_approval"
  Optionally sends WhatsApp notification to reviewer
        │
        ▼
Reviewer approves in Sheet (status → "approved")
        │
        ▼
n8n Trigger (watches for "approved" rows)
  Creates post in Postiz via API for each target platform
  Schedules for optimal time window
        │
        ▼
Google Sheets Update
  status → "posted", stores Postiz post IDs, timestamp
```

### Google Sheets Schema

| Column | Type | Who fills it |
|--------|------|-------------|
| date | Date | Staff |
| content_pillar | Dropdown (Cow Life / Farm Ops / Community / Kitchen / Spiritual / CTA) | Staff |
| raw_text | Text (1-3 sentences) | Staff |
| media_url | URL (Google Drive link or filename) | Staff |
| platforms | Checkboxes (IG, FB, TikTok, Threads, LinkedIn) | Staff |
| status | Dropdown (draft / ready / pending_approval / approved / posted / error) | Automated + reviewer |
| caption_ig | Text | AI-generated |
| caption_fb | Text | AI-generated |
| caption_tt | Text | AI-generated |
| caption_th | Text | AI-generated |
| caption_li | Text | AI-generated |
| postiz_ids | Text | Automated |
| posted_at | DateTime | Automated |
| error_msg | Text | Automated |

**Staff workflow:** Fill date, pillar, raw_text, media_url, check platforms, set status to "ready". Everything else is automated.

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

PLATFORM: {platform_name}
PLATFORM RULES: {platform_specific_instructions}
CONTENT PILLAR: {pillar_from_sheet}

Generate a caption for this content: {raw_text_from_sheet}
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

| Pillar | Weight | Tone Guidance |
|--------|--------|---------------|
| Cow personalities & daily life | 40% | Personality-driven, name specific cows (Tabby, Dennis, Sparkle, Daring Denise, Brisham), emotional connection, parasocial relationship building |
| Farm operations & sustainability | 25% | Educational, sustainability focus, behind-the-scenes, regenerative agriculture expertise |
| Community & people | 15% | Spotlight format, gratitude, warmth, volunteer/intern stories |
| Kitchen & food | 10% | Recipe teasers, farm-to-table narrative, sattvic cuisine, head chef Madhupan |
| Spiritual dimension | 5% | Gentle, invitational, not doctrinal. Morning routines, festival celebrations |
| Calls to action | 5% | Clear ask, impact framing, urgency without pressure. Donate, visit, volunteer, adopt-a-cow |

### AI Provider

Claude via OAuth/Max subscription — no per-API-call cost. Model-agnostic prompt design so provider can be swapped in n8n if needed.

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

1. n8n generates AI captions, writes them to Google Sheet, sets status to "pending_approval"
2. Optionally sends WhatsApp notification to designated reviewer (stretch goal — WhatsApp Business API via n8n)
3. Reviewer reads captions in Sheet, sets status to "approved"
4. n8n picks up approved rows and publishes via Postiz

Brand consistency: enforced via AI system prompt. Automated validation check (flagging "Gita Nagari", wrong URLs) is a question for the temple president meeting.

## Media Handling

- **Source:** Google Drive shared folder as media library + direct URL in Sheet
- **Images:** JPEG, PNG, WebP. n8n downloads from Drive URL before passing to Postiz
- **Video:** MP4. Platform-specific dimension/length validation (TikTok, Instagram Reels)
- **Google Drive integration:** n8n watches a shared folder. Optional: auto-create Sheet rows when new media appears

## Error Handling

| Failure | Response |
|---------|----------|
| Google Sheets unreachable | Retry 3x, then WhatsApp/email alert |
| AI caption generation fails | Mark row "error", log reason, alert |
| Postiz API rate limit (30/hr) | Queue with exponential backoff, max 3 attempts |
| Postiz API auth failure | Alert, mark "error" |
| Media URL invalid | Post text-only or mark "error" (configurable) |
| Platform not connected in Postiz | Skip that platform, post to connected ones |

## Infrastructure

| Service | Location | Purpose |
|---------|----------|---------|
| Postiz | https://postiz.sethpc.xyz | Schedule/publish posts |
| n8n | https://n8n.sethpc.xyz | Workflow orchestration + AI |
| Google Sheets | Google Workspace | Content calendar |
| Google Drive | Google Workspace | Media library |

**Constraint:** Postiz API in beta — 30 requests/hour. Sufficient for scheduled posting (even at full cadence: 5 platforms x 5 posts/day = 25 req/day).

**Deployment constraint:** Seth manages the live server. This repo tracks desired state (docker-compose, workflow exports, documentation). We have direct access to n8n at sethpc.xyz.

## Decisions for Temple President Meeting

- Posting frequency per platform (defaults provided above)
- Platform priority order for initial rollout
- Whether to add automated brand consistency validation beyond AI prompts
- Who is the designated content reviewer
- Facebook page rebrand authorization (still "Gita Nagari Farm" with 5.7K followers)
