# Project: Postiz Social Media Automation

Automation layer for Gita Valley (ISKCON Gita Nagari) social media scheduling using Postiz, Docker infrastructure with PostgreSQL, Redis, and Temporal.

## Tech Stack

- Python 3.11+
- Docker Compose (Postiz, PostgreSQL, Redis, Temporal)
- n8n (workflow automation, separate host)
- Postiz API (self-hosted social media scheduler)

## Structure

```
docker-compose.yaml   # Postiz + PostgreSQL + Redis + Temporal
dynamicconfig/        # Temporal dynamic configuration
docs/                 # Research docs, audits, plans
.claude/rules/        # Auto-loaded behavior rules (synced from template)
.claude/hooks/        # Automation hooks (18 hooks enabled)
.taskmaster/          # Task Master data (tasks, PRDs, reports)
```

## Development Commands

```bash
# Docker infrastructure
docker compose up -d                # Start all services
docker compose ps                   # Check service status
docker compose logs postiz           # View Postiz logs

# Python automation layer (when built)
pip install -e ".[dev]"
pytest
ruff check . --fix
```

## Key Decisions & Constraints

- **Postiz API is in beta** — rate limits and endpoints may change
- **n8n runs on separate host** — communication via HTTP/webhooks
- **Platform app approvals needed** — Facebook, Instagram require business verification
- **Content pillars**: 40% spiritual education, 25% farm/community, 15% events, 10% behind-scenes, 5% seasonal, 5% collaborative
- **Content mix**: 70% value-add, 20% engagement, 10% promotional
- **Rebranding in progress** — "Gita Nagari" → "Gita Valley" across all platforms

## Taskmaster Workflows

### Workflow Rules (MANDATORY)

1. **PRD first**: ALWAYS create a PRD before generating tasks. Never use `add-task` to build a task list from scratch — write a PRD in `.taskmaster/docs/`, then parse it.
2. **New tag per phase**: Each workflow phase gets its own tag (e.g., `postiz-mvp`, `feature-automation`). Never pollute the `master` tag with phase-specific work.
3. **Switch tags**: Always `task-master tags use <name>` before running set-status, show, or list — operations target the active tag.
4. **Expand after parse**: Always run `task-master expand --id=<id>` on complex tasks after parse-prd to generate actionable subtasks.
5. **Float task count**: Use `--num-tasks 0` with parse-prd to let the AI determine the right number of tasks. Don't hardcode counts.

### Commands

```bash
# List tasks (current tag)
task-master list                        # Default view
task-master list all                    # Include subtasks
task-master list --ready                # Only actionable tasks (deps satisfied)
task-master list --ready --blocking     # Highest-impact tasks to work on next
task-master list -c                     # Compact one-line output (fewer tokens)

# Show / navigate
task-master show <id>                   # Task details
task-master next                        # Next recommended task

# Status updates (positional syntax)
task-master set-status <id> <status>    # e.g., set-status 3 done

# Task decomposition
task-master expand --id=<id>            # Break task into subtasks
task-master analyze-complexity          # Complexity report (run before expand)

# PRD → tasks
task-master parse-prd --input=<file> --num-tasks=0

# Tag management
task-master tags use <tag-name>         # Switch active tag
task-master tags list --ready           # Tags with actionable task counts
```

## Current Focus

- [ ] Dogfood Test 4, Run 2 — testing full v2.3.1 template workflow
- [ ] Phase 0: Bootstrap (in progress)

## Superpowers (Required)

This template requires the [Superpowers](https://github.com/obra/superpowers) plugin for workflow enforcement:

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

**Task Master + Superpowers = Complete Workflow:**
- **Task Master** (MCP) = WHAT to work on (task tracking, dependencies, status)
- **Superpowers** (Plugin) = HOW to work on it (TDD enforcement, debugging discipline)
