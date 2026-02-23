#!/bin/bash
# session-summary.sh - Generate session summary on stop
# Hook type: Stop
# Triggers when: Claude finishes responding (main agent)
#
# This hook logs session activity for later review.
# Useful for tracking what was accomplished in each session.
#
# Note: The Stop event only fires on normal completions, not on user
# interrupts, so no stop-reason filtering is needed.

# Best-effort: never block session exit
set +e

# Consume stdin (Stop event JSON — we don't need it for logging)
cat > /dev/null 2>&1

TIMESTAMP=$(date -Iseconds)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
LOG_DIR="$PROJECT_DIR/.claude/logs"
LOG_FILE="$LOG_DIR/sessions.log"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Get recent git activity if available
GIT_CHANGES=""
if [ -d "$PROJECT_DIR/.git" ]; then
    GIT_CHANGES=$(cd "$PROJECT_DIR" && git diff --stat HEAD~1 2>/dev/null | tail -1 || echo "no changes")
fi

# Log the session
cat >> "$LOG_FILE" << EOF
---
timestamp: $TIMESTAMP
git_summary: $GIT_CHANGES
---
EOF

echo "Session logged to .claude/logs/sessions.log"

exit 0
