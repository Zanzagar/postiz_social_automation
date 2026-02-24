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

## Connectivity Issues

- No `/api/health` endpoint exists (404). Use `/api/` ("App is running!") for health checks.
- Timezone verification requires authenticated login — not verified from CLI.
- API key not available in this session — authenticated endpoint testing deferred to Task 2.

## Health Check Script

See `scripts/postiz-health-check.sh` for automated verification.
