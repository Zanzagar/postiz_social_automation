# Project Template v2.6.0: An AI-Augmented Software Engineering Framework

**Author:** Corey Hoydic
**Version:** 2.6.0
**Date:** March 24, 2026
**Repository:** github.com/Zanzagar/project-template

---

## Executive Summary

This template transforms Claude Code from a reactive code-completion tool into a **structured engineering co-pilot** with enforced workflows, specialized sub-agents, persistent learning, and resource-conscious context management. Built on [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) (45K+ stars) with [Task Master](https://github.com/eyaltoledano/claude-task-master) integration and [Superpowers](https://github.com/obra/superpowers) TDD enforcement.

| Component | Count | Loading | Startup Cost |
|-----------|-------|---------|--------------|
| Agents | 40 | Description always (~2.4K) | ~2.4K |
| Skills | 153 (via profiles) | Metadata for active profile | ~3-25K |
| Commands | 88 | On `/command` | 0 |
| Rules | 68 | 11 core always + 57 language on file edit | ~19K |
| Hooks | 22 | On event trigger | 0 |
| MCP tools | 6 (recommended) | Always | ~3K |
| Superpowers | 13 skills | Always | ~3-5K |
| **Startup total (minimal profile)** | | | **~30-35K** |
| **Startup total (all profile)** | | | **~55-60K** |
| **Working context (minimal)** | | | **~145K** |

**v2.6.0 adds:** Skill profile system (15 named profiles, 22 categories), 84 ECC skill imports, 13 ops plugin skills, Anthropic document-skills plugin (PDF/DOCX/PPTX/XLSX), 26 new agents, 32 new commands, 51 language-specific rule files across 6 new languages (C#, Kotlin, Perl, PHP, Rust, Swift), and toolkit discovery for skill profiles.

---

## The Problem: Why "Out of the Box" Isn't Enough

### What actually goes wrong without a template

Consider a concrete scenario: a graduate student building a geostatistical interpolation pipeline for their thesis. They open Claude Code and type "Build me a kriging pipeline that reads borehole data from CSV, fits a variogram, and generates a prediction grid as a GeoTIFF."

Within 90 seconds, Claude generates 300 lines of code — CSV parsing, variogram fitting with `pykrige`, grid generation, rasterio export. It looks complete. The student runs it, gets a GeoTIFF output, and commits with the message "added kriging" and moves on.

Here's what they don't realize happened:

1. **No tests exist.** The AI generated zero test files. The student now has a working pipeline with 0% test coverage. When they modify the variogram model from spherical to exponential two weeks later, the grid dimensions silently change because of a parameter they didn't understand. They discover this the night before their thesis committee meeting — their prediction surface no longer aligns with their validation data.

2. **The coordinate reference system is wrong.** Claude assumed WGS84 (EPSG:4326) but the borehole data is in a local projected CRS (e.g., NAD83 / UTM Zone 17N). The kriging results look reasonable because the data is clustered, but the spatial statistics are computed on unprojected coordinates — meaning distances are in degrees, not meters. Every variogram parameter and every prediction is subtly wrong. A code review would have caught this immediately, but none was enforced.

3. **The session is gone.** The next day, the student opens Claude Code and says "now add cross-validation." Claude has no memory of yesterday's decisions — which variogram model was chosen, what the grid resolution is, how the CRS was handled. The student spends 20 minutes re-explaining their own pipeline to the AI.

4. **Context degraded mid-session.** After loading 10 MCP tool definitions (134 tools, 50K+ tokens), Claude's effective working context is already halved before the student types anything. By the time they've loaded rasterio documentation, a few data files, and had some back-and-forth, quality silently degrades. Claude starts forgetting the CRS conventions from earlier, suggesting `matplotlib` plots when `rasterio` was already being used, and generating code that contradicts the existing pipeline.

5. **The commit history is useless.** After three weeks of development, the git log reads: "added kriging", "updates", "fixed stuff", "more changes", "final version", "actual final version". The thesis advisor reviewing the code can't tell what was built when, can't evaluate the development process, and has no way to verify which decisions the student made versus which the AI made.

**None of these failures are caused by the AI being incapable.** Claude Code can write tests, handle CRS transformations, remember context, and produce clean commits. It just doesn't do these things *automatically*. Without a template, the quality of AI-assisted output depends entirely on the developer knowing to ask for best practices — which is exactly what students are still learning.

### The five gaps a template fills

| Gap | What Happens Without It | What the Template Does |
|-----|------------------------|----------------------|
| **Memory** | Every session starts from zero. The AI forgets your architecture, conventions, and past decisions. | Persistent session summaries, work logs, instinct system, and CLAUDE.md carry context across sessions indefinitely. |
| **Discipline** | The AI writes whatever you ask for, including insecure code, untested features, and broken commits. | TDD enforcement (Superpowers deletes untested code), security gates, conventional commit rules, and verification pipelines make bad practices harder than good ones. |
| **Resources** | 50K+ tokens consumed by unused tools at startup. Quality degrades silently mid-session with no recovery. | Token-conscious design (35K startup, 165K working). Strategic compaction, tiered documentation lookups, and on-demand skill loading maximize working context. |
| **Context** | Generic "textbook" code that doesn't fit the project's patterns, framework idioms, or architectural decisions. | 17 behavior rules, 48 domain skills, and language-specific coding standards teach the AI your project's conventions. |
| **Specialization** | One general-purpose model handles security review, architecture planning, test generation, and documentation with equal (shallow) depth. | 14 purpose-built agents with appropriate model tiers, tool access, and domain training produce categorically deeper results in each specialty. |

### What a well-configured template provides

| Capability | Without Template | With Template |
|-----------|-----------------|---------------|
| **Session continuity** | Forgets everything | Persistent memory, session summaries, work logs |
| **Code quality** | Whatever you ask for | TDD enforcement, automated linting, security gates |
| **Architecture** | Generic patterns | Project-specific rules, conventions, prior decisions |
| **Specialization** | One model does all | 14 purpose-built agents (security, architecture, review...) |
| **Resource efficiency** | Burns through context | Token-conscious presets, strategic compaction, tiered lookups |
| **Workflow** | Reactive (does what you say) | Proactive (detects phase, suggests next steps, catches mistakes) |
| **Learning** | Starts fresh daily | Instinct system captures patterns, evolves into skills |
| **Collaboration** | Single model | Multi-model parallel execution (Claude + Gemini + GPT) |
| **Observability** | No tracking | Per-session usage telemetry, model capability routing |

The difference is analogous to the difference between giving someone a text editor and giving them an IDE. The underlying capability is the same, but the **scaffolding around it** determines whether that capability translates into reliable, high-quality output.

---

## Architecture Overview

```
project-template/
├── .claude/
│   ├── agents/          # 14 sub-agents (opus/sonnet/haiku tiers)
│   ├── commands/        # 56 slash commands
│   ├── skills/          # 48 domain knowledge modules
│   ├── rules/           # 11 core + 6 language-specific rules
│   ├── hooks/           # 22 hooks (bash + Node.js)
│   │   └── lib/         # hook-flags.js, resolve-formatter.js, utils.js
│   ├── presets/         # 5 project-type presets
│   ├── instincts/       # Continuous learning patterns (JSON)
│   ├── contexts/        # Session modes (dev/review/research)
│   ├── sessions/        # Summaries, cost logs, handoff docs
│   └── upstream-manifest.json  # 85 tracked upstream files
├── .taskmaster/         # Task Master (AI task management)
├── scripts/             # harness-audit.js, multi-model-query.py, etc.
├── docs/                # TEMPLATE_OVERVIEW, SECURITY, HOOKS, MCP_SETUP
├── .github/workflows/   # CI validators
├── CLAUDE.md            # Master config (~12K, loaded every session)
└── CHANGELOG.md
```

---

## System Layer Model

The template operates in five layers. Information flows upward; authority flows downward.

```
┌─────────────────────────────────────────────────────────────┐
│  AGENTS (40)        Isolated context windows                │
│  Opus (reasoning) · Sonnet (frequent) · Haiku (lightweight) │
├─────────────────────────────────────────────────────────────┤
│  COMMANDS (88)      User-invocable workflows                │
│  /plan, /tdd, /verify, /pr, /orchestrate, /brainstorm      │
├─────────────────────────────────────────────────────────────┤
│  SKILLS (153)       Domain knowledge, profile-managed       │
│  22 categories · 15 named profiles · minimal→all            │
├─────────────────────────────────────────────────────────────┤
│  RULES (68)         Behavioral constraints, auto-loaded     │
│  11 core + 57 language rules across 12 directories          │
├─────────────────────────────────────────────────────────────┤
│  HOOKS (22)         Event-driven automation                 │
│  Format, guard, track, persist — 3 profile tiers            │
└─────────────────────────────────────────────────────────────┘
```

**Hooks** enforce constraints at the tool level. **Rules** define behavioral standards Claude must follow. **Skills** provide domain expertise when relevant. **Commands** orchestrate multi-step workflows. **Agents** handle specialized tasks in isolated context windows with dedicated model tiers.

**Authority hierarchy:** Rules > Superpowers enforcement > Instincts > Defaults. A rule cannot be overridden by an instinct. Superpowers TDD enforcement requires explicit user acknowledgment to bypass.

---

## Hook System

### Profile System (v2.5.0)

All hooks are controlled by the `TEMPLATE_HOOK_PROFILE` environment variable. Each hook checks its profile assignment at startup via `lib/hook-flags.js` — if the current profile isn't in the hook's allowed set, it exits immediately (zero overhead).

| Profile | Active Hooks | Use Case |
|---------|-------------|----------|
| **minimal** | 7 — lifecycle + safety | Fast sessions, debugging, exploration |
| **standard** | 18 — adds formatting, analysis, learning, cost tracking | Normal development (default) |
| **strict** | 22 — adds doc blocking, TS checking, tmux enforcement | Pre-commit, CI, thorough review |

```bash
export TEMPLATE_HOOK_PROFILE=minimal               # Switch profile
export TEMPLATE_DISABLED_HOOKS=build-analysis       # Disable specific hooks
```

Alternatively, use presets: `/settings fast` (all hooks off), `/settings minimal` (lightweight subset), `/settings safe` (safety only).

### Quality Gate Consolidation (v2.5.0)

`quality-gate.js` consolidates three concerns into one PostToolUse hook:

| Concern | Legacy Hook | Behavior |
|---------|-------------|----------|
| Auto-formatting | post-edit-format | Biome/Prettier (JS/TS), ruff (Python), gofmt, rustfmt |
| Debug detection | console-log-audit | Warns on console.log, print(), fmt.Print, System.out |
| Type checking | typescript-check | tsc --noEmit filtered to the edited file |

**Architecture:** Both quality-gate.js and the three legacy hooks are configured in settings.json. The legacy Node.js hooks detect quality-gate.js via `require.resolve()` — if found, they delegate and exit. If quality-gate.js is removed, they fall back to their original behavior. This progressive consolidation pattern avoids breaking changes.

### Hook Inventory

| Hook | Event | Matcher | Profiles | Purpose |
|------|-------|---------|----------|---------|
| session-init.sh | SessionStart | — | all | Phase detection, health check, session resume |
| project-index.sh | SessionStart | — | all | Codebase JSON index for sub-agents |
| observe.sh | Pre+PostToolUse | * | std,str | Tool observation with secret scrubbing |
| pre-commit-check.sh | PreToolUse | Bash | all | Conventional commit format, branch protection |
| auto-tmux-dev.js | PreToolUse | Bash | std,str | Auto-run dev servers in tmux (non-blocking) |
| protect-sensitive-files.sh | PreToolUse | Edit,Write | all | Block .env/.pem/credentials; config tamper guard |
| dev-server-blocker.js | PreToolUse | Bash | str | Block dev servers outside tmux |
| long-running-tmux-hint.sh | PreToolUse | Bash | str | Advisory tmux reminder for slow commands |
| file-size-guard.js | PreToolUse | Write | std,str | Block source code files exceeding 800 lines |
| doc-file-blocker.sh | PreToolUse | Write | str | Block .md creation outside docs/ |
| quality-gate.js | PostToolUse | Edit,Write | std,str | Consolidated format + debug audit + TS check |
| post-edit-format.js | PostToolUse | Edit,Write | std,str | Legacy formatter (delegates to quality-gate) |
| console-log-audit.js | PostToolUse | Edit | std,str | Legacy debug audit (delegates to quality-gate) |
| typescript-check.js | PostToolUse | Edit | str | Legacy TS check (delegates to quality-gate) |
| build-analysis.sh | PostToolUse | Bash | std,str | Advisory analysis of build command output |
| pr-url-extract.sh | PostToolUse | Bash | std,str | PR creation URL from git push output |
| pre-compact.sh | UserPromptSubmit | — | all | Save working state before context compaction |
| suggest-compact.js | UserPromptSubmit | — | std,str | Suggest compaction at 50/75 tool calls |
| session-end.js | Stop | — | all | Detailed session summary to .claude/sessions/ |
| check-console-log.js | Stop | — | std,str | End-of-session debug statement check |
| pattern-extraction.sh | Stop | — | all | Extract instinct candidates from git history |
| cost-tracker.js | Stop | — | std,str | Session token/cost metrics to cost-log.jsonl |

Profiles: **all** = minimal+standard+strict; **std,str** = standard+strict; **str** = strict only.

---

## Security Model

Four security layers cover different attack surfaces:

| Layer | Scope | Mechanism |
|-------|-------|-----------|
| **Runtime guards** | File-level protection | `protect-sensitive-files.sh` — blocks .env, .pem, credentials |
| **Config tamper guard** | Linter/formatter settings | Same hook — blocks edits to ruff.toml, .eslintrc, biome.json |
| **Behavioral rules** | Agent behavior constraints | `security-hardening.md` — deny lists, prompt injection guardrails |
| **Config audit** | CLAUDE.md, MCPs, hooks, agents | AgentShield (`npx ecc-agentshield scan`) |
| **Code audit** | OWASP Top 10, secrets, deps | `/security-audit` → security-reviewer agent |

### OWASP Agentic Top 10 Mapping (v2.5.0)

| OWASP Risk | Template Mitigation |
|------------|---------------------|
| A01: Excessive Agency | Hook profiles limit scope; tool allowlists in settings |
| A02: Data Leakage | Secret scrubbing in observe.sh; protect-sensitive-files.sh |
| A03: Tool Misuse | file-size-guard.js; protect-sensitive-files.sh |
| A04: Prompt Injection | Guardrails in security-hardening.md rule |
| A05: Insecure Output | /code-review + /security-audit commands |
| A06: Autonomy Abuse | SIGUSR1 throttling; cost-tracker.js; suggest-compact.js |
| A07: System Prompt Leak | N/A (Claude Code runs locally, no API exposure) |
| A08: Data Integrity | Config tamper guard in protect-sensitive-files.sh |
| A09: Insecure Plugin | MCP audit (manage-mcps.sh); 10/80 rule (max 10 servers, 80 tools) |
| A10: Supply Chain | AgentShield CI scan; upstream-manifest.json tracking |

### Config Tamper Guard (v2.5.0)

`protect-sensitive-files.sh` blocks edits to linter/formatter configs (ruff.toml, .eslintrc, biome.json, .prettierrc, .golangci.yml, etc.) to prevent Claude from weakening code quality settings. Override with `TEMPLATE_ALLOW_CONFIG_EDIT=1`. Multi-purpose configs (tsconfig.json, pyproject.toml) get a warning instead of a block.

See `docs/SECURITY.md` for full security documentation including AgentShield CI integration, deny list recommendations, and the PR audit checklist.

---

## Resource Observability

### Usage Telemetry (v2.5.0)

`cost-tracker.js` (Stop hook) logs per-session token usage to `.claude/sessions/cost-log.jsonl` for understanding session patterns:

```json
{"timestamp":"2026-03-20T01:00:00Z","session_id":"abc","model":"opus","input_tokens":45000,"output_tokens":12000}
```

This telemetry helps identify which tasks consume the most context and when sessions are approaching limits — it's an observability tool, not a cost-saving mechanism.

### Model Routing by Capability

`/model-route` recommends the appropriate model tier based on **task complexity and risk**, not cost:

| Task Type | Recommended | Why |
|-----------|-------------|-----|
| Architecture, complex planning | Opus | Maximum reasoning depth for high-stakes decisions |
| Implementation, code review | Sonnet | Strong for scoped, well-defined work |
| Formatting, simple transforms | Haiku | Sufficient for mechanical, deterministic tasks |

**Default to the highest-capability model when in doubt.** Never sacrifice reasoning depth for speed.

---

## Continuous Learning Pipeline

### Observation → Pattern → Instinct

```
observe.sh (Pre+PostToolUse, matcher: *)
  ├── Captures tool name, input/output (truncated to 5KB)
  ├── Scrubs secrets (Bearer tokens, API keys, passwords)    ← v2.5.0
  ├── Archives observations >10MB with auto-purge (30 days)  ← v2.5.0
  └── Writes to .claude/instincts/observations.jsonl
           ↓
  Observer daemon (haiku, background)
  ├── Signaled every 20 tool uses (SIGUSR1 throttle)         ← v2.5.0
  └── Creates instinct candidates (confidence 0.3-0.5)
           ↓
  .claude/instincts/
  ├── candidates/  (0.3-0.5 confidence, auto-created)
  ├── personal/    (0.5-0.7+, reinforced by repetition)
  └── inherited/   (team-shared via /instinct-import)
           ↓
  /learn       — manual extraction (nudged at 75 tool calls)
  /evolve      — cluster instincts → promote to full skills
  /instinct-export / /instinct-import — team sharing
```

**v2.5.0 improvements to observe.sh:**
- **Secret scrubbing:** Regex-based removal of Bearer tokens, API keys (sk-, ghp_, AKIA...), passwords, and auth headers before persisting to disk
- **SIGUSR1 throttling:** Observer daemon signaled every N observations (default 20, configurable via `TEMPLATE_OBSERVER_SIGNAL_INTERVAL`) instead of every tool use
- **Auto-purge:** Archived observation files older than 30 days automatically deleted (daily check via marker file)

**Authority:** Rules > Instincts > Defaults (always). Active instincts (confidence >0.7) decay at -0.05/week when unused. Instincts supplement rules — they never override them.

---

## Harness Audit Scoring (v2.5.0)

`node scripts/harness-audit.js` runs a deterministic 70-point health check across 7 categories. All checks are file-existence or content-based — reproducible for the same commit.

| Category | Points | What It Measures |
|----------|--------|-----------------|
| **Tool Coverage** | 10 | Hooks in settings.json, MCP servers, agents (3+), skills (10+), commands (10+) |
| **Context Efficiency** | 10 | CLAUDE.md exists and <20KB, conditional language rules, context modes, token docs |
| **Quality Gates** | 10 | Pre-commit hook, formatter, quality gate, file size guard, sensitive file protection |
| **Memory & Persistence** | 10 | Session init/end hooks, pre-compact, sessions dir, compaction advisor |
| **Eval & Testing** | 10 | Test command, linter configured, CI workflow, /verify command, /eval command |
| **Security Guardrails** | 10 | Sensitive file protection, security rule, .gitignore blocks .env, no secrets, doc blocker |
| **Resource Management** | 10 | Usage tracker, /model-route, hook profiles, sub-agent routing docs, settings presets |

**Grading:** A (90-100%), B (80-89%), C (70-79%), D (60-69%), F (<60%). Exit code 1 if below 50%.

```bash
node scripts/harness-audit.js              # Full audit (text)
node scripts/harness-audit.js --format json # Machine-readable
node scripts/harness-audit.js security      # Single category
/harness-audit                              # Via slash command
```

Current score: **70/70 (100%) A**.

---

## Project Lifecycle Pipeline

### Always Active (every session, ~35-40K tokens)

CLAUDE.md, 11 core rules, 2 MCP servers (Task Master + Context7), Superpowers plugin (13 skills).

### Phase 1: Ideation — "I want to build..."

| Action | Component | Type |
|--------|-----------|------|
| Explore ideas | `superpowers:brainstorming` | Skill (mandatory for non-trivial work) |
| Research | `/research`, WebSearch, WebFetch | Command + tools |
| Multi-model perspectives | `/multi-plan` → `multi-model-query.py` | Command + script |
| **Output** | `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` | Design doc |

### Phase 2: Planning — "Here's what we'll build"

| Action | Component | Type |
|--------|-----------|------|
| Validate tech assumptions | `/research` (after brainstorming) | Command |
| Create PRD | `/prd-generate` or manual | Command |
| Parse into tasks | `task-master parse-prd --num-tasks 0 --force` | CLI (not MCP) |
| Analyze complexity | `task-master analyze-complexity` → `complexity-report` | CLI |
| Expand complex tasks | `task-master expand --id=<id>` (score >= 5) | CLI |

### Phase 3: Building — "Implement task by task"

| Step | Action | Component |
|------|--------|-----------|
| Claim | `task-master next` / `set-status in-progress` | MCP |
| **RED** | Write failing tests | `superpowers:test-driven-development` |
| **GREEN** | Make tests pass | Language rules + domain skills (on demand) |
| **REFACTOR** | Clean up | Maintain green tests |
| Verify | `/verify` (test + lint + types + security) | Command |
| Commit | `git commit` → pre-commit-check.sh validates | Hook |
| Complete | `task-master set-status <id> done` | MCP |

**Exceptions:** Infrastructure/config tasks use validation testing instead of TDD. Documentation skips TDD entirely.

### Phase 4: Review — "Is it good enough?"

| Action | Component |
|--------|-----------|
| Code quality | `/code-review` → code-reviewer agent |
| Security scan | `/security-audit` → security-reviewer agent |
| Multi-agent review | `/orchestrate review` → code + security + database agents |
| Language-specific | `/python-review`, `/go-review` → specialized agents |
| Verify before done | `superpowers:verification-before-completion` |

### Phase 5: Shipping — "Get it out the door"

Prescribed sequence from `workflow-enforcement.md`: (1) `/code-review` → address critical/high findings, (2) `git push -u origin <branch>` → pr-url-extract.sh fires, (3) `/pr` → squash merge default for feature/bugfix, (4) `gh run watch <id>` → verify CI, (5) merge → sync main → cleanup branch → update tasks → tag if release-worthy.

---

## Workflow Enforcement

### Decision Thresholds

| Work Type | Size | Workflow |
|-----------|------|----------|
| Feature (multi-task) | — | Full pipeline: brainstorm → validate → PRD → tasks → TDD |
| Feature (single task) | — | TDD directly (skip brainstorm/PRD) |
| Bug fix | < 10 lines | Direct TDD, no task needed |
| Bug fix | 10-50 lines | Create task, then TDD |
| Bug fix | > 50 lines | systematic-debugging first, then task + TDD |
| Refactor | < 50 lines | Direct with tests |
| Refactor | 50-200 lines | Create task + TDD |
| Refactor | 200+ lines | Full pipeline: PRD, tasks, TDD per subtask |
| Documentation | Any | No TDD. `docs:` commit prefix |
| Infrastructure | Any | Validation testing (syntax + loading), not TDD |

### Three Enforcement Tiers

| Tier | Mechanism | Scope |
|------|-----------|-------|
| **Hard (hooks)** | pre-commit-check.sh | Commit format, branch protection |
| **Hard (plugin)** | Superpowers TDD | Tests before production code |
| **Advisory** | /phase-check | Phase prerequisites (reports only) |
| **Normative** | workflow-enforcement.md | Pipeline sequence, thresholds, merge strategy |

---

## Comparison: Template vs. Raw Claude Code

### Scenario: "Build a kriging pipeline with cross-validation for soil heavy metal prediction"

**Without template (raw Claude Code):**
1. Student types the request
2. Claude generates the entire pipeline in one shot — data loading, variogram fitting, kriging, export
3. No tests. No CRS validation. No cross-validation correctness check. No type hints.
4. Student runs it, gets a pretty GeoTIFF, presents it
5. Thesis committee asks: "How did you handle spatial autocorrelation in your cross-validation?" The student has no answer — they didn't realize that random k-fold CV is invalid for spatially correlated data, and the AI didn't mention it because it wasn't asked

**With template:**
1. `/brainstorm Build a kriging pipeline with cross-validation for soil heavy metal data` → Superpowers brainstorming explores approaches: ordinary vs universal kriging, variogram model selection, spatial vs random CV. Produces a design doc identifying that random k-fold is invalid for spatially autocorrelated data — catching this *before* any code is written.
2. `/research` → Validates technical assumptions: pykrige API for variogram fitting, rasterio CRS handling, spatial CV libraries (scikit-learn's `GroupKFold` with spatial blocks).
3. `/prd-generate` → Structures the validated design into a PRD with dependency graph: (1) data loading & CRS validation, (2) exploratory spatial analysis, (3) variogram modeling, (4) kriging with spatial cross-validation, (5) export & visualization.
4. Task Master parses the PRD into tracked tasks with dependencies. Student starts with Task 1 (data loading).
5. `/tdd` → TDD guide writes failing tests: "test that input data is reprojected to UTM", "test that NaN values are handled", "test that output CRS matches input CRS"
6. `/verify` → Tests pass, ruff linting clean, mypy types checked
7. `/commit` → `feat(data): Add borehole CSV loader with CRS validation`
8. Repeat for Tasks 2-5 (variogram, kriging, spatial CV, export) — each following the RED-GREEN-REFACTOR TDD cycle
9. `/code-review` → Python reviewer checks for NumPy anti-patterns, type safety, proper error handling
10. `/python-review` → Catches mutable default arguments, missing type hints, hardcoded file paths
11. `/pr` → Pull request documenting methodology decisions with test plan
12. `/learn` → Captures "spatial CV required for spatially correlated data" as an instinct for future sessions

The difference isn't just quality — it's **reproducibility**. The template produces consistently high-quality output because the process is enforced, not optional. And critically, the brainstorming phase caught the spatial cross-validation issue *before* code was written — saving the student from a methodological error that would have undermined the entire thesis.

### Quantitative Comparison

| Metric | Raw Claude Code | With Template |
|--------|----------------|---------------|
| Test coverage | 0% (tests not written) | 80%+ (TDD enforced) |
| CRS validation | None (silent errors) | Enforced by tests and code review |
| Commit quality | "added kriging" | `feat(variogram): Add spherical model with auto-fit` |
| Methodology review | None | Planner catches spatial CV issues before coding |
| Session continuity | None | Summaries, work log, instincts |
| Context efficiency | ~50K wasted on unused tools | <35K startup, 165K working |
| Specialization | 1 general model | 14 specialized agents |
| Documentation | Manual or forgotten | Auto-generated codemaps, session summaries |
| Learning | Starts fresh every session | Persistent instinct system, cross-session memory |
| Reproducibility | Hardcoded paths, no seeds | Verified by `/verify` pipeline |
| Usage telemetry | None | Per-session tracking via cost-tracker.js |

---

## Multi-Model Collaboration

`/multi-plan` and `/multi-execute` query multiple AI models in parallel, synthesizing diverse perspectives. Claude generates all perspectives by default. Optionally add API keys for genuinely independent perspectives:

- `GOOGLE_AI_KEY` — Gemini (free tier available)
- `OPENAI_API_KEY` — GPT (pay-as-you-go)

Gracefully degrades to Claude-only without API keys. Check: `python3 scripts/multi-model-query.py --check`

---

## Session Persistence

Three complementary layers:

| Layer | Mechanism | Captures |
|-------|-----------|----------|
| **Automatic snapshots** | session-end.sh (Stop hook) | Git diff, commits, files, tasks |
| **Pre-compaction state** | pre-compact.sh (UserPromptSubmit) | Branch, uncommitted changes, active task |
| **Handoff documents** | Claude writes on request | Decisions, reasoning, exact next steps |

Resume complex work: `Read .claude/sessions/handoff-YYYYMMDD.md and MEMORY.md`

---

## Value Proposition for Academic Projects

### For Students

**Scenario: A graduate student building their first spatial prediction model.**

Without the template, they face a blank directory and an AI that will generate whatever they ask for — including methodological mistakes they won't catch until their committee defense. They hardcode file paths to `/home/student/data/` because they don't know about configuration management. They write no tests because "it's just research code." They commit once a week with messages like "update." They discover their cross-validation was statistically invalid when a committee member asks why they used random k-fold on spatially autocorrelated data.

With the template:
- Their first `/commit` is rejected because the message doesn't follow conventional commit format. They learn the convention immediately — and their thesis advisor can later read the git log to understand the development timeline.
- Their first attempt to write a variogram fitting function triggers the TDD guide: "Write a failing test first." They learn to define expected behavior *before* implementation — a discipline that prevents silent numerical errors from propagating through the pipeline.
- Their first spatial operation is accompanied by proactive CRS checking (from learned instincts). They learn about coordinate reference systems before computing invalid distances.
- When they use `pickle` to serialize a trained model (a security risk), the Python reviewer catches it and suggests `joblib` or safetensors instead.

**The result isn't just a better pipeline — it's a better researcher.** The template's enforced workflows become muscle memory. Students who use it for a semester internalize TDD, version control discipline, reproducibility practices, and code review habits that distinguish reliable research from one-off scripts.

Beyond enforcement, the template provides **domain expertise on demand.** Need to configure a PostgreSQL spatial database? The `postgresql-patterns` skill knows about GiST indexing for geometry columns, PostGIS query optimization, and migration safety. Need Python testing patterns? The `python-testing` skill provides pytest fixtures, parametrization, and mocking strategies. The 153 skills (managed by profiles to load only what's relevant) act as an always-available senior engineer across every domain the student might encounter — without requiring the student to know the right questions to ask.

Critically, **quality scales with the project.** A thesis codebase that grows to 10,000+ lines maintains the same quality standards as the first 100 lines, because the template's enforcement doesn't fatigue. The TDD guide is just as strict on line 10,000 as on line 1. The security reviewer doesn't get tired of scanning. This is where AI-assisted development fundamentally differs from manual discipline — the template never has a bad day.

**Specific capabilities students gain:**

| Situation | What the Template Does | What the Student Learns |
|-----------|----------------------|----------------------|
| Starting a new analysis | `/brainstorm` → `/research` → `/prd-generate` → Task Master | Methodology design before coding, scope management |
| Writing any code | TDD enforces tests first | Defining expected behavior before implementation |
| Committing code | Rules require conventional format | Professional version control, traceable development |
| Completing a pipeline stage | `/verify` runs test + lint + type + security pipeline | Multi-stage quality gates for research code |
| Getting unexpected results | Five Whys debugging pattern (from reasoning rules) | Root cause analysis vs tweaking parameters until it "looks right" |
| Feeling stuck | Proactive steering detects uncertainty, offers structured help | Breaking problems down, asking for help productively |
| End of session | `/learn` extracts patterns, instincts persist | Reflection and knowledge management |

### For Research

**Scenario: A graduate student building a geostatistical ML pipeline comparing kriging methods against deep learning for mineral concentration prediction.**

Research code in geostatistics and ML is notoriously difficult to reproduce. Hardcoded file paths to local shapefiles, missing random seeds in neural network training, unversioned GDAL/rasterio dependencies (where minor version differences change output), and undocumented preprocessing steps (how was the DEM resampled? which CRS was used for distance calculations?) mean that even the author can't reproduce their own results six months later — let alone a reviewer or future student extending the work.

The template addresses this at the process level:

1. **Every methodological decision is recorded.** Conventional commits, work logs, and session summaries create an audit trail that documents not just *what* was built, but *why* each decision was made. When a committee member asks "why did you use ordinary kriging instead of universal kriging with a trend surface?", the answer is in the work log — captured during the session where the decision was made, complete with the trade-offs considered, not reconstructed from memory months later.

2. **Dependencies are tracked from day one.** The template's verification pipeline catches unversioned dependencies before they become a problem. `pip freeze > requirements.txt` — including the exact versions of `rasterio`, `geopandas`, `pykrige`, `scikit-learn`, and `torch` — isn't something the student has to remember. It's part of the workflow. This prevents the "it worked on my machine" problem that plagues spatial computing where GDAL version differences can change raster output.

3. **Multi-model perspectives reduce methodological bias.** If a student asks one AI model "what interpolation method should I use for sparse borehole data?", they get one opinion shaped by that model's training data. `/multi-plan` gives them three independent opinions — perhaps kriging, random forest with spatial features, and Gaussian process regression — surfaces the trade-offs between them, and forces the student to reason about *why* one method is appropriate for their data rather than accepting the first suggestion.

4. **The methodology section writes itself.** When every commit follows a convention (`feat(variogram): Add spherical model auto-fitting with weighted least squares`), every development phase is tracked in Task Master, and every session generates a summary, the student has a complete record of their analytical pipeline development. The template doesn't just produce better code — it produces documentable, defensible methodology that can be directly referenced in a thesis or publication.

5. **Collaboration becomes meaningful.** When two researchers in the same group both use the template, they follow the same development process — the same commit conventions, the same testing discipline, the same code review standards. This makes peer review between group members productive rather than superficial, because both parties understand the workflow. Instincts can be exported and imported (`/instinct-export`, `/instinct-import`), so when one group member discovers that `pykrige` requires a specific variogram binning strategy for sparse data, the entire group benefits in their next session. The template transforms a collection of individual researchers into a group with shared engineering practices and shared institutional knowledge.

### For the Department

**Scenario: A professor overseeing 30 capstone projects with 4-person teams.**

Without standardization, each team invents their own workflow. Some use git effectively; others email zip files. Some write tests; others don't. Some teams communicate well; others have one person doing all the work while others struggle in silence. The professor has no visibility into process quality until the final presentation.

The template changes this:

1. **Every team starts with the same foundation.** The template is cloned once and provides identical tooling, rules, and workflows to every team. This eliminates the "our team didn't know about X" excuse and establishes a baseline of professional practice.

2. **Process quality becomes measurable.** The professor can look at any team's git log and see:
   - Are commits frequent and well-described? (Enforced by commit rules)
   - Are features tested before they're committed? (Enforced by TDD)
   - Are security issues caught early? (Tracked by `/security-audit`)
   - Is the team following a structured workflow? (Tracked by Task Master)

   This is not surveillance — it's the same visibility that a tech lead has on a professional team. The template creates a paper trail that makes good process visible and bad process obvious.

3. **The AI becomes a force multiplier for faculty guidance.** A professor can't sit with every team during every coding session. But the template can. It catches the same mistakes the professor would catch — hardcoded credentials, untested code, broken commits — and addresses them in real time. The professor's limited time can then focus on higher-level guidance: architecture decisions, research direction, and career mentorship.

4. **The template itself is a teaching tool.** The rules and skills encode best practices that students absorb through use — not through lectures. The authority hierarchy (Rules > Instincts > Defaults) teaches software engineering governance: some constraints are non-negotiable (rules), some are learned suggestions (instincts), and some are baseline defaults. This mirrors real-world engineering organizations where certain practices are mandated by policy, others are team conventions, and others are individual preferences. Students who internalize this hierarchy understand governance — a concept that's difficult to teach abstractly but natural to learn through a system that enforces it.

5. **Grading becomes more meaningful.** Instead of evaluating only the final output (does the app work?), the professor can evaluate the process (was the app built well?). The template's audit trail — commits, task completion, code review findings, test coverage — provides evidence of engineering discipline that a working demo alone cannot show. The harness audit (`/harness-audit`) provides a deterministic 70-point health score across 7 categories that can serve as a baseline assessment.

---

## Component Inventory

### Agents (40)

**Original (14):**

| Agent | Model | Purpose |
|-------|-------|---------|
| planner | Opus | Architecture planning, implementation design |
| architect | Opus | System design, ADR output, technology selection |
| code-reviewer | Sonnet | Quality review with severity tiers, >80% confidence filtering |
| security-reviewer | Sonnet | OWASP Top 10, dependency scanning, secret detection |
| tdd-guide | Sonnet | Test-driven development coaching (advisory) |
| build-resolver | Sonnet | Build failure diagnosis, CI fixes (polyglot) |
| database-reviewer | Sonnet | SQL optimization, N+1 detection, migration safety |
| e2e-runner | Sonnet | Playwright/Cypress/Selenium test generation |
| refactor-cleaner | Sonnet | Dead code removal, preserves all tests |
| go-reviewer | Sonnet | Go idioms, goroutine leaks, error wrapping |
| go-build-resolver | Sonnet | Go modules, CGO, cross-compilation errors |
| python-reviewer | Sonnet | Python async, metaclasses, GIL, packaging |
| doc-updater | Haiku | README, docstrings, API docs, CHANGELOG |
| observer | Haiku | Background pattern analysis, instinct creation |

**ECC Import (15):** cpp-reviewer, cpp-build-resolver, rust-reviewer, rust-build-resolver, java-reviewer, java-build-resolver, kotlin-reviewer, kotlin-build-resolver, typescript-reviewer, flutter-reviewer, pytorch-build-resolver, debugger, error-detective, harness-optimizer, loop-operator

**Ops Plugins (11):** kubernetes-architect, network-engineer, incident-responder, devops-troubleshooter, observability-engineer, performance-engineer, database-optimizer, chief-of-staff, docs-lookup, test-automator, ui-visual-validator

### Rules (68)

**Core (11, always loaded, ~19K tokens):**

| Rule | Governs |
|------|---------|
| claude-behavior.md | Commit frequency, conventional commits, immutability, security checklist |
| git-workflow.md | Branch naming, recovery commands, team collaboration |
| reasoning-patterns.md | Clarification, brainstorming, five whys, adopt/extend/compose/build matrix |
| workflow-guide.md | Phase detection, tool selection decision tree, commitment checkpoints |
| workflow-enforcement.md | Task-type workflows, size thresholds, merge strategy, branch completion |
| context-management.md | Thinking modes, compaction strategy, token budgets, sub-agent patterns |
| proactive-steering.md | Project co-pilot behaviors, scope management, auto-tool invocation |
| authority-hierarchy.md | Rules > Superpowers > Instincts > Defaults precedence |
| superpowers-integration.md | Pipeline override: brainstorm → validate → PRD; writing-plans scope |
| taskmaster-usage.md | CLI vs MCP matrix, flags, timeouts, token-conscious task viewing |
| security-hardening.md | Deny lists, prompt injection guardrails, PR audit, OWASP mapping |

**Language-specific (57 files across 12 directories, loaded on file edit, 0 startup tokens):**

| Directory | Files | Trigger | Topics |
|-----------|-------|---------|--------|
| python/ | 5 | `.py` | coding-standards, testing, security, patterns, hooks |
| typescript/ | 5 | `.ts`, `.tsx`, `.js`, `.jsx` | coding-standards, testing, security, patterns, hooks |
| golang/ | 5 | `.go` | coding-standards, testing, security, patterns, hooks |
| java/ | 5 | `.java` | coding-standards, testing, security, patterns, hooks |
| cpp/ | 5 | `.cpp`, `.hpp`, `.h` | coding-standards, testing, security, patterns, hooks |
| rust/ | 5 | `.rs` | coding-style, testing, security, patterns, hooks |
| kotlin/ | 5 | `.kt`, `.kts` | coding-standards, testing, security, patterns, hooks |
| swift/ | 5 | `.swift` | coding-standards, testing, security, patterns, hooks |
| csharp/ | 5 | `.cs` | coding-standards, testing, security, patterns, hooks |
| php/ | 5 | `.php` | coding-standards, testing, security, patterns, hooks |
| perl/ | 5 | `.pl`, `.pm` | coding-standards, testing, security, patterns, hooks |
| frontend/ | 2 | `.jsx`, `.tsx`, `.vue`, `.svelte` | component-standards, workflow |

### Skills (153)

Skills live in `.claude/skills-available/` and are symlinked into `.claude/skills/` by the active profile. Use `./scripts/manage-skill-profiles.sh list` for the full inventory.

**By category (22 categories):**

| Category | Skills | Example Skills |
|----------|--------|----------------|
| Universal | 31 | tdd-workflow, verification-loop, debugging, code-review, git-recovery, search-first, blueprint, strategic-compact |
| Python | 5 | python-patterns, python-testing, python-django, python-data-science |
| Django | 4 | django-patterns, django-security, django-tdd, django-verification |
| TypeScript | 1 | typescript-patterns |
| Go | 2 | golang-patterns, golang-testing |
| Java/Spring | 5 | java-springboot, spring-boot-security, spring-boot-tdd, jpa-patterns |
| C++ | 2 | cpp-coding-standards, cpp-testing |
| Rust | 3 | rust-review, rust-build, rust-test |
| Kotlin | 3 | kotlin-review, kotlin-build, kotlin-test |
| Flutter | 1 | flutter-review (via agent) |
| Frontend | 3 | frontend-patterns, frontend-design, e2e-testing |
| Database | 3 | database-patterns, database-migrations, postgresql-patterns |
| API/Backend | 2 | api-design, backend-patterns |
| DevOps | 2 | docker-patterns, deployment-patterns |
| Security | 2 | security-scan, security-review |
| AI/Eval | 6 | eval-harness, eval-metrics, agentic-engineering, ai-regression-testing, autonomous-loops, cost-aware-llm-pipeline |
| Learning | 3 | continuous-learning-v2, skill-stocktake, codebase-onboarding |
| Ops | 5 | incident-response, accessibility-audit, monitor-setup, slo-implement |
| Session | 4 | save-session, resume-session, checkpoint, aside |
| Documentation | 2 | update-docs, update-codemaps |
| Build | 4 | build-fix, go-build, cpp-build, gradle-build |
| Multi-model | 3 | multi-plan, multi-execute, multi-workflow |

**By source:**

| Source | Count | Notes |
|--------|-------|-------|
| Original template | 48 | Core workflow + domain skills |
| ECC v1.9.0 import | 84 | Deduplicated, 41 overlaps skipped |
| Anthropic skills (Apache 2.0) | 8 | Adopted from plugin cache |
| Ops plugins (wshobson) | 13 | K8s, incident response, observability, accessibility |

**Plugin skills (proprietary, not redistributed):**

| Skill | Plugin | Purpose |
|-------|--------|---------|
| pdf | document-skills@anthropic-agent-skills | PDF creation, extraction, merge/split, OCR |
| docx | document-skills@anthropic-agent-skills | Word document creation and manipulation |
| pptx | document-skills@anthropic-agent-skills | PowerPoint presentation generation |
| xlsx | document-skills@anthropic-agent-skills | Excel spreadsheet processing |

### Commands (88)

**Original (56)** shown below. **ECC import (27)** added: /smart-fix, /rust-review, /rust-build, /rust-test, /kotlin-review, /kotlin-build, /kotlin-test, /cpp-review, /cpp-build, /cpp-test, /go-test, /prompt-optimize, /claw, /devfleet, /benchmark, /design-system, /deep-research, /context-budget, /loop-start, /loop-status, /skill-health, /projects, /promote, /prune, /docs, /pm2, /gradle-build. **Ops plugins (5)** added: /incident-response, /accessibility-audit, /monitor-setup, /slo-implement, /e2e.

| Command | Description |
|---------|-------------|
| **Setup & Config** | |
| /setup | Guided project setup wizard |
| /settings | Configure settings (presets: fast, minimal, safe, thorough, autoformat) |
| /health | Project health check with AgentShield status |
| /plugins | Plugin management |
| /mcps | MCP server management |
| **Task Management** | |
| /tasks | List Taskmaster tasks for current or specified tag |
| /task-status | Update Taskmaster task status |
| /prd | Show or parse PRD documents |
| /prd-generate | Research-backed PRD generation with architecture diagrams |
| /phase-check | Validate phase transition prerequisites |
| **Testing & Quality** | |
| /test | Run project test suite |
| /lint | Run linting and code quality checks |
| /verify | Full verification pipeline (test + lint + types + security) |
| /test-coverage | Analyze coverage gaps, generate missing tests |
| /tdd | Enforce test-driven development workflow |
| /go-test | Go TDD with table-driven tests and coverage |
| /e2e | Generate and run end-to-end tests (Playwright/Cypress) |
| /quality-gate | Run consolidated quality gate manually |
| **Code Review** | |
| /code-review | Comprehensive code review (quality + security) |
| /python-review | Python-specific review (PEP 8, type hints, idioms) |
| /go-review | Go-specific review (idioms, concurrency, security) |
| /security-audit | Security vulnerability scan (code-level OWASP) |
| **Implementation** | |
| /plan | Create implementation plan, wait for confirmation |
| /build-fix | Fix build and type errors incrementally |
| /go-build | Fix Go build errors and linter issues |
| /optimize | Performance analysis and optimization |
| /refactor-clean | Safe dead code removal with test verification |
| /generate-tests | Generate tests for specified file or module |
| **Planning & Research** | |
| /brainstorm | Structured brainstorming with approaches |
| /research | Structured research (papers, docs, exploration) |
| /multi-plan | Multi-model planning (Claude + Gemini + GPT) |
| /multi-execute | Multi-model implementation |
| /orchestrate | Multi-agent analysis pipeline (review, security, refactor) |
| /aside | Quick side question without losing current context |
| **Git & Release** | |
| /commit | Create conventional commit |
| /pr | Create GitHub Pull Request |
| /rollback | Guided rollback with session context |
| /changelog | Generate changelog from git history |
| /check-upstream | Check upstream repos for changes |
| /github-sync | Sync tasks with GitHub Issues |
| **Session & Learning** | |
| /sessions | Session history viewer with cleanup |
| /checkpoint | Manual session state save |
| /save-session | Save session state for later resume |
| /resume-session | Resume from saved session |
| /learn | Extract reusable patterns from current session |
| /learn-eval | Extract patterns with self-evaluation |
| /instinct-status | View learned instinct patterns and confidence scores |
| /instinct-import | Import instincts from shared JSON file |
| /instinct-export | Export instincts for team sharing |
| /evolve | Cluster instincts into new skills |
| /skill-create | Auto-generate skills from git commit history |
| **Documentation & Scoring** | |
| /update-codemaps | Generate architecture docs in docs/CODEMAPS/ |
| /update-docs | Trigger doc-updater agent on changed files |
| /eval | Code quality metrics with trend tracking |
| /model-route | Get model tier recommendation for a task |
| /harness-audit | Run deterministic template health scoring (70 points) |

---

## Development History

### v2.0.0 — v2.2.0: ECC Integration & Feature Parity

The template's development followed a deliberate research-first methodology: study the best existing implementations, understand their design decisions, then build something that combines their strengths with our unique requirements.

#### Phase 1: ECC Integration (15 tasks, 75 subtasks)

**The catalyst:** After building an initial template with workflow enforcement rules, proactive steering, and Task Master integration, we discovered [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) — a 45K+ star repository that won Anthropic's hackathon for Claude Code configuration. Rather than compete with ECC, we studied it systematically and integrated its best patterns.

**What we learned from ECC and adopted:**
- **Token optimization** was a blind spot. Our original template loaded 10 MCP servers (134 tools, 50K+ startup tokens) — violating ECC's own 10/80 rule. We reduced to 2 MCPs (42 tools, 25K startup). This single change recovered ~25K tokens of working context.
- **Session persistence** was critical. Without it, every session started from zero. ECC's pattern of saving session summaries on exit and reloading them on start meant context survived across sessions without manual effort.
- **Context modes** (dev/review/research) let the same template behave differently based on the task. A review session loads read-only rules and emphasizes thoroughness; a dev session loads write-first rules and emphasizes speed.
- **Agent architecture** with model tiering (Opus for high-stakes reasoning, Sonnet for frequent operations, Haiku for documentation) matched cost to value instead of using the most expensive model for everything.

**What we kept from our original design:**
- **Proactive steering** — Claude detects the development phase and adjusts behavior automatically. ECC doesn't have this.
- **Task Master integration** — AI-powered task management with dependencies, status tracking, and expansion. ECC uses a different approach.
- **Superpowers TDD enforcement** — The template requires the Superpowers plugin, which will delete production code written without failing tests. This is stricter than ECC's advisory TDD.

#### Phase 2: Full Feature Parity (35 tasks, 175 subtasks)

**Key implementation decisions:**
- **Language-specific rules use `paths:` frontmatter** so they load only when matching files are edited. A Python developer never pays the token cost for Go rules. This was our innovation — ECC loads all language rules at startup.
- **Skills use a profile system** (`manage-skill-profiles.sh`) — 153 skills organized into 22 categories, loaded via symlinks from `skills-available/`. The `minimal` profile loads 31 skills (~3K tokens), while `all` loads everything (~28K). Skill metadata IS always loaded for active skills, so profiles control real context cost.
- **The instinct system uses confidence scoring** (0.0-1.0) with automatic decay. Unused patterns lose 0.05 confidence per week and are removed when they reach 0. This prevents knowledge rot — outdated patterns fade naturally instead of persisting forever.

**Delivery:** 50 tasks, 250 subtasks total across both phases. All implemented through Claude Code itself — the template was built using the template's own workflow enforcement, which served as both a development tool and a stress test.

#### v2.1.0: The Honest Reckoning

After declaring "feature parity," we performed a quantitative audit against ECC's actual component inventory. The results were humbling — raw coverage was ~62% (we had claimed ~82% by counting functional equivalents). We fetched ECC's actual source code for every overlapping command and compared line-by-line, replaced 2 commands entirely where ECC's design was superior, merged improvements into 3 more, and added 6 new skills plus 12 agent-invoking commands.

#### v2.2.0: Feature Parity Completion

Completed ECC feature parity with 12 domain skills, 9 automation hooks, and documentation updates — all gap-analyzed against ECC's source code.

### v2.3.0: Template Overlay Infrastructure

Real-world overlay testing on three projects revealed a **critical architectural finding**: Claude Code's parent-directory traversal registers rules and CLAUDE.md from parent directories, but does NOT register commands, skills, or hooks. This meant all slash commands and skills were silently broken for any project that didn't have its own local `.claude/` directory.

Built `init-project.sh` (bootstraps local `.claude/` structure), `smoke-test.sh` (validates overlay deployments), and the `superpowers-integration.md` rule (fixes a workflow conflict where Superpowers brainstorming skill bypassed the template's PRD pipeline).

### v2.4.0: Dogfood Remediation

Systematic dogfood testing (Phases 0-6, 25 tasks, 263 tests, 21 commits) revealed 15 findings. Key discoveries:
- Claude uses MCP despite CLI documentation (4 violations) → added `taskmaster-usage.md` rule
- Process overhead degrades brainstorming → streamlined workflow
- Missing technical validation step → added VALIDATE phase between brainstorming and PRD
- TDD doesn't fit infrastructure tasks → added validation testing exceptions

### v2.5.0: Hook Architecture & Quality Infrastructure

Major infrastructure release adding:
- **Hook profile system** (minimal/standard/strict) — trade thoroughness for speed via `TEMPLATE_HOOK_PROFILE`
- **Quality gate consolidation** — `quality-gate.js` replaces 3 separate hooks with progressive delegation
- **Usage telemetry** — per-session token tracking to `cost-log.jsonl`
- **File size guard** — blocks source code files exceeding 800 lines (documentation/data files exempt)
- **Harness audit** — deterministic 70-point health scoring across 7 categories
- **Security hardening** — OWASP Agentic Top 10 mapping, config tamper guard, secret scrubbing in observations
- **Three new skills** — agentic-engineering, autonomous-loops, eval-metrics
- **Two new commands** — `/model-route`, `/harness-audit`

### v2.6.0: Skill Profiles & Ecosystem Expansion

The largest single expansion in template history, tripling the component count through structured imports and a new profile system to manage the resulting complexity.

**Skill profile system:**
- Moved all skills from `.claude/skills/` to `.claude/skills-available/` (git-tracked source of truth)
- `.claude/skills/` now contains symlinks managed by `scripts/manage-skill-profiles.sh`
- 15 named profiles (minimal, python, go, java, fullstack, all, etc.) across 22 categories
- `minimal` profile: 31 skills, ~3K metadata tokens. `all` profile: 153 skills, ~25K metadata tokens
- `toolkit` command shows related commands, agents, and rules per profile
- `TEMPLATE_SKILL_PROFILE` env var controls activation; `session-init.sh` recreates symlinks on fresh sessions

**ECC v1.9.0 import (84 skills, 15 agents, 27 commands):**
- Shallow-cloned ECC at commit `2166d80`, deduplicated against existing inventory
- Skipped 41 skill duplicates, 12 agent duplicates, 33 command duplicates
- Added language-specific build resolvers (Rust, Kotlin, C++, Java, Go) and reviewers
- Added multi-model commands (smart-fix, devfleet, claw) and session utilities

**Language rules expansion (51 new files, 6 new directories):**
- New languages: C#, Kotlin, Perl, PHP, Rust, Swift (5 rules each: coding-standards, testing, security, patterns, hooks)
- Deepened existing languages: Python, Go, Java, TypeScript, C++ (added testing, security, hooks, patterns)
- All use `paths:` frontmatter — zero startup cost when not editing that language

**Ops plugins (13 skills, 11 agents, 5 commands):**
- Extracted from wshobson/agents: accessibility-compliance, incident-response, observability-monitoring, kubernetes-operations
- New `ops` profile category covering K8s, Helm, GitOps, Prometheus, Grafana, SLOs, WCAG

**Anthropic document-skills plugin:**
- 4 proprietary skills (PDF, DOCX, PPTX, XLSX) via `/plugin marketplace add anthropics/skills`
- 8 Apache 2.0 example skills adopted into template, 3 Anthropic-specific deleted, 2 conflicting removed

**CI fixes:** Excluded `skills-available/` from ruff linting; skip mypy when `src/` doesn't exist.

### Project-Type Presets

One-command project scaffolding — a student can clone the template, run one command, and have a fully configured project:

| Preset | Stack | Skills Activated |
|--------|-------|-----------------|
| `python-fastapi` | FastAPI + SQLAlchemy + PostgreSQL | python-patterns, api-design, database-patterns, postgresql-patterns |
| `node-nextjs` | Next.js 14+ + React + TypeScript + Prisma | typescript-patterns, frontend-patterns, e2e-testing |
| `go-api` | Go stdlib + PostgreSQL + sqlc | golang-patterns, golang-testing, api-design, postgresql-patterns |
| `java-spring` | Spring Boot 3.2+ + JPA + PostgreSQL + Flyway | java-springboot, spring-boot-security, spring-boot-tdd, jpa-patterns |
| `python-data-science` | pandas + scikit-learn + Jupyter + matplotlib | python-patterns, python-testing, database-patterns |

```bash
./scripts/setup-preset.sh python-fastapi --name "My API Project"
# Or: /setup preset python-fastapi
```

---

## Future Roadmap

### Phase 1: Journel Server Deployment

The template moves from a WSL development environment to Journel (departmental Linux server), which changes several operational assumptions:

| Task | What Changes | Implementation |
|------|-------------|----------------|
| **Environment validation** | WSL has path quirks (`/mnt/c/` vs `/home/`). Native Linux eliminates these but may introduce different issues (permissions, package availability). | Run `/health` on Journel, fix any environment-specific failures. Validate all hooks execute correctly on the server's shell (bash version, node availability). |
| **Claude Code installation** | WSL had Claude Code pre-installed. Journel needs fresh installation with OAuth authentication. | Install via `npm install -g @anthropic-ai/claude-code`. Configure OAuth (no API key needed with Claude Pro). Verify MCP servers (Task Master, Context7) connect. |
| **Multi-model API keys** | `/multi-plan` and `/multi-execute` require Gemini and OpenAI API keys for full functionality. | Configure `.env` with `GOOGLE_AI_KEY` and `OPENAI_API_KEY`. Without these, multi-model commands gracefully degrade to Claude-only mode. |
| **Shared instinct repository** | Currently, instincts live in each developer's `.claude/instincts/`. For team use, instincts should be shareable. | Create a shared instinct directory on Journel. Use `/instinct-export` and `/instinct-import` to sync patterns between team members. |
| **Git configuration** | Journel may have different git credentials, SSH keys, and remote access. | Configure git with SSH key for GitHub access. Verify `git push` works from Journel to the template repository. |

### Phase 2: Team Collaboration Features

| Feature | Description | Value |
|---------|-------------|-------|
| **Shared instinct library** | Central repository of learned patterns that all team members' Claude instances can access. When one developer discovers a workaround, everyone benefits. | Eliminates redundant debugging across team members. A fix discovered on Monday is available to all teammates by Tuesday. |
| **Cross-project pattern extraction** | Analyze instincts across multiple projects to identify universal patterns vs project-specific ones. | Universal patterns become template-level skills. Project-specific patterns stay as project instincts. |
| **Team review aggregation** | Combine `/code-review` findings across team members to build a shared understanding of codebase quality. | Faculty can see aggregated quality metrics across all student projects without reviewing each one individually. |
| **Instinct conflict resolution** | When two developers' instincts contradict, surface the conflict and let the team decide which pattern wins. | Prevents "my Claude says X, your Claude says Y" disagreements by making learned patterns explicit and reviewable. |

### Phase 3: CI/CD Integration

The template's `/verify` pipeline currently runs locally. CI/CD integration runs it automatically on every push:

```yaml
# .github/workflows/template-verify.yml
name: Template Verification
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run test suite
        run: pytest --cov=src --cov-report=xml
      - name: Run linter
        run: ruff check .
      - name: Run type checker
        run: mypy src/
      - name: Run security scan
        run: bandit -r src/ -f json -o bandit-report.json
      - name: Upload coverage
        uses: codecov/codecov-action@v4
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            // Post verification results as PR comment
```

This means the same quality gates enforced locally by the template are also enforced in CI — no code merges to main without passing all stages.

### Phase 4: Metrics Dashboard

Track development quality and velocity over time:

| Metric | Source | What It Shows |
|--------|--------|---------------|
| **Test coverage trend** | pytest/jest coverage reports | Is coverage improving, stable, or declining? |
| **Commit frequency** | Git log analysis | How often are students committing? (Template enforces frequent commits) |
| **Security issue density** | `/security-audit` historical results | Are security practices improving over time? |
| **TDD compliance** | Superpowers enforcement logs | What percentage of code was written test-first? |
| **Instinct growth** | `.claude/instincts/` file count and confidence scores | Is the team's collective knowledge growing? |
| **Code quality scores** | `/eval` pass@k metrics | Are feature implementations becoming more reliable? |
| **Session costs** | `cost-log.jsonl` telemetry | Token usage trends, model distribution, cost per task |

This data enables faculty to assess not just *what* students built, but *how* they built it — measuring process quality alongside output quality.

### Phase 5: Academic Workflow Mode

Specialized rules and workflows for research-oriented development:

| Feature | What It Does |
|---------|-------------|
| **Experiment logging** | Automatically log hyperparameters, dataset versions, and results for ML experiments. Each run gets a timestamped entry in `experiments/`. |
| **Reproducibility checks** | `/verify` gains a reproducibility stage: checks for hardcoded paths, missing seed values, unversioned dependencies, and non-deterministic operations. |
| **Citation tracking** | When Claude references external libraries, papers, or techniques, it logs the citation. `/citations` generates a bibliography of all tools and references used. |
| **Notebook discipline** | Rules for Jupyter notebook hygiene: clear outputs before commit, no hardcoded credentials in cells, mandatory markdown headers explaining each section. |
| **Data pipeline validation** | Skills for validating data pipelines: schema checks, null handling, data drift detection, train/test leakage prevention. |
| **Thesis/paper integration** | `/update-docs` gains a mode for updating LaTeX or Markdown thesis chapters when the underlying code changes, keeping implementation descriptions in sync with actual code. |

### Phase 6: Custom Agent Creation Framework

Allow students and faculty to define project-specific agents without modifying the template core:

```markdown
<!-- .claude/agents/custom/ml-reviewer.md -->
---
model: sonnet
tools: Read, Grep, Glob
description: Review ML code for common mistakes
---

# ML Code Reviewer

Check for:
- Train/test data leakage
- Missing random seeds
- Hardcoded hyperparameters that should be configurable
- Incorrect loss function for the task type
- Missing model checkpointing
- Evaluation on training data
```

This turns domain expertise into reusable AI configuration. A professor who knows ML anti-patterns writes them once as an agent definition, and every student's Claude instance enforces them automatically.

---

## Conclusion

The gap between "AI writes code" and "AI assists in engineering high-quality software" is not a matter of model capability — it's a matter of **scaffolding**. This template bridges that gap by providing:

1. **Structure** where raw LLMs offer none
2. **Enforcement** where raw LLMs only suggest
3. **Specialization** where raw LLMs generalize
4. **Memory** where raw LLMs forget
5. **Efficiency** where raw LLMs waste resources

The template is not a replacement for understanding software engineering. It is a **force multiplier** that ensures the AI's considerable capabilities are channeled through disciplined processes, producing output that meets professional standards rather than merely appearing to.

Any student using this template starts their project with the workflow enforcement, quality gates, and domain expertise that typically takes years of professional experience to internalize. The template makes the right way the easy way.

---

*Built with Claude Code (Anthropic) | Informed by Everything Claude Code (45K+ stars)*
*Template v2.6.0 | 40 agents, 153 skills, 88 commands, 68 rules, 22 hooks, 15 profiles | 70/70 harness score*
