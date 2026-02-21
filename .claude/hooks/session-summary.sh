#!/bin/bash
# session-summary.sh - Generate session summary on stop
# Hook type: Stop
# Triggers when: Claude finishes responding (main agent)
#
# This hook logs session activity for later review.
# Useful for tracking what was accomplished in each session.

set -e

# Read the input JSON from stdin
INPUT=$(cat)

# Extract session info
STOP_REASON=$(echo "$INPUT" | jq -r '.stop_hook_reason // "unknown"')
TIMESTAMP=$(date -Iseconds)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
LOG_DIR="$PROJECT_DIR/.claude/logs"
LOG_FILE="$LOG_DIR/sessions.log"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Only log on end_turn (not on interrupts)
if [ "$STOP_REASON" = "end_turn" ]; then
    # Get recent git activity if available
    GIT_CHANGES=""
    if [ -d "$PROJECT_DIR/.git" ]; then
        GIT_CHANGES=$(cd "$PROJECT_DIR" && git diff --stat HEAD~1 2>/dev/null | tail -1 || echo "no changes")
    fi

    # Log the session
    cat >> "$LOG_FILE" << EOF
---
timestamp: $TIMESTAMP
stop_reason: $STOP_REASON
git_summary: $GIT_CHANGES
---
EOF

    echo "Session logged to .claude/logs/sessions.log"
fi

exit 0
