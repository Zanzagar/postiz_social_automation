# Infrastructure Migration Plan — Leaving sethpc.xyz

**Date:** 2026-09-07 · **Status:** DECISION NEEDED (§2) · **Owner:** Corey
**See also:** `docs/hub-hosting-plan.md` (hosting the Hub itself at social.gitavalley.org). **Research behind this plan:** `docs/research/postiz-hosting-migration.md` (hosting options, prices, Postiz requirements) and `docs/research/platform-oauth-domain-requirements.md` (what Meta / Google / TikTok bind to the domain). Every factual claim below is sourced there; this document is the runbook.

---

## 0. What actually depends on Seth today

Verified against the repo and live DNS on 2026-09-07:

| Thing | On Seth's infra? | Used by our app? | Migration action |
|---|---|---|---|
| **Postiz** at `postiz.sethpc.xyz` (v2.18.0; Postiz + Postgres + Redis + Temporal + Elasticsearch) | Yes — resolves to a **residential Verizon IP** (71.178.159.217) via Google Cloud DNS | **Yes — the only runtime dependency.** Backend reads `POSTIZ_BASE_URL` (`api/config.py`); frontend hardcodes the "Postiz Admin" link (`Sidebar.tsx`, `BottomNav.tsx`) | Replace (this plan) |
| Postiz **provider secrets** (Meta app secret, Google client secret, TikTok keys) in Seth's `postiz.env` | Yes | Indirectly | Re-obtain from our own consoles; **rotate after cut-over** (§5) |
| Postiz **channel OAuth tokens** (FB, IG, YouTube) + our Public API key | Yes (Postiz Postgres) | Yes | Reconnect on the new instance (2-min OAuth each); new API key |
| n8n at `n8n.sethpc.xyz` | Yes | **No** — appears in docs/README only; zero references in `api/`, `src/`, `frontend/` | Drop; delete stale docs |
| Gitea `git.sethpc.xyz` | Yes | **No** — this repo's remote is GitHub | Nothing |
| Content Hub (FastAPI :8000 + React :3000) | No — Corey's machine (its own single point of failure) | — | **Move to AWS Lightsail at social.gitavalley.org — see `docs/hub-hosting-plan.md`.** The Claude Max login cannot follow it (Anthropic terms); the server uses a temple-owned Anthropic Console API key (≈ $5/mo) |
| `gitavalley.org` (WordPress) | No — **SiteGround** (`ns1/ns2.siteground.net`, not Cloudflare) | Privacy/Terms URLs | DNS record for a Postiz subdomain is added in SiteGround Site Tools (Path B only) |

**What Seth's box holds that we would lose:** nothing we need. Content, captions, analytics history and the media library live in our own SQLite (`data/gvsa.db`) and Drive. Postiz there holds 4 channel connections and zero scheduled posts.

---

## 1. Requirements

1. Reliable, datacenter-hosted; no single volunteer's home connection.
2. Low ops for one technical-but-not-sysadmin maintainer.
3. Public HTTPS (all three platforms require HTTPS OAuth callbacks).
4. Postiz Public API for the Content Hub (posting + analytics).
5. 4 channels (FB page, IG, YouTube, TikTok), a few posts/week, 1–3 staff.
6. Budget-sensitive nonprofit; predictable monthly cost.
7. **Time-to-public-posting matters** (recording week is stalled on Seth).

---

## 2. The decision: Postiz Cloud vs self-hosted VPS

| | **Path A — Postiz Cloud** | **Path B — Self-host on a VPS** |
|---|---|---|
| Monthly cost | Standard **$29** (5 channels, one shared login, API included) or Team **$39** (10 channels, named seats) | DigitalOcean 4 GB NYC $24 + weekly backups $4.80 ≈ **$29**; AWS Lightsail 4 GB ≈ **$8 effective** if the TechSoup AWS credit ($1,000/yr, $95 fee) is granted |
| Ops | **None** (updates, backups, TLS, Temporal — all Postiz's) | Monthly `docker compose pull && up -d` (four security releases in Q2 2026 alone), Caddy, provider backups, disk watch; Corey becomes the new single point of failure |
| Platform apps | **Postiz's already-approved apps** — "Provider developer apps: already registered, just click connect" (docs.postiz.com/cloud/overview) | Our own Meta / Google / TikTok apps — **all three App Reviews required** (§6) |
| Time to *public* posting on all 4 channels | **Day 1** | Weeks to months: Meta BV + App Review (posts from a Dev-mode app are **visible only to app role users** until Live); YouTube uploads **forced private** until the compliance audit passes (no published timeline); TikTok posts **SELF_ONLY/private** until the content audit passes (no published timeline); Google verification may push back on Postiz's `youtubepartner` Content-ID scope |
| Ongoing review upkeep | None | Meta annual Data Use Checkup; YouTube audit valid ~12 months; TikTok: **any** app change (incl. redirect URI) = new revision + re-review |
| Domain / DNS | Not needed | `social.gitavalley.org` A record (needs SiteGround access); one Domain-level TikTok URL property; Google Search Console verification of gitavalley.org |
| Data | Tokens/posts on Postiz's cloud ("managed by Postiz"; no export feature documented) — content + analytics remain in **our** SQLite either way | Ours |
| API rate limit | 90–100 req/hr (vs 30 today) | 90/hr default on v2.23 |
| Reversibility | Cheap either direction: reconnect 4 channels + new API key | Same |

### Recommendation

**Path A — Postiz Cloud, Standard plan ($29/mo), upgrading to Team ($39) only when named staff logins matter.** Reasons, in order:

1. **It removes the actual risk.** The failure we are fixing is "one volunteer's box." Path B moves that risk to Corey; Path A removes it.
2. **It collapses the review workstream to zero.** Every gate in §6 exists solely because we run our own developer apps. Under Path A the Meta app, the Google OAuth client, the TikTok sandbox, the justifications and the three screencasts are no longer on the critical path. The first "real" publish is public on day one — under Path B, even after the Meta E2E dry run succeeds, the post is invisible to the public until App Review approval.
3. **Cost is a wash** (~$29 either way; $348/yr), so the decision is purely control vs. ops + reviews.
4. **Reversible.** Same product, same API; if pricing or trust changes, Path B is a one-day move.

Choose **Path B** instead if the temple requires data to stay on infrastructure it controls, or if a permanent admin is willing to own a server and the review upkeep. If Path B, the TechSoup AWS credit makes Lightsail the cheapest reliable option; DigitalOcean is the simplest.

**One thing to keep regardless of path:** the Meta app stays in **Development mode** for the Content Hub's direct Graph API use (history import, insights backfill). Dev mode grants all permissions to app role holders (Corey is admin), so no Meta review is needed for that.

---

## 3. Path A — Postiz Cloud (≈ 1 day)

1. **Sign up** at postiz.com with an organisation account (`iot.admin@gitavalley.org` or similar shared identity, not a personal account). 7-day trial → Standard plan. Keep the password in the temple's password manager.
2. **Connect channels** (Settings → Add Channel): Facebook Page "Gita Nagari Farm", Instagram "Gita Valley" (Instagram via Facebook Business — IG is already linked to the Page), YouTube "Gita Valley" brand account, TikTok `@gitavalley` (real login — no sandbox). Each is a normal OAuth click through Postiz's apps.
3. **Public API key:** Settings → Developers → copy.
4. **Content Hub cut-over** (§4 code changes first, then):
   ```
   POSTIZ_BASE_URL=https://api.postiz.com/public/v1
   POSTIZ_API_KEY=<new key>
   ```
   Restart backend: `kill -9 $(systemctl show gvsa-backend -p MainPID --value)`. Health page must show `postiz: ok · 4 integrations connected`.
5. **E2E publish** from the Content Hub: Media → farm photo → draft → FB + IG → Publish now → verify live on facebook.com / Instagram. Then one YouTube upload and one TikTok clip (public). This *is* the first real publish — make it a keeper.
6. **Auto-release settings:** review Settings → Publishing (all platforms currently "wait for blessing"; keep TikTok on manual).
7. **Decommission Seth** (§5) and update docs (§7).

Not needed under Path A: DNS, TLS, VPS, the four redirect URIs, Meta Business Verification, the YouTube audit form, the TikTok production app, the review screencasts.

---

## 4. Content Hub changes (both paths, ~1 hour, one PR)

1. `api/config.py` and `src/content_engine/postiz.py`: drop the `postiz.sethpc.xyz` defaults — require `POSTIZ_BASE_URL` from `.env` (fail loudly if absent).
2. Frontend "Postiz Admin" link (`Sidebar.tsx`, `BottomNav.tsx`, `layout.test.tsx`): read `VITE_POSTIZ_URL` (fallback `https://platform.postiz.com` for Cloud, or the VPS hostname); rebuild the docker frontend.
3. `.env.example`: rename the stale `POSTIZ_API_URL` to `POSTIZ_BASE_URL`; document both Cloud and self-host values.
4. Postiz integration IDs change on the new instance — the backend resolves them per call from `GET /integrations`, so nothing is cached; verify once.
5. `README.md`, `docs/gita-valley-context.md`, `docs/INFRASTRUCTURE_STATUS.md`, `docs/platform-setup-guide.md`, `docs/N8N_INTEGRATION.md`: remove sethpc/n8n references (n8n was never wired in).

---

## 5. Decommissioning Seth's infrastructure (both paths)

Do this **after** a test post has published from every channel on the new instance:

1. Old Postiz (`postiz.sethpc.xyz`): Settings → Channels → **disconnect** FB, IG, YouTube (revokes those tokens). Delete the old Public API key (Settings → Developers → rotate).
2. **Rotate the secrets that live in Seth's `postiz.env`** — they were handed over in plaintext:
   - Meta: developers.facebook.com → App `955821356900142` → Settings → Basic → **Reset App Secret** (Path B: put the new secret in our own Postiz env).
   - Google: Cloud Console → Credentials → OAuth client → **Reset secret** (or create a new client; Path A: can simply delete the client's Postiz redirect URI).
   - TikTok: developer portal → regenerate client secret (sandbox and production).
   - The old `POSTIZ_API_KEY` (already once exposed in the public repo) dies with the instance.
3. Meta app roles: remove Seth if he holds a role. Business Portfolio: confirm only temple staff are admins.
4. Message Seth: thank him; ask him to `docker compose down -v` the Postiz stack and n8n and delete the env file. No dependency remains if he never does.
5. Remove the "swap TikTok sandbox keys" and "key-rotation SQL" asks from the handoff — both are moot.

---

## 6. MUST be done before submitting each application (Path B only)

Under **Path A none of this is required** — posting goes through Postiz's approved apps; keep our Meta app in Development mode for analytics.

Under Path B, **finalise the domain first (`social.gitavalley.org`), then submit all three in one pass.** Every platform binds reviewed artefacts to the hostname; Google explicitly re-runs brand verification on a redirect-URI change and TikTok re-reviews *any* change after approval. Legend: **(N)** do now, independent of domain · **(D)** only after the new domain is live.

### Common prerequisites
- **(N)** SiteGround access for the person adding the `social.gitavalley.org` A record; VPS provisioned; Caddy TLS green.
- **(N)** `gitavalley.org` privacy policy: add a link to Google's privacy policy (`https://policies.google.com/privacy`) — required by YouTube Developer Policies. Footer already shows Privacy Policy + Terms of Use links (TikTok requirement satisfied) and already names Google/YouTube/Meta/Facebook/Instagram/TikTok.
- **(D)** Postiz env: `FRONTEND_URL=https://social.gitavalley.org`; provider keys set; channels reconnected; Content Hub E2E publish succeeds on the new host.
- **(D)** Record every screencast/demo **on the new domain** (1080p, English UI, mouse visible, no audio needed for Meta).

### Meta App Review (10 permissions)
1. **(N) Business Verification** of the "Gita Nagari Farm" Business Portfolio — required for Advanced Access on all ten permissions. Needs EIN + an official document with the org's legal name/address (from the temple president). Start it *today*; it is the long pole.
2. **(N)** Settings → Basic: icon (1024×1024; the transparent PNG is already made), category Business, Privacy Policy `https://gitavalley.org/privacy-policy/`, Terms `https://gitavalley.org/terms-of-use/`, **App Purpose = "Yourself or your own business"**, data-deletion instructions URL.
3. **(N)** Data Use Checkup (required before Live mode).
4. **(N)** Per-permission justifications (drafted in `docs/platform-verification-guide.md` §1 — re-read each so none are copy-paste identical; Meta rejects duplicates).
5. **(N, re-do if it slips)** ≥1 successful API call per permission **within 30 days of submission** (Graph API Explorer or Postiz in Dev mode). The April 2026 calls are outside the window.
6. **(D)** App Domains + Website URL + Valid OAuth Redirect URIs = `https://social.gitavalley.org/integrations/social/facebook` and `/instagram` (Strict Mode exact match). Remove the sethpc entries.
7. **(D)** Reviewer access instructions + test login for the Postiz URL.
8. **(D)** Screencasts A/B/C on the new domain (scripts in `docs/video-recording-readiness.md`).
9. Submit all 10 → decision "within a week" → switch to Live. Note: Dev-mode posts are visible **only to role users** until Live.

### Google — OAuth verification + YouTube API compliance audit
1. **(N)** Google Search Console: verify `gitavalley.org` as a **Domain property** with an account that is Owner/Editor on the `gita-valley-content-repository` Cloud project (DNS TXT at SiteGround).
2. **(N)** Google Auth Platform → Branding: app name/logo, home page `https://gitavalley.org`, privacy `https://gitavalley.org/privacy-policy/`, terms `https://gitavalley.org/terms-of-use/`, Authorized domain `gitavalley.org`.
3. **(N)** Scope justifications for Postiz's 8 scopes, including a defensible answer for `youtubepartner` (Content ID API — "not accessible to all developers"). Fallback if Google refuses: patch the self-hosted YouTube provider to drop that scope, or stay unverified (100-user cap is irrelevant to us; users click through the warning).
4. **(N)** Audit-form organisation/contact/business-model answers (pre-written in the verification guide §2; form fields listed in the research doc).
5. **(D)** OAuth client: add `https://social.gitavalley.org/integrations/social/youtube`; wait "5 minutes to a few hours"; reconnect the YouTube channel.
6. **(D)** Verification demo video (consent screen with client ID visible; each scope exercised) on the new domain.
7. **(D)** Submit the **YouTube API Services compliance audit** form: Primary Access URL = the Postiz host; demo credentials; screenshots of OAuth flow, upload UI, homepage, privacy policy. No official timeline; uploads stay **private** until it passes.
8. Existing YouTube channel tokens survive the redirect change (refresh has no `redirect_uri`).

### TikTok — production app review (Login Kit + Content Posting + Display)
1. **(N)** App icon, name, description framed as the organisation's publishing tool ("apps must not be for private or personal use").
2. **(N)** Website URL = `https://gitavalley.org` (not the Postiz login page); Privacy + Terms links visible without opening a menu — already true.
3. **(N)** **URL properties:** verify `gitavalley.org` as a **Domain** property in **Production** mode (DNS signature TXT at SiteGround) — one verification covers Terms, Privacy, Web URL, the redirect host and the media-pull host.
4. **(N)** Confirm Postiz's posting UI meets the Content Sharing Guidelines checked in audit (creator nickname shown, privacy level chosen manually, commercial toggles off by default, music-usage consent line, preview).
5. **(N)** Finish sandbox testing with `@gitavalley` as target user (sandbox cannot post public videos).
6. **(D)** Production draft: Web platform redirect URI `https://social.gitavalley.org/integrations/social/tiktok`; Web URL; import sandbox config.
7. **(D)** Demo videos (≤5 × 50 MB) on the new domain, showing Login Kit + every scope + Direct Post end-to-end; the demo domain must match the Website URL's domain.
8. Submit → "several days to two weeks". Until the separate content audit passes, posts must use `privacy_level = SELF_ONLY` and the account must be private (Postiz defaults to PUBLIC_TO_EVERYONE — select manually).
9. After approval, **any** change (incl. redirect URI) requires a new revision + re-review.

### Send to the temple president (Path B)
EIN + official organisation document (Meta Business Verification); YouTube authorization letter template (verification guide §2) in case Google asks; budget approval for the VPS (or, Path A, the Postiz subscription).

---

## 7. Timeline

| | Path A (Cloud) | Path B (VPS + own apps) |
|---|---|---|
| Infra live | Day 1 | Day 1–2 (VPS, DNS, Caddy, env, reconnect) |
| First public post on FB/IG/YT/TikTok | Day 1 | FB/IG: after Meta BV + review (≈1–4 weeks). YouTube: after audit (unpublished timeline). TikTok: after review (≤2 weeks) **and** content audit (unpublished) |
| Seth decommissioned | Day 2 | Day 2–3 |
| Ongoing | $29–39/mo, no ops | ~$29/mo + monthly update routine + annual/12-month review upkeep |

## 8. Open questions (only you can answer)

1. **Path A or B?** (§2) — this gates everything else.
2. Who has the **SiteGround** login for gitavalley.org DNS (Path B) and can edit the privacy-policy page (both paths)?
3. Which Google account owns the `gita-valley-content-repository` Cloud project (Search Console verification must be done by a project Owner/Editor)?
4. Is the temple willing to complete **Meta Business Verification** (EIN + document) — Path B's long pole?
5. Path A: shared Postiz login (Standard $29) or named seats (Team $39)?
