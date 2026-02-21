# Claude Code Hooks

This directory contains example hook scripts for automating Claude Code workflows.

## What Are Hooks?

Hooks are shell scripts that run automatically at specific points in Claude's workflow:
- **Before** Claude uses a tool (can block the action)
- **After** Claude finishes an action (for logging, formatting, etc.)
- **On events** like session start/end, notifications, etc.

## Available Hooks

| Script | Event | Purpose |
|--------|-------|---------|
| `session-init.sh` | SessionStart | Project state detection, session reload (<24h), phase guidance |
| `pre-commit-check.sh` | PreToolUse (Bash) | Validates code before git commits |
| `post-edit-format.sh` | PostToolUse (Edit\|Write) | Auto-formats files after edits |
| `protect-sensitive-files.sh` | PreToolUse (Edit\|Write) | Blocks edits to .env, keys, etc. |
| `session-summary.sh` | Stop | Logs session activity (lightweight) |
| `session-end.sh` | Stop | Generates detailed session summary for cross-session continuity |
| `pre-compact.sh` | Manual/UserPromptSubmit | Saves working state before context compaction |

## How to Enable Hooks

Hooks are configured in `.claude/settings.json` or `.claude/settings.local.json`:

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

## Quick Start

1. **Copy the example settings:**
   ```bash
   cp .claude/hooks/settings-example.json .claude/settings.local.json
   ```

2. **Or enable individual hooks using `/hooks`:**
   - Type `/hooks` in Claude Code
   - Select which hooks to enable

3. **Test a hook manually:**
   ```bash
   echo '{"tool_input":{"file_path":".env"}}' | .claude/hooks/protect-sensitive-files.sh
   ```

## Creating Custom Hooks

1. Create a script in `.claude/hooks/`
2. Make it executable: `chmod +x your-hook.sh`
3. Read JSON from stdin, write feedback to stdout
4. Use exit codes to allow (0) or block (2)

See the example scripts for patterns you can adapt.
