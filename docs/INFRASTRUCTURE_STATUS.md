# Infrastructure Status

Last verified: 2026-02-24

## Service URLs

| Service | URL | Status | Notes |
|---------|-----|--------|-------|
| Postiz Dashboard | https://postiz.sethpc.xyz/ | OK (HTTP 200) | Redirects to /auth when unauthenticated |
| Postiz API | https://postiz.sethpc.xyz/api/ | OK (HTTP 200) | Returns "App is running!" |
| Postiz Swagger Docs | https://postiz.sethpc.xyz/api/docs | OK (HTTP 200) | 148 endpoints documented |
| n8n | https://n8n.sethpc.xyz/ | OK (HTTP 200) | Separate host from Postiz |

## Service Versions (from docker-compose.yaml)

| Service | Image | Version | Port |
|---------|-------|---------|------|
| Postiz | ghcr.io/gitroomhq/postiz-app | latest | 4007→5000 |
| PostgreSQL (Postiz) | postgres | 17-alpine | internal |
| Redis | redis | 7.2 | internal |
| Temporal | temporalio/auto-setup | 1.28.1 | 7233 |
| Temporal PostgreSQL | postgres | 16 | internal |
| Temporal Elasticsearch | elasticsearch | 7.17.27 | internal |
| Temporal UI | temporalio/ui | 2.34.0 | 8080 |

## API Surface

Postiz exposes 148 API endpoints. Key endpoint groups for automation:

| Group | Example Endpoints | Auth Required |
|-------|-------------------|---------------|
| Posts | `/posts`, `/posts/list`, `/posts/{id}` | Yes |
| Integrations | `/integrations`, `/integrations/list` | Yes |
| Media | `/media`, `/media/upload-simple` | Yes |
| Analytics | `/analytics/{integration}` | Yes |
| Public API v1 | `/public/v1/posts`, `/public/v1/integrations` | API Key |

The `/public/v1/*` endpoints are the external API for n8n integration.

## API Authentication

- **Auth header**: `Authorization: <api-key>` (no Bearer prefix)
- **Base URL**: `https://postiz.sethpc.xyz/api/public/v1`
- **Rate limit**: 30 requests/hour
- **API key location**: Settings > Public API in Postiz dashboard
- **Postiz version**: v2.18.0 (confirmed via dashboard)
- **n8n custom node**: `n8n-nodes-postiz` (available on npm)
- **Postiz MCP server**: Available (HTTP streaming, URL in Settings > Public API)

## Connectivity Notes

- No `/api/health` endpoint exists (404). Use `/api/` ("App is running!") for health checks.
- Dashboard login works (email/password auth verified).
- API key tested and working against `/public/v1/integrations`.
- No channels connected yet (empty integrations array).

## Health Check Script

See `scripts/postiz-health-check.sh` for automated verification.
