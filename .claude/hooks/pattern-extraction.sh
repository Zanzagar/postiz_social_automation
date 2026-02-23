#!/bin/bash
# pattern-extraction.sh - Extract patterns from session for continuous learning
# Hook type: Stop (runs on session end)
# Triggers when: Claude Code session ends
#
# Analyzes git history from the current session to identify potential
# instinct candidates. Saves a session summary + heuristic patterns
# as JSON files in .claude/instincts/candidates/
#
# This is the engine that powers cross-session learning. Without it,
# the instinct system only grows via manual /learn invocations.
#
# Exit codes:
#   0 = Always (best effort, never blocks)

set +e  # Never fail — this is advisory

INSTINCT_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/instincts/candidates"
mkdir -p "$INSTINCT_DIR"

# Get commits from the last 4 hours (approximate session length)
RECENT_COMMITS=$(git log --since="4 hours ago" --oneline 2>/dev/null)
[ -z "$RECENT_COMMITS" ] && exit 0

# Dedup: skip if a candidate already exists for the current HEAD commit
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
if grep -rl "\"head_commit\": \"$HEAD_SHA\"" "$INSTINCT_DIR" >/dev/null 2>&1; then
    exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID=$(date +"%Y%m%d_%H%M%S")

# Count commit types to detect patterns
FEAT_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* feat" || true)
FIX_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* fix" || true)
TEST_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* test" || true)
REFACTOR_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* refactor" || true)
TOTAL_COMMITS=$(echo "$RECENT_COMMITS" | wc -l | tr -d ' ')

# Only extract if there was meaningful work (3+ commits)
[ "$TOTAL_COMMITS" -lt 3 ] && exit 0

# Get the file types worked on
FILE_TYPES=$(git diff --name-only HEAD~"$TOTAL_COMMITS"..HEAD 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -5)

# Build file_types JSON safely
FILE_TYPES_JSON=$(echo "$FILE_TYPES" | awk 'NF==2 {printf "%s\"%s\": %s", (NR>1?", ":""), $2, $1}' | sed 's/^/{/;s/$/}/')
[ -z "$FILE_TYPES_JSON" ] && FILE_TYPES_JSON="{}"

# Collect commit messages for downstream analysis
COMMIT_MESSAGES=$(echo "$RECENT_COMMITS" | sed 's/^[a-f0-9]* //' | jq -R . | jq -s '.')

# Detect dominant work category
CATEGORY="general"
if [ "$FIX_COUNT" -gt "$FEAT_COUNT" ] && [ "$FIX_COUNT" -gt "$REFACTOR_COUNT" ]; then
    CATEGORY="debugging-approach"
elif [ "$TEST_COUNT" -ge 2 ]; then
    CATEGORY="testing-strategy"
elif [ "$REFACTOR_COUNT" -ge 2 ]; then
    CATEGORY="coding-style"
elif [ "$FEAT_COUNT" -ge 2 ]; then
    CATEGORY="architecture-preference"
fi

# Determine primary language from file types
PRIMARY_LANG=$(echo "$FILE_TYPES" | head -1 | awk '{print $2}')

# Generate session summary candidate
cat > "$INSTINCT_DIR/session_${SESSION_ID}.json" << INSTINCT_EOF
{
  "type": "session-summary",
  "extracted_at": "$TIMESTAMP",
  "session_id": "$SESSION_ID",
  "head_commit": "$HEAD_SHA",
  "commit_count": $TOTAL_COMMITS,
  "commit_types": {
    "feat": $FEAT_COUNT,
    "fix": $FIX_COUNT,
    "test": $TEST_COUNT,
    "refactor": $REFACTOR_COUNT
  },
  "file_types_touched": $FILE_TYPES_JSON,
  "primary_language": "$PRIMARY_LANG",
  "detected_category": "$CATEGORY",
  "commit_messages": $COMMIT_MESSAGES,
  "status": "candidate",
  "confidence": 0.3,
  "notes": "Auto-extracted from session. Use /learn to analyze and promote to instincts."
}
INSTINCT_EOF

echo "Pattern extraction complete: $TOTAL_COMMITS commits analyzed."
echo "Candidate saved to $INSTINCT_DIR/session_${SESSION_ID}.json"

exit 0
