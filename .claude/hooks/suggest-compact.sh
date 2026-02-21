#!/usr/bin/env bash
# suggest-compact.sh — Suggests context compaction at optimal times
# Trigger: UserPromptSubmit (lightweight, runs on every prompt)
#
# Checks tool call count via session state and suggests compaction
# at phase transitions or after significant exploration.
#
# This hook is advisory — it prints a suggestion, not a command.
#
# Configuration:
#   COMPACT_THRESHOLD — Tool calls before first suggestion (default: 50)
#
# Session isolation:
#   Uses CLAUDE_SESSION_ID if available for per-session tracking,
#   falls back to PPID for process-level isolation.

set -euo pipefail

THRESHOLD=${COMPACT_THRESHOLD:-50}
REPEAT_INTERVAL=25

# Session-specific counter for isolation across parallel sessions
SESSION_ID="${CLAUDE_SESSION_ID:-${PPID:-default}}"
SESSIONS_DIR="${PROJECT_DIR:-.}/.claude/sessions"
COMPACT_STATE="${SESSIONS_DIR}/compact-state-${SESSION_ID}.tmp"

# Ensure sessions directory exists
mkdir -p "$SESSIONS_DIR"

# Initialize or read tool call counter
if [ -f "$COMPACT_STATE" ]; then
    TOOL_CALLS=$(cat "$COMPACT_STATE" 2>/dev/null || echo "0")
else
    TOOL_CALLS=0
fi

# Increment counter
TOOL_CALLS=$((TOOL_CALLS + 1))
echo "$TOOL_CALLS" > "$COMPACT_STATE"

# Suggest compaction at threshold
# These are advisory — the user/Claude decides whether to act
if [ "$TOOL_CALLS" -eq "$THRESHOLD" ]; then
    echo "[StrategicCompact] ${THRESHOLD} tool calls reached — consider /compact if transitioning phases" >&2
fi

# Recurring suggestions after threshold
if [ "$TOOL_CALLS" -gt "$THRESHOLD" ] && [ $(( TOOL_CALLS % REPEAT_INTERVAL )) -eq 0 ]; then
    echo "[StrategicCompact] ${TOOL_CALLS} tool calls — good checkpoint for /compact if context is stale" >&2
fi
