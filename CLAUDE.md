# Project: Postiz Social Media Automation

Automation layer for Gita Valley (ISKCON Gita Nagari) social media scheduling, built on top of a self-hosted Postiz instance with Docker infrastructure.

## Tech Stack

- Python 3.11+
- Docker Compose (Postiz, PostgreSQL, Redis, Temporal, Elasticsearch)
- Postiz (self-hosted social media scheduler) — app on port 4007
- Temporal (workflow engine) — gRPC on 7233, UI on 8080
- PostgreSQL 17 (Postiz data) + PostgreSQL 16 (Temporal data)
- Redis 7.2 (Postiz caching/queuing)

## Structure

```
docker-compose.yaml    # Infrastructure: Postiz + PostgreSQL + Redis + Temporal + ES
.env.example           # Environment template (Postiz config, DB URLs, API keys)
dynamicconfig/         # Temporal dynamic configuration
docs/                  # Research docs, design docs, dogfood tracking
src/                   # Automation layer (to be built)
tests/                 # Test files (to be built)
.claude/rules/         # Auto-loaded behavior rules (synced from template)
.taskmaster/           # Task Master project data
```

## Development Commands

```bash
# Docker infrastructure
docker compose up -d                    # Start all services
docker compose ps                       # Check service status
docker compose logs postiz --tail=50    # View Postiz logs
docker compose down                     # Stop all services

# Python automation layer
pip install -e ".[dev]"                 # Install dependencies (once setup exists)
pytest                                  # Run tests

# Task Master
task-master list -c                     # Compact task list
task-master next                        # Next recommended task
task-master set-status <id> <status>    # Update task status
```

## Key Decisions & Constraints

- **Postiz API is in beta** — rate limits and endpoints may change
- **Separate infrastructure hosts**: Postiz runs in Docker on sethpc.xyz; n8n runs on a separate machine
- **Platform app approvals needed**: Facebook/Instagram require business verification for API access
- **Content pillar weights**: 40% Spiritual/Educational, 25% Community, 15% Farm/Sustainable, 10% Events, 5% Behind-the-Scenes, 5% Seasonal/Holiday
- **Content mix**: 70% pre-planned, 20% timely/reactive, 10% experimental
- **Rebranding in progress**: "ISKCON Gita Nagari" transitioning to "Gita Valley" — automation must handle both names

## Gotchas & Watch-outs

- Postiz container exposes port 4007 (maps to internal 5000)
- JWT_SECRET in .env.example is a placeholder — regenerate for production
- Temporal UI at port 8080 — useful for debugging workflow executions
- Two separate PostgreSQL instances: one for Postiz, one for Temporal
- `.env` is gitignored; copy `.env.example` and customize

## Taskmaster Workflows

### Workflow Rules (MANDATORY)

1. **PRD first**: ALWAYS create a PRD before generating tasks. Never use `add-task` to build a task list from scratch — write a PRD in `.taskmaster/docs/`, then parse it.
2. **New tag per phase**: Each workflow phase gets its own tag (e.g., `postiz-mvp`, `feature-scheduling`). Never pollute the `master` tag with phase-specific work.
3. **Switch tags**: Always `task-master tags use <name>` before running set-status, show, or list — operations target the active tag.
4. **Expand after parse**: Always run `task-master expand --id=<id>` on complex tasks after parse-prd to generate actionable subtasks.
5. **Float task count**: Use `--num-tasks 0` with parse-prd to let the AI determine the right number of tasks. Don't hardcode counts.

### Commands

```bash
task-master list -c                     # Compact one-line output (fewer tokens)
task-master list --ready --blocking     # Highest-impact tasks to work on next
task-master show <id>                   # Task details
task-master next                        # Next recommended task
task-master set-status <id> <status>    # e.g., set-status 3 done
task-master expand --id=<id>            # Break task into subtasks
task-master analyze-complexity          # Complexity report (run before expand)
task-master parse-prd --input=<file> --num-tasks=0  # PRD to tasks
task-master tags use <tag-name>         # Switch active tag
```

## Current Focus

- [ ] Dogfood test of project template v2.3.1 (full workflow)
- [ ] Build automation layer on top of Postiz infrastructure
- [ ] Social media scheduling automation for Gita Valley

## Research Context

Domain research docs in `docs/`:
- `gita-valley-context.md` — Client profile, social accounts, content strategy
- `gita-valley-online-presence-audit-v2.md` — Platform audit, rebranding gaps
- `social-media-automation-assessment.md` — Postiz vs SaaS comparison
- `N8N_INTEGRATION.md` — n8n and Postiz connection setup

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
