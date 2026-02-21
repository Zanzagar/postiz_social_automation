# Gita Valley — Social Media Automation Project Context

> Reference document for Claude Code development sessions.
> Last updated: February 18, 2026

---

## Infrastructure

| Service | URL | Notes |
|---|---|---|
| **Postiz** | https://postiz.sethpc.xyz | Social media scheduler (self-hosted, open source) |
| **n8n** | https://n8n.sethpc.xyz | Workflow automation |
| **Repo** | https://github.com/Zanzagar/postiz_social_automation | Public |

- Postiz API Key: `fc03fe1e9b2f432837aeb00bdb35f6e238e95a23fac150d9651a6f477abd887d`
- Postiz host in n8n credential: `https://postiz.sethpc.xyz`
- n8n community node: `n8n-nodes-postiz` v0.2.17 (installed, credential tested ✅)
- Both services on Seth's server behind reverse proxies — must communicate via public URLs
- Postiz internal: 192.168.0.232:4007 / n8n internal: 192.168.0.133:5678

---

## The Client: Gita Valley

**What they are:** 430-acre regenerative eco-farm and cow sanctuary in Port Royal, Pennsylvania. The only USDA-certified slaughter-free dairy in North America. Certified 501(c)(3) nonprofit. Founded 1974 as "Gita Nagari" by Swami Prabhupada, officially rebranded to "Gita Valley."

**Key facts:**
- 85 cows total, 16 producing milk (400 gallons/week)
- $18/gallon ahimsa milk with waitlist of hundreds
- 20 full-time residents, ~24 volunteers
- 3,000 visitors/year via weekend retreats
- University work-study program: 54 spots, 1,200 applications (after one viral TikTok from an intern)
- Gift shop called "Mootique"
- Website: https://gitavalley.org (well-designed, fully rebranded)
- E-commerce: https://shopgitanagari.com (Shopify, still old branding)

---

## Social Media Accounts (as of Feb 9, 2026)

| Platform | Handle | Followers | Last Post | Engagement | Rebranded? |
|---|---|---|---|---|---|
| **Instagram** | @gita.valley | 4,414 | Nov 24, 2025 | ~0.2-0.4% | ✅ Yes |
| **Facebook** | fb.com/gitavalley | 5,700 | Dec 16, 2025 | Unknown | ❌ Still "Gita Nagari Farm" |
| **TikTok** | @gitavalley | 198 | Unknown | 1,290 total likes | ⚠️ Partial (old logo, old link) |
| **Threads** | gita.valley | Unknown | Unknown | Unknown | ✅ Yes |
| **LinkedIn** | /company/gita-valley | Unknown | Unknown | Unknown | ✅ Yes |
| **YouTube** | — | — | — | — | ❌ Doesn't exist |

**Secondary/Legacy accounts:**
- @gnadoptacow (Instagram, Adopt-a-Cow program)
- @gita.nagari.eco.farm (Instagram, abandoned — 5 followers, 0 posts)

**Benchmark:** Farm/sanctuary accounts at 4K followers should see 3-6% engagement. Gita Valley gets 0.2-0.4% — caused by multi-month posting gaps and algorithm deprioritization.

---

## The Problem We're Solving

The farm creates compelling content (atmospheric cow photos, farm life videos, community events) but has **no system for consistent posting**. Content happens daily on a 430-acre photogenic farm — it just doesn't get captured and distributed. Posts happen when someone remembers, resulting in multi-month gaps.

The viral TikTok paradox proves demand exists: one intern's personal TikTok generated 1,200 applications. The official account has 198 followers. The content resonates when it actually gets posted.

---

## Automation Pipeline Architecture

```
Content Source (Google Sheets/Drive)
        │
        ▼
   n8n Trigger (new row / schedule / webhook)
        │
        ▼
   AI Caption Generator (per-platform optimization)
        │
        ▼
   Approval Step (optional — email/Slack notification)
        │
        ▼
   Postiz Node (createPost)
        │
        ├── Instagram (@gita.valley)
        ├── Facebook (fb.com/gitavalley)
        ├── TikTok (@gitavalley)
        └── Threads (gita.valley)
```

**Postiz n8n node fields:**
- Credential (API key — configured ✅)
- Operation: Create Post
- Type: Now | Scheduled
- Date: ISO datetime (for scheduled)
- Tags: array
- Channel ID: maps to connected social account in Postiz (need to connect channels)
- Group: for multi-platform posting
- Content Items: post text + media
- Settings: platform-specific options

**Still needed:**
1. Connect social channels (Instagram, Facebook, TikTok) in Postiz dashboard
2. Build n8n workflows
3. Set up Postiz → n8n webhooks for event-driven flows

---

## Content Strategy (for AI caption generation)

### Content Pillars
| Pillar | Weight | Examples |
|---|---|---|
| Cow personalities & daily life | 40% | Individual cow stories (named: Tabby, Dennis, Sparkle, Daring Denise, Brisham), dawn milking, cow cuddling |
| Farm operations & sustainability | 25% | Regenerative practices, organic certification, maple syrup, apiary, forest stewardship |
| Community & people | 15% | Volunteer spotlights, intern stories, visitor testimonials, retreat highlights |
| Kitchen & food | 10% | Farm-to-table, sattvic/vegetarian cooking, head chef Madhupan, recipes |
| Spiritual dimension | 5% | Morning mantras, bhakti yoga, festival celebrations, meditation |
| Calls to action | 5% | Donate, visit, volunteer, adopt-a-cow, buy products |

### Content Mix Rule: 70/20/10
- 70% value content (education, entertainment, farm life)
- 20% community content (testimonials, spotlights, partnerships)
- 10% ask content (donations, sales, recruitment)

### Posting Cadence Targets
| Platform | Frequency |
|---|---|
| Instagram | 4-5 posts/week + daily Stories |
| Facebook | 3-4 posts/week |
| TikTok | 3-5 short videos/week |
| Threads | Mirror Instagram |
| LinkedIn | 1-2 posts/week |

### Voice & Tone Guidelines
- Warm, welcoming, grounded — not preachy or overly spiritual
- Lead with the cows and the farm, not the religion
- Use "Gita Valley" consistently (never "Gita Nagari" in new content)
- Hashtags observed on recent posts: #farmlife #farmhumor #funnycow #funnyanimals #cows #farmretreat #vlog #gitanagri
- The unique differentiator to always emphasize: "Only USDA Certified Slaughter-Free Dairy Farm"

---

## Rebrand Status (affects content generation)

The automation pipeline should **always use "Gita Valley" branding** in generated content. The rebrand is incomplete across platforms:

- ✅ Website, Instagram, Threads, LinkedIn → "Gita Valley"
- ❌ Facebook page name, TikTok logo/link, Shopify store, all third-party listings → still "Gita Nagari" variants
- ❌ Facebook contact email still points to contact@gnecofarm.org
- ❌ TikTok bio links to gnecofarm.org instead of gitavalley.org

When generating captions, always use:
- Name: "Gita Valley"
- Website: gitavalley.org
- Tagline: "Cultivating Soil and Soul"
- Key claim: "Only USDA Certified Slaughter-Free Dairy Farm in North America"

---

## Photo/Video Asset Repositories

These are existing content archives that could feed the pipeline:

- Alternative Break Quotes (May 2019): https://photos.app.goo.gl/nmWEyRbb2dNJQWX2A
- Parijata Dasi collection (Dec 2019): https://photos.app.goo.gl/uiVnB5wTomLJ76gi7
- GN Farm Videos (Jan 2020–Feb 2021): https://photos.app.goo.gl/WTsiGtD88mysWi4Q8

---

## Key People

- **Seth Freiberg** (seth@sethfreiberg.com) — infrastructure/server admin, hosts Postiz and n8n
- **Dhruva** — farm contact, referenced in ISKCON directories (dhruva.bts@pamho.net)
- **Parijata Dasi (PJ)** — farm owner, has personal video content collection
- **Madhupan** — head chef (content opportunity for cooking content)
- **Temple President** — meeting scheduled, decision-maker for social media strategy
