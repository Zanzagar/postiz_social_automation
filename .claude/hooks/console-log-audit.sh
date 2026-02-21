#!/bin/bash
# console-log-audit.sh - Warn about debug statements in edited files
# Hook type: PostToolUse (matcher: "Edit")
# Triggers after: Claude edits a file
#
# Scans the edited file for common debug statements that shouldn't
# be committed. Warns but does not block (exit 0).
#
# Exit codes:
#   0 = Always (advisory only)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

EXTENSION="${FILE_PATH##*.}"
WARNINGS=""

case "$EXTENSION" in
    py)
        # Python debug statements
        MATCHES=$(grep -n "print(" "$FILE_PATH" 2>/dev/null | grep -v "# noqa" | grep -v "logging\." | head -5)
        if [ -n "$MATCHES" ]; then
            WARNINGS="Python print() statements found (consider using logging):\n$MATCHES"
        fi
        BREAKPOINTS=$(grep -n "breakpoint()\|pdb\.set_trace()\|import pdb" "$FILE_PATH" 2>/dev/null | head -3)
        if [ -n "$BREAKPOINTS" ]; then
            WARNINGS="$WARNINGS\nPython debugger statements found:\n$BREAKPOINTS"
        fi
        ;;
    js|jsx|ts|tsx)
        # JavaScript/TypeScript debug statements
        MATCHES=$(grep -n "console\.log\|console\.debug\|console\.warn\|debugger" "$FILE_PATH" 2>/dev/null | head -5)
        if [ -n "$MATCHES" ]; then
            WARNINGS="JavaScript debug statements found:\n$MATCHES"
        fi
        ;;
    go)
        # Go debug statements
        MATCHES=$(grep -n "fmt\.Print\|fmt\.Println\|log\.Print\|log\.Println" "$FILE_PATH" 2>/dev/null | grep -v "// debug" | head -5)
        if [ -n "$MATCHES" ]; then
            WARNINGS="Go print/log statements found (consider structured logging):\n$MATCHES"
        fi
        ;;
    java)
        # Java debug statements
        MATCHES=$(grep -n "System\.out\.print\|System\.err\.print\|e\.printStackTrace()" "$FILE_PATH" 2>/dev/null | head -5)
        if [ -n "$MATCHES" ]; then
            WARNINGS="Java debug statements found (use a logger):\n$MATCHES"
        fi
        ;;
    rb)
        # Ruby debug statements
        MATCHES=$(grep -n "puts \|p \|pp \|binding\.pry\|byebug" "$FILE_PATH" 2>/dev/null | head -5)
        if [ -n "$MATCHES" ]; then
            WARNINGS="Ruby debug statements found:\n$MATCHES"
        fi
        ;;
esac

if [ -n "$WARNINGS" ]; then
    echo -e "DEBUG AUDIT WARNING for $FILE_PATH:"
    echo -e "$WARNINGS"
    echo "These may be intentional, but review before committing."
fi

exit 0
