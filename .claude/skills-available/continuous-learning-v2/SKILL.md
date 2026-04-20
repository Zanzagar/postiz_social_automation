---
name: continuous-learning-v2
description: Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into skills/commands/agents. v2.1 adds project-scoped instincts to prevent cross-project contamination.
origin: ECC
version: 2.1.0
---

# Continuous Learning v2.1 - Instinct-Based Architecture

An advanced learning system that turns your Claude Code sessions into reusable knowledge through atomic "instincts" - small learned behaviors with confidence scoring.

**v2.1** adds **project-scoped instincts** — React patterns stay in your React project, Python conventions stay in your Python project, and universal patterns (like "always validate input") are shared globally.

**Authority**: Instincts never override rules. See `.claude/rules/authority-hierarchy.md`.

## When to Activate

- Setting up automatic learning from Claude Code sessions
- Configuring instinct-based behavior extraction via hooks
- Tuning confidence thresholds for learned behaviors
- Reviewing, exporting, or importing instinct libraries
- Evolving instincts into full skills, commands, or agents
- Managing project-scoped vs global instincts
- Promoting instincts from project to global scope

## What's New in v2.1

| Feature | v2.0 | v2.1 |
|---------|------|------|
| Storage | Global (.claude/instincts/) | Project-scoped (.claude/instincts/ + project registry) |
| Scope | All instincts apply everywhere | Project-scoped + global |
| Detection | None | git remote URL / repo path |
| Promotion | N/A | Project → global when seen in 2+ projects |
| Commands | 4 (status/evolve/export/import) | 6 (+promote/projects) |
| Cross-project | Contamination risk | Isolated by default |

## What's New in v2 (vs v1)

| Feature | v1 | v2 |
|---------|----|----|
| Observation | Stop hook (session end) | PreToolUse/PostToolUse (100% reliable) |
| Analysis | Main context | Background agent (Haiku) |
| Granularity | Full skills | Atomic "instincts" |
| Confidence | None | 0.3-0.9 weighted |
| Evolution | Direct to skill | Instincts -> cluster -> skill/command/agent |
| Sharing | None | Export/import instincts |

## Three Learning Paths

| Path | Trigger | Source | Output |
|------|---------|--------|--------|
| **observe.sh + observer** | Automatic (every tool call) | Tool usage patterns | `personal/*.md` |
| **pattern-extraction.sh** | Automatic (Stop event) | Git commit history | `candidates/*.json` |
| **`/learn`** | Manual (user invokes) | Session insights | `personal/*.md` |

## The Instinct Model

An instinct is a small learned behavior:

```yaml
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
scope: project
project_id: "a1b2c3d4e5f6"
project_name: "my-react-app"
---

# Prefer Functional Style

## Action
Use functional patterns over classes when appropriate.

## Evidence
- Observed 5 instances of functional pattern preference
- User corrected class-based approach to functional on 2025-01-15
```

**Properties:**
- **Atomic** -- one trigger, one action
- **Confidence-weighted** -- 0.3 = tentative, 0.9 = near certain
- **Domain-tagged** -- code-style, testing, git, debugging, workflow, etc.
- **Evidence-backed** -- tracks what observations created it
- **Scope-aware** -- `project` (default) or `global`

## How It Works

```
Session Activity (in a git repo)
      |
      | Hooks capture prompts + tool use (100% reliable)
      | + detect project context (git remote / repo path)
      v
+---------------------------------------------+
|  .claude/instincts/observations.jsonl        |
|  (or project-scoped per registry entry)      |
|   (prompts, tool calls, outcomes, project)   |
+---------------------------------------------+
      |
      | Observer agent reads (background, Haiku)
      v
+---------------------------------------------+
|          PATTERN DETECTION                   |
|   * User corrections -> instinct             |
|   * Error resolutions -> instinct            |
|   * Repeated workflows -> instinct           |
|   * Scope decision: project or global?       |
+---------------------------------------------+
      |
      | Creates/updates
      v
+---------------------------------------------+
|  .claude/instincts/personal/  (project)      |
|   * prefer-functional.yaml (0.7) [project]   |
|   * use-react-hooks.yaml (0.9) [project]     |
+---------------------------------------------+
|  .claude/instincts/personal/  (GLOBAL)       |
|   * always-validate-input.yaml (0.85) [global]|
|   * grep-before-edit.yaml (0.6) [global]     |
+---------------------------------------------+
      |
      | /evolve clusters + /promote
      v
+---------------------------------------------+
|  .claude/instincts/evolved/ (project-scoped) |
|   * commands/new-feature.md                  |
|   * skills/testing-workflow.md               |
|   * agents/refactor-specialist.md            |
+---------------------------------------------+
```

## Project Detection

The system automatically detects your current project:

1. **`CLAUDE_PROJECT_DIR` env var** (highest priority)
2. **`git remote get-url origin`** -- hashed to create a portable project ID (same repo on different machines gets the same ID)
3. **`git rev-parse --show-toplevel`** -- fallback using repo path (machine-specific)
4. **Global fallback** -- if no project is detected, instincts go to global scope

Each project gets a 12-character hash ID (e.g., `a1b2c3d4e5f6`). A registry file at `.claude/instincts/projects.json` maps IDs to human-readable names.

## Quick Start

### 1. Enable Observation Hooks

The template wires `observe.sh` in `.claude/settings.json` automatically. Hooks fire on every PreToolUse and PostToolUse event and write to `.claude/instincts/observations.jsonl`.

### 2. Initialize Directory Structure

The system creates directories automatically on first use, but you can also create them manually:

```bash
mkdir -p .claude/instincts/{personal,inherited,candidates,evolved/{agents,skills,commands},observations.archive}
```

### 3. Use the Instinct Commands

```bash
/instinct-status     # Show learned instincts (project + global)
/evolve              # Cluster related instincts into skills/commands
/instinct-export     # Export instincts to file
/instinct-import     # Import instincts from others
/promote             # Promote project instincts to global scope
/projects            # List all known projects and their instinct counts
```

## Commands

| Command | Description |
|---------|-------------|
| `/instinct-status` | Show all instincts (project-scoped + global) with confidence |
| `/learn` | Manually extract patterns from current session |
| `/evolve` | Cluster related instincts into skills/commands, suggest promotions |
| `/instinct-export` | Export instincts (filterable by scope/domain) |
| `/instinct-import <file>` | Import instincts with scope control |
| `/promote [id]` | Promote project instincts to global scope |
| `/projects` | List all known projects and their instinct counts |

## Configuration

Edit `.claude/instincts/config.json` to control the background observer:

```json
{
  "version": "2.1",
  "observer": {
    "enabled": false,
    "run_interval_minutes": 5,
    "min_observations_to_analyze": 20
  }
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `observer.enabled` | `false` | Enable the background observer agent |
| `observer.run_interval_minutes` | `5` | How often the observer analyzes observations |
| `observer.min_observations_to_analyze` | `20` | Minimum observations before analysis runs |

## Instinct Format (YAML Frontmatter Markdown)

Each instinct is a `.md` file in `personal/` or `inherited/`:

```markdown
---
id: prefer-grep-before-edit
trigger: "when searching for code to modify"
confidence: 0.65
domain: "workflow"
source: "session-observation"
---

# Prefer Grep Before Edit

## Action
Always use Grep to find the exact location before using Edit.

## Evidence
- Observed 8 times across 3 sessions
- Pattern: Grep -> Read -> Edit sequence
- Last observed: 2026-02-22
```

### Domains
| Domain | Examples |
|--------|----------|
| `code-style` | Naming conventions, formatting preferences |
| `testing` | Test patterns, fixture preferences |
| `debugging` | Debugging workflow, log placement |
| `workflow` | Tool usage, command patterns |
| `architecture` | Module organization, dependency patterns |
| `git` | Commit patterns, branch strategies |

## Confidence Management

### Thresholds
| Range | Status | Behavior |
|-------|--------|----------|
| < 0.3 | Noise | Discard — too unreliable |
| 0.3-0.7 | Candidate | Keep but don't auto-apply |
| > 0.7 | Active | Auto-approved for application |
| > 0.9 | Near-certain | Core behavior |

### Score Dynamics
| Event | Change |
|-------|--------|
| Pattern confirmed | +0.05 |
| User rejects | -0.1 |
| Week unused | -0.02 (decay) |
| Rule conflict | Deactivate (rules always win) |

### Initial Confidence (observer)
- 1-2 observations: 0.3 (tentative)
- 3-5 observations: 0.5 (moderate)
- 6-10 observations: 0.7 (strong)
- 11+ observations: 0.85 (very strong)

## Scope Decision Guide

| Pattern Type | Scope | Examples |
|-------------|-------|---------|
| Language/framework conventions | **project** | "Use React hooks", "Follow Django REST patterns" |
| File structure preferences | **project** | "Tests in `__tests__`/", "Components in src/components/" |
| Code style | **project** | "Use functional style", "Prefer dataclasses" |
| Error handling strategies | **project** | "Use Result type for errors" |
| Security practices | **global** | "Validate user input", "Sanitize SQL" |
| General best practices | **global** | "Write tests first", "Always handle errors" |
| Tool workflow preferences | **global** | "Grep before Edit", "Read before Write" |
| Git practices | **global** | "Conventional commits", "Small focused commits" |

## Instinct Promotion (Project -> Global)

When the same instinct appears in multiple projects with high confidence, it's a candidate for promotion to global scope.

**Auto-promotion criteria:**
- Same instinct ID in 2+ projects
- Average confidence >= 0.8

**How to promote:**

```bash
# Promote a specific instinct
python3 scripts/instinct-cli.py promote prefer-explicit-errors

# Auto-promote all qualifying instincts
python3 scripts/instinct-cli.py promote

# Preview without changes
python3 scripts/instinct-cli.py promote --dry-run
```

The `/evolve` command also suggests promotion candidates.

## Observation Hook

`observe.sh` runs on every PreToolUse and PostToolUse event:
- Captures tool name, truncated input/output (5KB max), session ID, timestamp
- Writes JSONL to `.claude/instincts/observations.jsonl`
- Archives when file exceeds 10MB
- Signals observer daemon via SIGUSR1 if running
- Uses `$1` CLI arg for phase detection (PR #242 fix)

## Observer Daemon

Background process (`scripts/start-observer.sh`) that:
- Spawns `claude --model haiku --max-turns 3` every 5 minutes
- Analyzes observations for patterns (user corrections, error resolutions, repeated workflows, tool preferences)
- Creates instinct files in `personal/`
- Archives processed observations

```bash
scripts/start-observer.sh        # Start
scripts/start-observer.sh stop   # Stop
scripts/start-observer.sh status # Check
```

## Skill Evolution

When 3+ related instincts cluster with confidence >0.7, `/evolve` promotes them:

| Source | Target | Criteria |
|--------|--------|----------|
| 2+ related instincts | Skill | Similar triggers, any confidence |
| Workflow instinct (>=70%) | Command | High-confidence workflow patterns |
| 3+ instincts (>=75% avg) | Agent | Complex multi-step patterns |

Generated structures go to `.claude/instincts/evolved/skills/`, `evolved/commands/`, `evolved/agents/`.

## CLI Tool

`scripts/instinct-cli.py` provides programmatic access:

```bash
python3 scripts/instinct-cli.py status                    # Show all instincts
python3 scripts/instinct-cli.py export -o instincts.yaml  # Export for sharing
python3 scripts/instinct-cli.py import instincts.yaml     # Import from others
python3 scripts/instinct-cli.py evolve                    # Analyze clusters
python3 scripts/instinct-cli.py evolve --generate         # Create evolved structures
```

## Storage

```
.claude/instincts/
├── config.json              # Learning system configuration
├── README.md                # Architecture documentation
├── projects.json            # Registry: project hash -> name/path/remote
├── observations.jsonl       # Raw tool use observations (gitignored)
├── personal/                # Auto-learned instincts (gitignored)
├── inherited/               # Imported from others (optionally committed)
├── candidates/              # Git-based session summaries (gitignored)
├── evolved/                 # Graduated to skills/commands/agents (committed)
│   ├── skills/
│   ├── commands/
│   └── agents/
└── observations.archive/    # Processed observations (gitignored)
```

## Sharing Instincts

Export project-level instincts for sharing or global use:

```bash
# Export all high-confidence instincts
/instinct-export --min-confidence=0.7 --output=team-instincts.yaml

# Import into another project
/instinct-import team-instincts.yaml

# Filter by domain
/instinct-export --domain=workflow --output=workflow-patterns.yaml
```

Exported instincts go to `inherited/` in the target project with source attribution.
To make instincts available globally across all projects, export and import into
each project — instincts are intentionally project-scoped so different projects
can learn different patterns.

## Why Hooks vs Skills for Observation?

> "v1 relied on skills to observe. Skills are probabilistic -- they fire ~50-80% of the time based on Claude's judgment."

Hooks fire **100% of the time**, deterministically. This means:
- Every tool call is observed
- No patterns are missed
- Learning is comprehensive

## Backward Compatibility

v2.1 is fully compatible with v2.0 and v1:
- Existing global instincts in `.claude/instincts/` still work as global instincts
- Existing learned skills from v1 still work
- Stop hook still runs (but now also feeds into v2)
- Gradual migration: run both in parallel

## Privacy

- Observations stay **local** on your machine
- Project-scoped instincts are isolated per project
- Only **instincts** (patterns) can be exported — not raw observations
- No actual code or conversation content is shared
- You control what gets exported and promoted
