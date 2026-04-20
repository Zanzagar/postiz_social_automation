# Claude Code Hooks

Hooks are shell scripts that run automatically during Claude Code's workflow, enabling automation, validation, and guardrails.

## Quick Start

1. **Enable a preset with hooks:**
   ```
   /settings safe
   ```

2. **Or manually copy the example settings:**
   ```bash
   cp .claude/hooks/settings-example.json .claude/settings.local.json
   ```

3. **Restart Claude Code** for changes to take effect.

## Available Hook Scripts

This template includes 18 ready-to-use hooks in `.claude/hooks/`:

### pre-commit-check.sh
**Event:** PreToolUse (matcher: "Bash")
**Purpose:** Validates code and workflow discipline before git commits
**Tests:** 22 passing

- **Blocks** direct commits to main/master branch (branch protection)
- **Blocks** non-conventional commit messages (validates `type: description` format)
- Runs linter (ruff) if available
- Runs tests (pytest) if available
- Checks for debug statements (pdb, breakpoint, console.log)
- Scans for hardcoded secrets
- **Advisory warning** when no Task Master task is in-progress
- All checks individually skippable: `SKIP_BRANCH_CHECK=1`, `SKIP_COMMIT_FORMAT=1`, `SKIP_LINT=1`, `SKIP_TESTS=1`, `SKIP_TASK_CHECK=1`
- **Optional tools:** `ruff` (linting) and `pytest` (tests) are checked via `command -v` — if not installed, those checks are silently skipped. Install via `pip install ruff pytest` or in a project venv. Exit code 5 (no tests collected) is treated as OK for new projects.

### post-edit-format.sh
**Event:** PostToolUse (matcher: "Edit|Write")
**Purpose:** Auto-formats files after Claude edits them

Supports:
- Python (ruff)
- JavaScript/TypeScript (prettier)
- Go (gofmt)
- Rust (rustfmt)
- Shell (shfmt)

### protect-sensitive-files.sh
**Event:** PreToolUse (matcher: "Edit|Write")
**Purpose:** Prevents Claude from editing sensitive files

Blocks edits to:
- `.env`, `.env.local`, `.env.production`
- `credentials.json`, `secrets.json`
- Private keys (`*.pem`, `*.key`, `id_rsa`)
- Protected directories (`.git`, `node_modules`, `__pycache__`)

### session-end.sh
**Event:** Stop
**Purpose:** Generates detailed session summary for cross-session continuity

Captures on session end:
- Git branch, recent commits, modified files, diff stats
- Task Master progress (in-progress and pending tasks)
- Writes to `.claude/sessions/session-summary-YYYYMMDD-HHMMSS.md`

Only fires on `end_turn` stop reason (not on tool errors or interrupts).

### session-summary.sh
**Event:** Stop
**Purpose:** Lightweight session activity logging

Creates entries in `.claude/logs/sessions.log` with:
- Timestamp
- Stop reason
- Git changes summary

*Note: `session-end.sh` is the recommended replacement. It provides richer context for session reload.*

### pre-compact.sh
**Event:** UserPromptSubmit (auto) or manual
**Purpose:** Saves comprehensive working state before context compaction
**Tests:** 17 passing

Preserves:
- Active Task Master task and **active tag** (from `.taskmaster/state.json`)
- Current branch and **uncommitted changes count** (with stderr warning)
- **TDD phase detection** (RED = tests failing, GREEN/REFACTOR = tests passing)
- Placeholder for manual context notes

**Auto-trigger:** Fires on every user prompt (saves state continuously).
**Manual trigger:** `./claude/hooks/pre-compact.sh`

Saved state is detected by `session-init.sh` on next session start.

### session-init.sh
**Event:** SessionStart
**Purpose:** Comprehensive project initialization and context loading

Detects five project scenarios:

| Scenario | Detection | Action |
|----------|-----------|--------|
| **New** | No src/, no Taskmaster, placeholder CLAUDE.md | Full setup guide |
| **Adopting** | Has code but no Taskmaster/state file | Integration steps |
| **Proto** | Has template-like structure but no sync tracking | Suggests official sync |
| **Upgrade** | Has state file but outdated version or missing components | Shows update command |
| **Existing** | Fully configured and current | Loads context |

Displays (for existing projects):
- Current Taskmaster task (if any)
- Uncommitted git changes
- Current branch (warns if on main)
- Critical issues and recommendations

Activates for projects with:
- `.claude/mcp-registry.json`, OR
- `.template/source` (sync tracking), OR
- Template-like structure (CLAUDE.md + .claude/commands or hooks)

### project-index.sh
**Event:** SessionStart
**Purpose:** Maintains a lightweight JSON index of codebase structure

Generates `.claude/project-index.json` containing:
- File paths and directory structure
- Import/export statements (with line numbers)
- Function and class signatures (with line numbers)

**Why this matters:**
- Sub-agents can understand codebase structure without loading full files
- Reduces context consumption during exploration
- Regenerates automatically if older than 5 minutes

**Token benefit:** Instead of reading 10 files to understand structure (~5-10k tokens), reference the index (~500-1k tokens).

Supports: Python, TypeScript, JavaScript

### suggest-compact.sh
**Event:** UserPromptSubmit
**Purpose:** Suggests context compaction at optimal times

Tracks tool call count across the session and suggests `/compact` at phase transitions or after significant activity. Uses a configurable threshold (default: 50 tool calls) with recurring reminders every 25 calls after the threshold.

- First suggestion at 50 tool calls (configurable via `COMPACT_THRESHOLD` env var)
- Recurring suggestions every 25 calls after threshold
- One-time `/learn` suggestion at 75 tool calls for pattern capture
- Per-session isolation using `CLAUDE_SESSION_ID` or `PPID`
- Stores counter state in `.claude/sessions/compact-state-*.tmp`
- **Advisory only** -- prints suggestions to stderr, never blocks

### doc-file-blocker.sh
**Event:** PreToolUse (matcher: "Write")
**Purpose:** Prevents creation of unnecessary documentation files

LLMs tend to create stray `.md`, `.txt`, and `.rst` files unprompted. This hook restricts documentation file creation to approved locations.

Allowed files (by name):
- `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- `LICENSE.md`, `LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `SKILL.md`

Allowed directories:
- `docs/`, `.claude/`, `.taskmaster/`, `.prd/`

- **Blocks** documentation files written outside approved locations
- Non-documentation files (`.py`, `.ts`, `.json`, etc.) are always allowed

### console-log-audit.sh
**Event:** PostToolUse (matcher: "Edit|Write")
**Purpose:** Warns about debug statements left in edited files

Scans edited files for common debug statements that should not be committed. Language-aware detection:

| Language | Detected Statements |
|----------|-------------------|
| Python | `print()`, `breakpoint()`, `pdb.set_trace()`, `import pdb` |
| JavaScript/TypeScript | `console.log`, `console.debug`, `console.warn`, `debugger` |
| Go | `fmt.Print`, `fmt.Println`, `log.Print`, `log.Println` |
| Java | `System.out.print`, `System.err.print`, `e.printStackTrace()` |
| Ruby | `puts`, `p`, `pp`, `binding.pry`, `byebug` |

- Shows up to 5 matches per category with line numbers
- Respects `# noqa` comments in Python
- **Advisory only** -- warns but never blocks

### pattern-extraction.sh
**Event:** Stop
**Purpose:** Extracts patterns from session git history for continuous learning

Analyzes commits from the last 4 hours to identify work patterns and generate instinct candidates. This is the engine that powers cross-session learning without manual `/learn` invocations.

- Requires 3+ commits to activate (skips trivial sessions)
- Deduplicates by HEAD commit SHA (won't re-extract same state)
- Categorizes sessions by commit type distribution: `debugging-approach`, `testing-strategy`, `coding-style`, `architecture-preference`, or `general`
- Detects primary language from file extensions touched
- Saves candidate JSON files to `.claude/instincts/candidates/session_*.json`
- Candidates start at confidence 0.3 and can be promoted via `/learn`
- **Advisory only** -- best-effort, never blocks or fails

### build-analysis.sh
**Event:** PostToolUse (matcher: "Bash")
**Purpose:** Provides advisory analysis of build command output

Detects build commands and analyzes their output for errors and warnings. Supports multiple build systems:

| Build Type | Commands Detected |
|------------|------------------|
| Node.js | `npm run build`, `npx tsc`, `yarn build` |
| Rust | `cargo build`, `cargo check` |
| Go | `go build`, `go vet` |
| Java | `mvn compile`, `mvn package`, `gradle build` |
| Python | `python -m py_compile`, `python setup.py`, `pip install` |
| Native | `make`, `cmake` |

- On failure: reports error/warning counts and suggests `/build-fix`
- On success with >3 warnings: reports warning count
- On clean success: stays silent
- **Advisory only** -- never blocks

### typescript-check.sh
**Event:** PostToolUse (matcher: "Edit|Write")
**Purpose:** Runs type checking after editing TypeScript files

When a `.ts` or `.tsx` file is edited, automatically runs `tsc --noEmit` to catch type errors immediately. Walks up from the edited file to find the nearest `tsconfig.json`.

- Only activates for `.ts` and `.tsx` files
- Requires `npx` to be available
- Filters `tsc` output to show only errors in the edited file (up to 5)
- Skips silently if no `tsconfig.json` is found
- **Advisory only** -- reports type errors but never blocks

### dev-server-blocker.sh
**Event:** PreToolUse (matcher: "Bash")
**Purpose:** Prevents dev servers from capturing the terminal

Dev servers run indefinitely and capture the terminal, which blocks Claude Code from doing further work. This hook detects common dev server commands and blocks them unless they are running safely.

Detected commands:
- Node.js: `npm run dev`, `npm start`, `npx next dev`, `pnpm dev`, `yarn dev`
- Python: `flask run`, `uvicorn --reload`, `manage.py runserver`
- Static: `hugo server`, `jekyll serve`
- Rust: `cargo watch`

Allowed when:
- Running inside tmux (`$TMUX` is set)
- Command ends with `&` (background mode)
- Using Claude Code's `run_in_background` parameter

- **Blocks** dev server commands that would capture the terminal
- Provides three alternative approaches in the block message

### pr-url-extract.sh
**Event:** PostToolUse (matcher: "Bash")
**Purpose:** Extracts PR creation URLs from git push output

After a `git push` command completes, scans stdout and stderr for pull request or merge request creation URLs. Supports GitHub (`/pull/new/` and `/compare/`) and GitLab (`/merge_requests/new`) URL patterns.

When a URL is detected, displays:
- The PR creation URL
- Quick action commands: `/pr`, `gh pr create --web`, `gh pr view --web`

- Only activates for `git push` commands
- Checks both stdout and stderr (git push writes to stderr)
- **Advisory only** -- never blocks

### long-running-tmux-hint.sh
**Event:** PreToolUse (matcher: "Bash")
**Purpose:** Advisory tmux reminder for potentially long-running commands

Complements `dev-server-blocker.sh` by covering commands that are long-running but not indefinite. Suggests tmux for session persistence when not already in a tmux session.

Detected commands:
- Package managers: `npm install`, `npm ci`, `pnpm install`, `yarn install`, `pip install`, `poetry install`, `pdm install`
- Test suites: `pytest`, `python -m pytest`, `cargo test`, `go test`
- Build tools: `cargo build`, `make`, `cmake --build`, `go build`, `mvn`, `gradle`
- Containers: `docker build`, `docker-compose up`, `docker compose up`

- Skips silently if already inside tmux (`$TMUX` is set)
- **Advisory only** -- suggests tmux but never blocks the command

### observe.sh
**Event:** PreToolUse / PostToolUse (matcher: "*")
**Purpose:** Captures tool use events for continuous learning pattern analysis

Core component of the Continuous Learning v2 system. Records every tool invocation as a JSONL observation for later analysis by the observer daemon. Runs as both a PreToolUse and PostToolUse hook, with the phase passed as a CLI argument (`pre` or `post`).

- Logs observations to `.claude/instincts/observations.jsonl`
- Truncates large inputs/outputs to 5000 characters
- Auto-archives observation file when it exceeds 10 MB
- Signals the observer daemon (via `USR1`) when new observations arrive
- Can be disabled by creating `.claude/instincts/disabled`
- Falls back to logging raw input on parse errors
- **Advisory only** -- best-effort, never blocks or fails

## Configuration

Hooks are configured in settings files. Create `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre-commit-check.sh",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

### Settings File Precedence

1. `~/.claude/settings.json` - User global (all projects)
2. `.claude/settings.json` - Project (committed)
3. `.claude/settings.local.json` - Project local (gitignored)

Later files override earlier ones.

## Hook Events Reference

| Event | Trigger | Can Block? | Use Cases |
|-------|---------|------------|-----------|
| `PreToolUse` | Before tool execution | Yes | Validation, protection |
| `PostToolUse` | After tool completes | No | Formatting, logging |
| `UserPromptSubmit` | User sends message | Yes | Input validation |
| `Stop` | Claude finishes | No | Logging, cleanup |
| `SubagentStop` | Subagent finishes | No | Logging |
| `Notification` | Notifications sent | No | Custom alerts |
| `SessionStart` | Session begins | No | Context loading |
| `SessionEnd` | Session ends | No | Cleanup |

## Matchers

For `PreToolUse` and `PostToolUse`, use regex matchers:

| Pattern | Matches |
|---------|---------|
| `"Bash"` | Bash tool only |
| `"Edit\|Write"` | Edit or Write tools |
| `"mcp__*"` | All MCP tools |
| `".*"` | Any tool |

## Exit Codes

For blocking events (`PreToolUse`, `UserPromptSubmit`):

| Code | Meaning |
|------|---------|
| `0` | Allow the action |
| `2` | Block the action |
| `1` | Warning (doesn't block) |

## Environment Variables

Available in all hooks:
- `$CLAUDE_PROJECT_DIR` - Absolute path to project root

## Input/Output

Hooks receive JSON via stdin:

```json
{
  "session_id": "abc123",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "...",
    "new_string": "..."
  }
}
```

Write to stdout/stderr for feedback shown to Claude.

## Creating Custom Hooks

1. Create script in `.claude/hooks/`:
   ```bash
   #!/bin/bash
   INPUT=$(cat)
   # Your logic here
   exit 0  # or exit 2 to block
   ```

2. Make executable:
   ```bash
   chmod +x .claude/hooks/my-hook.sh
   ```

3. Add to settings:
   ```json
   {
     "hooks": {
       "PreToolUse": [{
         "matcher": "Bash",
         "hooks": [{
           "type": "command",
           "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/my-hook.sh"
         }]
       }]
     }
   }
   ```

## Security Considerations

Hooks execute shell commands automatically. Review any hook scripts before enabling:

- Don't blindly copy hooks from untrusted sources
- Test hooks manually first
- Use absolute paths (`$CLAUDE_PROJECT_DIR`)
- Validate inputs from stdin

## Settings Presets

Use `/settings` to quickly configure common hook combinations:

| Preset | Hooks Enabled |
|--------|--------------|
| `fast` | None |
| `thorough` | Pre-commit check, session-init, session-end |
| `safe` | Pre-commit + file protection, session-init, session-end |
| `autoformat` | Post-edit formatting |
| `minimal` | Lifecycle + safety hooks (via TEMPLATE_HOOK_PROFILE) |

See `.claude/settings-presets.json` for full configurations.

## Troubleshooting

### Hook not running
- Check settings file syntax (valid JSON)
- Verify matcher pattern matches the tool
- Ensure script is executable (`chmod +x`)
- Restart Claude Code after changes

### Hook blocking unexpectedly
- Test script manually with sample input
- Check exit codes in your script
- Review stdout/stderr for error messages

### Testing a hook
```bash
echo '{"tool_input":{"file_path":"test.py"}}' | .claude/hooks/your-hook.sh
echo $?  # Check exit code
```
