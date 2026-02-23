#!/bin/bash
# typescript-check.sh - Run type checking after editing TypeScript files
# Hook type: PostToolUse (matcher: "Edit")
# Triggers after: Claude edits a file
#
# If the edited file is .ts or .tsx, runs tsc --noEmit on it to catch
# type errors immediately. Fast feedback prevents debugging later.
#
# Exit codes:
#   0 = Always (advisory only, never blocks)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] && exit 0

# Only check TypeScript files
case "$FILE_PATH" in
    *.ts|*.tsx) ;;
    *) exit 0 ;;
esac

# Check if tsc is available
if ! command -v npx &>/dev/null; then
    exit 0
fi

# Find the nearest tsconfig.json
SEARCH_DIR=$(dirname "$FILE_PATH")
TSCONFIG=""
while [ "$SEARCH_DIR" != "/" ]; do
    if [ -f "$SEARCH_DIR/tsconfig.json" ]; then
        TSCONFIG="$SEARCH_DIR/tsconfig.json"
        break
    fi
    SEARCH_DIR=$(dirname "$SEARCH_DIR")
done

[ -z "$TSCONFIG" ] && exit 0

# Run type check (quick, single file context)
TSC_OUTPUT=$(cd "$(dirname "$TSCONFIG")" && npx tsc --noEmit --pretty 2>&1 | grep "$FILE_PATH" | head -5)

if [ -n "$TSC_OUTPUT" ]; then
    ERROR_COUNT=$(echo "$TSC_OUTPUT" | wc -l)
    echo "TYPESCRIPT CHECK: $ERROR_COUNT type error(s) in $(basename "$FILE_PATH"):"
    echo "$TSC_OUTPUT"
fi

exit 0
