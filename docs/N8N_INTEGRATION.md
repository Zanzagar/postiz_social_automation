# n8n + Postiz Integration

## Overview

The n8n instance at `n8n.sethpc.xyz` connects to Postiz via the `n8n-nodes-postiz` community node (v0.2.17) to automate social media posting.

## Setup

### 1. Get Postiz API Key

1. Open Postiz at [http://localhost:4007](http://localhost:4007)
2. Go to **Settings -> API**
3. Copy the API key

### 2. Create n8n Credential

1. In n8n, go to **Credentials -> Add Credential**
2. Search for "Postiz"
3. Enter:
   - **API URL**: `http://<postiz-host>:4007/api` (use machine IP if n8n is on a different host)
   - **API Key**: paste from step 1

### 3. Available n8n Operations

The Postiz node supports:
- **Create Post** - Schedule a post to connected social accounts
- **Get Posts** - Retrieve scheduled/published posts
- **Delete Post** - Remove a scheduled post

### 4. Example Workflow: AI Caption + Schedule

```
Trigger (cron/webhook)
  -> Read content calendar (Google Sheets / Airtable)
  -> Generate caption (Claude / OpenAI node)
  -> Upload media to Postiz
  -> Create scheduled post via Postiz node
```

## Network Notes

- If n8n and Postiz are on the same machine, use `http://localhost:4007/api`
- If on different machines, use the Postiz host's IP/hostname
- Postiz must be reachable from the n8n instance on port 4007
