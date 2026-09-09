# Hosting Decision Matrices — Content Hub and Scheduling Engine

**Date:** 2026-09-08 · **Owner:** Corey · **Audience:** Corey and the temple president
**Evidence:** `docs/research/hub-wordpress-linkage.md`, `docs/research/social-data-access-own-apps.md`, `docs/research/hub-hosting-aws-vps.md`, `docs/research/claude-on-server-options.md`, `docs/research/postiz-hosting-migration.md`, `docs/research/platform-oauth-domain-requirements.md`. Every verdict below was adversarially re-verified against primary sources on 2026-09-07/08. Scores are the maintainer's judgment on a 1–5 scale; weights are stated so the president can change them.

---

## 0. The finding that reshapes both matrices

**"Unfettered access to all of our content and engagement metrics" is a property of the temple's own developer apps, not of where Postiz runs.**

- Postiz, Cloud or self-hosted, runs the same open-source provider code. Its analytics endpoints fetch a **small subset** of metrics live from the platforms (4 Facebook page series, snapshot post numbers, 7/30/90-day windows), cache them in Redis for one hour, and **persist nothing**: the Postiz database has no analytics table at all. Self-hosting Postiz therefore adds zero read access. The only thing a self-hosted Postiz database holds that Cloud does not is a copy of the OAuth token, which our own app can mint anyway.
- Every byte of history the Hub holds today (100 Facebook posts, hashtag and media performance, pillar-gap suggestions, the "history" side of analytics) came from **the temple's own Meta app over the Graph API**, and that path is identical under either Postiz option.
- **The old belief that App Review was needed for full history is wrong.** A live, read-only probe on 2026-09-08 with the current role-holder token paged **all 1,598 Facebook posts with engagement** and read **825+ Instagram media with reach, saves, shares and views**. The March import stopped at 100 because the second page returned a non-200 under the original heavy-fields query and was never re-run (`meta_importer.py:113-115`). Meta's own docs say role-only apps are exempt from Business Verification, Development mode has no separate rate-limit tier, a long-lived Page token never expires, and the Platform Terms contain no "development mode is for testing only" clause. Google's unverified project is unrestricted for reads (the audit only affects extra quota and public uploads). TikTok's Sandbox exposes Display API reads for up to 10 target accounts, including `@gitavalley`; an unaudited Production app returns nothing until approved.
- What actually bounds history is the platforms themselves: Facebook returns roughly 600 ranked posts per year at 100 per page with a 2-year insights window; Instagram caps media at 10,000 with 2-year media insights; YouTube Analytics goes back to channel start; TikTok walks public videos by cursor.

**Consequence:** publishing and reading are separate decisions. The maximum-functionality configuration is **publish through Postiz Cloud (public posting on day one) and read through the temple's own apps (full history, full metrics, now)**. Self-hosting Postiz would give up the first without improving the second.

**Data-pipeline gaps found (hosting-independent, all fixable):** the Facebook import must be re-run for 1,598 posts; the Instagram import is coded but unconfigured (`META_INSTAGRAM_ACCOUNT_ID` unset); the insights backfill uses `post_impressions*` metrics that Meta deprecated above Graph API v25 and now return 400, so it needs rewriting to current metrics; the CLI scripts read `META_PAGE_ACCESS_TOKEN` while `.env` defines `META_PAGE_TOKEN`; there is no YouTube or TikTok importer yet; and the Postiz per-post analytics chain is dead until the publish-connector defect is fixed. These are the real work items behind "maximum functionality", and none of them depend on the hosting choice.

## 0b. The volunteer-administrator dependency, and the self-sustainability test

The decision against self-hosting is, at root, a decision against depending on any single volunteer's equipment and attention, whoever the volunteer is. The current arrangement makes the cost of that dependency concrete. None of this is a criticism of Seth, who has hosted the scheduler for free since February; it is a description of what the organisation does not control.

### What Seth controls today (verified 2026-09-07)

| Asset | Where it lives | What the temple can do without him |
|---|---|---|
| The production scheduler (`postiz.sethpc.xyz`) | Docker on his home hardware, on a **residential Verizon connection** (71.178.159.217) | Nothing: no SSH, no admin access ("Need admin login from Seth", `docs/platform-setup-guide.md`; "We do NOT have direct access to push updates", `docs/gita-valley-context.md`) |
| The domain and DNS `sethpc.xyz` | His registrar and Google Cloud DNS account | Nothing; if the domain lapses, every `*.sethpc.xyz` address dies, including any OAuth redirect URI a platform review was bound to |
| The temple's platform secrets (Meta app secret, Google client secret, TikTok keys) | Plaintext in his `postiz.env` | Cannot revoke his copy except by rotating every secret |
| The channel OAuth tokens and the Public API key | His PostgreSQL database | Cannot rotate the once-exposed API key: it needs one SQL statement on his host, requested in July and still pending |
| Software currency | Postiz v2.18.0; four security releases (v2.21.5–v2.21.10, April–June 2026) have shipped since | Cannot patch |
| Backups | Unknown | Cannot verify or restore |
| Second-order infrastructure (n8n, Gitea) | Same host and domain | Unused by the Hub, but any credential stored there (the Postiz key in n8n) is outside our control |

### The tensions this creates

1. **Velocity.** The TikTok sandbox-key swap has been pending since 2026-08-17; the API-key rotation since July. Recording week stalled on messages to a Discord bot. Every future change to the scheduler (an upgrade, a new provider key, a redirect URI for a review) queues behind the same channel.
2. **Security.** The organisation's platform secrets sit on hardware and a home network it cannot audit, shared in plaintext with a non-staff volunteer, and a compromised API key cannot be rotated on demand.
3. **Availability.** A home uplink, a single machine, no stated SLA, and no known backup or restore procedure. An ISP outage, a power cut, a hardware failure or a move ends publishing until one person is reachable.
4. **Governance and ownership.** There is no agreement, no handover document, no second administrator, and no organisational login. The temple cannot compel, audit, or replace the arrangement; goodwill is the only guarantee.
5. **Compliance coupling.** Any platform review submitted from `postiz.sethpc.xyz` would bind reviewer access, demo videos, verified URL properties and redirect URIs to a domain the organisation does not own (`docs/research/platform-oauth-domain-requirements.md`). A later move would re-trigger Google brand verification and a full TikTok re-review.
6. **Exit cost grows with time.** Every channel connected, every scheduled post, and every review artifact tied to his domain raises the cost of leaving later. It is cheapest to leave now, with four channels and an empty calendar.

### The same test applied to self-hosting under Corey

Self-hosting Postiz on the temple's own server removes Seth but re-creates the pattern with Corey: one volunteer holding root, patching a seven-container stack monthly, owning three platform reviews and their yearly upkeep, and being the only person who knows how it fits together. That is a better position than today (the organisation would at least own the server and accounts), but it is not self-sustaining. The Cloud option moves the operational burden to a vendor with an SLA and support channel, leaves the organisation owning the account, and reduces Corey's role to administrator, which any successor can inherit from a shared login.

### Self-sustainability test

Six conditions the organisation should be able to answer "yes" to for its publishing stack. Pass/fail per option:

| Condition | Stay on Seth's server | Self-host Postiz (Corey admin) | Postiz Cloud + Hub on Lightsail (recommended) |
|---|---|---|---|
| Every account and domain is owned by the organisation (shared org email), not an individual | No | Yes | Yes |
| No volunteer-controlled hardware or home network in the publishing path | No | Partly (temple-owned cloud server, volunteer-operated) | Yes (vendor-operated scheduler; Lightsail with automatic snapshots for the Hub) |
| Credentials can be rotated by the organisation without any specific person | No | Yes | Yes |
| Security patches and backups happen without a volunteer remembering | No | No (monthly manual routine) | Yes for the scheduler; Hub patches remain a light monthly task with a runbook |
| A documented runbook exists and a second administrator is named | No | Only if written and staffed | Runbooks in `docs/`; a second admin is a login away |
| Losing any one person costs less than a day to recover from | No | No (server knowledge concentrated in one person) | Yes |

**Reading the table:** the recommended configuration is the only one that passes every row. Self-hosting passes ownership and rotation but fails the "no single volunteer" rows, which are the rows that failed under Seth. Two follow-through items make the recommended option fully self-sustaining rather than nearly: name a second administrator with access to the shared org email and the AWS, Anthropic and Postiz accounts, and keep `docs/DEPLOYMENT.md` current so a successor can operate the Hub from the runbook alone.

---

## 1. Matrix A — Hosting the Content Hub (the social.gitavalley.org question)

### A1. Weighted comparison

Weights: Cost 15% · Reliability 25% · Ops burden 20% · Fit for the app 20% · Data control 10% · Time to deploy 10%. Scores 1 (worst) to 5 (best).

| Option | $/mo | $/yr | Cost | Reliab. | Ops | Fit | Data | Time | **Weighted** | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **AWS Lightsail 2 GB, us-east-1, subdomain social.gitavalley.org** | $12 (+~$1 snapshots); ≈ $0 under TechSoup | $156 | 5 | 5 | 4 | 5 | 5 | 4 | **4.70** | **RECOMMENDED** |
| DigitalOcean Basic 2 GB NYC + weekly backups | $14.40 | $173 | 4 | 5 | 4 | 5 | 5 | 4 | 4.55 | Runner-up (no nonprofit credit) |
| Fly.io shared-cpu 2 GB + 10 GB volume | ≈ $12.20 | ≈ $146 | 5 | 4 | 4 | 4 | 4 | 4 | 4.15 | Viable equal; single-copy volume, usage billing |
| Railway Hobby + volume | ≈ $12–18 (est.) | ≈ $150–215 | 4 | 4 | 5 | 3 | 4 | 4 | 4.00 | Viable; 5 GB volume cap, usage-billed |
| Render Standard 2 GB + 10 GB disk | $27.50 | $330 | 2 | 4 | 5 | 3 | 4 | 4 | 3.70 | 2.3× the cost; free tier spins down |
| Laptop (status quo) | $0 | $0 | 5 | 1 | 3 | 3 | 5 | 5 | 3.20 | Single point of failure; AI on a personal subscription that cannot be shared |
| SiteGround Cloud "Jump Start" (same account as the website) | $100 | $1,200 | 1 | 4 | 4 | 1 | 3 | 2 | 2.65 | No documented Python service runtime, no root/Docker; 8× Lightsail |
| SiteGround shared (GrowBig/GoGeek, already paid) | $0 extra | $0 | 5 | 3 | 3 | 1 | 3 | 1 | 2.55 | Cannot run the app: no Python web runtime ("No" to Django), 768 MB/process, proxies banned |

Rejected without scoring (research §1): EC2 (≈ 60% dearer than Lightsail for no benefit), Fargate + EFS (SQLite on network storage), App Runner (closed to new customers), Elastic Beanstalk and Lightsail Containers (no persistent disk), Hetzner US (repriced to $20+).

### A2. Linking the Hub to the existing WordPress site

The website and its DNS are on SiteGround (`ns1/ns2.siteground.net`, not Cloudflare). "Linked" can mean three things; each is costed.

| # | Way to link | Extra $/mo | Extra $/yr | Effort | Who must act | Drawbacks | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Subdomain `social.gitavalley.org`**: one A record in Site Tools → Domain → DNS Zone Editor → the Lightsail static IP; Caddy on the Hub box issues the certificate; a free Custom Link in the WordPress menu | **$0** | **$0** | ~15 min | SiteGround account holder (DNS) + WordPress editor (menu) | Separate login from WordPress (fine: the Hub's own login is the gate). Do **not** use Site Tools → Subdomains, which provisions a SiteGround-hosted site | **RECOMMENDED** |
| 2a | Folder path `gitavalley.org/social` proxied from SiteGround | — | — | Impossible | — | Apache `ProxyPass` has no `.htaccess` context; SiteGround documents no `mod_proxy`, bans proxies, and owns the nginx layer | REJECT |
| 2b | Folder path via Cloudflare Free + a Worker route | $0 (Workers Free 100k req/day; $5 if exceeded) | $0 | 1–2 dev days + a DNS-migration day | Domain registrant (move nameservers to Cloudflare), web admin (recreate every DNS/email record, SSL Full Strict), developer (rebase `/api` in 19 routers, Vite base, router basename, nginx, stored media URLs) | The **whole domain's DNS leaves SiteGround** (SiteGround CDN auto-disables), WordPress runs behind Cloudflare, a Worker sits in every request | NOT WORTH IT |
| 2c | Folder path via Cloudflare Origin Rules DNS override | Enterprise only | — | — | — | "Override DNS records" is Enterprise-only | REJECT |
| 2d | Folder path via Cloudflare Snippets | Pro $20–25 | $240–300 | as 2b | as 2b | Snippets unavailable on Free; still needs the DNS move and the refactor | REJECT |
| 3a | Host the Hub on the SiteGround shared plan | $0 | $0 | Impossible | — | No Python web-app runtime, resource caps, proxies banned (Node.js projects exist, but the Hub is Python) | REJECT |
| 3b | Host the Hub on SiteGround Cloud | +$100 | +$1,200 | Unsupported | Account owner | Still no root, no Docker, no documented Python service; 8× Lightsail | REJECT |
| 4a | iframe the Hub inside a private WordPress page | $0 | $0 | 1–2 h | Developer + WP editor | Blocked today by the Hub's `X-Frame-Options: SAMEORIGIN`; no security or usability gain | POINTLESS |
| 4b | Shared login: WordPress as an OpenID Connect provider | $0 (Automattic OpenID Connect Server plugin) or $89/yr (WP OAuth Server Personal) | $0–89 | 1–2 dev days + plugin upkeep | WP admin + developer | WordPress becomes a login dependency; the free plugin is small and last updated 2025-04. Named local Hub accounts (Phase 4) are the better step for 1–3 staff | DEFER |

**Answer to "can it be on gitavalley.org?":** yes, as `social.gitavalley.org`, at no extra cost, with a menu link from the site. Not as a folder on the main site, and not on the SiteGround account itself.

---

## 2. Matrix B — Hosting the scheduling engine (Postiz)

### B1. Weighted comparison

Weights: Cost 15% · Time to public posting 25% · Ops burden 15% · Publishing functionality 20% · Data/knowledge access 10% · Control and reversibility 15%. Costs assume the Hub already runs on a Lightsail box.

| Option | $/mo | $/yr | Cost | Time-to-public | Ops | Publishing | Data | Control | **Weighted** | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **Postiz Cloud, Standard** (5 channels, one shared login, API on all plans) | $29 | $348 | 3 | 5 | 5 | 4 | 5 | 3 | **4.20** | **RECOMMENDED** |
| Postiz Cloud, Team (10 channels, named seats) | $39 | $468 | 2 | 5 | 5 | 5 | 5 | 3 | 4.25 | Choose when named staff logins matter |
| Self-host on the Hub's box (upgrade Lightsail 2 GB → 4 GB) | +$12 | +$144 | 5 | 1 | 2 | 2 → 4 after reviews | 5 | 5 | 2.95 | Cheapest in dollars; weeks–months of private-only posting, three reviews, heavier box |
| Self-host on a separate VPS | $24–29 | $288–348 | 3 | 1 | 2 | 2 → 4 | 5 | 5 | 2.65 | Same as above at a higher price |
| Elestio managed Postiz | ≈ $18 | ≈ $216 | 4 | 1 | 4 | 2 → 4 | 5 | 4 | 2.95 | Managed updates/backups but still own apps and reviews; stack composition unverified |
| Stay on Seth's server | $0 | $0 | 5 | 1 | 1 | 1 | 5 | 1 | 2.00 | The problem being solved |

**Why "Data" is 5 for every row:** it does not discriminate. The Hub reads content and metrics through the temple's own apps whichever engine delivers posts (§0).

**Why self-hosting scores 1 on time and 2 on publishing today:** with our own apps, Facebook and Instagram posts from a Development-mode app are visible only to app role users until Meta's Business Verification and App Review pass (1–4 weeks); YouTube uploads are forced private until Google's compliance audit passes (no published timeline); TikTok posts are private-only until TikTok's content audit passes (no published timeline), and any later change to the app, including a new web address, triggers re-review. After all reviews pass, publishing functionality rises to 4 (equal to Cloud on capability, with unlimited channels and seats, but with annual Meta Data Use Checkup, 12-month YouTube audits and TikTok revisions as ongoing upkeep).

### B2. Data access, side by side (from the research, verified)

| Data | Own app, direct (Dev / unverified / Sandbox) | Postiz Cloud API | Self-hosted Postiz API | Self-hosted Postiz DB |
|---|---|---|---|---|
| Facebook posts + engagement | Full feed, reactions by type, shares, comment text; 2-year post insights; ~600 ranked posts/yr, 100/page | 4 snapshot numbers per Postiz-published post | Same 4 | Postiz-authored rows only; no metrics |
| Page insights | All `page_*` metrics incl. demographics; 90 days/query, 2-year history | 4 daily series over 7/30/90 d, cached 1 h | Same 4 | Not stored |
| Instagram media insights | Media list (10K cap); views, reach, saved, likes, comments, shares, interactions; account metrics | Per-post snapshot; follower count + reach over 7/30 d | Same | Not stored |
| YouTube analytics | Full Analytics API, history to channel start; video statistics; 10,000 units/day; no audit gate on reads | 6 daily series + 4 per-video counts | Same | Not stored |
| TikTok stats | Account counters + per-video view/like/comment/share for public videos; Sandbox works for ≤10 target accounts | 4 counters + 20 most-recent videos | Same | Not stored |
| Historical backfill depth | Platform-defined (above) | None: 7/30/90-day windows from the connection date | None | None |
| Raw database access | You design the store (`data/gvsa.db`) | No | No | Yes (tokens, posts, media) |
| Token ownership | Yes, minted by your app; Page token never expires | No | Yes, but with Postiz-chosen scopes | Yes |

---

## 3. Combined recommendation and what it costs

| | Monthly | Yearly |
|---|---|---|
| Hub on Lightsail 2 GB at social.gitavalley.org (+ snapshots) | $13 | $156 |
| AI writing on the temple's Anthropic account (capped at $25) | ≈ $5 | ≈ $60 |
| Postiz Cloud Standard | $29 | $348 |
| **Total, list price** | **≈ $47** | **≈ $565** |
| Total with the TechSoup AWS credit ($95/yr fee) | ≈ $34 | ≈ $500 |
| Alternative: self-host Postiz on the same box (4 GB) instead of Cloud | ≈ $30 | ≈ $360 (+ reviews, private-only posting until they pass) |

**Recommendation:** Hub on Lightsail at `social.gitavalley.org` (Matrix A row 1, linkage option 1); Postiz Cloud Standard for publishing (Matrix B row 1); the temple's own Meta, Google and TikTok apps kept for **reading**, in Development, unverified and Sandbox modes respectively, which already give full access to our own history and metrics. The $200/year that self-hosting Postiz would save buys, in exchange, public posting on day one and no platform paperwork, ever.

## 4. Work items that "maximum functionality" actually requires (all hosting-independent)

1. Fix the Postiz publish connector (decision brief, Appendix B) so per-post analytics can flow.
2. Re-run the Facebook history import for all 1,598 posts; set `META_INSTAGRAM_ACCOUNT_ID` and import the 825+ Instagram media; fix the `META_PAGE_ACCESS_TOKEN` / `META_PAGE_TOKEN` name mismatch.
3. Rewrite the insights backfill to current Graph API metrics (the `post_impressions*` family is deprecated above v25).
4. Add YouTube (Analytics + Data API) and TikTok (Display API, Sandbox now, approved Production later) importers.
5. Long-term TikTok reads: submit a **read-only** TikTok app review (Login Kit + Display API scopes, no Content Posting) whenever convenient; it does not block publishing, which goes through Postiz Cloud.
