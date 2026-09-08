# Hosting the Content Hub at social.gitavalley.org — AWS vs VPS Research

Date: 2026-09-07 (all URLs fetched 2026-09-07/08 UTC; every price below was read from the provider's own page or price API on that date — none from memory)
Sources: aws.amazon.com (Lightsail/EC2/EBS/S3/EFS/Fargate/App Runner/Elastic Beanstalk/ELB/VPN pricing, Free Tier, Nonprofit Credit Program, blogs), docs.aws.amazon.com (Lightsail, App Runner, Elastic Beanstalk, ECS), AWS Price List offer files (`pricing.us-east-1.amazonaws.com`) and the EC2 on-demand price feed (`b0.p.awsstatic.com`), page.techsoup.org / blog.techsoup.org, digitalocean.com, api.linode.com, api.vultr.com + docs.vultr.com, Hetzner price API + docs.hetzner.com, siteground.com/kb, caddyserver.com, developers.cloudflare.com + cloudflare.com/plans, tailscale.com, uptimerobot.com, sqlite.org, github.com (caddy-ratelimit, fail2ban). Local verification: `systemctl show gvsa-backend`, `docker stats`, `du`, repo files (`gvsa-backend.service`, `docker-compose.yaml`, `api/auth.py`).

Question: where should the Gita Valley Content Hub — FastAPI (Python 3.11) + React SPA behind nginx, one SQLite file, a ~600 MB media directory, two in-process background loops (30-second publish loop + content scheduler), and a Claude CLI / Anthropic SDK subprocess with outbound HTTPS — live so that it has a persistent disk, a long-running process, outbound internet and HTTPS at `https://social.gitavalley.org` (DNS at SiteGround), for 1–3 staff on home/mobile connections, with or without self-hosted Postiz (Docker, ~4 GB) on the same box?

## TL;DR

| | Verdict |
|---|---|
| **(a) Hub only (Postiz Cloud or Postiz elsewhere)** | **AWS Lightsail 2 GB Linux bundle, us-east-1 — $12/mo** (2 vCPU, 60 GB SSD, 3 TB transfer, static IP included) + automatic daily snapshots (7 kept, $0.05/GB-mo) + nightly `db+media → S3` sync (~2 GB ≈ $0.05/mo). ≈ **$13–15/mo list; ≈ $0 hosting + $95/yr TechSoup fee if the AWS credit is used.** Runner-up: **DigitalOcean Basic 2 GB (NYC) $12 + weekly backups 20% = $14.40/mo.** |
| **(b) Hub + self-hosted Postiz on one box** | **Lightsail 4 GB — $24/mo** as the floor (measured idle Postiz stack = 1.77 GiB + Hub ≈ 0.2 GiB); **Lightsail 8 GB — $44/mo** if the TechSoup credit pays for it ($528/yr < $1,000). Runner-up: **DigitalOcean 4 GB $24 + $4.80 backups = $28.80/mo** (8 GB: $57.60). |
| **Do not use** | App Runner (closed to new customers, no persistent disk), Lightsail Containers (no persistent disk), Elastic Beanstalk ("no persistent local storage"), ECS Fargate + EFS (≈$40–60/mo, SQLite on NFS is a documented corruption risk), Hetzner US (CPX11 2 GB is $20.49/mo after the 15 June 2026 price adjustment). |
| **DNS + TLS** | One **A record** `social` → the Lightsail static IP in SiteGround's DNS Zone Editor; **Caddy** issues Let's Encrypt/ZeroSSL certs automatically once ports 80/443 are open in the Lightsail firewall (base-OS blueprints open only 22 and 80 by default — add 443). A Lightsail load balancer ($18/mo) is unnecessary for one instance. |
| **Access control** | Keep the Hub's existing JWT login (single shared password, lockout) behind Caddy, SSH by key only with **Tailscale** (free for ≤6 users) for admin access, fail2ban on sshd. **Cloudflare Access is not feasible for one subdomain while the zone stays at SiteGround** — Free/Pro plans support only "full setup" (nameservers move to Cloudflare); the partial/CNAME setup that would let `social.` alone go through Cloudflare requires the **Business plan ($200/mo billed annually, $250 monthly)**. AWS Client VPN ≈ $73/mo standing cost — overkill. |
| **Ops** | ≈ 1–2 h/month: monthly OS + app updates, glance at UptimeRobot (free, 50 monitors, 5-min checks) and Lightsail alarms (email/SMS, 2 per metric), quarterly restore test from a snapshot or the S3 copy. |

## 1. What the app needs (measured on the current box, 2026-09-07)

| Component | Measured | Source |
|---|---|---|
| FastAPI backend (`gvsa-backend`, uvicorn, both loops running) | **127 MB** resident (`MemoryCurrent=126824448`) | `systemctl show gvsa-backend` |
| Frontend nginx container | 11 MiB | `docker stats` |
| Hub backend as a container (`gita-valley-content-hub`) | 51 MiB | `docker stats` |
| SQLite DB (`data/gvsa.db`) | 1.3 MB; `data/` = 2.5 MB | `ls -la`, `du -sh` |
| Media directory | ~600 MB (task statement; the repo's `media/` is read relative to the working directory — `api/main.py:112`) | task statement |
| Postiz stack (v2.18 compose: postiz 746 MiB, temporal-elasticsearch 790 MiB, temporal 101 MiB, temporal-postgres 84 MiB, postiz-postgres 37 MiB, redis 12 MiB) | **≈ 1.77 GiB idle** | `docker stats` |
| Claude CLI subprocess | not measured (Node process, spawned per generation; 3-concurrent limit in the engine) | — |

Hard requirements the platform must meet: a persistent local filesystem (SQLite + media), one always-on process (the publish loop runs every 30 s inside the API process — serverless/scale-to-zero platforms are out), unrestricted outbound 443 (api.anthropic.com, Postiz, Meta/Google APIs), inbound 443 on a custom subdomain, and credentials for the AI subprocess on the server (an `ANTHROPIC_API_KEY` env var, or a Claude CLI OAuth profile completed once over SSH — the current systemd unit already puts `~/.local/bin` on PATH for the CLI, `gvsa-backend.service`).

## 2. AWS options (us-east-1)

### 2.1 Lightsail instance bundles (recommended AWS path)

Linux/Unix bundles **with public IPv4**, from https://aws.amazon.com/lightsail/pricing/ and https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html (fetched 2026-09-07):

| Bundle | $/mo | vCPU | RAM | SSD | Transfer | Sustainable CPU baseline (per vCPU) |
|---|---|---|---|---|---|---|
| Nano | $5 | 2 | 0.5 GB | 20 GB | 1 TB | 5 % |
| Micro | $7 | 2 | 1 GB | 40 GB | 2 TB | 10 % |
| **Small** | **$12** | 2 | **2 GB** | 60 GB | 3 TB | 20 % |
| **Medium** | **$24** | 2 | **4 GB** | 80 GB | 4 TB | 20 % |
| **Large** | **$44** | 2 | **8 GB** | 160 GB | 5 TB | 30 % |
| Xlarge | $84 | 4 | 16 GB | 320 GB | 6 TB | 40 % |

Baselines from https://docs.aws.amazon.com/lightsail/latest/userguide/baseline-cpu-performance.html ("Lightsail instances continuously earn … CPU burst capacity"; instances above baseline spend accrued burst). A scheduler that idles most of the day is the ideal shape for this.

What the bundle includes and what it costs extra:

- **Included in all plans:** "Static IP address · Intuitive management console · DNS management · One-click SSH terminal access · Powerful API · Highly available SSD storage · Server monitoring" — https://aws.amazon.com/lightsail/pricing/.
- **Static IP:** "There are no costs associated with static IP addresses when they are attached to a Lightsail instance"; unattached >1 h costs $0.005/h; without a static IP "each time you stop or restart your instance, Lightsail assigns a new public IP address" — https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html, https://aws.amazon.com/lightsail/faq/.
- **The IPv4 pricing change:** AWS charges $0.005/h per public IPv4 since 1 Feb 2024 (https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/). Lightsail folded it into the bundle: "Revised prices for bundles that include a public IPv4 address will be effective on all new and existing Lightsail bundles starting May 1, 2024" (https://aws.amazon.com/blogs/compute/announcing-ipv6-instance-bundles-and-pricing-update-on-amazon-lightsail/). **IPv6-only bundles keep the old prices** — $3.50 / $5 / $10 / $20 / $40 — and "Static IPs cannot be attached to IPv6-only instances" (FAQ). IPv6-only is not usable here: staff on mobile/home IPv4-only networks and the Meta/Google webhooks need an IPv4 endpoint.
- **Snapshots:** "$0.05 USD/GB-month for both instance snapshots and for disk snapshots" (FAQ). **Automatic snapshots** are daily, "The latest seven daily automatic snapshots are stored before the oldest one is replaced", deleted with the instance unless copied to a manual snapshot, and billed at the snapshot rate — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-configuring-automatic-snapshots.html. Snapshots can restore to the same or a larger bundle (never smaller) and can be exported to EC2 — https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html. The pages fetched do not say how much of a 60 GB disk a daily snapshot bills (dedup rule); budget $0.50–4/mo for 7 dailies of a ~10 GB-used disk and check the first bill.
- **Block storage:** $0.10/GB-mo if the media directory ever outgrows the bundle disk (pricing page).
- **Data transfer:** overage "$0.09 USD/GB" in US regions, charged only on outbound over the allowance (FAQ) — irrelevant at 3 TB included.
- **Firewall:** two independent firewalls (IPv4/IPv6); "Firewall rules are always permissive"; source restriction by single IP, dash range or CIDR; up to 30 source IPs per rule via console, 60 via API/CLI; all outbound allowed; **base-OS blueprints (Ubuntu, Debian, Amazon Linux…) open only SSH 22 and HTTP 80 by default** — HTTPS 443 must be added — https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html.
- **Monitoring/alarms:** alarms on a single metric per resource, "You can add two alarms per metric", evaluated every 5 minutes, notifications by console banner, email and SMS, configurable missing-data handling — https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-alarms.html. The page states no charge; the pricing page lists "Server monitoring" as included.
- **Load balancer:** "$18 USD/mo" (pricing page), "Lightsail certificates and certificate management are free with use of a Lightsail load balancer" (FAQ). A load balancer is for "multiple Lightsail instances, in multiple Availability Zones" (https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-lightsail-load-balancers.html) — for one instance it is $18/mo to avoid running Caddy. Not worth it.
- **Lightsail vs EC2 for a non-sysadmin (FAQ):** Lightsail is for "projects that require a few virtual private servers and users who prefer a simple management interface"; move to EC2 when you need "consistently high CPU performance for applications such as video encoding or HPC". Lightsail can reach other AWS services (S3 for backups) over the public endpoints, and VPC peering is available for private IPs. Everything a hobby-level operator must otherwise assemble on EC2 — security group, Elastic IP, EBS volume, IPv4 line item, snapshot lifecycle — is one console page here.

### 2.2 EC2 (for comparison)

On-demand Linux, US East (N. Virginia), from AWS's own price feed (`b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/.../Linux/index.json`, fetched 2026-09-07); monthly = hourly × 730 h:

| Instance | vCPU | RAM | $/h | ≈ $/mo | + IPv4 ($0.005/h = $3.65) | + gp3 root (40 GB × $0.08) | ≈ all-in |
|---|---|---|---|---|---|---|---|
| t4g.small (Graviton/ARM) | 2 | 2 GiB | $0.0168 | $12.26 | $3.65 | $3.20 | **≈ $19.1** |
| t3a.small | 2 | 2 GiB | $0.0188 | $13.72 | $3.65 | $3.20 | ≈ $20.6 |
| t3.small | 2 | 2 GiB | $0.0208 | $15.18 | $3.65 | $3.20 | ≈ $22.0 |
| t4g.medium | 2 | 4 GiB | $0.0336 | $24.53 | $3.65 | $6.40 (80 GB) | **≈ $34.6** |
| t3.medium | 2 | 4 GiB | $0.0416 | $30.37 | $3.65 | $6.40 (80 GB) | ≈ $40.4 |
| t4g.large | 2 | 8 GiB | $0.0672 | $49.06 | $3.65 | $12.80 (160 GB) | ≈ $65.5 |

EBS gp3: "$0.08 per GB-month" with 3,000 IOPS / 125 MB/s included; EBS Snapshots Standard "$0.05 per GB-month" — https://aws.amazon.com/ebs/pricing/. Data transfer out: first 100 GB/month free aggregated across services, then regional rates (https://aws.amazon.com/s3/pricing/ data-transfer tab). Verdict: EC2 costs ~60 % more than the equivalent Lightsail bundle once IPv4 and disk are added, includes far less transfer, and adds security groups, EIPs, EBS and snapshot-lifecycle management. No benefit at this scale; ARM (t4g) would also mean the ARM caveats already recorded for Postiz in `postiz-hosting-migration.md` §1.

### 2.3 Elastic Beanstalk — unsuitable

"There is no additional charge for AWS Elastic Beanstalk" (https://aws.amazon.com/elasticbeanstalk/pricing/), but "Elastic Beanstalk applications run on Amazon EC2 instances that have no persistent local storage. When the Amazon EC2 instances terminate, the local file system isn't saved" (https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.concepts.design.html). SQLite + a media directory would have to move to EFS (see 2.5) or RDS, and every platform update replaces the instance. It is EC2 cost plus a deployment framework the app does not need.

### 2.4 App Runner — unsuitable (and closed)

"AWS App Runner is no longer open to new customers. Existing customers can continue to use the service as normal … we do not plan to introduce new features" — https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html. Nothing on the architecture page (https://docs.aws.amazon.com/apprunner/latest/dg/architecture.html) or the pricing page ($0.064/vCPU-h + $0.007/GB-h active, $0.007/GB-h provisioned — https://aws.amazon.com/apprunner/pricing/) describes persistent storage; it is a request-driven container runtime. AWS's stated replacement is **ECS Express Mode** ("no additional charge … You pay only for the underlying AWS resources": an ECS service on Fargate + an Application Load Balancer) — i.e. option 2.5.

### 2.5 ECS Fargate + EFS — works on paper, wrong shape

Fargate Linux/x86 in us-east-1: $0.000011244/vCPU-s (≈ $0.0404/vCPU-h) and $0.000001235/GB-s (≈ $0.00444/GB-h); ARM ≈ $0.0324/vCPU-h and $0.00356/GB-h; 20 GB ephemeral storage included — https://aws.amazon.com/fargate/pricing/. EFS Standard "$0.30 per GB-Mo" in USE1, Elastic Throughput reads $0.03/GB and writes $0.06/GB (AWS Price List offer file `AmazonEFS/current/us-east-1/index.json`, published 2026-08-31). ALB "$0.0225" per hour + "$0.008 per LCU" hour (https://aws.amazon.com/elasticloadbalancing/pricing/). Fargate tasks are otherwise ephemeral; EFS is how "your tasks have access to the same persistent storage, no matter the instance on which they land" and needs Fargate platform 1.4.0+ (https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html).

| Task size | Fargate | ALB | IPv4 (ALB, 2 AZs) | EFS 3 GB | ≈ total |
|---|---|---|---|---|---|
| 0.5 vCPU / 1 GB | $14.75 + $3.24 = $18.0 | $16.4 + LCU | $3.65–7.30 | $0.90 | **≈ $40–45/mo** |
| 1 vCPU / 2 GB | $29.5 + $6.5 = $36.0 | $16.4 + LCU | $3.65–7.30 | $0.90 | **≈ $58–62/mo** |

Two disqualifiers beyond price: (1) EFS is NFS, and SQLite's own corruption guide warns "some filesystems contain bugs in their locking logic … This is especially true of network filesystems and NFS in particular … database corruption might result" (https://www.sqlite.org/howtocorrupt.html §2.1); (2) VPC + subnets + task definition + IAM roles + ECR + ALB listener + ACM cert is a large surface for a non-sysadmin to own.

### 2.6 Lightsail Container Service — unsuitable

Powers: Nano $7 (0.25 vCPU / 512 MB), Micro $10 (0.25 / 1 GB), Small $15 (0.5 / 1 GB), Medium $40 (1 / 2 GB), Large $80 (2 / 4 GB), XLarge $160 (4 / 8 GB); 500 GB transfer each; HTTPS-only public endpoint with auto HTTP→HTTPS redirect; "Alerting based on these metrics is currently not supported" — https://aws.amazon.com/lightsail/pricing/, https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html, https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-containers.html. Neither page lists any volume, disk or persistent-storage feature; AWS re:Post answers (secondary, AWS-moderated) state Lightsail containers get ≥20 GiB ephemeral storage and do not support disks — https://repost.aws/questions/QU8GVkIsWOQGqedjXWLD91fA/volumes-with-containers-in-amazon-lightsail. SQLite and the media directory would be lost on every redeploy.

### 2.7 S3 for nightly backups

US East (N. Virginia), AWS Price List offer file `AmazonS3/current/us-east-1/index.json` (published 2026-08-31, fetched 2026-09-07): S3 Standard "$0.023 per GB - first 50 TB / month"; PUT/COPY/POST/LIST "$0.005 per 1,000"; GET "$0.004 per 10,000"; Standard-IA $0.0125/GB-mo; Glacier Instant Retrieval $0.004/GB-mo. Data transfer out "for the first 100GB per month" free (https://aws.amazon.com/s3/pricing/). **≈ 2 GB of db + media with 30 daily DB copies ≈ $0.05/mo**; even 10 GB is $0.23/mo. Not worth tiering to IA/Glacier at this size.

### 2.8 AWS Free Tier (2026) — the credits model

- Announced 15 July 2025: new customers get "$100 in AWS credits upon sign-up and can earn an additional $100" ($20 × five activities); "The free account plan expires after 6 months or when you exhaust your credits, whichever comes first"; on the **paid plan** "AWS will automatically apply your Free Tier credits to the use of eligible services"; "If your AWS account was created before July 15, 2025, you'll continue to be in the legacy Free Tier program" — https://aws.amazon.com/blogs/aws/aws-free-tier-update-new-customers-can-get-started-and-explore-aws-with-up-to-200-in-credits/, https://aws.amazon.com/free/, https://aws.amazon.com/free/free-tier-faqs/.
- Free plan restriction: "limited from accessing a subset of AWS services and offerings that would immediately consume the entire Free Tier credit amount"; when the free plan expires "AWS closes your account" (90-day grace to upgrade) — FAQ. The FAQ does not list whether Lightsail is on the free-plan subset; do not rely on it.
- Lightsail-specific: "Evaluate Amazon Lightsail with a 90-day free trial with the **Paid plan**" covering the $5/$7/$12 Linux plans, the $10 Micro container and the $15 database — https://aws.amazon.com/free/compute/lightsail/. So a **new AWS account on the paid plan gets the $12 bundle free for 90 days plus up to $200 of credits** — enough to run the 4 GB bundle for the rest of the first year on credits alone.

### 2.9 AWS Nonprofit Credit Program via TechSoup

- AWS: "Up to $5,000 USD per fiscal year (July 1 to June 30)"; "The AWS Promotional Credit is valid for all on-demand services with pay-as-you-go pricing" — which covers Lightsail, EC2, S3 and data transfer; excluded: Reserved Instances, Mechanical Turk, ineligible Support plans, AWS Marketplace, Route 53 domain registration/transfer, cryptocurrency mining, upfront fees; eligibility 501(c)(3) (and several other 501(c) types) validated by TechSoup; one grant per fiscal year; credit valid ≥1 year — https://aws.amazon.com/government-education/nonprofits/nonprofit-credit-program/.
- TechSoup: "$1,000 in AWS credits", "$95" admin fee, 12-month validity, "Apply credits to on-demand cloud usage fees" — https://page.techsoup.org/aws. TechSoup's tiered product pages (smaller / medium-sized / larger nonprofits, `techsoup.org/products/amazon-web-services-credit-for-*`) returned a bot-block page (926 bytes) to automated fetch; search snippets of those pages describe $1,000 (budget < $10 M), $2,000 ($10–50 M) and $5,000 (> $50 M) tiers — **treat the tier thresholds as unverified; the $1,000/$95 figure is verified**. TechSoup's 2021 change notice confirms credits "can be applied to usage fees for AWS on-demand cloud services and certain AWS support fees" per fiscal year — https://blog.techsoup.org/posts/what-you-need-to-know-about-changes-to-techsoups-aws-credits-program.
- Arithmetic: $1,000 covers Lightsail 4 GB ($288/yr) + snapshots + S3 with ~$650 to spare, or 8 GB ($528/yr) with ~$400 to spare. Effective cost = the $95 fee ≈ $8/mo.

## 3. Non-AWS VPS equivalents (US East)

| Provider | 2 GB | 4 GB | 8 GB | Backups | IPv4 | Source (fetched 2026-09-07) |
|---|---|---|---|---|---|---|
| **DigitalOcean Basic (Regular)** | $12 (1 vCPU, 50 GiB, 2 TB) | $24 (2 vCPU, 80 GiB, 4 TB) | $48 (4 vCPU, 160 GiB, 5 TB) | "20% (Weekly) or 30% (Daily) of Droplet cost"; snapshots $0.06/GB-mo | included ("each Droplet … comes with its own public IPv4"; v5 droplets bill IPv4 separately at an introductory $0.00/h "subject to change") | https://www.digitalocean.com/pricing/droplets |
| **Akamai/Linode Shared** | $12 (1 vCPU, 50 GB, 2 TB) + backups $2.50 | $24 (2 vCPU, 80 GB, 4 TB) + $5 | $48 (4 vCPU, 160 GB, 5 TB) + $10 | add-on prices per plan (Backups add-on) | included in plan | public API `https://api.linode.com/v4/linode/types` (`g6-standard-1/2/4`; no us-east surcharge listed) |
| **Vultr Cloud Compute (vc2, NJ)** | $10 (1 vCPU, 55 GB, 2 TB) or $15 (2 vCPU, 65 GB, 3 TB) | $20 (2 vCPU, 80 GB, 3 TB) | $40 (4 vCPU, 160 GB, 4 TB) | "an additional 20% charge based on the instance's base hourly or monthly price" | not itemised by the API | `https://api.vultr.com/v2/plans` (pricing page blocks automated fetch); https://docs.vultr.com/support/platform/billing/how-much-does-it-cost-to-enable-automatic-backups |
| **Hetzner Cloud US (ASH1/HIL1)** | CPX11 $20.49 (2 vCPU, 40 GB, 1 TB) | CPX21 $37.49 (3 vCPU, 80 GB, 2 TB) | CPX31 $73.49 (4 vCPU, 160 GB, 3 TB) | daily, 7 slots; percentage not shown on the pages fetched (**unverified**) | primary IPv4 "€ 0.50 ($ 0.60) monthly" (https://docs.hetzner.com/general/infrastructure-and-availability/ipv4-pricing/) | `https://website-price-api.hetzner.com/api/v1/products/CLOUD_121` (CPX11), `CLOUD_123` (CPX21), `CLOUD_125` (CPX31); US CPX11 went from $0.0112/h to $0.0328/h on 15 June 2026 — https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/ |

Verdict: DigitalOcean, Linode and Vultr are within $3/mo of Lightsail at 2 GB and 4 GB with backups included, on a plain Ubuntu box with the same Caddy + systemd/Docker recipe. Lightsail wins only because of the TechSoup credit and the 90-day trial; without them DigitalOcean 2 GB/4 GB is the equal-simplicity runner-up. Hetzner US is no longer competitive.

## 4. DNS and TLS

1. **SiteGround A record.** Client Area › Services › Domains › Settings › **DNS Zone Editor** (Site Tools carries the same editor under Domain › DNS Zone Editor): add an **A** record, Name `social`, Value = the Lightsail static IPv4, TTL default. "If you want to edit an A record so that part of your site points to another server, you need to know the IPv4 address of this server and insert it in the corresponding field" — https://www.siteground.com/kb/manage-dns-records/. Nothing else in the zone changes; gitavalley.org WordPress stays on SiteGround.
2. **Attach a static IP first** (free while attached) so the A record never goes stale after a stop/start — Lightsail static-IP doc above.
3. **Lightsail firewall:** keep 22 (restrict to the admin's IP or, better, close it and use Tailscale SSH — §5), keep 80, **add HTTPS 443**. All outbound is already allowed.
4. **Caddy automatic HTTPS** activates when "your domain's A/AAAA records point to your server", "ports 80 and 443 are open externally" and Caddy can bind them; CAs are Let's Encrypt and ZeroSSL; challenges HTTP-01 (port 80), TLS-ALPN-01 (port 443) or DNS-01; "HTTP is redirected to HTTPS" automatically — https://caddyserver.com/docs/automatic-https. A two-line Caddyfile (`social.gitavalley.org { reverse_proxy 127.0.0.1:8000 … }`) replaces nginx-as-TLS-terminator; keep nginx only for the SPA if preferred, or let Caddy `file_server` it.
5. **Alternative — Lightsail load balancer + Lightsail certificate:** $18/mo, free DNS-validated cert, HTTP→HTTPS redirect, health checks; built for multi-instance HA. For one instance it doubles the bill to avoid installing Caddy. Not recommended.

## 5. Access control for an internal tool on the public internet

What exists today: the Hub has JWT bearer auth (`api/auth.py` — single shared password, HS256 tokens, in-process failed-attempt lockout keyed on the socket client IP; 17 of 19 routers depend on `get_current_user`). Two deployment gotchas: (1) `_get_client_ip` deliberately ignores `X-Forwarded-For`, so behind Caddy on the same host every client is `127.0.0.1` and the lockout becomes global (one attacker locks out staff) — either trust the proxy header from localhost only or move rate limiting to Caddy; (2) the lockout table is per-process and lost on restart (comment in the file).

| Option | Requirements | Cost | Fit for 1–3 staff on home/mobile IPs |
|---|---|---|---|
| **(a) App-level auth + proxy hardening + fail2ban** | Keep the JWT login; optionally add Caddy `basic_auth` as a second gate ("Caddy configuration does not accept plaintext passwords; you MUST hash them" via `caddy hash-password`, bcrypt default — https://caddyserver.com/docs/caddyfile/directives/basic_auth); HTTP rate limiting is **not** built into Caddy — `mholt/caddy-ratelimit` must be compiled in with `xcaddy build --with github.com/mholt/caddy-ratelimit` (https://github.com/mholt/caddy-ratelimit); fail2ban "scans log files like /var/log/auth.log and bans IP addresses conducting too many failed login attempts … by updating system firewall rules" (https://github.com/fail2ban/fail2ban) — protects sshd, and can watch Caddy's JSON access log for 401s | $0 | **Baseline — required regardless of the options below.** Works from any network, no client software. |
| **(b) Cloudflare Access / Zero Trust** | Access needs "An active domain on Cloudflare … Domains must belong to an active zone in your Cloudflare account", in either full or partial (CNAME) setup — https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/. "A primary setup (also known as full) is … the only one available for Free or Pro plans" and means moving gitavalley.org's nameservers to Cloudflare — https://developers.cloudflare.com/dns/zone-setups/full-setup/. "A CNAME setup (partial) is only available to customers on a Business or Enterprise plan" — https://developers.cloudflare.com/dns/zone-setups/partial-setup/; Business is "$200 /mo billed annually, or $250/mo billed monthly" (https://www.cloudflare.com/plans/network-cdn/; the Business page lists "Partial (CNAME) DNS setup"). Zero Trust itself: free plan "protects up to 50 users at no cost" (https://blog.cloudflare.com/teams-plans/, 2020 — the current plans page renders prices client-side and could not be confirmed on this fetch) | $0 for Access, **but either move the whole zone to Cloudflare (free, DNS-only mode keeps SiteGround hosting) or pay $200/mo** | **Not feasible for `social.` alone while DNS stays at SiteGround.** Worth revisiting only if the temple agrees to host gitavalley.org DNS at Cloudflare (a one-time nameserver change; all existing records must be copied first). Best UX of all options once available (identity-provider login, no server-side auth code exposed). |
| **(c) Tailscale (+ Serve/Funnel)** | Personal plan "$0 Free forever … Unlimited user devices · Up to 6 users" (https://tailscale.com/pricing); "Charities, not-for-profit organizations, and educational institutions receive a 50% discount" on paid plans (https://tailscale.com/docs/account/manage-plans/free-plans-discounts). **Serve** exposes a local port only inside the tailnet with automatic HTTPS and identity headers (`Tailscale-User-Login` …) — https://tailscale.com/kb/1312/serve; **Funnel** exposes it publicly, "only listen on ports 443, 8443, and 10000", "subject to non-configurable bandwidth limits" — https://tailscale.com/kb/1223/funnel | $0 | **Best for admin SSH** (close port 22 entirely) and a good way to make the Hub tailnet-only if the org ever wants zero public exposure. Requires the Tailscale app on each staff device. Postiz cannot sit behind Serve: OAuth redirects and media fetch by Meta/TikTok need a public HTTPS origin. Funnel's bandwidth cap makes it a poor front door for media uploads. |
| **(d) AWS-native: Lightsail firewall allowlist / Client VPN** | Firewall source-IP rules (up to 60 per protocol family) — useless against rotating home/mobile IPs. AWS Client VPN: "$0.10 per hour in AWS Client VPN endpoint hourly fees" + "$0.05 per connection per hour" (https://aws.amazon.com/vpn/pricing/) ≈ **$73/mo standing** + connections | ≈ $73+/mo | No. |

**Recommendation:** (a) as the baseline (fix the proxy-IP gotcha, enable `basic_auth` only if the app login is ever found wanting, fail2ban on sshd) **plus** (c) Tailscale for SSH/admin so port 22 is closed to the internet. Revisit (b) if the domain's DNS moves to Cloudflare.

## 6. Operations

| Area | Recommendation | Evidence |
|---|---|---|
| Backups | **Both**: Lightsail automatic snapshots (daily, 7 kept, whole-box restore incl. OS and Docker volumes; ~$0.50–4/mo) **and** a nightly cron that writes a consistent SQLite copy (use SQLite's online backup — `sqlite3 gvsa.db ".backup /tmp/gvsa-YYYYMMDD.db"` — never `cp` a live WAL database) and runs `aws s3 sync media/ s3://…/media/` + uploads the DB copy with a 30-day lifecycle rule. ≈ $0.05/mo. The S3 copy is what survives an accidental instance delete (automatic snapshots are deleted with the instance). | §2.1 snapshots, §2.7 S3 |
| Updates | Ubuntu `unattended-upgrades` for security patches; monthly: `apt full-upgrade`, `git pull && pip install -e .`, frontend rebuild, restart; if co-hosting Postiz, `docker compose pull && docker compose up -d` (release cadence and security patches in `postiz-hosting-migration.md` §1). Restart = `systemctl restart gvsa-backend` (see `reference_backend_service.md` for the SIGTERM gotcha in the current unit). | repo `gvsa-backend.service` |
| Monitoring | **UptimeRobot Free: "50 monitors", "5 min. monitoring interval", email/SMS/voice alerts** (https://uptimerobot.com/pricing/) on `https://social.gitavalley.org/api/health` — catches the box, Caddy, the API and (via the health endpoint) Postiz/Claude reachability. **Lightsail alarms** (2 per metric; email + SMS) on CPU utilization, burst-capacity and status-check metrics for host-level problems. | §2.1 |
| Docker vs systemd | **Hub only:** systemd unit + venv as today (fewer moving parts, no daemon to patch, the Claude CLI path already handled). **Hub + Postiz:** Docker is required for Postiz anyway, and the repo's `docker-compose.yaml` already defines `content-hub` and `content-frontend` services alongside the Postiz stack — run everything under one compose file with Caddy as a container or host service, one `docker compose pull && up -d` for updates, named volumes for `data/`, `media/` and `postiz-uploads` (all captured by instance snapshots). | repo `docker-compose.yaml` lines 134–147 |
| Logs | journald with `SystemMaxUse=500M` (systemd path) or Docker `json-file` driver with `max-size`/`max-file` (compose path); Caddy JSON access log with `roll_keep` — keep 14–30 days, nothing longer is needed for a 3-user tool. | — |
| Secrets | `.env` on the box with 600 permissions (JWT secret, Postiz key, Anthropic key or CLI OAuth profile); the Claude CLI profile lives in the service user's home — complete `claude` login once over SSH after provisioning. | `gvsa-backend.service` comment |
| Time | Provisioning: ~half a day (instance, DNS, Caddy, service, backups, monitors, Tailscale). Ongoing: **≈ 1–2 h/month** (updates + a glance at alerts) plus a quarterly 30-minute restore drill. | — |

## 7. Sizing and co-hosting

Measured: Hub ≈ 0.2 GiB (backend 127 MB + nginx 11 MiB + Caddy, before a Claude CLI subprocess); Postiz stack ≈ 1.77 GiB idle, of which 790 MiB is Temporal's Elasticsearch (256 MB heap + JVM) — §1. Add ~0.3 GiB for the OS and Docker, and headroom for Node (Claude CLI) and image pulls.

| Scenario | RAM math | Bundle | Why |
|---|---|---|---|
| **(a) Hub only** (Postiz Cloud or Postiz on another box) | 0.2 + OS 0.3 + Claude CLI/Node ~0.3 + page cache ≈ 1 GB | **2 GB ($12)** — not 1 GB | 1 GB would run it, but a single Claude generation plus an `apt` upgrade would swap; 2 GB has a 20 % CPU baseline and 60 GB disk (media growth) for $5 more. 4 GB buys nothing here. |
| **(b) Hub + self-hosted Postiz** | 0.2 + 1.77 + OS/Docker 0.3 + Claude CLI 0.3 ≈ 2.6 GB idle, peaks higher (Postiz spawns 32 provider workers; ES GC) | **4 GB ($24) floor; 8 GB ($44) if credit-funded** | 4 GB matches the prior research's floor for Postiz alone with enough left for the Hub; Postiz's own recommended spec is 8 GB (`postiz-hosting-migration.md` §1). Enable a 2 GB swapfile on the 4 GB bundle. |

Co-hosting trade-off: one box halves the ops surface (one snapshot, one Caddy, one Tailscale node, one monthly update window) and the Hub talks to Postiz over localhost. The cost is blast radius — a Postiz memory spike or a bad `compose pull` can take the Hub down with it, and the box must stay public for Postiz's OAuth/media even if the Hub could otherwise hide behind Tailscale. Separate boxes ($12 + $24 = $36 vs $24–44) are justified only if the Hub must remain reachable while Postiz is being rebuilt, or if the org wants the Hub tailnet-only.

## 8. Cost table and recommendation

Monthly, list price, us-east-1 / US-East, fetched 2026-09-07.

| Option | (a) Hub only $/mo | (b) Hub + Postiz $/mo | Backups | Ops burden | Fit |
|---|---|---|---|---|---|
| **Lightsail 2 GB / 4 GB / 8 GB** | **$12** (+ ~$0.5–4 snapshots + $0.05 S3) | **$24 or $44** (+ ~$1–4 snapshots + $0.05 S3) | Auto snapshots 7 daily + S3 | Low (console firewall/static IP/snapshots; Caddy + systemd or compose) | **Recommended**; ≈ $0 hosting under TechSoup ($95/yr) or the 90-day trial + $200 credits on a new account |
| DigitalOcean Basic 2 GB / 4 GB / 8 GB + weekly backups | $14.40 | $28.80 / $57.60 | Provider weekly (or daily +30 %) + S3/Spaces | Low, identical recipe | **Runner-up** for both (a) and (b) |
| Linode 2 GB / 4 GB / 8 GB + Backups | $14.50 | $29 / $58 | Provider add-on | Low | Equivalent alternate |
| Vultr 2 GB (2 vCPU) / 4 GB / 8 GB + 20 % backups | $18 (or $12 at 1 vCPU) | $24 / $48 | Provider +20 % | Low | Cheapest at 4 GB; pricing page not machine-readable, verify IPv4 at checkout |
| Hetzner US CPX11 / CPX21 / CPX31 | $20.49 | $37.49 / $73.49 | 7-slot daily (price unverified) | Low | No — repriced June 2026 |
| EC2 t4g.small / t4g.medium + IPv4 + gp3 + snapshots | ≈ $19–20 | ≈ $35–37 | EBS snapshots $0.05/GB-mo (DLM policy) | Medium (SG, EIP, EBS, IAM) | No benefit over Lightsail at this size |
| ECS Fargate + EFS + ALB (0.5 vCPU/1 GB … 1 vCPU/2 GB) | ≈ $40–45 | ≈ $60+ (Postiz would need its own tasks + RDS) | EFS backup/S3 | High | No — cost, complexity, SQLite-on-NFS |
| Elastic Beanstalk single instance | EC2 cost + EFS | — | — | Medium-high | No — "no persistent local storage" |
| App Runner | — | — | — | — | Closed to new customers |
| Lightsail Containers Micro/Small | $10–15 | — | none possible | Low | No — ephemeral storage |

**Recommendation (a) — Hub only: AWS Lightsail 2 GB Linux bundle ($12/mo) in us-east-1**, Ubuntu blueprint, static IP attached, firewall 80/443 open (22 closed, Tailscale for SSH), Caddy for HTTPS at `social.gitavalley.org` via one SiteGround A record, backend under systemd as today, automatic snapshots on, nightly SQLite `.backup` + media sync to S3, UptimeRobot + two Lightsail alarms. Apply for the TechSoup AWS credit ($1,000 for $95) so hosting is effectively covered; a brand-new AWS account on the paid plan also gets the $12 bundle free for 90 days plus $100–200 in credits. **Runner-up:** DigitalOcean Basic 2 GB in NYC with weekly backups ($14.40/mo) — same recipe, no credit programme, choose it if the org would rather not open an AWS account.

**Recommendation (b) — Hub + self-hosted Postiz: Lightsail 4 GB ($24/mo) minimum, 8 GB ($44/mo) if the TechSoup credit is secured**, everything under the repo's single `docker-compose.yaml` (Postiz stack + `content-hub` + `content-frontend` + Caddy), named volumes, automatic snapshots + S3 for `gvsa.db`, `media/` and a `pg_dump` of Postiz. This is the same host the earlier Postiz research already picked, so the two decisions converge on one box. **Runner-up:** DigitalOcean 4 GB ($28.80 with weekly backups; $57.60 at 8 GB).

Sequencing note (from `postiz-hosting-migration.md` §6): fix the final hostnames (`social.gitavalley.org` for the Hub; the Postiz hostname) **before** submitting the Meta/TikTok/Google app reviews — redirect-URI changes are review-relevant.

## Open items / uncertainty

- **TechSoup tiers:** techsoup.org product/FAQ pages block automated fetch (bot page); the $1,000/$95/12-month offer is verified on page.techsoup.org; the budget-based $2,000/$5,000 tiers come from search snippets only. Confirm in the TechSoup catalogue when applying; the AWS page caps the programme at $5,000/fiscal year.
- **Does the temple already have an AWS account?** Accounts created before 15 July 2025 stay on the legacy Free Tier and are "ineligible for Free Tier credits or the free account plan"; the Lightsail 90-day trial page says "with the Paid plan". A new account created for this project is the clean path.
- **Lightsail snapshot billing granularity** (how much of a 60 GB disk a daily snapshot bills) is not stated on the pages fetched; check the first invoice.
- **Cloudflare Zero Trust free-plan seat count (50)** comes from Cloudflare's 2020 launch post; the current plans page renders prices client-side and returned no figures. Irrelevant unless the zone moves to Cloudflare.
- **Hetzner backup pricing** (percentage) and **Vultr IPv4 add-on** were not readable from the pages/APIs fetched.
- **Claude CLI on a headless server:** the CLI's OAuth profile must be created once over SSH in the service user's home (or use an `ANTHROPIC_API_KEY`); whether the Max-subscription OAuth flow is permitted for a shared server process is a licensing question not answered by any page fetched here.
- **Hub auth behind a reverse proxy:** `_get_client_ip` ignores proxy headers, so the login lockout keys on `127.0.0.1` once Caddy fronts the app — decide whether to trust `X-Forwarded-For` from localhost or move brute-force protection to Caddy/fail2ban before going public.
- **Postiz + Hub on 4 GB** is an estimate from idle measurements on a 26 GB box; watch `docker stats` and the Lightsail memory/burst metrics for the first two weeks and upsize from a snapshot if needed (snapshots can restore to a larger bundle, never a smaller one).

## Sources (fetched 2026-09-07/08 UTC)

| Source | Status |
|---|---|
| https://aws.amazon.com/lightsail/pricing/ | OK (bundles, IPv6-only, snapshots $0.05/GB-mo, block storage $0.10/GB-mo, LB $18, container powers, "Static IP address … Included in all Lightsail plans") |
| https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html | OK (full bundle tables, IPv4 vs IPv6-only) |
| https://docs.aws.amazon.com/lightsail/latest/userguide/baseline-cpu-performance.html | OK (baselines) |
| https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-configuring-automatic-snapshots.html | OK (7 dailies, billing, deletion with resource) |
| https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html | OK |
| https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html | OK |
| https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html | OK |
| https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-alarms.html | OK |
| https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-lightsail-load-balancers.html | OK |
| https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-container-services.html, …/amazon-lightsail-faq-containers.html | OK (no storage feature documented) |
| https://repost.aws/questions/QU8GVkIsWOQGqedjXWLD91fA/volumes-with-containers-in-amazon-lightsail | Secondary (AWS re:Post) — "no disks" claim |
| https://aws.amazon.com/lightsail/faq/ | OK (static IP fee, snapshot price, $0.09/GB overage, Lightsail vs EC2, LB certs) |
| https://aws.amazon.com/blogs/compute/announcing-ipv6-instance-bundles-and-pricing-update-on-amazon-lightsail/ | OK (1 May 2024 repricing; price tables are images) |
| https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/ | OK ($0.005/h from 1 Feb 2024) |
| https://aws.amazon.com/free/compute/lightsail/ | OK (90-day trial on the paid plan) |
| https://aws.amazon.com/free/, https://aws.amazon.com/free/free-tier-faqs/, https://aws.amazon.com/blogs/aws/aws-free-tier-update-new-customers-can-get-started-and-explore-aws-with-up-to-200-in-credits/ | OK (credits model, 15 July 2025 cut-over) |
| https://aws.amazon.com/government-education/nonprofits/nonprofit-credit-program/ | OK |
| https://page.techsoup.org/aws | OK ($1,000 / $95 / 12 months) |
| https://www.techsoup.org/products/amazon-web-services-credit-for-smaller-nonprofits-g-50197- (+ medium/larger pages, FAQ, support.techsoup.org article) | **Blocked** (bot page / 403) — tiers unverified |
| https://blog.techsoup.org/posts/what-you-need-to-know-about-changes-to-techsoups-aws-credits-program | OK (2021; fiscal-year rule) |
| EC2 on-demand feed `https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US East (N. Virginia)/Linux/index.json` | OK (gzip) |
| https://aws.amazon.com/ebs/pricing/ | OK (gp3 $0.08, snapshots standard $0.05) |
| `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json` (published 2026-08-31) | OK |
| `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEFS/current/us-east-1/index.json` (published 2026-08-31) | OK |
| https://aws.amazon.com/s3/pricing/, https://aws.amazon.com/efs/pricing/ | Rendered without price tables (JS); figures taken from the offer files above |
| https://aws.amazon.com/fargate/pricing/, https://aws.amazon.com/elasticloadbalancing/pricing/, https://aws.amazon.com/apprunner/pricing/, https://aws.amazon.com/elasticbeanstalk/pricing/, https://aws.amazon.com/vpn/pricing/ | OK |
| https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html, …/architecture.html | OK (closed to new customers; ECS Express Mode) |
| https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/concepts.concepts.design.html | OK |
| https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html | OK |
| https://www.sqlite.org/howtocorrupt.html | OK (§2.1 NFS locking) |
| https://www.digitalocean.com/pricing/droplets | OK |
| https://api.linode.com/v4/linode/types | OK (https://www.linode.com/pricing/ → akamai.com/cloud/pricing renders regionally, no tables) |
| https://api.vultr.com/v2/plans; https://docs.vultr.com/support/platform/billing/how-much-does-it-cost-to-enable-automatic-backups | OK (pricing page 403) |
| https://website-price-api.hetzner.com/api/v1/products/CLOUD_121 / 123 / 125; https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/; …/ipv4-pricing/; https://docs.hetzner.com/cloud/servers/backups-snapshots/overview/ | OK (backup % not on these pages; hetzner.com/cloud renders prices client-side) |
| https://www.siteground.com/kb/manage-dns-records/ | OK |
| https://caddyserver.com/docs/automatic-https, https://caddyserver.com/docs/caddyfile/directives/basic_auth | OK |
| https://github.com/mholt/caddy-ratelimit, https://github.com/fail2ban/fail2ban | OK |
| https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/, https://developers.cloudflare.com/dns/zone-setups/full-setup/, https://developers.cloudflare.com/dns/zone-setups/partial-setup/ | OK |
| https://www.cloudflare.com/plans/network-cdn/ (Free $0, Pro $20/$25, Business $200/$250), https://www.cloudflare.com/plans/business/ ("Partial (CNAME) DNS setup") | OK |
| https://www.cloudflare.com/plans/zero-trust-services/ | Rendered without figures; https://blog.cloudflare.com/teams-plans/ (2020) used for the 50-user free tier |
| https://tailscale.com/pricing, https://tailscale.com/docs/account/manage-plans/free-plans-discounts, https://tailscale.com/kb/1312/serve, https://tailscale.com/kb/1223/funnel | OK |
| https://uptimerobot.com/pricing/ | OK |
| Local: `systemctl show gvsa-backend`, `docker stats`, `du -sh data`, `gvsa-backend.service`, `docker-compose.yaml`, `api/auth.py`, `api/main.py:112` | OK |
