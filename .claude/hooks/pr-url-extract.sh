#!/usr/bin/env bash
# pr-url-extract.sh - Extract PR URL from git push output
# Hook type: PostToolUse (matcher: "Bash")
# Triggers when: After Bash command completes
#
# Extracts PR creation URLs from git push output and provides
# helpful review commands. Advisory only — never blocks.
#
# Exit codes:
#   0 = Always (advisory hook)

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
OUTPUT=$(echo "$INPUT" | jq -r '.stdout // empty')

# Process git push and gh pr create commands (merged trigger points)
[[ "$COMMAND" != *"git push"* && "$COMMAND" != *"gh pr create"* ]] && exit 0

# ECC pattern: extract PR URL from gh pr create output
if [[ "$COMMAND" == *"gh pr create"* ]]; then
    CREATED_PR=$(echo "$OUTPUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/[0-9]+' | head -1)
    if [ -n "$CREATED_PR" ]; then
        REPO=$(echo "$CREATED_PR" | sed 's|https://github.com/\([^/]*/[^/]*\)/pull/.*|\1|')
        PR_NUM=$(echo "$CREATED_PR" | sed 's|.*/pull/\([0-9]*\)|\1|')
        echo "PR created: $CREATED_PR"
        echo "To review: gh pr review $PR_NUM --repo $REPO"
    fi
    exit 0
fi

# Extract PR URL patterns:
# GitHub: https://github.com/owner/repo/pull/new/branch-name
PR_URL=$(echo "$OUTPUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/new/[^[:space:]]+' | head -1)

# GitHub compare URL: https://github.com/owner/repo/compare/branch-name
if [ -z "$PR_URL" ]; then
    PR_URL=$(echo "$OUTPUT" | grep -oE 'https://github\.com/[^/]+/[^/]+/compare/[^[:space:]]+' | head -1)
fi

# GitLab: https://gitlab.com/.../merge_requests/new
if [ -z "$PR_URL" ]; then
    PR_URL=$(echo "$OUTPUT" | grep -oE 'https://gitlab\.com/[^[:space:]]+merge_requests/new[^[:space:]]*' | head -1)
fi

# Also check stderr (git push writes to stderr)
if [ -z "$PR_URL" ]; then
    STDERR=$(echo "$INPUT" | jq -r '.stderr // empty')
    PR_URL=$(echo "$STDERR" | grep -oE 'https://github\.com/[^/]+/[^/]+/pull/new/[^[:space:]]+' | head -1)
    if [ -z "$PR_URL" ]; then
        PR_URL=$(echo "$STDERR" | grep -oE 'https://github\.com/[^/]+/[^/]+/compare/[^[:space:]]+' | head -1)
    fi
fi

[ -z "$PR_URL" ] && exit 0

# Output helpful message
echo "PR creation URL detected: $PR_URL"
echo ""
echo "Quick actions:"
echo "  /pr                     # Create PR via Claude Code"
echo "  gh pr create --web      # Open PR creation in browser"
echo "  gh pr view --web        # View existing PR"

exit 0
