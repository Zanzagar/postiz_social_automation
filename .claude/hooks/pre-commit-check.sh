#!/bin/bash
# pre-commit-check.sh - Validate code before committing
# Hook type: PreToolUse (matcher: "Bash")
# Triggers when: Claude runs git commit commands
#
# Exit codes:
#   0 = Allow the commit
#   2 = Block the commit (shows reason to Claude)
#   1 = Warning only (doesn't block)

set -e

# Read the input JSON from stdin
INPUT=$(cat)

# Extract the command being run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only check git commit commands
if [[ ! "$COMMAND" =~ ^git\ commit ]]; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
ERRORS=()

# Check 1: Run linter if ruff is available
if command -v ruff &> /dev/null; then
    if ! ruff check "$PROJECT_DIR/src" "$PROJECT_DIR/tests" 2>/dev/null; then
        ERRORS+=("Linting errors found. Run 'ruff check --fix' first.")
    fi
fi

# Check 2: Run tests if pytest is available
if command -v pytest &> /dev/null; then
    if ! pytest -q --tb=no "$PROJECT_DIR/tests" 2>/dev/null; then
        ERRORS+=("Tests are failing. Fix tests before committing.")
    fi
fi

# Check 3: Look for common issues in staged files
STAGED_FILES=$(cd "$PROJECT_DIR" && git diff --cached --name-only 2>/dev/null || echo "")

for file in $STAGED_FILES; do
    filepath="$PROJECT_DIR/$file"
    [ -f "$filepath" ] || continue

    # Check for debug statements
    if grep -q "import pdb\|breakpoint()\|console\.log\|debugger" "$filepath" 2>/dev/null; then
        ERRORS+=("Debug statement found in $file")
    fi

    # Check for hardcoded secrets patterns
    if grep -qE "(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]" "$filepath" 2>/dev/null; then
        ERRORS+=("Possible hardcoded secret in $file")
    fi
done

# Report results
if [ ${#ERRORS[@]} -gt 0 ]; then
    echo "Pre-commit checks failed:"
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
    exit 2  # Block the commit
fi

echo "Pre-commit checks passed"
exit 0
