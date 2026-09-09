# Attaching the Content Hub to gitavalley.org (SiteGround WordPress) — Research

Date: 2026-09-08 (all URLs fetched 2026-09-08 local / 2026-09-09 01:xx UTC; every price and limit below was read from the provider's own page on that date — none from memory)
Sources: siteground.com/kb + siteground.com/cloud-hosting.htm + siteground.com/web-hosting.htm + siteground.com/blog (webinar Q&A, wildcard-SSL Q&A), developers.cloudflare.com (Workers pricing/limits/routes/fetch, Origin Rules, Snippets, DNS zone setups) + cloudflare.com/plans, httpd.apache.org (mod_proxy, rewrite flags), wordpress.org/documentation + developer.wordpress.org + make.wordpress.org, wordpress.org/plugins (openid-connect-server, oauth2-provider, miniorange-oauth-20-server), wp-oauth.com, plugins.miniorange.com, developer.mozilla.org, fly.io/docs, render.com (pricing, docs/disks, docs/free, docs/docker), railway.com/pricing + docs.railway.com, aws.amazon.com/lightsail/pricing, vite.dev, fastapi.tiangolo.com, caddyserver.com. Local verification: `frontend/nginx.conf`, `frontend/vite.config.ts`, `frontend/src/main.tsx`, `frontend/src/lib/api.ts`, `api/main.py`, `api/routes/*.py`, `api/auth.py`. Prior research this builds on: `docs/research/hub-hosting-aws-vps.md` (Lightsail 2 GB $12/mo verdict).

Question: the nonprofit's existing public site `gitavalley.org` is WordPress on SiteGround, and the domain's DNS is also at SiteGround (`ns1/ns2.siteground.net`, not Cloudflare). The Content Hub (FastAPI + React SPA behind nginx, one SQLite file, ~600 MB media directory, two in-process background loops, a Claude CLI/Node subprocess) needs a persistent disk, an always-on process, outbound HTTPS and its own HTTPS endpoint. How can it be "attached" to the WordPress site, what does each way cost beyond the Hub's own $12/mo Lightsail box, and what does each break?

## TL;DR

| Option | Extra cost | Verdict |
|---|---|---|
| **1. `social.gitavalley.org` → A record to the Lightsail static IP; Caddy does TLS; a Custom Link in the WordPress menu** | **$0** | **Do this.** One A record in Site Tools → Domain → DNS Zone Editor (SiteGround: "If you want to edit an A record so that part of your site points to another server, you need to know the IPv4 address of this server and insert it in the corresponding field"). Do **not** use Site Tools → Domain → Subdomains — that tool creates a hosted site with "their own document root folder" on SiteGround, and SiteGround's SSL Manager can only issue Let's Encrypt for names that resolve to SiteGround. |
| **2. `gitavalley.org/social` proxied to the Hub** | $0 on paper, but the whole domain's DNS must move to Cloudflare and the app must be refactored for a sub-path | **Not worth it.** SiteGround cannot do it (Apache's `ProxyPass` is not an `.htaccess` directive at all; SiteGround's KB documents no `mod_proxy`, states "Installation of proxies is not allowed", and the nginx layer in front of Apache is SiteGround-managed). Cloudflare Free can do it only with a **Worker on a route** after a **full nameserver move** (partial/CNAME setup is Business-plan-only, $200–250/mo); Origin Rules "Override DNS records" is **Enterprise-only**; Snippets are **not on Free**. Moving DNS auto-disables SiteGround CDN, forces re-creating every DNS/email record, and puts WordPress behind Cloudflare's proxy. The Hub hard-codes `/api` in 11 routers, `api.ts`, `nginx.conf`, uses `BrowserRouter` without a `basename`, and has no Vite `base` — all would change. |
| **3. Host the Hub on SiteGround** | Shared: $0 (already paid) but impossible; Cloud: **+$100/mo ($1,200/yr)** and still unsupported | **Reject.** Shared plans: Python 3.13 via SSH/CGI only, "No, you cannot do that on GoGeek plan" (Django), "Root SSH access, however, is not allowed", "up to 768MB RAM per process", CPU-second caps, cron "at least 30 minutes" apart, no daemon/Docker support documented. Cloud Jump Start ($100/mo, 4 cores/8 GB) is "fully managed", lists "WP-CLI and SSH" but not root or Docker, and the root-access KB explicitly covers "Shared/Cloud". 8× the price of Lightsail for a box that still can't run uvicorn as a service. |
| **4a. iframe of the subdomain in a private WordPress page** | $0 | **Pointless.** The Hub's nginx already sends `X-Frame-Options: SAMEORIGIN`, so `gitavalley.org` (a different origin) cannot frame `social.gitavalley.org` until that header is changed to CSP `frame-ancestors`; a WordPress "Private" page hides only the page, not the Hub URL; and the Hub's own login is still required inside the frame. |
| **4b. WordPress as the OIDC/OAuth identity provider** | $0 (Automattic's free "OpenID Connect Server" plugin) to $89–$500/yr (commercial plugins) + 1–2 dev days | **Defer.** For 1–3 staff, named accounts in the Hub's own DB are less work and one fewer dependency. If real SSO is wanted later, the free Automattic plugin + an OIDC client library in FastAPI is the path; note it shows only "100+" active installs and was last updated 2025-04-17. |
| **5. PaaS instead of Lightsail** | Fly.io ≈ $12.20/mo; Railway ≈ $12–18/mo (usage-billed, est.); Render Standard + disk $27.50/mo | Fly.io and Railway are viable equals; Render is 2× the price and its Starter (512 MB) is too small; Render Free spins down after 15 min idle and cannot attach a disk. All three run a Dockerfile (so the Node CLI subprocess is fine) and pin a volume to one instance (so SQLite is safe as long as you run exactly one). |

## 1. Option 1 — subdomain `social.gitavalley.org` → external server

### 1.1 SiteGround steps (Site Tools → Domain → DNS Zone Editor)

All from https://www.siteground.com/kb/manage-dns-records-site-tools (fetched 2026-09-08):

- "To add, edit or delete a DNS record, go to **Site Tools > Domain > DNS Zone Editor**."
- "In the Create New Record section, you can click the tab corresponding to the type of record you wish to create (it can be an A, AAAA, CNAME, MX, SRV or TXT record), then fill in the required information and click Create."
- "The A record specifies the IP addresses from IPv4 (internet protocol version 4) corresponding to your domain and its subdomains."
- "If you want to edit an A record so that part of your site points to another server, you need to know the IPv4 address of this server and insert it in the corresponding field."
- "In the required information for all record types, there is a drop-down menu called TTL (time to live)."
- Pre-condition, which gitavalley.org satisfies: "You can manage DNS records only if your domain is pointed to our name servers."

Concrete record: type **A**, Name `social` (→ `social.gitavalley.org`), Value = the Lightsail static IPv4, TTL default. The same steps are on the older KB page https://www.siteground.com/kb/manage-dns-records (fetched 2026-09-08), which carries the identical "part of your site points to another server" sentence. SiteGround's nameserver-change KB says "The new DNS settings will need several hours to propagate" (https://www.siteground.com/kb/how_to_change_my_ns_record) and its pointing tutorial says "up to 72 hours" (https://www.siteground.com/kb/point-domain-siteground); a single new A record with a short TTL is normally live in minutes.

### 1.2 Cost

None of the three SiteGround DNS pages mentions any fee for DNS records; DNS management is a Site Tools feature of the existing hosting plan (shared plans page: "Free SSL, CDN, Backups" bundled — https://www.siteground.com/web-hosting.htm, fetched 2026-09-08). **Extra cost: $0/mo.**

### 1.3 TLS — external server only, no SiteGround involvement

- Caddy on the Hub box: "Caddy serves public DNS names over HTTPS using certificates from a public ACME CA such as Let's Encrypt or ZeroSSL" and "Caddy keeps all managed certificates renewed and redirects HTTP (default port 80) to HTTPS (default port 443) automatically"; requirement: "If your domain's A/AAAA records point to your server, ports 80 and 443 are open externally, Caddy can bind to those ports … then sites will be served over HTTPS automatically" — https://caddyserver.com/docs/automatic-https (fetched 2026-09-08).
- SiteGround's SSL Manager is irrelevant here and could not help anyway: "If the www subdomain does not resolve, the certificate cannot be issued for it" — the Let's Encrypt issuance in Site Tools requires the name to resolve to SiteGround (https://www.siteground.com/kb/is-lets-encrypt-only-for-non-www-domain-names, fetched 2026-09-08). SiteGround's own answer to "Can a sub domain and wildcard SSL be applied to a local server or non siteground hosted server?" was "You can't install a LE certificate on your local server. As to other hosting accounts, yes you can but you need to contact them." (https://www.siteground.com/blog/free-lets-encrypt-wildcard-ssl, comment Q&A, fetched 2026-09-08). Nothing needs to be requested from SiteGround.

### 1.4 WordPress navigation link — free

- Classic/hybrid themes: Appearance → Menus. "In your menu, you can add different items such as links to pages, articles, categories, or custom links to the url of your choice, such as another site" … "**Open link in new tab** — Click the checkbox to open the menu item in a new tab" — https://wordpress.org/documentation/article/appearance-menus-screen/ (last modified 2026-07-28, fetched 2026-09-08).
- Block themes (WordPress 6.0+): the Navigation block. "If you select 'Add blocks' and add a block like Page Link or Custom Link, a pop-up will appear where you can search or enter the URL for the menu item, toggle the **Open in new tab** option" — https://wordpress.org/documentation/article/navigation-block/ (last modified 2026-05-25, fetched 2026-09-08).
- The Menus screen note: "In WordPress 6.0 and later, when using a block theme, navigation is managed via the Navigation block." Which of the two applies depends on the gitavalley.org theme (not checked here).

Because the Hub is a staff tool, the link is better placed in a footer/utility menu or an existing "Staff" page than the public primary navigation; that is a content decision, not a technical constraint.

### 1.5 Do NOT use Site Tools → Domain → Subdomains

- What that tool does: "To establish a new subdomain, navigate to **Site Tools > Domain > Subdomains > Create New Subdomain**. Enter your desired prefix in the Name field and click Create." … "After the subdomain is created, you can install a website installation for it" (WordPress/App Installer) — https://www.siteground.com/kb/subdomain (fetched 2026-09-08).
- It provisions a hosted site on SiteGround: "Additional sites you are hosting on your account, such as subdomains, have their own document root folder. Their respective website files need to be uploaded under the respective folder." — https://www.siteground.com/kb/upload-website-files (fetched 2026-09-08).
- Its SSL path is SiteGround-hosted only: "Secure your subdomains through **Site Tools > Security > SSL Manager**" (same KB) and, per 1.3, issuance requires the name to resolve to SiteGround.

So the Subdomains tool creates a SiteGround-hosted `social.gitavalley.org` whose files live on SiteGround — the opposite of what is wanted. The KB does not say whether the tool also writes an A record for the prefix into the DNS zone (SiteGround's DNS pages do not document it either way — **unverified**). Practical rule: create only the A record in DNS Zone Editor; if a `social` subdomain already exists under Domain → Subdomains, delete it and confirm no stale `social` A record pointing at SiteGround remains in the zone.

### 1.6 Drawbacks

- Separate origin from `gitavalley.org`: no shared WordPress login (see §4), separate cookie/storage scope (irrelevant today — the Hub uses a localStorage JWT, `frontend/src/lib/api.ts` lines 3–18, 43).
- The Hub is publicly reachable by URL; its own login (shared password, lockout, `api/auth.py`) is the gate. That is unchanged from any other hosting choice.

## 2. Option 2 — folder path `gitavalley.org/social` proxied to the Hub

### 2.1 Can SiteGround managed WordPress hosting do it? No.

| Evidence | Source (fetched 2026-09-08) |
|---|---|
| Apache: `ProxyPass` — "Context: server config, virtual host, directory" and "This directive is not supported within `<Directory>`, `<If>` and `<Files>` containers." No `.htaccess` context is listed, so `ProxyPass` cannot be placed in a customer `.htaccess` regardless of `AllowOverride`. | https://httpd.apache.org/docs/2.4/mod/mod_proxy.html |
| Apache: the `RewriteRule … [P]` alternative — "`mod_proxy` must be enabled in order to use this flag" (and carries an SSRF warning). | https://httpd.apache.org/docs/2.4/rewrite/flags.html |
| SiteGround `.htaccess`: "The AllowOverride directive in the Apache's configuration has been set to 'All' on all servers." The page lists `mod_rewrite`, ModSecurity filters and `AddHandler` examples only; **no mention of `mod_proxy`/`ProxyPass`**. It also warns: "The above works only if you disable the NGINX Direct Delivery for your website" — i.e. an nginx layer SiteGround controls sits in front of Apache. | https://www.siteground.com/kb/is_it_possible_to_set_apaches_allowoverride_directive_to_all/ |
| SiteGround policy: "Installation of proxies is not allowed neither by our security policy, nor by our Data Centers, where we host all of our production servers." | https://www.siteground.com/kb/do_you_allow_proxies_to_be_hosted |
| SiteGround architecture: nginx is the reverse proxy in front of Apache (SuperCacher/NGINX Direct Delivery), configured by SiteGround, not by customers. | https://www.siteground.com/blog/supercacher-nginx-ssl-support (secondary — blog) |

Verdict: there is no customer-configurable reverse-proxy on StartUp/GrowBig/GoGeek (or Cloud — same Site Tools, no root, §3). Whether `mod_proxy` happens to be loaded on SiteGround's Apache is undocumented; even if `[P]` worked, it would violate the proxies policy and be bypassed by NGINX Direct Delivery.

### 2.2 What it would take with Cloudflare instead

**Pre-condition: move the entire domain's DNS to Cloudflare (Free plan, $0).**

- Plans: "Free … $0 /month", "Pro … $20 /mo billed annually, or $25/mo billed monthly", "Business … $200 /mo billed annually, or $250/mo billed monthly" — https://www.cloudflare.com/plans/ (fetched 2026-09-08).
- Only a full setup is available on Free: "A CNAME setup (partial) is only available to customers on a Business or Enterprise plan." — https://developers.cloudflare.com/dns/zone-setups/partial-setup/. Full setup = "Remove your existing authoritative nameservers" / "Add the nameservers provided by Cloudflare" at the registrar, after "If your domain has DNSSEC active, you must turn it off at your registrar" — https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/ (fetched 2026-09-08).
- What that does to SiteGround services:
  - "You can manage DNS records only if your domain is pointed to our name servers." — SiteGround's DNS Zone Editor stops being the place to manage DNS (https://www.siteground.com/kb/manage-dns-records-site-tools).
  - "If you have activated the CDN and then change the domain's nameservers, the service will stop working and will be automatically disabled." — https://www.siteground.com/kb/manage-cdn (fetched 2026-09-08).
  - "When you change the name servers of a domain, all advanced records (A-records, CNAME-records, MX-records, SRV-records, and so on) will resolve from the DNS zone of the provider whose nameservers you are setting" … "it is strongly recommended to add them to the DNS zone of your new provider before switching the nameservers" — every record, including SiteGround email MX/SPF/DKIM, must be re-created at Cloudflare (https://www.siteground.com/kb/how_to_change_my_ns_record).
  - WordPress goes behind Cloudflare's proxy (routes require the record to be "proxied by Cloudflare (also known as orange-clouded)"): SiteGround then requires "If your website loads with HTTPS from the hosting side, set the SSL Support to Full (Strict)" — "Having the wrong mode set will cause the 'ERR_TOO_MANY_REDIRECTS'" (https://www.siteground.com/kb/too-many-redirects). SiteGround also warns proxied CNAMEs break its email-marketing domain authentication: "we recommend creating an unproxied CNAME record" (https://www.siteground.com/kb/domain-authentication-issue-cloudflare).

**Mechanism A — Workers route `gitavalley.org/social*` → `fetch()` to the Hub origin (works on Free).**

- Route requirements: "An active Cloudflare zone", "A Worker to invoke", "A DNS record set up for the domain … or subdomain … proxied by Cloudflare"; patterns: "If a route pattern path ends with `*`, then it matches all suffixes of that path"; "Routes are recommended for use cases where your application's origin server is external to Cloudflare." — https://developers.cloudflare.com/workers/configuration/routing/routes/ and …/routing/ (fetched 2026-09-08).
- The Worker rewrites the URL to `https://social.gitavalley.org/…` (or the Lightsail IP) and returns the response; Workers' `fetch()` example "use fetch to respond with another site" is exactly this pattern — https://developers.cloudflare.com/workers/runtime-apis/fetch/.
- Free-tier limits: "100,000 per day" requests, "10 milliseconds of CPU time per invocation" (https://developers.cloudflare.com/workers/platform/pricing/); "50/request" subrequests, 6 simultaneous outbound connections (https://developers.cloudflare.com/workers/platform/limits/). Workers Paid is "$5 USD per month for an account" with "10 million included per month". A 1–3-user staff tool will never approach 100k/day, so **$0**; the 10 ms CPU cap is fine for pass-through proxying (streaming bodies is I/O, not CPU), including the SSE `/api/generate` stream.

**Mechanism B — Origin Rules "DNS record override" (would avoid writing a Worker): Enterprise-only.**

Availability table read from the raw page: "Override Host header | No | No | No | Yes", "Override SNI | No | No | No | Yes", "Override DNS records | No | No | No | Yes", "Override destination port | Yes | Yes | Yes | Yes" (Free/Pro/Business/Enterprise); "Origin Rules require that you proxy the DNS records of your domain (or subdomain) through Cloudflare." — https://developers.cloudflare.com/rules/origin-rules/ (fetched 2026-09-08). Port override alone cannot send `/social/*` to a different host. **Not available on Free/Pro/Business.**

**Mechanism C — Snippets: not on Free.** "Availability | No | Yes | Yes | Yes", "Number of snippets | 0 | 25 | 50 | 300", "Number of snippet subrequests | 0 | 2 | 3 | 5", max execution "5 ms" — https://developers.cloudflare.com/rules/snippets/ (fetched 2026-09-08). Pro ($20–25/mo) would be needed; the Worker route is strictly better and free.

### 2.3 App-side cost of living under `/social`

Verified against the repo on 2026-09-08:

| Piece | Today | Change needed for `/social` |
|---|---|---|
| Vite build | no `base` in `frontend/vite.config.ts` | `base: '/social/'` — "If you are deploying your project under a nested public path, simply specify the `base` config option and all asset paths will be rewritten accordingly" (https://vite.dev/guide/build#public-base-path) |
| Router | `<BrowserRouter …>` in `frontend/src/main.tsx` with no `basename` | add `basename="/social"` |
| API client | absolute `/api/...` paths throughout `frontend/src/lib/api.ts` (e.g. lines 687–699) | prefix every call, or an env-driven base |
| Backend | `prefix="/api"` in 11 routers under `api/routes/*.py`; `/media/...` file URLs served by FastAPI | either change every prefix or run uvicorn with `--root-path /social` and have the proxy strip the prefix — FastAPI: "the proxy … would put your **FastAPI** application under a path like `/api/v1` … Uvicorn will expect the proxy to access Uvicorn at `http://127.0.0.1:8000/app`, and then it would be the proxy's responsibility to add the extra `/api/v1` prefix on top" (https://fastapi.tiangolo.com/advanced/behind-a-proxy/) |
| nginx | `location /api/` and `location ~ ^/media/.+\..+$` in `frontend/nginx.conf` | mirror the prefix; SSE `proxy_buffering off` must survive the Worker hop |
| Cookies | none — JWT in localStorage | no change; but `localStorage` would now be scoped to `gitavalley.org`, shared with any WordPress-side scripts on the same origin |
| Public media resolver / Postiz callbacks | absolute URLs on `social.gitavalley.org` (per `docs/research/hub-hosting-aws-vps.md`) | rebase; any URL persisted in the DB must be migrated |

Each of these is a mechanical change, but together they touch every layer, and the "is it `/api` or `/social/api` here?" question would follow every future feature.

### 2.4 Verdict on Option 2

Not worth it. It delivers a cosmetic URL (`gitavalley.org/social` vs `social.gitavalley.org`) at the price of (a) migrating the nonprofit's entire public DNS and email records to another provider, (b) losing the SiteGround CDN and putting WordPress behind Cloudflare's proxy with an SSL-mode gotcha, (c) a Worker in the request path of every Hub call, and (d) a cross-cutting refactor of the Hub. Only a Cloudflare Enterprise plan makes it configuration-only (Origin Rules). If the organisation ever moves DNS to Cloudflare for its own reasons, revisit; until then Option 1.

## 3. Option 3 — host the Hub on SiteGround itself

### 3.1 Shared / managed WordPress plans (StartUp $17.99, GrowBig $29.99, GoGeek $44.99 renewal; promo $2.99/$4.99/$7.99 — https://www.siteground.com/web-hosting.htm, fetched 2026-09-08)

| Requirement | SiteGround position | Source (fetched 2026-09-08) |
|---|---|---|
| Persistent Python process (uvicorn) | Python is exposed as an interpreter over SSH ("Python 3.13.2 … on linux", `pip3 install module-name`) and as CGI ("AddHandler cgi-script .pl .py .htm .shtml .sh .cgi"). No page documents a Python web-app runtime. To "Can i install python Django in my Gogeek account?" SiteGround answered "No, you cannot do that on GoGeek plan." | https://www.siteground.com/kb/see-available-python-modules ; https://www.siteground.com/kb/can_i_run_my_own_cgi_scripts/ ; https://www.siteground.com/blog/webinar-about-the-new-client-area-and-site-tools (Q&A) |
| Node daemon | "SiteGround supports Node.js on Shared and Cloud hosting plans … StartUp – 0 (not supported), GrowBig – up to 5, GoGeek – up to 10, Cloud – unlimited number of Node.js projects" (KB last updated Sep 03, 2026). The KB says nothing about how a "project" runs (ports, process manager, uptime), and no how-to article exists in the KB. | https://www.siteground.com/kb/node-js-available |
| Root / Docker | "SSH access is allowed for all hosting plans. Root SSH access, however, is not allowed." (title: "Can I have SSH root access to my Shared/Cloud server?"). Docker is not mentioned anywhere in the KB or plan pages; without root there is no Docker daemon. | https://www.siteground.com/kb/can_i_have_ssh_root_access_to_my_sharedvpd_server |
| Resource limits | CPU seconds: StartUp "1000/hour, 10000/day, 300000/month"; GrowBig "2000/hour, 20000/day, 600000/month"; GoGeek "4000/hour, 40000/day, 800000/month"; "up to 768MB RAM per process"; databases "up to 1000MB"; cron "at least 30 minutes difference between scheduled script executions"; enforcement: "we may need to limit the access to your website until you take action." | https://www.siteground.com/kb/fair-use-siteground-hosting |
| Cron | Site Tools → Devs → Cron Jobs; email per execution ("This may flood your inbox in case your crons run too often") | https://www.siteground.com/kb/manage-cron-jobs |
| Proxies / daemons | "Installation of proxies is not allowed" | https://www.siteground.com/kb/do_you_allow_proxies_to_be_hosted |

An always-on uvicorn process with a 30-second publish loop and a Claude CLI subprocess is exactly the kind of workload these limits exist to prevent (a single always-running process would consume the hourly CPU-second budget by itself). **Cannot host the Hub.**

### 3.2 SiteGround Cloud Hosting (https://www.siteground.com/cloud-hosting.htm, fetched 2026-09-08)

- Plans: "Jump Start — $100.00/mo" (4 cores, 8 GB RAM, 40 GB SSD), "Business — $200.00/mo" (8 / 12 GB / 80 GB), "Business Plus — $300.00/mo", "Super Power — $400.00/mo"; all "5TB Data Transfer".
- Included list (verbatim): "Dedicated resources, Automated Scaling, Unlimited Websites, Free SSL, Free Email, Free CDN, Dedicated IP, Daily Backups, On-demand backups, NGINX Direct Delivery, Dynamic Caching, Memcached, Collaborators and Clients, White-label access, Build Your Own Plans, WordPress Autoinstall, WordPress Autoupdates, WordPress Migrator Plugin, Staging + Git, WP-CLI and SSH, 30% faster PHP, Private DNS, Smart, constantly updated WAF, 24/7 Priority Support". Described as "fully managed".
- **No root access, no Docker, no custom services** appear anywhere on the page, and the root-access KB above is titled for "Shared/Cloud". Node.js is "unlimited number of Node.js projects" on Cloud, still with no documented runtime model; Python daemons are undocumented.

Verdict: $100/mo (= $1,200/yr) buys a bigger managed-PHP container with the same Site Tools ceiling — 8.3× Lightsail's $12/mo (https://aws.amazon.com/lightsail/pricing/: "$12 USD/mo 2 GB Memory 2 vCPUs 60 GB SSD Disk 3 TB Transfer", fetched 2026-09-08) for a platform that does not document running a Python service at all. **Reject.**

## 4. Option 4 — embedding and single sign-on

### 4.1 (a) iframe of `social.gitavalley.org` inside a private WordPress page

- Hub side today: `frontend/nginx.conf` line 39 — `add_header X-Frame-Options "SAMEORIGIN" always;`. MDN: "SAMEORIGIN — The document can only be embedded if all ancestor frames have the same origin as the page itself." `https://gitavalley.org` and `https://social.gitavalley.org` are different origins, so the frame is blocked until the Hub switches to CSP: "The Content-Security-Policy HTTP header has a frame-ancestors directive which you should use instead" (`ALLOW-FROM` "is an obsolete directive") — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options (fetched 2026-09-08).
- Cookies: not an issue for the Hub as built (JWT in localStorage, no session cookie). If cookies were added later, `SameSite` is judged by "site (the registrable domain)", so parent `gitavalley.org` and child `social.gitavalley.org` are same-site and cookies would still flow; MDN nonetheless notes browsers "have all started to block third-party cookies by default" — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies.
- WordPress "Private" visibility: "Private posts are automatically published but not visible to anyone but those with the appropriate permission levels (Editor or Administrator)" and "If a visitor were to guess the URL for your private post, they would still not be able to see your content" — https://wordpress.org/documentation/article/content-visibility-classic-editor/ (fetched 2026-09-08). This protects the *WordPress page*, not `social.gitavalley.org`, which remains directly reachable. Staff would still log into the Hub inside the frame.
- Functional drawbacks: nested scrolling and a fixed frame height on a dashboard-style SPA, browser file pickers/downloads inside a frame, no URL bar deep-linking, mobile usability, plus the extra header change. **Zero security or convenience gain for 1–3 staff. Pointless.**

### 4.2 (b) WordPress as OAuth2/OIDC identity provider

| Plugin | Free tier | Paid | Notes | Source (fetched 2026-09-08) |
|---|---|---|---|---|
| **OpenID Connect Server** (Automattic) | Free, open source; "use your own WordPress install to authenticate with a webservice that provides OpenID Connect"; clients registered via the `oidc_registered_clients` filter in `functions.php` (id, secret, redirect URI, grant types, `scope => 'openid profile'`) | — | "100+" active installations; last updated **April 17, 2025**; tested up to 6.8.8 — a small, slow-moving project | https://wordpress.org/plugins/openid-connect-server/ |
| **WP OAuth Server** (Jayson T Cote, wp-oauth.com) | Free: "Unlimited OAuth 2.0 Clients", Authorization Code w/ Implicit, PKCE, "WP REST API Authentication"; **OpenID Connect is Pro-only** | Personal **$89.00/year** (1 site), Business **$149.00/year** (up to 3 sites), Developer **$499.00/year** (unlimited); "All license options are valid for 1 year"; "Non-profits and educational systems receive discounts" on request | 3,000+ installs, tested up to 7.0.4, updated ~Aug 2026 | https://wordpress.org/plugins/oauth2-provider/ ; https://wp-oauth.com/downloads/wp-oauth-server/ ; https://wp-oauth.com/ |
| **WP OAuth Server (miniOrange)** | Free: "Supports only 1 Client Application", Authorization Code grant, OIDC discovery/JWKS/userinfo endpoints, HS256/RS256 | Product page: Premium "$900 /year" prepaid or "$149 /month" postpaid, "$50 per Client Application" extra; **miniOrange's pricing index page shows a different figure: "$500/year" or "$89/month", user-based** — the two pages disagree (flagged) | 1,000+ installs, tested up to 7.1, updated ~Aug 2026 | https://plugins.miniorange.com/wp-oauth-server ; https://plugins.miniorange.com/wordpress-pricing ; https://wordpress.org/plugins/miniorange-oauth-20-server/ |

Free no-plugin alternative (not SSO, but shared credentials): WordPress core **Application Passwords** — "The credentials can be passed along to REST API requests served over `https://` using Basic Auth/RFC 7617"; available "on sites served over SSL/HTTPS" since WordPress 5.6 (https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/ ; https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/). The Hub could verify a WP username + application password by calling `GET /wp-json/wp/v2/users/me` and mint its own JWT. That makes WordPress a hard dependency for Hub login without giving staff a single sign-in.

Hub-side work for real OIDC: add an OIDC client flow to FastAPI (Authlib or similar), map WP roles → Hub roles, keep a break-glass local admin — roughly 1–2 developer days, plus plugin upkeep on the WordPress side. Named accounts in the Hub's own SQLite (already planned) are ~half a day and add no cross-system dependency.

**Verdict: defer.** For 1–3 staff the shared password → named local accounts step is the right next move. Revisit OIDC only if the temple standardises on WordPress logins for staff tools; then the free Automattic plugin is the starting point, with WP OAuth Server Pro ($89/yr) as the maintained commercial fallback.

## 5. Option 5 — PaaS alternatives to a Lightsail VM (brief)

Hub needs: one always-on instance, a persistent volume for `data/gvsa.db` + ~600 MB media, outbound HTTPS, and the ability to run the Claude CLI (Node) as a subprocess. Sizing from `docs/research/hub-hosting-aws-vps.md`: backend ≈ 127 MB resident, Claude CLI/Node ≈ 0.3 GB, target 2 GB RAM.

| Host | Always-on 2 GB-class instance | Persistent volume | SQLite safety | Node subprocess | Est. $/mo | Source (fetched 2026-09-08) |
|---|---|---|---|---|---|---|
| **Fly.io** | `shared-cpu-1x` in Ashburn (iad): 1 GB **$5.70**, 2 GB **$10.70** (256 MB $1.94); Amsterdam 2 GB $11.11 — prices vary by region. Usage-billed; "All organizations … require a credit card on file"; no free tier/hobby plan on the page | Volumes "$0.15/GB per month of provisioned capacity"; snapshots "$0.08/GB per month", "First 10GB free each month" | "a volume can be attached to only one Machine" and "Each volume exists on one server in a single region. It is not network storage." Single-copy warning: "If you only have a single copy of your data on a single volume, and that drive fails, then the data is lost" — keep the nightly off-box backup; Fly names "LiteFS - Distributed SQLite" only for replication | Yes — "Fly Launch can deploy your app from a Dockerfile" | **≈ $12.20** (2 GB + 10 GB volume) + egress $0.02/GB (NA/EU) | https://fly.io/docs/about/pricing/ ; https://fly.io/docs/volumes/overview/ ; https://fly.io/docs/languages-and-frameworks/dockerfile/ |
| **Render** | Free "$0/month 512 MB RAM" (unusable: "spins down a Free web service that goes 15 minutes without receiving any inbound traffic", "750 Free instance hours" per month, "Free web services cannot attach a persistent disk"); Starter **$7/month** 512 MB / 0.5 CPU (too small for the CLI); Standard **$25/month** 2 GB / 1 CPU | "Persistent disks $0.25 per GB per month"; "You can attach a persistent disk to a paid Render web service" only | "You can't scale a service to multiple instances if it has a disk attached" (good — enforces single writer); "Adding a disk to a service prevents zero-downtime deploys" (a few seconds' outage per deploy) | Yes — "Render can build your service's Docker image based on the Dockerfile in your project repo" | **$27.50** (Standard + 10 GB) | https://render.com/pricing ; https://render.com/docs/disks ; https://render.com/docs/free ; https://render.com/docs/docker |
| **Railway** | Hobby "$5 / month" incl. "$5 of resource usage per month"; usage: memory "$0.00000386 per GB/s" (≈ $10/GB-mo), vCPU "$0.00000772 per vCPU/s" (≈ $20/vCPU-mo), egress "$0.05 per GB" | "$0.00000006 per GB/s" (≈ $0.15/GB-mo); Hobby volume cap "5GB" (Pro 50 GB) | "Each service can only have a single volume"; "Replicas cannot be used with volumes"; "There will be a small amount of downtime when re-deploying a service that has a volume attached" | Yes — "Railway will look for and use a `Dockerfile` at the root of the source directory" | **≈ $12–18 (estimate)**: $5 plan + ~1 GB RAM ($10) + fractional vCPU + 5 GB volume ($0.75), minus the $5 credit; 2 GB RAM pushes ≈ $22–28 | https://railway.com/pricing ; https://docs.railway.com/reference/pricing/plans ; https://docs.railway.com/reference/volumes ; https://docs.railway.com/guides/dockerfiles |
| **AWS Lightsail** (baseline) | "$12 USD/mo 2 GB Memory 2 vCPUs 60 GB SSD Disk 3 TB Transfer" | included (60 GB) | plain disk, single VM | any (full VM) | **$12** | https://aws.amazon.com/lightsail/pricing/ |

None of the three PaaS pages says "SQLite" is supported or unsupported for its volumes except Fly's LiteFS pointer; all three make the volume single-instance, which is the property SQLite needs. Only Railway's Hobby 5 GB cap is a real constraint (media growth). Fly.io is the price-equal alternative; Railway is close but usage-billed; Render costs ~2.3× for the same RAM. Verdict unchanged from the prior document: Lightsail 2 GB (or DigitalOcean 2 GB) remains the pick; Fly.io is the PaaS fallback.

## 6. Decision matrix

| # | Option | Extra cost / month | Extra cost / year | Setup effort | Who must act | Drawbacks | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `social.gitavalley.org` A record → Lightsail; Caddy TLS; WP Custom Link | **$0** | **$0** | ~15 min (one A record, one menu item, Caddy already planned) | SiteGround account holder (DNS Zone Editor); WordPress editor/admin (menu) | Separate login from WordPress; Hub URL is public (own login is the gate); must avoid the Subdomains tool | **Recommended** |
| 2a | `gitavalley.org/social` via SiteGround `.htaccess` proxy | — | — | Not possible | — | `ProxyPass` not an `.htaccess` directive; SG documents no `mod_proxy`, bans proxies, owns the nginx layer | **Reject** |
| 2b | `gitavalley.org/social` via Cloudflare Free + Worker route | $0 (Workers Free 100k req/day; $5/mo Paid if exceeded) | $0 | 1–2 dev days app refactor + DNS migration day + ongoing Worker | Domain registrant / DNS owner (nameserver change); web admin (Cloudflare SSL mode, re-create all records incl. email); developer (base path refactor) | Whole domain leaves SiteGround DNS: SG CDN auto-disabled, every DNS/email record re-created, WordPress behind Cloudflare proxy; Worker in every request; app must be rebased (`/api`, router basename, Vite base, nginx, media URLs) | **Not worth it** |
| 2c | Same via Cloudflare Origin Rules DNS override | Enterprise plan (custom pricing) | — | — | — | "Override DNS records: No/No/No/Yes" (Enterprise only) | **Reject** |
| 2d | Same via Cloudflare Snippets | Pro $20–25 | $240–300 | as 2b | as 2b | Snippets "Availability: No" on Free; 2 subrequests/5 ms on Pro; still needs the DNS move and refactor | **Reject** |
| 3a | Host Hub on SiteGround shared (GrowBig/GoGeek) | $0 (already paid) | $0 | Not possible | — | No root, Django "No", 768 MB/process, CPU-second caps, cron ≥30 min, proxies banned, Node runtime undocumented | **Reject** |
| 3b | Host Hub on SiteGround Cloud Jump Start | **+$100** | **+$1,200** | Unsupported | Account owner (purchase) | Still "Root SSH access … not allowed", no Docker/custom services on the plan page, Python service undocumented; 8.3× Lightsail | **Reject** |
| 4a | iframe of Hub in a private WP page | $0 | $0 | 1–2 h (CSP `frame-ancestors`, WP page) | Developer (header); WP editor (page) | Blocked today by `X-Frame-Options: SAMEORIGIN`; no security gain (Hub URL still public, Hub login still required); nested scrolling/mobile/file dialogs | **Pointless** |
| 4b | WordPress as OIDC IdP | $0 (Automattic plugin) or $89/yr (WP OAuth Server Personal) or $500–900/yr (miniOrange premium, pages disagree) | $0 / $89 / $500–900 | 1–2 dev days + plugin install/maintenance | WP admin (plugin, client registration); developer (OIDC client in FastAPI) | WordPress becomes a login dependency; Automattic plugin small/stale (100+ installs, updated 2025-04); overkill for 1–3 staff vs named local accounts | **Defer** |
| 5a | Fly.io instead of Lightsail | ≈ $12.20 (2 GB iad + 10 GB vol) | ≈ $146 | ½ day (Dockerfile, volume, secrets) | Developer | Usage billing + card; single-copy volume (keep off-box backup); regional price variance | **Viable equal** |
| 5b | Render Standard + disk | $27.50 | $330 | ½ day | Developer | 2.3× cost; Starter 512 MB too small; Free spins down and has no disk; disk = no zero-downtime deploy | **Pricier — no** |
| 5c | Railway Hobby | ≈ $12–18 (est.) | ≈ $150–215 (est.) | ½ day | Developer | Usage-billed; 5 GB volume cap on Hobby; brief downtime per redeploy | **Viable, watch volume cap** |

## 7. Recommended sequence (Option 1)

1. Lightsail instance up, static IP attached, firewall ports 22/80/443 open (per `hub-hosting-aws-vps.md`).
2. SiteGround Site Tools → Domain → DNS Zone Editor → Create New Record → **A** tab → Name `social`, IPv4 = static IP, default TTL → Create. Confirm no `social` entry exists under Domain → Subdomains.
3. Caddyfile `social.gitavalley.org { reverse_proxy … }`; Caddy obtains/renews the certificate itself once the record resolves.
4. WordPress: Appearance → Menus (or Navigation block) → Custom Link `https://social.gitavalley.org`, label e.g. "Staff Hub", "Open link in new tab" on, placed in a footer/utility menu. Optionally put the link on an Editor-only Private page instead of a public menu.
5. Later, independently: named Hub accounts; revisit OIDC only if a WordPress-wide staff SSO policy appears.

## 8. Open items / unverified

- Whether SiteGround's Subdomains tool also writes an A record into the zone when a subdomain is created (KB silent) — check the zone after any accidental creation.
- Which theme type gitavalley.org runs (classic Menus screen vs block Navigation block) — determines which of the two WordPress docs applies.
- miniOrange OAuth Server pricing: product page says $900/yr or $149/mo; pricing index says $500/yr or $89/mo — contact them if ever relevant.
- WP OAuth Server licensing page (`/about/wp-oauth-server-licensing/`) returned HTTP 500 during this research; prices are from the downloads page.
- Railway monthly figure is an estimate from published per-second rates and an assumed ~1 GB RAM / ~0.25 vCPU average; actual usage billing may differ.
- SiteGround Node.js "projects" runtime model (ports, supervision, uptime) is undocumented in the KB; not needed for the verdict.

## Sources (all fetched 2026-09-08 local / 2026-09-09 UTC)

SiteGround: https://www.siteground.com/kb/manage-dns-records-site-tools · https://www.siteground.com/kb/manage-dns-records · https://www.siteground.com/kb/subdomain · https://www.siteground.com/kb/upload-website-files · https://www.siteground.com/kb/is-lets-encrypt-only-for-non-www-domain-names · https://www.siteground.com/kb/install-lets-encrypt-domain/ · https://www.siteground.com/blog/free-lets-encrypt-wildcard-ssl · https://www.siteground.com/kb/how_to_change_my_ns_record · https://www.siteground.com/kb/point-domain-siteground · https://www.siteground.com/kb/manage-cdn · https://www.siteground.com/kb/activate-cloudflare-cdn · https://www.siteground.com/kb/too-many-redirects · https://www.siteground.com/kb/domain-authentication-issue-cloudflare · https://www.siteground.com/kb/is_it_possible_to_set_apaches_allowoverride_directive_to_all/ · https://www.siteground.com/kb/do_you_allow_proxies_to_be_hosted · https://www.siteground.com/kb/see-available-python-modules · https://www.siteground.com/kb/can_i_run_my_own_cgi_scripts/ · https://www.siteground.com/kb/node-js-available · https://www.siteground.com/kb/can_i_have_ssh_root_access_to_my_sharedvpd_server · https://www.siteground.com/kb/fair-use-siteground-hosting · https://www.siteground.com/kb/manage-cron-jobs · https://www.siteground.com/blog/webinar-about-the-new-client-area-and-site-tools · https://www.siteground.com/cloud-hosting.htm · https://www.siteground.com/web-hosting.htm
Apache: https://httpd.apache.org/docs/2.4/mod/mod_proxy.html · https://httpd.apache.org/docs/2.4/rewrite/flags.html
Cloudflare: https://www.cloudflare.com/plans/ · https://developers.cloudflare.com/dns/zone-setups/partial-setup/ · https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/ · https://developers.cloudflare.com/workers/configuration/routing/routes/ · https://developers.cloudflare.com/workers/configuration/routing/ · https://developers.cloudflare.com/workers/runtime-apis/fetch/ · https://developers.cloudflare.com/workers/platform/pricing/ · https://developers.cloudflare.com/workers/platform/limits/ · https://developers.cloudflare.com/rules/origin-rules/ · https://developers.cloudflare.com/rules/snippets/
WordPress: https://wordpress.org/documentation/article/appearance-menus-screen/ · https://wordpress.org/documentation/article/navigation-block/ · https://wordpress.org/documentation/article/content-visibility-classic-editor/ · https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/ · https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/ · https://wordpress.org/plugins/openid-connect-server/ · https://wordpress.org/plugins/oauth2-provider/ · https://wordpress.org/plugins/miniorange-oauth-20-server/ · https://wp-oauth.com/ · https://wp-oauth.com/downloads/wp-oauth-server/ · https://plugins.miniorange.com/wp-oauth-server · https://plugins.miniorange.com/wordpress-pricing
MDN: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options · https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies
Hosts: https://aws.amazon.com/lightsail/pricing/ · https://fly.io/docs/about/pricing/ · https://fly.io/docs/volumes/overview/ · https://fly.io/docs/languages-and-frameworks/dockerfile/ · https://render.com/pricing · https://render.com/docs/disks · https://render.com/docs/free · https://render.com/docs/docker · https://railway.com/pricing · https://docs.railway.com/reference/pricing/plans · https://docs.railway.com/reference/volumes · https://docs.railway.com/guides/dockerfiles
App-side: https://vite.dev/guide/build#public-base-path · https://fastapi.tiangolo.com/advanced/behind-a-proxy/ · https://caddyserver.com/docs/automatic-https
