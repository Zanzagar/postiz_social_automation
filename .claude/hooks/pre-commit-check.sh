#!/bin/bash
# pre-commit-check.sh - Validate code before committing
# Hook type: PreToolUse (matcher: "Bash")
# Triggers when: Claude runs git commit commands
#
# Exit codes:
#   0 = Allow the commit
#   2 = Block the commit (shows reason to Claude)
#   1 = Warning only (doesn't block)
#
# Skip individual checks with environment variables:
#   SKIP_BRANCH_CHECK=1  - Skip main/master branch protection
#   SKIP_COMMIT_FORMAT=1 - Skip conventional commit format validation
#   SKIP_LINT=1           - Skip linter check
#   SKIP_TESTS=1          - Skip test suite check
#   SKIP_TASK_CHECK=1     - Skip task-in-progress advisory warning

# Best-effort: never silently skip checks
set +e

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

# --- Check 1: Branch protection (R1.2) ---
# Block direct commits to main/master branch
if [[ -z "$SKIP_BRANCH_CHECK" ]]; then
    CURRENT_BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "")
    if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
        ERRORS+=("Direct commits to $CURRENT_BRANCH are blocked.")
        ERRORS+=("Create a feature branch: git checkout -b feature/<description>")
    fi
fi

# --- Check 2: Conventional commit format (R1.1) ---
# Validate commit message matches: type(scope)?: description
if [[ -z "$SKIP_COMMIT_FORMAT" ]]; then
    COMMIT_MSG=""
    # Extract message from -m "message" or -m 'message'
    if [[ "$COMMAND" =~ -m[[:space:]]+\"([^\"]+)\" ]]; then
        COMMIT_MSG="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ -m[[:space:]]+\'([^\']+)\' ]]; then
        COMMIT_MSG="${BASH_REMATCH[1]}"
    elif [[ "$COMMAND" =~ -m[[:space:]]+\"\$\(cat ]]; then
        # Heredoc pattern: -m "$(cat <<'EOF' ... — extract first line after heredoc
        if [[ "$COMMAND" =~ $'\n'([^$'\n']+) ]]; then
            COMMIT_MSG="${BASH_REMATCH[1]}"
        fi
    fi

    if [[ -n "$COMMIT_MSG" ]]; then
        # Conventional commit regex: type(scope)?!?: description
        CONVENTIONAL_REGEX='^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([a-zA-Z0-9_-]+\))?!?:[[:space:]].+'
        if [[ ! "$COMMIT_MSG" =~ $CONVENTIONAL_REGEX ]]; then
            ERRORS+=("Commit message must follow conventional commits format: type: description")
            ERRORS+=("  Valid types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert")
            ERRORS+=("  Example: feat: add user authentication")
        fi
    fi
    # If COMMIT_MSG is empty (e.g., --file, --amend, heredoc we can't parse), skip check gracefully
fi

# --- Check 3: Run linter if ruff is available (R1.4) ---
if [[ -z "$SKIP_LINT" ]]; then
    if command -v ruff &> /dev/null; then
        LINT_DIRS=()
        [ -d "$PROJECT_DIR/src" ] && LINT_DIRS+=("$PROJECT_DIR/src")
        [ -d "$PROJECT_DIR/tests" ] && LINT_DIRS+=("$PROJECT_DIR/tests")
        if [ ${#LINT_DIRS[@]} -gt 0 ]; then
            if ! ruff check "${LINT_DIRS[@]}" 2>/dev/null; then
                ERRORS+=("Linting errors found. Run 'ruff check --fix' first.")
            fi
        fi
    fi
fi

# --- Check 4: Run tests if pytest is available (R1.4) ---
if [[ -z "$SKIP_TESTS" ]]; then
    if command -v pytest &> /dev/null; then
        if [ -d "$PROJECT_DIR/tests" ]; then
            if ! pytest -q --tb=no "$PROJECT_DIR/tests" 2>/dev/null; then
                ERRORS+=("Tests are failing. Fix tests before committing.")
            fi
        fi
    fi
fi

# --- Check 5: Look for common issues in staged files ---
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

# --- Advisory: Task Master in-progress check (R1.3) ---
if [[ -z "$SKIP_TASK_CHECK" ]]; then
    if command -v task-master &> /dev/null; then
        IN_PROGRESS=$(task-master list --status in-progress 2>/dev/null | grep -c "in-progress" || true)
        if [[ "$IN_PROGRESS" -eq 0 ]]; then
            echo "Advisory: No Task Master task is in-progress. Consider tracking work with task-master."
        fi
    fi
fi

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
