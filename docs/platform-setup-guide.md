# Platform Setup Guide

## Priority Platforms (from temple president)

1. **Facebook** — Ready (in Meta Business Suite)
2. **Instagram** — In progress (adding to Meta Business Suite)
3. **YouTube** — Needs Google account with channel ownership
4. **TikTok** — No account yet, needs to be created

## Platform Accounts

| Platform | Account | Status | Login Email |
|----------|---------|--------|-------------|
| Facebook | Gita Valley Page | In Meta Business Suite | corey@gitavalley.org (admin) |
| Instagram | Gita Valley IG | Adding to Meta Business Suite | TBD |
| Threads | Auto-linked to IG | Pending IG setup | — |
| YouTube | Gita Valley channel | Needs setup | TBD |
| TikTok | None yet | Needs account creation | TBD |
| LinkedIn | TBD | Not priority | TBD |
| X/Twitter | TBD | Not priority | TBD |
| Google Business Profile | TBD | Not priority | TBD |

## Developer Apps (for API access through Postiz)

| Platform | Portal | What You Need | Status |
|----------|--------|---------------|--------|
| Meta (FB/IG/Threads) | developers.facebook.com | Meta Business Suite admin. Create app → Dev Mode → add accounts as testers. Privacy policy: gitavalley.org/privacy-policy/ | Not started |
| YouTube | console.cloud.google.com | Google account with channel ownership. OAuth consent screen in "External Testing" mode (up to 100 test users, no review). | Not started |
| TikTok | developers.tiktok.com | TikTok account + app registration | Blocked — no account yet |

## Infrastructure Logins

| Service | Purpose | Access | Status |
|---------|---------|--------|--------|
| Postiz (postiz.sethpc.xyz) | Scheduling engine — connect platform apps here | Need admin login from Seth | TBD |
| Google Sheets | Content source — staff enters posts | Google service account (credentials.json) | Not configured |
| Google Drive | Media storage | Same Google account as Sheets | Not configured |
| Claude | AI caption generation | Max subscription / OAuth | Working |
| Seth's server (sethpc.xyz) | SSH for Postiz config, Docker management | Seth has access | Available |
| Meta Business Suite | Facebook/IG page management | corey@gitavalley.org | Active |

## Setup Sequence

1. **Meta Developer App** — Create at developers.facebook.com, Dev Mode, add FB + IG as testers
2. **Connect FB + IG in Postiz** — Use developer app credentials at postiz.sethpc.xyz
3. **Google Cloud Project** — Create at console.cloud.google.com, enable YouTube Data API
4. **Connect YouTube in Postiz** — Use Google OAuth credentials
5. **Create TikTok account** — Then register developer app at developers.tiktok.com
6. **Connect TikTok in Postiz** — Use TikTok app credentials
7. **Google Sheets service account** — Create at console.cloud.google.com, download credentials.json
8. **Configure .env** — Set real POSTIZ_API_KEY, SPREADSHEET_ID, GOOGLE_SHEETS_CREDENTIALS

## Notes

- Meta Development Mode avoids the 1+ month full app review process
- Only accounts added as testers can post — fine for single-org use
- Privacy policy already exists: https://gitavalley.org/privacy-policy/
- Threads auto-connects when Instagram is linked to Meta Business Suite

*Last updated: 2026-03-16*
