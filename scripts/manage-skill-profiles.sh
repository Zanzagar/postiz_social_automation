#!/usr/bin/env bash
# manage-skill-profiles.sh — Manage skill loading profiles to control context overhead
#
# Skills consume ~300 tokens each in metadata (always loaded). Language-specific
# skills (Django, Spring Boot, Go, etc.) are wasted context for projects that
# don't use those languages. Profiles load only relevant skills.
#
# Usage:
#   ./scripts/manage-skill-profiles.sh set <profile|categories>
#   ./scripts/manage-skill-profiles.sh list
#   ./scripts/manage-skill-profiles.sh current
#   ./scripts/manage-skill-profiles.sh categories
#
# Examples:
#   ./scripts/manage-skill-profiles.sh set python       # Universal + Python + DB
#   ./scripts/manage-skill-profiles.sh set minimal       # Universal only
#   ./scripts/manage-skill-profiles.sh set all           # Everything
#   ./scripts/manage-skill-profiles.sh set python,frontend  # Custom combo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_AVAILABLE="$PROJECT_DIR/.claude/skills-available"
SKILLS_ACTIVE="$PROJECT_DIR/.claude/skills"

# Colors
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; RED=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

# ─── Skill Category Definitions ──────────────────────────────────────────────

declare -A CATEGORIES

# Core workflow skills (language-agnostic)
CATEGORIES[universal]="agentic-engineering ai-regression-testing api-design autonomous-loops backend-patterns benchmark blueprint claude-api code-review codebase-onboarding coding-standards context-budget continuous-learning-v2 cost-aware-llm-pipeline debugging deep-research design-system eval-harness eval-metrics git-recovery iterative-retrieval regex-vs-llm-structured-text rules-distill safety-guard search-first security-review security-scan skill-stocktake strategic-compact tdd-workflow verification-loop"

# Language ecosystems
CATEGORIES[python]="python-patterns python-testing python-data-science python-django django-patterns django-security django-tdd django-verification pytorch-patterns"
CATEGORIES[java]="java-springboot java-coding-standards jpa-patterns spring-boot-tdd spring-boot-security springboot-verification"
CATEGORIES[go]="golang-patterns golang-testing"
CATEGORIES[typescript]="typescript-patterns bun-runtime nextjs-turbopack nuxt4-patterns"
CATEGORIES[cpp]="cpp-testing cpp-coding-standards"
CATEGORIES[kotlin]="kotlin-patterns kotlin-testing kotlin-coroutines-flows kotlin-exposed-patterns kotlin-ktor-patterns"
CATEGORIES[rust]="rust-patterns rust-testing"
CATEGORIES[swift]="swift-actor-persistence swift-concurrency-6-2 swift-protocol-di-testing swiftui-patterns"
CATEGORIES[perl]="perl-patterns perl-security perl-testing"
CATEGORIES[laravel]="laravel-patterns laravel-security laravel-tdd laravel-verification"

# Domain categories
CATEGORIES[frontend]="frontend-design frontend-patterns e2e-testing webapp-testing web-artifacts-builder browser-qa click-path-audit frontend-slides liquid-glass-design"
CATEGORIES[mobile]="android-clean-architecture compose-multiplatform-patterns flutter-dart-code-review foundation-models-on-device"
CATEGORIES[database]="database-patterns database-migrations postgresql-patterns clickhouse-io"
CATEGORIES[infra]="docker-patterns deployment-patterns dmux-workflows"
CATEGORIES[ops]="incident-runbook-templates on-call-handoff-patterns postmortem-writing distributed-tracing grafana-dashboards prometheus-configuration slo-implementation gitops-workflow helm-chart-scaffolding k8s-manifest-generator k8s-security-policies screen-reader-testing wcag-audit-patterns"
CATEGORIES[creative]="algorithmic-art canvas-design theme-factory video-editing"
CATEGORIES[authoring]="doc-coauthoring mcp-builder skill-creator architecture-decision-records"
CATEGORIES[ai-ops]="agent-eval agent-harness-construction ai-first-engineering canary-watch continuous-agent-loop enterprise-agent-ops mcp-server-patterns prompt-optimizer santa-method plankton-code-quality content-hash-cache-pattern"
CATEGORIES[media]="fal-ai-media videodb x-api exa-search"
CATEGORIES[research]="article-writing content-engine crosspost deep-research investor-materials investor-outreach market-research product-lens"
CATEGORIES[industry]="carrier-relationship-management customs-trade-compliance energy-procurement inventory-demand-planning logistics-exception-management nutrient-document-processing production-scheduling quality-nonconformance returns-reverse-logistics visa-doc-translate"
CATEGORIES[meta]="claude-devfleet data-scraper-agent documentation-lookup nanoclaw-repl project-guidelines-example ralphinho-rfc-pipeline skill-comply team-builder"

# ─── Named Profile Definitions ───────────────────────────────────────────────

declare -A PROFILES
PROFILES[minimal]="universal"
PROFILES[python]="universal python database"
PROFILES[java]="universal java database"
PROFILES[go]="universal go"
PROFILES[kotlin]="universal kotlin java database"
PROFILES[rust]="universal rust"
PROFILES[swift]="universal swift mobile"
PROFILES[typescript]="universal typescript frontend"
PROFILES[cpp]="universal cpp"
PROFILES[laravel]="universal laravel database"
PROFILES[fullstack]="universal python typescript frontend database infra"
PROFILES[web]="universal python typescript frontend database infra"
PROFILES[mobile-dev]="universal kotlin swift mobile"
PROFILES[ai-engineer]="universal python ai-ops research"
PROFILES[ops]="universal ops infra"
PROFILES[all]="universal python java go typescript cpp kotlin rust swift perl laravel frontend mobile database infra ops creative authoring ai-ops media research industry meta"

# ─── Functions ────────────────────────────────────────────────────────────────

get_skills_for_categories() {
    local cats="$1"
    local skills=""
    for cat in $cats; do
        if [ -n "${CATEGORIES[$cat]:-}" ]; then
            skills="$skills ${CATEGORIES[$cat]}"
        fi
    done
    echo "$skills" | tr ' ' '\n' | sort -u | tr '\n' ' '
}

count_tokens() {
    local total=0
    for skill_dir in "$SKILLS_AVAILABLE"/*/; do
        name=$(basename "$skill_dir")
        if echo " $1 " | grep -q " $name "; then
            desc=$(sed -n '/^description:/,/^[a-z]*:/{ /^description:/p; /^  /p }' "$skill_dir/SKILL.md" 2>/dev/null)
            total=$((total + ${#desc} / 4))
        fi
    done
    echo "$total"
}

# ─── Language → Related Components Map ────────────────────────────────────────

# Maps profile categories to related commands, agents, and rule directories
# Format: "commands|agents|rules-dir"
declare -A RELATED
RELATED[python]="/python-review|python-reviewer|python"
RELATED[java]="/gradle-build|java-reviewer,java-build-resolver|java"
RELATED[go]="/go-build,/go-review,/go-test|go-reviewer,go-build-resolver|golang"
RELATED[kotlin]="/kotlin-build,/kotlin-review,/kotlin-test,/gradle-build|kotlin-reviewer,kotlin-build-resolver|kotlin"
RELATED[rust]="/rust-build,/rust-review,/rust-test|rust-reviewer,rust-build-resolver|rust"
RELATED[cpp]="/cpp-build,/cpp-review,/cpp-test|cpp-reviewer,cpp-build-resolver|cpp"
RELATED[typescript]="—|typescript-reviewer|typescript"
RELATED[swift]="—|—|swift"
RELATED[perl]="—|—|perl"
RELATED[laravel]="—|—|php"
RELATED[frontend]="/e2e,/accessibility-audit|ui-visual-validator,e2e-runner|frontend"
RELATED[ops]="/incident-response,/monitor-setup,/slo-implement,/smart-fix|incident-responder,devops-troubleshooter,observability-engineer,kubernetes-architect|—"
RELATED[database]="—|database-reviewer,database-optimizer|—"
RELATED[mobile]="—|flutter-reviewer|—"

show_related_components() {
    local profile_name="$1"
    local cats=""

    # Resolve profile to categories
    if [ -n "${PROFILES[$profile_name]:-}" ]; then
        cats="${PROFILES[$profile_name]}"
    elif [[ "$profile_name" == custom:* ]]; then
        cats="universal $(echo "$profile_name" | sed 's/^custom://' | tr ',' ' ')"
    else
        return
    fi

    local has_related=false
    local related_cmds="" related_agents="" related_rules=""

    for cat in $cats; do
        [ "$cat" = "universal" ] && continue
        local rel="${RELATED[$cat]:-}"
        [ -z "$rel" ] && continue

        local cmds agents rules_dir
        cmds=$(echo "$rel" | cut -d'|' -f1)
        agents=$(echo "$rel" | cut -d'|' -f2)
        rules_dir=$(echo "$rel" | cut -d'|' -f3)

        [ "$cmds" != "—" ] && [ -n "$cmds" ] && related_cmds="$related_cmds $cmds"
        [ "$agents" != "—" ] && [ -n "$agents" ] && related_agents="$related_agents $agents"
        [ "$rules_dir" != "—" ] && [ -n "$rules_dir" ] && related_rules="$related_rules $rules_dir"
    done

    # Clean up and deduplicate
    related_cmds=$(echo "$related_cmds" | tr ',' '\n' | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ' || true)
    related_agents=$(echo "$related_agents" | tr ',' '\n' | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ' || true)
    related_rules=$(echo "$related_rules" | tr ',' '\n' | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ' || true)

    if [ -n "$related_cmds" ] || [ -n "$related_agents" ] || [ -n "$related_rules" ]; then
        printf "\n${BOLD}Your toolkit:${NC}\n"
        [ -n "$related_cmds" ] && printf "  ${BLUE}Commands:${NC}  %s\n" "$related_cmds"
        [ -n "$related_agents" ] && printf "  ${BLUE}Agents:${NC}    %s\n" "$related_agents"
        [ -n "$related_rules" ] && printf "  ${BLUE}Rules:${NC}     %s\n" "$(echo $related_rules | sed 's/ /, /g') (auto-load via paths:)"
    fi

    # Always show universal toolkit
    printf "  ${BLUE}Universal:${NC} /plan /tdd /test /lint /commit /pr /code-review /verify /brainstorm\n"
}

activate_skills() {
    local skills="$1"
    local profile_name="$2"

    # Create active directory if needed
    mkdir -p "$SKILLS_ACTIVE"

    # Remove existing symlinks (only symlinks, preserve any real files)
    find "$SKILLS_ACTIVE" -maxdepth 1 -type l -delete 2>/dev/null

    # Create symlinks for active skills
    local count=0
    for skill in $skills; do
        if [ -d "$SKILLS_AVAILABLE/$skill" ]; then
            ln -sf "../skills-available/$skill" "$SKILLS_ACTIVE/$skill"
            count=$((count + 1))
        fi
    done

    # Save profile name
    echo "$profile_name" > "$SKILLS_ACTIVE/.profile"

    local tokens
    tokens=$(count_tokens "$skills")
    printf "${GREEN}✓${NC} Activated ${BOLD}%d${NC} skills (profile: ${BOLD}%s${NC}, ~%d metadata tokens)\n" "$count" "$profile_name" "$tokens"

    # Show related components (commands, agents, rules)
    show_related_components "$profile_name"
}

cmd_set() {
    local input="${1:-}"
    if [ -z "$input" ]; then
        printf "${RED}Error:${NC} specify a profile or categories\n"
        printf "Usage: $0 set <profile|cat1,cat2,...>\n"
        printf "Run '$0 list' to see available profiles\n"
        exit 1
    fi

    # Check if it's a named profile
    if [ -n "${PROFILES[$input]:-}" ]; then
        local cats="${PROFILES[$input]}"
        local skills
        skills=$(get_skills_for_categories "$cats")
        activate_skills "$skills" "$input"
        return
    fi

    # Otherwise treat as comma-separated categories
    local cats
    cats=$(echo "$input" | tr ',' ' ')

    # Always include universal
    if ! echo " $cats " | grep -q " universal "; then
        cats="universal $cats"
    fi

    # Validate categories
    for cat in $cats; do
        if [ -z "${CATEGORIES[$cat]:-}" ]; then
            printf "${RED}Error:${NC} unknown category '$cat'\n"
            printf "Run '$0 categories' to see available categories\n"
            exit 1
        fi
    done

    local skills
    skills=$(get_skills_for_categories "$cats")
    activate_skills "$skills" "custom:$input"
}

cmd_list() {
    printf "${BOLD}Available Skill Profiles${NC}\n"
    printf "════════════════════════════════════════════\n\n"

    local current
    current=$(cat "$SKILLS_ACTIVE/.profile" 2>/dev/null || echo "unknown")

    for profile in minimal python java go typescript cpp fullstack all; do
        local cats="${PROFILES[$profile]}"
        local skills
        skills=$(get_skills_for_categories "$cats")
        local count
        count=$(echo "$skills" | wc -w)
        local tokens
        tokens=$(count_tokens "$skills")

        local marker=""
        if [ "$profile" = "$current" ]; then
            marker=" ${GREEN}← active${NC}"
        fi

        printf "  ${BOLD}%-12s${NC} %2d skills  ~%5d tokens  (%s)%b\n" \
            "$profile" "$count" "$tokens" "$cats" "$marker"
    done

    printf "\n${YELLOW}Custom:${NC} $0 set python,frontend,database\n"
    printf "(always includes 'universal' automatically)\n"
}

cmd_current() {
    local profile
    profile=$(cat "$SKILLS_ACTIVE/.profile" 2>/dev/null || echo "none")
    local count
    count=$(find "$SKILLS_ACTIVE" -maxdepth 1 -type l 2>/dev/null | wc -l)

    printf "Profile: ${BOLD}%s${NC}\n" "$profile"
    printf "Active skills: %d\n" "$count"

    if [ "$count" -gt 0 ]; then
        printf "\nActive:\n"
        for link in "$SKILLS_ACTIVE"/*/; do
            [ -L "${link%/}" ] && printf "  %s\n" "$(basename "$link")"
        done
    fi
}

cmd_categories() {
    printf "${BOLD}Skill Categories${NC}\n"
    printf "════════════════════════════════════════════\n\n"

    for cat in universal python java go typescript cpp kotlin rust swift perl laravel frontend mobile database infra ops creative authoring ai-ops media research industry meta; do
        local skills="${CATEGORIES[$cat]}"
        local count
        count=$(echo "$skills" | wc -w)
        local tokens
        tokens=$(count_tokens "$skills")
        printf "  ${BLUE}%-12s${NC} %2d skills  ~%5d tokens\n" "$cat" "$count" "$tokens"
        for skill in $skills; do
            printf "    %s\n" "$skill"
        done
        printf "\n"
    done
}

# ─── Main ─────────────────────────────────────────────────────────────────────

if [ ! -d "$SKILLS_AVAILABLE" ]; then
    printf "${RED}Error:${NC} %s not found. Are you in the project root?\n" "$SKILLS_AVAILABLE"
    exit 1
fi

cmd_toolkit() {
    local profile
    profile=$(cat "$SKILLS_ACTIVE/.profile" 2>/dev/null || echo "none")

    if [ "$profile" = "none" ]; then
        printf "${RED}No profile set.${NC} Run: $0 set <profile>\n"
        return
    fi

    printf "${BOLD}Your Toolkit${NC} (profile: ${BOLD}%s${NC})\n" "$profile"
    printf "════════════════════════════════════════════\n"
    show_related_components "$profile"
    printf "\n"

    # Show active skill count
    local count
    count=$(find "$SKILLS_ACTIVE" -maxdepth 1 -type l 2>/dev/null | wc -l)
    printf "${BOLD}Active skills:${NC} %d\n" "$count"

    # Show all agents (always available)
    local agents_dir="$PROJECT_DIR/.claude/agents"
    if [ -d "$agents_dir" ]; then
        printf "${BOLD}Available agents:${NC} %d (always available regardless of profile)\n" "$(ls "$agents_dir"/*.md 2>/dev/null | wc -l)"
    fi

    # Show all commands
    local cmds_dir="$PROJECT_DIR/.claude/commands"
    if [ -d "$cmds_dir" ]; then
        printf "${BOLD}Available commands:${NC} %d (always available regardless of profile)\n" "$(ls "$cmds_dir"/*.md 2>/dev/null | wc -l)"
    fi

    # Show rules
    local rules_dir="$PROJECT_DIR/.claude/rules"
    if [ -d "$rules_dir" ]; then
        local core_rules lang_dirs
        core_rules=$(ls "$rules_dir"/*.md 2>/dev/null | wc -l)
        lang_dirs=$(ls -d "$rules_dir"/*/ 2>/dev/null | wc -l)
        printf "${BOLD}Rules:${NC} %d core (always) + %d language dirs (auto-load via paths:)\n" "$core_rules" "$lang_dirs"
    fi
}

case "${1:-help}" in
    set)      cmd_set "${2:-}" ;;
    list)     cmd_list ;;
    current)  cmd_current ;;
    toolkit)  cmd_toolkit ;;
    categories) cmd_categories ;;
    help|--help|-h)
        printf "Usage: $0 <command> [args]\n\n"
        printf "Commands:\n"
        printf "  set <profile|cats>  Activate a skill profile (minimal/python/java/go/fullstack/all)\n"
        printf "  list                Show available profiles with token costs\n"
        printf "  current             Show currently active profile\n"
        printf "  toolkit             Show your full toolkit (commands, agents, rules for active profile)\n"
        printf "  categories          Show all skill categories and their skills\n"
        ;;
    *)
        printf "${RED}Unknown command:${NC} $1\n"
        printf "Run '$0 help' for usage\n"
        exit 1
        ;;
esac
