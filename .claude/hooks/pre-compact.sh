#!/bin/bash
# pre-compact.sh - Save working state before context compaction
# Hook type: Manual (run before /compact when context feels heavy)
#
# Usage:
#   .claude/hooks/pre-compact.sh
#   Or triggered automatically via UserPromptSubmit hook (see settings-example.json)
#
# The saved state is detected by session-init.sh on the next session start.

# Best-effort: never block user prompts
set +e

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
UNCOMMITTED_COUNT=0
ACTIVE_TASK=""
ACTIVE_TAG="master"
TDD_PHASE="unknown"

# --- Git state ---
if [ -d "$PROJECT_DIR/.git" ]; then
    CURRENT_BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "detached")
    UNCOMMITTED=$(cd "$PROJECT_DIR" && git status --porcelain 2>/dev/null | head -10 || true)
    UNCOMMITTED_COUNT=$(cd "$PROJECT_DIR" && git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$UNCOMMITTED_COUNT" -gt 0 ] 2>/dev/null; then
        echo "WARNING: $UNCOMMITTED_COUNT uncommitted changes will not be preserved." >&2
    fi
fi

# --- Active Task Master task ---
ACTIVE_TASK=$(task-master list --status in-progress --json 2>/dev/null \
    | jq -r '.tasks[] | "- \(.title) (ID: \(.id))"' 2>/dev/null \
    | head -5)
[ -z "$ACTIVE_TASK" ] && ACTIVE_TASK="none"

# --- Active Task Master tag (R2.1) ---
if [ -f "$PROJECT_DIR/.taskmaster/state.json" ]; then
    ACTIVE_TAG=$(jq -r '.currentTag // .activeTag // "master"' "$PROJECT_DIR/.taskmaster/state.json" 2>/dev/null)
fi
[ -z "$ACTIVE_TAG" ] && ACTIVE_TAG="master"

# --- TDD Phase detection (R2.2) ---
# Best-effort: infer from test execution status
if [ -d "$PROJECT_DIR/tests" ]; then
    if command -v pytest &> /dev/null; then
        if pytest -q --tb=no "$PROJECT_DIR/tests" > /dev/null 2>&1; then
            TDD_PHASE="GREEN or REFACTOR (tests passing)"
        else
            TDD_PHASE="RED (tests failing)"
        fi
    else
        TDD_PHASE="unknown (pytest not available)"
    fi
else
    TDD_PHASE="N/A (no tests directory)"
fi

# --- Write enhanced state file ---
cat > "$STATE_FILE" << EOF
# Pre-Compaction State
*Saved: $TIMESTAMP*

## Active Task
$ACTIVE_TASK

## Task Master Tag
$ACTIVE_TAG

## TDD Phase
$TDD_PHASE

## Branch: $CURRENT_BRANCH

## Uncommitted Changes ($UNCOMMITTED_COUNT files)
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
