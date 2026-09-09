# Read Access to Our Own Social Data via Own, Unaudited Developer Apps

Date: 2026-09-08

Question: what READ access (content + engagement metrics, full history) does Gita Valley get to its OWN Facebook Page (id 293313989490, ~1,600 posts), Instagram Business account, YouTube channel and TikTok account when it uses its OWN developer apps that have NOT passed review — Meta app in Development mode / Standard Access, Google Cloud OAuth project "In production, unverified" with no YouTube compliance audit, TikTok app in Sandbox or unaudited Production — and does self-hosting Postiz change any of that?

Scope note: every claim below traces to a first-party page or first-party source file fetched on 2026-09-08. Where a platform's docs are silent, the doc says so rather than guessing.

## Sources

All fetched 2026-09-08.

Meta
- [S1] App Modes — https://developers.facebook.com/docs/development/build-and-test/app-modes
- [S2] Access Levels — https://developers.facebook.com/docs/graph-api/overview/access-levels
- [S3] Rate Limits — https://developers.facebook.com/docs/graph-api/overview/rate-limiting
- [S4] Business Verification — https://developers.facebook.com/docs/development/release/business-verification
- [S5] App Roles — https://developers.facebook.com/docs/development/build-and-test/app-roles
- [S6] Page /feed — https://developers.facebook.com/docs/graph-api/reference/page/feed
- [S7] Page /posts — https://developers.facebook.com/docs/graph-api/reference/page/posts
- [S8] Page /published_posts — https://developers.facebook.com/docs/graph-api/reference/page/published_posts
- [S9] Page Post node — https://developers.facebook.com/docs/graph-api/reference/pagepost/
- [S10] Post /comments — https://developers.facebook.com/docs/graph-api/reference/post/comments
- [S11] Page /insights — https://developers.facebook.com/docs/graph-api/reference/page/insights
- [S12] Insights metric reference (page_* and post_*) — https://developers.facebook.com/docs/graph-api/reference/insights
- [S13] Permissions reference — https://developers.facebook.com/docs/permissions
- [S14] Page Public Content Access feature — https://developers.facebook.com/docs/features-reference/page-public-content-access
- [S15] Long-lived tokens — https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived
- [S16] Token debugging & errors — https://developers.facebook.com/docs/facebook-login/access-tokens/debugging-and-error-handling
- [S17] IG Media /insights — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/insights
- [S18] IG User /insights — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/insights
- [S19] IG User /media — https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
- [S20] IG Insights guide — https://developers.facebook.com/docs/instagram-platform/insights
- [S21] Platform Terms — https://developers.facebook.com/terms/
- [S22] Developer Policies — https://developers.facebook.com/devpolicy/

Google / YouTube
- [S23] Data API quota — https://developers.google.com/youtube/v3/getting-started
- [S24] Quota & compliance audits — https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
- [S25] videos.insert (private-upload restriction) — https://developers.google.com/youtube/v3/docs/videos/insert
- [S26] videos resource (statistics) — https://developers.google.com/youtube/v3/docs/videos
- [S27] channels resource (statistics) — https://developers.google.com/youtube/v3/docs/channels
- [S28] commentThreads.list — https://developers.google.com/youtube/v3/docs/commentThreads/list
- [S29] Analytics API metrics — https://developers.google.com/youtube/analytics/metrics
- [S30] Analytics API dimensions — https://developers.google.com/youtube/analytics/dimensions
- [S31] Analytics channel reports — https://developers.google.com/youtube/analytics/channel_reports
- [S32] Analytics reports.query — https://developers.google.com/youtube/analytics/reference/reports/query
- [S33] Reporting API (bulk) — https://developers.google.com/youtube/reporting/v1/reports/
- [S34] Unverified apps (Cloud Console help) — https://support.google.com/cloud/answer/7454865
- [S35] Sensitive-scope verification — https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification
- [S36] OAuth 2.0 overview (refresh-token expiry) — https://developers.google.com/identity/protocols/oauth2
- [S37] OAuth verification requirements — https://support.google.com/cloud/answer/13463073

TikTok
- [S38] Display API overview — https://developers.tiktok.com/docs/en/display-api-overview
- [S39] Display API get started — https://developers.tiktok.com/docs/en/display-api-get-started
- [S40] /v2/video/list/ — https://developers.tiktok.com/doc/tiktok-api-v2-video-list
- [S41] /v2/video/query/ — https://developers.tiktok.com/doc/tiktok-api-v2-video-query
- [S42] Video object — https://developers.tiktok.com/doc/tiktok-api-v2-video-object
- [S43] /v2/user/info/ — https://developers.tiktok.com/doc/tiktok-api-v2-get-user-info
- [S44] Scopes reference — https://developers.tiktok.com/doc/tiktok-api-scopes
- [S45] Add a Sandbox — https://developers.tiktok.com/docs/en/add-a-sandbox
- [S46] Register your app — https://developers.tiktok.com/docs/en/getting-started-create-an-app
- [S47] App Review FAQ — https://developers.tiktok.com/docs/en/getting-started-faq
- [S48] App Review Guidelines — https://developers.tiktok.com/docs/en/app-review-guidelines
- [S49] Research API — https://developers.tiktok.com/products/research-api

Postiz (source at `main`, fetched 2026-09-08)
- [P1] facebook.provider.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/integrations/social/facebook.provider.ts
- [P2] instagram.provider.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts
- [P3] youtube.provider.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/integrations/social/youtube.provider.ts
- [P4] tiktok.provider.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts
- [P5] public.integrations.controller.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/apps/backend/src/public-api/routes/v1/public.integrations.controller.ts
- [P6] integration.service.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/database/prisma/integrations/integration.service.ts
- [P7] schema.prisma — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/database/prisma/schema.prisma
- [P8] throttler.provider.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/throttler/throttler.provider.ts ; app.module.ts — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/apps/backend/src/app.module.ts
- [P9] Postiz docs: Analytics — https://docs.postiz.com/general/analytics.md ; Public API overview — https://docs.postiz.com/public-api.md ; Platform analytics — https://docs.postiz.com/public-api/analytics/platform.md

## TL;DR

| Platform | Own unaudited app can read… | Hard caps that matter for a 1,600-post backfill |
|---|---|---|
| Facebook Page | Full Page feed/posts (message, attachments, permalink, `shares.count`, `reactions.summary`, `comments`), post insights, Page insights, with **Standard Access in Development mode** because the Page admin holds an app role [S2][S4] | `/feed`: "approximately 600 ranked, published posts per year", max 100 per request [S6][S7][S8]; all insights: "Only the last two years of insights data is available", 90 days per `since/until` query, Page needs 100+ likes [S11][S12] |
| Instagram Business | Media list + media insights + account insights via `instagram_manage_insights` [S17][S18] | Media edge returns "a maximum of 10K of the most recently created media" [S19]; media "Metrics data is stored for up to 2 years", stories 24h [S17]; account "User Metrics data is stored for up to 90 days" [S20] |
| YouTube | Everything: `videos.list` statistics, `channels.list`, comments, full YouTube Analytics API (all dimensions/metrics) — no read is gated by audit or verification [S23][S24][S25][S32] | Default 10,000 units/day, list calls cost 1 unit [S23]; unverified consent screen caps **new** users at 100 total [S34] — irrelevant for one internal account |
| TikTok | Display API: `user.info.stats` counts + per-video `view/like/comment/share_count`, title, description, create_time — for **public** videos of the authorized account [S40][S42][S43] | Sandbox: up to 10 target accounts, Display API works, no review needed [S45]; unaudited Production: "you will not have access to the APIs until your application has been approved" [S47]; 20 videos per page with cursor [S40] |
| Postiz (any hosting) | A fixed, small subset of the above, snapshot-only for posts, Redis-cached 1 h, no history table [P1–P7] | Analytics endpoints wrap the same platform calls with fewer metrics; the DB holds tokens and Postiz-authored posts, not platform history [P7] |

**Verdict:** self-hosting Postiz gives **no additional read access** to the nonprofit's own content or metrics. Postiz's analytics (Cloud or self-hosted) are a strict subset of what the nonprofit's own apps return when called directly, and the same unaudited-app permissions are what a self-hosted Postiz would be using anyway. The knowledge database should be fed by direct Graph / YouTube / TikTok calls with the nonprofit's own app tokens; Postiz hosting choice is orthogonal to read access. Details in Section D.

## A. Meta (Facebook Page + Instagram Business)

### A1. What Standard Access in Development mode allows

App Modes [S1]:
> "Apps in Development mode can only request permissions from role users, and only permissions with standard or advanced access levels."
> "Any data generated while an app is in Development mode, such as test posts, can only be seen by role users."
> "All newly created apps start out in Development mode and should not be switched to Live mode until app development is complete."

Access Levels [S2]:
> "Permissions with Standard Access can only be requested from app users who have a role on the requesting app."
> "All Business, Consumer, and Gaming apps are automatically approved for Standard Access for all permissions and features."
> "Advanced Access, however, must be approved on an individual permission and feature basis through the App Review process."
> "Apps that have Advanced Access for a permission or feature must complete Data Use Checkup, which is an annual process"

App Roles [S5]: Administrators, Developers and Testers "can grant the app any permission while it is in development"; Testers may be "registered Meta developers and regular users".

Business Verification [S4]:
> "If your app will only be used by app users who have a role on the app itself you do not need to complete verification; these users can grant your app any permissions at any time and all features are always active."

So: with the Page admin holding an app role (Admin/Developer/Tester), the app can be granted `pages_show_list`, `pages_read_engagement`, `pages_read_user_content`, `read_insights`, `instagram_basic`, `instagram_manage_insights` at Standard Access with no App Review and no Business Verification. The permission reference [S13] describes what each permits:

| Permission | Meta's description [S13] |
|---|---|
| `pages_read_engagement` | "allows your app to read content (posts, photos, videos, events) posted by the Page, read followers data (including name, PSID), and profile picture, and read metadata and other insights about the Page" |
| `pages_read_user_content` | "allows your app to read user generated content on the Page, such as posts, comments, and ratings by users or other Pages" |
| `read_insights` | "allows your app to read the Insights data for Pages, apps and web domains the person owns" |
| `instagram_basic` | "allows your app to read an Instagram account profile's info and media" |
| `instagram_manage_insights` | "allows your app to get access to insights for the Instagram account linked to a Facebook Page" — Allowed usage: "Get data insights of an Instagram Business account", "Get story insights of an Instagram Business account" |

Page-feed read requirements [S6][S7]: "A Page access token" from a person who can perform CREATE_CONTENT, MANAGE or MODERATE on the Page, with `pages_read_engagement` and `pages_read_user_content`. Page insights [S11]: "A Page access token requested by a person who can perform the ANALYZE task on the Page" plus `read_insights, pages_read_engagement`; Features: "Not applicable".

The **Page Public Content Access** feature [S14] is only for Pages the app does NOT manage: it grants "access to the Pages Search API and to read public data for Pages for which you lack the pages_read_engagement permission and the pages_read_user_content permission." Its warning "Once you set your app to live mode, it will not be able to see any Page public content without this feature" concerns other Pages' public content; it is not a constraint on reading a Page whose admin granted the permissions above.

Answer to A(1): yes — Page feed/posts, post-level engagement, Page insights and Instagram Business insights are all readable in Development mode at Standard Access for a Page whose admin is a role user.

### A2. Development-mode rate limits

Searched [S3] for "development"/"dev mode"/"live mode". The only development-tier language is on the Marketing API: Ads Insights and Ads Management "By default, an new app should be on the development tier" and the header field `"ads_api_access_tier": "development_access"`. **There is no Development-mode tier for Pages or Instagram BUC limits.** The Pages BUC formula applies regardless of mode:

> "Calls within 24 hours = 4800 * Number of Engaged Users" (Page or system-user token) — "The Number of Engaged Users is the number of Users who engaged with the Page per 24 hours."
> User/app tokens: "Calls within one hour = 200 * Number of Users".

Instagram Platform BUC: "Calls within 24 hours = 4800 * Number of Impressions" [S3]. Practical consequence: with a Page token, a low-engagement Page still gets thousands of calls/day; a 1,600-post backfill at 100 posts/page plus per-post insights is a few thousand calls, achievable in one or two days with modest pacing.

### A3. Staying in Development mode indefinitely — compliance

- Business Verification doc [S4] explicitly exempts role-only apps (quote in A1).
- App Modes [S1] says apps "should not be switched to Live mode until app development is complete" — it imposes no deadline.
- Platform Terms [S21]: searched for "Development mode", "testing", "live mode" — **no clause found**. Section 12.a defines App as "any technical integration with Platform or to which we have assigned an App identification number." The retention rule that does apply is 3.d.i.2: delete Platform Data "when retaining the Platform Data is no longer necessary for a legitimate business purpose that is consistent with these Terms" — a knowledge base of the Page's own content is a legitimate business purpose, but the obligation still exists.
- Developer Policies [S22]: no clause on Development mode or a requirement to go Live; the only "testing" mention is 2.3 ("Your App shouldn't crash or freeze during the testing process").
- Data Use Checkup applies to apps "that have Advanced Access" [S2]; a Standard-Access-only app is outside that annual requirement.

Conclusion: an internal-only app used solely by role users can remain in Development mode with Standard Access indefinitely; no primary document says otherwise. (Confidence: high on "no documented prohibition"; Meta can still change policy.)

### A4. Page feed history and backfill depth

Edges: `/feed` returns "any interactions with a Facebook Page including: posts and links published by this Page, visitors to this Page, and public posts in which the Page has been tagged" and "Published and unpublished posts will be returned" (filter with `is_published`) [S6]. `/posts` is "The posts of a Facebook Page." [S7]. `/published_posts` returns "A list of PagePost nodes" [S8]. Pagination is cursor-based (`paging.cursors.before/after`, `paging.next`) with `since`/`until`/`limit` [S6].

Documented caps (identical text on [S6][S7][S8]):
> "The API will return approximately 600 ranked, published posts per year"
> "You can only read a maximum of 100 feed posts with the `limit` field"
> "If a Post has expired, you will no longer be able to view the content using the Graph API."
> "Video Posts - To get a list of video posts, the person making the request must be an admin of the Page"
> "This endpoint does not return Reels." [S9] — and the `/video_reels` edge is write-only ("You can't perform this operation on this endpoint" for GET) [fetched page/video_reels]; `/videos` is likewise write-only in the current reference.

There is no documented "last N years" cutoff; the cap is per-year volume (~600 ranked posts/year), which does not bite a Page with ~1,600 posts spread over many years unless a single year exceeded ~600 posts. Reels published to the Page are not enumerable through these edges.

Post-level engagement fields on each PagePost [S9]: `message`, `story`, `created_time`, `full_picture`, `attachments`, `permalink_url`, `shares` (count), `is_published`, `status_type`; edges `comments`, `reactions`, `likes`, `insights`, `sharedposts`. `comments` supports `filter=stream|toplevel`, `order=chronological|reverse_chronological` and `summary=true` → `total_count` [S10]. Post insights [S12] include `post_impressions*` (many `_unique` variants "Deprecated above Graph API v25"), `post_clicks`, `post_clicks_by_type`, `post_reactions_by_type_total`, per-reaction totals (`post_reactions_like_total` … `post_reactions_anger_total`), `post_activity_by_action_type`, `post_media_view`, `post_total_media_view_unique`, and `post_video_*` — but "Only the last two years of insights data is available" [S12]. Reactions/comments/shares counts as **fields** carry no such window in the reference; only the **insights** edge does.

### A5. Page token longevity

> "Long-lived Page access token do not have an expiration date and only expire or are invalidated under certain conditions." [S15]

Obtain via a long-lived User token (about 60 days) held by someone with a Page role, then `GET /{app-scoped-user-id}/accounts` [S15]. Invalidation conditions [S16]: user logged out (code 190 / subcode 460), password change, app de-authorized (subcode 458), and "due to security related events, access tokens may be invalidated before the expected expiration time"; "Facebook will not notify you that an access token has become invalid."

### A6. Instagram insights and retention

IG User `/media` [S19]: returns "all IG Media on an IG User", supports `since`/`until` time-based pagination, "returns a maximum of 10K of the most recently created media"; stories excluded (use `/stories`). Permissions: `instagram_basic` + `pages_read_engagement` or `pages_show_list`.

IG Media `/insights` [S17] metrics: "comments, crossposted_views, facebook_views, follows, ig_reels_avg_watch_time, ig_reels_video_view_total_time, impressions, likes, link_clicks, navigation, profile_activity, profile_visits, reach, reels_skip_rate, replies, reposts, saved, shares, total_interactions, views". Limits: "Metrics data is stored for up to 2 years."; "Story media metrics are only available for 24 hours."; "Data used to calculate metrics can be delayed up to 48 hours."; "Insights data is not available for any media within an Instagram Media album."; "comments, likes, views, and total_interactions report organic interaction metrics only". Permissions (Facebook Login path): `instagram_basic, instagram_manage_insights, pages_read_engagement`.

IG User `/insights` [S18] metrics: "accounts_engaged, comments, engaged_audience_demographics, follows_and_unfollows, follower_demographics, likes, profile_links_taps, reach, replies, reposts, saves, shares, total_interactions, views"; `impressions` deprecated as of v22.0. `since`/`until` are UNIX timestamps; "If you do not include these parameters, the API will look back 24 hours." `metric_type=total_value` allows breakdowns. Follower-count metrics unavailable under 100 followers; demographics capped at top 45 values. The Insights guide adds: "User Metrics data is stored for up to 90 days" and "This API returns only data for media owned by Instagram professional accounts" [S20]. Neither reference states a "media created before conversion" exclusion; that is undocumented in the current pages (treat older-media insights as best-effort).

### A7. What Postiz actually requests for Facebook and Instagram

Read directly from the provider source [P1][P2]:

| Postiz method | Exact Graph call | Metrics returned |
|---|---|---|
| Facebook `analytics()` | `/{page}/insights?metric=page_total_media_view_unique,page_media_view,page_post_engagements,page_daily_follows&period=day&since&until` | 4 page-level series over 7/30/90 days |
| Facebook `postAnalytics()` | `/{post}/insights?metric=post_total_media_view_unique,post_reactions_by_type_total,post_clicks,post_clicks_by_type` | 4 snapshot numbers dated "today"; reactions are summed across types; the `date` argument is ignored |
| Instagram `analytics()` | `/{ig-user}/insights?metric=follower_count,reach&period=day` and `…?metric_type=total_value&metric=likes,views,comments,shares,saves,replies&period=day` | 2 daily series + 6 period totals |
| Instagram `postAnalytics()` | `/{media}/insights?metric=views,reach,saved,likes,comments,shares` | 6 snapshot numbers dated "today" |

Scopes Postiz requests: Facebook `pages_show_list, business_management, pages_manage_posts, pages_manage_engagement, pages_read_engagement, read_insights`; Instagram `instagram_basic, pages_show_list, pages_read_engagement, business_management, instagram_content_publish, instagram_manage_comments, instagram_manage_insights` [P1][P2]. Postiz never requests `pages_read_user_content`, so a Postiz-issued token cannot read user comments on the Page at all.

Not requested by Postiz but available directly: post `message`/`attachments`/`permalink_url`, `comments` (text, authors, replies), per-reaction-type totals kept separately, `shares.count`, `post_impressions*`, `post_activity_by_action_type`, `post_video_*`; Page demographics (`page_fans_country/city/locale`), `page_views_total`, `page_fans`; IG `follower_demographics`, `engaged_audience_demographics`, `profile_links_taps`, `total_interactions`, Reels watch-time metrics, story insights, and the media list itself with captions/timestamps. Postiz's Facebook/Instagram analytics are therefore a small subset of the direct Graph API surface.

## B. YouTube

### B1. Unverified consent screen, no compliance audit — effect on reads

- Compliance audit [S24]: "If you would like to request additional quota beyond the default allocation, you must first complete an audit to show that your project is in compliance with the YouTube API Services Terms of Service." Nothing in the audit page restricts any read call.
- The only documented functional restriction for unaudited projects is on uploads [S25]: "All videos uploaded via the `videos.insert` endpoint from unverified API projects created after 28 July 2020 will be restricted to private viewing mode." Reads are not mentioned.
- Unverified OAuth consent screen [S34]: the app "might display an 'unverified app' screen before it displays the consent screen"; the cap is "100 new users in total, after the app presents the unverified app screen". Exemptions listed: "Apps in development", "OAuth-based plugins", "Internal apps". The sensitive-scope page [S35] adds that verification is not needed "if you are the only user of your app or if your app is used by only a few users, all of whom are known personally to you" — which describes a nonprofit reading its own channel.
- Refresh tokens [S36]: 7-day expiry applies only to projects "with an OAuth consent screen configured for an external user type and a publishing status of 'Testing'". The project here is "In production", so refresh tokens do not carry that 7-day limit. Also: "There is currently a limit of 100 refresh tokens per Google Account per OAuth 2.0 client ID."

Result: `videos.list` (part=statistics), `channels.list`, `commentThreads.list`, and YouTube Analytics `reports.query` on the owned channel are unrestricted by verification/audit status.

### B2. Quota

> "Projects that enable the YouTube Data API have a default quota allocation of 100 `search.list` calls, 100 `videos.insert` calls, and 10,000 units per day combined for all other endpoints." "A read operation that retrieves a list of resources -- channels, videos, playlists -- usually costs 1 unit." [S23]

`commentThreads.list` costs 1 unit, `maxResults` 1–100, supports `videoId` or `allThreadsRelatedToChannelId` [S28]. A full channel backfill (uploads playlist → `videos.list` in batches of 50 → comments) fits comfortably inside 10,000 units/day.

### B3. Direct Analytics API vs Postiz

Postiz `analytics()` [P3]: `reports.query({ids:'channel==MINE', metrics:'views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,subscribersLost', dimensions:'day'})` and then **drops `views`** from the returned cards (only 6 labels are pushed). `postAnalytics()`: `videos.list(part=statistics,snippet)` → `viewCount, likeCount, commentCount, favoriteCount` (Google: favoriteCount "is now always set to 0"; dislikeCount is owner-only since 2021-12-13 [S26]). Postiz requests scopes `youtube, youtube.force-ssl, youtube.readonly, youtube.upload, youtubepartner, yt-analytics.readonly` [P3].

Direct Analytics API [S29][S30][S31][S32]:
- Metrics: view (`views, engagedViews, playlistViews, redViews, viewerPercentage`), watch time (`estimatedMinutesWatched, estimatedRedMinutesWatched, averageViewDuration, averageViewPercentage`), engagement (`comments, likes, dislikes, shares, subscribersGained, subscribersLost, videosAddedToPlaylists, videosRemovedFromPlaylists`), playlist, card, annotation, livestream (`averageConcurrentViewers, peakConcurrentViewers`), audience retention (`audienceWatchRatio, relativeRetentionPerformance, startedWatching, stoppedWatching`), revenue (needs monetary scope).
- Dimensions: `video, playlist, day, month, country, province, city, dma, insightTrafficSourceType/Detail, insightPlaybackLocationType/Detail, deviceType, operatingSystem, ageGroup, gender, sharingService, subscribedStatus, youtubeProduct, liveOrOnDemand, creatorContentType, elapsedVideoTimeRatio, livestreamPosition`.
- `reports.query` takes `ids=channel==MINE`, `startDate/endDate`, `filters` (up to 500 video IDs), `maxResults`, `sort`; scope `yt-analytics.readonly` [S32]. Channel reports note "Before January 1, 2013 data is only available for the top 10 videos" [S31] — i.e. history otherwise extends back through the channel's life; no shorter cutoff is documented.
- Bulk Reporting API [S33] is a complement, not a backfill: reports are "available for 60 days from the time that they are generated" and a new job only back-fills "the 30-day period prior to the time that you created the job".

Postiz thus returns 6 channel series + 4 (effectively 3 useful) per-video counters; the direct API exposes dozens of metrics across ~25 dimensions with full history.

## C. TikTok

### C1. Display API fields for the authorized account

- Scopes [S44]: `user.info.basic` "Read a user's profile info (open id, avatar, display name ...)"; `user.info.profile` "Read access to profile_web_link, profile_deep_link, bio_description, is_verified."; `user.info.stats` "Read access to a user's statistical data, such as likes count, follower count, following count, and video count"; `video.list` "Read a user's public videos on TikTok".
- `/v2/user/info/` [S43]: fields `open_id, union_id, avatar_url…, display_name, bio_description, profile_deep_link, is_verified, username, follower_count, following_count, likes_count, video_count`.
- `/v2/video/list/` [S40]: "can return a paginated list for the given user's **public** TikTok video posts"; `max_count` "Default is 10. Maximum is 20."; cursor pagination via `has_more`/`cursor`.
- `/v2/video/query/` [S41]: "Up to 20 video IDs can be included per request."; fields `id, create_time, cover_image_url, share_url, video_description, duration, height, width, title, embed_html, embed_link, like_count, comment_count, share_count, view_count, is_aigc`.
- Video object [S42]: `like_count` "Number of likes for the video", `comment_count`, `share_count`, `view_count` (int64), `create_time` "UTC Unix epoch (in seconds) of when the TikTok video was posted", `video_description` max 150.

No history cap beyond pagination is documented for `video.list`; the overview describes it as "the metadata of a TikTok user's recently uploaded videos" [S38], so treat full-archive paging as unverified until tested. Private videos are excluded by definition of the scope. No per-video comment text endpoint exists in the Display API (comments are count-only).

### C2. Sandbox vs unaudited Production

- Sandbox [S45][S46]: "Sandbox mode is a restricted environment that allows you to try out integrations without having to submit your app for review."; "You can add up to 10 accounts."; "To add a TikTok account that you own as a target user, you must provide its login credentials."; "After you add target users, you may authorize them if you want to use Login Kit and the other products dependent on it."; the only exclusions are "Content Posting API for public videos or Data Portability API". Display API reads for target users are therefore available in Sandbox (inference from the exclusion list; the docs do not enumerate included products explicitly).
- Unaudited Production [S47]: "you will not have access to the APIs until your application has been approved." and "Once your application has been reviewed by our team and approved, your app status will show as Live and your app will have access to the products and scopes requested in the application." Production statuses: Draft, In review, Live, Not approved [S46]. Review requires a Sandbox demo for first-time apps [S48].

So for a Sandbox app with the Gita Valley account as a target user, `user.info.stats` and `video.list/query` reads work today; an unaudited Production app returns nothing.

### C3. Research API eligibility

[S49]: applicants must be "Academic institutions in the U.S., EEA, UK, Canada, or Switzerland; or" a "Not-for-profit and/or independent research institution, organization, association, or body in the EU", or Brazil youth-safety organizations, with an ethics review and non-commercial purpose. A U.S. religious nonprofit is not in scope; and the Research API covers public data generally, not the applicant's own private analytics.

### C4. Postiz TikTok analytics

`analytics()` [P4]: `user/info?fields=follower_count,following_count,likes_count,video_count`, then `video/list` with `max_count: 20` (one page only) and `video/query?fields=id,like_count,comment_count,share_count,view_count` — returning four account counters plus **sums over the 20 most recent videos** ("Views", "Recent Likes", "Recent Comments", "Recent Shares"), all snapshot-dated "today". `postAnalytics()`: `video/query` for one video → `view_count, like_count, comment_count, share_count`. Scopes requested: `video.list, user.info.basic, video.publish, video.upload, user.info.profile, user.info.stats`. Postiz never pages past the first 20 videos and never stores titles/descriptions/create_time.

## D. Verdict and data-access matrix

### How Postiz serves analytics (both hostings)

- Public API routes: `GET /public/v1/analytics/:integration?date=` and `GET /public/v1/analytics/post/:postId?date=` [P5] — they call the provider `analytics()` / `postAnalytics()` methods quoted above; nothing else.
- Caching: `checkAnalytics` reads `integration:{org}:{integration}:{date}` from Redis and, in production, stores the platform response for 3600 s [P6]. No metrics are persisted to PostgreSQL — there is no analytics model in the schema [P7].
- Rate limit: the throttler guard only counts `POST` to `/public/v1/posts` (`limit: API_LIMIT ?? 90` per hour) [P8]; analytics GETs are not throttled by Postiz (the "30 requests per hour" text in the OpenAPI description [P9] is stale relative to the code and, per the overview, applies to create-post only). Platform rate limits still apply underneath.
- DB contents [P7]: `Integration` holds `token` (plain), `refreshToken`, `tokenExpiration`, `internalId` (platform account id), `providerIdentifier`; `Post` holds only Postiz-authored posts (`content`, `publishDate`, `releaseId`, `releaseURL`, `state`, `error`, …). Historical platform posts and any metric history are absent.
- Postiz docs confirm the surface: Facebook "Page impressions, post engagement, followers, media views"; Instagram "Followers, reach, likes, views, comments, shares, saves, replies"; TikTok "Followers, following, total likes, video count"; YouTube "Estimated minutes watched, average view duration and percentage, subscribers gained and lost, likes"; ranges 7/30/90 days (FB, YT) or 7/30 (IG, TikTok); "Most platforms only return data from the point the connection was authorised." [P9]

### Does self-hosting Postiz give MORE read access than Postiz Cloud + own apps direct?

No. Precisely:

1. Every metric Postiz returns is fetched live from the same platform endpoints the nonprofit's own app can call, with a shorter metric list, snapshot-only post numbers, and no history table. Self-hosting changes which OAuth app issues the token (the nonprofit's own app) but not the Postiz code path, so the self-hosted analytics API is the same subset as Cloud's.
2. Read access is a property of the **token**, and the token is a property of the **app + role user**. With the nonprofit's own Meta app in Development mode, the Page admin (role user) grants Standard-Access permissions [S2][S4]; a long-lived Page token then has no expiry [S15]. That token is equally usable from a script, from self-hosted Postiz, or both. Postiz Cloud, by contrast, uses Postiz's own apps, so the nonprofit never holds those tokens and cannot make direct Graph calls with them.
3. The one thing self-hosted Postiz adds over Cloud is the `Integration.token` row in a database the nonprofit controls [P7] — a convenient token store for the same own-app token, not additional permissions. Note that the Postiz Facebook scope list omits `pages_read_user_content`, so a token minted through Postiz's Facebook connect flow cannot read user comments; a token minted through the nonprofit's own consent flow with that scope can.
4. Backfill depth is set by the platforms, not by Postiz: FB ~600 ranked posts/year and 2-year insights window; IG 10K media and 2-year media insights; YouTube Analytics back to channel start (top-10 only before 2013); TikTok public videos via 20-per-page cursor. Postiz reads none of that history (7–90 day windows; first 20 TikTok videos).

Recommendation for the knowledge database: run the ingestion against the platforms directly with the nonprofit's own app tokens (Meta Dev-mode app + role-user Page token; Google unverified project; TikTok Sandbox target user), store results in `data/gvsa.db`, and treat Postiz purely as the scheduler/publisher. Keep the apps in Development/Sandbox/unverified state — no primary source requires otherwise for internal, role-user-only use.

### Data-access matrix

| Data | Own app direct (Dev / unverified / Sandbox) | Postiz Cloud analytics API | Self-hosted Postiz analytics API | Self-hosted Postiz DB |
|---|---|---|---|---|
| Facebook posts + engagement | Full: `/feed`/`/posts` (message, attachments, permalink, `shares.count`, `reactions.summary`, comment text via `pages_read_user_content`), post insights (2-yr window); ~600 ranked posts/yr, 100/page [S6][S9][S12] | 4 snapshot numbers per Postiz-published post (`post_total_media_view_unique`, summed reactions, clicks, clicks-by-type) [P1] | Same 4 numbers, same code [P1] | Postiz-authored `Post` rows only (content, publishDate, releaseId); no platform posts, no metrics [P7] |
| Page insights | All `page_*` metrics incl. demographics, `period=day/week/days_28/month/lifetime`, 90 days per query, 2-yr history, Page ≥100 likes [S11][S12] | 4 daily series (`page_total_media_view_unique, page_media_view, page_post_engagements, page_daily_follows`) over 7/30/90 d, Redis-cached 1 h [P1][P6] | Same 4 series [P1] | Not stored [P7] |
| Instagram media insights | Media list (10K cap) + per-media `views, reach, saved, likes, comments, shares, total_interactions, profile_visits, follows, ig_reels_*` etc., 2-yr retention; account metrics incl. `follower_demographics` [S17][S18][S19] | Per-post `views, reach, saved, likes, comments, shares` snapshot; account `follower_count, reach` daily + 6 period totals over 7/30 d [P2] | Same [P2] | Not stored [P7] |
| YouTube analytics | Full Analytics API (all metrics × dimensions, `channel==MINE`, history to channel start), `videos.list` statistics, `channels.list`, comment threads; 10,000 units/day; no audit/verification gate on reads [S23][S24][S29][S30][S32] | 6 daily series (`estimatedMinutesWatched, averageViewDuration, averageViewPercentage, subscribersGained, subscribersLost, likes`) over 7/30/90 d; per-video `viewCount, likeCount, commentCount, favoriteCount` [P3] | Same [P3] | Not stored [P7] |
| TikTok stats | `user.info.stats` counts + per-video `view/like/comment/share_count`, `title`, `video_description`, `create_time`, `share_url` for public videos; Sandbox works for ≤10 target accounts; unaudited Production returns nothing until approved [S40]–[S47] | 4 account counters + sums over 20 most-recent videos; per-video 4 counts; 7/30 d labels only [P4] | Same [P4] | Not stored [P7] |
| Historical backfill depth | Platform-defined: FB ~600 ranked posts/yr + 2-yr insights; IG 10K media + 2-yr media insights + 90-d account metrics; YT full history (top-10 pre-2013); TikTok cursor over public videos [S6][S12][S17][S19][S20][S31][S40] | None: 7/30/90-day windows, "data from the point the connection was authorised" [P9] | None (same code) | None — no metrics tables [P7] |
| Raw DB access | N/A — you design the store (`data/gvsa.db`) | No | No (API only) | Yes: PostgreSQL with `Integration`, `Post`, `Media`, … [P7] |
| Token ownership | Yes: minted by your app to your role user; long-lived Page token "do not have an expiration date" [S15]; Google refresh token not 7-day-limited in "In production" [S36] | No: tokens belong to Postiz's apps in Postiz's DB | Yes: your app's tokens, but Postiz-chosen scopes (no `pages_read_user_content`) [P1] | Yes: `Integration.token` / `refreshToken` in plaintext rows [P7] |

## Open items

1. **Facebook Reels history**: `/feed`, `/posts` exclude Reels and `/video_reels` + `/videos` are write-only in the current reference. Confirm empirically whether Reels appear under `/posts` with `attachments` or need the Reels Publishing API `GET /{page}/video_reels` (older docs allowed reads). [S9]
2. **Pre-conversion Instagram media**: current references do not state whether insights exist for media created before the account became a Business account; test on the oldest IG media.
3. **TikTok `video.list` depth**: docs say "recently uploaded videos" [S38] but document only cursor pagination; verify the cursor walks the full public archive in Sandbox.
4. **Facebook "~600 ranked posts per year"**: check per-year post counts of Page 293313989490 against this cap; if any year exceeds ~600, expect gaps and use `since`/`until` windows to probe.
5. **YouTube scope sensitivity**: Google's docs cite "deleting a YouTube video" as a sensitive-scope example [S35] but do not publish a per-scope table; the Cloud Console flags them at request time. Does not affect read capability, only the unverified-screen UX.
6. **Postiz rate-limit text**: OpenAPI blurb says 30 req/h while the overview and code say 90 (`API_LIMIT`) on create-post only [P8][P9]; treat 90/h create-post as current and confirm on the sethpc.xyz instance.
7. **Meta retention duty**: Platform Terms 3.d.i.2 requires deleting Platform Data when no longer necessary for a legitimate business purpose [S21]; document the knowledge base's purpose and retention policy so the Dev-mode app remains defensible.
