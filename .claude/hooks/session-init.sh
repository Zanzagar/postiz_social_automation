#!/bin/bash
# session-init.sh - Comprehensive project initialization and health check
# Hook type: SessionStart
# Triggers when: A new Claude Code session begins
#
# This hook:
# 1. Detects project state (new, adopting, existing)
# 2. Checks for critical setup gaps
# 3. Loads relevant context for the session
# 4. Provides actionable next steps

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STATE_FILE="$PROJECT_DIR/.claude/project-state.json"
MCP_CONFIG="$PROJECT_DIR/.claude/mcp-project.json"
REGISTRY="$PROJECT_DIR/.claude/mcp-registry.json"
CLAUDE_MD="$PROJECT_DIR/CLAUDE.md"
TASKMASTER_DIR="$PROJECT_DIR/.taskmaster"
TEMPLATE_VERSION_FILE="$PROJECT_DIR/.template/version"
TEMPLATE_SOURCE_FILE="$PROJECT_DIR/.template/source"
SYNC_SCRIPT="$PROJECT_DIR/scripts/sync-template.sh"

# Current template version (update when releasing new versions)
CURRENT_TEMPLATE_VERSION="2.0.0"

# Only run for projects using this template
# Check for registry OR template tracking OR resembling structure
HAS_REGISTRY=false
HAS_TEMPLATE_TRACKING=false
HAS_TEMPLATE_STRUCTURE=false

[ -f "$REGISTRY" ] && HAS_REGISTRY=true
[ -f "$TEMPLATE_SOURCE_FILE" ] && HAS_TEMPLATE_TRACKING=true

# Check for template-like structure (proto-template detection)
if [ -f "$CLAUDE_MD" ] && [ -d "$PROJECT_DIR/.claude" ]; then
    # Has CLAUDE.md and .claude/ directory - likely template-based
    if [ -d "$PROJECT_DIR/.claude/commands" ] || [ -d "$PROJECT_DIR/.claude/hooks" ]; then
        HAS_TEMPLATE_STRUCTURE=true
    fi
fi

# Exit if this doesn't look like a template project at all
if [ "$HAS_REGISTRY" = false ] && [ "$HAS_TEMPLATE_TRACKING" = false ] && [ "$HAS_TEMPLATE_STRUCTURE" = false ]; then
    exit 0
fi

# Collect project state
HAS_STATE_FILE=false
HAS_MCP_CONFIG=false
HAS_TASKMASTER=false
HAS_CUSTOMIZED_CLAUDE_MD=false
HAS_SRC=false
HAS_UNCOMMITTED=false
HAS_SYNC_SCRIPT=false
HAS_SUPERPOWERS=false
CURRENT_BRANCH=""
CURRENT_TASK=""
INSTALLED_VERSION=""
MISSING_COMPONENTS=()
SESSIONS_DIR="$PROJECT_DIR/.claude/sessions"
SESSION_AGE_HOURS=24
LAST_SESSION=""
LAST_SESSION_AGE=""

[ -f "$STATE_FILE" ] && HAS_STATE_FILE=true
ACTIVE_PRESET=""
if [ "$HAS_STATE_FILE" = true ] && command -v jq &> /dev/null; then
    ACTIVE_PRESET=$(jq -r '.preset // empty' "$STATE_FILE" 2>/dev/null)
fi
[ -f "$MCP_CONFIG" ] && HAS_MCP_CONFIG=true
[ -d "$TASKMASTER_DIR" ] && HAS_TASKMASTER=true
[ -d "$PROJECT_DIR/src" ] && HAS_SRC=true
[ -f "$SYNC_SCRIPT" ] && HAS_SYNC_SCRIPT=true

# Check for Superpowers plugin (marker file or common locations)
# Users can create .superpowers-installed to confirm installation
if [ -f "$PROJECT_DIR/.superpowers-installed" ] || \
   [ -d "$HOME/.claude/plugins/superpowers" ] || \
   [ -f "$PROJECT_DIR/.claude/superpowers.json" ]; then
    HAS_SUPERPOWERS=true
fi

# Get installed template version
if [ -f "$TEMPLATE_VERSION_FILE" ]; then
    INSTALLED_VERSION=$(cat "$TEMPLATE_VERSION_FILE" 2>/dev/null | tr -d '[:space:]')
fi

# Check for missing template components
[ ! -f "$REGISTRY" ] && MISSING_COMPONENTS+=("mcp-registry.json")
[ ! -d "$PROJECT_DIR/.claude/hooks" ] && MISSING_COMPONENTS+=("hooks/")
[ ! -d "$PROJECT_DIR/.claude/commands" ] && MISSING_COMPONENTS+=("commands/")
[ ! -d "$PROJECT_DIR/.claude/rules" ] && MISSING_COMPONENTS+=("rules/")
[ ! -f "$SYNC_SCRIPT" ] && MISSING_COMPONENTS+=("sync-template.sh")

# Check for LOCALLY available commands/skills (parent inheritance doesn't register these)
# Claude Code only registers commands/skills from LOCAL .claude/ directories (or symlinks).
# Parent-directory traversal works for rules and CLAUDE.md, but NOT commands/skills.
HAS_LOCAL_COMMANDS=false
HAS_LOCAL_SKILLS=false
if [ -d "$PROJECT_DIR/.claude/commands" ] || [ -L "$PROJECT_DIR/.claude/commands" ]; then
    HAS_LOCAL_COMMANDS=true
fi
if [ -d "$PROJECT_DIR/.claude/skills" ] || [ -L "$PROJECT_DIR/.claude/skills" ]; then
    HAS_LOCAL_SKILLS=true
fi

# Check if CLAUDE.md has been customized (not still placeholder)
if [ -f "$CLAUDE_MD" ]; then
    if ! grep -q "\[PROJECT_NAME\]" "$CLAUDE_MD" 2>/dev/null; then
        HAS_CUSTOMIZED_CLAUDE_MD=true
    fi
fi

# Git status
if [ -d "$PROJECT_DIR/.git" ]; then
    CURRENT_BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo "")
    UNCOMMITTED=$(cd "$PROJECT_DIR" && git status --porcelain 2>/dev/null | head -5)
    [ -n "$UNCOMMITTED" ] && HAS_UNCOMMITTED=true
fi

# Get current Taskmaster task if available
if [ "$HAS_TASKMASTER" = true ] && command -v task-master &> /dev/null; then
    CURRENT_TASK=$(cd "$PROJECT_DIR" && task-master next 2>/dev/null | head -3 || echo "")
    TASK_COUNT=$(cd "$PROJECT_DIR" && task-master list 2>/dev/null | grep -c "^[0-9]" || echo "0")
    IN_PROGRESS_COUNT=$(cd "$PROJECT_DIR" && task-master list --status in-progress 2>/dev/null | grep -c "^[0-9]" || echo "0")
    DONE_COUNT=$(cd "$PROJECT_DIR" && task-master list --status done 2>/dev/null | grep -c "^[0-9]" || echo "0")
fi

# Session continuity - find most recent session summary
if [ -d "$SESSIONS_DIR" ]; then
    LAST_SESSION=$(ls -t "$SESSIONS_DIR"/session_*.md 2>/dev/null | head -1)
    if [ -n "$LAST_SESSION" ]; then
        # Cross-platform file age: GNU stat (-c) with BSD fallback (-f)
        SESSION_TIME=$(stat -c %Y "$LAST_SESSION" 2>/dev/null || stat -f %m "$LAST_SESSION" 2>/dev/null || echo "0")
        CURRENT_TIME=$(date +%s)
        if [ "$SESSION_TIME" -gt 0 ] 2>/dev/null; then
            LAST_SESSION_AGE=$(( (CURRENT_TIME - SESSION_TIME) / 3600 ))
        fi
    fi
fi

# Detect project phase based on signals
PROJECT_PHASE="ideation"
HAS_PRD=false
HAS_TASKS=false
HAS_ACTIVE_TASK=false

[ -f "$PROJECT_DIR/.taskmaster/docs/prd.txt" ] || [ -f "$PROJECT_DIR/.prd/prd.txt" ] && HAS_PRD=true
[ "$TASK_COUNT" -gt 0 ] 2>/dev/null && HAS_TASKS=true
[ "$IN_PROGRESS_COUNT" -gt 0 ] 2>/dev/null && HAS_ACTIVE_TASK=true

# Phase detection logic
if [ "$HAS_ACTIVE_TASK" = true ]; then
    PROJECT_PHASE="building"
elif [ "$HAS_TASKS" = true ] && [ "$HAS_ACTIVE_TASK" = false ]; then
    # Has tasks but none in progress - could be planning or review
    if [ "$DONE_COUNT" -gt 0 ] 2>/dev/null && [ "$TASK_COUNT" -eq "$DONE_COUNT" ] 2>/dev/null; then
        PROJECT_PHASE="shipping"
    else
        PROJECT_PHASE="planning"
    fi
elif [ "$HAS_PRD" = true ]; then
    PROJECT_PHASE="planning"
else
    PROJECT_PHASE="ideation"
fi

# Determine project scenario
# Priority: upgrade > proto > adopting > new > existing
SCENARIO="existing"

# Check for version mismatch (needs upgrade)
NEEDS_UPGRADE=false
if [ -n "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" != "$CURRENT_TEMPLATE_VERSION" ]; then
    NEEDS_UPGRADE=true
fi

# Check for missing components (partial installation)
HAS_MISSING_COMPONENTS=false
if [ ${#MISSING_COMPONENTS[@]} -gt 0 ]; then
    HAS_MISSING_COMPONENTS=true
fi

# Scenario logic
# Priority: upgrade (if has tracking) > proto > adopting > new > existing

# First: Check for upgrade (has template tracking but outdated/incomplete)
if [ "$HAS_TEMPLATE_TRACKING" = true ] && { [ "$NEEDS_UPGRADE" = true ] || [ "$HAS_MISSING_COMPONENTS" = true ]; }; then
    SCENARIO="upgrade"
# Second: No state file - determine if new, adopting, or proto
elif [ "$HAS_STATE_FILE" = false ]; then
    if [ "$HAS_TEMPLATE_STRUCTURE" = true ] && [ "$HAS_TEMPLATE_TRACKING" = false ]; then
        # Has template-like structure but wasn't synced - proto-template
        SCENARIO="proto"
    elif [ "$HAS_SRC" = false ] && [ "$HAS_TASKMASTER" = false ]; then
        SCENARIO="new"
    else
        SCENARIO="adopting"
    fi
fi
# Default: existing (has state file and is current)

# Build output based on scenario
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  Project Status                                             │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

# Critical issues first
CRITICAL_ISSUES=()
SETUP_NEEDED=()
RECOMMENDATIONS=()

# Check Taskmaster
if [ "$HAS_TASKMASTER" = false ]; then
    CRITICAL_ISSUES+=("Taskmaster not initialized")
    SETUP_NEEDED+=("Run: task-master init")
fi

# Check Superpowers (required for TDD enforcement)
if [ "$HAS_SUPERPOWERS" = false ]; then
    CRITICAL_ISSUES+=("Superpowers plugin not detected")
    SETUP_NEEDED+=("Install: /plugin marketplace add obra/superpowers-marketplace")
    SETUP_NEEDED+=("Then: /plugin install superpowers@superpowers-marketplace")
    SETUP_NEEDED+=("Create .superpowers-installed after installation to dismiss this warning")
fi

# Check for locally registered commands/skills
if [ "$HAS_LOCAL_COMMANDS" = false ] || [ "$HAS_LOCAL_SKILLS" = false ]; then
    CRITICAL_ISSUES+=("Slash commands not registered (needs local .claude/commands/ and .claude/skills/)")
    SETUP_NEEDED+=("Run: ./scripts/init-project.sh (creates symlinks or copies from template)")
    SETUP_NEEDED+=("Or run: /setup (guided wizard)")
fi

# Check CLAUDE.md customization
if [ "$HAS_CUSTOMIZED_CLAUDE_MD" = false ]; then
    SETUP_NEEDED+=("Customize CLAUDE.md with project details")
fi

# Check MCP configuration
if [ "$HAS_MCP_CONFIG" = false ]; then
    RECOMMENDATIONS+=("Configure MCPs for your project type: /mcps")
fi

# Check git branch (should not be on main for active development)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    RECOMMENDATIONS+=("Create a feature branch before making changes")
fi

# Output scenario-specific guidance
case $SCENARIO in
    new)
        echo "📦 NEW PROJECT DETECTED"
        echo ""
        echo "This appears to be a fresh project. Recommended setup:"
        echo ""
        echo "  1. Update CLAUDE.md with your project name and details"
        echo "  2. Initialize Taskmaster: task-master init"
        echo "  3. Create a PRD in .taskmaster/docs/prd.txt"
        echo "  4. Generate tasks: task-master parse-prd"
        echo "  5. Configure MCPs: /mcps"
        echo ""
        ;;
    proto)
        echo "🔍 PROTO-TEMPLATE DETECTED"
        echo ""
        echo "This project has template-like structure but wasn't officially synced."
        echo "This could be an older template version or manual setup."
        echo ""
        echo "To fully integrate the latest template:"
        echo ""
        if [ "$HAS_SYNC_SCRIPT" = true ]; then
            echo "  ./scripts/sync-template.sh adopt"
        else
            echo "  1. Get sync script: curl -O https://raw.githubusercontent.com/[your-org]/project-template/main/scripts/sync-template.sh"
            echo "  2. Run: ./scripts/sync-template.sh adopt --git [template-url]"
        fi
        echo ""
        echo "Missing components: ${MISSING_COMPONENTS[*]:-none detected}"
        echo ""
        ;;
    upgrade)
        echo "⬆️  TEMPLATE UPDATE AVAILABLE"
        echo ""
        if [ -n "$INSTALLED_VERSION" ]; then
            echo "Installed: v$INSTALLED_VERSION → Latest: v$CURRENT_TEMPLATE_VERSION"
        fi
        if [ "$HAS_MISSING_COMPONENTS" = true ]; then
            echo "Missing components: ${MISSING_COMPONENTS[*]}"
            echo ""
            echo "To get all new features:"
            echo "  ./scripts/sync-template.sh sync --all"
            echo ""
            echo "Or selectively add:"
            echo "  ./scripts/sync-template.sh sync --rules    # Add .claude/rules/ (auto-loaded)"
            echo "  ./scripts/sync-template.sh sync --hooks    # Add automation hooks"
            echo "  ./scripts/sync-template.sh sync --commands # Add new slash commands"
        else
            echo ""
            echo "To update:"
            echo "  ./scripts/sync-template.sh update"
        fi
        echo ""
        echo "Preview changes first:"
        echo "  ./scripts/sync-template.sh sync --all --dry-run"
        echo ""
        ;;
    adopting)
        echo "🔄 EXISTING PROJECT - TEMPLATE INTEGRATION"
        echo ""
        echo "Integrating template into existing project. Setup needed:"
        echo ""
        if [ "$HAS_TASKMASTER" = false ]; then
            echo "  • Initialize Taskmaster: task-master init"
        fi
        if [ "$HAS_CUSTOMIZED_CLAUDE_MD" = false ]; then
            echo "  • Update CLAUDE.md with your project details"
        fi
        if [ "$HAS_MCP_CONFIG" = false ]; then
            echo "  • Configure MCPs for project type: /mcps"
        fi
        echo ""
        echo "Your existing code will not be modified."
        echo ""
        ;;
    existing)
        # Show project phase
        case $PROJECT_PHASE in
            ideation)
                echo "💭 PHASE: Ideation"
                echo "   Ready to explore ideas and gather requirements."
                echo ""
                echo "   Suggested: /brainstorm <idea> | /research <topic>"
                ;;
            planning)
                echo "📝 PHASE: Planning"
                echo "   Tasks: $TASK_COUNT total | $DONE_COUNT done"
                echo ""
                if [ "$HAS_PRD" = true ] && [ "$HAS_TASKS" = false ]; then
                    echo "   Next: task-master parse-prd to generate tasks"
                else
                    echo "   Suggested: task-master next | task-master expand"
                fi
                ;;
            building)
                echo "🔨 PHASE: Building"
                echo "   Tasks: $IN_PROGRESS_COUNT in progress | $DONE_COUNT done"
                echo ""
                if [ -n "$CURRENT_TASK" ]; then
                    echo "📋 Current Task:"
                    echo "$CURRENT_TASK"
                fi
                echo ""
                echo "   Suggested: /test | /lint | /commit"
                ;;
            shipping)
                echo "🚀 PHASE: Shipping"
                echo "   All $TASK_COUNT tasks complete!"
                echo ""
                echo "   Suggested: /pr | /changelog | /github-sync"
                ;;
        esac
        echo ""

        if [ "$HAS_UNCOMMITTED" = true ]; then
            echo "⚠️  Uncommitted changes detected:"
            echo "$UNCOMMITTED"
            echo ""
        fi

        if [ -n "$CURRENT_BRANCH" ]; then
            echo "🌿 Branch: $CURRENT_BRANCH"
        fi

        if [ -n "$ACTIVE_PRESET" ]; then
            echo "📦 Preset: $ACTIVE_PRESET"
        fi

        if [ -n "$CURRENT_BRANCH" ] || [ -n "$ACTIVE_PRESET" ]; then
            echo ""
        fi

        # Session continuity: show last session if recent
        if [ -n "$LAST_SESSION" ] && [ -n "$LAST_SESSION_AGE" ] && [ "$LAST_SESSION_AGE" -lt "$SESSION_AGE_HOURS" ] 2>/dev/null; then
            echo "📋 Last Session (${LAST_SESSION_AGE}h ago):"
            # Extract key sections concisely
            MODIFIED=$(grep -A5 "## Files Modified" "$LAST_SESSION" 2>/dev/null | tail -n +2 | head -5 | sed 's/^/   /')
            TASKS=$(grep -A5 "## Task Progress" "$LAST_SESSION" 2>/dev/null | tail -n +2 | head -3 | sed 's/^/   /')
            [ -n "$MODIFIED" ] && echo "$MODIFIED"
            [ -n "$TASKS" ] && echo "$TASKS"
            echo ""
        fi

        # Pre-compact state detection
        PRE_COMPACT_FILE="$SESSIONS_DIR/pre-compact-state.md"
        if [ -f "$PRE_COMPACT_FILE" ]; then
            echo "⚠️  Pre-compaction state saved. Review: $PRE_COMPACT_FILE"
            echo ""
        fi
        ;;
esac

# Show critical issues if any
if [ ${#CRITICAL_ISSUES[@]} -gt 0 ]; then
    echo "❌ CRITICAL:"
    for issue in "${CRITICAL_ISSUES[@]}"; do
        echo "   • $issue"
    done
    echo ""
fi

# Show setup items if any (for new/adopting/proto)
if [ ${#SETUP_NEEDED[@]} -gt 0 ] && [ "$SCENARIO" != "existing" ] && [ "$SCENARIO" != "upgrade" ]; then
    echo "📝 Setup needed:"
    for item in "${SETUP_NEEDED[@]}"; do
        echo "   • $item"
    done
    echo ""
fi

# Show recommendations if any
if [ ${#RECOMMENDATIONS[@]} -gt 0 ]; then
    echo "💡 Recommendations:"
    for rec in "${RECOMMENDATIONS[@]}"; do
        echo "   • $rec"
    done
    echo ""
fi

# Quick commands reminder
case $SCENARIO in
    existing)
        echo "Quick commands: /tasks | /commit | /test | /lint"
        ;;
    upgrade)
        echo "Quick commands: /health | ./scripts/sync-template.sh status"
        ;;
esac

exit 0
