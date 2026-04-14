#!/bin/bash
# sync-template.sh - Sync stock files from project-template
# Version: 2.0.0
#
# Usage:
#   ./scripts/sync-template.sh [command] [options]
#
# Commands:
#   sync              Sync template files (default)
#   adopt             Adopt template into existing project (first-time setup)
#   update            Update to latest template version
#   status            Show sync status and version info
#
# Options:
#   --dry-run         Preview changes without applying
#   --template PATH   Use local template path (default: ~/projects/project-template)
#   --git URL         Use git remote URL instead of local path
#   --rules           Sync .claude/rules/ files (auto-loaded by Claude Code)
#   --commands        Sync .claude/commands/ files
#   --skills          Sync .claude/skills/ files
#   --plugins         Sync plugin system files
#   --hooks           Sync .claude/hooks/ files
#   --scripts         Sync scripts/ (harness-audit, observer, CLI tools)
#   --mcps            Sync MCP management files
#   --all             Sync all template files
#   --force           Overwrite without prompting
#   --check-versions  Show version info for synced files
#   --minimal         Only sync essential files (CLAUDE.md template, core commands)
#
# Note: If no category flags given, defaults to syncing rules only.

set -e

# Configuration
TEMPLATE_PATH="${TEMPLATE_PATH:-$HOME/projects/project-template}"
TEMPLATE_GIT=""
COMMAND="sync"
DRY_RUN=false
SYNC_COMMANDS=false
SYNC_SKILLS=false
SYNC_PLUGINS=false
SYNC_HOOKS=false
SYNC_MCPS=false
SYNC_SCRIPTS=false
MINIMAL=false
FORCE=false
CHECK_VERSIONS=false
TEMP_DIR=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Stock files to sync
# New location: .claude/rules/ (auto-loaded by Claude Code)
STOCK_CLAUDE_RULES=(
    ".claude/rules/claude-behavior.md"
    ".claude/rules/git-workflow.md"
    ".claude/rules/python/coding-standards.md"
    ".claude/rules/reasoning-patterns.md"
    ".claude/rules/workflow-guide.md"
    ".claude/rules/context-management.md"
    ".claude/rules/proactive-steering.md"
)

# Legacy location: docs/rules/ (kept for backward compatibility)
STOCK_DOCS_RULES=(
    "docs/rules/git-workflow.md"
    "docs/rules/python-standards.md"  # legacy location, maps to .claude/rules/python/coding-standards.md
    "docs/rules/self-improve.md"
    "docs/MCP_SETUP.md"
)

# Combined for default sync
STOCK_RULES=(
    "${STOCK_CLAUDE_RULES[@]}"
    "${STOCK_DOCS_RULES[@]}"
)

STOCK_COMMANDS=(
    ".claude/commands/lint.md"
    ".claude/commands/test.md"
    ".claude/commands/tasks.md"
    ".claude/commands/task-status.md"
    ".claude/commands/prd.md"
    ".claude/commands/commit.md"
    ".claude/commands/pr.md"
    ".claude/commands/changelog.md"
    ".claude/commands/generate-tests.md"
    ".claude/commands/security-audit.md"
    ".claude/commands/optimize.md"
    ".claude/commands/settings.md"
    ".claude/commands/setup.md"
    ".claude/commands/health.md"
    ".claude/commands/brainstorm.md"
    ".claude/commands/github-sync.md"
    ".claude/commands/research.md"
)

STOCK_SKILLS=(
    ".claude/skills/code-review/SKILL.md"
    ".claude/skills/debugging/SKILL.md"
    ".claude/skills/git-recovery/SKILL.md"
)

STOCK_PLUGINS=(
    ".claude/plugins/registry.json"
    ".claude/commands/plugins.md"
    "scripts/manage-plugins.sh"
    "docs/PLUGINS.md"
)

STOCK_HOOKS=(
    ".claude/hooks/session-init.sh"
    ".claude/hooks/pre-commit-check.sh"
    ".claude/hooks/post-edit-format.sh"
    ".claude/hooks/protect-sensitive-files.sh"
    ".claude/hooks/session-summary.sh"
    ".claude/hooks/project-index.sh"
    ".claude/hooks/settings-example.json"
    ".claude/hooks/README.md"
    ".claude/settings-presets.json"
    "docs/HOOKS.md"
)

STOCK_MCPS=(
    ".claude/mcp-registry.json"
    ".claude/commands/mcps.md"
    "scripts/manage-mcps.sh"
)

STOCK_SCRIPTS=(
    "scripts/harness-audit.js"
    "scripts/start-observer.sh"
    "scripts/instinct-cli.py"
    "scripts/multi-model-query.py"
    "scripts/setup-preset.sh"
    "scripts/smoke-test.sh"
    "scripts/init-project.sh"
    "scripts/sync-template.sh"
    "scripts/check-upstream.sh"
)

# Minimal set for quick adoption
STOCK_MINIMAL=(
    "CLAUDE.md"
    ".claude/rules/claude-behavior.md"
    ".claude/rules/git-workflow.md"
    ".claude/commands/tasks.md"
    ".claude/commands/commit.md"
    ".claude/commands/setup.md"
)

# Cleanup function
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        sync|adopt|update|status) COMMAND="$1" ;;
        --dry-run) DRY_RUN=true ;;
        --template) TEMPLATE_PATH="$2"; shift ;;
        --git) TEMPLATE_GIT="$2"; shift ;;
        --commands) SYNC_COMMANDS=true ;;
        --skills) SYNC_SKILLS=true ;;
        --plugins) SYNC_PLUGINS=true ;;
        --hooks) SYNC_HOOKS=true ;;
        --mcps) SYNC_MCPS=true ;;
        --scripts) SYNC_SCRIPTS=true ;;
        --rules) SYNC_RULES=true ;;
        --all) SYNC_COMMANDS=true; SYNC_SKILLS=true; SYNC_PLUGINS=true; SYNC_HOOKS=true; SYNC_MCPS=true; SYNC_SCRIPTS=true; SYNC_RULES=true ;;
        --minimal) MINIMAL=true ;;
        --force) FORCE=true ;;
        --check-versions) CHECK_VERSIONS=true ;;
        --help|-h)
            head -28 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *) echo -e "${RED}Unknown parameter: $1${NC}"; exit 1 ;;
    esac
    shift
done

echo -e "${BLUE}Template Sync Tool v2.0.0${NC}"
echo "==========================="
echo -e "Command: ${BOLD}$COMMAND${NC}"

# Check for saved template source if none provided
if [ -z "$TEMPLATE_GIT" ] && [ "$TEMPLATE_PATH" = "$HOME/projects/project-template" ]; then
    if [ -f ".template/source" ]; then
        SAVED_SOURCE=$(cat .template/source)
        if [[ "$SAVED_SOURCE" == http* ]] || [[ "$SAVED_SOURCE" == git@* ]]; then
            TEMPLATE_GIT="$SAVED_SOURCE"
            echo "Using saved template source: $TEMPLATE_GIT"
        elif [ -d "$SAVED_SOURCE" ]; then
            TEMPLATE_PATH="$SAVED_SOURCE"
            echo "Using saved template path: $TEMPLATE_PATH"
        fi
    fi
fi

# If git URL provided, clone to temp directory
if [ -n "$TEMPLATE_GIT" ]; then
    TEMP_DIR=$(mktemp -d)
    echo "Cloning template from: $TEMPLATE_GIT"
    git clone --depth 1 --quiet "$TEMPLATE_GIT" "$TEMP_DIR"
    TEMPLATE_PATH="$TEMP_DIR"
    echo -e "${GREEN}Cloned successfully${NC}"
else
    echo "Template source: $TEMPLATE_PATH"
fi
echo ""

if [ ! -d "$TEMPLATE_PATH" ]; then
    echo -e "${RED}Error: Template directory not found at $TEMPLATE_PATH${NC}"
    echo ""
    echo "Options:"
    echo "  1. Set TEMPLATE_PATH environment variable"
    echo "  2. Use --template /path/to/template"
    echo "  3. Use --git https://github.com/user/project-template.git"
    exit 1
fi

# Build file list based on command and options
build_file_list() {
    FILES_TO_SYNC=()

    if [ "$MINIMAL" = true ]; then
        FILES_TO_SYNC=("${STOCK_MINIMAL[@]}")
        return
    fi

    if [ "$COMMAND" = "adopt" ]; then
        # Adopt mode: Include everything needed for first-time setup
        FILES_TO_SYNC=("${STOCK_RULES[@]}")
        FILES_TO_SYNC+=("${STOCK_COMMANDS[@]}")
        FILES_TO_SYNC+=("${STOCK_HOOKS[@]}")
        FILES_TO_SYNC+=("${STOCK_MCPS[@]}")
        FILES_TO_SYNC+=("CLAUDE.md")
        return
    fi

    # Check if any specific sync flags were given
    ANY_FLAGS=false
    [ "$SYNC_COMMANDS" = true ] && ANY_FLAGS=true
    [ "$SYNC_SKILLS" = true ] && ANY_FLAGS=true
    [ "$SYNC_PLUGINS" = true ] && ANY_FLAGS=true
    [ "$SYNC_HOOKS" = true ] && ANY_FLAGS=true
    [ "$SYNC_MCPS" = true ] && ANY_FLAGS=true
    [ "$SYNC_SCRIPTS" = true ] && ANY_FLAGS=true
    [ "$SYNC_RULES" = true ] && ANY_FLAGS=true

    # If no flags given, default to rules only
    if [ "$ANY_FLAGS" = false ]; then
        FILES_TO_SYNC=("${STOCK_RULES[@]}")
        return
    fi

    # Otherwise, only sync what's explicitly requested
    FILES_TO_SYNC=()

    if [ "$SYNC_RULES" = true ]; then
        FILES_TO_SYNC+=("${STOCK_RULES[@]}")
    fi
    if [ "$SYNC_COMMANDS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_COMMANDS[@]}")
    fi
    if [ "$SYNC_SKILLS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_SKILLS[@]}")
    fi
    if [ "$SYNC_PLUGINS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_PLUGINS[@]}")
    fi
    if [ "$SYNC_HOOKS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_HOOKS[@]}")
    fi
    if [ "$SYNC_SCRIPTS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_SCRIPTS[@]}")
    fi
    if [ "$SYNC_MCPS" = true ]; then
        FILES_TO_SYNC+=("${STOCK_MCPS[@]}")
    fi
}

build_file_list

# Check versions mode
if [ "$CHECK_VERSIONS" = true ]; then
    echo -e "${BLUE}Version Check${NC}"
    echo "-------------"
    for file in "${FILES_TO_SYNC[@]}"; do
        local_file="./$file"
        template_file="$TEMPLATE_PATH/$file"

        local_ver="(not found)"
        template_ver="(not found)"

        if [ -f "$local_file" ]; then
            local_ver=$(grep -oP '(?<=template-version: )[0-9.]+' "$local_file" 2>/dev/null || echo "(no version)")
        fi
        if [ -f "$template_file" ]; then
            template_ver=$(grep -oP '(?<=template-version: )[0-9.]+' "$template_file" 2>/dev/null || echo "(no version)")
        fi

        if [ "$local_ver" = "$template_ver" ]; then
            echo -e "  $file: ${GREEN}$local_ver${NC}"
        else
            echo -e "  $file: ${YELLOW}$local_ver -> $template_ver${NC}"
        fi
    done
    exit 0
fi

# Status command - show sync state
if [ "$COMMAND" = "status" ]; then
    echo ""
    echo -e "${BOLD}Template Status${NC}"
    echo "---------------"

    if [ -f ".template/source" ]; then
        echo -e "Source: $(cat .template/source)"
    else
        echo -e "Source: ${YELLOW}Not tracked (run sync to save)${NC}"
    fi

    if [ -f ".template/version" ]; then
        echo -e "Version: $(cat .template/version)"
    fi

    echo ""
    echo -e "${BOLD}Configuration:${NC}"
    [ -d ".taskmaster" ] && echo -e "  ${GREEN}✓${NC} Taskmaster initialized" || echo -e "  ${RED}✗${NC} Taskmaster not initialized"
    [ -f "CLAUDE.md" ] && ! grep -q "\[PROJECT_NAME\]" CLAUDE.md && echo -e "  ${GREEN}✓${NC} CLAUDE.md customized" || echo -e "  ${YELLOW}!${NC} CLAUDE.md needs customization"
    [ -f ".claude/mcp-project.json" ] && echo -e "  ${GREEN}✓${NC} MCPs configured" || echo -e "  ${YELLOW}!${NC} MCPs not configured"
    [ -f ".claude/settings.local.json" ] && echo -e "  ${GREEN}✓${NC} Hooks enabled" || echo -e "  ${DIM}○${NC} Hooks not enabled (optional)"

    echo ""
    echo "Run './scripts/sync-template.sh --check-versions' to see file versions"
    exit 0
fi

# Ensure directories exist
ensure_directories() {
    mkdir -p docs/rules

    if [ "$SYNC_COMMANDS" = true ] || [ "$COMMAND" = "adopt" ]; then
        mkdir -p .claude/commands
    fi
    if [ "$SYNC_SKILLS" = true ]; then
        mkdir -p .claude/skills/code-review
        mkdir -p .claude/skills/debugging
        mkdir -p .claude/skills/git-recovery
    fi
    if [ "$SYNC_PLUGINS" = true ] || [ "$COMMAND" = "adopt" ]; then
        mkdir -p .claude/plugins
    fi
    if [ "$SYNC_HOOKS" = true ] || [ "$COMMAND" = "adopt" ]; then
        mkdir -p .claude/hooks
    fi
    if [ "$SYNC_SCRIPTS" = true ] || [ "$SYNC_MCPS" = true ] || [ "$COMMAND" = "adopt" ]; then
        mkdir -p scripts
    fi
}

ensure_directories

# Sync files
for file in "${FILES_TO_SYNC[@]}"; do
    template_file="$TEMPLATE_PATH/$file"
    local_file="./$file"

    if [ ! -f "$template_file" ]; then
        echo -e "${YELLOW}Skip: $file (not in template)${NC}"
        continue
    fi

    if [ ! -f "$local_file" ]; then
        echo -e "${GREEN}New: $file${NC}"
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$(dirname "$local_file")"
            cp "$template_file" "$local_file"
            echo "  -> Created"
        fi
        continue
    fi

    # Check if files differ
    if diff -q "$template_file" "$local_file" > /dev/null 2>&1; then
        echo -e "Same: $file"
    else
        echo -e "${YELLOW}Changed: $file${NC}"
        if [ "$DRY_RUN" = true ]; then
            echo "  Diff preview:"
            diff --color=always "$local_file" "$template_file" 2>/dev/null | head -15 || true
        elif [ "$FORCE" = true ]; then
            cp "$template_file" "$local_file"
            echo -e "  ${GREEN}Updated (forced)${NC}"
        else
            echo "  Local file differs from template."
            read -p "  Overwrite with template version? [y/N/d(iff)] " -n 1 -r
            echo
            case $REPLY in
                y|Y)
                    cp "$template_file" "$local_file"
                    echo -e "  ${GREEN}Updated${NC}"
                    ;;
                d|D)
                    diff --color=always "$local_file" "$template_file" || true
                    read -p "  Overwrite? [y/N] " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        cp "$template_file" "$local_file"
                        echo -e "  ${GREEN}Updated${NC}"
                    else
                        echo "  Skipped"
                    fi
                    ;;
                *)
                    echo "  Skipped"
                    ;;
            esac
        fi
    fi
done

# Full directory sync for adopt mode
# Copies ALL files from template .claude/ subdirectories (not just curated lists)
sync_full_directories() {
    local template="$1"
    local subdirs=("rules" "commands" "skills" "agents" "contexts" "hooks")

    echo ""
    echo -e "${BOLD}Syncing full .claude/ directories...${NC}"

    for subdir in "${subdirs[@]}"; do
        local source_dir="$template/.claude/$subdir"
        local dest_dir=".claude/$subdir"

        if [ ! -d "$source_dir" ]; then
            echo -e "  ${YELLOW}Skip:${NC} .claude/$subdir/ (not in template)"
            continue
        fi

        mkdir -p "$dest_dir"
        local new_count=0
        local updated_count=0
        local same_count=0

        while IFS= read -r -d '' file; do
            local rel="${file#$source_dir/}"
            local dest="$dest_dir/$rel"
            mkdir -p "$(dirname "$dest")"

            if [ ! -f "$dest" ]; then
                new_count=$((new_count + 1))
                if [ "$DRY_RUN" = false ]; then
                    cp "$file" "$dest"
                fi
            elif ! diff -q "$file" "$dest" > /dev/null 2>&1; then
                updated_count=$((updated_count + 1))
                if [ "$DRY_RUN" = false ] && [ "$FORCE" = true ]; then
                    cp "$file" "$dest"
                fi
            else
                same_count=$((same_count + 1))
            fi
        done < <(find "$source_dir" -type f -print0)

        local total=$((new_count + updated_count + same_count))
        if [ "$DRY_RUN" = true ]; then
            echo -e "  ${BLUE}Preview:${NC} .claude/$subdir/ — $total files ($new_count new, $updated_count changed, $same_count same)"
        else
            echo -e "  ${GREEN}Synced:${NC} .claude/$subdir/ — $total files ($new_count new, $updated_count updated, $same_count unchanged)"
        fi
    done
}

# Run full directory sync for adopt mode (after individual file sync)
if [ "$COMMAND" = "adopt" ]; then
    sync_full_directories "$TEMPLATE_PATH"
fi

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "Dry run complete. No files were modified."
    echo "Run without --dry-run to apply changes."
else
    # Record template source for future syncs
    mkdir -p .template
    if [ -n "$TEMPLATE_GIT" ]; then
        echo "$TEMPLATE_GIT" > .template/source
    else
        echo "$TEMPLATE_PATH" > .template/source
    fi

    # Record template version if available
    if [ -f "$TEMPLATE_PATH/.template-version" ]; then
        cp "$TEMPLATE_PATH/.template-version" .template/version
    fi

    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    chmod +x .claude/hooks/*.sh 2>/dev/null || true

    echo -e "${GREEN}Sync complete.${NC}"
    echo "Template source saved to .template/source"

    # Command-specific next steps
    if [ "$COMMAND" = "adopt" ]; then
        echo ""
        echo -e "${BOLD}Next steps to complete adoption:${NC}"
        echo ""
        echo "  1. Customize CLAUDE.md with your project details"
        echo "     - Replace [PROJECT_NAME] with your project name"
        echo "     - Fill in tech stack and patterns"
        echo ""
        echo "  2. Initialize Taskmaster:"
        echo "     task-master init"
        echo ""
        echo "  3. Enable hooks (optional but recommended):"
        echo "     cp .claude/hooks/settings-example.json .claude/settings.local.json"
        echo ""
        echo "  4. Configure MCPs for your project:"
        echo "     /mcps"
        echo ""
        echo "  5. Start Claude Code and run /setup for guided configuration"
        echo ""
        echo -e "  ${YELLOW}NOTE: If Claude Code is already running, restart it.${NC}"
        echo "     Hooks, rules, and CLAUDE.md only load at session startup."
    fi
fi
