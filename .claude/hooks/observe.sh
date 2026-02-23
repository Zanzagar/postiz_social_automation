#!/bin/bash
# observe.sh - Continuous Learning v2 observation hook
# Adapted from ECC (affaan-m/everything-claude-code) continuous-learning-v2
#
# Captures tool use events for pattern analysis.
# Claude Code passes hook data via stdin as JSON.
#
# Hook type: PreToolUse / PostToolUse
# Phase argument: "pre" or "post" passed as $1 from hook config
#
# Fix applied from ECC PR #242: Uses $1 for phase detection instead of
# stdin hook_type field (which Claude Code does not include).
#
# Hook config (in .claude/settings.json):
# {
#   "hooks": {
#     "PreToolUse": [{
#       "matcher": "*",
#       "hooks": [{ "type": "command", "command": ".claude/hooks/observe.sh pre" }]
#     }],
#     "PostToolUse": [{
#       "matcher": "*",
#       "hooks": [{ "type": "command", "command": ".claude/hooks/observe.sh post" }]
#     }]
#   }
# }

set +e  # Never fail — observation is best-effort

# Project-scoped paths (not global ~/.claude/homunculus/)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
CONFIG_DIR="$PROJECT_DIR/.claude/instincts"
OBSERVATIONS_FILE="$CONFIG_DIR/observations.jsonl"
MAX_FILE_SIZE_MB=10

# Phase detection from CLI argument (PR #242 fix)
HOOK_PHASE="${1:-post}"
export HOOK_PHASE

# Ensure directory exists
mkdir -p "$CONFIG_DIR"

# Skip if disabled
if [ -f "$CONFIG_DIR/disabled" ]; then
    exit 0
fi

# Read JSON from stdin (Claude Code hook format)
INPUT_JSON=$(cat)

# Exit if no input
if [ -z "$INPUT_JSON" ]; then
    exit 0
fi

# Parse using python via stdin pipe (safe for all JSON payloads)
PARSED=$(echo "$INPUT_JSON" | python3 -c '
import json
import sys
import os

try:
    data = json.load(sys.stdin)

    # Phase comes from CLI argument, not stdin JSON
    hook_phase = os.environ.get("HOOK_PHASE", "post")

    tool_name = data.get("tool_name", data.get("tool", "unknown"))
    tool_input = data.get("tool_input", data.get("input", {}))
    tool_output = data.get("tool_output", data.get("output", ""))
    session_id = data.get("session_id", "unknown")

    # Truncate large inputs/outputs
    if isinstance(tool_input, dict):
        tool_input_str = json.dumps(tool_input)[:5000]
    else:
        tool_input_str = str(tool_input)[:5000]

    if isinstance(tool_output, dict):
        tool_output_str = json.dumps(tool_output)[:5000]
    else:
        tool_output_str = str(tool_output)[:5000]

    # Determine event type from CLI phase argument
    event = "tool_start" if hook_phase == "pre" else "tool_complete"

    print(json.dumps({
        "parsed": True,
        "event": event,
        "tool": tool_name,
        "input": tool_input_str if event == "tool_start" else None,
        "output": tool_output_str if event == "tool_complete" else None,
        "session": session_id
    }))
except Exception as e:
    print(json.dumps({"parsed": False, "error": str(e)}))
' 2>/dev/null)

# Check if parsing succeeded
PARSED_OK=$(echo "$PARSED" | python3 -c "import json,sys; print(json.load(sys.stdin).get('parsed', False))" 2>/dev/null)

if [ "$PARSED_OK" != "True" ]; then
    # Fallback: log raw input for debugging
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    export TIMESTAMP
    echo "$INPUT_JSON" | python3 -c "
import json, sys, os
raw = sys.stdin.read()[:2000]
print(json.dumps({'timestamp': os.environ['TIMESTAMP'], 'event': 'parse_error', 'raw': raw}))
" >> "$OBSERVATIONS_FILE" 2>/dev/null
    exit 0
fi

# Archive if file too large
if [ -f "$OBSERVATIONS_FILE" ]; then
    file_size_mb=$(du -m "$OBSERVATIONS_FILE" 2>/dev/null | cut -f1)
    if [ "${file_size_mb:-0}" -ge "$MAX_FILE_SIZE_MB" ]; then
        archive_dir="$CONFIG_DIR/observations.archive"
        mkdir -p "$archive_dir"
        mv "$OBSERVATIONS_FILE" "$archive_dir/observations-$(date +%Y%m%d-%H%M%S).jsonl"
    fi
fi

# Build and write observation
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export TIMESTAMP

echo "$PARSED" | python3 -c "
import json, sys, os

parsed = json.load(sys.stdin)
observation = {
    'timestamp': os.environ['TIMESTAMP'],
    'event': parsed['event'],
    'tool': parsed['tool'],
    'session': parsed['session']
}

if parsed.get('input'):
    observation['input'] = parsed['input']
if parsed.get('output'):
    observation['output'] = parsed['output']

print(json.dumps(observation))
" >> "$OBSERVATIONS_FILE" 2>/dev/null

# Signal observer if running
OBSERVER_PID_FILE="$CONFIG_DIR/.observer.pid"
if [ -f "$OBSERVER_PID_FILE" ]; then
    observer_pid=$(cat "$OBSERVER_PID_FILE")
    if kill -0 "$observer_pid" 2>/dev/null; then
        kill -USR1 "$observer_pid" 2>/dev/null || true
    fi
fi

exit 0
