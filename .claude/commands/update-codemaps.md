Generate token-lean architecture documentation in `docs/CODEMAPS/`.

Usage: `/update-codemaps [scope]`

Arguments: $ARGUMENTS

## Scope Options

- `all` (default): Generate all codemap files
- `architecture`: System diagram and boundaries only
- `backend`: API routes and service mapping only
- `frontend`: Component hierarchy only
- `data`: Database schema and relationships only
- `dependencies`: External service and library mapping only

## Step 1: Scan Project Structure

1. Identify project type (monorepo, single app, library, microservice)
2. Find all source directories (`src/`, `lib/`, `app/`, `packages/`)
3. Map entry points (`main.py`, `index.ts`, `main.go`, `cmd/`)
4. Respect `.gitignore` for exclusions

## Step 2: Generate Codemaps

Create or update files in `docs/CODEMAPS/`:

| File | Contents |
|------|----------|
| `architecture.md` | High-level system diagram, service boundaries, data flow |
| `backend.md` | API routes, middleware chain, service-to-repository mapping |
| `frontend.md` | Page tree, component hierarchy, state management flow |
| `data.md` | Database tables, relationships, migration history |
| `dependencies.md` | External services, third-party integrations, shared libraries |

### Token-Lean Format

Codemaps are optimized for AI context consumption — minimal prose, maximum information density:

```markdown
<!-- Generated: 2026-02-13 | Files scanned: 142 | Token estimate: ~800 -->

# Backend Architecture

## Routes
POST /api/users → UserController.create → UserService.create → UserRepo.insert
GET  /api/users/:id → UserController.get → UserService.findById → UserRepo.findById
DELETE /api/users/:id → UserController.delete → UserService.remove → UserRepo.delete

## Key Files
src/services/user.py    (business logic, 120 lines)
src/repos/user.py       (database access, 80 lines)
src/api/user_routes.py  (endpoint handlers, 95 lines)

## Dependencies
- PostgreSQL (primary data store)
- Redis (session cache, rate limiting)
- Stripe (payment processing)
```

### Architecture Diagram Example

```markdown
<!-- Generated: 2026-02-13 | Files scanned: 142 | Token estimate: ~600 -->

# Architecture Overview

## System Diagram
┌─────────────────────────────────┐
│           API Layer             │  src/api/
│  (Routes, Middleware, Schemas)  │
├─────────────────────────────────┤
│         Service Layer           │  src/services/
│     (Business Logic, Rules)     │
├─────────────────────────────────┤
│        Repository Layer         │  src/repos/
│   (Data Access, ORM Queries)    │
├─────────────────────────────────┤
│         Infrastructure          │  src/config/, src/db/
│  (Config, DB, External APIs)    │
└─────────────────────────────────┘

## Key Boundaries
- API layer NEVER accesses repositories directly
- Services are framework-agnostic (no FastAPI/Django imports)
- All DB access goes through repository layer
```

### Data Schema Example

```markdown
<!-- Generated: 2026-02-13 | Tables: 12 | Token estimate: ~400 -->

# Data Schema

## Tables
users         (id, email, password_hash, created_at)
orders        (id, user_id FK→users, total, status, created_at)
order_items   (id, order_id FK→orders, product_id FK→products, qty, price)
products      (id, name, price, stock, category_id FK→categories)

## Relationships
users 1──* orders 1──* order_items *──1 products

## Recent Migrations
0042_add_user_preferences.py  (2026-02-10)
0043_add_order_tracking.py    (2026-02-12)
```

## Step 3: Diff Detection

If previous codemaps exist:

1. Calculate diff percentage against existing files
2. If changes > 30%: show diff and request user approval before overwriting
3. If changes <= 30%: update in place
4. Log changes to `.reports/codemap-diff.txt`

## Step 4: Add Freshness Metadata

Every codemap file gets a metadata header:

```markdown
<!-- Generated: YYYY-MM-DD | Files scanned: N | Token estimate: ~N -->
```

This lets Claude (and humans) quickly assess staleness.

## Step 5: Staleness Report

After generation, report:
- Files added/removed/modified since last scan
- New dependencies detected
- Architecture changes (new routes, services, etc.)
- Codemaps not updated in 90+ days (staleness warning)

```
Codemap Update Summary
──────────────────────
Updated:  docs/CODEMAPS/backend.md (5 new routes)
Updated:  docs/CODEMAPS/data.md (2 new tables)
Skipped:  docs/CODEMAPS/frontend.md (no changes)
Flagged:  docs/CODEMAPS/dependencies.md (94 days stale)
──────────────────────
```

## Design Principles

- **Token-lean**: File paths and function signatures, not full code blocks
- **Information-dense**: One line per route, one line per table
- **Keep each codemap under 1000 tokens** for efficient context loading
- **ASCII diagrams** over verbose descriptions
- **Mermaid** for complex relationships (renders in GitHub/VS Code)

## Relationship to project-index.sh

| Tool | Format | Purpose | When to Use |
|------|--------|---------|-------------|
| `project-index.sh` | JSON | Machine-readable for sub-agents | Auto (hook) |
| `/update-codemaps` | Markdown | Human-readable for developers | Manual |

The project index is lightweight and auto-generated. Codemaps are richer, human-friendly, and manually triggered when architecture changes.

## When to Use

- After significant architectural changes
- When onboarding new team members
- Before architecture review meetings
- Monthly maintenance alongside `/eval metrics`
