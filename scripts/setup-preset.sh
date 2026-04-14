#!/bin/bash
# setup-preset.sh - Apply a project-type preset to scaffold directories and configure CLAUDE.md
# Version: 1.0.0
#
# Usage:
#   ./scripts/setup-preset.sh <preset-name> [options]
#   ./scripts/setup-preset.sh --list
#
# Presets:
#   python-fastapi       FastAPI + SQLAlchemy + PostgreSQL
#   node-nextjs          Next.js + React + TypeScript
#   go-api               Go stdlib + PostgreSQL + sqlc
#   java-spring          Spring Boot + JPA + PostgreSQL
#   python-data-science  pandas + scikit-learn + Jupyter
#
# Options:
#   --dry-run            Preview changes without applying
#   --force              Overwrite already-customized CLAUDE.md
#   --name <name>        Set project name (default: directory name)
#   --list               List available presets

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PRESETS_FILE="$PROJECT_ROOT/.claude/presets/project-presets.json"
CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
STATE_FILE="$PROJECT_ROOT/.claude/project-state.json"
GITIGNORE_FILE="$PROJECT_ROOT/.gitignore"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Options
DRY_RUN=false
FORCE=false
PROJECT_NAME=""
LIST_ONLY=false
PRESET_NAME=""

# ─── Helpers ──────────────────────────────────────────────────────────

check_jq() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required but not installed.${NC}"
        echo "Install with: sudo apt install jq (Linux) or brew install jq (macOS)"
        exit 1
    fi
}

log_info() {
    echo -e "${BLUE}→${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_dry() {
    echo -e "${DIM}  [dry-run]${NC} $1"
}

# ─── Parse Arguments ─────────────────────────────────────────────────

parse_args() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --dry-run) DRY_RUN=true ;;
            --force) FORCE=true ;;
            --list) LIST_ONLY=true ;;
            --name)
                shift
                PROJECT_NAME="$1"
                ;;
            -*)
                log_error "Unknown option: $1"
                echo "Usage: ./scripts/setup-preset.sh <preset-name> [--dry-run] [--force] [--name <name>]"
                exit 1
                ;;
            *)
                if [ -z "$PRESET_NAME" ]; then
                    PRESET_NAME="$1"
                else
                    log_error "Unexpected argument: $1"
                    exit 1
                fi
                ;;
        esac
        shift
    done
}

# ─── Core Functions ──────────────────────────────────────────────────

list_presets() {
    echo -e "${BOLD}${BLUE}Available Project Presets${NC}"
    echo "========================"
    echo ""

    local presets
    presets=$(jq -r '.presets | keys[]' "$PRESETS_FILE")

    for preset in $presets; do
        local name desc
        name=$(jq -r ".presets[\"$preset\"].name" "$PRESETS_FILE")
        desc=$(jq -r ".presets[\"$preset\"].description" "$PRESETS_FILE")
        echo -e "  ${CYAN}${preset}${NC}"
        echo -e "    ${desc}"
        echo ""
    done

    echo "Usage: ./scripts/setup-preset.sh <preset-name> [--dry-run]"
    echo "  Or:  /setup preset <preset-name>"
}

validate_preset() {
    local preset="$1"

    if ! jq -e ".presets[\"$preset\"]" "$PRESETS_FILE" > /dev/null 2>&1; then
        log_error "Unknown preset: ${preset}"
        echo ""
        echo "Available presets:"
        jq -r '.presets | keys[] | "  " + .' "$PRESETS_FILE"
        exit 1
    fi
}

check_claude_md_state() {
    if [ ! -f "$CLAUDE_MD" ]; then
        log_error "CLAUDE.md not found at $CLAUDE_MD"
        exit 1
    fi

    if ! grep -q "\[PROJECT_NAME\]" "$CLAUDE_MD" 2>/dev/null; then
        if [ "$FORCE" = false ]; then
            log_error "CLAUDE.md appears to be already customized (no [PROJECT_NAME] placeholder)."
            echo "  Use --force to overwrite, or edit CLAUDE.md manually."
            exit 1
        else
            log_warning "CLAUDE.md already customized — overwriting with --force"
        fi
    fi
}

show_preview() {
    local preset="$1"

    local name desc
    name=$(jq -r ".presets[\"$preset\"].name" "$PRESETS_FILE")
    desc=$(jq -r ".presets[\"$preset\"].description" "$PRESETS_FILE")

    echo ""
    echo -e "${BOLD}${BLUE}Preset: ${name}${NC}"
    echo -e "${DIM}${desc}${NC}"
    echo ""

    # Tech stack
    echo -e "${BOLD}Tech Stack:${NC}"
    jq -r ".presets[\"$preset\"].tech_stack[]" "$PRESETS_FILE" | while read -r item; do
        echo "  • $item"
    done
    echo ""

    # Directories
    echo -e "${BOLD}Directories to create:${NC}"
    jq -r ".presets[\"$preset\"].directories[]" "$PRESETS_FILE" | while read -r dir; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            echo -e "  ${DIM}$dir/ (exists)${NC}"
        else
            echo -e "  ${GREEN}$dir/${NC} (new)"
        fi
    done
    echo ""

    # Dev commands
    echo -e "${BOLD}Development commands:${NC}"
    jq -r ".presets[\"$preset\"].dev_commands | to_entries[] | \"  \" + .key + \": \" + .value" "$PRESETS_FILE"
    echo ""

    # Packages
    echo -e "${BOLD}Recommended packages:${NC}"
    echo -e "  ${CYAN}Runtime:${NC}"
    jq -r ".presets[\"$preset\"].packages.runtime[]" "$PRESETS_FILE" | while read -r pkg; do
        echo "    • $pkg"
    done
    echo -e "  ${CYAN}Dev:${NC}"
    jq -r ".presets[\"$preset\"].packages.dev[]" "$PRESETS_FILE" | while read -r pkg; do
        echo "    • $pkg"
    done
    echo ""

    # Skills
    echo -e "${BOLD}Related skills (auto-activated by tech stack keywords):${NC}"
    jq -r ".presets[\"$preset\"].skills[]" "$PRESETS_FILE" | while read -r skill; do
        echo "  • $skill"
    done
    echo ""

    # CLAUDE.md sections
    echo -e "${BOLD}CLAUDE.md sections to update:${NC}"
    echo "  • Tech Stack"
    echo "  • Structure"
    echo "  • Development Commands"
    echo "  • Project-Specific Patterns"
    echo ""
}

create_directories() {
    local preset="$1"

    log_info "Creating directories..."

    jq -r ".presets[\"$preset\"].directories[]" "$PRESETS_FILE" | while read -r dir; do
        local full_path="$PROJECT_ROOT/$dir"
        if [ -d "$full_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                log_dry "Skip (exists): $dir/"
            fi
        else
            if [ "$DRY_RUN" = true ]; then
                log_dry "Would create: $dir/"
            else
                mkdir -p "$full_path"
                # Add .gitkeep to empty directories
                touch "$full_path/.gitkeep"
                log_success "Created $dir/"
            fi
        fi
    done
}

rewrite_claude_md() {
    local preset="$1"
    local project_name="$2"

    log_info "Updating CLAUDE.md..."

    if [ "$DRY_RUN" = true ]; then
        log_dry "Would update CLAUDE.md sections: Tech Stack, Structure, Development Commands, Patterns"
        return
    fi

    # Build replacement content for each section
    local tech_stack structure dev_commands patterns

    # Tech stack as markdown list
    tech_stack=$(jq -r ".presets[\"$preset\"].tech_stack[]" "$PRESETS_FILE" | sed 's/^/- /')

    # Structure as code block content
    structure=$(jq -r ".presets[\"$preset\"].structure_doc" "$PRESETS_FILE")

    # Dev commands as bash code block content
    dev_commands=""
    local install test lint typecheck security run_cmd
    install=$(jq -r ".presets[\"$preset\"].dev_commands.install" "$PRESETS_FILE")
    test=$(jq -r ".presets[\"$preset\"].dev_commands.test" "$PRESETS_FILE")
    lint=$(jq -r ".presets[\"$preset\"].dev_commands.lint" "$PRESETS_FILE")
    typecheck=$(jq -r ".presets[\"$preset\"].dev_commands.typecheck" "$PRESETS_FILE")
    security=$(jq -r ".presets[\"$preset\"].dev_commands.security" "$PRESETS_FILE")
    run_cmd=$(jq -r ".presets[\"$preset\"].dev_commands.run" "$PRESETS_FILE")

    dev_commands="# Install dependencies
${install}

# Run tests
${test}

# Run linter
${lint}

# Type checking
${typecheck}

# Security audit
${security}

# Run development server
${run_cmd}"

    # Patterns as markdown list
    patterns=$(jq -r ".presets[\"$preset\"].patterns[]" "$PRESETS_FILE" | sed 's/^/- /')

    # Use awk for section-state replacement
    # Strategy: track which section we're in. When we hit a target section header,
    # print the header, print new content, then skip original content until next ## header.
    local tmp_file
    tmp_file=$(mktemp)

    awk -v project_name="$project_name" \
        -v tech_stack="$tech_stack" \
        -v structure="$structure" \
        -v dev_commands="$dev_commands" \
        -v patterns="$patterns" \
    '
    BEGIN { skip = 0; section = "" }

    /^# Project:/ {
        print "# Project: " project_name
        next
    }

    /^\[One-line description/ {
        next
    }

    /^## Tech Stack/ {
        if (skip == 1) { print "" }
        print $0
        print ""
        print tech_stack
        skip = 1
        section = "tech_stack"
        next
    }

    /^## Structure/ {
        if (skip == 1) { print "" }
        print $0
        print ""
        print "```"
        print structure
        print "```"
        skip = 1
        section = "structure"
        next
    }

    /^## Development Commands/ {
        if (skip == 1) { print "" }
        print $0
        print ""
        print "```bash"
        print dev_commands
        print "```"
        skip = 1
        section = "dev_commands"
        next
    }

    /^## Project-Specific Patterns/ {
        if (skip == 1) { print "" }
        print $0
        print ""
        print patterns
        skip = 1
        section = "patterns"
        next
    }

    /^## / {
        if (skip == 1) {
            print ""
            skip = 0
            section = ""
        }
        print $0
        next
    }

    {
        if (skip == 0) {
            print $0
        }
    }
    ' "$CLAUDE_MD" > "$tmp_file"

    mv "$tmp_file" "$CLAUDE_MD"
    log_success "Updated CLAUDE.md with ${preset} configuration"
}

update_project_state() {
    local preset="$1"
    local project_name="$2"

    log_info "Writing project state..."

    if [ "$DRY_RUN" = true ]; then
        log_dry "Would write .claude/project-state.json"
        return
    fi

    local tech_stack_json
    tech_stack_json=$(jq -c ".presets[\"$preset\"].tech_stack" "$PRESETS_FILE")

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Merge with existing state if present, or create new
    if [ -f "$STATE_FILE" ]; then
        local tmp_file
        tmp_file=$(mktemp)
        jq --arg preset "$preset" \
           --arg name "$project_name" \
           --arg ts "$timestamp" \
           --argjson tech "$tech_stack_json" \
           '. + {
               preset: $preset,
               project_name: $name,
               tech_stack: $tech,
               preset_applied_at: $ts,
               setup_complete: true
           }' "$STATE_FILE" > "$tmp_file"
        mv "$tmp_file" "$STATE_FILE"
    else
        jq -n --arg preset "$preset" \
              --arg name "$project_name" \
              --arg ts "$timestamp" \
              --argjson tech "$tech_stack_json" \
              '{
                  initialized_at: $ts,
                  scenario: "new",
                  project_name: $name,
                  preset: $preset,
                  tech_stack: $tech,
                  preset_applied_at: $ts,
                  setup_complete: true,
                  onboarding_steps_completed: [
                      "preset_applied",
                      "claude_md_customized",
                      "directories_created"
                  ]
              }' > "$STATE_FILE"
    fi

    log_success "Written project state to .claude/project-state.json"
}

update_gitignore() {
    local preset="$1"

    local additions
    additions=$(jq -r ".presets[\"$preset\"].gitignore_additions[]" "$PRESETS_FILE" 2>/dev/null)

    if [ -z "$additions" ]; then
        return
    fi

    log_info "Updating .gitignore..."

    if [ "$DRY_RUN" = true ]; then
        log_dry "Would append preset-specific entries to .gitignore"
        return
    fi

    # Check if preset section already exists
    if grep -q "# Preset: $preset" "$GITIGNORE_FILE" 2>/dev/null; then
        log_warning ".gitignore already has entries for preset ${preset} — skipping"
        return
    fi

    {
        echo ""
        echo "# Preset: $preset"
        echo "$additions"
    } >> "$GITIGNORE_FILE"

    log_success "Updated .gitignore with ${preset} entries"
}

generate_starter_files() {
    local preset="$1"
    local project_name="$2"

    log_info "Generating starter files for TDD..."

    if [ "$DRY_RUN" = true ]; then
        log_dry "Would generate starter files (conftest.py, __init__.py, test stub)"
        return
    fi

    # Detect language family from tech stack
    local tech_stack
    tech_stack=$(jq -r ".presets[\"$preset\"].tech_stack[]" "$PRESETS_FILE" | tr '[:upper:]' '[:lower:]')

    local is_python=false
    local is_node=false
    local is_go=false
    echo "$tech_stack" | grep -qi "python" && is_python=true
    echo "$tech_stack" | grep -qi "node\|next\|react\|typescript" && is_node=true
    echo "$tech_stack" | grep -qi "^go " && is_go=true

    # Convert project name to valid Python package name
    local package_name
    package_name=$(echo "$project_name" | tr '-' '_' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_]//g')

    if [ "$is_python" = true ]; then
        # Create __init__.py files in all src/ subdirectories
        find "$PROJECT_ROOT/src" -type d 2>/dev/null | while read -r dir; do
            if [ ! -f "$dir/__init__.py" ]; then
                touch "$dir/__init__.py"
            fi
        done
        log_success "Created __init__.py files in src/"

        # Create tests/conftest.py if it doesn't exist
        if [ ! -f "$PROJECT_ROOT/tests/conftest.py" ]; then
            cat > "$PROJECT_ROOT/tests/conftest.py" << 'CONFTEST_EOF'
"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_data():
    """Example fixture — replace with project-specific setup."""
    return {"key": "value"}
CONFTEST_EOF
            log_success "Created tests/conftest.py"
        fi

        # Create a passing test stub so pytest works immediately
        if [ ! -f "$PROJECT_ROOT/tests/test_setup.py" ]; then
            cat > "$PROJECT_ROOT/tests/test_setup.py" << TESTSETUP_EOF
"""Verify project setup is correct."""


def test_project_imports():
    """Verify the package is importable — proves setup works."""
    # Replace 'src' with actual module imports once code exists
    assert True, "Project scaffolding is complete"


def test_fixture_works(sample_data):
    """Verify conftest fixtures load correctly."""
    assert sample_data == {"key": "value"}
TESTSETUP_EOF
            log_success "Created tests/test_setup.py (2 passing tests)"
        fi

        # Remove erroneous tests/conftest/ directory if it exists (was a preset bug)
        if [ -d "$PROJECT_ROOT/tests/conftest" ]; then
            rm -rf "$PROJECT_ROOT/tests/conftest"
            log_warning "Removed erroneous tests/conftest/ directory"
        fi

    elif [ "$is_node" = true ]; then
        # Create a basic test stub for Node/Next.js
        if [ ! -f "$PROJECT_ROOT/tests/setup.test.ts" ]; then
            mkdir -p "$PROJECT_ROOT/tests"
            cat > "$PROJECT_ROOT/tests/setup.test.ts" << 'NODETEST_EOF'
describe('Project Setup', () => {
  it('should have working test infrastructure', () => {
    expect(true).toBe(true);
  });
});
NODETEST_EOF
            log_success "Created tests/setup.test.ts"
        fi

    elif [ "$is_go" = true ]; then
        # Create a basic Go test stub
        if [ ! -f "$PROJECT_ROOT/main_test.go" ]; then
            cat > "$PROJECT_ROOT/main_test.go" << 'GOTEST_EOF'
package main

import "testing"

func TestSetup(t *testing.T) {
	// Verify project scaffolding works
	t.Log("Project setup is complete")
}
GOTEST_EOF
            log_success "Created main_test.go"
        fi
    fi
}

show_summary() {
    local preset="$1"
    local project_name="$2"

    local name
    name=$(jq -r ".presets[\"$preset\"].name" "$PRESETS_FILE")

    echo ""
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${BOLD}${YELLOW}  DRY RUN COMPLETE${NC} — no changes were made"
    else
        echo -e "${BOLD}${GREEN}  PRESET APPLIED: ${name}${NC}"
    fi

    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ "$DRY_RUN" = false ]; then
        echo -e "  Project: ${BOLD}${project_name}${NC}"
        echo -e "  Preset:  ${CYAN}${preset}${NC}"
        echo ""
        echo -e "${BOLD}Next steps:${NC}"
        echo ""
        echo "  1. Install packages:"

        local install_cmd
        install_cmd=$(jq -r ".presets[\"$preset\"].dev_commands.install" "$PRESETS_FILE")
        echo -e "     ${CYAN}${install_cmd}${NC}"
        echo ""

        echo "  2. Recommended packages to install:"
        jq -r ".presets[\"$preset\"].packages.runtime[]" "$PRESETS_FILE" | while read -r pkg; do
            echo "     • $pkg"
        done
        echo ""

        echo "  3. Initialize Taskmaster (if not done):"
        echo -e "     ${CYAN}task-master init${NC}"
        echo ""

        echo "  4. Verify TDD works (should pass):"
        echo -e "     ${CYAN}pytest${NC}"
        echo ""

        echo "  5. Create a PRD and start planning:"
        echo -e "     ${CYAN}task-master parse-prd .taskmaster/docs/prd.txt${NC}"
        echo ""
    fi
}

# ─── Main ────────────────────────────────────────────────────────────

main() {
    parse_args "$@"
    check_jq

    # Check presets file exists
    if [ ! -f "$PRESETS_FILE" ]; then
        log_error "Presets file not found: $PRESETS_FILE"
        exit 1
    fi

    # List mode
    if [ "$LIST_ONLY" = true ]; then
        list_presets
        exit 0
    fi

    # Require preset name
    if [ -z "$PRESET_NAME" ]; then
        log_error "No preset specified."
        echo ""
        list_presets
        exit 1
    fi

    # Validate
    validate_preset "$PRESET_NAME"
    check_claude_md_state

    # Default project name to directory name
    if [ -z "$PROJECT_NAME" ]; then
        PROJECT_NAME=$(basename "$PROJECT_ROOT")
    fi

    # Show preview
    show_preview "$PRESET_NAME"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}${BOLD}DRY RUN${NC} — showing what would happen:"
        echo ""
    fi

    # Execute
    create_directories "$PRESET_NAME"
    generate_starter_files "$PRESET_NAME" "$PROJECT_NAME"
    rewrite_claude_md "$PRESET_NAME" "$PROJECT_NAME"
    update_project_state "$PRESET_NAME" "$PROJECT_NAME"
    update_gitignore "$PRESET_NAME"

    # Summary
    show_summary "$PRESET_NAME" "$PROJECT_NAME"
}

main "$@"
