#!/bin/bash
# pattern-extraction.sh - Extract patterns from session for continuous learning
# Hook type: Stop (runs on session end)
# Triggers when: Claude Code session ends
#
# Analyzes git history from the current session to identify potential
# instinct candidates. Saves them as JSON files in .claude/instincts/candidates/
#
# This is the engine that powers cross-session learning. Without it,
# the instinct system only grows via manual /learn invocations.
#
# Exit codes:
#   0 = Always (best effort, never blocks)

INSTINCT_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/instincts/candidates"
mkdir -p "$INSTINCT_DIR"

# Get commits from the last 4 hours (approximate session length)
RECENT_COMMITS=$(git log --since="4 hours ago" --oneline 2>/dev/null)
[ -z "$RECENT_COMMITS" ] && exit 0

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID=$(date +"%Y%m%d_%H%M%S")

# Count commit types to detect patterns
FEAT_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* feat" || true)
FIX_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* fix" || true)
TEST_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* test" || true)
REFACTOR_COUNT=$(echo "$RECENT_COMMITS" | grep -c "^[a-f0-9]* refactor" || true)
TOTAL_COMMITS=$(echo "$RECENT_COMMITS" | wc -l)

# Only extract if there was meaningful work (3+ commits)
[ "$TOTAL_COMMITS" -lt 3 ] && exit 0

# Get the file types worked on
FILE_TYPES=$(git diff --name-only HEAD~"$TOTAL_COMMITS"..HEAD 2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -5)

# Generate a session summary as a candidate instinct
cat > "$INSTINCT_DIR/session_${SESSION_ID}.json" << INSTINCT_EOF
{
  "extracted_at": "$TIMESTAMP",
  "session_id": "$SESSION_ID",
  "commit_count": $TOTAL_COMMITS,
  "commit_types": {
    "feat": $FEAT_COUNT,
    "fix": $FIX_COUNT,
    "test": $TEST_COUNT,
    "refactor": $REFACTOR_COUNT
  },
  "file_types_touched": $(echo "$FILE_TYPES" | awk '{print "\"" $2 "\": " $1}' | paste -sd, | sed 's/^/{/;s/$/}/'),
  "status": "candidate",
  "confidence": 0.3,
  "notes": "Auto-extracted from session. Review with /instinct-status and promote or discard."
}
INSTINCT_EOF

echo "Pattern extraction complete: $TOTAL_COMMITS commits analyzed."
echo "Candidate instinct saved to $INSTINCT_DIR/session_${SESSION_ID}.json"

exit 0
