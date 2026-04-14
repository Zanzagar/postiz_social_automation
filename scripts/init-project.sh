#!/bin/bash
# init-project.sh - Initialize local .claude/ structure for command/skill registration
# Version: 1.0.0
#
# Usage:
#   ./scripts/init-project.sh [options]
#
# Options:
#   --mode symlink|copy   Override auto-detection (default: auto)
#   --template PATH       Template source path (default: auto-detect or ~/projects/project-template)
#   --dry-run             Preview changes without applying
#   --force               Recreate even if dirs already exist
#   --help                Show this help
#
# Auto-detection:
#   - If a parent directory contains .claude/commands/ with >10 files, uses symlinks
#   - Otherwise, copies from --template path
#
# What it creates:
#   .claude/commands/   - Slash commands (/health, /commit, etc.)
#   .claude/skills/     - Skills (/code-review, /debugging, etc.)
#   .claude/agents/     - Sub-agent definitions (planner, code-reviewer, etc.)
#   .claude/contexts/   - Context modes (dev, review, research)
#   .claude/hooks/      - Automation hooks (session-init, pre-commit, etc.)
#   .claude/settings.json - Hook definitions (without this, zero hooks fire)
#   .taskmaster/        - Task Master directories + tuned config.json
#   .template/          - Version tracking for template updates
#
# What it does NOT touch:
#   instincts/  - User-specific learned patterns
#   sessions/   - Runtime session data
#   plugins/    - User-installed plugins
#
# Note on rules/:
#   Rules inherit from parent directories in Claude Code, so nested projects
#   don't need local copies. However, standalone projects (copy mode) DO need
#   rules copied locally since there's no parent to inherit from.

set -e

# --- Constants ---

# Directories to initialize (order doesn't matter)
# rules/ is included because standalone projects need them (no parent inheritance)
TARGET_DIRS=("rules" "commands" "skills-available" "agents" "contexts" "hooks")

# Minimum command count to identify a directory as a template
MIN_TEMPLATE_COMMANDS=10

# Minimum number of TARGET_DIRS subdirectories that must exist to qualify as a template
# Prevents false positives from partial .claude/ setups (e.g., projects with only commands/)
MIN_TEMPLATE_SUBDIRS=4

# Max parent levels to walk when auto-detecting
MAX_PARENT_DEPTH=5

# Default template path detection:
# 1. $TEMPLATE_PATH env var (explicit override)
# 2. $CLAUDE_PROJECT_DIR (set by Claude Code when running from template)
# 3. Script's own location (if init-project.sh lives in template/scripts/)
# 4. Hardcoded fallback
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PARENT="$(dirname "$SCRIPT_DIR")"

if [ -n "${TEMPLATE_PATH:-}" ]; then
    DEFAULT_TEMPLATE_PATH="$TEMPLATE_PATH"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "${CLAUDE_PROJECT_DIR}/.claude/commands" ]; then
    DEFAULT_TEMPLATE_PATH="$CLAUDE_PROJECT_DIR"
elif [ -d "$SCRIPT_PARENT/.claude/commands" ]; then
    # Script is in template/scripts/, so parent is the template root
    DEFAULT_TEMPLATE_PATH="$SCRIPT_PARENT"
else
    DEFAULT_TEMPLATE_PATH="$HOME/projects/project-template"
fi

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# --- State ---
MODE="auto"          # auto | symlink | copy
TEMPLATE_PATH="${TEMPLATE_PATH:-$DEFAULT_TEMPLATE_PATH}"
TEMPLATE_DETECTED=""  # Set by auto-detection
FORCE=false
DRY_RUN=false
PROJECT_DIR="$PWD"

# Counters for summary
CREATED=0
SKIPPED=0
WARNED=0

# --- Helper Functions ---

show_usage() {
    head -30 "$0" | tail -n +2 | sed 's/^# \?//'
}

log_info() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARNED=$((WARNED + 1))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_skip() {
    echo -e "${DIM}[SKIP]${NC} $1"
    SKIPPED=$((SKIPPED + 1))
}

log_create() {
    echo -e "${GREEN}[CREATE]${NC} $1"
    CREATED=$((CREATED + 1))
}

log_dry() {
    echo -e "${BLUE}[DRY-RUN]${NC} $1"
}

# --- Auto-Detection ---

# Check if a directory qualifies as a full template
# Requires both sufficient commands AND sufficient subdirectory coverage
is_valid_template() {
    local dir="$1"

    # Check 1: Must have enough commands
    if [ ! -d "$dir/.claude/commands" ]; then
        return 1
    fi
    local cmd_count
    cmd_count=$(find "$dir/.claude/commands" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
    if [ "$cmd_count" -le "$MIN_TEMPLATE_COMMANDS" ]; then
        return 1
    fi

    # Check 2: Must have enough of the target subdirectories present
    # This prevents false positives from partial .claude/ setups (e.g., a parent
    # project that has commands/ and skills/ but is missing agents/, hooks/, rules/)
    local subdir_count=0
    for subdir in "${TARGET_DIRS[@]}"; do
        if [ -d "$dir/.claude/$subdir" ]; then
            subdir_count=$((subdir_count + 1))
        fi
    done
    if [ "$subdir_count" -lt "$MIN_TEMPLATE_SUBDIRS" ]; then
        return 1
    fi

    return 0
}

# Walk parent directories looking for a valid template
find_template_parent() {
    local dir="$PROJECT_DIR"
    local depth=0

    while [ "$depth" -lt "$MAX_PARENT_DEPTH" ] && [ "$dir" != "/" ]; do
        dir="$(dirname "$dir")"
        depth=$((depth + 1))

        if is_valid_template "$dir"; then
            echo "$dir"
            return 0
        fi
    done
    return 1
}

# Determine mode and template path
auto_detect() {
    if [ "$MODE" != "auto" ]; then
        # Mode explicitly set, validate template path
        if [ ! -d "$TEMPLATE_PATH/.claude" ]; then
            log_error "Template not found at: $TEMPLATE_PATH"
            log_error "Use --template PATH to specify the template location"
            exit 1
        fi
        return
    fi

    # Try to find a template parent
    local parent
    if parent=$(find_template_parent); then
        MODE="symlink"
        TEMPLATE_DETECTED="$parent"
        TEMPLATE_PATH="$parent"
    elif [ -d "$TEMPLATE_PATH/.claude" ]; then
        MODE="copy"
    else
        log_error "Could not auto-detect template parent directory"
        log_error "And default template path not found: $TEMPLATE_PATH"
        echo ""
        echo "Options:"
        echo "  1. Run from within a project nested under the template directory"
        echo "  2. Set TEMPLATE_PATH environment variable"
        echo "  3. Use --template /path/to/project-template"
        exit 1
    fi
}

# --- Symlink Creation ---

# Calculate relative path from source to target
calc_relative_path() {
    python3 -c "import os.path; print(os.path.relpath('$1', '$2'))"
}

# Create symlinks from project .claude/ to template .claude/
create_symlinks() {
    local template_dir="$1"

    for subdir in "${TARGET_DIRS[@]}"; do
        local target="$template_dir/.claude/$subdir"
        local link="$PROJECT_DIR/.claude/$subdir"

        if [ ! -d "$target" ]; then
            log_skip "$subdir/ (not in template)"
            continue
        fi

        if [ -L "$link" ]; then
            if [ "$FORCE" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    log_dry "Would recreate symlink: $subdir/"
                else
                    rm "$link"
                    local rel_path
                    rel_path=$(calc_relative_path "$target" "$PROJECT_DIR/.claude")
                    ln -s "$rel_path" "$link"
                    log_create "$subdir/ -> $rel_path (recreated)"
                fi
            else
                log_skip "$subdir/ (symlink exists -> $(readlink "$link"))"
            fi
            continue
        fi

        if [ -d "$link" ]; then
            if [ "$FORCE" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    log_dry "Would replace directory with symlink: $subdir/"
                else
                    rm -rf "$link"
                    local rel_path
                    rel_path=$(calc_relative_path "$target" "$PROJECT_DIR/.claude")
                    ln -s "$rel_path" "$link"
                    log_create "$subdir/ -> $rel_path (replaced directory)"
                fi
            else
                log_warn "$subdir/ exists as directory (may shadow template — use --force to replace with symlink)"
            fi
            continue
        fi

        # Create new symlink
        if [ "$DRY_RUN" = true ]; then
            local rel_path
            rel_path=$(calc_relative_path "$target" "$PROJECT_DIR/.claude")
            log_dry "Would create symlink: $subdir/ -> $rel_path"
        else
            local rel_path
            rel_path=$(calc_relative_path "$target" "$PROJECT_DIR/.claude")
            ln -s "$rel_path" "$link"
            log_create "$subdir/ -> $rel_path"
        fi
    done
}

# --- Copy Mode ---

# Copy directories from template to project
copy_dirs() {
    local template_dir="$1"

    for subdir in "${TARGET_DIRS[@]}"; do
        local source="$template_dir/.claude/$subdir"
        local dest="$PROJECT_DIR/.claude/$subdir"

        if [ ! -d "$source" ]; then
            log_skip "$subdir/ (not in template)"
            continue
        fi

        if [ -L "$dest" ]; then
            if [ "$FORCE" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    log_dry "Would replace symlink with copy: $subdir/"
                else
                    rm "$dest"
                    cp -r "$source" "$dest"
                    local count
                    count=$(find "$dest" -type f | wc -l)
                    log_create "$subdir/ ($count files copied, replaced symlink)"
                fi
            else
                log_skip "$subdir/ (symlink exists -> $(readlink "$dest"))"
            fi
            continue
        fi

        if [ -d "$dest" ]; then
            if [ "$FORCE" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    log_dry "Would replace directory: $subdir/"
                else
                    rm -rf "$dest"
                    cp -r "$source" "$dest"
                    local count
                    count=$(find "$dest" -type f | wc -l)
                    log_create "$subdir/ ($count files copied, replaced existing)"
                fi
            else
                log_skip "$subdir/ (directory exists — use --force to replace)"
            fi
            continue
        fi

        # Copy new
        if [ "$DRY_RUN" = true ]; then
            local count
            count=$(find "$source" -type f | wc -l)
            log_dry "Would copy: $subdir/ ($count files)"
        else
            cp -r "$source" "$dest"
            local count
            count=$(find "$dest" -type f | wc -l)
            log_create "$subdir/ ($count files copied)"
        fi
    done
}

# --- Security Checks ---

# Verify symlink targets don't escape the template tree
verify_symlink_safety() {
    local template_dir="$1"
    local template_real
    template_real=$(realpath "$template_dir")

    for subdir in "${TARGET_DIRS[@]}"; do
        local link="$PROJECT_DIR/.claude/$subdir"
        if [ -L "$link" ]; then
            local target_real
            target_real=$(realpath "$link" 2>/dev/null || echo "BROKEN")
            if [ "$target_real" = "BROKEN" ]; then
                log_warn "$subdir/ symlink is broken"
            elif [[ "$target_real" != "$template_real"* ]]; then
                log_warn "$subdir/ symlink points outside template tree: $target_real"
            fi
        fi
    done
}

# --- Main ---

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --template) TEMPLATE_PATH="$2"; shift ;;
        --mode)
            if [[ "$2" != "symlink" && "$2" != "copy" ]]; then
                log_error "Invalid mode: $2 (must be 'symlink' or 'copy')"
                exit 1
            fi
            MODE="$2"; shift
            ;;
        --force) FORCE=true ;;
        --dry-run) DRY_RUN=true ;;
        --help|-h) show_usage; exit 0 ;;
        *) log_error "Unknown parameter: $1"; show_usage; exit 1 ;;
    esac
    shift
done

# Header
echo -e "${BLUE}${BOLD}init-project.sh v1.0.0${NC}"
echo "========================"
echo ""

# Auto-detect mode and template
auto_detect

echo -e "Mode:     ${BOLD}$MODE${NC}"
echo -e "Template: ${BOLD}$TEMPLATE_PATH${NC}"
echo -e "Project:  ${BOLD}$PROJECT_DIR${NC}"
if [ -n "$TEMPLATE_DETECTED" ]; then
    echo -e "Detected: ${GREEN}Parent template found at $TEMPLATE_DETECTED${NC}"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "          ${YELLOW}(dry-run — no changes will be made)${NC}"
fi
if [ "$FORCE" = true ]; then
    echo -e "          ${YELLOW}(force — existing dirs will be replaced)${NC}"
fi
echo ""

# Ensure .claude/ exists
if [ ! -d "$PROJECT_DIR/.claude" ]; then
    if [ "$DRY_RUN" = true ]; then
        log_dry "Would create .claude/ directory"
    else
        mkdir -p "$PROJECT_DIR/.claude"
        log_info "Created .claude/ directory"
    fi
fi

# Execute based on mode
case $MODE in
    symlink)
        echo -e "${BOLD}Creating symlinks to template...${NC}"
        echo ""
        create_symlinks "$TEMPLATE_PATH"
        ;;
    copy)
        echo -e "${BOLD}Copying from template...${NC}"
        echo ""
        copy_dirs "$TEMPLATE_PATH"
        ;;
esac

# Copy root-level .claude/settings.json (hook definitions)
# This file lives at .claude/settings.json, NOT inside any of the TARGET_DIRS
# subdirectories, so the directory copy/symlink logic above misses it.
# Without settings.json, zero hooks fire on session start.
SETTINGS_SRC="$TEMPLATE_PATH/.claude/settings.json"
SETTINGS_DST="$PROJECT_DIR/.claude/settings.json"
if [ -f "$SETTINGS_SRC" ]; then
    if [ ! -f "$SETTINGS_DST" ] || [ "$FORCE" = true ]; then
        if [ "$DRY_RUN" = true ]; then
            log_dry "Would copy .claude/settings.json (hook definitions)"
        else
            cp "$SETTINGS_SRC" "$SETTINGS_DST"
            log_create ".claude/settings.json (hook definitions)"
        fi
    else
        log_skip ".claude/settings.json (already exists — use --force to replace)"
    fi
fi

# Copy scripts/ directory (harness-audit, observer, instinct CLI, multi-model, etc.)
# These live at the project root, not under .claude/, so TARGET_DIRS misses them.
# Several commands depend on scripts: /harness-audit, /multi-plan, /plugins, /mcps.
SCRIPTS_SRC="$TEMPLATE_PATH/scripts"
SCRIPTS_DST="$PROJECT_DIR/scripts"
if [ -d "$SCRIPTS_SRC" ]; then
    if [ ! -d "$SCRIPTS_DST" ] || [ "$FORCE" = true ]; then
        if [ "$DRY_RUN" = true ]; then
            local count
            count=$(find "$SCRIPTS_SRC" -type f | wc -l)
            log_dry "Would copy scripts/ ($count files)"
        else
            [ -d "$SCRIPTS_DST" ] && rm -rf "$SCRIPTS_DST"
            cp -r "$SCRIPTS_SRC" "$SCRIPTS_DST"
            chmod +x "$SCRIPTS_DST"/*.sh 2>/dev/null || true
            chmod +x "$SCRIPTS_DST"/*.py 2>/dev/null || true
            local count
            count=$(find "$SCRIPTS_DST" -type f | wc -l)
            log_create "scripts/ ($count files copied)"
        fi
    else
        log_skip "scripts/ (directory exists — use --force to replace)"
    fi
fi

# Ensure Task Master directory structure and config exist
# Creates .taskmaster/ with subdirectories that the CLI expects.
# Also copies the template's config.json with tuned settings (claude-code provider,
# opus/sonnet models, 200k tokens) — overwriting task-master init's wrong defaults.
for tm_dir in "tasks" "reports" "docs"; do
    if [ ! -d "$PROJECT_DIR/.taskmaster/$tm_dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            log_dry "Would create .taskmaster/$tm_dir/"
        else
            mkdir -p "$PROJECT_DIR/.taskmaster/$tm_dir"
            log_info "Created .taskmaster/$tm_dir/"
        fi
    fi
done

# Create skeleton tasks.json if it doesn't exist
# Without this, `task-master tags add` fails because the file doesn't exist yet.
# The chicken-and-egg: you want a tag before parse-prd, but tags need tasks.json.
TASKS_FILE="$PROJECT_DIR/.taskmaster/tasks/tasks.json"
if [ ! -f "$TASKS_FILE" ]; then
    if [ "$DRY_RUN" = true ]; then
        log_dry "Would create skeleton .taskmaster/tasks/tasks.json"
    else
        cat > "$TASKS_FILE" << 'SKELETON'
{
  "data": {
    "master": {
      "tasks": [],
      "metadata": {
        "createdAt": "",
        "updatedAt": ""
      }
    }
  }
}
SKELETON
        log_create ".taskmaster/tasks/tasks.json (skeleton for tag operations)"
    fi
fi

# Copy template's Task Master config with project name substitution
# Both `task-master init` (CLI) and MCP `initialize_project` create configs with
# wrong defaults (wrong provider, wrong models, wrong maxTokens). This ensures the
# template's tuned values are always applied: provider=claude-code, opus/sonnet, 200k tokens.
TM_CONFIG_SRC="$TEMPLATE_PATH/.taskmaster/config.json"
TM_CONFIG_DST="$PROJECT_DIR/.taskmaster/config.json"
if [ -f "$TM_CONFIG_SRC" ]; then
    TM_PROJECT_NAME=$(basename "$PROJECT_DIR")
    # Escape sed-special characters in project name (& and \ have meaning in replacement)
    TM_PROJECT_NAME_SAFE=$(printf '%s' "$TM_PROJECT_NAME" | sed 's/[\/&]/\\&/g')
    TM_CONFIG_ACTION="configured"
    [ -f "$TM_CONFIG_DST" ] && TM_CONFIG_ACTION="updated"
    if [ "$DRY_RUN" = true ]; then
        log_dry "Would configure .taskmaster/config.json (project: $TM_PROJECT_NAME)"
    else
        sed "s/__PROJECT_NAME__/$TM_PROJECT_NAME_SAFE/g" "$TM_CONFIG_SRC" > "$TM_CONFIG_DST"
        log_create ".taskmaster/config.json ($TM_CONFIG_ACTION, project: $TM_PROJECT_NAME)"
    fi
else
    log_warn ".taskmaster/config.json not found in template — Task Master will use its own defaults"
fi

# Create .template/ tracking directory (version + source)
# Without this, session-init.sh classifies copy-mode projects as "proto-templates"
# and shows sync recommendations instead of the phase/status display.
# Also enables version comparison for future template updates.
TEMPLATE_TRACK_DIR="$PROJECT_DIR/.template"
if [ ! -d "$TEMPLATE_TRACK_DIR" ] || [ "$FORCE" = true ]; then
    if [ "$DRY_RUN" = true ]; then
        log_dry "Would create .template/ tracking (version + source)"
    else
        mkdir -p "$TEMPLATE_TRACK_DIR"
        if [ -f "$TEMPLATE_PATH/.template/version" ]; then
            cp "$TEMPLATE_PATH/.template/version" "$TEMPLATE_TRACK_DIR/version"
        else
            echo "unknown" > "$TEMPLATE_TRACK_DIR/version"
        fi
        echo "$TEMPLATE_PATH" > "$TEMPLATE_TRACK_DIR/source"
        INSTALLED_VERSION=$(cat "$TEMPLATE_TRACK_DIR/version" 2>/dev/null | tr -d '[:space:]')
        log_create ".template/ (version: ${INSTALLED_VERSION:-unknown}, source: $TEMPLATE_PATH)"
    fi
else
    log_skip ".template/ (already exists — use --force to replace)"
fi

# Security verification for symlinks
if [ "$MODE" = "symlink" ] && [ "$DRY_RUN" = false ]; then
    echo ""
    verify_symlink_safety "$TEMPLATE_PATH"
fi

# Summary
echo ""
echo -e "${BOLD}Summary:${NC}"
echo -e "  Created: ${GREEN}$CREATED${NC}"
echo -e "  Skipped: ${DIM}$SKIPPED${NC}"
echo -e "  Warnings: ${YELLOW}$WARNED${NC}"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "Dry run complete. Run without --dry-run to apply changes."
fi

if [ "$CREATED" -gt 0 ] && [ "$DRY_RUN" = false ]; then
    echo ""
    echo -e "${GREEN}Done!${NC} Project initialized from template."
    echo ""
    echo "What was set up:"
    echo "  • Slash commands, skills, agents, hooks, rules, contexts"
    [ -f "$PROJECT_DIR/.claude/settings.json" ] && echo "  • .claude/settings.json (hook definitions)"
    [ -d "$PROJECT_DIR/scripts" ] && echo "  • scripts/ (harness-audit, observer, multi-model, CLI tools)"
    [ -f "$PROJECT_DIR/.taskmaster/config.json" ] && echo "  • .taskmaster/config.json (claude-code provider, tuned settings)"
    [ -d "$PROJECT_DIR/.template" ] && echo "  • .template/ tracking (version management)"
    echo ""
    # Initialize skill profile if skills-available exists
    SKILL_PROFILE_SCRIPT="$PROJECT_DIR/scripts/manage-skill-profiles.sh"
    if [ -x "$SKILL_PROFILE_SCRIPT" ] && [ -d "$PROJECT_DIR/.claude/skills-available" ]; then
        PROFILE="${TEMPLATE_SKILL_PROFILE:-all}"
        bash "$SKILL_PROFILE_SCRIPT" set "$PROFILE"
        echo ""
    fi

    echo "Next steps:"
    echo "  1. Customize CLAUDE.md with your project details"
    echo "  2. Set skill profile for your language: ./scripts/manage-skill-profiles.sh set <python|java|go|fullstack|all>"
    echo "  3. Start a new Claude Code session to pick up hooks and rules"
    echo ""
    echo -e "${YELLOW}Note:${NC} If you later run 'task-master init', re-run this script"
    echo "to restore the template's Task Master config."
fi

exit 0
