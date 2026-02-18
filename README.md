# Postiz Social Media Automation - Gita Valley

Social media scheduling and automation for ISKCON Gita Valley using [Postiz](https://postiz.com), connected to n8n for AI-powered content workflows.

## Architecture

```
Content Calendar (n8n) -> AI Captions (n8n/Claude) -> Postiz API -> Instagram, Facebook, TikTok
```

### Stack

| Service | Purpose | Port |
|---------|---------|------|
| Postiz | Social media scheduler | 4007 |
| PostgreSQL | Postiz database | internal |
| Redis | Postiz cache | internal |
| Temporal | Workflow engine | 7233 |
| Temporal UI | Workflow dashboard | 8080 |
| Temporal PostgreSQL | Temporal database | internal |
| Temporal Elasticsearch | Temporal search | internal |

## Quick Start

1. Copy `.env.example` to `.env` and fill in secrets (a JWT secret is pre-generated in `.env`):

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

2. Start the stack:

```bash
make up
```

3. Wait for all services to become healthy (~30-60 seconds):

```bash
make status
```

4. Open Postiz at [http://localhost:4007](http://localhost:4007) and register your first user account.

5. Find your API key: **Settings -> API** in the Postiz dashboard.

## Common Commands

```bash
make up        # Start all services
make down      # Stop all services
make logs      # Follow Postiz logs
make restart   # Stop + start
make status    # Show service status
make clean     # Remove everything including data (destructive!)
```

## n8n Integration

The n8n instance at `n8n.sethpc.xyz` has the `n8n-nodes-postiz` community node (v0.2.17) installed.

See [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md) for connection setup.

## Social Media Setup

After Postiz is running, connect social accounts through the Postiz dashboard:

1. **Instagram** - Connected via Facebook Business (requires Facebook App)
2. **Facebook** - Direct page connection
3. **TikTok** - Requires TikTok Developer App

API keys for these platforms go into the `.env` file or are configured directly in the Postiz dashboard under Settings.
