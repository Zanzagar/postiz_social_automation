#!/bin/bash
# doc-file-blocker.sh - Prevent creation of unnecessary documentation files
# Hook type: PreToolUse (matcher: "Write")
# Triggers when: Claude attempts to create a new file
#
# LLMs tend to create unnecessary .md and .txt files ("let me create NOTES.md...")
# This hook allows documentation only in approved locations.
#
# Exit codes:
#   0 = Allow the write
#   2 = Block the write

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] && exit 0

FILENAME=$(basename "$FILE_PATH")
EXTENSION="${FILENAME##*.}"

# Only check documentation file types
if [[ "$EXTENSION" != "md" && "$EXTENSION" != "txt" && "$EXTENSION" != "rst" ]]; then
    exit 0
fi

# Allowed documentation files (exact names)
ALLOWED_FILES=(
    "README.md"
    "CLAUDE.md"
    "CHANGELOG.md"
    "CONTRIBUTING.md"
    "LICENSE.md"
    "LICENSE"
    "SECURITY.md"
    "CODE_OF_CONDUCT.md"
    "SKILL.md"
)

for allowed in "${ALLOWED_FILES[@]}"; do
    if [[ "$FILENAME" == "$allowed" ]]; then
        exit 0
    fi
done

# Allowed documentation directories
ALLOWED_DIRS=(
    "/docs/"
    "/.claude/"
    "/.taskmaster/"
    "/.prd/"
)

for dir in "${ALLOWED_DIRS[@]}"; do
    if [[ "$FILE_PATH" == *"$dir"* ]]; then
        exit 0
    fi
done

# Block unexpected documentation files
echo "BLOCKED: Creating documentation file outside approved locations: $FILENAME"
echo "Allowed locations: docs/, .claude/, .taskmaster/, or standard files (README.md, CHANGELOG.md, etc.)"
echo "If this file is needed, create it in docs/ or ask the user first."
exit 2
