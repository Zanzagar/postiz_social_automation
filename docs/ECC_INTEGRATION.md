# ECC Integration Guide

Features integrated from [Everything Claude Code](https://github.com/anthropics/ecc) patterns, adapted for this template.

## What Was Integrated

| Feature | Source | Files |
|---------|--------|-------|
| **Phase 1** | | |
| Token optimization presets | ECC settings patterns | `.claude/settings-presets.json` |
| Context management docs | ECC token guidance | `.claude/rules/context-management.md` |
| MCP discipline (10/80 rule) | ECC budget patterns | `scripts/manage-mcps.sh`, `docs/MCP_SETUP.md` |
| Session persistence | ECC session hooks | `.claude/hooks/session-end.sh`, `pre-compact.sh` |
| Session init reload | ECC continuity patterns | `.claude/hooks/session-init.sh` |
| Pre-compaction state | ECC state preservation | `.claude/hooks/pre-compact.sh` |
| Context injection modes | ECC mode patterns | `.claude/contexts/dev.md`, `review.md`, `research.md` |
| Python standards reorganization | ECC modular rules | `.claude/rules/python/coding-standards.md` |
| Agent definitions (4 core) | ECC agent patterns | `.claude/agents/` |
| Code review enhancement | ECC review patterns | `.claude/skills/code-review/SKILL.md` |
| Health check MCP audit | ECC budget monitoring | `.claude/commands/health.md` |
| **Phase 2** | | |
| AgentShield security scanning | ECC config security | `docs/SECURITY.md`, `/health` integration |
| 9 additional agents | ECC agent library | `.claude/agents/` (14 total) |
| 10 multi-language skills | ECC skill library | `.claude/skills/` (20 total after Phase 2) |
| Continuous learning v2 | ECC instinct patterns | `.claude/instincts/`, `/evolve` |
| Authority hierarchy | ECC rule precedence | `.claude/rules/authority-hierarchy.md` |
| Multi-agent orchestration | ECC pipeline patterns | `/orchestrate` command |
| Multi-model collaboration | ECC multi-model patterns | `/multi-plan`, `/multi-execute` |
| Verification pipeline | ECC quality patterns | `/verify` command |
| Quality eval tracking | ECC metrics patterns | `/eval` command, `.claude/evals/` |
| Skill auto-generation | ECC evolution patterns | `/skill-create` command |
| Architecture codemaps | ECC documentation patterns | `/update-codemaps`, `docs/CODEMAPS/` |
| Session checkpoints | ECC session patterns | `/checkpoint` command |
| Doc automation | ECC doc patterns | `/update-docs` command |
| TypeScript rules | ECC polyglot patterns | `.claude/rules/typescript/coding-standards.md` |
| Go rules | ECC polyglot patterns | `.claude/rules/golang/coding-standards.md` |
| Java rules | ECC polyglot patterns | `.claude/rules/java/coding-standards.md` |
| Frontend component rules | ECC polyglot patterns | `.claude/rules/frontend/component-standards.md` |
| **Phase 2.2** | | |
| 12 domain skills | ECC skill parity | `.claude/skills/` (39 total with python-data-science) |
| 6 automation hooks | ECC hook patterns | `.claude/hooks/` (18 total) |

## Quick Start

### Session Persistence

Enable with any preset that includes hooks:
```bash
/settings safe       # Includes session-init + session-end
/settings thorough   # Includes session-init + session-end
/settings standard   # Full hook set including session persistence
```

**How it works:**
1. `session-end.sh` runs on Stop → writes summary to `.claude/sessions/`
2. `session-init.sh` runs on SessionStart → detects and displays recent summaries
3. `pre-compact.sh` runs on UserPromptSubmit → saves state before `/compact`

### Context Modes

Launch Claude Code with mode-specific behavior:
```bash
alias claude-dev='claude --append-system-prompt "$(cat .claude/contexts/dev.md)"'
alias claude-review='claude --append-system-prompt "$(cat .claude/contexts/review.md)"'
alias claude-research='claude --append-system-prompt "$(cat .claude/contexts/research.md)"'
```

| Mode | Focus | Token overhead |
|------|-------|----------------|
| `dev` | Code-first, frequent commits | ~100 tokens |
| `review` | Severity-ordered, >80% confidence | ~100 tokens |
| `research` | Read-first, cite sources | ~100 tokens |

### MCP Discipline (10/80 Rule)

```bash
# Check your budget
./scripts/manage-mcps.sh audit

# Optimize if over budget
./scripts/manage-mcps.sh select
```

**Target:** Max 10 MCPs, 80 tools. Keeps startup overhead at ~15-20% of context.

### Agents (14 total)

Invoke via Task tool with agent-specific prompts. Definitions in `.claude/agents/`:

| Agent | Model | Access | Use Case |
|-------|-------|--------|----------|
| planner | opus | Read-only | Architecture planning, implementation design |
| code-reviewer | sonnet | Read-only | Code review with severity tiers |
| security-reviewer | sonnet | + Bash | OWASP Top 10, dependency scanning |
| build-resolver | sonnet | All | Build failures, CI fixes |
| architect | opus | Read-only | System design, ADR output format |
| tdd-guide | sonnet | Read-only | TDD coaching (advisory, Superpowers enforces) |
| database-reviewer | sonnet | Read-only | SQL optimization, N+1, migration safety |
| doc-updater | haiku | Write | README, docstrings, API docs, CHANGELOG |
| refactor-cleaner | sonnet | Write | Controlled refactoring, preserves tests |
| e2e-runner | sonnet | + Bash | Playwright/Cypress/Selenium, flaky tests |
| go-reviewer | sonnet | Read-only | Go patterns, goroutine leaks |
| go-build-resolver | sonnet | All | Go module/CGO/cross-compilation |
| python-reviewer | sonnet | Read-only | Python async, metaclasses, GIL |
| observer | haiku | All tools | Background pattern analysis, instinct creation |

### Continuous Learning

```bash
/instinct-status         # View learned patterns
/evolve                  # Cluster instincts into skills
/instinct-import file    # Import shared instincts
/instinct-export         # Export for sharing
```

Instincts are lightweight JSON in `.claude/instincts/` with confidence scoring (0-1). Authority: Rules > Instincts > Defaults.

### Multi-Agent Orchestration

```bash
/orchestrate review      # Code review → Security → Database analysis pipeline
/orchestrate security    # Security-focused analysis pipeline
/orchestrate refactor    # Review → Refactor → Verify pipeline
```

### Multi-Model Collaboration

```bash
/multi-plan <requirements>    # Claude + Gemini + GPT perspectives
/multi-execute <task>         # Parallel implementation, Claude synthesizes
```

Requires optional API keys in `.env`:
- `GOOGLE_AI_KEY` — Gemini (alternative perspectives)
- `OPENAI_API_KEY` — GPT (implementation patterns)

Gracefully degrades to Claude-only if keys are missing.

### Security (Two-Layer)

| Layer | Tool | Scope |
|-------|------|-------|
| Config-level | `npx ecc-agentshield scan` | CLAUDE.md, MCP permissions, hooks, agents |
| Code-level | `/security-audit` | OWASP Top 10, SQL injection, XSS, deps |

See `docs/SECURITY.md` for details.

## Token Overhead

| Component | Tokens | Loaded |
|-----------|--------|--------|
| Core rules (8 files) | ~5k | Every session (auto-loaded) |
| Language rules (5 files) | 0 at startup | Only when matching files edited |
| Skills (40 total) | 0 at startup | Only when invoked via `/skill-name` |
| Instincts (JSON) | ~50-200 each | Only when continuous-learning skill active |
| Agents | 0 at startup | Only when spawned via Task tool |
| AgentShield | 0 | External tool (npx), no context cost |

**Key insight**: Phases 2-2.2 add significant capability (40 skills, 18 hooks, 14 agents) without increasing startup overhead. Skills, agents, instincts, and language rules are all on-demand.

## Migration Notes

### From pre-ECC (Phase 1 upgrade)

1. **New directories** — Copy:
   - `.claude/agents/`
   - `.claude/contexts/`
   - `.claude/sessions/` (with `.gitkeep`)

2. **Updated files** — Review changes in:
   - `.claude/settings-presets.json` (new `optimized` preset, hooks in `safe`/`thorough`)
   - `.claude/hooks/settings-example.json` (new hooks)
   - `.claude/rules/context-management.md` (token optimization section)
   - `.claude/commands/health.md` (MCP budget section)
   - `docs/HOOKS.md` (new hook documentation)
   - `docs/MCP_SETUP.md` (10/80 rule section)

3. **Moved files** — If you customized:
   - `.claude/rules/python-standards.md` → `.claude/rules/python/coding-standards.md`

4. **New scripts** — Add to `scripts/`:
   - `manage-mcps.sh` now has `audit` command

5. **gitignore** — Add: `.claude/sessions/*.md`

### From Phase 1 (Phase 2 upgrade)

1. **New directories** — Copy:
   - `.claude/instincts/` (with `README.md` and `example.json`)
   - `.claude/evals/`
   - `.claude/rules/typescript/`, `golang/`, `java/`, `frontend/`
   - `.claude/skills/` (10 new skill directories)
   - `docs/CODEMAPS/`

2. **New agent files** — Copy to `.claude/agents/`:
   - `architect.md`, `tdd-guide.md`, `database-reviewer.md`, `doc-updater.md`
   - `refactor-cleaner.md`, `e2e-runner.md`, `go-reviewer.md`
   - `go-build-resolver.md`, `python-reviewer.md`

3. **New command files** — Copy to `.claude/commands/`:
   - `orchestrate.md`, `multi-plan.md`, `multi-execute.md`
   - `verify.md`, `eval.md`, `checkpoint.md`
   - `skill-create.md`, `update-codemaps.md`, `update-docs.md`
   - `instinct-status.md`, `instinct-import.md`, `instinct-export.md`, `evolve.md`

4. **New rule files** — Copy:
   - `.claude/rules/authority-hierarchy.md`
   - `.claude/rules/typescript/coding-standards.md`
   - `.claude/rules/golang/coding-standards.md`
   - `.claude/rules/java/coding-standards.md`
   - `.claude/rules/frontend/component-standards.md`

5. **Updated files** — Review changes in:
   - `.claude/commands/health.md` (AgentShield status section added)
   - `.claude/commands/security-audit.md` (AgentShield reference added)
   - `.claude/rules/proactive-steering.md` (orchestration patterns added)
   - `.claude/rules/workflow-guide.md` (orchestration/multi-model in decision tree)
   - `CLAUDE.md` (all Phase 2 sections)

6. **New docs** — Copy:
   - `docs/SECURITY.md` (AgentShield documentation)

7. **gitignore** — Add:
   - `.claude/instincts/*.json` (personal instincts)
   - `!.claude/instincts/example.json` (keep the example)
   - `.claude/evals/*.json` (eval history)
   - `.claude/agentshield-last-run` (marker file)

8. **Multi-model setup** (optional) — Add to `.env`:
   - `GOOGLE_AI_KEY=your_key` (Gemini)
   - `OPENAI_API_KEY=your_key` (GPT)
   - See `.claude/examples/multi-model-config.json`
