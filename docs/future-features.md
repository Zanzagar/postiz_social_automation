# Gita Valley Social Automation — Future Features

## What's Built Today

A content creation and scheduling pipeline: staff enters raw text + media in Google Sheets → AI generates platform-specific captions via Claude → review/edit in the React dashboard → send to Postiz for scheduling across Instagram, Facebook, TikTok, Threads, LinkedIn.

**Dashboard**: [localhost:3000](http://localhost:3000) — create, review drafts, calendar view, AI suggestions, system health.

---

## Planned & Proposed Features

### 1. Website Content Syndication
**Pull content from gitavalley.com and push to social audiences.**

- Crawl/RSS feed from the website for new blog posts, event announcements, program updates
- AI summarizes long-form website content into platform-appropriate social posts
- Auto-detect content pillar from website categories (events → Events pillar, teachings → Spiritual Education, etc.)
- Option for auto-scheduling or manual review before posting
- Backfill: take existing website content library and generate a social content calendar from it

### 2. Auto-Publish Mode
- Currently all posts require manual approval (Sheet status column or dashboard)
- Add configurable auto-publish: approve immediately after AI generation, or schedule with a delay window for review
- Per-platform auto-publish rules (e.g., auto-publish to Facebook but require review for Instagram)

### 3. Content Analytics Dashboard
- Track engagement metrics per platform (likes, shares, comments, reach)
- Identify which content pillars perform best
- Best time-to-post analysis by platform
- Charts and trends over time

### 4. Dark Mode
- CSS variables already defined in the frontend theme
- Toggle in sidebar/settings

### 5. Real-Time Notifications
- WebSocket or polling for live updates when:
  - AI generation completes
  - Post is published by Postiz
  - Errors occur (failed publish, API issues)
- Optional email/WhatsApp notifications for critical alerts

### 6. Multi-User Support
- Currently single shared password
- Add user accounts with roles (admin, content creator, reviewer)
- Approval workflows: creator submits → reviewer approves → auto-publish

### 7. Media Library
- Centralized media browser (images, videos, graphics)
- Integration with Google Drive folder
- AI-suggested media for content ideas
- Template graphics for recurring content types (verse of the week, event announcements)

### 8. Content Templates
- Save reusable templates for recurring post types:
  - Sunday feast announcements
  - Weekly Bhagavad Gita verse
  - Farm update format
  - Event promotion series
- AI fills in templates with current details

### 9. PWA / Mobile Install
- Progressive Web App manifest for "Add to Home Screen"
- Offline-capable draft editing
- Push notifications on mobile

### 10. Hashtag & SEO Intelligence
- AI-suggested hashtags per platform based on content and trends
- Track hashtag performance over time
- Platform-specific hashtag strategies (Instagram max 30, Twitter best at 2-3)

### 11. Content Calendar AI Planning
- AI generates a full week/month content calendar based on:
  - Content pillar distribution targets (40/25/15/10/5/5)
  - Upcoming events and festivals (Janmashtami, Ratha Yatra, etc.)
  - Engagement patterns from analytics
  - Gaps in recent posting history

### 12. Cross-Platform Repurposing
- Take a long YouTube video → extract clips for TikTok/Reels
- Turn blog posts into carousel graphics
- Convert event photos into stories/reels with text overlays

### 13. Audience Segmentation
- Different messaging for different audience segments:
  - Devotee community (spiritual content, Sanskrit terms)
  - Local community (farm events, CSA, family programs)
  - General public (wellness, sustainable living, nature)
- AI adapts tone and vocabulary per audience

### 14. Postiz MCP Integration
- Direct Claude CLI → Postiz scheduling (bypass n8n for simple workflows)
- Conversational scheduling: "Schedule this for Thursday at 10am on Instagram and Facebook"

### 15. WhatsApp Integration
- Notification channel for post approvals
- Quick approve/reject from WhatsApp
- Content submission via WhatsApp (staff sends photo + caption → enters pipeline)

---

### 16. AI Content Iteration & Editing
**Refine and iterate on AI-generated content through conversational prompting.**

- **Click-to-edit on Calendar entries**: Click a draft post → opens editor with caption pre-filled + a prompt box ("Make it more casual", "Add a call to action", "Shorten for Twitter") → AI regenerates that platform's caption
- **Click-to-create from Suggestions**: Click a suggestion card → pre-fills the Create page with that idea as raw text → generate from there
- **Conversational refinement**: After AI generates captions, add a text input per caption ("Refine: make the Instagram version shorter") → re-generate just that platform while keeping the others

### 17. UI Component Upgrade (Magic MCP + frontend-design)
**Rebuild all frontend components using the proper design pipeline.**

- v1 components were hand-written JSX — functional but not design-polished
- Re-run each page through: `frontend-design` skill → Magic MCP `component_inspiration` → `component_builder` → `component_refiner`
- Pages to upgrade: Login, Dashboard, Create, Review Drafts, Calendar, Suggestions, Health
- Enforced by `.claude/rules/frontend-workflow.md` for all future component work

### 18. Postiz Analytics Integration
**Pull engagement metrics from Postiz into our dashboard instead of building analytics from scratch.**

- Use Postiz API to fetch likes, shares, comments, reach per post
- Display in our Analytics page — correlate with content pillars
- Avoids duplicating Postiz's existing analytics capabilities
- Postiz Admin link already in sidebar for direct access

### 19. Postiz Media Library Integration
**Use Postiz's built-in media management instead of building a separate media library.**

- Pull media assets from Postiz via API
- Display in our dashboard for content creation
- Upload media through our UI, store in Postiz
- Avoids duplicating Postiz's media storage (feature #7 replaced by this)

### 20. Embedded Postiz Admin
**Deeper integration of Postiz admin features into our dashboard.**

- Currently: external link opens Postiz in new tab
- Future: embed Postiz views via iframe or replicate key admin UIs (integration setup, account management) using Postiz API
- Requires Postiz to allow iframe embedding (X-Frame-Options) or full API coverage

---

## Priority Recommendation

**Near-term (next sprint):**
1. Website Content Syndication — directly answers temple leadership's request
2. Auto-Publish Mode — reduces manual work
3. AI Content Iteration & Editing — click-to-edit, click-to-create from suggestions, conversational refinement
4. Content Templates — saves time on recurring content

**Medium-term:**
5. Postiz Analytics Integration — pull engagement data instead of building from scratch
6. Multi-User Support
7. Content Calendar AI Planning

**Longer-term:**
7-15 based on team capacity and temple priorities

---

*Last updated: 2026-03-16*
