#!/bin/bash
# Claude Code Status Line
# Displays: model | git branch | context % bar | session duration
# Receives JSON session data via stdin from Claude Code
#
# Setup: Add to ~/.claude/settings.json:
#   { "statusLine": { "type": "command", "command": "~/.claude/statusline.sh" } }
#
# Or for project-level:
#   { "statusLine": { "type": "command", "command": ".claude/statusline.sh" } }

input=$(cat)

# --- Model ---
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')

# --- Git Branch ---
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -n "$branch" ]; then
    # Check for dirty working tree
    if ! git diff --quiet HEAD 2>/dev/null; then
        branch="${branch}*"
    fi
else
    branch="-"
fi

# --- Context Window ---
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
# Build 10-char progress bar
filled=$(( pct / 10 ))
empty=$(( 10 - filled ))
bar=""
for ((i=0; i<filled; i++)); do bar+="█"; done
for ((i=0; i<empty; i++)); do bar+="░"; done

# Color the percentage: green <50, yellow 50-75, red >75
if [ "$pct" -ge 75 ]; then
    color="\033[31m"  # red
elif [ "$pct" -ge 50 ]; then
    color="\033[33m"  # yellow
else
    color="\033[32m"  # green
fi
reset="\033[0m"

# --- Session Duration ---
ms=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
secs=$(( ms / 1000 ))
if [ "$secs" -ge 3600 ]; then
    hrs=$(( secs / 3600 ))
    mins=$(( (secs % 3600) / 60 ))
    duration="${hrs}h ${mins}m"
elif [ "$secs" -ge 60 ]; then
    mins=$(( secs / 60 ))
    duration="${mins}m"
else
    duration="${secs}s"
fi

# --- Output ---
printf "[%s] %s │ ctx: %s %b%s%%%b │ %s" \
    "$model" "$branch" "$bar" "$color" "$pct" "$reset" "$duration"
