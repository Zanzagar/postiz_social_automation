# Hosting the Content Hub at social.gitavalley.org — Plan

**Date:** 2026-09-07 · **Status:** DECISION NEEDED (§2) · **Owner:** Corey
**Research behind this plan:** `docs/research/hub-hosting-aws-vps.md` (AWS/VPS options, DNS, TLS, access control, prices) and `docs/research/claude-on-server-options.md` (Anthropic terms, sanctioned auth, API pricing, cost model). Both were adversarially re-verified against primary sources on 2026-09-07. Companion: `docs/infrastructure-migration-plan.md` (the scheduling-engine move) and `docs/decision-brief-hosting-2026-09.md` (the president's brief).

---

## 0. What the Hub is today, in hosting terms

The Hub runs on Corey's laptop: a FastAPI backend under systemd (port 8000, Python 3.11 venv, ~124 MB RSS), a React SPA in a docker nginx container (port 3000, proxies `/api` and `/media` to the host), a **1.3 MB SQLite database** (`data/gvsa.db`, 26 tables incl. FTS5), **22 MB of local media** (originals, thumbnails, adapted crops; 564 MB more lives in Google Drive), a Drive service-account key, and two background loops inside the backend process (30-second auto-publish, content scheduler). Nothing in the code is Windows/WSL-specific.

**The one true host dependency is AI generation.** Every AI feature (caption generation, iterate, knowledge "Ask", pillar classification, calendar plan, media alt-text) shells out to the Claude Code CLI (`claude -p … --model sonnet`), authenticated by **Corey's personal Claude Max subscription login**, which is why generation costs $0 today and why the code comments say the backend "must run on the host."

## 1. Findings that decide the shape

1. **Hosting the Hub itself is easy and cheap.** It needs a small always-on Linux box with a persistent disk (SQLite + media + long-running loops rule out serverless). AWS Lightsail 2 GB in us-east-1 is **$12/month** (2 vCPU, 60 GB SSD, static IP included, 3 TB transfer) plus ~$1/month for daily snapshots and cents for S3 backups. Under the **TechSoup AWS credit** ($1,000/year for a $95 admin fee) the hosting bill is effectively covered. Runner-up: DigitalOcean 2 GB + weekly backups, $14.40. Rejected: EC2 (≈60% dearer for no benefit), Fargate/EFS (SQLite-on-NFS risk, $40+), App Runner (closed to new customers), Elastic Beanstalk and Lightsail Containers (no persistent disk), Hetzner US (repriced to $20+).
2. **`social.gitavalley.org` is one DNS record.** An A record in SiteGround's DNS Zone Editor pointing at the Lightsail static IP; Caddy on the box obtains and renews the certificate automatically; open port 443 in the Lightsail firewall (base images open only 22 and 80). The $18/month Lightsail load balancer is unnecessary.
3. **The AI cannot move on the Max subscription.** Anthropic's Consumer Terms forbid making an account available to anyone else and forbid automated access except through an API key; the Claude Code legal page says OAuth is "intended exclusively for purchasers of … subscription plans" for their ordinary use, that developers building products must use API keys, and that routing requests "through Free, Pro, or Max plan credentials on behalf of their users" is not permitted; the June-2026 help article says "Teams running shared production automation should use Claude Platform with an API key." A `claude setup-token` long-lived token is likewise bound to one subscriber. Verdict: **the server must use an Anthropic Console organisation owned by the temple, with an API key.** Corey keeps his Max subscription for his own interactive work.
4. **The API is cheap at our volume.** Measured prompts are ~5,300 characters; planned volume is ~20 posts/month, ~100–250 calls/month. On Claude Sonnet 5 ($2/$10 per million tokens, verified 2026-09-07) that is **≈ $2–9/month** (mid case $4.73 with prompt caching). Opus 5 ≈ $5–22; Haiku 4.5 ≈ $1–4. No Anthropic API discount for nonprofits exists (Claude for Nonprofits discounts *seats*, not API). Set a Console spend limit of $25/month.
5. **Two ways to switch the AI, both fine:**
   - **(a) Keep the CLI, authenticate with an API key** — install Claude Code on the server, set `ANTHROPIC_API_KEY`, add `--bare` (documented as the mode for scripted use; never reads OAuth) and a tool restriction to every `claude -p` call, pin model IDs. **1–2 hours.** Costs ≈ $1.65–9/month *more* than the direct API because the CLI prepends ~18,600 harness tokens per call (measured).
   - **(b) Replace the subprocess with the Anthropic Python SDK** — one chokepoint helper (`generator.py:_call_claude`) plus six sibling helpers; add `cache_control` on the stable brand/knowledge prefix; Sonnet 5 for generation, Haiku 4.5 for classification. **About one day.** Also the only way to fix the media alt-text feature, which today invokes `claude -p --image`, a flag that does not exist, so alt-text generation has always failed silently.
   Recommendation: (b) as the destination; (a) is an acceptable stopgap if the move must happen first.
6. **The Hub must be hardened before it faces the internet.** Verified on the running instance: `/docs`, `/openapi.json`, every file under `/media/**`, and the Google Drive file proxy are reachable **without login**; the login lockout is keyed on the socket IP (behind a proxy every visitor shares one IP, so an attacker can lock out staff); the JWT sits in localStorage with no refresh; uvicorn listens on all interfaces. Also latent: the calendar-plan route blocks the event loop for up to 120 s, and the Postiz publish payload defect (see the decision brief, Appendix B).

## 2. Decision

| | **A. Hub on AWS Lightsail at social.gitavalley.org** (recommended) | **B. Hub stays on Corey's laptop** |
|---|---|---|
| Availability | Datacenter, always on, reachable by any staff member from anywhere | Only when the laptop is on, on the office/home network; single point of failure (the same problem as Seth's box) |
| Cost | $12/month hosting (+~$1 snapshots) + **≈ $5/month AI** on the temple's own Anthropic account; hosting ≈ $0 under TechSoup | $0 hosting; AI free on Corey's subscription, but that arrangement cannot be shared with other staff |
| Who can use it | Any staff with the password (named accounts in Phase 4) | Effectively Corey |
| Work to get there | ~3–4 working days: hardening (§4), AI switch (§1.5), deploy (§3) | None |
| Pairs with | Postiz Cloud (recommended) → total ≈ **$47/month list, ≈ $34/month + $95/yr with TechSoup**; or self-hosted Postiz on the same box (Lightsail 4 GB, $24) | — |

**Recommendation: A.** The Hub is the organisation's tool; it should live on infrastructure the organisation owns, under accounts the organisation owns (AWS, Anthropic Console, Postiz), with Corey as an administrator rather than the host.

## 3. Deployment shape

- **Box:** Lightsail 2 GB Linux (Ubuntu 24.04) in us-east-1, static IP, automatic daily snapshots on. (4 GB if Postiz is self-hosted on the same box.)
- **DNS:** `social.gitavalley.org` → A record at SiteGround → Lightsail static IP.
- **Edge:** Caddy on 80/443 with automatic HTTPS; reverse-proxies to nginx (SPA) which proxies `/api` and `/media` to the backend on 127.0.0.1:8000. Lightsail firewall: 443 open, 80 open (for ACME/redirect), 22 restricted to Corey's IP or closed in favour of Tailscale for admin access.
- **Backend:** systemd unit under a dedicated `gvsa` user, `EnvironmentFile=/etc/gvsa/gvsa.env`, `ExecStart` binds 127.0.0.1:8000 with `--proxy-headers`, `ExecStartPre=alembic upgrade head`, exactly **one** worker (the in-process loops require it). Python venv rebuilt from `pyproject.toml` (add `pillow`; move `streamlit` to an optional extra; add `anthropic`).
- **Data:** `/opt/gvsa/data/gvsa.db` (copy the laptop file; enable WAL), `/opt/gvsa/media/` (copy), `/etc/gvsa/credentials.json` (0600). Drive keeps serving as the media repository.
- **Backups:** Lightsail daily snapshots (7 kept) + nightly `sqlite3 .backup` and `rsync` of media and `data/*.json` to an S3 bucket, 30-day retention. Restore drill once.
- **Monitoring:** UptimeRobot (free) on `https://social.gitavalley.org/health`; Lightsail CPU/disk alarms.
- **Ops:** ~1–2 hours/month (OS updates, `git pull` + restart, check backups).

## 4. Hardening checklist (before DNS goes live)

1. Require auth on `/media/**` and the Drive file proxy (short-lived signed URL for `<img>`/`<video>` tags); restrict the Drive proxy to catalogued file IDs; stop echoing exception text.
2. Disable `/docs`, `/redoc`, `/openapi.json` in production (`docs_enabled` setting).
3. Derive client IP from `X-Forwarded-For` only from the trusted proxy; persist lockout state in SQLite; strong random `API_PASSWORD`; rotate `JWT_SECRET`.
4. `CORS_ORIGINS=["https://social.gitavalley.org"]`; bind uvicorn to 127.0.0.1; delete the legacy Streamlit service.
5. Move the crawl and Meta-import background tasks to CLI scripts on systemd timers (known SQLite + event-loop gotcha).
6. Fix the calendar-plan route (run the model call off the event loop via the shared helper).
7. Fix the Postiz publish contract (decision brief, Appendix B) and live-verify with a draft.
8. Phase 4 follow-up: named user accounts and per-user audit (currently one shared password).

## 5. Code changes (one PR, ~2–3 days including tests)

| File | Change |
|---|---|
| `api/config.py`, `api/main.py` | Env-driven `cors_origins`, `media_dir`, `docs_enabled`; proxy-header handling; WAL + busy_timeout on the SQLite engine (`api/dependencies.py`) |
| `api/auth.py` | Forwarded-IP handling; SQLite-backed lockout |
| `api/routes/drive.py`, `/media` mount | Auth or signed URLs; restrict Drive proxy to catalogued IDs |
| `src/content_engine/generator.py` `_call_claude` + 6 sibling helpers, `src/content_engine/health.py` | Anthropic SDK client with `cache_control` (option b), or `--bare` + API key + tool restriction + pinned model IDs (option a); health check reads the API key instead of `claude auth status` |
| `api/routes/media.py` `_generate_media_meta` | Vision via SDK image block (replaces the non-existent `--image` flag) |
| `api/routes/calendar_plan.py` | Off-loop execution through the shared helper |
| `frontend/nginx.conf`, `Sidebar.tsx`, `BottomNav.tsx`, `frontend/Dockerfile` | Proxy target; `VITE_POSTIZ_URL` build arg |
| `pyproject.toml`, new `Dockerfile.backend` or `deploy/gvsa-backend.service`, `deploy/Caddyfile`, `deploy/hub.env.example`, `scripts/backup.sh` | Server packaging, env template, backups |
| `docs/DEPLOYMENT.md` | The runbook (provision → DNS → Caddy → env → data copy → alembic → first login → backups → update procedure) |

## 6. Migration steps (Hub)

1. Temple creates the accounts: **AWS** (new account, so the 90-day Lightsail trial and TechSoup credit apply), **Anthropic Console** organisation (API key, $25/month spend limit), and registers with **TechSoup** for the AWS credit. Corey is an admin on each; a shared org email owns them.
2. Land the hardening + AI-switch PR (§4, §5); run the full test suites; verify AI generation end-to-end with the API key locally.
3. Provision Lightsail 2 GB, attach static IP, enable snapshots; install Docker/Caddy/Python; create the `gvsa` user; deploy code, env, credentials.
4. Freeze the laptop copy; copy `data/gvsa.db`, `media/`, `data/*.json`; run `alembic upgrade head`; start services; smoke-test on the IP.
5. Add the SiteGround A record; confirm Caddy issues the certificate; hard-refresh; log in; run one caption generation and one publish (after the Postiz cut-over).
6. Turn on UptimeRobot and the backup timer; run a restore drill; retire the laptop services (stop `gvsa-backend`, remove the docker frontend).
7. Update docs and memory; hand the president the account inventory.

## 7. Open questions (only you can answer)

1. Proceed with the Hub move (A) now, in parallel with the Postiz decision?
2. Who will own the temple's AWS and Anthropic Console accounts (shared org email), and is the temple willing to register with TechSoup ($95/yr) for the AWS credit?
3. Admin access: Tailscale for the nonprofit (free tier is for individuals; request the nonprofit plan) or SSH restricted to Corey's IP?
4. AI switch: direct SDK (recommended, ~1 day) or CLI-with-API-key stopgap (1–2 h)?
