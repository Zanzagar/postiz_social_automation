# Platform OAuth + App Review Requirements for the Postiz Domain Move — Research

Date: 2026-09-07
Sources: developers.facebook.com, developers.google.com, support.google.com, developers.tiktok.com, github.com/gitroomhq/postiz-app (`main` @ cae2565, 2026-08-15), docs.postiz.com. Full list with fetch dates in the Sources section at the end. All pages fetched 2026-09-07 unless noted.

## Question

Postiz is moving from `postiz.sethpc.xyz` (volunteer's server) to a permanent domain, most likely a subdomain of `gitavalley.org` (owned by the temple). Three platform reviews are pending (Meta App Review, Google OAuth verification + YouTube API compliance audit, TikTok production app review). What is bound to the domain, what must be redone if the domain changes after a review, and what can be done now?

## Verdict (TL;DR)

**Migrate the domain first, then submit all three reviews.** Every platform ties at least one reviewed artefact (URL fields, demo video, reviewer access instructions, verified URL property / authorized domain) to the Postiz hostname, and two of the three (Google brand verification, TikTok) explicitly say a redirect-URI/URL change after approval goes back through review. Meta approves permissions, not domains, but reserves the right to re-review on settings changes and needs a reachable URL to test. None of the three platforms invalidate already-issued channel tokens when the redirect URI changes.

| Platform | What the review binds to the domain | Changing the domain after approval | Existing channel tokens survive a redirect-URI change? |
|----------|-------------------------------------|-------------------------------------|--------------------------------------------------------|
| Meta | Reviewer access URL/instructions, screencasts, App Domains / Website platform, Valid OAuth Redirect URIs | Approval is per permission, not per URL. But "Making changes to your app's basic or advanced settings after you have submitted may require re-review" [M-SG]. No doc enumerates which changes. | Yes — long-lived/Page token exchange uses `fb_exchange_token` with no `redirect_uri` [M-LL] |
| Google / YouTube | Authorized domains (must be Search-Console-verified, top private domain you own), redirect URI, home page + privacy policy on the same verified domain, demo video, audit-form "Primary Access URL" + screenshots | Changing "redirect URI ... displayed on your OAuth consent screen" requires **brand verification again** (no unverified-screen/100-user-cap penalty while pending) [G-CHG]. Audit form is per project; no official statement on re-audit after a URL change (unverified). | Yes — refresh request is `client_id, client_secret, grant_type=refresh_token, refresh_token`; no `redirect_uri` [G-WS] |
| TikTok | Terms URL, Privacy URL, Web URL must be *verified URL properties*; redirect URI registered; demo video domain must match the Website URL | **Yes, re-review.** "Once your app is approved and live, any subsequent changes must be submitted for review and approved to appear in the live release" [T-APP] | Yes — refresh request has no `redirect_uri` [T-TOK] |

## What Postiz actually requests (source of truth)

Verified against `gitroomhq/postiz-app` `main` on 2026-09-07 (raw files; provider dir last touched 2026-08-15). Every callback is `${FRONTEND_URL}/integrations/social/<identifier>`; docs.postiz.com confirms `FRONTEND_URL` is "Used as the OAuth redirect base" [P-CFG]. **The domain move is therefore a `FRONTEND_URL` change plus re-registering four redirect URIs.**

| Provider (identifier) | Auth endpoint | Scopes (verbatim from source) | Callback path |
|---|---|---|---|
| `facebook` ("Facebook Page") | `https://www.facebook.com/v25.0/dialog/oauth` | `pages_show_list, business_management, pages_manage_posts, pages_manage_engagement, pages_read_engagement, read_insights` | `/integrations/social/facebook` |
| `instagram` ("Instagram (Facebook Business)") | `https://www.facebook.com/v25.0/dialog/oauth` (**Facebook Login**) | `instagram_basic, pages_show_list, pages_read_engagement, business_management, instagram_content_publish, instagram_manage_comments, instagram_manage_insights` | `/integrations/social/instagram` |
| `instagram-standalone` ("Instagram (Standalone)") | `https://www.instagram.com/oauth/authorize` (**Instagram Login**, `enable_fb_login=0`) | `instagram_business_basic, instagram_business_content_publish, instagram_business_manage_comments, instagram_business_manage_insights` | `/integrations/social/instagram-standalone` |
| `youtube` | Google OAuth2 client, `access_type: 'offline'`, `prompt: 'consent'` | `userinfo.profile, userinfo.email, youtube, youtube.force-ssl, youtube.readonly, youtube.upload, youtubepartner, yt-analytics.readonly` (all `https://www.googleapis.com/auth/...`) | `/integrations/social/youtube` |
| `tiktok` | `https://www.tiktok.com/v2/auth/authorize/` | `video.list, user.info.basic, video.publish, video.upload, user.info.profile, user.info.stats` | `/integrations/social/tiktok` |

Notes from source:
- Both Meta providers use plain Facebook Login (`/dialog/oauth` with a `scope` parameter), not a Facebook-Login-for-Business `config_id`. Meta says Login for Business is "the preferred ... solution for tech providers" and "If you are not a Tech Provider ... Facebook Login is recommended" [M-FLB] — the existing Facebook Login product is the right one.
- `checkScopes()` in `social.integrations.interface.ts` throws `NotEnoughScopes` unless **every** requested scope was granted. So every scope above must be approved/granted for the connect to succeed.
- Postiz's TikTok `post()` sends `privacy_level: settings.privacy_level || 'PUBLIC_TO_EVERYONE'` for direct posts; unaudited clients must send `SELF_ONLY` (see TikTok §3a) — the Postiz UI privacy selector must be used until audited.
- docs.postiz.com's TikTok page lists a `video.create` scope that does not exist in the provider; ignore it, the source is authoritative.

---

## 1. Meta (Facebook Pages + Instagram via Facebook Login)

### 1a. Where the domain-bound settings live, and re-review

| Setting | Location (per Meta docs) | Doc statement |
|---|---|---|
| Valid OAuth Redirect URIs | Products > Facebook Login > Settings [M-SEC] | Strict Mode "requir[es] an exact match from your Valid OAuth redirect URIs list"; "The full URI must be an exact match, including all parameters, with the exception of the optional state parameter" [M-SEC] |
| App Domains | Settings > Basic [M-SEC][M-BAS] | "use this to lock down the domains and subdomains which can be used to perform Facebook Login on behalf of your app" [M-SEC]; "Domains and subdomains of your app for app installation and are used during Graph API request for verification" [M-BAS] |
| Website platform / Site URL | Settings > Basic > platforms | App Review content page: "You will also need to provide the platforms that your app will be available on (website, iOs store, etc.)" [M-CON]. Reviewer-instructions dialog is per platform: "A popup dialog appears for each platform on which you app is available" [M-PAGES] |
| Privacy Policy URL, Terms URL, Icon, Category | Settings > Basic | Each "required to switch your app to Live mode" [M-BAS] |

**Does App Review approve domains?** No. "Permissions that have been approved through App Review can be requested from any app user, but unapproved permissions can only be requested from app users who have a role on the requesting app" and "approved features are active for all app users" [M-AR]. Nothing in the App Review, Access Levels, or Basic Settings docs binds approval to App Domains, Site URL, or redirect URIs.

**But** the Submission Guide's pre-submission checklist says: "Making changes to your app's basic or advanced settings after you have submitted may require re-review." [M-SG] Meta does not list which settings. Verdict: changing App Domains / Site URL / redirect URIs after approval will not revoke permissions, but Meta reserves the right to re-review, and the reviewer-facing artefacts (screencast URL, access instructions) would be stale. The App Review FAQs page (`.../app-review/AR-FAQs`) is JavaScript-rendered and returned only navigation chrome on fetch — any FAQ statement on this is **unverified**.

Old-doc statement (search snippet only, page now redirects to the hub — unverified): "If you need to add new permissions to a live app, you should repeat the Development Mode testing and App Review steps whenever you add new permissions, features, or products."

### 1b. Does the domain in the screencast matter?

Meta does not require a particular domain, but reviewers must reach the app at the URL you give and use the recordings as a test script:

- "Make sure we can access your app or website. Your app must be publicly available or you must provide instructions on how to access it." [M-SG]
- "We will use your recordings as guides when testing your app to verify that it actually uses all of the permissions and features you are requesting." [M-SG]
- "Any requested permission or feature missing a screen recording will not be approved"; one recording per permission/feature; "Use English as the app UI language"; "Omit audio; our reviewers will not listen to it"; resolution "1080 or better"; monitor width "1440 or less"; "Increase your mouse's cursor size"; "use your mouse to interact with your app instead of your keyboard" [M-SG]
- Instagram page adds: "If needed, provide any required test credentials for Meta reviewers to log into your app or website." [M-IGAR]

Verdict: the screencast domain is not itself a criterion, but recordings and access instructions that point at `postiz.sethpc.xyz` become useless the moment that host is retired. Record on the final domain.

### 1c. Current App Review requirements checklist

| Item | Requirement (verbatim where possible) | Source |
|---|---|---|
| App icon | "Upload a 1024x1024 compliant app icon image to Settings > Basic > App Icon." General asset rule: "less than 5 MB, between 512 x 512 and 1024 x 1024 pixels, and in JPEG, GIF or PNG format." Must not use Meta logos/trademarks or include "Facebook"/"FB". **No "transparent PNG" requirement exists in the primary docs**; the only transparency statement is on the Instant Games App Center page: "Make sure to upload a square image without transparent background as App icon (1024 x 1024)." | [M-SG][M-PAGES][M-BAS][M-APPC] |
| Privacy Policy URL | "the URL that we present to app users in any of Meta's authentication solution interfaces"; required for Live mode | [M-SG][M-BAS] |
| Terms of Service URL | required for Live mode | [M-BAS] |
| Category | "select a category that accurately describes your app"; required for Live mode | [M-SG][M-BAS] |
| App Purpose ("Business Use") | "Set this to Yourself or your own business if your app is only available to people who have a role on your app, or a role in a Business that has claimed your app. Otherwise set it to Clients." | [M-SG] |
| App Verification section | "If app users can sign into your app using any of Meta's authentication solutions, set the radio button to Yes." (Postiz users do sign in with Facebook Login to connect channels.) | [M-SG] |
| Data Protection Officer contact | required if doing business in the EU | [M-PAGES] |
| Data deletion URL | "A data deletion URL with instructions or a callback" listed under "Required app assets" to publish | [M-PAGES] |
| Successful API calls | "Make at least 1 successful API call using each permission for which you are requesting advanced access. Calls must be made within 30 days of submitting for App Review and can be made using your app or the Graph API Explorer tool." | [M-SG] |
| Per-permission text | "Each permission and feature must have its own description. Do not copy and paste." | [M-SG] |
| Business Verification | "Advanced Access now requires Business Verification" (effective 2023-02-01). Exception: "If your app will only be used by app users who have a role on the app itself you do not need to complete verification." Start at Settings > Basic > Verification; "you may be prompted to complete business verification if you have not done so already" during submission. | [M-BV][M-SG] |
| Data Use Checkup | "an annual assessment"; "Developers do not need to complete DUC while the app is in Development mode, but will need to complete DUC before the app can be switched to Live mode." | [M-DUC] |
| Access Verification / Tech Provider | "Access verification is the process we use to determine if a business operates as a Tech Provider" (a business accessing "business data owned by other businesses"). "Access verification is independent of App Review and permission access levels." Only applies to apps used by other businesses; **not applicable** to an app used only by the temple's own portfolio. | [M-AV][M-TP] |
| Review time | "you should receive a decision within a week." | [M-SG] |
| Live mode | "You should only switch it to Live mode after you have completed app development and have completed App Review." "Apps in Live mode can only request approved permissions from app users ... This restriction applies to everyone, even users who have a role on the app itself" | [M-MODES][M-SG] |

**Which permissions need Business Verification for Advanced Access?** Permissions reference: "Business Verification is required for all apps making requests for Advanced Access" [M-PERM]. Per-permission, all ten requested (`pages_show_list, business_management, pages_manage_posts, pages_manage_engagement, pages_read_engagement, read_insights, instagram_basic, instagram_content_publish, instagram_manage_comments, instagram_manage_insights`) require App Review for Advanced Access and therefore BV; only `public_profile`/`email` are exempt [M-PERM]. Instagram overview restates: "Your app must complete Meta App Review to be granted Advanced Access" and "You must complete Business Verification if your app requires Advanced Access" [M-IG].

**"1:1 / own business" flow.** For an app used only by the temple: App Purpose = "Yourself or your own business" [M-SG]; no Access Verification [M-AV]; Business Verification of the temple's Business Portfolio is still required for Advanced Access [M-BV][M-PERM]. There is no documented path to publish publicly from a Live app without Advanced Access (see 1d).

### 1d. Does Development-mode posting work for role holders?

**Yes, but the posts are only visible to role users until the app goes Live.**
- "Apps in Development mode can only request permissions from role users" and "Any data generated while an app is in Development mode, such as test posts, can only be seen by role users." [M-MODES]
- "When an app is in development mode, it will have access to all permissions and features, but can only access data for the following roles on the app: Administrator, Developer, Tester and Analytics User." [M-LIVE19]
- "data generated while in Development mode such as test posts will become visible to all app users once you switch [to Live]." [M-SG]

Implication for the planned "Meta E2E dry run": a Dev-mode publish to the Page is a genuine API publish, but per Meta it is not publicly visible until the app is Live (and Live requires App Review for these permissions, else even role users lose them [M-SG]). Whether Instagram media created via a Dev-mode app is likewise hidden is **not stated** in the Instagram content-publishing doc (unverified).

### 1e. Instagram API with Facebook Login vs Instagram Login

| | Instagram API with Facebook Login | Instagram API with Instagram Login |
|---|---|---|
| Meta description | "Your app serves Instagram professional accounts that are linked to a Facebook Page" | "Your app serves Instagram professional accounts with a presence on Instagram only" |
| Requires FB Page link | Yes: "Instagram professional accounts must be connected to a Facebook Page." | No |
| Host / token | `graph.facebook.com`, Facebook User or Page token | `graph.instagram.com`, Instagram User token |
| Permissions | `instagram_basic, instagram_content_publish, instagram_manage_comments, instagram_manage_insights, instagram_manage_messages, pages_show_list, pages_read_engagement` | `instagram_business_basic, instagram_business_content_publish, instagram_business_manage_comments, instagram_business_manage_messages` |
| Postiz provider | `instagram` (7 scopes, incl. `business_management`) — **this is what the current Meta app / Facebook Login product supports** | `instagram-standalone` (4 scopes, needs separate `INSTAGRAM_APP_ID/SECRET` and the "Instagram" product with Instagram Business Login) |

Source: [M-IG], Postiz source. Both paths require App Review + BV for Advanced Access [M-IG]. The Instagram overview also notes an exception "for limited permissions (`instagram_basic`, `instagram_manage_comments`) for private apps unable to be tested during review" [M-IG] — not useful here because `instagram_content_publish` is the one that matters.

---

## 2. Google / YouTube

### 2a. OAuth client: redirect URIs, JavaScript origins, Authorized domains, Search Console

- Redirect URIs are set on the Cloud Console **Clients** page ("Web application" type). Rules: HTTPS (localhost exempt), no raw IPs, public-suffix TLD, no wildcards/fragments/userinfo [G-WS][G-CLI].
- **Propagation:** "It may take 5 minutes to a few hours for changes made to these settings to take effect" [G-CLI].
- **Authorized JavaScript origins:** not needed for Postiz — the `youtube` provider uses a server-side `OAuth2Client` code exchange; no origin is used.
- **Authorized domains:** "All domains used in your project, whether in the branding page or client configuration pages must be pre-registered here." "If you have verified the domain with Google, you can use any Top Private Domain as an Authorized Domain." [G-BRANDSUP] Brand verification: "Verify the ownership of your authorized domains using the Google Search Console"; "A Google Account with owner permissions for a domain must be associated with the API Console project"; you must include "the top private domains that are used in the URIs of the App domain section" [G-BRAND]. Verification requirements page: "An account listed as a project owner or editor on your GCP account must verify ownership of the authorized domain using Google Search Console" [G-REQ].
- So: a `postiz.gitavalley.org` redirect URI means `gitavalley.org` must be an Authorized domain and Search-Console-verified by a project owner/editor. For `postiz.sethpc.xyz`, `sethpc.xyz` would have to be verified by a project owner/editor — i.e. Seth's Google account on the temple's Cloud project — which is exactly the entanglement the migration removes.

### 2b. Brand verification vs sensitive-scope verification vs YouTube API compliance audit

Three distinct processes:

| Process | Owner / where | What it requires | Timeline (official) |
|---|---|---|---|
| **Brand verification** | Cloud Console > Google Auth Platform > Branding | App name/logo, home page, privacy policy, terms, authorized domains verified in Search Console. "Your brand must be verified if you want your application logo and application name to be visible to users on the consent screen." Changes to name/logo/home page/privacy policy/authorized domains "are saved as Draft Branding"; "Compliant verification results are valid for 7 days. If you don't publish within that timeframe, the status will change to Need to re-verify." | "typically takes a few minutes"; manual review "usually takes 2-3 business days" [G-BRAND]; support FAQ says "2-3 Business days" [G-FAQ] |
| **Sensitive-scope verification** | Cloud Console > Verification Center | Scope justification; demo video: "Show the OAuth grant process that users will experience, in English"; "Show that the browser address bar of the OAuth consent screen correctly includes your app's OAuth client ID"; "demonstrate the functionality that's enabled by each sensitive scope"; video must show "the same exact scopes you are requesting"; uploaded to YouTube as Unlisted. Home page: on a verified domain you own, must "accurately represent your app" (not just a login page), link privacy policy; privacy policy "hosted within the same domain as your application's home page". "Apps in development, testing or staging are not applicable for verification" — publish to production first, then "Prepare for Verification". | "typically takes 3-5 business days" [G-SENS]; support FAQ says "10 Business days" [G-FAQ] |
| **YouTube API Services compliance audit** | YouTube (form: "YouTube API Services - Audit and Quota Extension Form") | Separate from Google OAuth verification (neither doc references the other). Required "when you would like to request additional quota beyond the default allocation" [G-QUOTA] **and** to lift the private-upload restriction: "All videos uploaded via the `videos.insert` endpoint from unverified API projects created after 28 July 2020 will be restricted to private viewing mode. To lift this restriction, each API project must undergo an audit to verify compliance with the Terms of Service." [G-INSERT][G-REV] | **No official timeline published** (unverified). Audits valid ~12 months: "If you have completed an API Compliance Audit within the last 12 months but require an additional quota extension..." [G-QUOTA] |

**What the audit form asks for** (field labels as rendered 2026-09-07 [G-FORM]): request type; "Your Full Legal Name", "Your Organization's Legal Name", "Your Organization's Primary Website", legal address, "Category", "Organization Size / Type"; technical + business contacts; "Describe your organization's work as it relates to YouTube", "Who is your target audience?", "How does your API Client monetize or generate revenue?"; "API Client Name", "Does this API Client name contain the word 'YouTube'?", **"Primary Access URL"**, **"Privacy Policy URL"**, "Terms of Service URL (Optional)", **"Is your API Client publicly accessible?"**, **Demo Account Credentials** (Username/Email, Password, Login URL, Special Instructions); per project: "Google Cloud Project Number", use-case categories, "Does this API Client require users to sign in with their Google Account (OAuth 2.0)?", expected usage, endpoint checklist, quota requested (separately for `search.list` and `videos.insert`), "Detailed Justification"; **required evidence: "Privacy Policy Screenshots", "Homepage Screenshot", "Terms of Service Documentation"**; conditional evidence: "OAuth Flow Screenshots", "Upload Interface Screenshots", etc.

**Does the audit require the domain / privacy policy to be on a domain you own?** Not stated anywhere in the YouTube ToS, Developer Policies, or audit docs (unverified/no statement). The Developer Policies require the privacy policy to be "prominently displayed and easily accessible to users at all times", to "reference and link to the Google Privacy Policy", and to disclose what the client accesses/stores [G-POL]. The ToS lets YouTube "monitor, review and inspect your API Client(s) ... at any time" [G-TOS]. Practically, "Primary Access URL", the OAuth-flow/upload screenshots and demo credentials all name the Postiz host, so an audit filed against `postiz.sethpc.xyz` documents an installation that will cease to exist.

Note the Google OAuth-verification requirement that the privacy policy be "hosted within the same domain as your application's home page" [G-SENS]. With home page = `https://gitavalley.org` and privacy policy = `https://gitavalley.org/privacy-policy/` this is already satisfied; `postiz.gitavalley.org` sits under the same top private domain.

### 2c. Consequences of "In production, unverified"

- Publishing status: "Projects configured with a publishing status of In production are available to any user with a Google Account" [G-AUD]. Testing status "limited to up to 100 test users" whose "authorizations ... will expire seven days from the time of consent" [G-AUD].
- Unverified app screen + cap: "unverified apps that are accessing restricted or sensitive scopes have a 100 new-user cap restriction" [G-FAQ]; "100 new users in total, after the app presents the unverified app screen" [G-UNV]. "This cap is removed only after an app has been successfully verified." Personal-use apps with "fewer than 100 users" may continue "without going through verification (users will be allowed to click through 'unverified app' warning screens during sign-in)" [G-NOTNEEDED].
- Are YouTube scopes sensitive? Google gives "deleting a YouTube video" as an example of a sensitive scope [G-SENS]; `youtube.force-ssl` is "See, edit, and permanently delete your YouTube videos, ratings, comments and captions" and `youtube` is "Manage your YouTube account" [G-SCOPES]. Treat all YouTube scopes Postiz requests as sensitive (the exact classification list is shown in the Cloud Console scope picker, not in public docs — unverified beyond the example).
- **Refresh tokens do NOT expire in 7 days once In production.** The 7-day rule is explicitly Testing-only: "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of 'Testing' is issued a refresh token expiring in 7 days, unless the only OAuth scopes requested are a subset of name, email address, and user profile" [G-OAUTH]. Other expiry causes: revoked, unused for six months, password change with Gmail scopes, >100 live refresh tokens per account per client ID [G-OAUTH]. Postiz uses `access_type: 'offline'` + `prompt: 'consent'` so a refresh token is always issued.
- **Scope risk to flag:** Postiz requests `https://www.googleapis.com/auth/youtubepartner` ("View and manage your assets and associated content on YouTube") [G-SCOPES]. That scope belongs to the YouTube Content ID API, which "is intended for use by YouTube content partners and is not accessible to all developers or to all YouTube users" [G-CID]. Verification requires justifying every requested scope and "the same exact scopes" in the demo [G-SENS][G-REQ]; expect a reviewer question on this scope. Postiz's `checkScopes()` requires it to be granted, so it cannot simply be removed from the consent screen without patching the provider.

### 2d. Does changing the redirect URI later break existing channel tokens?

**No.** The authorization-code exchange requires `redirect_uri` ("must exactly match one of the authorized redirect URIs for the OAuth 2.0 client") [G-WS], but the refresh request body is only `client_id`, `client_secret` (optional), `grant_type=refresh_token`, `refresh_token` [G-WS]. Tokens are scoped to the OAuth client ID ("limit of 100 refresh tokens per Google Account per OAuth 2.0 client ID" [G-OAUTH]), not to a redirect URI. So connected YouTube channels keep working after the URI list changes; only *new* connections need the new URI.

Caveat (branding, not tokens): "If you make any modifications to your app's name, logo/icon, redirect URI, homepage link, or privacy policy link displayed on your OAuth consent screen, your app will be required to complete brand verification again ... These changes will not be visible to the users till the app is reverified. These changes do not trigger the unverified app screen or the 100-user cap." [G-CHG]

---

## 3. TikTok (Login Kit + Content Posting API Direct Post + Display API)

### 3a. Production app-review requirements

**App details** [T-ARG]: custom app name (no social-media company names, not a functionality description); "The app icon must be a clear image"; icon spec "1024 x 1024 px", "JPEG, JPG, or PNG", "Up to 5 MB" [T-APP]. Description: "Apps must not be for private or personal use. Apps must not contain adult content. Apps that are still in development or testing will not be approved." (Frame the app as the organisation's publishing tool, not a personal script.)

**Website URL / legal docs** [T-ARG]: "A valid official website that houses information about your web and services. Your website URL cannot be a landing page or login page. You must have an externally facing fully developed website. Your Privacy Policy and Terms of Service links must be visible on the website URL without having to open a menu to view them, and the links must be active." A Postiz login page does **not** qualify as the Website URL; `https://gitavalley.org` (with visible Privacy/Terms links) does.

**URL properties / domain verification** [T-APP]: "Before submitting your app for review, you must verify URL properties for all URLs in your app configuration." "For apps created after September 9, 2024, the following URLs require verification: Terms of Service URL, Privacy Policy URL, Web or Desktop URL." (Changelog 2024-09-09: "Implemented verification of URL ownership as a mandatory component for app configuration" [T-CL].) "All apps that use the Content Posting API upload URL ... must verify these URLs, regardless of when the app was created." Steps: "Click the URL properties button at the top of your app page. Ensure you are verifying properties for your app in Production mode, then click Verify properties." Verify by **Domain** ("enter your domain and subdomain name") or **URL prefix** ("enter your complete URL ... Download the provided signature file, then upload it to your URL"). Media-transfer guide: "To verify domain ownership, it is recommended that you add a signature string to the domain's DNS records. Once the ownership of a domain is verified, all paths under that domain or its subdomains are considered owned by the developer application." [T-MTG] "For Sandbox environments, URL verification is only required for Content Posting API." [T-APP]
- The **redirect URI is not in the enumerated list** of URLs requiring verification; the Login Kit web doc only says it "must be registered in the Login Kit product configuration", HTTPS, absolute, static, ≤10 URIs, <512 chars, no query/fragment [T-LKW]. Given the "all URLs in your app configuration" sentence, treat the redirect host as needing a verified property to be safe — trivial when everything is under `gitavalley.org` (one Domain verification covers all subdomains [T-MTG]).
- Postiz media pulled by TikTok ("PULL_FROM_URL") must also come from a verified domain [T-MTG]; docs.postiz.com repeats this.

**Platform** [T-ARG]: "Web apps: You must provide a valid redirect URI under the web app configuration section."

**Demo video** [T-ARG] (verbatim): "At least one demo video that shows the complete end-to-end flow of the up-to-date integrations. You may upload a maximum of 5 videos, up to 50 MB each." "If your app has not been approved before, you are required to use a sandbox environment on the Developer Portal to demonstrate the integration." "The demo video should showcase the website or app where the features will actually be integrated. All selected products and scopes must be clearly demonstrated in the video. If you don't need certain products or scopes, make sure to remove them before review." "The video should clearly show the user interface and user interactions. **If you intend to integrate with a web app, make sure the domain of the website shown in the demo video matches the website URL you provide.**"
- Interpretation: Website URL = `https://gitavalley.org`, demo recorded on `postiz.gitavalley.org` → same registrable domain. A demo on `postiz.sethpc.xyz` with Website URL `gitavalley.org` would visibly mismatch. (TikTok does not define whether "domain" tolerates subdomains — unverified; a Domain-type URL property does cover subdomains.)

**Sandbox vs production** [T-SBX][T-SBXBLOG][T-APP]: "Sandbox mode is a restricted environment that allows you to try out integrations without having to submit your app for review." Up to 5 sandboxes; "up to 10 accounts" as target users; "Sandbox mode does not offer access to Content Posting API for public videos or Data Portability API." Import: "you can import your Sandbox configuration to a Draft of your app in Production mode to get it ready for submission" (overwrites the draft config).

**Unaudited production behaviour** [T-CSG][T-GS][T-DP]: "All content posted by unaudited clients will be restricted to private viewing mode." "User cap: Unaudited API Clients can allow up to 5 users to post in a 24 hour window. All user accounts using the API client to post must be set to private at the time of posting. Private Viewership: Unaudited API Clients can only post contents in SELF_ONLY viewership. To make the contents publicly viewable later on, the account owner must first change their account visibility to public, and then change the privacy settings of each content to 'Everyone.'" Direct-post reference: "Unaudited clients can only post to a private account." Lifting it: "your API client must undergo an audit to verify compliance with our Terms of Service."

**UX rules checked in the audit** [T-CSG]: display creator nickname (from `creator_info/query`), privacy level "manually select[ed] ... from a dropdown and there should be no default value", commercial-content toggle off by default, interaction settings off by default, consent line "By posting, you agree to TikTok's Music Usage Confirmation", content preview. (Postiz implements creator_info + a privacy selector; verify the UI against these before recording the demo.)

### 3b. Can redirect URIs be changed after approval without re-review?

**No.** App statuses [T-APP]: "Live: Your current revision of the app was approved and integrations are live. If you want to make changes, click the Create revision button to create a Draft cloned from the Live version." "Once your app is approved and live, any subsequent changes must be submitted for review and approved to appear in the live release." FAQ repeats it verbatim [T-FAQ]. A domain move after approval = new revision + new demo videos (the demo must show "up-to-date integrations" on the matching domain [T-ARG]) + re-verified URL properties.

Existing tokens: TikTok's refresh request is `client_key, client_secret, grant_type=refresh_token, refresh_token` — no `redirect_uri` (only the code exchange requires it: "Its value must be the same as the redirect_uri used for requesting code"). Access tokens last 86400 s, refresh tokens 31536000 s [T-TOK]. Connected channels survive a redirect change.

### 3c. Scopes Postiz needs and review

| Scope | TikTok description [T-SCOPES] | Product | Review |
|---|---|---|---|
| `user.info.basic` | "Read a user's profile info (open id, avatar, display name ...)" | Login Kit | Reviewed with the app; sandbox grants to target users |
| `user.info.profile` | "Read access to profile_web_link, profile_deep_link, bio_description, is_verified." | Display API (user info) | Reviewed with the app |
| `user.info.stats` | "Read access to a user's statistical data, such as likes count, follower count, following count, and video count" | Display API | Reviewed with the app |
| `video.list` | "Read a user's public videos on TikTok" | Display API — "Granted user.info.basic and video.list scopes" required [T-DISP] | Reviewed with the app |
| `video.upload` | "Share content to creator's account as a draft to further edit and post in TikTok." | Content Posting API (Upload/inbox) | Reviewed with the app |
| `video.publish` | "Directly post content to a user's TikTok profile." | Content Posting API Direct Post — "Your app must be approved for the video.publish scope" [T-GS] | Reviewed; plus the separate content audit for public visibility |

TikTok's scope reference does not mark individual scopes as review-exempt; the review guideline is "Only request permissions and features that your app needs" and "All selected products and scopes must be clearly demonstrated in the video" [T-ARG]. Every scope in the table must be added to the Production draft and shown in the demo.

### 3d. Timelines

- App review: "App review may take several days to two weeks after submission." [T-FAQ]
- Business verification (only "for publishing mini games and mini dramas" and "monetization features" — **not required** for Login Kit / Content Posting / Display): "1-3 business days" [T-BIZ].
- Content Posting audit: no separate timeline published (unverified).

---

## 4. Cross-cutting checklist

Legend: **(D)** depends on the final domain — wait for migration; **(N)** domain-independent — can be done now; **(R)** would have to be redone if a review were submitted before migrating.

### Meta

| # | Item | Class | Source |
|---|---|---|---|
| 1 | Business Verification of the temple's Business Portfolio (documents, legal name) | (N) | [M-BV] |
| 2 | Settings > Basic: Privacy Policy URL `https://gitavalley.org/privacy-policy/`, Terms URL, Category, 1024x1024 icon, App Purpose = "Yourself or your own business", DPO contact if applicable, data-deletion URL/instructions | (N) — all point at gitavalley.org or are static | [M-SG][M-BAS][M-PAGES] |
| 3 | Make ≥1 successful call per requested permission (Graph API Explorer or Postiz in Dev mode) within 30 days of submission | (N) but re-do the 30-day window if submission slips | [M-SG] |
| 4 | Data Use Checkup answers (needed before Live) | (N) | [M-DUC] |
| 5 | Per-permission usage descriptions (no copy/paste) | (N) — write now, mention the final URL | [M-SG] |
| 6 | App Domains, Website platform / Site URL, Valid OAuth Redirect URIs = final Postiz host + `/integrations/social/facebook` and `/instagram` (Strict Mode exact match) | (D) | [M-SEC][M-BAS][M-CON] |
| 7 | Reviewer access instructions + test credentials pointing at the reachable Postiz URL | (D) | [M-SG][M-IGAR] |
| 8 | Screencasts (one per permission, English UI, 1080p, mouse visible) recorded on the final domain | (D) | [M-SG] |
| 9 | If submitted before migrating: re-record 8, resubmit 7, update 6, and expect possible re-review ("may require re-review") | (R) | [M-SG] |

### Google / YouTube

| # | Item | Class | Source |
|---|---|---|---|
| 1 | Search Console verification of `gitavalley.org` (Domain property) by an account that is Owner/Editor on the Cloud project | (N) — the org already owns the domain | [G-BRAND][G-REQ] |
| 2 | Branding: app name/logo, home page `https://gitavalley.org`, privacy `https://gitavalley.org/privacy-policy/`, terms; ensure the privacy policy references and links the Google Privacy Policy and describes YouTube data use | (N) | [G-BRAND][G-POL][G-SENS] |
| 3 | Authorized domains: add `gitavalley.org` (covers `postiz.gitavalley.org`) | (N) if the final host is under gitavalley.org; (D) otherwise | [G-BRANDSUP] |
| 4 | Scope justification text for the 8 Postiz scopes incl. a defensible answer for `youtubepartner` (or patch the provider) | (N) | [G-SENS][G-CID] |
| 5 | Audit-form organisation/contact/business-model answers | (N) | [G-FORM] |
| 6 | OAuth client: add `https://<final-host>/integrations/social/youtube`; allow "5 minutes to a few hours" | (D) | [G-CLI] |
| 7 | Verification demo video (OAuth consent with client ID visible, each scope in use) recorded on the final domain | (D) | [G-SENS][G-REQ] |
| 8 | Audit form: "Primary Access URL", "Is your API Client publicly accessible?", demo credentials, OAuth-flow / upload-interface / homepage / privacy screenshots | (D) | [G-FORM] |
| 9 | If brand-verified before migrating: changing the consent-screen redirect URI ⇒ brand verification again (no user-facing penalty while pending). If audited before migrating: no official re-audit rule (unverified) but the audited URL/screenshots would be wrong | (R) | [G-CHG] |
| 10 | Existing YouTube channel tokens: nothing to redo | — | [G-WS] |

### TikTok

| # | Item | Class | Source |
|---|---|---|---|
| 1 | App name/icon (1024x1024, JPEG/JPG/PNG ≤5 MB), description that is clearly an organisational product, not "private or personal use" | (N) | [T-ARG][T-APP] |
| 2 | Website URL = `https://gitavalley.org` with Privacy Policy + Terms links visible without opening a menu; both pages live | (N) — verify gitavalley.org has visible Terms link (privacy exists) | [T-ARG] |
| 3 | URL properties: verify `gitavalley.org` as a **Domain** property in Production mode (DNS signature string) — covers the Web URL, Terms, Privacy, redirect host and media-pull host at once | (N) if final host is a gitavalley.org subdomain; (D) otherwise | [T-APP][T-MTG] |
| 4 | Implement/confirm Content Posting UX rules in the Postiz posting UI (creator nickname, no default privacy, toggles off, consent text, preview) | (N) | [T-CSG] |
| 5 | Sandbox: target users (≤10), finish integration testing; remember sandbox cannot post public videos | (N) | [T-SBX] |
| 6 | Production draft: Web platform redirect URI `https://<final-host>/integrations/social/tiktok`; Web/Desktop URL; Content Posting upload URL domain | (D) | [T-ARG][T-LKW][T-APP] |
| 7 | Demo videos (≤5 × 50 MB) showing Login Kit + every scope + Direct Post end-to-end, on a domain that "matches the website URL you provide" | (D) | [T-ARG] |
| 8 | If approved before migrating: "Create revision" → new redirect URI/URLs → new demo videos → full re-review ("any subsequent changes must be submitted for review") | (R) | [T-APP][T-FAQ] |
| 9 | Until the content audit passes: post with `privacy_level = SELF_ONLY`, account private, ≤5 posting users/24 h | — | [T-CSG][T-DP] |

### Recommended sequence

1. Now (domain-independent): Meta Business Verification; Search Console verification of `gitavalley.org`; TikTok Domain property for `gitavalley.org`; Google branding + scope justifications; Meta per-permission write-ups + API-call evidence; TikTok UX conformance in Postiz; confirm `gitavalley.org` shows Terms + Privacy links prominently and the privacy policy mentions Google/YouTube data use.
2. Migrate Postiz to `postiz.gitavalley.org` (set `FRONTEND_URL`; register the four redirect URIs; reconnect any channel that fails — tokens themselves survive).
3. Record all screencasts/demos on the final domain; submit Meta App Review, Google verification, YouTube audit, TikTok production review in one pass.

---

## Sources (all fetched 2026-09-07)

Meta
- [M-SEC] https://developers.facebook.com/docs/facebook-login/security/ — Valid OAuth Redirect URIs, Strict Mode, App Domains
- [M-BAS] https://developers.facebook.com/docs/development/create-an-app/app-dashboard/basic-settings — App Domains, Privacy/Terms URL, icon, category, verification status
- [M-AR] https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/app-review/ (and /docs/app-review/) — what App Review approves
- [M-SG] https://developers.facebook.com/docs/app-review/submission-guide/ (same content as .../app-review/submission-guide) — checklist, screen recordings, App Purpose, "may require re-review", "within a week", Live-mode note
- [M-CON] https://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/app-review/content — app settings + platforms sentence
- [M-MODES] https://developers.facebook.com/docs/development/build-and-test/app-modes — Development mode statements
- [M-ACC] https://developers.facebook.com/docs/graph-api/overview/access-levels/ — Standard vs Advanced Access
- [M-BV] https://developers.facebook.com/docs/development/release/business-verification — BV required for Advanced Access; role-user exception
- [M-AV] https://developers.facebook.com/docs/development/release/access-verification/ — Access Verification / Tech Provider
- [M-TP] https://developers.facebook.com/docs/development/release/tech-providers/ — Tech Provider definition
- [M-DUC] https://developers.facebook.com/docs/development/maintaining-data-access/data-use-checkup/ — annual DUC, required before Live
- [M-PERM] https://developers.facebook.com/docs/permissions/ — per-permission review + BV statement
- [M-IG] https://developers.facebook.com/docs/instagram-platform/overview — IG API with Facebook Login vs Instagram Login
- [M-IGAR] https://developers.facebook.com/docs/instagram-platform/app-review — screencast + test credentials
- [M-IGPUB] https://developers.facebook.com/docs/instagram-platform/content-publishing — publishing permissions, 100 posts/24 h
- [M-PAGES] https://developers.facebook.com/documentation/pages-api/create-an-app — use case, "Review your app settings", required app assets (icon 512–1024 px, JPEG/GIF/PNG, <5 MB), per-platform reviewer dialog
- [M-PAPI] https://developers.facebook.com/docs/pages-api/posts — publishing permissions
- [M-FLB] https://developers.facebook.com/docs/facebook-login/facebook-login-for-business — for tech providers; plain Facebook Login otherwise
- [M-LL] https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived — `fb_exchange_token` params (no redirect_uri)
- [M-LIVE19] https://developers.facebook.com/blog/post/2019/09/23/live-mode-for-production-use/ — Dev-mode data access limited to role users; Live-mode required fields
- [M-APPC] https://developers.facebook.com/docs/games/build/instant-games/get-started/app-center/ — the only "without transparent background" icon statement (games context)
- [M-REL] https://developers.facebook.com/docs/development/release/ — release steps
- UNREACHABLE: https://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/app-review/AR-FAQs (JS-rendered, returned navigation only); https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/app-review/faqs (404); https://developers.facebook.com/docs/apps/review (redirects to hub — the "repeat App Review when adding permissions to a live app" sentence is from a search snippet only)

Google / YouTube
- [G-WS] https://developers.google.com/identity/protocols/oauth2/web-server — redirect URI rules, code-exchange `redirect_uri`, refresh request params (curl-grepped)
- [G-CLI] https://support.google.com/cloud/answer/15549257 — Manage OAuth Clients; "5 minutes to a few hours"
- [G-BRANDSUP] https://support.google.com/cloud/answer/10311615 — Authorized domains must be pre-registered; Top Private Domain
- [G-BRAND] https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification — Search Console, Draft Branding, 7-day validity, timelines
- [G-SENS] https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification — demo video, home page/privacy on same domain, 3-5 business days, "deleting a YouTube video" example, personal-use cap note
- [G-REQ] https://support.google.com/cloud/answer/13464321 — verification requirements
- [G-CHG] https://support.google.com/cloud/answer/13464018 — changes to approved app (redirect URI ⇒ brand re-verification)
- [G-FAQ] https://support.google.com/cloud/answer/13463817 — timelines (2-3 / 10 business days / 6 weeks), 100-user cap
- [G-UNV] https://support.google.com/cloud/answer/7454865 — unverified app screen, 100 new users
- [G-AUD] https://support.google.com/cloud/answer/15549945 — publishing status Testing vs In production
- [G-NOTNEEDED] https://support.google.com/cloud/answer/13464323 — when verification is not needed
- [G-SUBMIT] https://support.google.com/cloud/answer/13461325 — publish → prepare for verification steps
- [G-OAUTH] https://developers.google.com/identity/protocols/oauth2 — refresh-token expiration incl. Testing 7-day rule
- [G-SCOPES] https://developers.google.com/identity/protocols/oauth2/scopes — YouTube scope descriptions (curl-grepped)
- [G-CID] https://developers.google.com/youtube/partner/getting_started — Content ID API is for content partners only
- [G-INSERT] https://developers.google.com/youtube/v3/docs/videos/insert — unverified-project uploads forced private
- [G-REV] https://developers.google.com/youtube/v3/revision_history — 28 July 2020 entry
- [G-QUOTA] https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits — audit for quota, 12-month validity
- [G-POL] https://developers.google.com/youtube/terms/developer-policies — privacy policy requirements
- [G-TOS] https://developers.google.com/youtube/terms/api-services-terms-of-service — monitoring/audit clause
- [G-FORM] https://support.google.com/youtube/contact/yt_api_form — audit form fields as rendered

TikTok
- [T-APP] https://developers.tiktok.com/doc/getting-started-create-an-app — icon spec, URL properties (2024-09-09 rule, Production mode, Domain vs prefix), Login Kit redirect, app statuses, "any subsequent changes must be submitted for review"
- [T-ARG] https://developers.tiktok.com/doc/app-review-guidelines — name/icon/description/website/legal, Web redirect URI, demo video requirements incl. domain-match sentence
- [T-FAQ] https://developers.tiktok.com/doc/getting-started-faq — "several days to two weeks"; changes after approval
- [T-LKW] https://developers.tiktok.com/doc/login-kit-web — redirect URI registration rules
- [T-TOK] https://developers.tiktok.com/doc/oauth-user-access-token-management — token exchange/refresh params and lifetimes
- [T-SCOPES] https://developers.tiktok.com/doc/tiktok-api-scopes — scope descriptions
- [T-DISP] https://developers.tiktok.com/doc/display-api-get-started — required scopes
- [T-GS] https://developers.tiktok.com/doc/content-posting-api-get-started — video.publish approval, unaudited private, creator_info
- [T-DP] https://developers.tiktok.com/doc/content-posting-api-reference-direct-post — privacy_level enum, "Unaudited clients can only post to a private account"
- [T-CSG] https://developers.tiktok.com/doc/content-sharing-guidelines — unaudited caps (5 users/24 h, SELF_ONLY), UX rules
- [T-MTG] https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide — DNS signature, domain covers subdomains, URL-prefix rules
- [T-SBX] https://developers.tiktok.com/doc/add-a-sandbox — sandbox limits, import to Production draft
- [T-SBXBLOG] https://developers.tiktok.com/blog/introducing-sandbox — sandbox overview
- [T-BIZ] https://developers.tiktok.com/doc/verify-your-business — when business verification is required; 1-3 business days
- [T-CL] https://developers.tiktok.com/doc/changelog — 2024-09-09 URL-ownership entry
- [T-DEVCFG] https://developers.tiktok.com/doc/set-up-development-configuration — URL properties (signature file)

Postiz
- [P-IG] https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/integrations/social/instagram.provider.ts
- [P-IGS] .../instagram.standalone.provider.ts
- [P-FB] .../facebook.provider.ts
- [P-YT] .../youtube.provider.ts
- [P-TT] .../tiktok.provider.ts
- [P-ABS] .../social.integrations.interface.ts — `checkScopes()`
- [P-CFG] https://docs.postiz.com/configuration/reference — `FRONTEND_URL` "Used as the OAuth redirect base"
- [P-DOCIG] https://docs.postiz.com/providers/instagram, [P-DOCTT] https://docs.postiz.com/providers/tiktok, [P-DOCYT] https://docs.postiz.com/providers/youtube — setup guides (secondary; note the TikTok page's nonexistent `video.create` scope)
