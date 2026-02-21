# Project: Postiz Social Media Automation

Social media scheduling and automation for ISKCON Gita Valley using self-hosted Postiz, connected to n8n for AI-powered content workflows.

## Tech Stack

- Docker / Docker Compose (all services containerized)
- Postiz (open-source social media scheduler) — `ghcr.io/gitroomhq/postiz-app:latest`
- PostgreSQL 17 (Postiz database)
- Redis 7.2 (Postiz cache)
- Temporal 1.28 (workflow engine for Postiz background jobs)
- Elasticsearch 7.17 (Temporal search backend)
- n8n (external, at `n8n.sethpc.xyz`) — AI content generation + scheduling automation

## Structure

```
docker-compose.yaml   # Full stack definition (7 services)
.env / .env.example   # Configuration (secrets, URLs, API keys)
Makefile              # Common operations (up, down, logs, status, clean)
dynamicconfig/        # Temporal dynamic configuration
docs/                 # Integration guides and assessments
.claude/              # AI assistant configuration (from project-template)
```

## Development Commands

```bash
# Start all services
make up

# Stop all services
make down

# View Postiz logs
make logs

# Check service health
make status

# Restart stack
make restart

# Remove everything including data (DESTRUCTIVE)
make clean

# Docker Compose directly
docker compose ps                    # Service status
docker compose logs -f postiz        # Follow Postiz logs
docker compose exec postiz-postgres psql -U postiz-user postiz-db-local  # DB shell
```

## Project-Specific Patterns

- **Infrastructure-only project**: No custom application code. All functionality comes from Postiz (container) + n8n (external)
- **Configuration-driven**: Changes happen in `.env`, `docker-compose.yaml`, and `dynamicconfig/`
- **External integrations**: Social media APIs are configured in the Postiz dashboard (Settings -> API), not in code
- **n8n workflows**: Content automation pipelines live in n8n at `n8n.sethpc.xyz`, not in this repo

## Key Decisions & Constraints

- **Self-hosted over SaaS**: Postiz self-hosted (free) vs hosted ($29-99/mo)
- **Docker-only deployment**: No bare-metal setup — everything runs in containers
- **Temporal for reliability**: Postiz uses Temporal for background job scheduling (posting, analytics)
- **Postiz API rate limit**: 30 requests/hour (beta API) — sufficient for scheduled posting
- **WSL development**: Running on Windows Subsystem for Linux — Docker Desktop required

## Gotchas & Watch-outs

- `.env` contains secrets (JWT_SECRET, database passwords) — never commit
- Temporal needs both PostgreSQL AND Elasticsearch healthy before it starts
- First startup takes ~60 seconds for all health checks to pass
- Postiz runs on port 4007 (maps internal 5000 -> external 4007)
- Social media API keys (Facebook, TikTok, X) are configured in Postiz dashboard, NOT in `.env`
- `make clean` destroys all data including uploaded media and database — use with caution

## Taskmaster Workflows

### Workflow Rules (MANDATORY)

1. **PRD first**: ALWAYS create a PRD before generating tasks. Never use `add-task` to build a task list from scratch — write a PRD in `.taskmaster/docs/`, then parse it.
2. **New tag per phase**: Each workflow phase gets its own tag (e.g., `content-pipeline`, `monitoring`). Never pollute the `master` tag with phase-specific work.
3. **Switch tags**: Always `task-master tags use <name>` before running set-status, show, or list — operations target the active tag.
4. **Expand after parse**: Always run `task-master expand --id=<id>` on complex tasks after parse-prd to generate actionable subtasks.
5. **Float task count**: Use `--num-tasks 0` with parse-prd to let the AI determine the right number of tasks. Don't hardcode counts.

### Commands

```bash
# List tasks for current tag
task-master list --with-subtasks

# Show specific task details
task-master show <id>

# Update task status
task-master set-status --id <id> --status=<status>

# Get next recommended task
task-master next

# Expand task into subtasks
task-master expand --id=<id>

# Parse PRD to generate tasks (use --num-tasks 0 to let AI decide count)
task-master parse-prd <prdfile> --num-tasks 0

# Switch tag context
task-master tags use <tag-name>
```

## Development Workflow

### Daily Loop
1. Check `make status` — ensure all services healthy
2. Check task-master for next task
3. Implement changes (config, docker-compose, scripts, docs)
4. Test with `make restart` + `make status`
5. Small, focused commits

## Current Focus

- [ ] Initial template integration and workflow validation
- [ ] Content automation pipeline (n8n -> AI caption -> Postiz -> social platforms)
- [ ] Monitoring and health check improvements

## Integration Points

### n8n Connection
- n8n instance: `n8n.sethpc.xyz`
- Community node: `n8n-nodes-postiz` v0.2.17
- See `docs/N8N_INTEGRATION.md` for setup

### Social Platforms (via Postiz dashboard)
- Instagram (via Facebook Business)
- Facebook Pages
- TikTok
- More available through Postiz

## Superpowers (Required)

This project uses the Superpowers plugin for workflow enforcement (TDD, debugging, code review). See parent template documentation for details.

## Slash Commands

Commands inherited from project-template via `.claude/commands/`. Key commands:
- `/setup` — Guided project setup
- `/health` — Project health check
- `/tasks` — List Taskmaster tasks
- `/commit` — Create conventional commit
- `/brainstorm` — Structured brainstorming
- `/verify` — Full verification pipeline

## Reference Docs

- `docs/N8N_INTEGRATION.md` — n8n + Postiz connection guide
- `docs/social-media-automation-assessment.md` — Technology assessment
- `docs/gita-valley-context.md` — Organizational context
