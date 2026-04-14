#!/bin/bash
# manage-mcps.sh - Enable/disable MCP servers based on project needs
# Version: 1.0.0
#
# Usage:
#   ./scripts/manage-mcps.sh [command] [options]
#
# Commands:
#   list              List all known MCP servers with status
#   status            Show currently enabled/disabled MCPs for this project
#   enable <server>   Enable an MCP server for this project
#   disable <server>  Disable an MCP server for this project
#   preset <name>     Apply a preset configuration
#   select            Interactive MCP selection wizard
#   tokens            Show estimated token usage
#   audit             Check MCP budget (10/80 rule) and show warnings
#   install <server>  Install an MCP server globally (if not installed)
#
# Options:
#   --global          Apply to user scope instead of project scope
#   --dry-run         Preview changes without applying

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY_FILE="$PROJECT_ROOT/.claude/mcp-registry.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# MCP Budget Limits (10/80 rule)
# More MCPs = more tool definitions loaded = less working context
MAX_MCPS=10
MAX_TOOLS=80

# Options
SCOPE="project"
DRY_RUN=false

# Check for jq
check_jq() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required but not installed.${NC}"
        echo "Install with: sudo apt install jq (Linux) or brew install jq (macOS)"
        exit 1
    fi
}

# Check for claude CLI
check_claude() {
    if ! command -v claude &> /dev/null; then
        echo -e "${RED}Error: claude CLI not found.${NC}"
        exit 1
    fi
}

# Get installed MCPs from claude
get_installed_mcps() {
    claude mcp list 2>/dev/null | grep -E "✓ Connected" | cut -d: -f1 || true
}

# Check if MCP is enabled for current scope
is_enabled() {
    local server="$1"
    # Check if it appears in mcp list output as connected
    claude mcp list 2>/dev/null | grep -q "^$server:" && return 0 || return 1
}

# Audit MCP budget against 10/80 limits
# Usage: audit_mcp_budget [--brief]
# Returns: 0=OK, 1=over MCP limit, 2=over tool limit, 3=both over
audit_mcp_budget() {
    check_jq
    check_claude
    local brief=false
    [[ "${1:-}" == "--brief" ]] && brief=true

    local installed=$(get_installed_mcps)
    local mcp_count=0
    local tool_count=0

    for server in $installed; do
        ((mcp_count++))
        local tools=$(jq -r ".servers[\"$server\"].tools // 0" "$REGISTRY_FILE" 2>/dev/null)
        if [[ "$tools" =~ ^[0-9]+$ ]]; then
            tool_count=$((tool_count + tools))
        fi
    done

    local status=0

    # Determine status
    local mcp_over=false tool_over=false
    local mcp_warn=false tool_warn=false
    if [ "$mcp_count" -ge "$MAX_MCPS" ]; then mcp_over=true; fi
    if [ "$tool_count" -ge "$MAX_TOOLS" ]; then tool_over=true; fi
    if [ "$mcp_count" -ge $((MAX_MCPS * 8 / 10)) ]; then mcp_warn=true; fi
    if [ "$tool_count" -ge $((MAX_TOOLS * 8 / 10)) ]; then tool_warn=true; fi

    if $mcp_over && $tool_over; then status=3;
    elif $tool_over; then status=2;
    elif $mcp_over; then status=1; fi

    if $brief; then
        # One-line summary for inline use
        if [ "$status" -gt 0 ]; then
            echo -e "${YELLOW}Budget: ${mcp_count}/${MAX_MCPS} MCPs, ${tool_count}/${MAX_TOOLS} tools${NC}"
            $mcp_over && echo -e "${RED}  ⚠ Over MCP limit (max ${MAX_MCPS})${NC}"
            $tool_over && echo -e "${RED}  ⚠ Over tool limit (max ${MAX_TOOLS})${NC}"
        elif $mcp_warn || $tool_warn; then
            echo -e "${YELLOW}Budget: ${mcp_count}/${MAX_MCPS} MCPs, ${tool_count}/${MAX_TOOLS} tools (approaching limit)${NC}"
        fi
        return $status
    fi

    # Full report
    echo -e "${BOLD}${BLUE}MCP Budget Report (10/80 Rule)${NC}"
    echo "==============================="
    echo ""

    # MCP count with bar
    local mcp_pct=$((mcp_count * 100 / MAX_MCPS))
    local mcp_color="$GREEN"
    $mcp_warn && mcp_color="$YELLOW"
    $mcp_over && mcp_color="$RED"

    local mcp_filled=$((mcp_count > MAX_MCPS ? MAX_MCPS : mcp_count))
    local mcp_empty=$((MAX_MCPS - mcp_filled))
    local mcp_bar=""
    for ((i=0; i<mcp_filled; i++)); do mcp_bar+="●"; done
    for ((i=0; i<mcp_empty; i++)); do mcp_bar+="○"; done

    echo -e "  MCPs:  ${mcp_color}${mcp_count}/${MAX_MCPS}${NC} ${mcp_color}${mcp_bar}${NC}"

    # Tool count with bar
    local tool_pct=$((tool_count * 100 / MAX_TOOLS))
    local tool_color="$GREEN"
    $tool_warn && tool_color="$YELLOW"
    $tool_over && tool_color="$RED"

    local tool_bar_len=20
    local tool_filled=$((tool_pct * tool_bar_len / 100))
    [ "$tool_filled" -gt "$tool_bar_len" ] && tool_filled=$tool_bar_len
    local tool_empty=$((tool_bar_len - tool_filled))
    local tool_bar=""
    for ((i=0; i<tool_filled; i++)); do tool_bar+="█"; done
    for ((i=0; i<tool_empty; i++)); do tool_bar+="░"; done

    echo -e "  Tools: ${tool_color}${tool_count}/${MAX_TOOLS}${NC} ${tool_color}${tool_bar}${NC}"
    echo ""

    # Status line
    if [ "$status" -eq 0 ] && ! $mcp_warn && ! $tool_warn; then
        echo -e "  Status: ${GREEN}OK${NC} — within budget"
    elif [ "$status" -eq 0 ]; then
        echo -e "  Status: ${YELLOW}WARNING${NC} — approaching limits"
    else
        echo -e "  Status: ${RED}EXCEEDED${NC} — over budget"
        $mcp_over && echo -e "  ${RED}⚠ Reduce MCPs to under ${MAX_MCPS} for optimal context usage${NC}"
        $tool_over && echo -e "  ${RED}⚠ Reduce tools to under ${MAX_TOOLS} (disable heavy servers)${NC}"
    fi

    echo ""
    echo -e "${DIM}Why this matters: Each tool definition consumes context tokens at startup.${NC}"
    echo -e "${DIM}Staying under 10 MCPs / 80 tools keeps overhead at ~15-20% of context.${NC}"

    return $status
}

# List all MCPs with status
list_mcps() {
    check_jq
    check_claude

    echo -e "${BOLD}${BLUE}MCP Servers${NC}"
    echo "============"
    echo ""

    local installed=$(get_installed_mcps)

    # Get all servers from registry
    local servers=$(jq -r '.servers | keys[]' "$REGISTRY_FILE")

    for server in $servers; do
        local name=$(jq -r ".servers[\"$server\"].name" "$REGISTRY_FILE")
        local desc=$(jq -r ".servers[\"$server\"].description" "$REGISTRY_FILE")
        local tokens=$(jq -r ".servers[\"$server\"].estimated_tokens" "$REGISTRY_FILE")
        local tools=$(jq -r ".servers[\"$server\"].tools // 0" "$REGISTRY_FILE")
        local categories=$(jq -r ".servers[\"$server\"].categories | join(\", \")" "$REGISTRY_FILE")

        # Color-code tool count by weight
        local tool_indicator="${GREEN}●${NC}"  # 1-5: lightweight
        if [ "$tools" -ge 16 ]; then
            tool_indicator="${RED}●${NC}"      # 16+: heavy
        elif [ "$tools" -ge 6 ]; then
            tool_indicator="${YELLOW}●${NC}"   # 6-15: moderate
        fi

        # Check if installed
        if echo "$installed" | grep -q "^$server$"; then
            echo -e "${GREEN}●${NC} ${BOLD}$name${NC} ($server)"
            echo -e "  ${DIM}$desc${NC}"
            echo -e "  Tokens: ~$tokens | Tools: $tools $tool_indicator | $categories"
        else
            echo -e "${DIM}○ $name ($server)${NC}"
            echo -e "  ${DIM}$desc${NC}"
            echo -e "  ${DIM}Tokens: ~$tokens | Tools: $tools | Not installed${NC}"
        fi
        echo ""
    done

    echo -e "${DIM}Tool weight: ${GREEN}●${NC}${DIM} light (1-5) ${YELLOW}●${NC}${DIM} moderate (6-15) ${RED}●${NC}${DIM} heavy (16+)${NC}"
}

# Show current status
show_status() {
    check_claude

    echo -e "${BOLD}${BLUE}Current MCP Status${NC}"
    echo "==================="
    echo ""

    echo -e "${BOLD}Enabled MCPs:${NC}"
    claude mcp list 2>&1 | grep -E "✓ Connected" | while read line; do
        local name=$(echo "$line" | cut -d: -f1)
        echo -e "  ${GREEN}●${NC} $name"
    done

    echo ""
    echo -e "${DIM}Use './scripts/manage-mcps.sh disable <name>' to disable for this project${NC}"
}

# Enable an MCP
enable_mcp() {
    check_claude
    local server="$1"

    if [ -z "$server" ]; then
        echo -e "${RED}Error: Server name required${NC}"
        echo "Usage: $0 enable <server-name>"
        exit 1
    fi

    echo -e "${BLUE}Enabling: ${BOLD}$server${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would run: claude mcp enable $server --scope $SCOPE${NC}"
        return
    fi

    claude mcp enable "$server" --scope "$SCOPE" 2>&1 || {
        echo -e "${YELLOW}Server may not be installed. Checking registry...${NC}"
        if jq -e ".servers[\"$server\"]" "$REGISTRY_FILE" > /dev/null 2>&1; then
            local install_cmd=$(jq -r ".servers[\"$server\"].install_command" "$REGISTRY_FILE")
            echo -e "To install, run:"
            echo -e "  ${CYAN}$install_cmd${NC}"
        else
            echo -e "${RED}Unknown server: $server${NC}"
        fi
        return 1
    }

    echo -e "${GREEN}Enabled successfully${NC}"
    echo -e "${YELLOW}Note: Restart Claude Code for changes to take effect${NC}"

    # Budget check after successful enable
    audit_mcp_budget --brief
}

# Disable an MCP
disable_mcp() {
    check_claude
    local server="$1"

    if [ -z "$server" ]; then
        echo -e "${RED}Error: Server name required${NC}"
        echo "Usage: $0 disable <server-name>"
        exit 1
    fi

    echo -e "${BLUE}Disabling: ${BOLD}$server${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would run: claude mcp disable $server --scope $SCOPE${NC}"
        return
    fi

    claude mcp disable "$server" --scope "$SCOPE" 2>&1

    echo -e "${GREEN}Disabled successfully${NC}"
    echo -e "${YELLOW}Note: Restart Claude Code for changes to take effect${NC}"
}

# Apply a preset
apply_preset() {
    check_jq
    check_claude
    local preset="$1"

    if [ -z "$preset" ]; then
        echo -e "${BOLD}${BLUE}Available Presets${NC}"
        echo "=================="
        echo ""

        jq -r '.presets | to_entries[] | "\(.key)|\(.value.name)|\(.value.description)|\(.value.estimated_tokens)"' "$REGISTRY_FILE" | \
        while IFS='|' read -r key name desc tokens; do
            echo -e "${BOLD}$key${NC}: $name"
            echo -e "  $desc"
            echo -e "  ${DIM}Estimated tokens: ~$tokens${NC}"
            echo ""
        done
        return
    fi

    # Check if preset exists
    if ! jq -e ".presets[\"$preset\"]" "$REGISTRY_FILE" > /dev/null 2>&1; then
        echo -e "${RED}Unknown preset: $preset${NC}"
        echo "Run: $0 preset"
        exit 1
    fi

    local preset_name=$(jq -r ".presets[\"$preset\"].name" "$REGISTRY_FILE")
    local servers=$(jq -r ".presets[\"$preset\"].servers[]" "$REGISTRY_FILE")

    echo -e "${BLUE}Applying preset: ${BOLD}$preset_name${NC}"
    echo ""

    # Get all known servers
    local all_servers=$(jq -r '.servers | keys[]' "$REGISTRY_FILE")
    local installed=$(get_installed_mcps)

    # Disable servers not in preset
    for server in $installed; do
        if ! echo "$servers" | grep -q "^$server$"; then
            echo -e "Disabling: $server"
            if [ "$DRY_RUN" != true ]; then
                claude mcp disable "$server" --scope "$SCOPE" 2>/dev/null || true
            fi
        fi
    done

    # Enable servers in preset
    for server in $servers; do
        if echo "$installed" | grep -q "^$server$"; then
            echo -e "Enabling: $server"
            if [ "$DRY_RUN" != true ]; then
                claude mcp enable "$server" --scope "$SCOPE" 2>/dev/null || true
            fi
        else
            echo -e "${YELLOW}Not installed: $server${NC}"
            local install_cmd=$(jq -r ".servers[\"$server\"].install_command" "$REGISTRY_FILE" 2>/dev/null)
            if [ -n "$install_cmd" ] && [ "$install_cmd" != "null" ]; then
                echo -e "  Install with: ${CYAN}$install_cmd${NC}"
            fi
        fi
    done

    echo ""
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] No changes made${NC}"
    else
        echo -e "${GREEN}Preset applied${NC}"
        echo -e "${YELLOW}Restart Claude Code for changes to take effect${NC}"

        # Budget check after preset apply
        audit_mcp_budget --brief
    fi
}

# Show token usage
show_tokens() {
    check_jq
    check_claude

    echo -e "${BOLD}${BLUE}Token Usage Estimate${NC}"
    echo "====================="
    echo ""

    local installed=$(get_installed_mcps)
    local total=0

    echo -e "${BOLD}Enabled MCPs:${NC}"
    for server in $installed; do
        local tokens=$(jq -r ".servers[\"$server\"].estimated_tokens // 0" "$REGISTRY_FILE")
        local name=$(jq -r ".servers[\"$server\"].name // \"$server\"" "$REGISTRY_FILE")
        if [ "$tokens" != "0" ] && [ "$tokens" != "null" ]; then
            printf "  %-25s %'6d tokens\n" "$name" "$tokens"
            total=$((total + tokens))
        else
            printf "  %-25s %s\n" "$server" "(unknown)"
        fi
    done

    echo ""
    echo -e "${BOLD}Total MCP overhead:${NC} ~${CYAN}$total${NC} tokens"
    echo ""

    # MCP budget summary
    local mcp_count=0
    local tool_count=0
    for server in $installed; do
        ((mcp_count++))
        local tools=$(jq -r ".servers[\"$server\"].tools // 0" "$REGISTRY_FILE" 2>/dev/null)
        [[ "$tools" =~ ^[0-9]+$ ]] && tool_count=$((tool_count + tools))
    done

    local mcp_color="$GREEN" tool_color="$GREEN"
    [ "$mcp_count" -ge $((MAX_MCPS * 8 / 10)) ] && mcp_color="$YELLOW"
    [ "$mcp_count" -ge "$MAX_MCPS" ] && mcp_color="$RED"
    [ "$tool_count" -ge $((MAX_TOOLS * 8 / 10)) ] && tool_color="$YELLOW"
    [ "$tool_count" -ge "$MAX_TOOLS" ] && tool_color="$RED"

    echo -e "${BOLD}Budget (10/80 Rule):${NC}"
    echo -e "  MCPs:  ${mcp_color}${mcp_count}/${MAX_MCPS}${NC}"
    echo -e "  Tools: ${tool_color}${tool_count}/${MAX_TOOLS}${NC}"
    echo ""
    echo -e "${DIM}Note: This is approximate. Actual usage varies by tool complexity.${NC}"
    echo -e "${DIM}Run '$0 audit' for detailed budget analysis.${NC}"
}

# Interactive selection
interactive_select() {
    check_jq
    check_claude

    echo -e "${BOLD}${BLUE}MCP Selection Wizard${NC}"
    echo "====================="
    echo ""
    echo "This wizard helps you enable/disable MCPs based on your project needs."
    echo -e "${YELLOW}Note: More MCPs = more context tokens used per conversation.${NC}"
    echo ""

    echo -e "${BOLD}What type of project are you working on?${NC}"
    echo ""
    echo "  1) Python Backend (APIs, databases)"
    echo "  2) Frontend (React, Vue, browser testing)"
    echo "  3) Full-Stack Web Application"
    echo "  4) E-Commerce / Payments"
    echo "  5) WordPress / Content"
    echo "  6) Testing & QA Automation"
    echo "  7) Minimal (just essentials)"
    echo "  8) Custom selection"
    echo ""
    read -p "Select [1-8]: " project_type

    case $project_type in
        1) apply_preset "python-backend" ;;
        2) apply_preset "frontend" ;;
        3) apply_preset "fullstack" ;;
        4) apply_preset "e-commerce" ;;
        5) apply_preset "content" ;;
        6) apply_preset "testing" ;;
        7) apply_preset "minimal" ;;
        8)
            echo ""
            echo -e "${BOLD}Select MCPs to enable:${NC}"
            echo ""

            local servers=$(jq -r '.servers | keys[]' "$REGISTRY_FILE")
            local i=1
            local server_array=()

            for server in $servers; do
                local name=$(jq -r ".servers[\"$server\"].name" "$REGISTRY_FILE")
                local tokens=$(jq -r ".servers[\"$server\"].estimated_tokens" "$REGISTRY_FILE")
                echo "  $i) $name (~$tokens tokens)"
                server_array+=("$server")
                ((i++))
            done

            echo ""
            read -p "Enter numbers (comma-separated): " selections

            # Parse selections
            local selected=()
            IFS=',' read -ra NUMS <<< "$selections"
            for num in "${NUMS[@]}"; do
                num=$(echo "$num" | tr -d ' ')
                if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#server_array[@]}" ]; then
                    selected+=("${server_array[$((num-1))]}")
                fi
            done

            echo ""
            echo -e "${BOLD}Selected:${NC} ${selected[*]}"
            read -p "Apply this configuration? [Y/n]: " confirm

            if [[ ! "$confirm" =~ ^[Nn]$ ]]; then
                local installed=$(get_installed_mcps)

                # Disable all first
                for server in $installed; do
                    claude mcp disable "$server" --scope "$SCOPE" 2>/dev/null || true
                done

                # Enable selected
                for server in "${selected[@]}"; do
                    if echo "$installed" | grep -q "^$server$"; then
                        claude mcp enable "$server" --scope "$SCOPE" 2>/dev/null || true
                    else
                        echo -e "${YELLOW}Not installed: $server${NC}"
                    fi
                done

                echo -e "${GREEN}Configuration applied${NC}"
                echo -e "${YELLOW}Restart Claude Code for changes to take effect${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Invalid selection${NC}"
            exit 1
            ;;
    esac
}

# Install an MCP
install_mcp() {
    check_jq
    check_claude
    local server="$1"

    if [ -z "$server" ]; then
        echo -e "${RED}Error: Server name required${NC}"
        exit 1
    fi

    if ! jq -e ".servers[\"$server\"]" "$REGISTRY_FILE" > /dev/null 2>&1; then
        echo -e "${RED}Unknown server: $server${NC}"
        exit 1
    fi

    local install_cmd=$(jq -r ".servers[\"$server\"].install_command" "$REGISTRY_FILE")
    local env_vars=$(jq -r ".servers[\"$server\"].env_vars[]" "$REGISTRY_FILE" 2>/dev/null)

    echo -e "${BLUE}Installing: ${BOLD}$server${NC}"

    if [ -n "$env_vars" ]; then
        echo -e "${YELLOW}Required environment variables:${NC}"
        for var in $env_vars; do
            echo "  - $var"
        done
        echo ""
    fi

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would run: $install_cmd${NC}"
        return
    fi

    echo "Running: $install_cmd"
    eval "$install_cmd"

    echo -e "${GREEN}Installed successfully${NC}"
    echo -e "${YELLOW}Restart Claude Code for changes to take effect${NC}"
}

# Parse arguments
ARGS=()
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --global) SCOPE="user" ;;
        --dry-run) DRY_RUN=true ;;
        *) ARGS+=("$1") ;;
    esac
    shift
done

# Main
main() {
    local command="${ARGS[0]:-help}"
    local remaining=("${ARGS[@]:1}")

    case "$command" in
        list)
            list_mcps
            ;;
        status)
            show_status
            ;;
        enable)
            enable_mcp "${remaining[@]}"
            ;;
        disable)
            disable_mcp "${remaining[@]}"
            ;;
        preset)
            apply_preset "${remaining[@]}"
            ;;
        select|wizard)
            interactive_select
            ;;
        tokens)
            show_tokens
            ;;
        audit)
            audit_mcp_budget
            ;;
        install)
            install_mcp "${remaining[@]}"
            ;;
        help|--help|-h)
            head -20 "$0" | tail -n +2 | sed 's/^# //'
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            echo "Run: $0 help"
            exit 1
            ;;
    esac
}

main
