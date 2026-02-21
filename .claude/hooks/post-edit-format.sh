#!/bin/bash
# post-edit-format.sh - Auto-format files after editing
# Hook type: PostToolUse (matcher: "Edit|Write")
# Triggers when: Claude edits or writes files
#
# This hook runs formatters automatically after file changes.
# Exit code doesn't block (PostToolUse can't block), but feedback is shown.

set -e

# Read the input JSON from stdin
INPUT=$(cat)

# Extract the file path that was edited
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty')

[ -z "$FILE_PATH" ] && exit 0
[ -f "$FILE_PATH" ] || exit 0

# Determine file type and format accordingly
case "$FILE_PATH" in
    *.py)
        # Python: Use ruff for formatting
        if command -v ruff &> /dev/null; then
            ruff format "$FILE_PATH" 2>/dev/null && echo "Formatted: $FILE_PATH (ruff)"
        fi
        ;;
    *.js|*.jsx|*.ts|*.tsx|*.json|*.md)
        # JavaScript/TypeScript/JSON/Markdown: Use prettier
        if command -v prettier &> /dev/null; then
            prettier --write "$FILE_PATH" 2>/dev/null && echo "Formatted: $FILE_PATH (prettier)"
        fi
        ;;
    *.go)
        # Go: Use gofmt
        if command -v gofmt &> /dev/null; then
            gofmt -w "$FILE_PATH" 2>/dev/null && echo "Formatted: $FILE_PATH (gofmt)"
        fi
        ;;
    *.rs)
        # Rust: Use rustfmt
        if command -v rustfmt &> /dev/null; then
            rustfmt "$FILE_PATH" 2>/dev/null && echo "Formatted: $FILE_PATH (rustfmt)"
        fi
        ;;
    *.sh)
        # Shell: Use shfmt if available
        if command -v shfmt &> /dev/null; then
            shfmt -w "$FILE_PATH" 2>/dev/null && echo "Formatted: $FILE_PATH (shfmt)"
        fi
        ;;
esac

exit 0
