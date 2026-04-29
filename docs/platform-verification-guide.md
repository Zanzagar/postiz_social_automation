# Platform Verification & App Review Guide

All verifications are tied to developer portals, not Postiz. Rebuilding Postiz does NOT require re-verification.

Privacy Policy URL for all platforms: `https://gitavalley.org/privacy-policy/`

---

## 1. Meta App Review (Facebook + Instagram)

**Portal**: [developers.facebook.com](https://developers.facebook.com)
**App ID**: `955821356900142`
**App Name**: Gita Valley Social Analytics
**Business Portfolio**: Gita Nagari Farm (ID: `816957151986167`)
**Facebook Page**: Gita Nagari Farm (ID: `293313989490`)
**Instagram Business Account**: ID `17841404334505942`
**Timeline**: 1-4 weeks
**What it unlocks**: Advanced Access for posting + analytics. Posting works in Dev Mode for app role holders only; Advanced Access allows any authorized user and unlocks full analytics.

### Current Status (as of 2026-04-22)

- [x] Meta App created (`955821356900142`)
- [x] Business Portfolio linked (Gita Nagari Farm)
- [x] Instagram Business Account linked to Facebook Page
- [x] Instagram linked to Business Portfolio (via business.facebook.com > Accounts > Instagram accounts)
- [x] Test API calls completed for all 5 permissions requiring them (2026-04-22)
- [ ] Wait 24 hours for "Request Advanced Access" buttons to activate (~2026-04-23)
- [ ] Submit all 10 permissions for Advanced Access review
- [ ] Switch app to Live Mode

### Permissions to Request (all 10 at once)

#### For Postiz Posting (Facebook) — 3 permissions
| Permission | Purpose | Test call needed? |
|---|---|---|
| `pages_show_list` | Postiz sees your page | No |
| `pages_manage_posts` | Publish content | No |
| `business_management` | Business asset access | No |

#### For Postiz Posting (Instagram) — 3 permissions
| Permission | Purpose | Test call needed? |
|---|---|---|
| `instagram_basic` | IG account connection | No |
| `instagram_content_publish` | IG posting | Yes — completed 2026-04-22 |
| `instagram_manage_comments` | IG comment management | Yes — completed 2026-04-22 |

#### For Analytics Dashboard (Content Hub) — 4 permissions
| Permission | Purpose | Test call needed? |
|---|---|---|
| `pages_read_engagement` | Read likes, comments, shares | No |
| `pages_manage_engagement` | Manage/respond to comments | Yes — completed 2026-04-22 |
| `read_insights` | Read reach, impressions, demographics | Yes — completed 2026-04-22 |
| `instagram_manage_insights` | IG analytics | Yes — completed 2026-04-22 |

### Test API Calls (Prerequisite — DONE)

5 of 10 permissions require a successful test API call before the "Request Advanced Access" button activates (up to 24 hours after the call). All 5 were completed on 2026-04-22 via the Graph API Explorer:

| Permission | Test call | Result |
|---|---|---|
| `instagram_content_publish` | POST /{ig-user-id}/media + media_publish | Success (post created and published) |
| `instagram_manage_comments` | GET /{ig-post-id}/comments | Success (empty array — no comments yet) |
| `pages_manage_engagement` | GET /{page-id}/feed?fields=id,message,comments.limit(1) | Success (returned posts + comments) |
| `read_insights` | GET /{page-id}/insights?metric=page_views_total&period=day | Success (empty data — expected) |
| `instagram_manage_insights` | GET /{ig-user-id}/insights?metric=reach&period=day | Success (returned real reach data) |

### App Settings (do before submitting review)

1. Go to Meta Developers > App `955821356900142` > Settings > Basic
2. Upload app icon (any Gita Valley logo)
3. Set category: "Business"
4. Set Privacy Policy URL: `https://gitavalley.org/privacy-policy/`
5. Set Terms of Service URL: `https://gitavalley.org/privacy-policy/`
6. Save changes
7. Add Postiz redirect URIs under Facebook Login > Settings > Valid OAuth Redirect URIs:
   - `https://postiz.sethpc.xyz/integrations/social/facebook`
   - `https://postiz.sethpc.xyz/integrations/social/instagram`

### Submission: Written Justifications (per permission)

Copy-paste these into the "Describe how you will use this permission" field for each:

**`pages_show_list`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary in Port Royal, PA. This permission allows our scheduling application to display the Facebook Page owned by our organization so staff can select it as a publishing target. Used for a single Facebook Page managed by our social media team. No third-party user data is collected.

**`pages_manage_posts`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Publishes AI-assisted, staff-approved content to a single Facebook Page on a scheduled basis. Content covers spiritual education, farm life, community events, and cow protection — all created and reviewed by our social media team before publishing. No third-party user data is collected.

**`business_management`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. This permission allows the application to access business assets (Pages and Instagram accounts) within our Meta Business Portfolio for content scheduling and analytics. Used exclusively for assets owned by our organization. No third-party user data is collected.

**`instagram_basic`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. This permission allows the application to connect our Instagram Business Account for content scheduling. Used for a single Instagram account owned by our organization. No third-party user data is collected.

**`instagram_content_publish`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Publishes staff-approved content to our organizational Instagram Business Account on a scheduled basis. Content is AI-drafted, human-reviewed, and covers spiritual education, farm life, and community events. No third-party user data is collected.

**`instagram_manage_comments`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Reads and manages comments on our Instagram posts to enable community engagement tracking within our content dashboard. Helps our social media team monitor audience response and reply to followers from a single interface. No third-party user data is collected.

**`pages_read_engagement`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Reads engagement metrics (likes, comments, shares) on our Facebook Page posts to populate an analytics dashboard. Data is used internally to optimize posting schedule and content pillar distribution (spiritual education, farm life, events, etc.). No third-party user data is collected.

**`pages_manage_engagement`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Reads and manages comments and reactions on our Facebook Page to enable community engagement tracking. Allows our social media team to monitor and respond to audience interactions from a centralized dashboard. No third-party user data is collected.

**`read_insights`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Reads Page-level insights (reach, impressions, demographics) to populate an analytics dashboard used by our social media team. Data drives content strategy decisions — identifying which content pillars and posting times generate the most community engagement. No third-party user data is collected.

**`instagram_manage_insights`:**
> Self-hosted content management tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary. Reads Instagram account and media insights (reach, impressions, engagement) to populate an analytics dashboard. Data helps our social media team evaluate content performance across platforms and optimize our posting strategy. No third-party user data is collected.

### Submission: Screen Recordings

Batch into 3 recordings (~60 seconds each) rather than 10 individual ones. Use OBS (free), Loom, or QuickTime. 1080p minimum, MP4 format.

**Recording A — Posting Flow** (covers: `pages_show_list`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`)
1. Open the Content Hub (localhost:3000 or deployed URL)
2. Navigate to the **Create** page
3. Enter content — type a short caption, select a content pillar
4. Select **Facebook** and **Instagram** as target platforms
5. Click Generate / Preview to show AI-assisted caption
6. Click Publish (or show the scheduling flow)
7. Show confirmation that content was sent to both platforms

Optional narration: "This is our internal content management tool. Staff creates content, selects target platforms, and publishes to our Facebook Page and Instagram account."

**Recording B — Engagement & Comments** (covers: `instagram_manage_comments`, `pages_manage_engagement`, `pages_read_engagement`)
1. Open the Content Hub
2. Navigate to the **Analytics** page or **Dashboard**
3. Show engagement metrics — likes, comments, shares per post
4. Show the top posts section with engagement data
5. Show pillar distribution chart (demonstrates how engagement data drives strategy)
6. If there's a comments view, show reading/responding to a comment

Optional narration: "Our dashboard displays engagement metrics from our Facebook Page and Instagram account. We use this data to optimize our content strategy across five content pillars."

**Recording C — Insights & Analytics** (covers: `read_insights`, `instagram_manage_insights`)
1. Open the Content Hub
2. Navigate to the **Analytics** page
3. Show reach and impressions data (even if sparse)
4. Show any charts/graphs displaying trends over time
5. Show pillar breakdown — how insights inform content distribution
6. Scroll through to show the full analytics dashboard

Optional narration: "Our analytics dashboard reads Page-level and Instagram insights to help our social media team evaluate content performance and adjust our posting schedule."

### Submission: Q&A Answers

| Question | Answer |
|---|---|
| "Are you creating an integration for multiple business clients?" | **No** |
| "Are you creating an integration on behalf of an individual client?" | **Yes** |
| "Does your app store Facebook data?" | **Yes — post metadata and engagement metrics in a local database for analytics. No personal user data is stored.** |
| "How long is data retained?" | **Indefinitely, for historical trend analysis. Data is stored locally and not shared with third parties.** |

This routes into the 1:1 (Tech Provider) flow — simpler than SaaS, no annual re-verification.

### Submission Steps (after 24-hour wait)

1. Go to App Review > Permissions and Features
2. For each of the 10 permissions, click "Request Advanced Access"
3. Paste the corresponding written justification
4. Upload the appropriate screen recording (A, B, or C)
5. After all 10 are submitted, switch app from Development to **Live Mode**

### Business Verification

Meta may request business verification as part of the review. Have ready:
- EIN (tax ID) for Gita Valley / ISKCON Gita Nagari (501(c)(3) nonprofit)
- Domain ownership proof (gitavalley.org)
- Or utility bill / official document showing the organization name and address

### What Happens After Approval

- All 10 permissions become available at Advanced Access level
- Any user (not just app role holders) can authorize the app
- Analytics endpoints in the content hub will populate with real engagement data
- No further action needed — permissions persist indefinitely unless Meta changes policy

### Key IDs Reference

| Asset | ID |
|---|---|
| Meta App | `955821356900142` |
| Business Portfolio | `816957151986167` |
| Facebook Page | `293313989490` |
| Instagram Business Account | `17841404334505942` |

---

## 2. YouTube API Compliance Audit

**Portal**: [Google Cloud Console](https://console.cloud.google.com)
**Project**: `gita-valley-content-repository` (Project Number: `533124303545`)
**Service Account**: `content-engine@gita-valley-content-repository.iam.gserviceaccount.com`
**YouTube Channel**: Gita Valley (Brand Account, managed by `iot.admin@gitavalley.org`)
**Timeline**: Unknown (days to weeks, no guaranteed SLA)
**What it unlocks**: Uploading videos as public or unlisted via API. Without this, all API uploads are forced to private.

### Current Status (as of 2026-04-22)

- [x] YouTube Data API v3 enabled
- [x] YouTube Analytics API enabled
- [x] YouTube Reporting API enabled
- [x] OAuth consent screen configured (External, app name "Gita Valley Content Hub")
- [x] OAuth client ID created (Web application)
- [x] `iot.admin@gitavalley.org` added as test user on consent screen
- [ ] Add redirect URI to OAuth client: `https://postiz.sethpc.xyz/integrations/social/youtube`
- [ ] Add `iot.admin@gitavalley.org` as Editor on Cloud project (IAM)
- [ ] **BLOCKED**: Brand Account trust step — needs Workspace admin for gitavalley.org
- [ ] Submit YouTube API Compliance Audit form
- [ ] Receive audit approval

### OAuth Credentials

Stored securely outside this repo. Configured in Postiz `.env` as:
```
YOUTUBE_CLIENT_ID=<stored securely>
YOUTUBE_CLIENT_SECRET=<stored securely>
```

### Setup Steps

#### Completed

1. **APIs enabled** — YouTube Data API v3, Analytics API, Reporting API all enabled in project `gita-valley-content-repository`
2. **OAuth consent screen** — Configured as External, app name "Gita Valley Content Hub", support email `coreyhoydic@gmail.com`, test user `iot.admin@gitavalley.org`
3. **OAuth client ID** — Created (Web application type), Client ID and Secret saved securely

#### Remaining

4. **Add redirect URI** to the OAuth client:
   - Cloud Console → Credentials → click on the OAuth client
   - Under "Authorized redirect URIs" add: `https://postiz.sethpc.xyz/integrations/social/youtube`
   - Save

5. **Add `iot.admin@gitavalley.org` as Editor** on the Cloud project:
   - IAM & Admin → IAM → Grant Access
   - Principal: `iot.admin@gitavalley.org`
   - Role: Editor
   - Save

6. **Brand Account trust step** (BLOCKED — needs Workspace admin):
   - Sign in to [admin.google.com](https://admin.google.com) as a **gitavalley.org Workspace super admin**
   - `iot.admin@gitavalley.org` is NOT a Workspace admin — cannot do this step
   - Navigate: Security → Access and data control → API Controls → Manage Third Party App Access
   - Click "Add app" → "OAuth App Name or Client ID"
   - Enter the OAuth Client ID
   - Set access to **Trusted**
   - Wait 5+ hours for propagation

   **Alternatives if no Workspace admin is available:**
   - Try connecting in Postiz without this step — consent screen is in Testing mode with `iot.admin@` as a test user, so it *might* work
   - If blocked with "admin has restricted this app" error, then Workspace admin is required
   - Find out who set up Google Workspace for gitavalley.org — that person is the super admin

### Submission Steps (after setup is complete)

1. Go to [YouTube API Compliance Audit Form](https://support.google.com/youtube/contact/yt_api_form)
2. Sign in with the Google account that owns the Cloud project (`coreyhoydic@gmail.com`)
3. Fill out the form:

| Field | Value |
|---|---|
| Your name | Corey Hoydic |
| Email | coreyhoydic@gmail.com |
| API Client name | Gita Valley Content Hub |
| API Project number | 533124303545 |

**"Describe your API project":**
> Self-hosted social media scheduling tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary in Port Royal, PA. Uses YouTube Data API to upload educational and community content videos to a single organizational YouTube channel on a scheduled basis. The tool is used internally by our social media team, not offered as a service to external users.

**"How does your project comply with YouTube API Terms of Service":**
> The project uploads content only to a single channel owned by our organization. No user data is collected from third parties. No automated scraping or data harvesting. Content is original, created by our social media team. The application is not distributed to external users — it is a self-hosted internal tool.

**"Do you store YouTube data?":**
> Yes — we store video IDs and upload timestamps in a local SQLite database to track publishing history. No viewer data, comments, or analytics data are stored locally.

**Privacy policy URL:** `https://gitavalley.org/privacy-policy/`

4. Submit

### Authorization Letter

Google may ask for proof of organizational authorization. Have the temple president send a simple email:

> I, [Temple President Name], [Title] of Gita Valley (ISKCON Gita Nagari), authorize Corey Hoydic to manage the Gita Valley YouTube channel via API using the Gita Valley Content Hub application (Google Cloud Project #533124303545).
>
> [Signature]
> [Date]

### Workaround While Waiting

Upload videos as private via API, then manually set to public/unlisted in YouTube Studio. Functional but defeats automation purpose.

### What Happens After Approval

- API uploads can be set to public or unlisted
- Default quota: 10,000 units/day (more than sufficient for typical use)
- No further action needed

### Key IDs Reference

| Asset | ID |
|---|---|
| Google Cloud Project | `gita-valley-content-repository` |
| Project Number | `533124303545` |
| Service Account | `content-engine@gita-valley-content-repository.iam.gserviceaccount.com` |
| YouTube Channel Owner | `iot.admin@gitavalley.org` |
| Cloud Project Owner | `coreyhoydic@gmail.com` |

---

## 3. TikTok Production Review

**Portal**: [developers.tiktok.com](https://developers.tiktok.com)
**TikTok Handle**: [@gitavalley](https://www.tiktok.com/@gitavalley)
**Account Email**: `socialmedia@gnecofarm.org`
**Organization**: Gita Valley (created on developers.tiktok.com)
**Account Type**: Business (confirmed 2026-04-25)
**Timeline**: 5-10 business days after submission
**What it unlocks**: Posting videos publicly via API. Without this, all uploads stay in sandbox (private, max 128MB file size).

### Current Status (as of 2026-04-29)

- [x] TikTok account exists (@gitavalley)
- [x] Account is Business type (confirmed)
- [x] Logged into developers.tiktok.com as `socialmedia@gnecofarm.org`
- [x] Organization "Gita Valley" created on developer portal
- [x] Developer app "Gita Valley Social" created — Client Key + Client Secret generated
- [ ] Fill in app details (icon, category, description, URLs)
- [ ] Add products: Login Kit + Content Posting API
- [ ] Add scopes
- [ ] Add redirect URI for Postiz
- [ ] Connect TikTok in Postiz (sandbox mode)
- [ ] Record demo video of sandbox upload flow
- [ ] Write review explanation
- [ ] Submit for production review

### App Details (fill in on developer portal)

| Field | Value |
|---|---|
| App icon | Gita Valley logo (1024x1024, JPEG/PNG, <5MB) |
| App name | Gita Valley Social |
| Category | Select closest to "Social Media" or "Business" |
| Description | `Self-hosted social media scheduling tool for Gita Valley, a 501(c)(3) nonprofit farm and cow sanctuary. Manages and publishes scheduled content to our organizational TikTok account.` |
| Terms of Service URL | `https://gitavalley.org/privacy-policy/` |
| Privacy Policy URL | `https://gitavalley.org/privacy-policy/` |
| Platforms | **Web** (check only Web) |

### Products to Add

Click "Add products" and enable:

1. **Login Kit**
   - Add redirect URI: `https://postiz.sethpc.xyz/integrations/social/tiktok`
2. **Content Posting API**
   - Enable "Direct Post"

### Scopes to Add

Click "Add scopes" and request:
- `user.info.basic`
- `user.info.profile`
- `video.create`
- `video.upload`
- `video.publish`

### App Review Explanation (paste into the review text field)

> Gita Valley Social is a self-hosted social media scheduling tool for Gita Valley (ISKCON Gita Nagari), a 501(c)(3) nonprofit farm and cow sanctuary in Port Royal, PA. The app uses Login Kit to authenticate our organizational TikTok account, and Content Posting API to publish scheduled video content. Content is created by our social media team — educational videos about sustainable farming, cow protection, and community events. The tool is used internally by a single organization and is not offered as a service to external users. Only our own organizational account is accessed. No third-party user data is collected, shared, or stored.

### Demo Video (required for submission)

Record a 2-3 minute screen recording (OBS, Loom, or QuickTime) showing:
1. Open Postiz (postiz.sethpc.xyz) or the Content Hub
2. Create a new post with a video file
3. Select TikTok as the target platform
4. Submit the post
5. Show the post appearing in TikTok (private/sandbox is fine)

Tips:
- MP4 or MOV format, max 50MB per file
- Narration is helpful but not required
- Sandbox mode is expected — the video does NOT need to be public
- Domain shown in video must match redirect URI (postiz.sethpc.xyz)

### Remaining Sequence

1. Fill in app details + add products + add scopes (above)
2. Save app details on developer portal
3. Copy Client Key + Client Secret → add to Postiz `.env`:
   ```
   TIKTOK_CLIENT_ID=<Client Key>
   TIKTOK_CLIENT_SECRET=<Client Secret>
   ```
4. Restart Postiz: `docker compose restart postiz`
5. Connect TikTok in Postiz: Settings → Channels → Add Channel → TikTok
6. Test a sandbox upload through Postiz
7. Record demo video of the working flow
8. Paste review explanation + upload demo video on developer portal
9. Submit for production review
10. Wait 5-10 business days

### Important TikTok Caveat

Media files must be **publicly reachable over HTTPS** for TikTok's servers to fetch them. Localhost or private routes will fail. Your Postiz instance at sethpc.xyz should handle this, but verify that uploaded media files are accessible at a public URL.

### If Rejected

TikTok provides specific feedback on what to fix. Common rejection reasons:
- Demo video doesn't clearly show the upload flow
- Privacy policy is missing or inaccessible
- App description is too vague
- Scopes shown in video don't match requested scopes

Fix the cited issues and resubmit. Re-review is typically faster.

### What Happens After Approval

- Sandbox restrictions are lifted
- Video uploads become publicly visible
- File size limit increases from 128MB to 10GB
- No further action needed

### Key IDs Reference

| Asset | Value |
|---|---|
| TikTok Handle | @gitavalley |
| Account Email | `socialmedia@gnecofarm.org` |
| Developer Org | Gita Valley |
| App Name | Gita Valley Social |
| Client Key | Stored securely outside repo |
| Client Secret | Stored securely outside repo |

---

## Timeline Overview

| Platform | Submit when | Expected wait | Posts publicly |
|---|---|---|---|
| Facebook | Day of meeting | 1-4 weeks (posting works day 1 without review) | Day 1 |
| Instagram | Day of meeting | Same Meta review as Facebook | Day 1 |
| YouTube | Day after meeting | Unknown (days to weeks) | After audit approval |
| TikTok | ~3-5 days after meeting | 5-10 business days | ~2-3 weeks after meeting |

## Key Principle

All verifications are stored in the **platform developer portals**, not in Postiz. If Postiz is rebuilt, moved, or upgraded:
- No verification needs to be redone
- Only re-authorize OAuth connections (click "Connect" again, ~2 min per platform)
- Keep the same domain (`postiz.sethpc.xyz`) so redirect URIs remain valid
- If the domain changes, update redirect URIs in all developer portals (5 min total)

## Postiz Environment Variables (After All Setup)

```bash
# Facebook + Instagram (same Meta App)
FACEBOOK_APP_ID=955821356900142
FACEBOOK_APP_SECRET=<from Meta Developers > App > Settings > Basic>

# TikTok
TIKTOK_CLIENT_ID=<16 chars from TikTok Developer Portal>
TIKTOK_CLIENT_SECRET=<32 chars from TikTok Developer Portal>

# YouTube
YOUTUBE_CLIENT_ID=<from Google Cloud Console > Credentials>
YOUTUBE_CLIENT_SECRET=<from Google Cloud Console > Credentials>
```

After updating `.env`, restart Postiz: `docker compose restart postiz`

Then connect each channel: Postiz UI > Settings > Channels > Add Channel
