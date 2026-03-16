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

## Priority Recommendation

**Near-term (next sprint):**
1. Website Content Syndication — directly answers temple leadership's request
2. Auto-Publish Mode — reduces manual work
3. Content Templates — saves time on recurring content

**Medium-term:**
4. Content Analytics Dashboard
5. Multi-User Support
6. Content Calendar AI Planning

**Longer-term:**
7-15 based on team capacity and temple priorities

---

*Last updated: 2026-03-16*
