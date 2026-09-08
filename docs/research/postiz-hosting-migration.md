# Postiz Cloud Hosting Migration — Research

Date: 2026-09-07 (all URLs fetched 2026-09-07/08 UTC)
Sources: docs.postiz.com, github.com/gitroomhq/postiz-app, github.com/gitroomhq/postiz-docker-compose, postiz.com/pricing, provider pricing pages/APIs (Hetzner, DigitalOcean, Vultr, Akamai/Linode, AWS Lightsail, Oracle), elest.io, railway.com, repocloud.io, pikapods.com, coolify.io, dokploy.com, developers.cloudflare.com, caddyserver.com, TechSoup, Google/Meta/TikTok developer docs. Local verification: `docker manifest inspect`, `gh release view`, `gh search code`.

Question: how should Gita Valley move Postiz off the volunteer box at `postiz.sethpc.xyz` (v2.18.0, docker compose: Postiz + PostgreSQL + Redis + Temporal + Temporal-Elasticsearch) to something reliable and low-ops, given 3–4 channels, a few posts/week, 1–3 staff users, our own Meta/Google/TikTok developer apps, and a FastAPI app that talks to `/api/public/v1`?

## TL;DR

| | Verdict |
|---|---|
| **Recommendation** | **Self-host the official compose on a 4 GB US-East x86 VPS behind Caddy at `social.gitavalley.org`** — DigitalOcean Basic 4 GB (NYC, $24/mo + $4.80 weekly backups) or, if the TechSoup AWS credit is secured, AWS Lightsail 4 GB ($24/mo, covered by the $1,000/yr credit for a $95 admin fee). Keeps our own platform apps, unlimited channels/users, our data, and the FastAPI integration unchanged. Ops = `docker compose pull && docker compose up -d` monthly + provider backups. |
| **Runner-up** | **Postiz Cloud, Team plan ($39/mo)** — zero ops, Public API on every plan, and channels connect through Postiz's already-registered platform apps, so *no Meta/TikTok/Google App Reviews would be needed for posting*. Costs about the same as a VPS but you give up data control, team seats below $39, and the own-app work already done. |
| **Do not** | Oracle Always Free (now 2 OCPU/12 GB, idle instances reclaimed, no capacity promise); Hetzner US (no longer cheap: CPX11 2 GB ≈ $21/mo, CX/CAX ARM plans are EU-only); Coolify's one-click Postiz (template pinned to v2.10.1, no Temporal). |
| **Migration path** | No official export/import. With 4 channels, a **fresh install + reconnect channels + new API key + re-invite users** is the practical path (~1 hour). Pick the final domain **before** submitting the Meta/TikTok/Google reviews — all three treat redirect URIs as review-relevant settings. |

## 1. Postiz self-host requirements (v2.23.0)

### Latest version and upgrade mechanics

- Latest release: **v2.23.0, published 2026-08-04** ("Streamed media uploads, duplicate-post protection & MCP fixes") — verified with `gh release view --repo gitroomhq/postiz-app` and https://github.com/gitroomhq/postiz-app/releases. Our box runs v2.18.0; there were four security releases between (v2.21.5–v2.21.10, Apr–Jun 2026: GHSA-34w8-5j2v-h6ww, GHSA-44wg-r34q-hvfx, PSA-2026-T0E4W0, PSA-2026-NWZN9J) — https://github.com/gitroomhq/postiz-app/releases. **Whatever host we choose must make updates cheap.**
- The official compose uses `ghcr.io/gitroomhq/postiz-app:latest` (https://raw.githubusercontent.com/gitroomhq/postiz-docker-compose/main/docker-compose.yaml). The container's start command runs `prisma db push` before launching (`"pm2-run": "pm2 delete all || true && pnpm run prisma-db-push && ..."` in https://raw.githubusercontent.com/gitroomhq/postiz-app/main/package.json), so schema changes apply on boot; an upgrade is `docker compose pull && docker compose up -d`.
- Docs: "Always pull the file from the repository rather than copying a snapshot. The services, images, and environment variables change between releases" and "When you change variables, you must run `docker compose down` and then `docker compose up`" — https://docs.postiz.com/installation/docker-compose.
- License AGPL-3.0; README: "At the moment, there is no difference between the hosted version and the self-hosted version" — https://github.com/gitroomhq/postiz-app.

### Required services

| Service | Required? | Source |
|---|---|---|
| PostgreSQL 14+ | Yes | https://docs.postiz.com/self-host/installation/system-requirements |
| Redis 6+ | Yes ("queues, rate limiting, and short-lived caches") | same; https://docs.postiz.com/configuration/reference |
| Temporal | **Yes — "bundled with Docker Compose; required since v2.12.0"** | https://docs.postiz.com/self-host/installation/system-requirements; migration guide https://docs.postiz.com/installation/migration |
| Elasticsearch | **Not listed as a Postiz requirement.** It ships in the official compose only as Temporal's visibility store (`ENABLE_ES=true`, `elasticsearch:7.17.27`, `ES_JAVA_OPTS=-Xms256m -Xmx256m`) | official compose (URL above); Temporal supports PostgreSQL as the visibility store and `auto-setup` creates the SQL visibility DB when `ENABLE_ES=false` — https://docs.temporal.io/self-hosted-guide/visibility, https://raw.githubusercontent.com/temporalio/docker-builds/main/docker/auto-setup.sh |
| Object storage | Optional (local filesystem default, or Cloudflare R2) | https://docs.postiz.com/configuration/uploads |

Official compose services (9): `postiz`, `postiz-postgres` (postgres:17-alpine), `postiz-redis` (redis:7.2), `temporal` (temporalio/auto-setup:1.28.1), `temporal-postgresql` (postgres:16), `temporal-elasticsearch` (7.17.27), `temporal-ui` (2.34.0), `temporal-admin-tools`, `spotlight` (optional debug). Our repo's `docker-compose.yaml` mirrors this. Dropping Elasticsearch (set `ENABLE_ES=false`, remove the ES service and `depends_on`) is technically supported by Temporal but is a deviation from the compose Postiz tells you to pull verbatim — treat as an unsupported memory optimisation, unnecessary on a 4 GB box.

Architecture: one container runs Frontend + Backend + Orchestrator; the orchestrator "Runs Temporal workflows and activities, replacing the old cron and worker services"; Redis is "session state management and caching" — https://docs.postiz.com/self-host/architecture. The backend "embeds a Temporal worker. It needs a long-running Node host… serverless functions won't work" — https://docs.postiz.com/self-host/troubleshooting.

### Sizing

| Source | Figure |
|---|---|
| System requirements | Minimum **2 vCPU / 2 GB ("all-in-one, light use") / 20 GB**; recommended 4 vCPU / 8 GB / 50 GB + persistent uploads volume — https://docs.postiz.com/self-host/installation/system-requirements |
| Docker Compose page | "tested on: Virtual Machine, Ubuntu 24.04, 2Gb RAM, 2 vCPUs" — https://docs.postiz.com/installation/docker-compose |
| Issue #1570 (open, 2026-05-29) | Idle with 8 integrations: Postiz ~27 % CPU / 672 MiB, Temporal ~31 % CPU, Temporal-ES ~330 MiB, Postgres ~18 % CPU; cause: 32 provider workers auto-start regardless of configured providers — https://github.com/gitroomhq/postiz-app/issues/1570 |

Verdict: ~1.5 GB resident at idle plus JVM/Node headroom → **4 GB RAM / 2 vCPU is the practical floor for a reliable install**; 2 GB works but has no headroom for an ES heap bump or an image pull.

### Environment variables (from https://docs.postiz.com/configuration/reference)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL`, `REDIS_URL` | Yes | Postgres (Prisma) / Redis connection strings |
| `JWT_SECRET` | Yes | "A long random string used to sign session JWTs". Also keys the AES-256-CBC `fixedEncryption` used for the org **Public API key** and custom-credential provider secrets (see §6) |
| `FRONTEND_URL` | Yes | "The URL the browser uses to reach the Postiz frontend" — must "exactly match the URL you use in the browser, protocol and port included" (https://docs.postiz.com/self-host/troubleshooting) |
| `NEXT_PUBLIC_BACKEND_URL` | Yes | Browser → backend URL; pattern `https://<host>/api` (https://docs.postiz.com/self-host/reverse-proxies/caddy) |
| `BACKEND_INTERNAL_URL` | Yes | SSR → backend inside the network |
| `MAIN_URL` | No | Absolute links in emails/SEO; also added to the CORS allowlist |
| `TEMPORAL_ADDRESS` / `TEMPORAL_NAMESPACE` / `TEMPORAL_API_KEY` / `TEMPORAL_TLS` | No (defaults) | `TEMPORAL_API_KEY` only for Temporal Cloud |
| `STORAGE_PROVIDER` | No | `local` (default) or `cloudflare`; plus `UPLOAD_DIRECTORY`, `NEXT_PUBLIC_UPLOAD_STATIC_DIRECTORY` or the six `CLOUDFLARE_*` R2 vars |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | per provider | One Meta app serves Facebook Page + Instagram (https://docs.postiz.com/providers/facebook) |
| `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` | per provider | Needs YouTube Data v3 + Analytics + Reporting APIs enabled (https://docs.postiz.com/providers/youtube) |
| `TIKTOK_CLIENT_ID` / `TIKTOK_CLIENT_SECRET` | per provider | Docs use `TIKTOK_CLIENT_ID` (not `_KEY`) — https://docs.postiz.com/providers/tiktok |
| `DISABLE_REGISTRATION` | No | Set `true` after the first signup |
| `API_LIMIT` | No | "Per-hour limit on the public-API create-post endpoint. Defaults to 90" (our v2.18 was 30/hr) |
| `NOT_SECURED` | No | "Dev only. Never set in production" |

Redirect URI pattern for every OAuth provider: `{FRONTEND_URL}/integrations/social/{provider}` — https://docs.postiz.com/self-host/providers/overview.

### HTTPS / reverse proxy

- "Postiz sets secure cookies, so it expects HTTPS in production. See Reverse proxies." — https://docs.postiz.com/installation
- TikTok: "will not allow http:// for your app redirect URI, so you will need to be accessing Postiz from HTTPS" and media "must be publicly reachable over HTTPS; localhost or private routes (e.g., /uploads) will fail" — https://docs.postiz.com/providers/tiktok. Google: "Redirect URIs must use the HTTPS scheme" — https://developers.google.com/identity/protocols/oauth2/web-server. Meta: HTTPS required for OAuth redirects — https://developers.facebook.com/docs/facebook-login/security/.
- Official guides: Caddy (https://docs.postiz.com/self-host/reverse-proxies/caddy), Nginx (https://docs.postiz.com/reverse-proxies/nginx), Traefik + Compose (https://docs.postiz.com/reverse-proxies/traefik). The image "bundles frontend and backend in one container exposed on port 5000 internally, requiring the reverse proxy to forward only one upstream" (nginx page). The official compose publishes it as host port **4007**.
- Uploads with `STORAGE_PROVIDER=local`: "Your local `/uploads` path must therefore be reachable from the public internet over HTTPS for those providers to work" (TikTok/Instagram pull-from-URL) — https://docs.postiz.com/configuration/uploads. R2 alternative documented at https://docs.postiz.com/self-host/configuration/r2 (docs call it "free"; no R2 pricing on the page). A related open self-host bug: Instagram "Media fetch failed" (9004/2207052) behind a correctly configured Caddy proxy, v2.21.6, unresolved — https://github.com/gitroomhq/postiz-app/issues/1472.

### ARM64

- Docs do not state supported architectures; issue #995 asking for arm64 was closed stale (opened 2025-09-27) — https://github.com/gitroomhq/postiz-app/issues/995.
- **Verified locally 2026-09-07:** `docker manifest inspect ghcr.io/gitroomhq/postiz-app:latest` and `:v2.23.0` list `linux/amd64` **and** `linux/arm64`; all sidecars (`temporalio/auto-setup:1.28.1`, `temporalio/ui:2.34.0`, `temporalio/admin-tools`, `elasticsearch:7.17.27`, `postgres:17-alpine`, `postgres:16`, `redis:7.2`) are multi-arch. So ARM (Oracle A1, Hetzner CAX) works today but is undocumented and unsupported.

### What state lives where (for backups)

From the Prisma schema (https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/database/prisma/schema.prisma):

| Store | Contents |
|---|---|
| Postiz PostgreSQL | `Organization` (incl. `apiKey`), `User`, `UserOrganization` (roles), `Integration` (`providerIdentifier`, `internalId`, `token`, `refreshToken`, `customInstanceDetails`), `Post` (`publishDate`, `content`), `Media` (`path`), `OAuthApp`, `Webhooks`, `Sets`, analytics/notifications |
| `postiz-uploads` volume | Uploaded media files (local storage) |
| `postiz-config` volume / env | `postiz.env` (all secrets and provider keys) |
| Temporal PostgreSQL + ES | Workflow state (scheduled publishing runs, token refresh). Treat as rebuildable; do not migrate |
| Redis | Sessions/cache — rebuildable |

There is no backup/restore page in the docs index (https://docs.postiz.com/llms.txt) and the "Backup/Restore. Moving to a new machine" issue was closed stale with no answer — https://github.com/gitroomhq/postiz-app/issues/1061. Backups = `pg_dump` of the Postiz DB + uploads volume + `postiz.env` (+ VPS snapshot).

## 2. Postiz Cloud as an alternative

Plans (https://postiz.com/pricing, https://docs.postiz.com/cloud/plans):

| Plan | Monthly | Yearly | Channels | Team members | Public API / CLI / MCP | AI credits |
|---|---|---|---|---|---|---|
| Standard | $29 | $278 | 5 | **No** | Yes | 20 images / 3 videos |
| Team | $39 | $374 | 10 | Yes (unlimited) | Yes | 100 / 10 |
| Pro | $49 | $470 | 30 | Yes | Yes | 300 / 30 |
| Ultimate | $99 | $950 | 100 | Yes | Yes | 500 / 60 |

- Posts per month "Unlimited" on all plans; "There is no free tier on cloud… new organisations are usually offered a 7 day trial" — https://docs.postiz.com/general/quickstart.
- **The decisive statement** — cloud vs self-hosted table: "Provider developer apps — *Already registered, just click connect*" (Cloud) vs "*You register each one and supply keys*" (Self-hosted); "Data location — Managed by Postiz" vs "Your infrastructure" — https://docs.postiz.com/cloud/overview. Quickstart: "Every platform is ready to connect" on cloud. Maintainer on self-host: "using Postiz in a self hosted Enviroment requires you to set up App IDs and Secret yourself" — https://github.com/gitroomhq/postiz-app/discussions/587. **On Cloud we would not need our own Meta business verification, TikTok audit, or Google OAuth verification to post.**
- Public API: cloud base `https://api.postiz.com/public/v1/`; rate limit "is a single global value for the whole instance. It does not tier by subscription plan" — https://docs.postiz.com/public-api/introduction. The docs disagree on the number: the API intro says 90/hr self-hosted, "100 for the cloud"; the limits page says "90 requests per hour on the create-post endpoint" — https://docs.postiz.com/cloud/limits. Either is 3× our current 30/hr. Media caps on cloud: images 10 MB, video 1 GB.
- Limitations found: (a) **no documentation that cloud lets you use your own provider apps** — unknown, assume no; (b) no data-export feature documented anywhere in the docs index; on cancellation "Your data stays… Publishing and API access stop" — https://docs.postiz.com/cloud/downgrades; (c) team members require Team plan or above — https://docs.postiz.com/general/settings/team; (d) data residency "Managed by Postiz" (region unspecified).

Verdict: a genuine option. For our 4 channels the Standard plan fits by channel count but has one login; with 1–3 staff we would need Team ($39/mo = $468/yr, or $374/yr prepaid). Price is comparable to a backed-up VPS; the trade is ops + App Reviews (Cloud wins) vs data control, seats, and reuse of our own apps (self-host wins).

## 3. Managed / one-click hosting

| Provider | What was verified | Price | Fit |
|---|---|---|---|
| **Elestio** (https://elest.io/open-source/postiz) | "Fully managed": automated backups (daily snapshots, remote Borg, optional S3), auto SSL, auto software + OS updates (schedulable, can be disabled), monitoring/alerts, custom domains — https://elest.io/open-source/postiz/resources/managed-service-features. Support Level 1 free (7-day backup retention, 3-day response), L2 $50/mo, L3 $200/mo — https://elest.io/pricing. Trial "$20 in credits… 3-day validity". Providers: Netcup, Hetzner, DigitalOcean, Vultr, Linode, Lightsail, Scaleway, AWS. | Postiz page: "Starting at $16/mo"; rendered plan table (default provider): **$18/mo for 2 CPU / 4 GB / 60 GB**, $33/mo for 4 CPU / 8 GB — https://elest.io/open-source/postiz/resources/plans-and-pricing | Best "managed self-host". **Unverified:** whether Elestio's Postiz stack includes Temporal/ES (their `elestio-examples/postiz` repo 404s; the install guide does not say). Ask before buying. Provider env vars still ours to set. |
| **Railway** (https://railway.com/pricing) | Hobby $5/mo incl. $5 usage; usage: RAM ≈ $10/GB-month, CPU ≈ $20/vCPU-month, volumes $0.15/GB-month, egress $0.05/GB. Template "Deploy Postiz (Temporal)" by Protemplate (not official): 7 services — Postiz (`latest`), Postgres, Redis, Temporal, Temporal UI, admin tools, Elasticsearch; 124 deploys — https://railway.com/deploy/postiz-temporal. Another template ("shinyduo", 482 deploys) is pinned to **v2.11.3 (pre-Temporal) — avoid** — https://railway.com/deploy/postiz. | Estimate at ~2–2.5 GB resident RAM + ~0.5 vCPU idle (issue #1570 numbers): **≈ $30–45/mo**; uncertain, usage-billed | Elastic pricing works against an always-on 7-container stack. Not cheaper than a VPS and less predictable. |
| **PikaPods** | Postiz **not offered**; open feature request — https://www.pikapods.com/apps, https://feedback.pikapods.com/posts/702/add-postiz | — | N/A |
| **RepoCloud** (https://repocloud.io/details/Postiz/) | "deploys via Docker Compose with PostgreSQL, Redis, and Temporal pre-wired"; tiers "$6.00/month max" (2 GB/1 vCPU/30 GB), "$9.00" (2 GB/2 vCPU), "$12.00" (4 GB/2 vCPU/40 GB); snapshots $0.10/GB-month; "free credit for your first 30 days" — https://repocloud.io/pricing | $12/mo for 4 GB | Cheapest managed-ish option, but datacenter locations, backup policy and update policy are not documented on the pages fetched. Treat as unproven for a reliability-first choice. |
| **Coolify** (self-managed PaaS) | Service page exists (https://coolify.io/docs/services/postiz) but the compose template is pinned to `ghcr.io/gitroomhq/postiz-app:v2.10.1` with **no Temporal** (last touched 2026-01-05) — https://github.com/coollabsio/coolify/blob/main/templates/compose/postiz.yaml | VPS cost | Stale one-click; you would paste the official compose yourself. Adds a control plane to maintain. |
| **Dokploy** (self-managed PaaS) | Template includes Postiz `latest`, Postgres 17, Redis, Temporal 1.28.1 + Elasticsearch 7.17.27 (Temporal added in PR #784) — https://raw.githubusercontent.com/Dokploy/templates/main/blueprints/postiz/docker-compose.yml, https://github.com/Dokploy/templates/pull/784 | VPS cost | Current, but same argument: an extra layer for a single app. |

## 4. VPS options for running the official compose

Prices are the providers' own pages/APIs; "Backups" is the provider's add-on. Region = nearest to Pennsylvania.

| Provider / plan | vCPU / RAM / disk | $/mo | Backups | US-East region | Arch | Notes |
|---|---|---|---|---|---|---|
| **DigitalOcean Basic 4 GB** | 2 / 4 GB / 80 GB, 4 TB transfer | **$24** | +20 % weekly ($4.80) or +30 % daily; snapshots $0.06/GB — https://www.digitalocean.com/pricing/droplets | NYC1/2/3 (https://docs.digitalocean.com/platform/regional-availability/) | x86 | 2 GB/1 vCPU is $12 |
| DigitalOcean Basic 2 GB | 1 / 2 GB / 50 GB | $12 | as above | NYC | x86 | Tight for Temporal + ES |
| **Vultr Cloud Compute** (`vc2-2c-4gb`) | 2 / 4 GB / 80 GB, 3 TB | **$20** | (pricing page blocked our fetch — 403 bot challenge) | `ewr` New Jersey, plus atl/ord/dfw/mia/sea/lax/sjc — https://api.vultr.com/v2/plans?type=vc2 | x86 | `vc2-1c-2gb` $10, `vc2-2c-2gb` $15 (same API) |
| **Akamai/Linode 4 GB** | 2 / 4 GB / 80 GB, 4 TB | **$24** ($0.036/hr) | Backups add-on $5/mo (2 GB: $2.50) — https://www.akamai.com/cloud/pricing/north-america | Newark NJ, Washington DC | x86 | 2 GB $12, Nanode 1 GB $5 |
| **AWS Lightsail 4 GB** (IPv4 bundle) | 2 / 4 GB / 80 GB, 4 TB | **$24** | Snapshots $0.05/GB-month — https://aws.amazon.com/lightsail/pricing/ | us-east-1 (N. Virginia) | x86 | 2 GB bundle $12; "As part of the AWS Free Tier, you can get started with Amazon Lightsail for free" (no duration stated on the page). Eligible for the AWS nonprofit credit below |
| **Hetzner Cloud US** (Ashburn `ash`, Hillsboro `hil`) | CPX11 2 / 2 GB / 40 GB; CPX21 3 / 4 GB / 80 GB; CPX31 4 / 8 GB / 160 GB | **€17.99 / €32.49 / €62.99** incl. IPv4 (price API: $20.49 / $37.49 / $73.49 + $0.60 IPv4 → **≈ $21.09 / $38.09 / $74.09**) — https://www.hetzner.com/cloud/regular-performance/, https://website-price-api.hetzner.com/api/v1/products/CLOUD_121 (…123, 125) | Snapshots/backups not checked | ash / hil — https://docs.hetzner.com/cloud/general/locations/ | x86 only in US | **Only CPX plans exist in US locations; US traffic 1 TB.** No longer a bargain vs DO/Vultr |
| Hetzner Cloud EU (Falkenstein/Nuremberg/Helsinki) | CX23 2 / 4 GB / 40 GB (x86); CAX11 2 / 4 GB / 40 GB (Ampere ARM) | **€5.99 ($7.09)** incl. IPv4 for CX23 — https://www.hetzner.com/cloud/cost-optimized/, https://website-price-api.hetzner.com/api/v1/views/cloud_matrix | — | **EU only** ("eu-central, NBG1, HEL1"); page flagged the tiers "currently unavailable" at fetch time | x86 or ARM | Cheapest reliable option if a German/Finnish server is acceptable (~90 ms from PA; irrelevant for a scheduler, OAuth callbacks don't care). ARM caveat: works (multi-arch images verified) but undocumented by Postiz |
| **Oracle Cloud Always Free** | Ampere A1: **"1,500 OCPU hours and 9,000 GB hours per month… equivalent to 2 OCPUs and 12 GB of memory"** (not the older 4/24); 2× AMD micro (1/8 OCPU, 1 GB); 200 GB block; 10 TB egress — https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm, confirmed on https://www.oracle.com/cloud/free/ ("Arm-based Ampere A1 cores and 12 GB of memory usable as 1 VM or 2 VMs") | $0 | none built in | Ashburn (us-ashburn-1) as home region | ARM | **Reclamation rule:** idle instances "may be reclaimed by Oracle" if over 7 days 95th-pct CPU < 20 %, network < 20 %, memory < 20 % — a few posts/week is exactly that profile. Must be in the tenancy's home region. Capacity for free A1 shapes is not promised anywhere on the page (the "Out of host capacity" problem is widely reported but is community knowledge, not a primary source) |

Nonprofit credits (primary sources):

- **AWS**: "The AWS Nonprofit Credit Program works with TechSoup… Organizations may request one grant of AWS Promotional Credit each fiscal year (July 1 to June 30)… valid for all on-demand services with pay-as-you-go pricing… valid for at least one year"; "Up to $5,000 USD", any budget size eligible — https://aws.amazon.com/government-education/nonprofits/nonprofit-credit-program/. (TechSoup search listings describe budget tiers — $1,000 under $10M, $2,000 for $10–50M, $5,000 above — but the tier pages themselves were unreachable.) TechSoup's offer for smaller orgs: **"$1,000 in AWS credits… Admin Fee $95… Valid for 12 months"** — https://page.techsoup.org/aws (the techsoup.org product/FAQ pages returned 403/empty to our fetch). $1,000 covers Lightsail 4 GB ($288/yr) plus snapshots with room to spare; effective hosting cost ≈ $95/yr while the grant is renewed annually.
- **Google**: Google for Nonprofits lists Workspace, Ad Grants, YouTube Nonprofit Program and Maps Platform credits — **no Google Cloud credit amount is published** — https://www.google.com/nonprofits/. The Cloud help article only says nonprofits can "Start building on Google Cloud with free credits and select free services (up to specific monthly limits)" with no figure or application path — https://support.google.com/nonprofits/answer/16245748; `cloud.google.com/nonprofits` 404s. Not a planning basis.

RAM vs plan: 2 GB plans (DO $12, Linode $12, Lightsail $12, Vultr $10) meet the documented minimum but leave no headroom; **4 GB plans ($20–24) are the sensible tier**; 8 GB is unnecessary at our volume.

## 5. Domain and TLS

- **Use `social.gitavalley.org`** (we control the zone; the domain is already the Meta app's privacy-policy host). Postiz docs' examples assume one hostname for UI + API: `MAIN_URL=https://<host>`, `FRONTEND_URL=https://<host>`, `NEXT_PUBLIC_BACKEND_URL=https://<host>/api` — https://docs.postiz.com/self-host/reverse-proxies/caddy. Keep frontend and backend on the same parent domain: "If `FRONTEND_URL` and `NEXT_PUBLIC_BACKEND_URL` resolve to different parent domains… the browser treats the backend cookie as third-party" — https://docs.postiz.com/self-host/troubleshooting. A provider subdomain (e.g. `*.elestio.app`, `*.up.railway.app`) works technically but means re-registering redirect URIs if we ever move again — one more reason to own the hostname from day one.
- **Caddy** (docs example uses `tls internal` for LAN; "If you are hosting on a public domain, Caddy allows you to use LetsEncrypt for automatic certificate management" — same page). With the official compose (host port 4007):

  ```caddyfile
  social.gitavalley.org {
          reverse_proxy localhost:4007
  }
  ```

  Caddy's Automatic HTTPS needs the A/AAAA record pointing at the server, ports 80 and 443 reachable, and a persistent data dir; it uses Let's Encrypt/ZeroSSL, renews automatically, and redirects HTTP→HTTPS — https://caddyserver.com/docs/automatic-https.
- **Cloudflare DNS** (if gitavalley.org's DNS is on Cloudflare — to be confirmed): simplest is a **DNS-only (grey-cloud) A record** so Caddy talks ACME directly; DNS-only "responds with your server's actual IP address and does not route HTTP/HTTPS traffic through its network" — https://developers.cloudflare.com/dns/proxy-status/. If proxied (orange cloud): set SSL mode **Full (strict)** (origin cert from Let's Encrypt or Cloudflare Origin CA); never Flexible (redirect loops — https://developers.cloudflare.com/ssl/troubleshooting/too-many-redirects/); Origin CA certs are only trusted via the proxy ("Site visitors may see untrusted certificate errors if you pause Cloudflare or disable proxying") — https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/. OAuth callbacks are ordinary HTTPS GETs and work in either mode; media fetches by Meta/TikTok also work through the proxy. Cloudflare's own OAuth troubleshooting is not covered in Postiz docs (the OAuth troubleshooting page addresses `Invalid state`, `invalid_grant`, `Failed to fetch` only — https://docs.postiz.com/general/troubleshooting/oauth-connect).

## 6. Migration mechanics

**No official export/import exists** (docs index has no backup/migration page other than the v2.12 Temporal migration; issue #1061 unanswered). Two viable paths:

### Path A — carry the database (keeps post history, analytics, media library)

1. Provision the new host, install Docker, clone `postiz-docker-compose`, write `postiz.env` with the **same `JWT_SECRET`**. Reason: the org's Public API key is written as `AuthService.fixedEncryption(makeId(20))` (AES-256-CBC keyed from `JWT_SECRET`) — https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/nestjs-libraries/src/database/prisma/organizations/organization.repository.ts, https://raw.githubusercontent.com/gitroomhq/postiz-app/main/libraries/helpers/src/auth/auth.service.ts — and sessions are signed with it ("Regenerating it invalidates every existing session" — https://docs.postiz.com/self-host/troubleshooting). Facebook/Instagram/YouTube/TikTok tokens are stored without that wrapper (verified with `gh search code fixedEncryption`), so they survive a secret change, but keep the secret anyway.
2. `pg_dump` the **Postiz** database (not Temporal's), `docker cp`/rsync the `postiz-uploads` volume, restore both on the new host, `docker compose up -d` (Prisma `db push` runs on boot and upgrades the schema from v2.18 to v2.23).
3. Uncertainty: scheduled posts are Temporal workflows on the old Temporal DB; the docs' own Temporal migration copies only Postiz Postgres and says nothing about pending schedules — https://docs.postiz.com/installation/migration. **Cut over with an empty calendar** (publish or delete anything pending), then verify with a test post.

### Path B — fresh install + reconnect (recommended at our scale)

What must be recreated: first-user signup → `DISABLE_REGISTRATION=true`; invite the 1–2 other staff (Settings → Team: roles User / Admin / Super Admin, invite link is time-limited — https://docs.postiz.com/general/settings/team); reconnect 4 channels via "Add Channel" (channel `id`s in `GET /integrations` change — our FastAPI caches them, so refresh); copy the new **Public API key** from Settings → Developers (keys "do not expire on their own"; rotate to revoke — https://docs.postiz.com/general/settings/developers) into the FastAPI env together with the new base URL; re-create any Sets/signatures/webhooks. Post history stays on the old box (export what matters first — our own SQLite already holds the content).

### Provider-app changes are the real coupling (do this BEFORE App Reviews)

| Platform | Rule | Consequence |
|---|---|---|
| Meta | "The full URI must be an exact match… Strict Mode… requiring an exact match from your Valid OAuth redirect URIs list"; App Domains lock which domains may perform login — https://developers.facebook.com/docs/facebook-login/security/ | Add `https://social.gitavalley.org/integrations/social/facebook` and `/instagram` to the Meta app (and the domain to App Domains) alongside the old sethpc URIs until cut-over. Whether this alone triggers a new review is not stated on the page — keep the domain stable before submitting |
| Google (YouTube) | "If you make any modifications to your app's name, logo/icon, **redirect URI**, homepage link, or privacy policy link displayed on your OAuth consent screen, your app will be required to complete brand verification again" — https://support.google.com/cloud/answer/13464018; redirect URI must match exactly and use HTTPS — https://developers.google.com/identity/protocols/oauth2/web-server | Change the redirect URI *before* seeking verification; our client is currently unverified so nothing is lost by changing now |
| TikTok | "Once your app is approved and live, any subsequent changes must be submitted for review and approved to appear in the live release" — https://developers.tiktok.com/doc/getting-started-create-an-app | Our app is still in sandbox — set the final redirect URI now, before Seth swaps keys and before submission |

## 7. Comparison

| Option | $/mo (est.) | Ops burden | Backups | Reliability | Arch | Own apps / App Review | Fit |
|---|---|---|---|---|---|---|---|
| **DigitalOcean 4 GB + weekly backups, official compose, Caddy** | ~$29 | Low-moderate: monthly `compose pull`, watch releases; Docker-literate maintainer suffices | Provider backups + `pg_dump` | High (NYC, x86, standard Docker) | x86 | Own apps; reviews needed (in progress) | **Recommended** |
| **AWS Lightsail 4 GB + TechSoup credit** | $24 list → ~$8 effective ($95/yr fee) | Same as DO; plus annual TechSoup renewal | Snapshots $0.05/GB | High (us-east-1) | x86 | Own apps | **Recommended if the credit is secured**; same ops model |
| Vultr / Linode 4 GB | $20–29 | Same | Linode add-on $5; Vultr unverified | High (NJ) | x86 | Own apps | Equivalent alternates |
| **Postiz Cloud Team** | $39 ($31/mo prepaid) | None | Postiz-managed; no export | High (vendor SLA unpublished) | — | **Postiz's apps — no reviews needed**; API on all plans | **Runner-up**; Standard $29 if one shared login is acceptable |
| Elestio managed Postiz | ~$18–25 | Very low (auto backup/update/SSL) | Daily, 7-day retention on free support | Good, but Temporal-currency of their stack unverified | x86 | Own apps | Attractive; verify stack first |
| RepoCloud 4 GB | $12 | Low, undocumented | Snapshots $0.10/GB; policy unknown | Unknown location/SLA | ? | Own apps | Budget only |
| Railway (Temporal template) | ~$30–45, usage-billed | Low | Volumes; no managed DB backups verified | Good | x86 | Own apps | Not cheaper, less predictable |
| Hetzner EU CX23 | $7 | Same as DO | Not checked | High, but EU location | x86 (or ARM CAX11) | Own apps | Cheapest credible; only if EU is acceptable |
| Hetzner US CPX21 | ~$38 | Same | — | High | x86 | Own apps | Overpriced now |
| Oracle Always Free A1 | $0 | Moderate + reclamation risk | None built in | **Low for our idle profile** | ARM | Own apps | Sandbox only |
| Coolify/Dokploy on a VPS | VPS cost | Higher (control plane + app) | Depends | Good | x86/ARM | Own apps | Unneeded layer for one app |
| Stay on sethpc.xyz | $0 | On Seth; single volunteer, home uplink | Unknown | The problem we are solving | x86 | Own apps | Baseline |

## 8. Recommendation

**Primary: self-host the official compose on a 4 GB x86 US-East VPS at `social.gitavalley.org`.** Concretely: DigitalOcean Basic 4 GB in NYC3 with weekly backups (~$29/mo), or AWS Lightsail 4 GB in us-east-1 if the TechSoup $1,000 AWS credit ($95 admin fee) is approved — same ops model, near-zero hosting bill. Reasons:

1. It preserves everything already built: our own Meta/Google/TikTok apps (Facebook, Instagram and YouTube already connected; first real publish pending the Meta E2E dry run), the FastAPI integration (only `POSTIZ_BASE_URL` and the API key change), unlimited channels and team seats, and our data on our infrastructure — the docs' own self-hosted column (https://docs.postiz.com/cloud/overview).
2. Reliability at this size is about the host, not the app: a datacenter VPS with provider backups and a 4 GB box (2× the documented minimum) removes the home-server failure modes; x86 avoids the undocumented-ARM path.
3. Ops burden is bounded and matches the maintainer's skills: Caddy gives automatic HTTPS; upgrades are `docker compose pull && docker compose up -d` with Prisma syncing on boot; the release cadence (four security patches in Q2 2026) means a monthly 10-minute routine, which is the main cost of self-hosting.
4. Price is not the differentiator — a backed-up VPS and Postiz Cloud both land at ~$29–39/mo — so the choice reduces to control + reuse of prior work (VPS) versus zero ops + no App Reviews (Cloud).

**Runner-up: Postiz Cloud, Team plan ($39/mo; Standard $29 if one shared login is tolerable).** Choose it if the App Reviews stall (Meta business verification, TikTok audit) or if nobody wants to own a server: channels connect through Postiz's already-registered apps, the Public API is on every plan, and our FastAPI needs only a base-URL/key change. Costs: no data export, team seats gated to $39+, data location "Managed by Postiz". Switching between the two later is cheap (reconnect 4 channels, new key), so the decision is reversible.

**Sequence that avoids re-doing reviews:** provision the VPS and DNS → point the Meta, Google and TikTok apps at `https://social.gitavalley.org/integrations/social/…` → reconnect channels and run the Meta E2E dry run on the new host → *then* record the App Review screencasts and submit. Decommission sethpc once a test post has published from each channel.

## Open items / uncertainty

- Elestio: whether its Postiz stack bundles Temporal (+ES) is unverified (example repo 404). Ask support before choosing it.
- Hetzner cost-optimized/CAX tiers showed "currently unavailable" on the page at fetch time; prices came from the site's price API (`website-price-api.hetzner.com`), USD/EUR both listed there.
- Vultr's pricing page blocks automated fetches (403); prices above are from the public `api.vultr.com/v2/plans` endpoint, which does not itemise IPv4 or backup add-ons.
- Google Cloud nonprofit credits: no primary page states an amount; treat as unavailable for planning. TechSoup's own AWS product/FAQ pages returned 403/empty; the $1,000/$95 figures are from `page.techsoup.org/aws`.
- Whether pending scheduled posts survive a Path-A DB move without the Temporal DB is undocumented; plan the cut-over with an empty calendar.
- Whether Postiz Cloud permits bring-your-own provider apps is not documented; assume not.
- Whether gitavalley.org DNS is on Cloudflare (affects §5) — check with the WordPress host.
