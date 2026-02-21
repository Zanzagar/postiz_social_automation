#!/bin/bash
# dev-server-blocker.sh - Prevent dev servers from capturing the terminal
# Hook type: PreToolUse (matcher: "Bash")
# Triggers when: Claude attempts to run a Bash command
#
# Dev servers (npm run dev, flask run, etc.) run indefinitely and capture
# the terminal. This hook blocks them unless running inside tmux, where
# you can detach safely.
#
# Exit codes:
#   0 = Allow the command
#   2 = Block the command

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0

# Detect dev server commands
IS_DEV_SERVER=false
case "$COMMAND" in
    *"npm run dev"*|*"npm start"*|*"npx next dev"*)
        IS_DEV_SERVER=true; SERVER="Node.js dev server" ;;
    *"pnpm dev"*|*"pnpm run dev"*|*"yarn dev"*)
        IS_DEV_SERVER=true; SERVER="Node.js dev server" ;;
    *"flask run"*|*"python -m flask run"*)
        IS_DEV_SERVER=true; SERVER="Flask dev server" ;;
    *"uvicorn"*"--reload"*|*"python manage.py runserver"*)
        IS_DEV_SERVER=true; SERVER="Python dev server" ;;
    *"hugo server"*|*"jekyll serve"*)
        IS_DEV_SERVER=true; SERVER="Static site dev server" ;;
    *"cargo watch"*)
        IS_DEV_SERVER=true; SERVER="Cargo watch server" ;;
esac

[ "$IS_DEV_SERVER" = false ] && exit 0

# Allow if running in background (& at end)
if [[ "$COMMAND" == *"&" ]] || [[ "$COMMAND" == *"run_in_background"* ]]; then
    exit 0
fi

# Allow if inside tmux
if [ -n "$TMUX" ]; then
    exit 0
fi

# Block with helpful message
echo "BLOCKED: $SERVER would capture the terminal."
echo ""
echo "Options:"
echo "  1. Run in tmux:  tmux new-session -d '$COMMAND'"
echo "  2. Run in background: Add & to the command"
echo "  3. Use Claude Code's run_in_background parameter"
echo ""
echo "Dev servers run indefinitely. Without tmux or background mode,"
echo "killing the terminal kills the server and any unsaved state."
exit 2
