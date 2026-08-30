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
- **2026-08-29 polish pass (recording-polish branch)** — the 11 stale March test
  drafts were purged (backup: `data/deleted-test-rows-backup-20260829.json`) and two
  clean future-dated drafts staged (hay season, Radhastami prep). Nine real farm
  photos were imported from the Facebook page's own photo library with alt text and
  pillars (hero candidates: `sunrise-over-the-farm.jpg`, `first-snow-at-the-temple.jpg`,
  `prima-golden-hour.jpg`) — the Media → Photos filter now leads with them. Pillar
  targets were rescaled to the documented fraction contract (Per pillar tab now shows
  Target 40/25/15/10/5/5%). The 853 orphaned media files are moved to
  `~/gvsa-orphan-backup-20260829/` (Health shows "all media files in sync").
- **Safety** — a manual publish and the auto-release loop can no longer double-post the
  same row (row claim); publishing always persists your latest edits first.

## Recording-day setup (in order, ~20 min)

1. **Backend service** — restored and running under systemd (verified 2026-08-03).
   One environment fix is in place as a symlink (`.venv/bin/claude → ~/.local/bin/claude`)
   so the service can find the Claude CLI; to make it durable across venv rebuilds,
   apply the unit override once (needs sudo):
   ```bash
   sudo systemctl edit gvsa-backend
   # add:
   # [Service]
   # Environment=PATH=/home/cjh5690/projects/ISKCON-GN/postiz_social_automation/.venv/bin:/home/cjh5690/.local/bin:/usr/local/bin:/usr/bin
   sudo systemctl daemon-reload && sudo systemctl restart gvsa-backend
   ```
   (Repo reference copy: `gvsa-backend.service`.)
2. **Postiz API key** — DECISION 2026-08-17: proceed with the EXISTING key (the UI on
   our Postiz version can't regenerate, and rotation needs a one-line SQL on the
   sethpc.xyz host — deferred until Seth is available). Risk accepted knowingly: the
   key was once exposed in the public repo, so the exposure window is bounded by
   **recording promptly after connecting channels and disconnecting the channels in
   Postiz afterward** until the key is rotated (reconnecting later is a 2-min OAuth
   click per platform; App Review approvals live in the developer portals and are
   unaffected).
   - Copy the current key: Postiz dashboard → https://postiz.sethpc.xyz → Settings →
     Public API → reveal/copy.
   - Put it in `.env` as `POSTIZ_API_KEY=<key>` (repo root — replaces "placeholder").
   - Restart the backend so it picks up the key:
     `kill -9 $(systemctl show gvsa-backend -p MainPID --value)` (respawns).
   - Rotation, when Seth is reachable:
     `docker exec -it <postgres-container> psql -U <user> -d <db> -c 'UPDATE "Organization" SET "apiKey" = NULL;'`
     then reload the Postiz dashboard (auto-regenerates), copy the new key into `.env`
     + the n8n credential, restart the backend, reconnect channels if disconnected.
3. **Connect channels in Postiz** — Postiz UI → Settings → Channels → Add Channel →
   Facebook and Instagram (works in Dev Mode for app role holders). For TikTok, finish
   the developer-portal app details first (see the verification guide §3), add the
   client key/secret to **Postiz's** `.env`, restart Postiz, then connect the channel.
4. **Sanity check** — open the app (:3000) and **hard-refresh once (Ctrl+Shift+R)**
   so the browser drops any cached pre-polish bundle. Health page: everything should
   be green, sidebar badge "All services connected". Media library shows real farm
   photos (Photos filter). Analytics should land on **All time** by default.
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
2. **Per platform** tab: platform row + posting-time heatmap (the starred peak cell
   is **Sunday noon** — narrate "weekend noon is our peak").
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
