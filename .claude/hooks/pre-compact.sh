#!/bin/bash
# pre-compact.sh - Save working state before context compaction
# Hook type: Manual (run before /compact when context feels heavy)
#
# Usage:
#   .claude/hooks/pre-compact.sh
#   Or triggered automatically via UserPromptSubmit hook (see settings-example.json)
#
# The saved state is detected by session-init.sh on the next session start.

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
SESSIONS_DIR="$PROJECT_DIR/.claude/sessions"
STATE_FILE="$SESSIONS_DIR/pre-compact-state.md"

mkdir -p "$SESSIONS_DIR"

# If called via UserPromptSubmit hook, check if input matches compact patterns
if [ -t 0 ] 2>/dev/null; then
    : # stdin is terminal, manual run — proceed
else
    INPUT=$(cat)
    USER_MSG=$(echo "$INPUT" | jq -r '.user_prompt // .message // ""' 2>/dev/null)
    if [ -n "$USER_MSG" ]; then
        if ! echo "$USER_MSG" | grep -qiE '(^/compact|compact.*context|context.*heavy)'; then
            exit 0  # Not a compaction-related message, skip
        fi
    fi
fi

# Capture current working state
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CURRENT_BRANCH="(no git)"
UNCOMMITTED=""
ACTIVE_TASK=""

if [ -d "$PROJECT_DIR/.git" ]; then
    CURRENT_BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "detached")
    UNCOMMITTED=$(cd "$PROJECT_DIR" && git status --porcelain 2>/dev/null | head -10 || true)
fi

ACTIVE_TASK=$(task-master list --status in-progress 2>/dev/null | head -5 || echo "none")

cat > "$STATE_FILE" << EOF
# Pre-Compaction State
*Saved: $TIMESTAMP*

## Active Task
$ACTIVE_TASK

## Branch: $CURRENT_BRANCH

## Uncommitted Changes
\`\`\`
${UNCOMMITTED:-none}
\`\`\`

## Context to Preserve
<!-- Add key decisions, variable names, or context that shouldn't be lost -->

---
*This file is overwritten on each run. Review on session reload.*
EOF

echo "Pre-compaction state saved to $STATE_FILE"
exit 0
