---
name: continuous-learning-v2
description: Instinct-based pattern extraction, confidence scoring, skill evolution
---
# Continuous Learning v2

Adapted from [ECC](https://github.com/affaan-m/everything-claude-code) continuous-learning-v2.

## Architecture

```
Session Activity
      |
      | observe.sh hooks (PreToolUse/PostToolUse)
      v
observations.jsonl
      |
      | Analyzed by:
      |   - Observer daemon (background, Haiku, every 5 min)
      |   - /learn command (manual, in-session)
      |   - pattern-extraction.sh (Stop event, git-based)
      v
instincts/personal/*.md
      |
      | /evolve clusters related instincts
      v
instincts/evolved/ (skills, commands, agents)
```

**Authority**: Instincts never override rules. See `.claude/rules/authority-hierarchy.md`.

## Three Learning Paths

| Path | Trigger | Source | Output |
|------|---------|--------|--------|
| **observe.sh + observer** | Automatic (every tool call) | Tool usage patterns | `personal/*.md` |
| **pattern-extraction.sh** | Automatic (Stop event) | Git commit history | `candidates/*.json` |
| **`/learn`** | Manual (user invokes) | Session insights | `personal/*.md` |

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

Generated structures go to `instincts/evolved/skills/`, `evolved/commands/`, `evolved/agents/`.

## CLI Tool

`scripts/instinct-cli.py` provides programmatic access:

```bash
python3 scripts/instinct-cli.py status                    # Show all instincts
python3 scripts/instinct-cli.py export -o instincts.yaml  # Export for sharing
python3 scripts/instinct-cli.py import instincts.yaml     # Import from others
python3 scripts/instinct-cli.py evolve                    # Analyze clusters
python3 scripts/instinct-cli.py evolve --generate         # Create evolved structures
```

## Commands

| Command | Description |
|---------|-------------|
| `/instinct-status` | View all instincts with confidence scores |
| `/learn` | Manually extract patterns from current session |
| `/evolve` | Cluster related instincts into skills/commands |
| `/instinct-export` | Export instincts for sharing |
| `/instinct-import <file>` | Import instincts from others |

## Storage

```
.claude/instincts/
├── config.json              # Learning system configuration
├── README.md                # Architecture documentation
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
