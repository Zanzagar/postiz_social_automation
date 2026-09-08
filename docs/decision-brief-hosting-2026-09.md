# Where the Social Hub Should Live — Decision Brief for the Temple President

**Prepared by:** Corey Hoydic · **Date:** 2026-09-07 · **Decision needed by:** before the next social media publishing push
**Companion documents:** `docs/hub-hosting-plan.md` (hosting the hub itself), `docs/infrastructure-migration-plan.md` (the scheduling-engine runbook), `docs/research/postiz-hosting-migration.md`, `docs/research/platform-oauth-domain-requirements.md` (sources for every figure below).

---

## 1. The situation in plain terms

Gita Valley's social media hub is software we built ourselves. Staff write a sentence, the hub drafts a caption for each platform in the farm's voice, a person approves it, and the hub sends it to Facebook, Instagram, YouTube and TikTok. The hub keeps our content, photos, analytics and knowledge base on our own equipment.

There are two hosting questions, not one. First, **the hub itself currently runs on Corey's laptop**, which means it is available only when that laptop is on and effectively only to Corey, and its caption writing runs on Corey's personal Claude subscription, an arrangement Anthropic's terms do not allow us to share with other staff or run on a server. Second, the one piece we did not build is the **scheduling engine** that actually delivers posts to the platforms, an open-source product called **Postiz**. Since February it has run on a **volunteer's home computer and home internet connection**. We cannot reach that volunteer reliably, and the platform connections, secret keys and settings all live on his machine. Every publishing task is currently waiting on him. The engine must move.

## 2. Hosting the hub itself (recommended: yes, now)

| | **Move the hub to a small AWS server at social.gitavalley.org** | **Leave it on Corey's laptop** |
|---|---|---|
| Availability | Always on, reachable by any staff member from anywhere, with daily backups | Only when the laptop is on; effectively one user; no backups beyond Corey's own |
| Annual cost | **$144** hosting (AWS Lightsail 2 GB, $12/month) + about **$60** for AI writing on a temple-owned Anthropic account (≈ $5/month at planned volume, capped at $25/month) — hosting is effectively free under the TechSoup AWS credit ($1,000/year for a $95 fee) | $0, but not shareable and not sustainable |
| Work | About 3–4 working days: security hardening before the hub faces the internet, switching AI billing to the temple's account, deployment | None |
| Ownership | AWS and Anthropic accounts owned by the temple with Corey as administrator | Everything sits with one volunteer |

Nothing about the hub's features changes. The web address becomes https://social.gitavalley.org (one DNS entry on the existing gitavalley.org website account).

## 3. Two ways forward for the scheduling engine

| | **Option A: Subscribe to Postiz's hosted service** | **Option B: Rent a cloud server and run Postiz ourselves** |
|---|---|---|
| Annual cost | **$348** (Standard, one shared login) or **$468** (Team, individual staff logins) | **≈ $348** (server + backups); could fall to ≈ $95 if a nonprofit AWS credit is granted |
| Who maintains it | Postiz (updates, backups, security, uptime) | One volunteer (monthly security updates, backups, outages) |
| Platform approvals | **None needed.** Postiz's own Facebook, Instagram, YouTube and TikTok apps are already approved | **Three separate developer reviews** (Meta, Google/YouTube, TikTok), each with documents, demo videos and waiting periods, and renewals every year |
| First public post | **Within 1–2 days of approval** | Facebook/Instagram: after Meta business verification and review (1–4 weeks). YouTube: uploads are forced private until Google's audit passes (no published timeline). TikTok: posts are private-only until TikTok's audit passes (no published timeline) |
| What we control | Our hub, content, data and analytics stay ours. Postiz holds the platform connections and the delivery queue | Everything, including the server |
| Risk | Depends on a commercial service (switching back is a one-day job) | Depends on one person, the same situation we are in now |

## 4. What stays exactly the same under either option

Nothing about the hub changes for staff. We checked every point where the hub talks to the scheduling engine (five operations: list connected channels, publish or schedule a post, save a draft, attach a photo or video, read performance numbers) and all five are available on Postiz's hosted service, on every plan, with a **higher** request allowance than we have today. The caption writing, media library, knowledge base, content calendar, pillar analytics and Facebook history import do not involve the scheduling engine at all.

One honest note: while verifying this, we found that the hub's publishing connector had never been exercised against a live scheduling engine and needs a one-day correction before first use. That is true under either option and is already scheduled.

## 5. Recommendation

**Move the hub to AWS at social.gitavalley.org, and use Option A, Postiz hosted service, Standard plan.** Combined: about **$47/month ($565/year)** at list price, or about **$34/month plus a $95 TechSoup fee (≈ $500/year)** with the AWS credit. Upgrade Postiz to Team ($468/year) only if individual staff logins are wanted.

The problem we are solving is dependence on a single volunteer's equipment. Option B moves that dependence rather than removing it, and adds months of platform paperwork whose only purpose is to let us keep running the engine ourselves. Option A removes the dependence, removes the paperwork, costs the same, and can be reversed later if the service disappoints.

## 6. What we need from you

1. **Approval to subscribe:** $348/year (Standard) or $468/year (Team). Monthly billing is available at $29 or $39 if preferred.
2. **A shared organisational email** (for example `social@gitavalley.org`) to own the Postiz, AWS and Anthropic accounts, so none of them sits with one person.
3. **Approval for the hub's hosting:** AWS Lightsail at $12/month (and TechSoup registration, $95/year, which covers it) plus an Anthropic API account for the AI writing, about $5/month with a $25 cap.
4. **Which staff should post:** one shared login (Standard) or named logins per person (Team).
5. **Only if Option B (self-hosting the scheduling engine) is chosen:** the organisation's EIN and an official document showing its legal name and address (Meta business verification), and access to the website's SiteGround account for DNS changes.

## 7. What happens next

| When | What |
|---|---|
| Days 1–4 after approval | Harden the hub for the internet, switch AI billing to the temple's account, deploy to AWS at social.gitavalley.org |
| Day 5 | Create the Postiz account, connect the four channels, switch the hub to the new engine, publish a first post to each channel |
| Day 6 | Retire the volunteer's installation and the laptop services; rotate the secret keys they held |
| Week 1 | Resume the normal publishing rhythm from the hub |

---

## Appendix A (technical): functionality parity audit

Every hub capability, how it reaches Postiz today, and its status on Postiz Cloud. Verified 2026-09-07 against the Postiz public-API source (`v2.18.0` and `main`) and docs.

| Hub capability | Postiz call today | On Postiz Cloud | Change needed |
|---|---|---|---|
| Connected channels (Health page, publish routing) | `GET /integrations` | Same | None (integration ids change; the hub resolves them per call) |
| Publish now / schedule (auto-release loop, Publish modal) | `POST /posts` | Same; 100 req/hr vs 30 today | **Fix payload shape** (defect below) |
| Send draft to Postiz | `POST /posts` | Same | Same fix |
| Attach photo or video | `POST /media` (does not exist) | `POST /upload`; images 10 MB, video 1 GB | **Fix endpoint** and pass `{id, path}` in the post |
| Per-post performance | `GET /analytics/post/:id` | Same | None |
| Channel performance | `GET /analytics/:integration` | Same | None |
| "Open in Postiz" links | Instance URL | `platform.postiz.com` | Config only (`VITE_POSTIZ_URL`) |
| Facebook history import, insights backfill | Our own Meta app, Graph API (not Postiz) | Unchanged | None; app stays in Development mode for role users |
| Caption generation, media library, knowledge base, calendar, pillars, suggestions, analytics engine | No Postiz involvement | Unchanged | None |
| Per-platform post settings (TikTok privacy, YouTube title) | Not sent today | Same API (`settings.__type`) | Future work either way |

**What Cloud does not offer:** our own provider apps (unused), unlimited channels (5 on Standard, 10 on Team), choosing when to upgrade (Cloud updates continuously; our client uses only the stable public API v1), and a documented data export (Postiz holds channel tokens and the delivery queue; all content and analytics already live in our own database).

## Appendix B (technical): the publishing-connector defect

Live check on 2026-09-07 against the current instance, using a draft that was deleted immediately:

- The hub sends `{"content", "integrations": [id], "status": "draft|schedule|now", "media": [id]}` to `POST /posts` and uploads media to `POST /media`.
- Postiz answers **`400 Bad Request: "All posts must have an integration id"`**. The public API expects `{"type": "draft|schedule|now", "date", "shortLink", "tags", "posts": [{"integration": {"id"}, "value": [{"content", "image": [{"id","path"}]}], "settings": {"__type": "<provider>"}}]}` and returns `[{"postId", "integration"}]`; uploads go to `POST /upload` (returns `{id, path}`). The documented shape returned **201**.
- No content row has ever stored a Postiz post id; the July "publish round-trip" work was verified with mocked tests only. The shape dates from the MVP commit.
- Fix: rewrite `publish_post` / `create_draft_post` / `upload_media` in `src/content_engine/postiz.py` to the documented contract, parse `postId` from the response, add per-platform `settings.__type`, update tests to the real contract, and live-verify with a draft. Estimated one day. Required before any real publish, on any host.

## Appendix C: why the project did not choose the hosted service in February

The February 2026 assessment (`docs/social-media-automation-assessment.md`) chose self-hosting for three reasons: cost ($10–25/month for a server versus $29–39/month hosted), data ownership, and a volunteer's offer to host for free. It did not anticipate two things that have since dominated the project: the developer-review burden that comes with running our own platform apps, and the fragility of volunteer-run infrastructure. Its hosted-plan facts are also outdated (the Standard plan no longer caps posts per month). The reasoning was sound for the information available; the information has changed.
