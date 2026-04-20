#!/bin/bash
# check-upstream.sh - Check all upstream sources for updates
#
# Compares current template state against upstream repos to identify
# changes worth reviewing. Run monthly or when planning updates.
#
# Usage: ./scripts/check-upstream.sh [--since YYYY-MM-DD] [--verbose]
#        ./scripts/check-upstream.sh --manifest [--diff]
#
# Upstreams tracked:
#   1. obra/superpowers           - Workflow enforcement plugin (14 skills)
#   2. affaan-m/everything-claude-code - ECC patterns (hooks, agents, commands)
#   3. anthropics/claude-plugins-official - Official Anthropic skills
#   4. task-master-ai (npm)       - Task management MCP server
#   5. wshobson/agents            - Plugin marketplace (65+ agents/skills)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Defaults
DEFAULT_SINCE="2026-02-22"  # Template v2.2.1 release date
SINCE="${DEFAULT_SINCE}"
VERBOSE=false
MANIFEST_MODE=false
SHOW_DIFF=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_FILE="$PROJECT_ROOT/.claude/upstream-manifest.json"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --since) SINCE="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        --manifest) MANIFEST_MODE=true; shift ;;
        --diff) SHOW_DIFF=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--since YYYY-MM-DD] [--verbose]"
            echo "       $0 --manifest [--diff]"
            echo ""
            echo "Check upstream repos for changes since a date (default: ${DEFAULT_SINCE})"
            echo ""
            echo "Modes:"
            echo "  (default)       Repo-level commit counts for all 5 upstreams"
            echo "  --manifest      File-level diff detection using upstream-manifest.json"
            echo ""
            echo "Options:"
            echo "  --since DATE    Check changes after this date (ISO 8601)"
            echo "  --verbose       Show commit messages, not just counts"
            echo "  --manifest      Use manifest for per-file upstream change detection"
            echo "  --diff          With --manifest: show actual diffs for changed files"
            echo "  --help          Show this help"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Check prerequisites
if ! command -v gh &>/dev/null; then
    echo -e "${RED}Error: gh CLI required. Install: https://cli.github.com/${NC}"
    exit 1
fi

if ! gh auth status &>/dev/null 2>&1; then
    echo -e "${RED}Error: gh not authenticated. Run: gh auth login${NC}"
    exit 1
fi

# ─────────────────────────────────────────────────────────────
# Manifest Mode: per-file upstream change detection
# ─────────────────────────────────────────────────────────────
if [[ "$MANIFEST_MODE" == "true" ]]; then
    if ! command -v jq &>/dev/null; then
        echo -e "${RED}Error: jq required for manifest mode. Install: sudo apt install jq${NC}"
        exit 1
    fi

    if [[ ! -f "$MANIFEST_FILE" ]]; then
        echo -e "${RED}Error: Manifest not found at $MANIFEST_FILE${NC}"
        echo -e "Run the audit to generate the manifest first."
        exit 1
    fi

    TOTAL_FILES=$(jq '.files | length' "$MANIFEST_FILE")
    TOTAL_ADOPTED=$(jq '[.files[] | select(.verdict == "Adopt")] | length' "$MANIFEST_FILE")
    TOTAL_ADAPTED=$(jq '[.files[] | select(.verdict == "Adapt")] | length' "$MANIFEST_FILE")
    ECC_SHA=$(jq -r '._stats.eccHeadAtAdoption' "$MANIFEST_FILE")

    echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  Manifest-Based Upstream Sync Check                 ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Manifest: ${CYAN}${TOTAL_FILES}${NC} tracked files (${TOTAL_ADOPTED} adopted, ${TOTAL_ADAPTED} adapted)"
    echo -e "  Adapted from ECC SHA: ${CYAN}${ECC_SHA}${NC}"
    echo ""

    # Group files by source repo
    SOURCES=$(jq -r '[.files[].source] | unique[]' "$MANIFEST_FILE")

    changed_count=0
    uptodate_count=0
    error_count=0

    for source in $SOURCES; do
        echo -e "${CYAN}━━━ Checking ${source} ━━━${NC}"

        # Get adapted SHA for this source (use first file's SHA as baseline)
        ADAPTED_SHA=$(jq -r "[.files[] | select(.source == \"${source}\")] | .[0].adaptedFromSha" "$MANIFEST_FILE")

        # Get current HEAD SHA
        CURRENT_HEAD=$(gh api "repos/${source}/commits/HEAD" --jq '.sha' 2>/dev/null | head -c 7)
        if [[ -z "$CURRENT_HEAD" ]]; then
            echo -e "  ${RED}Could not reach repo${NC}"
            error_count=$((error_count + 1))
            echo ""
            continue
        fi

        echo -e "  Adapted from: ${ADAPTED_SHA}  Current HEAD: ${CURRENT_HEAD}"

        if [[ "$ADAPTED_SHA" == "$CURRENT_HEAD" ]] || [[ "${ADAPTED_SHA:0:7}" == "${CURRENT_HEAD:0:7}" ]]; then
            SOURCE_COUNT=$(jq "[.files[] | select(.source == \"${source}\")] | length" "$MANIFEST_FILE")
            echo -e "  ${GREEN}All ${SOURCE_COUNT} files up to date (no upstream commits since adoption)${NC}"
            uptodate_count=$((uptodate_count + SOURCE_COUNT))
            echo ""
            continue
        fi

        # Get files changed between our SHA and current HEAD
        CHANGED_FILES=$(gh api "repos/${source}/compare/${ADAPTED_SHA}...HEAD" \
            --jq '.files[].filename' 2>/dev/null || echo "ERROR")

        if [[ "$CHANGED_FILES" == "ERROR" ]]; then
            echo -e "  ${RED}Could not compare commits${NC}"
            error_count=$((error_count + 1))
            echo ""
            continue
        fi

        # Cross-reference with manifest
        SOURCE_FILES=$(jq -r ".files | to_entries[] | select(.value.source == \"${source}\") | \"\(.key)|\(.value.sourcePath)|\(.value.verdict)\"" "$MANIFEST_FILE")

        source_changed=0
        source_uptodate=0

        while IFS='|' read -r local_path source_path verdict; do
            [[ -z "$local_path" ]] && continue

            if echo "$CHANGED_FILES" | grep -qF "$source_path"; then
                echo -e "  ${YELLOW}⚠ CHANGED${NC}  ${local_path}"
                echo -e "            Source: ${source_path} (${verdict})"
                source_changed=$((source_changed + 1))

                if [[ "$SHOW_DIFF" == "true" ]]; then
                    echo -e "            ${BLUE}--- Upstream diff ---${NC}"
                    # Fetch old and new versions, show diff
                    OLD_CONTENT=$(gh api "repos/${source}/contents/${source_path}?ref=${ADAPTED_SHA}" \
                        -H 'Accept: application/vnd.github.raw' 2>/dev/null || echo "")
                    NEW_CONTENT=$(gh api "repos/${source}/contents/${source_path}" \
                        -H 'Accept: application/vnd.github.raw' 2>/dev/null || echo "")
                    if [[ -n "$OLD_CONTENT" ]] && [[ -n "$NEW_CONTENT" ]]; then
                        diff <(echo "$OLD_CONTENT") <(echo "$NEW_CONTENT") | head -30 | sed 's/^/            /'
                        echo -e "            ${BLUE}--- (truncated to 30 lines) ---${NC}"
                    fi
                    echo ""
                fi
            else
                source_uptodate=$((source_uptodate + 1))
            fi
        done <<< "$SOURCE_FILES"

        changed_count=$((changed_count + source_changed))
        uptodate_count=$((uptodate_count + source_uptodate))

        if [[ "$source_changed" -eq 0 ]]; then
            echo -e "  ${GREEN}All ${source_uptodate} files up to date${NC}"
        else
            echo -e "  ${YELLOW}${source_changed} changed${NC}, ${GREEN}${source_uptodate} up to date${NC}"
        fi
        echo ""
    done

    # Summary
    echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
    if [[ "$changed_count" -eq 0 ]]; then
        echo -e "${BOLD}║  ${GREEN}All ${uptodate_count} tracked files up to date${NC}${BOLD}                 ║${NC}"
    else
        printf "${BOLD}║  ${YELLOW}%d file(s) changed upstream${NC}${BOLD}, ${GREEN}%d up to date${NC}${BOLD}         ║${NC}\n" "$changed_count" "$uptodate_count"
    fi
    if [[ "$error_count" -gt 0 ]]; then
        echo -e "${BOLD}║  ${RED}${error_count} source(s) unreachable${NC}${BOLD}                            ║${NC}"
    fi
    echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ "$changed_count" -gt 0 ]]; then
        echo -e "Next steps:"
        echo -e "  1. Review changed files with: ${CYAN}$0 --manifest --diff${NC}"
        echo -e "  2. Update local files and bump adaptedFromSha in manifest"
        echo -e "  3. Run CI validators: ${CYAN}node scripts/ci/validate-*.js${NC}"
    fi

    exit 0
fi

# ─────────────────────────────────────────────────────────────
# Repo-Level Mode (default): commit counts for all 5 upstreams
# ─────────────────────────────────────────────────────────────

echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  Upstream Sync Check — since ${SINCE}            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

total_changes=0

# ─────────────────────────────────────────────────────────────
# 1. Superpowers (obra/superpowers)
# ─────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ 1. Superpowers (obra/superpowers) ━━━${NC}"
echo -e "   Integration: Plugin marketplace install"
echo -e "   What we use: 14 workflow skills (TDD, debugging, brainstorming, etc.)"
echo -e "   Local patches: EnterPlanMode guard in brainstorming/SKILL.md"
echo ""

# Current installed version
INSTALLED_VERSION=""
if [[ -d "$HOME/.claude/plugins/cache/superpowers-marketplace/superpowers" ]]; then
    INSTALLED_VERSION=$(ls "$HOME/.claude/plugins/cache/superpowers-marketplace/superpowers/" 2>/dev/null | sort -V | tail -1)
    echo -e "   Installed version: ${GREEN}${INSTALLED_VERSION:-unknown}${NC}"
fi

# Latest release
LATEST_RELEASE=$(gh api repos/obra/superpowers/releases/latest --jq '.tag_name // "none"' 2>/dev/null || echo "no releases")
echo -e "   Latest release:    ${BLUE}${LATEST_RELEASE}${NC}"

# Compare versions (marketplace versions may be ahead of GitHub releases)
SP_INSTALLED_NUM="${INSTALLED_VERSION//v/}"
SP_LATEST_NUM="${LATEST_RELEASE//v/}"
if [[ "$SP_INSTALLED_NUM" == "$SP_LATEST_NUM" ]]; then
    echo -e "   Status: ${GREEN}Up to date${NC}"
elif [[ "$(printf '%s\n' "$SP_INSTALLED_NUM" "$SP_LATEST_NUM" | sort -V | tail -1)" == "$SP_INSTALLED_NUM" ]]; then
    echo -e "   Status: ${GREEN}Installed is ahead of latest release (marketplace pre-release)${NC}"
else
    echo -e "   Status: ${YELLOW}Update available${NC}"
    echo -e "   ${YELLOW}⚠ Re-apply EnterPlanMode patch after updating${NC}"
    total_changes=$((total_changes + 1))
fi

# Recent commits
SP_COMMITS=$(gh api "repos/obra/superpowers/commits?since=${SINCE}T00:00:00Z&per_page=100" --jq 'length' 2>/dev/null || echo "0")
echo -e "   Commits since ${SINCE}: ${BOLD}${SP_COMMITS}${NC}"

if [[ "$VERBOSE" == "true" ]] && [[ "$SP_COMMITS" -gt 0 ]]; then
    echo ""
    gh api "repos/obra/superpowers/commits?since=${SINCE}T00:00:00Z&per_page=10" \
        --jq '.[] | "     \(.commit.author.date | split("T")[0]) \(.commit.message | split("\n")[0])"' 2>/dev/null || true
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 2. ECC (affaan-m/everything-claude-code)
# ─────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ 2. ECC (affaan-m/everything-claude-code) ━━━${NC}"
echo -e "   Integration: Manually adapted (deep — hooks, agents, commands, scripts)"
echo -e "   What we use: Observer daemon, session hooks, multi-model, eval, orchestrate"
echo -e "   Divergences: 11 observer bug fixes, restructured hooks, authority hierarchy"
echo ""

ECC_COMMITS=$(gh api "repos/affaan-m/everything-claude-code/commits?since=${SINCE}T00:00:00Z&per_page=100" --jq 'length' 2>/dev/null || echo "error")
if [[ "$ECC_COMMITS" == "error" ]]; then
    echo -e "   ${RED}Could not reach repo (may be private or renamed)${NC}"
else
    echo -e "   Commits since ${SINCE}: ${BOLD}${ECC_COMMITS}${NC}"
    if [[ "$ECC_COMMITS" -gt 0 ]]; then
        total_changes=$((total_changes + 1))
        echo -e "   ${YELLOW}⚠ Review for: new skills, new agents, hook improvements${NC}"
        echo -e "   ${YELLOW}  Skip: bugs we already fixed, structural differences${NC}"
    fi
fi

if [[ "$VERBOSE" == "true" ]] && [[ "$ECC_COMMITS" -gt 0 ]] && [[ "$ECC_COMMITS" != "error" ]]; then
    echo ""
    echo -e "   Key directories to watch:"
    for dir in skills commands agents hooks; do
        count=$(gh api "repos/affaan-m/everything-claude-code/commits?since=${SINCE}T00:00:00Z&path=${dir}&per_page=100" \
            --jq 'length' 2>/dev/null || echo "?")
        echo -e "     ${dir}/: ${count} commits"
    done
    echo ""
    echo -e "   Recent commits:"
    gh api "repos/affaan-m/everything-claude-code/commits?since=${SINCE}T00:00:00Z&per_page=10" \
        --jq '.[] | "     \(.commit.author.date | split("T")[0]) \(.commit.message | split("\n")[0])"' 2>/dev/null || true
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 3. Anthropic Official (anthropics/claude-plugins-official)
# ─────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ 3. Anthropic Official (anthropics/claude-plugins-official) ━━━${NC}"
echo -e "   Integration: Manually copied skills"
echo -e "   What we use: frontend-design skill"
echo ""

ANTH_COMMITS=$(gh api "repos/anthropics/claude-plugins-official/commits?since=${SINCE}T00:00:00Z&per_page=100" --jq 'length' 2>/dev/null || echo "error")
if [[ "$ANTH_COMMITS" == "error" ]]; then
    echo -e "   ${RED}Could not reach repo (may be private)${NC}"
else
    echo -e "   Commits since ${SINCE}: ${BOLD}${ANTH_COMMITS}${NC}"
    if [[ "$ANTH_COMMITS" -gt 0 ]]; then
        total_changes=$((total_changes + 1))
        echo -e "   ${YELLOW}⚠ Check for new official skills or skill updates${NC}"
    else
        echo -e "   Status: ${GREEN}No changes${NC}"
    fi
fi

if [[ "$VERBOSE" == "true" ]] && [[ "$ANTH_COMMITS" -gt 0 ]] && [[ "$ANTH_COMMITS" != "error" ]]; then
    echo ""
    gh api "repos/anthropics/claude-plugins-official/commits?since=${SINCE}T00:00:00Z&per_page=10" \
        --jq '.[] | "     \(.commit.author.date | split("T")[0]) \(.commit.message | split("\n")[0])"' 2>/dev/null || true
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 4. Task Master AI (npm: task-master-ai)
# ─────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ 4. Task Master AI (npm: task-master-ai) ━━━${NC}"
echo -e "   Integration: MCP server (npm global install)"
echo -e "   What we use: Task management, PRD parsing, complexity analysis, autopilot"
echo ""

# Current installed version
INSTALLED_TM=$(npm list -g task-master-ai --depth=0 2>/dev/null | grep task-master-ai | sed 's/.*@//' || echo "not installed")
echo -e "   Installed version: ${GREEN}${INSTALLED_TM}${NC}"

# Latest npm version
LATEST_TM=$(npm view task-master-ai version 2>/dev/null || echo "unknown")
echo -e "   Latest on npm:     ${BLUE}${LATEST_TM}${NC}"

if [[ "$INSTALLED_TM" == "$LATEST_TM" ]]; then
    echo -e "   Status: ${GREEN}Up to date${NC}"
else
    echo -e "   Status: ${YELLOW}Update available${NC}"
    echo -e "   ${YELLOW}⚠ Review changelog for breaking changes before updating${NC}"
    echo -e "   ${YELLOW}  Update: npm install -g task-master-ai@latest${NC}"
    total_changes=$((total_changes + 1))
fi

# Check GitHub for recent activity
TM_COMMITS=$(gh api "repos/eyaltoledano/claude-task-master/commits?since=${SINCE}T00:00:00Z&per_page=100" --jq 'length' 2>/dev/null || echo "?")
echo -e "   GitHub commits since ${SINCE}: ${BOLD}${TM_COMMITS}${NC}"

if [[ "$VERBOSE" == "true" ]] && [[ "$TM_COMMITS" -gt 0 ]] && [[ "$TM_COMMITS" != "?" ]]; then
    echo ""
    gh api "repos/eyaltoledano/claude-task-master/commits?since=${SINCE}T00:00:00Z&per_page=10" \
        --jq '.[] | "     \(.commit.author.date | split("T")[0]) \(.commit.message | split("\n")[0])"' 2>/dev/null || true
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 5. wshobson/agents (Plugin Marketplace)
# ─────────────────────────────────────────────────────────────
echo -e "${CYAN}━━━ 5. Plugin Marketplace (wshobson/agents) ━━━${NC}"
echo -e "   Integration: Plugin source for manage-plugins.sh"
echo -e "   What we use: Plugin registry, downloadable domain-specific agents/skills"
echo ""

WS_COMMITS=$(gh api "repos/wshobson/agents/commits?since=${SINCE}T00:00:00Z&per_page=100" --jq 'length' 2>/dev/null || echo "error")
if [[ "$WS_COMMITS" == "error" ]]; then
    echo -e "   ${RED}Could not reach repo (may be private or renamed)${NC}"
else
    echo -e "   Commits since ${SINCE}: ${BOLD}${WS_COMMITS}${NC}"
    if [[ "$WS_COMMITS" -gt 0 ]]; then
        total_changes=$((total_changes + 1))
        echo -e "   ${YELLOW}⚠ Check for new plugins or updates to installed plugins${NC}"
    else
        echo -e "   Status: ${GREEN}No changes${NC}"
    fi
fi

if [[ "$VERBOSE" == "true" ]] && [[ "$WS_COMMITS" -gt 0 ]] && [[ "$WS_COMMITS" != "error" ]]; then
    echo ""
    gh api "repos/wshobson/agents/commits?since=${SINCE}T00:00:00Z&per_page=10" \
        --jq '.[] | "     \(.commit.author.date | split("T")[0]) \(.commit.message | split("\n")[0])"' 2>/dev/null || true
fi
echo ""

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
if [[ "$total_changes" -eq 0 ]]; then
    echo -e "${BOLD}║  ${GREEN}All upstreams up to date${NC}${BOLD}                              ║${NC}"
else
    echo -e "${BOLD}║  ${YELLOW}${total_changes} upstream(s) have changes to review${NC}${BOLD}              ║${NC}"
fi
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Update the --since date after reviewing: ${CYAN}${0} --since $(date +%Y-%m-%d)${NC}"
echo ""
echo -e "${BOLD}Local patches to re-apply after updates:${NC}"
echo -e "  • Superpowers brainstorming/SKILL.md: EnterPlanMode prohibition (2 lines after HARD-GATE)"
echo ""
