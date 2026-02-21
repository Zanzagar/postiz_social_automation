# Project Health Check

Run a comprehensive health check on the project to ensure everything is properly configured.

## Instructions

Perform the following checks and report results:

### 1. Template Configuration

```bash
# Check template status
./scripts/sync-template.sh status
```

Report:
- Template source (local/git)
- Last sync date
- Files needing updates

### 2. CLAUDE.md Status

```bash
# Check if customized
grep -q "\[PROJECT_NAME\]" CLAUDE.md && echo "NOT CUSTOMIZED" || echo "Customized"
```

If not customized, prompt: "CLAUDE.md still has placeholder values. Run /setup to configure."

### 3. Taskmaster Status

```bash
# Check initialization
ls -la .taskmaster/ 2>/dev/null || echo "Not initialized"

# Check for tasks
task-master list 2>/dev/null | head -10
```

Report:
- Initialized: Yes/No
- Task count
- Current/next task

### 4. Git Status

```bash
# Branch
git branch --show-current

# Status
git status --short

# Remote
git remote -v
```

Report:
- Current branch (warn if on main/master)
- Uncommitted changes count
- Remote configured: Yes/No

### 5. Code Quality

```bash
# Run linter (if available)
ruff check src/ tests/ 2>/dev/null || echo "Linter not available or no src/"

# Run type checker (if available)
mypy src/ 2>/dev/null || echo "Type checker not available"

# Run tests (quick)
pytest -q --tb=no 2>/dev/null || echo "Tests not available"
```

Report:
- Linting: Pass/Fail/N/A
- Type checking: Pass/Fail/N/A
- Tests: Pass/Fail/N/A

### 6. Dependencies

```bash
# Python
pip list --outdated 2>/dev/null | head -10

# Node
npm outdated 2>/dev/null | head -10
```

Report:
- Outdated packages count
- Critical updates (security)

### 7. MCP Configuration & Budget

```bash
# Check project MCP config
cat .claude/mcp-project.json 2>/dev/null || echo "Not configured"

# Check active MCPs
claude mcp list 2>/dev/null | grep -c "✓ Connected"

# Run MCP budget audit (10/80 rule)
./scripts/manage-mcps.sh audit 2>/dev/null
```

Report:
- MCPs configured: Yes/No
- Active MCP count
- Estimated token overhead
- Budget status (10/80 rule):
  - Under 8 MCPs / 60 tools → Healthy
  - 8-10 MCPs / 60-80 tools → Consider optimizing
  - Over 10 MCPs / 80 tools → Over budget

If `manage-mcps.sh` is not available or fails, fall back to basic MCP count only.

### 8. Context Budget Summary

```bash
# Get token usage estimate
./scripts/manage-mcps.sh tokens 2>/dev/null
```

Report:
- MCP token overhead estimate
- Budget compliance (10/80 rule)
- Recommendation if over budget: "Run `./scripts/manage-mcps.sh select` to optimize"

If the script is unavailable, skip this section with note: "Install manage-mcps.sh for budget tracking"

### 10. AgentShield Status

Check if AgentShield has been run recently:

```bash
# Check for AgentShield marker
ASHIELD_LAST_RUN=".claude/agentshield-last-run"
if [ -f "$ASHIELD_LAST_RUN" ]; then
    LAST_SCAN=$(cat "$ASHIELD_LAST_RUN")
    SCAN_AGE=$(( ($(date +%s) - LAST_SCAN) / 86400 ))
    if [ "$SCAN_AGE" -gt 7 ]; then
        echo "AgentShield: Stale (${SCAN_AGE} days ago)"
    else
        echo "AgentShield: Recent (${SCAN_AGE} days ago)"
    fi
else
    echo "AgentShield: Never run"
fi
```

Report:
- Recent (<7 days): Healthy
- Stale (>7 days): Warning — suggest re-scan
- Never run: Warning — suggest initial scan

After running AgentShield, update the marker:
```bash
date +%s > .claude/agentshield-last-run
```

### 11. Hooks Status

```bash
# Check if hooks enabled
cat .claude/settings.local.json 2>/dev/null | jq '.hooks' || echo "Not configured"
```

Report:
- Hooks enabled: Yes/No
- Which hooks are active

## Output Format

Present results as a health report:

```
╔════════════════════════════════════════════════════════════╗
║                    PROJECT HEALTH CHECK                     ║
╠════════════════════════════════════════════════════════════╣
║ Category              │ Status      │ Notes                 ║
╠───────────────────────┼─────────────┼───────────────────────╣
║ Template              │ ✓ Synced    │ v2.0.0               ║
║ CLAUDE.md             │ ✓ Customized│                       ║
║ Taskmaster            │ ✓ Active    │ 5 tasks pending       ║
║ Git                   │ ⚠ Warning   │ On main branch        ║
║ Linting               │ ✓ Pass      │                       ║
║ Tests                 │ ✗ Failing   │ 2 failures            ║
║ Dependencies          │ ⚠ Outdated  │ 3 packages            ║
║ MCPs                  │ ✓ Configured│ ~7,500 tokens         ║
║ Context Budget        │ ✓ Healthy   │ 4/10 MCPs, 35/80 tools║
║ AgentShield           │ ⚠ Stale     │ Last scan: 14 days ago║
║ Hooks                 │ ○ Optional  │ Not enabled           ║
╚════════════════════════════════════════════════════════════╝

Summary: 7 passed, 3 warnings, 1 failing

Recommendations:
1. Fix failing tests before continuing
2. Create a feature branch: git checkout -b feature/...
3. Update outdated dependencies: pip install --upgrade ...
```

## Actionable Recommendations

Based on findings, suggest specific fixes:

| Issue | Command |
|-------|---------|
| Not on feature branch | `git checkout -b feature/current-work` |
| Uncommitted changes | `/commit` |
| Failing tests | `pytest -v` to see details |
| Linting errors | `ruff check --fix src/` |
| MCPs not configured | `/mcps` |
| MCP budget exceeded | `./scripts/manage-mcps.sh select` |
| Hooks not enabled | `/settings safe` |
| AgentShield never run | `npx ecc-agentshield scan` |
| AgentShield scan stale | `npx ecc-agentshield scan` (re-scan) |
| CLAUDE.md not customized | `/setup` |
