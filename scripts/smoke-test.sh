#!/bin/bash
# smoke-test.sh - Verify template overlay is working correctly
# Version: 1.0.0
#
# Usage:
#   ./scripts/smoke-test.sh [project-dir]
#
# Tests LOCAL presence of template components. Unlike previous static checks,
# this script verifies that commands/skills are LOCALLY available (not just
# inherited from parent), which is required for Claude Code registration.
#
# Exit codes:
#   0 - All checks passed
#   1 - Critical checks failed (commands/skills missing)

set -e

PROJECT_DIR="${1:-.}"
PROJECT_DIR=$(realpath "$PROJECT_DIR")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Counters
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
TOTAL=0

pass() {
    echo -e "  ${GREEN}PASS${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
    TOTAL=$((TOTAL + 1))
}

fail() {
    echo -e "  ${RED}FAIL${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    TOTAL=$((TOTAL + 1))
}

warn() {
    echo -e "  ${YELLOW}WARN${NC} $1"
    WARN_COUNT=$((WARN_COUNT + 1))
    TOTAL=$((TOTAL + 1))
}

# --- Header ---
echo -e "${BLUE}${BOLD}Template Overlay Smoke Test${NC}"
echo "==========================="
echo -e "Project: ${BOLD}$PROJECT_DIR${NC}"
echo ""

# --- Check 1: Rules (can be local OR inherited from parent) ---
echo -e "${BOLD}1. Rules${NC}"
RULES_DIR=""
# Check local first
if [ -d "$PROJECT_DIR/.claude/rules" ] || [ -L "$PROJECT_DIR/.claude/rules" ]; then
    RULES_DIR="$PROJECT_DIR/.claude/rules"
else
    # Walk parents to find inherited rules
    check_dir="$PROJECT_DIR"
    while [ "$check_dir" != "/" ]; do
        check_dir="$(dirname "$check_dir")"
        if [ -d "$check_dir/.claude/rules" ]; then
            RULES_DIR="$check_dir/.claude/rules"
            break
        fi
    done
fi

if [ -n "$RULES_DIR" ]; then
    rule_count=$(find "$RULES_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
    if [ "$rule_count" -gt 0 ]; then
        pass "Rules: $rule_count rule files found (from $RULES_DIR)"
    else
        fail "Rules directory exists but is empty"
    fi
else
    fail "No rules found (local or inherited)"
fi

# --- Check 2: Commands (MUST be LOCAL) ---
echo -e "${BOLD}2. Commands${NC}"
if [ -d "$PROJECT_DIR/.claude/commands" ] || [ -L "$PROJECT_DIR/.claude/commands" ]; then
    cmd_dir="$PROJECT_DIR/.claude/commands"
    if [ -L "$cmd_dir" ]; then
        target=$(readlink "$cmd_dir")
        cmd_count=$(find -L "$cmd_dir" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
        pass "Commands: $cmd_count files (symlink -> $target)"
    else
        cmd_count=$(find -L "$cmd_dir" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
        pass "Commands: $cmd_count files (local directory)"
    fi
else
    fail "Commands: NOT locally available (slash commands will fail!)"
    echo -e "         ${DIM}Fix: ./scripts/init-project.sh${NC}"
fi

# --- Check 3: Skills (MUST be LOCAL) ---
echo -e "${BOLD}3. Skills${NC}"
if [ -d "$PROJECT_DIR/.claude/skills" ] || [ -L "$PROJECT_DIR/.claude/skills" ]; then
    skill_dir="$PROJECT_DIR/.claude/skills"
    if [ -L "$skill_dir" ]; then
        target=$(readlink "$skill_dir")
        skill_count=$(find -L "$skill_dir" -maxdepth 1 -type d 2>/dev/null | wc -l)
        skill_count=$((skill_count - 1))  # Subtract the directory itself
        pass "Skills: $skill_count skill dirs (symlink -> $target)"
    else
        skill_count=$(find -L "$skill_dir" -maxdepth 1 -type d 2>/dev/null | wc -l)
        skill_count=$((skill_count - 1))
        pass "Skills: $skill_count skill dirs (local directory)"
    fi
else
    fail "Skills: NOT locally available (skills will fail!)"
    echo -e "         ${DIM}Fix: ./scripts/init-project.sh${NC}"
fi

# --- Check 4: Agents (can work via parent, but local is better) ---
echo -e "${BOLD}4. Agents${NC}"
if [ -d "$PROJECT_DIR/.claude/agents" ] || [ -L "$PROJECT_DIR/.claude/agents" ]; then
    agent_dir="$PROJECT_DIR/.claude/agents"
    agent_count=$(find -L "$agent_dir" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
    pass "Agents: $agent_count definitions (local)"
else
    # Check parent inheritance
    check_dir="$PROJECT_DIR"
    found_agents=false
    while [ "$check_dir" != "/" ]; do
        check_dir="$(dirname "$check_dir")"
        if [ -d "$check_dir/.claude/agents" ]; then
            agent_count=$(find -L "$check_dir/.claude/agents" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
            warn "Agents: $agent_count definitions (inherited from $check_dir — consider local symlink)"
            found_agents=true
            break
        fi
    done
    if [ "$found_agents" = false ]; then
        fail "Agents: None found"
    fi
fi

# --- Check 5: Contexts ---
echo -e "${BOLD}5. Contexts${NC}"
if [ -d "$PROJECT_DIR/.claude/contexts" ] || [ -L "$PROJECT_DIR/.claude/contexts" ]; then
    ctx_count=$(find -L "$PROJECT_DIR/.claude/contexts" -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l)
    pass "Contexts: $ctx_count modes available"
else
    warn "Contexts: Not locally available (context modes won't work without local dir)"
fi

# --- Check 6: Hooks ---
echo -e "${BOLD}6. Hooks${NC}"
if [ -d "$PROJECT_DIR/.claude/hooks" ] || [ -L "$PROJECT_DIR/.claude/hooks" ]; then
    hook_count=$(find -L "$PROJECT_DIR/.claude/hooks" -maxdepth 1 -name "*.sh" -type f 2>/dev/null | wc -l)
    pass "Hooks: $hook_count scripts on disk"

    # Check if hooks are wired (settings.local.json exists with hooks config)
    if [ -f "$PROJECT_DIR/.claude/settings.local.json" ]; then
        if grep -q '"hooks"' "$PROJECT_DIR/.claude/settings.local.json" 2>/dev/null; then
            pass "Hooks: Configured in settings.local.json"
        else
            warn "Hooks: settings.local.json exists but no hooks config (run /settings safe)"
        fi
    else
        warn "Hooks: Not wired (run /settings safe or copy settings-example.json)"
    fi
else
    warn "Hooks: Not locally available"
fi

# --- Check 7: CLAUDE.md ---
echo -e "${BOLD}7. CLAUDE.md${NC}"
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    if grep -q "\[PROJECT_NAME\]" "$PROJECT_DIR/CLAUDE.md" 2>/dev/null; then
        warn "CLAUDE.md: Exists but not customized (still has [PROJECT_NAME] placeholder)"
    else
        pass "CLAUDE.md: Customized"
    fi
else
    # Check parent
    check_dir="$PROJECT_DIR"
    found_claude=false
    while [ "$check_dir" != "/" ]; do
        check_dir="$(dirname "$check_dir")"
        if [ -f "$check_dir/CLAUDE.md" ]; then
            pass "CLAUDE.md: Inherited from $check_dir"
            found_claude=true
            break
        fi
    done
    if [ "$found_claude" = false ]; then
        fail "CLAUDE.md: Not found"
    fi
fi

# --- Check 8: .gitignore ---
echo -e "${BOLD}8. .gitignore${NC}"
if [ -f "$PROJECT_DIR/.gitignore" ]; then
    missing_entries=()
    for entry in "settings.local.json" ".claude/sessions" ".claude/instincts"; do
        if ! grep -q "$entry" "$PROJECT_DIR/.gitignore" 2>/dev/null; then
            missing_entries+=("$entry")
        fi
    done
    if [ ${#missing_entries[@]} -eq 0 ]; then
        pass ".gitignore: Template entries present"
    else
        warn ".gitignore: Missing entries: ${missing_entries[*]}"
    fi
else
    warn ".gitignore: File not found"
fi

# --- Summary ---
echo ""
echo -e "${BOLD}Summary: $PASS_COUNT/$TOTAL passed${NC}"
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "  ${RED}$FAIL_COUNT CRITICAL failures${NC}"
fi
if [ "$WARN_COUNT" -gt 0 ]; then
    echo -e "  ${YELLOW}$WARN_COUNT warnings${NC}"
fi

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${RED}FAILED${NC} — Critical checks did not pass."
    echo "Run ./scripts/init-project.sh to fix missing commands/skills."
    exit 1
else
    echo ""
    echo -e "${GREEN}PASSED${NC} — All critical checks passed."
    exit 0
fi
