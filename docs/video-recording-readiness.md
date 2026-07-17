# App Review Screencast — Recording-Day Guide

Companion to `docs/platform-verification-guide.md` (which owns the portal steps, written
justifications, and submission flow). This guide covers **the platform side**: what was
made camera-ready, the setup you must do on recording day, and a click-by-click script
for each recording.

Last updated: 2026-07-16 (video-readiness branch).

---

## What's now camera-ready (done)

- **Publish round-trip with confirmation** — "Publish now" on the Refine step and on
  Drafts rows opens a publish modal with per-platform results (Posted · time / Scheduled /
  Failed with the real reason) and "n of m platforms published", plus "Posted to
  Instagram/Facebook" toasts. This is the confirmation moment Meta Recording A step 7 needs.
- **Media publishing works** — Drive-backed media is resolved to a public URL at publish
  time (required by Postiz and by TikTok's fetch). Note: publishing makes that Drive file
  link-shareable — intentional, since the media is going on a public feed.
- **Analytics tells the real story** — "All time" range added (the FB import ends
  Dec 2025, so shorter ranges are empty); 50 of 100 imported posts now have AI-classified
  pillars (Pillars tab is alive); pillar targets set from the documented content mix;
  hashtag intelligence populated. Reach shows "—  (no reach data imported yet)" honestly.
- **Health surfaces are truthful** — sidebar badge names the actual failing service
  (only Postiz until the key is rotated); Health page restyled with correct
  green/red status; Sheets correctly reports "Not configured (SQLite is the source of truth)".
- **Test data deleted** — the 9 test drafts are gone (backup:
  `data/deleted-test-rows-backup-20260716.json`). No stock imagery or "Gita Nagari"
  branding anywhere in the UI (verified by sweep).
- **Safety** — a manual publish and the auto-release loop can no longer double-post the
  same row (row claim); publishing always persists your latest edits first.

## Recording-day setup (in order, ~20 min)

1. **Restore the backend service** (needs your sudo; a manual process is serving :8000
   meanwhile):
   ```bash
   kill $(pgrep -f "uvicorn api.main:app") && sudo systemctl start gvsa-backend
   ```
2. **Rotate the Postiz API key** (the one blocking step only you can do):
   - Postiz dashboard → https://postiz.sethpc.xyz → Settings → API → generate new key,
     revoke the old one.
   - Put it in `.env` as `POSTIZ_API_KEY=<new key>` (repo root).
   - Restart the backend so it picks up the key:
     `kill -9 $(systemctl show gvsa-backend -p MainPID --value)` (respawns).
   - Update the n8n credential too (separate host) when convenient — not needed for
     the recordings.
3. **Connect channels in Postiz** — Postiz UI → Settings → Channels → Add Channel →
   Facebook and Instagram (works in Dev Mode for app role holders). For TikTok, finish
   the developer-portal app details first (see the verification guide §3), add the
   client key/secret to **Postiz's** `.env`, restart Postiz, then connect the channel.
4. **Sanity check** — open the app (:3000), Health page: everything should be green,
   sidebar badge "All services connected". Media library shows real farm photos.
5. *(Optional, better Recording C)* **Backfill reach data** from the Graph API:
   ```bash
   META_PAGE_ACCESS_TOKEN=<page token> python -m content_engine.scripts.backfill_history_insights
   ```
   Uses the page token (Bearer header; errors are token-redacted). Without this,
   reach honestly shows "—".
6. *(As needed)* Re-run pillar classification for any remaining unlabeled history posts:
   `python -m content_engine.scripts.backfill_history_pillars` (17 posts stayed
   unclassified; 33 have no text and never will classify).

## Recording scripts

Record at 1080p, MP4 (OBS/Loom/QuickTime). Use the prod app on **localhost:3000**.
Sign in before you start recording, or show the login (it's presentable).

### Meta Recording A — Posting flow (~60s)
Covers `pages_show_list`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`.
1. Open the app → **Compose**.
2. (Nice touch) Start from **Media**: pick a farm photo → "Use in a draft" — it lands in
   Compose with alt text prefilled.
3. Type one sentence (e.g. "Morning in the east pasture — the herd greeting the sun"),
   pick a pillar, select **Facebook + Instagram**.
4. **Generate captions** — the per-platform captions stream in (30–90s; trim this wait
   in the edit or narrate over it).
5. On the Refine step, click **Publish now**.
6. The modal shows Facebook and Instagram flipping to **Posted ·  time**, footer
   "2 of 2 platforms published", and "Posted to Facebook/Instagram" toasts.
   That's the confirmation beat — hold on it for a few seconds.

### Meta Recording B — Engagement & comments (~60s)
Covers `instagram_manage_comments`, `pages_manage_engagement`, `pages_read_engagement`.
1. Open **Analytics** → set range to **All time**.
2. Overview: engagement KPIs, engagement-by-day chart, Top post card.
3. **Per post** tab: the posts table with per-post engagement and trends.
4. **Per pillar** tab: the pillar distribution with actual-vs-target bars —
   narrate "engagement data drives our content mix across pillars".
   (There is no comments-reply view — skip that optional beat.)

### Meta Recording C — Insights & analytics (~60s)
Covers `read_insights`, `instagram_manage_insights`.
1. **Analytics** → All time → Overview (reach KPI — real numbers if you ran the
   insights backfill; "—" otherwise, in which case lean on engagement + trends).
2. **Per platform** tab: platform row + posting-time heatmap ("peak Saturday noon").
3. **Rhythm** tab: weekly cadence + festival markers.
4. End on the Dashboard for the daily-pulse view.

### TikTok demo (2–3 min)
1. **Media** → upload or pick an **mp4** (REEL badge) → add alt text in the inspector.
2. "Use in a draft" → Compose → sentence → select **TikTok** → Generate.
3. Refine → **Publish now** → modal shows TikTok **Posted**.
4. Open TikTok (the @gitavalley account) and show the post in sandbox/private.
   Reminder from the guide: the domain shown must match the redirect URI
   (postiz.sethpc.xyz), so also show the Postiz dashboard with the queued/sent post.

### YouTube
No video needed — it's a form audit (verification guide §2). Blocked on the Workspace
admin trust step, independent of the app.

## Known honest gaps (fine on camera)

- Reach/impressions are "—" until the insights backfill runs (or until real posting
  builds analytics_cache).
- 50 imported posts remain unpillared (33 have no text). The Pillars tab uses the 50
  classified ones.
- Comments-reply UI doesn't exist — Recording B's optional comment beat is skipped;
  the engagement permissions are justified by the metrics displays.
- `analytics_cache` (app-posted content metrics) fills only after real posts go out
  through Postiz and the sync runs — the history import carries Recordings B/C.
