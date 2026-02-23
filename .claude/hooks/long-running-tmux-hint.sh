#!/bin/bash
# long-running-tmux-hint.sh - Advisory tmux reminder for long commands
# Hook type: PreToolUse (matcher: "Bash")
# Triggers when: Claude attempts to run a Bash command
#
# Detects potentially long-running commands and suggests tmux
# if not already in a tmux session. Complements dev-server-blocker.sh.
#
# Exit codes:
#   0 = Always allow (advisory only, never blocks)

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0

# Already in tmux? No reminder needed.
[ -n "$TMUX" ] && exit 0

# Detect long-running command patterns
IS_LONG_RUNNING=false
REASON=""

case "$COMMAND" in
    *"npm install"*|*"npm ci"*|*"pnpm install"*|*"yarn install"*)
        IS_LONG_RUNNING=true; REASON="Package installation can take several minutes" ;;
    *"pip install"*|*"poetry install"*|*"pdm install"*)
        IS_LONG_RUNNING=true; REASON="Python dependency installation can be slow" ;;
    *"pytest"*|*"python -m pytest"*)
        IS_LONG_RUNNING=true; REASON="Test suites can run for minutes" ;;
    *"cargo build"*|*"cargo test"*)
        IS_LONG_RUNNING=true; REASON="Rust compilation can be slow" ;;
    *"make"*|*"cmake --build"*)
        IS_LONG_RUNNING=true; REASON="Build processes can take time" ;;
    *"docker build"*|*"docker-compose up"*|*"docker compose up"*)
        IS_LONG_RUNNING=true; REASON="Container builds can be slow" ;;
    *"go build"*|*"go test"*)
        IS_LONG_RUNNING=true; REASON="Go builds with dependencies can take time" ;;
    *"mvn"*|*"gradle"*|*"./gradlew"*)
        IS_LONG_RUNNING=true; REASON="Java builds are typically slow" ;;
esac

[ "$IS_LONG_RUNNING" = false ] && exit 0

# Advisory message (never blocks)
echo "HINT: $REASON."
echo "Consider tmux for session persistence: tmux new-session -d '$COMMAND'"

exit 0
