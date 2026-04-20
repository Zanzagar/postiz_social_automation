#!/usr/bin/env bash
# Executes a bash hook script only when enabled by template hook profile flags.
# Adapted from ECC (affaan-m/everything-claude-code) scripts/hooks/run-with-flags-shell.sh
#
# Usage:
#   bash run-with-flags-shell.sh <hookId> <scriptPath> [profilesCsv] [extra args...]
#
# Template adaptation: uses set +e for resilience (learned from hook failures),
# supports extra args passthrough (needed for observe.sh pre/post).

# Resilience: never let unexpected errors silently kill the hook
set +e

HOOK_ID="${1:-}"
SCRIPT_PATH="${2:-}"
PROFILES_CSV="${3:-standard,strict}"
shift 3 2>/dev/null || true
EXTRA_ARGS=("$@")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/../../.." && pwd)}"

# Preserve stdin for passthrough or script execution
INPUT="$(cat)"

if [[ -z "$HOOK_ID" || -z "$SCRIPT_PATH" ]]; then
  printf '%s' "$INPUT"
  exit 0
fi

# Ask Node helper if this hook is enabled
ENABLED="$(node "${SCRIPT_DIR}/check-hook-enabled.js" "$HOOK_ID" "$PROFILES_CSV" 2>/dev/null || echo yes)"
if [[ "$ENABLED" != "yes" ]]; then
  printf '%s' "$INPUT"
  exit 0
fi

# Resolve path (support both absolute and relative)
if [[ "$SCRIPT_PATH" != /* ]]; then
  SCRIPT_PATH="${PROJECT_ROOT}/${SCRIPT_PATH}"
fi

if [[ ! -f "$SCRIPT_PATH" ]]; then
  printf "[Hook] Script not found for %s: %s\n" "$HOOK_ID" "$SCRIPT_PATH" >&2
  printf '%s' "$INPUT"
  exit 0
fi

# Execute the hook script, passing stdin and any extra arguments
printf '%s' "$INPUT" | "$SCRIPT_PATH" "${EXTRA_ARGS[@]}"
