# Claude Code Hooks

All hooks are **enabled by default** via the tracked `.claude/settings.json`. Language-specific hooks (TypeScript, formatters) self-guard and no-op when they don't apply. Use `/settings fast` to disable all hooks, or other presets to slim down.

## What Are Hooks?

Hooks are shell scripts that run automatically at specific points in Claude's workflow:
- **Before** Claude uses a tool (can block the action)
- **After** Claude finishes an action (for logging, formatting, etc.)
- **On events** like session start/end, notifications, etc.

## Available Hooks

| Script | Event | Blocks? | Purpose |
|--------|-------|---------|---------|
| `session-init.sh` | SessionStart | No | Project state detection, session reload (<24h), phase guidance |
| `project-index.sh` | SessionStart | No | Generates codebase structure index for sub-agents |
| `pre-commit-check.sh` | PreToolUse (Bash) | **Yes** | Branch protection, conventional commit format, lint, tests, secrets (22 tests) |
| `dev-server-blocker.sh` | PreToolUse (Bash) | **Yes** | Blocks dev servers outside tmux to prevent terminal capture |
| `long-running-tmux-hint.sh` | PreToolUse (Bash) | No | Advisory tmux reminder for long-running commands |
| `protect-sensitive-files.sh` | PreToolUse (Edit\|Write) | **Yes** | Blocks edits to .env, keys, credentials |
| `doc-file-blocker.sh` | PreToolUse (Write) | **Yes** | Prevents .md creation outside approved locations |
| `post-edit-format.sh` | PostToolUse (Edit\|Write) | No | Auto-formats files (ruff, prettier, gofmt, etc.) |
| `console-log-audit.sh` | PostToolUse (Edit) | No | Warns about debug statements (print, console.log) |
| `typescript-check.sh` | PostToolUse (Edit) | No | Runs tsc --noEmit on .ts/.tsx files |
| `build-analysis.sh` | PostToolUse (Bash) | No | Advisory error/warning analysis after builds |
| `pr-url-extract.sh` | PostToolUse (Bash) | No | Extracts PR URL from git push output |
| `pre-compact.sh` | UserPromptSubmit | No | Saves task, tag, TDD phase, branch, uncommitted changes (17 tests) |
| `suggest-compact.sh` | UserPromptSubmit | No | Suggests compaction at 50+ tool calls |
| `session-end.sh` | Stop | No | Generates detailed per-session summary for cross-session continuity |
| `session-summary.sh` | Stop | No | Appends lightweight entry to rolling session log |
| `pattern-extraction.sh` | Stop | No | Auto-extracts instinct candidates from git history |

## How to Enable Hooks

Hooks are configured in Claude Code settings files:

- **`.claude/settings.json`** — Shared hook config (committed to git, team-visible)
- **`.claude/settings.local.json`** — Personal overrides (gitignored, user-specific)

**Use `settings.json` for hooks the whole team should run.** Only use `settings.local.json` for personal preferences or overrides.

Example `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/pre-commit-check.sh"
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/protect-sensitive-files.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-edit-format.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-summary.sh"
          }
        ]
      }
    ]
  }
}
```

## Hook Events Reference

| Event | When It Fires | Can Block? |
|-------|---------------|------------|
| `PreToolUse` | Before any tool call | Yes (exit 2) |
| `PostToolUse` | After tool completes | No |
| `UserPromptSubmit` | When user sends message | Yes (exit 2) |
| `Stop` | When Claude finishes | No |
| `SubagentStop` | When subagent finishes | No |
| `Notification` | On notifications | No |
| `SessionStart` | Session begins | No |
| `SessionEnd` | Session ends | No |

## Exit Codes

For blocking hooks (`PreToolUse`, `UserPromptSubmit`):
- `0` = Allow the action
- `2` = Block the action (Claude sees your stderr/stdout as reason)
- `1` or other = Warning only, doesn't block

## Environment Variables

Available in all hooks:
- `$CLAUDE_PROJECT_DIR` - Absolute path to project root

## Input Format

Hooks receive JSON via stdin with event-specific data:

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

## Customizing Hooks

All hooks are enabled by default in `.claude/settings.json` (tracked). To customize:

1. **Use a preset** (writes to `settings.local.json`, overrides tracked config):
   ```bash
   /settings fast        # Disables all hooks
   /settings optimized   # Lightweight subset + token savings
   /settings safe        # Safety hooks only
   ```

2. **Manual override** (copy and edit):
   ```bash
   cp .claude/settings.json .claude/settings.local.json
   # Edit settings.local.json to remove unwanted hooks
   ```

3. **Test a hook manually:**
   ```bash
   echo '{"tool_input":{"file_path":".env"}}' | .claude/hooks/protect-sensitive-files.sh
   ```

**Note:** `settings.local.json` completely overrides `settings.json` for hooks (no merging). If you define `hooks` in your local file, it replaces the entire tracked hook config.

## Creating Custom Hooks

1. Create a script in `.claude/hooks/`
2. Make it executable: `chmod +x your-hook.sh`
3. Read JSON from stdin, write feedback to stdout
4. Use exit codes to allow (0) or block (2)

See the example scripts for patterns you can adapt.
