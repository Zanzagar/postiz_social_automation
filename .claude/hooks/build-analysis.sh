#!/bin/bash
# build-analysis.sh - Analyze build command output for proactive feedback
# Hook type: PostToolUse (matcher: "Bash")
# Triggers after: Claude runs a Bash command
#
# Detects build commands and provides advisory analysis of the output.
# Runs quickly and does not block the workflow.
#
# Exit codes:
#   0 = Always (advisory only)

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
OUTPUT=$(echo "$INPUT" | jq -r '.tool_result.stdout // empty' 2>/dev/null)
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_result.exit_code // 0' 2>/dev/null)

[ -z "$COMMAND" ] && exit 0

# Detect build commands
IS_BUILD=false
case "$COMMAND" in
    *"npm run build"*|*"npx tsc"*|*"yarn build"*)
        IS_BUILD=true; BUILD_TYPE="node" ;;
    *"cargo build"*|*"cargo check"*)
        IS_BUILD=true; BUILD_TYPE="rust" ;;
    *"go build"*|*"go vet"*)
        IS_BUILD=true; BUILD_TYPE="go" ;;
    *"mvn compile"*|*"mvn package"*|*"gradle build"*)
        IS_BUILD=true; BUILD_TYPE="java" ;;
    *"python -m py_compile"*|*"python setup.py"*|*"pip install"*)
        IS_BUILD=true; BUILD_TYPE="python" ;;
    *"make"*|*"cmake"*)
        IS_BUILD=true; BUILD_TYPE="native" ;;
esac

[ "$IS_BUILD" = false ] && exit 0

# Analyze build output
if [ "$EXIT_CODE" != "0" ]; then
    # Build failed — count errors
    ERROR_COUNT=$(echo "$OUTPUT" | grep -ci "error" || true)
    WARNING_COUNT=$(echo "$OUTPUT" | grep -ci "warning" || true)

    echo "BUILD ANALYSIS ($BUILD_TYPE):"
    echo "  Status: FAILED (exit code $EXIT_CODE)"
    [ "$ERROR_COUNT" -gt 0 ] && echo "  Errors: ~$ERROR_COUNT"
    [ "$WARNING_COUNT" -gt 0 ] && echo "  Warnings: ~$WARNING_COUNT"
    echo "  Suggestion: Fix errors one at a time. Use /build-fix for guided resolution."
else
    # Build succeeded — check for warnings
    WARNING_COUNT=$(echo "$OUTPUT" | grep -ci "warning" || true)
    if [ "$WARNING_COUNT" -gt 3 ]; then
        echo "BUILD ANALYSIS ($BUILD_TYPE):"
        echo "  Status: SUCCESS with $WARNING_COUNT warnings"
        echo "  Consider addressing warnings to prevent future issues."
    fi
fi

exit 0
