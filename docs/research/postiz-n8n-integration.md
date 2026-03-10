# Postiz + n8n Integration — Research

Date: 2026-02-24
Sources: docs.postiz.com, github.com/gitroomhq/postiz-n8n, npm n8n-nodes-postiz

## Critical Finding: Use HTTP Request, Not Custom Node

The `n8n-nodes-postiz` custom node (v0.2.17) has critical bugs:

| Issue | Severity | Status |
|-------|----------|--------|
| [#7](https://github.com/gitroomhq/postiz-n8n/issues/7): 400 errors on Instagram/Reddit (hardcoded nesting) | **HIGH** | OPEN |
| [#6](https://github.com/gitroomhq/postiz-n8n/issues/6): Nodes break after version updates | HIGH | OPEN |
| [#4](https://github.com/gitroomhq/postiz-n8n/issues/4): Self-hosted connectivity issues | MEDIUM | OPEN |
| [#5](https://github.com/gitroomhq/postiz-n8n/issues/5): Video upload not supported | LOW | OPEN |
| [#8](https://github.com/gitroomhq/postiz-n8n/issues/8): No upload-from-URL | LOW | OPEN |

**Recommendation**: Use n8n HTTP Request nodes for all Postiz API calls.

## API Reference

### Authentication

```
Header: Authorization: <api-key>
(No Bearer prefix)
```

### Base URL

```
Self-hosted: https://postiz.sethpc.xyz/api/public/v1
```

### Rate Limit

**30 requests/hour** across all endpoints.

Optimization strategies:
- Batch multiple platforms in a single POST /posts request
- Cache GET /integrations response (don't re-fetch per run)
- With media: ~15 content pieces/hour (upload + post = 2 calls each)
- Text-only: ~30 posts/hour

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /integrations | List connected social channels |
| POST | /posts | Create/schedule posts |
| GET | /posts?startDate=&endDate= | List posts in date range |
| DELETE | /posts/{id} | Delete a post |
| POST | /upload | Upload media file (returns { id, path }) |
| POST | /upload-from-url | Upload media from URL |
| GET | /is-connected | Check if API key is valid |

### Post Creation Payload (Verified Working)

```json
{
  "type": "now",
  "date": "2026-02-24T10:00:00Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "channel-id-from-integrations" },
      "value": [
        {
          "content": "Post text here with #hashtags",
          "image": [
            {
              "id": "upload-id-from-upload-endpoint",
              "path": "https://uploads.example.com/photo.jpg"
            }
          ]
        }
      ],
      "settings": {
        "post_type": "post",
        "media_type": "IMAGE"
      }
    }
  ]
}
```

**Key details**:
- `type`: "now" (immediate), "schedule" (use `date` field), "draft"
- `posts` array: one entry per platform/channel
- `integration.id`: from GET /integrations response
- `value` array: content blocks (supports multi-image carousels)
- `settings`: platform-specific (varies by provider)

### Integration Response Format

```json
[
  {
    "id": "cm4ean69r0003w8w1cdomox9n",
    "name": "Display Name",
    "identifier": "instagram",
    "picture": "url",
    "disabled": false,
    "profile": "@handle"
  }
]
```

## n8n Workflow Architecture (Recommended)

```
1. Schedule Trigger (cron or Google Sheets trigger)
    ↓
2. Google Sheets: Read rows where status = "ready"
    ↓
3. AI Node (Claude): Generate platform-specific captions
    ↓
4. Google Sheets: Write captions back to sheet
    ↓
5. Google Sheets: Update status to "pending_approval"
    ↓
--- Human approval step (manual status change to "approved") ---
    ↓
6. Schedule Trigger: Check for status = "approved"
    ↓
7. HTTP Request: GET /integrations (cache if possible)
    ↓
8. HTTP Request: POST /upload (if media_url provided)
    ↓
9. Code Node: Build Postiz payload (platform routing + settings)
    ↓
10. HTTP Request: POST /posts (batch all platforms in one call)
    ↓
11. Google Sheets: Update status to "posted", write postiz_ids + timestamp
    ↓
12. Error Handler: Update status to "error", write error_msg
```

## Postiz MCP Server

Postiz exposes an MCP server for direct AI-assisted scheduling:
- URL: Available in Settings > Public API
- Protocol: HTTP streaming
- Use case: Claude can schedule posts directly without n8n

This is a potential future simplification — Claude reads Sheet, generates captions,
and schedules directly via MCP, bypassing n8n entirely for simple workflows.

## Payload Wizard

Postiz provides a built-in payload wizard (Settings > Public API > "Open the payload wizard")
that generates correct JSON payloads from UI input. Useful for discovering
platform-specific settings without trial and error.
