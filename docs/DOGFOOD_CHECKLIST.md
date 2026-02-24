# Dogfood Test Checklist — Project Template v2.3.1

**Target project**: `postiz-social-automation`
**Starting state**: No `.claude/`, no `.taskmaster/`, no `CLAUDE.md` — clean slate
**Template source**: `~/projects/project-template` (v2.3.1)

---

## How to Use This Checklist

Each item has:
- **Trigger**: What initiates this step
- **Expected Output**: What you should see (verbatim where possible)
- **Enforcement**: `HOOK` (hard block), `NORMATIVE` (rule, Claude discipline), or `ADVISORY` (suggestion only)
- **Known Gotchas**: Past failures from MEMORY.md or prior sessions

Mark each: `[x]` pass, `[!]` fail (note details), `[-]` skipped (with reason)

---

## Phase 0: Project Bootstrap

### 0.1 Create Project & Git Init

- **Trigger**: Manual — create project directory and initialize git
- **Commands**:
  ```bash
  mkdir -p ~/projects/postiz-social-automation
  cd ~/projects/postiz-social-automation
  git init
  git commit --allow-empty -m "chore: Initial commit"
  ```
- [x] Directory exists at `~/projects/postiz-social-automation` — actual path `~/projects/ISKCON-GN/postiz_social_automation`. Pre-existing from Run 1 + α2 work, reset to clean state via `71b84ee chore: Reset to clean state for dogfood Run 2`.
- [x] Git repo initialized with at least one commit (required for hooks) — 5 commits from Run 1 dogfood prep, most recent `71b84ee`
- **Enforcement**: PREREQUISITE — hooks and Task Master require a git repo
- **Gotcha**: Some hooks call `git log` or `git diff` and fail on repos with zero commits

### 0.2 Run init-project.sh

- **Trigger**: Manual — run from inside the postiz project directory
- **Command**: `~/projects/project-template/scripts/init-project.sh`
- [x] Auto-detects template at `~/projects/project-template` (parent walk or script-path detection) — detected via script-path, reported `Template: /home/cjh5690/projects/project-template`
- [x] Mode reported: `symlink` (projects are siblings, so should be copy mode — verify which!) — reported `copy` mode, correct since projects are in different parent dirs (`ISKCON-GN/` vs root `projects/`)
- [x] `.claude/` directory created — confirmed with 8 items (6 subdirs + settings.json + settings.local.json)
- [x] Symlinks OR copies created for: `rules/`, `commands/`, `skills/`, `agents/`, `contexts/`, `hooks/` — all 6 copied: rules/ (14 files), commands/ (48), skills/ (40), agents/ (14), contexts/ (3), hooks/ (20)
- [x] Each directory has files (not empty) — confirmed, 139 files total
- [x] Summary shows `Created: 6` (or appropriate count) — `Created: 9` (6 dirs + settings.json + .taskmaster/config.json + .template/). **Run 1 showed Created: 6 — improvement: init-project.sh now also creates settings.json, taskmaster config, and .template/ tracking.**
- [x] No errors or warnings about missing directories — clean run, 0 skipped, 0 warnings
- **Enforcement**: PREREQUISITE — without this, no commands/skills/hooks work
- **Gotchas**:
  - Script uses `python3` for `calc_relative_path` — must be installed
  - If projects are siblings (not nested), auto-detect may fall back to copy mode via `DEFAULT_TEMPLATE_PATH`
  - Previous bug: hardcoded path `~/projects/project-template` — fixed in v2.3.1 (now auto-detects from script location)

### 0.3 Verify settings.json Copied/Created

- **Trigger**: Part of init-project.sh (hooks/ directory includes settings.json reference)
- [x] `.claude/settings.json` exists in the project — **Run 1 FAILURE NOW FIXED**: init-project.sh now creates `.claude/settings.json` directly (output line: `[CREATE] .claude/settings.json (hook definitions)`). No manual copy needed. This was the #1 Run 1 failure.
- [x] Contains all hook definitions (SessionStart, PreToolUse, PostToolUse, UserPromptSubmit, Stop) — confirmed all 5 event types with 18 hooks total including observe.sh wildcard matchers
- [x] Hook paths use `$CLAUDE_PROJECT_DIR` prefix (portable across machines) — confirmed, every hook path starts with `$CLAUDE_PROJECT_DIR/.claude/hooks/`
- **Enforcement**: PREREQUISITE — without settings.json, zero hooks fire
- **Gotcha**: settings.json is in `.claude/hooks/` in the template but Claude Code reads from `.claude/settings.json`. Verify init-project.sh handles this correctly OR document that settings.json must be manually copied/symlinked to `.claude/settings.json`.

### 0.4 Create CLAUDE.md

- **Trigger**: Manual — copy template CLAUDE.md and customize for postiz project
- [x] `CLAUDE.md` exists at project root — created from template, customized for Postiz project
- [x] Project name, tech stack, and structure sections filled in — "Postiz Social Media Automation", Docker/PostgreSQL/Redis/Temporal/Python/n8n stack, project structure reflecting Docker infra + automation layer to be built
- [x] Taskmaster workflow section preserved (PRD first, new tag per phase, etc.) — all 5 mandatory workflow rules preserved verbatim from template
- **Enforcement**: NORMATIVE — Claude reads CLAUDE.md every session
- **Gotcha**: CLAUDE.md is project-specific and should NOT be symlinked from template

### 0.5 Initialize Task Master

- **Trigger**: Manual — `task-master init` in the project
- **Command**: `task-master init`
- [x] `.taskmaster/` directory created with `tasks/`, `reports/`, `docs/` subdirectories — all 3 created by init-project.sh directly (no separate `task-master init` needed)
- [x] `.taskmaster/config.json` created — **Run 1 FAILURE NOW FIXED**: init-project.sh now creates config from template with correct values. Output line: `[CREATE] .taskmaster/config.json (configured, project: postiz_social_automation)`.
- [x] Config has correct `projectName` (not template default) — `"postiz_social_automation"` (auto-derived from directory name). Run 1 had to manually fix from "Taskmaster" default.
- [x] Config has `maxTokens: 200000` (not the `task-master init` default of 32000) — confirmed `200000` on all 3 model configs (main/research/fallback). Provider is `claude-code`, models are `opus`/`opus`/`sonnet`. Run 1 got 120000 from MCP init.
- **Enforcement**: PREREQUISITE — Task Master CLI won't work without init
- **Gotchas**:
  - `task-master init` creates config with its own defaults (32k tokens, wrong project name) — MUST manually edit
  - If `.taskmaster/tasks/` doesn't exist, `task-master tags add` fails silently
  - init-project.sh creates `.taskmaster/{tasks,reports,docs}/` IF `.taskmaster/` already exists — so run `task-master init` FIRST, then re-run init-project.sh, OR manually mkdir

### 0.5.5 Restart Claude Code

- **Trigger**: Manual — after completing steps 0.1–0.5
- **Action**: Exit Claude Code (`/exit` or Ctrl+C), then restart in the project directory
- [x] Claude Code exited cleanly — user ran `/exit`, got "Goodbye!" confirmation
- [x] Claude Code restarted in the project directory — confirmed by new session start
- [x] Hooks, rules, and CLAUDE.md are now loaded (verified by session-init output in Phase 1.1) — confirmed: `SessionStart:resume hook success: Success` fired, Project Status box displayed, pre-compact.sh fired on first prompt, 14 rule files loaded, CLAUDE.md in context, 15 Superpowers skills loaded. **Run 1 note**: `.template/version` file now exists (created by init-project.sh), so version comparison works. Run 1 had to manually create this file.
- **Enforcement**: PREREQUISITE — hooks, rules, and CLAUDE.md only load at session startup. Without restart, none of the behavioral enforcement installed in 0.2–0.4 is active.
- **Gotcha**: Skipping this restart is invisible — everything appears to work, but hooks don't fire and rules aren't loaded. This is the most common onboarding mistake.

### 0.6 Install Superpowers Plugin

- **Trigger**: Manual — follow CLAUDE.md instructions
- **Commands**:
  ```
  /plugin marketplace add obra/superpowers-marketplace
  /plugin install superpowers@superpowers-marketplace
  ```
- [x] Superpowers skills appear in skill list (brainstorming, test-driven-development, etc.) — confirmed: 15 `superpowers:*` skills in session system-reminder (brainstorming, test-driven-development, writing-plans, executing-plans, systematic-debugging, requesting-code-review, receiving-code-review, finishing-a-development-branch, verification-before-completion, dispatching-parallel-agents, subagent-driven-development, using-git-worktrees, writing-skills, using-superpowers, keybindings-help)
- [x] `superpowers:brainstorming` is invocable — listed as available skill in Skill tool
- [x] `superpowers:test-driven-development` is invocable — listed as available skill in Skill tool
- **Enforcement**: PREREQUISITE — without Superpowers, TDD is advisory-only (not enforced)
- **Gotcha**: Superpowers detection in session-init.sh checks `find` + skills directory — improved in v2.3.1

### 0.7 Verify MCP Servers Connected

- **Trigger**: Start a Claude Code session in the project
- [x] Task Master MCP responds (test: `task-master list`) — confirmed: v0.43.0, `get_tasks` returned empty task list on `master` tag with 0/0 stats. No `.mcp.json` override issue this time (Run 1 failure #5 avoided — no local `.mcp.json` was created on restart).
- [x] Context7 MCP responds (test: resolve a library ID) — confirmed: resolved FastAPI to `/websites/fastapi_tiangolo` with 21.4k snippets, High reputation, score 91.4
- **Enforcement**: PREREQUISITE — Task Master MCP needed for data ops
- **Gotcha**: MCP servers are user-level config (`~/.claude/settings.json`), not project-level

---

## Phase 1: Session Start

### 1.1 session-init.sh Fires

- **Trigger**: `SessionStart` hook — fires when Claude Code session begins
- [x] Hook runs without errors (check for `SessionStart:startup hook success` in system message) — confirmed: `SessionStart:resume hook success: Success`
- [!] Project phase detected and displayed (IDEATION for new project) — **NOT SHOWN as "IDEATION"**. Session-init output was just "Success". The Project Status box from project-index.sh showed template update banner but no phase label. Same behavior as Run 1 — session-init.sh doesn't display a workflow phase indicator. **Recurring issue**: no phase detection output despite `.template/version` now existing.
- [x] Template version shown: `v2.3.1` — **FIXED from Run 1**: Project Status box shows `Installed: v2.3.1 → Latest: v2.3.1`. The `.template/version` file (now auto-created by init-project.sh) enables this. Run 1 couldn't show version because the file was missing.
- [x] No stale session summaries loaded (fresh project) — confirmed: only `pre-compact-state.md` exists in `.claude/sessions/`, no prior session summaries
- [!] Update banner NOT shown (installed version should match current) — **PARTIAL FAIL**: Banner says "TEMPLATE UPDATE AVAILABLE" with `Installed: v2.3.1 → Latest: v2.3.1` (same version!) and lists "Missing components: mcp-registry.json sync-template.sh". The update detection is version-match but flags missing files as an update. Not a blocking issue but misleading UX.
- **Enforcement**: HOOK — fires automatically
- **Gotchas**:
  - If `.template/version` file doesn't exist, version comparison may error
  - Hook assumes `jq` is installed for some operations

### 1.2 project-index.sh Fires

- **Trigger**: `SessionStart` hook — runs after session-init.sh
- [x] `Project index updated` message appears in system reminders — Project Status box appeared from project-index.sh hook (displayed template status info). **Run 1 FAILURE NOW FIXED**: project-index.sh no longer shows "PROTO-TEMPLATE DETECTED" — it correctly generates an index and shows project status.
- [x] `.claude/project-index.json` created/updated — confirmed: 308 bytes, generated at `2026-02-23T21:52:37`. **Run 1 FAILURE NOW FIXED**: file was not created in Run 1 (hook focused on template detection instead). Now creates valid JSON index.
- [x] Index contains file tree of the project — confirmed: contains `docker-compose.yaml` with signatures, `dynamicconfig/docker.yaml`, and structure listing `docs` and `dynamicconfig` dirs. Minimal but correct for a project with few source files.
- **Enforcement**: HOOK — fires automatically
- **Gotcha**: On empty projects, index will be minimal (just CLAUDE.md, .claude/, .taskmaster/)

### 1.3 pre-compact.sh Fires

- **Trigger**: `UserPromptSubmit` hook — fires on EVERY user message
- [x] `Pre-compaction state saved` message appears — confirmed: `UserPromptSubmit hook success: Pre-compaction state saved to .../pre-compact-state.md`
- [x] `.claude/sessions/pre-compact-state.md` created — confirmed: 455 bytes, saved at 21:53:25. Contains active task (none), tag (master), TDD phase (N/A), branch (main), and 5 uncommitted files listed.
- **Enforcement**: HOOK — fires every prompt
- **Gotcha**: This fires on every single user message, not just before compaction — it's preemptive

### 1.4 suggest-compact.sh Fires

- **Trigger**: `UserPromptSubmit` hook — fires on every user message
- [x] Silent on early messages (no output until 50+ tool calls) — confirmed: no suggest-compact output on first prompt (only pre-compact fired). Tool call count is low.
- [-] At 50 tool calls: advisory suggestion appears — skipped: session too new to reach 50 tool calls. Will verify later in session if reached.
- [-] At 75 tool calls: stronger suggestion — skipped: same reason
- [-] At 100 tool calls: urgent suggestion — skipped: same reason
- **Enforcement**: ADVISORY — suggestions only, no blocking
- **Gotcha**: Counter resets on session restart. Token-based, not message-based.

---

## Phase 2: Ideation (Brainstorming)

### 2.1 Skill Detection

- **Trigger**: User describes a feature to build (e.g., "I want to build a social media automation tool")
- [x] Claude detects that brainstorming skill applies — detected from startup prompt describing feature work ("build the automation layer")
- [x] `superpowers:brainstorming` skill is invoked BEFORE any code or planning — invoked immediately at Phase 2 start, before any code or planning. Created 6-item brainstorming checklist via TaskCreate.
- **Enforcement**: NORMATIVE (Superpowers) — skill should be invoked for any creative/feature work
- **Gotcha**: If Superpowers not installed, brainstorming is advisory only

### 2.2 Research & Context Intake

- **Trigger**: Brainstorming skill's first step: "Explore project context — check files, docs, recent commits"
- [x] Claude reads ALL existing research docs in `docs/` (non-dogfood files)
  - `gita-valley-context.md` — Read: 179 lines. Client profile (430-acre farm, 85 cows, 4.4K IG / 5.7K FB followers), social accounts with handle/follower data, content pillars (40/25/15/10/5/5), posting cadence targets, rebrand status, key people (Seth, Dhruva, PJ, Madhupan).
  - `gita-valley-online-presence-audit-v2.md` — Read: 275 lines. Platform-by-platform audit with engagement data (0.2-0.4% vs 3-6% benchmark), rebrand gap matrix (only website + IG rebranded), viral TikTok paradox (1,200 apps from intern's TikTok vs 198 official followers), P0-P4 priority actions.
  - `social-media-automation-assessment.md` — Read: 201 lines. Postiz + n8n recommended ($10-25/mo). Architecture: n8n = brain, Postiz = hands. Postiz API beta (30 req/hr). n8n-nodes-postiz v0.2.17 installed. Platform app approvals can take 1+ months.
  - `N8N_INTEGRATION.md` — Read: 45 lines. n8n connects via community node, operations: Create/Get/Delete Post, network config for cross-host communication.
- [x] Claude reads/analyzes existing infrastructure (Docker Compose, service config) if present — Read docker-compose.yaml: 7 services (postiz on 4007:5000, postiz-postgres, postiz-redis, temporal on 7233, temporal-postgresql, temporal-elasticsearch, temporal-ui on 8080). All on postiz-network bridge. Full production-ready stack.
- [x] Research findings are explicitly referenced when proposing approaches (not generic suggestions) — design doc references specific data: engagement rates, follower counts, cow names, pillar weights, API rate limits, platform rebrand status, posting cadence targets, infrastructure URLs
- [x] Technology constraints from research are acknowledged (Postiz API beta limits, n8n capabilities, platform app approvals) — design doc includes: API 30 req/hr limit with backoff strategy, platform app approval timeline, n8n community node capabilities, deployment constraint (Seth manages server)
- **Enforcement**: NORMATIVE (Superpowers brainstorming skill step 1 + startup prompt)
- **Context**: In α2, comprehensive domain audits (online presence audit, tech assessment) were created as part of the workflow and informed all subsequent design. These docs already exist in the project — the brainstorming must incorporate them, not ignore them.
- **Gotcha**: The brainstorming skill says "check files, docs, recent commits" but doesn't enforce it. If Claude skips this step, the design doc and PRD will be generic rather than domain-informed.

### 2.3 Brainstorming Process

- **Trigger**: `superpowers:brainstorming` skill loaded, research intake complete
- [x] Claude explores user intent before jumping to solutions — yes, but POORLY initially. First attempt asked meta-scope questions ("do we need Python?"). After user correction, restarted with domain synthesis showing understanding before asking questions. Required 2 restarts to get right.
- [!] Multiple approaches considered (at least 2-3) — **PARTIAL FAIL**: Initial attempts offered approaches but at wrong abstraction level (Python scope options, not pipeline design options). After restart, converged on single approach (n8n + Postiz + Sheets) through Q&A rather than presenting 2-3 competing architectures. The architecture was effectively pre-decided by the research docs, so multiple approaches were less relevant.
- [x] Approaches reference specific findings from research docs (e.g., API rate limits, platform rebrand status, content pillar weights) — yes, after restart. Design doc references: 0.2-0.4% engagement, 30 req/hr API limit, specific cow names, pillar weights, rebrand status per platform, follower counts.
- [x] Trade-offs discussed with domain-specific context (not abstract pros/cons) — approval workflow discussion was domain-informed (spiritual community needs content review). Media handling, AI provider choices grounded in existing infra.
- [x] User confirms direction before proceeding — user confirmed design looks correct before doc was written
- **Enforcement**: NORMATIVE (Superpowers skill instructions)

### 2.4 Design Doc Quality Check

- **Trigger**: Brainstorming produces design doc
- [x] Design doc references specific data from research docs (follower counts, API limits, platform statuses) — includes: 4,414 IG / 5,700 FB / 198 TikTok followers, 30 req/hr API limit, rebrand status per platform, 0.2-0.4% engagement vs 3-6% benchmark
- [x] Architecture decisions are grounded in the technology assessment (not reinvented from scratch) — "n8n = brain, Postiz = hands" architecture directly from assessment doc. Claude via OAuth/Max (not API billing). Google Sheets + Drive from assessment options.
- [x] Content strategy alignment: design doc reflects the 40/25/15/10/5/5 pillar weights and 70/20/10 mix — both captured with per-pillar tone adjustments (cow names, "gentle not doctrinal" for spiritual, etc.)
- [x] Infrastructure constraints captured: Docker stack, Postiz API beta limits, separate hosts for n8n/Postiz — all captured: 7 Docker services, 30 req/hr limit with backoff, Seth manages server, n8n at sethpc.xyz
- **Enforcement**: NORMATIVE (quality verification)
- **Context**: α1's design doc was 185 lines with detailed architecture, data flow, and phased rollout — all informed by the research docs. This is the quality bar.

### 2.5 Brainstorming Exit — CRITICAL OVERRIDE

- **Trigger**: Brainstorming skill completes
- [x] Design doc saved to `docs/plans/YYYY-MM-DD-<topic>-design.md` — saved to `docs/plans/2026-02-23-social-automation-pipeline-design.md`
- [x] **Does NOT route to `writing-plans`** — correctly routing to PRD creation per `superpowers-integration.md` rule override. Did not invoke writing-plans. **Run 1 noted this was broken TWICE in prior sessions — passes in Run 2.**
- [x] Instead routes to PRD creation (Phase 3) — transitioning to PRD now
- **Enforcement**: NORMATIVE (rule override in `.claude/rules/superpowers-integration.md`)
- **Gotcha**: **This was broken TWICE in prior sessions.** The Superpowers brainstorming skill explicitly says to invoke `writing-plans` as terminal state. Our rule overrides this. Verify Claude follows the rule, not the skill's default exit.

---

## Phase 3: Planning (PRD & Task Generation)

### 3.1 PRD Creation

- **Trigger**: After brainstorming completes (or if requirements are already clear)
- [x] PRD written to `.taskmaster/docs/prd_<slug>.txt` — `.taskmaster/docs/prd_social_automation.txt` (215 lines)
- [x] PRD contains: overview, architecture, technology stack, requirements, success criteria — all sections present plus non-goals, error handling table, success metrics, posting cadence, social accounts table
- [x] PRD contains a **Dependency Graph** section with layered dependencies — each Phase has `Depends on:` marker (Phase 1: nothing, Phase 2: Phase 1.4+1.5, Phase 3: Phase 2, Phase 4: Phase 3 + 3 weeks data)
  - [x] Foundation layer modules have NO dependencies — Phase 1 has no dependencies
  - [x] Each non-foundation module has explicit `Depends on [X, Y]` markers — all 3 later phases have explicit dependency markers
  - [x] Dependencies form a DAG (no circular references) — linear phase chain: 1→2→3→4
  - [x] Modules within the same layer that don't depend on each other are identifiable as parallelizable — Phase 1 items (1.1-1.5) are independent; channel connections (1.3) are parallel
- [x] PRD is NOT in random location (should be in `.taskmaster/docs/`) — correct location
- **Enforcement**: NORMATIVE (CLAUDE.md: "ALWAYS create a PRD before generating tasks")
- **Context**: The dependency graph is the most valuable section for `task-master parse-prd`. Without it, the parser must infer dependencies from prose — often incorrectly. `/prd-generate` now includes Phase 3.5 (Dependency Analysis) that produces this structure automatically.
- **Gotcha**: doc-file-blocker.sh may block `.md` files outside `docs/` — PRD uses `.txt` extension intentionally
- **Gotcha**: α1's PRD lacked explicit dependency chains. Combined with skipping `analyze-complexity` (which caused the default 5 subtasks per task), this produced poorly-ordered, flat task decomposition.

### 3.2 Create Tag for This Phase

- **Trigger**: Before parsing PRD into tasks
- **Command**: `task-master tags add <tag-name>` then `task-master tags use <tag-name>`
- [!] New tag created (e.g., `postiz-mvp` or `feature-automation`) — **FAILED**: `task-master tags add postiz-mvp` failed because `tasks.json` didn't exist yet. Tags require an existing tasks file. Tasks went to `master` tag instead.
- [!] Tag is active (verified with `task-master tags list`) — failed, stuck on `master`
- [!] Tasks are NOT being added to `master` tag — **FAILED**: all 30 tasks created in `master` tag due to tag creation failure above
- **Enforcement**: NORMATIVE (CLAUDE.md: "Each workflow phase gets its own tag")
- **Gotcha**: Tag ID spaces are independent — each tag starts at ID 1

### 3.3 Parse PRD into Tasks

- **Trigger**: PRD exists, tag is active
- **Command**: `task-master parse-prd --input=.taskmaster/docs/prd_<slug>.txt --num-tasks=0 --force`
- [!] Command executes WITHOUT hanging (no interactive prompt) — **USED MCP INSTEAD OF CLI** (see failure #4). MCP `parse_prd` succeeded but violates documented guidance: AI ops should use CLI, not MCP. MCP's `claude-code` provider spawns nested subprocess which can be blocked.
- [x] Output visible in terminal (not swallowed by ANSI codes) — MCP returned structured JSON, no ANSI issue
- [!] Tasks created in the active tag — created in `master` (tag creation failed, see 3.2)
- [x] Task count is AI-determined (not hardcoded) — 30 tasks generated with `--num-tasks=0`
- [x] `task-master list` shows the new tasks — `task-master list -c` confirmed 30 tasks
- **Enforcement**: NORMATIVE (workflow rule)
- **Gotchas** (CRITICAL — these are the most common failures):
  - **MUST use `--force` flag** — without it, interactive confirmation prompt blocks in non-interactive pipes
  - **MUST use long timeout** (900000ms / 15 min) — AI ops exceed default 2-min Bash timeout
  - **NEVER use `2>&1`** — merging stderr corrupts output (ANSI progress spinners make stdout appear empty)
  - **Must use CLI, not MCP** — `parse-prd` is an AI op; MCP's `claude-code` provider tries to spawn nested Claude subprocess which is blocked
  - Run command bare: `task-master parse-prd --input=<file> --num-tasks=0 --force`

### 3.4 Verify Task Output

- **Trigger**: After parse-prd completes
- **Command**: `task-master list -c` (compact, ~200 tokens)
- [x] Tasks listed with IDs, titles, and statuses — `task-master list -c` showed all 30 tasks
- [x] All tasks are `pending` status — confirmed, all `○` (pending)
- [x] Task titles are meaningful (not generic) — e.g., "Build AI Caption Generation Workflow", "Implement Rate Limiting for Postiz API"
- [x] Dependencies are reasonable (if set) — task-master set dependencies from PRD phase markers
- **Enforcement**: NORMATIVE (verification step)
- **Gotcha**: Use `task-master list -c` for token efficiency — NEVER `get_tasks` with `withSubtasks: true` for orientation (dumps ~19.5k tokens)

---

## Phase 4: Complexity Analysis

### 4.1 Analyze Complexity

- **Trigger**: After tasks are parsed from PRD
- **Command**: `task-master analyze-complexity`
- [!] Command runs without error — **USED MCP INSTEAD OF CLI** (see failure #5). MCP `analyze_project_complexity` succeeded but violates documented guidance. Should have used `task-master analyze-complexity` CLI.
- [x] Output may be empty/garbled (known rendering bug) — MCP returned full structured report (no ANSI issue since MCP bypasses terminal). CLI would have had the rendering bug.
- **Enforcement**: NORMATIVE (workflow rule: always analyze before expanding)
- **Gotcha**: **`analyze-complexity` has stdout rendering bug** — ANSI progress codes swallow output. This is expected. Always follow with `complexity-report`.

### 4.2 View Complexity Report

- **Trigger**: After analyze-complexity completes
- **Command**: `task-master complexity-report`
- [x] Report displays with per-task complexity scores (1-10) — scores range 1-7 across 30 tasks
- [x] Each task has an expansion recommendation (number of subtasks) — 0 subtasks for low-complexity, 3-4 for medium
- [x] Tasks scored >= 5 flagged for expansion — 12 tasks flagged (IDs: 10, 11, 15, 17, 18, 19, 20, 21, 23, 24, 25, 28)
- [x] Report is readable (not garbled by ANSI) — used MCP which returned structured JSON; CLI would need `complexity-report` workaround
- **Enforcement**: NORMATIVE (this is the workaround for 4.1's rendering bug)
- **Gotcha**: Pipeline must be: `parse-prd → analyze-complexity → complexity-report → expand`

---

## Phase 5: Task Expansion

### 5.1 Expand Complex Tasks

- **Trigger**: Complexity report shows tasks with score >= 5
- **Command**: `task-master expand --id=<id> --force` (per complex task)
- [x] Expansion runs for each task scoring >= 5 — all 12 tasks expanded. First 6 via MCP (wrong, see failure #6), last 6 via CLI (correct after user flagged the issue)
- [x] Subtasks created with meaningful titles — e.g., "Build Claude API HTTP Request Node with Prompt Composition", "Add Max 3 Attempts Logic with Final Error Marking"
- [x] Simple tasks (score < 5) NOT expanded (unless user requests) — 18 low-complexity tasks left unexpanded
- [x] Output visible in terminal — CLI expansions showed clean output with telemetry; MCP returned structured JSON
- **Enforcement**: NORMATIVE (threshold rule from MEMORY.md)
- **Gotchas**:
  - **Score >= 5 = ALWAYS expand** even if AI recommends 0 subtasks
  - Use `--force` to avoid interactive prompts
  - Long timeout needed (900000ms)
  - Do NOT use `expand --all` blindly — respects complexity report
  - NEVER use `2>&1` (same ANSI corruption issue as parse-prd)

### 5.2 Verify Expanded Tasks

- **Trigger**: After all expansions complete
- **Command**: `task-master list -c --with-subtasks` (~1-2k tokens)
- [x] Full task tree visible with parent tasks and subtasks — `task-master list -c --with-subtasks` shows 30 tasks + 41 subtasks
- [x] Subtask IDs use dot notation (e.g., `1.1`, `1.2`) — confirmed: e.g., task 10 has subtasks 10.1, 10.2, 10.3
- [x] Dependencies between subtasks are reasonable — subtasks within each task have sequential dependencies (e.g., 15.1→15.2→15.3→15.4)
- **Enforcement**: NORMATIVE (verification step)
- **Gotcha**: Only use `--with-subtasks` once at this point and once on session resume — it's heavier than compact list

---

## Phase 6: Implementation (TDD per Task)

### 6.1 Pick Next Task

- **Trigger**: Ready to implement
- **Command**: `task-master next` or `task-master list --ready --blocking`
- [x] Returns a task/subtask with all dependencies satisfied — `task-master next` returned Task 1 (no deps), then Task 8 (no deps) after Task 1 completed
- [x] Task is the highest-impact starting point — Task 1 (infra verification) is correct foundation task
- **Enforcement**: NORMATIVE (workflow rule)

### 6.2 Set Task In-Progress

- **Trigger**: Starting work on a task
- **Command**: `task-master set-status <id> in-progress`
- [x] Status updated successfully — both Task 1 and Task 8 set in-progress before work began
- [x] Only ONE task is in-progress at a time — Task 1 set done before Task 8 started
- **Enforcement**: NORMATIVE (one task in-progress rule from workflow-enforcement.md)

### 6.3 Create Feature Branch

- **Trigger**: Starting implementation work
- **Command**: `git checkout -b feature/<descriptive-name>`
- [x] Branch created from main — `feature/postiz-mvp` created from main
- [x] Branch name follows convention: `feature/`, `bugfix/`, `hotfix/` — `feature/postiz-mvp`
- [x] NOT working directly on main — all commits on feature branch
- **Enforcement**: HOOK (pre-commit-check.sh blocks commits to main)

### 6.4 Superpowers TDD — RED Phase

- **Trigger**: `superpowers:test-driven-development` skill invoked
- [-] Skill is invoked BEFORE writing any production code — SKIPPED: Tasks 1 (infra verification) and 8 (Google Sheets schema) are config/documentation tasks, not code. TDD not applicable.
- [-] Failing test written FIRST — SKIPPED: no testable code produced yet
- [-] Test describes the expected behavior — SKIPPED
- [-] Test actually FAILS when run (not a false pass) — SKIPPED
- **Enforcement**: NORMATIVE (Superpowers TDD) — if installed, Superpowers may delete code written without tests
- **Gotcha**: Superpowers TDD is strict — it deletes production code written without failing tests first
- **Finding #9**: Tasks 1-8 in our PRD are infrastructure/config tasks with no testable code. TDD only becomes relevant at Task 10+ (n8n workflow building). The PRD's task ordering front-loads manual/config work before code — this is correct for dependency ordering but means TDD won't be exercised until mid-implementation.

### 6.5 Superpowers TDD — GREEN Phase

- **Trigger**: Failing test exists
- [-] Minimal production code written to make test pass — SKIPPED: no TDD tasks reached yet
- [-] Test now PASSES — SKIPPED
- [-] No other tests broken — SKIPPED
- **Enforcement**: NORMATIVE (Superpowers TDD)

### 6.6 Superpowers TDD — REFACTOR Phase

- **Trigger**: Test passes
- [-] Code cleaned up (if needed) — SKIPPED
- [-] All tests still pass after refactor — SKIPPED
- [-] No behavior changes — SKIPPED
- **Enforcement**: NORMATIVE (Superpowers TDD)

### 6.7 Commit After TDD Cycle

- **Trigger**: TDD cycle complete (RED-GREEN-REFACTOR), or non-TDD task complete
- [x] `git add <specific-files>` (not `git add .`) — used specific file lists for all 3 commits
- [x] Commit message uses conventional format: `feat:`, `fix:`, `test:`, etc. — `feat:` for Tasks 1 and 8, `docs:` for research
- [x] pre-commit-check.sh validates commit message format — hook ran on all commits
- [x] pre-commit-check.sh blocks if committing to main branch — on feature/postiz-mvp, not main
- [x] Commit succeeds — 3 commits: `ded866b`, `ff9f2a8`, `75b2d36`
- **Enforcement**: HOOK (pre-commit-check.sh)
- **Gotcha**: Hook checks conventional commit format — "Fixed bug" will be rejected, must be "fix: ..."

### 6.8 Hook Triggers During Implementation

These hooks fire during normal coding work:

#### 6.8a protect-sensitive-files.sh
- **Trigger**: PreToolUse on `Edit` or `Write`
- [x] Blocks edits to `.env`, `credentials.json`, `secrets.json`, `*.pem`, `*.key` — confirmed: Write to `.env` was blocked with "protect-sensitive-files.sh" error
- [ ] Blocks edits to files in `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, `venv/`
- [x] Allows `.env.sample`, `.env.example` — confirmed: Edit to `.env.example` succeeded
- [x] Allows normal source files — confirmed: all other file writes/edits succeeded
- **Enforcement**: HOOK (exit 2 = block)

#### 6.8b doc-file-blocker.sh
- **Trigger**: PreToolUse on `Write`
- [ ] Blocks creating `.md` files outside `docs/`, `.claude/`, `.taskmaster/`, `.github/`
- [ ] Allows creating `.md` files in allowed directories
- [ ] Allows non-`.md` files anywhere
- **Enforcement**: HOOK (exit 2 = block)

#### 6.8c post-edit-format.sh
- **Trigger**: PostToolUse on `Edit` or `Write`
- [ ] Auto-formats edited files (runs formatter if configured)
- [ ] Silent if no formatter configured for file type
- **Enforcement**: HOOK (auto-runs, advisory output)

#### 6.8d console-log-audit.sh
- **Trigger**: PostToolUse on `Edit`
- [ ] Warns if debug statements added (print, console.log, debugger, etc.)
- [ ] Silent if no debug statements detected
- **Enforcement**: ADVISORY — warns but doesn't block

#### 6.8e typescript-check.sh
- **Trigger**: PostToolUse on `Edit` (only for `.ts`/`.tsx` files)
- [ ] Runs `tsc --noEmit` after editing TypeScript files
- [ ] Reports type errors if found
- [ ] Silent for non-TypeScript files
- **Enforcement**: ADVISORY — reports but doesn't block
- **Gotcha**: Postiz may be TypeScript-based — this hook will be active

#### 6.8f observe.sh
- **Trigger**: PreToolUse and PostToolUse on ALL tools (`matcher: "*"`)
- [ ] Silently captures tool usage patterns to `observations.jsonl`
- [ ] No visible output to user
- [ ] Does not block or slow down work
- **Enforcement**: HOOK (silent observation)
- **Gotcha**: Observer daemon uses `--dangerously-skip-permissions` — verify it doesn't interfere

#### 6.8g dev-server-blocker.sh
- **Trigger**: PreToolUse on `Bash`
- [ ] Blocks `npm run dev`, `yarn dev`, `next dev`, etc. if NOT in tmux
- [ ] Allows dev servers inside tmux
- [ ] Allows non-dev-server commands
- **Enforcement**: HOOK (exit 2 = block)
- **Gotcha**: If testing the postiz app requires a dev server, must use tmux

#### 6.8h long-running-tmux-hint.sh
- **Trigger**: PreToolUse on `Bash`
- [ ] Advises using tmux for long-running commands (npm, pytest, cargo, docker)
- [ ] Silent for quick commands
- **Enforcement**: ADVISORY — hint only

#### 6.8i build-analysis.sh
- **Trigger**: PostToolUse on `Bash`
- [ ] Analyzes build command output for errors/warnings
- [ ] Provides advisory analysis
- **Enforcement**: ADVISORY

#### 6.8j pr-url-extract.sh
- **Trigger**: PostToolUse on `Bash` (specifically after `git push`)
- [ ] Extracts PR creation URL from push output
- [ ] Suggests review commands
- **Enforcement**: ADVISORY

### 6.9 Execution Readiness Check

- **Trigger**: About to start implementing 3+ tasks in current session
- [ ] Claude checks context usage before proceeding
- [ ] At < 70%: proceeds normally
- [ ] At 70-80%: asks user whether to proceed or defer
- [ ] At > 80%: recommends deferring to fresh session
- **Enforcement**: NORMATIVE (new rule from v2.3.1 context-management.md)
- **Gotcha**: This was added specifically because it was violated — Claude auto-executed 8 tasks at ~140k tokens

### 6.10 Set Task Done

- **Trigger**: Task implementation complete, tests passing
- **Command**: `task-master set-status <id> done`
- [x] Status updated — Task 1 and Task 8 both set to `done` after completion
- [x] Claude suggests next task or milestone check-in — `task-master next` used after each completion
- **Enforcement**: NORMATIVE (workflow rule)

---

## Phase 7: Review

### 7.1 Code Review

- **Trigger**: Feature implementation complete on branch
- **Command**: `/code-review`
- [ ] Code review agent spawned (sonnet model, read-only)
- [ ] Findings organized by severity (critical > high > medium > low)
- [ ] Only findings with >80% confidence reported
- [ ] Critical/high findings addressed before PR
- **Enforcement**: NORMATIVE (workflow-enforcement.md: review before PR)

### 7.2 Security Audit (if applicable)

- **Trigger**: Code touches auth, payments, user data, or external APIs
- **Command**: `/security-audit`
- [ ] Security reviewer agent spawned
- [ ] OWASP Top 10 checks performed
- [ ] Findings reported with remediation steps
- **Enforcement**: NORMATIVE (workflow-guide.md: security review for sensitive code)

---

## Phase 8: Branch Completion

### 8.1 Push Branch

- **Trigger**: Review complete, all findings addressed
- **Command**: `git push -u origin <branch>`
- [ ] Branch pushed to remote
- [ ] pr-url-extract.sh suggests PR creation
- **Enforcement**: NORMATIVE

### 8.2 Create Pull Request

- **Trigger**: Branch pushed
- **Command**: `/pr` or `gh pr create`
- [ ] PR created with title and description
- [ ] Description includes summary and test plan
- [ ] PR targets main branch
- **Enforcement**: NORMATIVE (workflow-enforcement.md: merge via PR)

### 8.3 Verify CI

- **Trigger**: PR created, CI configured
- **Commands**: `gh run list --branch <branch> --limit 1` → `gh run watch <run-id>`
- [ ] CI run detected
- [ ] CI passes (or failures diagnosed and fixed)
- **Enforcement**: NORMATIVE (proactive-steering.md: post-push CI verification)
- **Gotcha**: If no CI configured, skip this step

### 8.4 Squash Merge via GitHub

- **Trigger**: CI passes, PR approved
- **Command**: `gh pr merge --squash`
- [ ] PR merged with squash strategy
- [ ] Single commit on main
- **Enforcement**: NORMATIVE (workflow-enforcement.md: squash merge is default for feature/bugfix/hotfix)

### 8.5 Sync Local & Clean Up

- **Trigger**: PR merged on GitHub
- **Commands**:
  ```bash
  git checkout main
  git pull origin main
  git branch -d <branch>      # lowercase -d MUST work after GitHub merge
  ```
- [ ] Main is up to date
- [ ] `git branch -d` (lowercase) succeeds — NO need for `-D`
- [ ] Branch deleted cleanly
- **Enforcement**: NORMATIVE (workflow-enforcement.md: always merge via GitHub for safe cleanup)
- **Gotcha**: **Local `git merge --squash` requires `-D` for cleanup** — this is why we always merge via GitHub PR. v2.3.1 docs clarify this.

### 8.6 Update Task Status

- **Trigger**: Branch merged, code on main
- **Command**: `task-master set-status <id> done` for all completed tasks
- [ ] All tasks for this phase set to `done`
- **Enforcement**: NORMATIVE

### 8.7 Tag Release (if applicable)

- **Trigger**: Feature merged to main
- **Command**: `git tag -a v<version> -m "description"` → `git push origin v<version>`
- [ ] Tag created (feat = minor bump, fix = patch bump)
- [ ] Tag pushed to remote
- **Enforcement**: NORMATIVE (optional for fix-only merges)

---

## Phase 9: Session Lifecycle

### 9.1 Session End — Stop Hooks

- **Trigger**: Session ends (Claude completes response, user ends session)
- [ ] session-end.sh fires — generates session summary to `.claude/sessions/`
- [ ] session-summary.sh fires — snapshot of session state
- [ ] pattern-extraction.sh fires — extracts instinct candidates from git history
- **Enforcement**: HOOK (fires on Stop event)
- **Gotchas**:
  - Stop fires after each Claude response completion, NOT on session exit
  - Does NOT fire on user interrupt (Escape/Ctrl+C mid-generation)
  - Hooks must use `set +e` — `set -e` causes silent failures

### 9.2 Session Resume

- **Trigger**: New session started in same project
- [ ] session-init.sh detects and displays recent session summaries (< 24h)
- [ ] Handoff doc loaded if present (`.claude/sessions/handoff-*.md`)
- [ ] Project phase correctly detected from prior state
- **Enforcement**: NORMATIVE (workflow-enforcement.md: session resume priority order)
- **Priority order**: Handoff doc > MEMORY.md > Session summary > `git log` + `task-master next`

### 9.3 Context Compaction

- **Trigger**: Auto-compaction at configured threshold (default 95%, or 50% with optimized settings)
- [ ] pre-compact.sh saves state before compaction
- [ ] After compaction: rules, CLAUDE.md, git state, Task Master still available
- [ ] After compaction: conversation history, read file contents LOST (must re-read)
- **Enforcement**: HOOK (pre-compact.sh) + AUTOMATIC (Claude Code compaction)

---

## Cross-Cutting Concerns

### C.1 Token Efficiency

- [ ] `task-master list -c` used for orientation (~200 tokens), not `get_tasks` with subtasks (~19.5k tokens)
- [ ] `task-master show <id>` for single task detail, not full list
- [ ] Context7 used only as Tier 3 (after existing knowledge and WebFetch fail)
- [ ] Sub-agents used for isolated research (fresh context)
- **Enforcement**: NORMATIVE (context-management.md)

### C.2 One Task In-Progress Rule

- [ ] Only one task has `in-progress` status at any time
- [ ] Before switching tasks: current task set to done/blocked/pending
- [ ] Then new task set to in-progress
- **Enforcement**: NORMATIVE (workflow-enforcement.md)

### C.3 Commit Frequency

- [ ] Commits after every completed function/feature
- [ ] Commits after every bug fix
- [ ] Commits before switching tasks
- [ ] No commits with broken code
- [ ] All commit messages use conventional format
- **Enforcement**: HOOK (pre-commit-check.sh validates format) + NORMATIVE (frequency)

### C.4 Branch Discipline

- [ ] Never commit directly to main
- [ ] Feature branches named `feature/<description>`
- [ ] Bugfix branches named `bugfix/<description>`
- **Enforcement**: HOOK (pre-commit-check.sh blocks main commits)

### C.5 Continuous Learning Pipeline

The full pipeline: observations → instinct candidates → active instincts → skill evolution.

#### C.5a Observations (observe.sh)
- **Trigger**: Every tool use (PreToolUse + PostToolUse, matcher `*`)
- [ ] `observations.jsonl` file created in `.claude/` or project root
- [ ] Entries accumulate as tools are used throughout the session
- [ ] No visible output to user (silent capture)
- **Enforcement**: HOOK (observe.sh fires on every tool use)

#### C.5b Instinct Candidate Extraction (pattern-extraction.sh)
- **Trigger**: Stop hook fires after Claude responses
- [ ] pattern-extraction.sh runs and analyzes recent git history
- [ ] Instinct candidates written to `.claude/instincts/` as JSON files
- [ ] Each candidate has: pattern, confidence score (0.3-0.7 for new candidates), context
- **Enforcement**: HOOK (Stop event)
- **Gotcha**: Only extracts from git history — sessions with no commits produce no candidates

#### C.5c Instinct Activation
- **Trigger**: Candidate reinforced across multiple sessions (confidence > 0.7)
- [ ] Check `/instinct-status` — shows candidate vs active instincts
- [ ] Active instincts (confidence > 0.7) are loaded and influence behavior
- [ ] Instincts with confidence < 0.3 decay and are removed
- **Enforcement**: NORMATIVE (authority-hierarchy.md: instincts supplement but never override rules)
- **Gotcha**: Single-session dogfood may not produce enough reinforcement for activation — candidates are still a valid outcome

#### C.5d Memory Persistence (MEMORY.md)
- **Trigger**: Claude discovers stable patterns worth remembering across sessions
- [ ] `~/.claude/projects/<project-path>/memory/MEMORY.md` created if useful patterns emerge
- [ ] Memories are semantic (by topic), not chronological
- [ ] No duplicate memories — check existing before writing
- [ ] Memories don't contradict CLAUDE.md instructions
- **Enforcement**: NORMATIVE (auto-memory system prompt instructions)
- **Gotcha**: MEMORY.md is auto-loaded every session — keep it lean. Use separate topic files for detail.

#### C.5e Skill Evolution (optional, multi-session)
- **Trigger**: Instinct clusters detected after multiple sessions
- **Command**: `/evolve`
- [ ] If enough instincts cluster around a theme, `/evolve` suggests promoting to a skill
- [ ] New skill created in `.claude/skills/` with proper SKILL.md format
- **Enforcement**: NORMATIVE (continuous-learning-v2 skill)
- **Gotcha**: Unlikely in a single dogfood session — this validates over weeks. Mark `[-]` skipped if single-session.

### C.6 PRD-First Rule

- [ ] No tasks created via `add-task` from scratch
- [ ] All tasks originate from a parsed PRD
- [ ] PRD stored in `.taskmaster/docs/`
- **Enforcement**: NORMATIVE (CLAUDE.md: "ALWAYS create a PRD before generating tasks")

### C.7 Tag Discipline

- [ ] Each workflow phase gets its own tag
- [ ] `master` tag not polluted with phase-specific work
- [ ] `task-master tags use <name>` before any status operations
- **Enforcement**: NORMATIVE (CLAUDE.md + workflow-enforcement.md)

---

## Failure Log

Track any failures here with details for post-dogfood debugging:

| # | Phase | Check | Expected | Actual | Severity | Fix/Notes |
|---|-------|-------|----------|--------|----------|-----------|
| 1 | 1.1 | Project phase detected | "IDEATION" label in session-init output | Just "Success" — no phase label | Low | Recurring from Run 1. session-init.sh doesn't output workflow phase. Template enhancement needed. |
| 2 | 1.1 | Update banner not shown | No banner when versions match | "TEMPLATE UPDATE AVAILABLE" shown despite `v2.3.1 → v2.3.1` — flags "Missing components: mcp-registry.json sync-template.sh" | Low | Version matches but missing optional files trigger banner. UX misleading but not blocking. |
| 3 | 2.3 | Multiple approaches considered | 2-3 competing architectures presented | Converged on single approach through Q&A; initial attempts asked wrong-level questions (meta-scope vs domain design) | Medium | Template process overhead (checklist, task tracking, rule compliance) consumed cognitive bandwidth that should have gone to domain engagement. α1 produced better brainstorming with less process. Critical dogfood finding: workflow enforcement may degrade creative output during brainstorming phase. |
| 4 | 3.3 | parse-prd uses CLI | CLI with `--force` and long timeout | Used MCP `parse_prd` instead of CLI | Medium | MCP worked this time, but documented guidance says CLI-only for AI ops (MCP `claude-code` provider spawns nested subprocess). Documented in DOGFOOD_CHECKLIST 3.3 gotchas and MEMORY.md. Claude ignored existing guidance in project docs. |
| 5 | 4.1 | analyze-complexity uses CLI | CLI command | Used MCP `analyze_project_complexity` instead of CLI | Medium | Same root cause as #4: Claude defaulted to MCP despite documented CLI-only guidance for AI ops. MCP returned structured data (avoided ANSI rendering bug), but violates the documented workflow. |
| 6 | 5.1 | expand uses CLI | CLI with `--force` and long timeout | First 6 expansions used MCP `expand_task`, last 6 used CLI after user flagged issue | Medium | User caught mid-execution. Corrected to CLI for remaining 6. **Notable: `--prompt` flag was used** to pass complexity report's `expansionPrompt` to each expand call — this produces better subtask decomposition than blind expansion. α1 didn't use prompts → got flat 5-subtask decomposition. |
| 7 | 3.4 | task list uses CLI compact | `task-master list -c` (~200 tokens) | Used MCP `get_tasks` (51KB / ~19.5k+ tokens dumped into context) | Medium | Guidance exists in CLAUDE.md line 73 and DOGFOOD_CHECKLIST 3.4 gotcha. Claude reached for MCP tool by default despite explicit documentation. Corrected immediately — used CLI for all subsequent listings. |
| 8 | 3.2 | Tag created before parse-prd | `postiz-mvp` tag active, tasks in new tag | `tags add` failed — `tasks.json` didn't exist yet | Low | Chicken-and-egg: tags require existing tasks.json. `parse-prd` creates tasks.json. Workaround: parse first (into master), then create tag and move tasks. Or: create empty tasks.json first. Template should document this ordering constraint. |
| 9 | 6.4 | TDD invoked before code | Superpowers TDD skill used before production code | TDD skipped — Tasks 1-8 are infra/config/docs with no testable code | Low | Not a template failure. PRD correctly front-loads config tasks before code. TDD becomes relevant at Task 10+. The checklist should note that TDD is N/A for config/documentation tasks. |
| 10 | 6.1 | Research done before implementation | N/A — not a checklist item | Mid-implementation research revealed critical API issues (Postiz node buggy, rate limits, HTTP Request preferred) that should have been discovered during IDEATION | Medium | The template pipeline is brainstorm → PRD → tasks → implement. Research about specific API capabilities and n8n ecosystem patterns should happen during brainstorming or between brainstorming and PRD. Our PRD assumed the Postiz n8n custom node works — it doesn't for Instagram. Template gap: no explicit "technical research" step between brainstorming and PRD. |
| 11 | 6.2 | Tasks blocked on external deps | All tasks actionable | Tasks 2-7 (platform connections) blocked on temple president providing social media credentials | Low | Real-world external dependency. `task-master set-status blocked` used correctly. The dependency was known from brainstorming but PRD didn't encode it as a formal blocker. Template handles this fine — `blocked` status exists. |

---

## Detailed Findings

### Finding #3 (Critical): Process Overhead Degrades Brainstorming Quality

**Severity**: Medium (functional) but High (strategic — affects all template users)

**Summary**: The template's workflow enforcement machinery (checklist tracking, task management, rule compliance) consumed cognitive bandwidth during brainstorming, producing measurably worse creative output than the same skill without that overhead.

**Evidence — α1 vs α2 vs Run 2 comparison**:

| Dimension | α1 (planning-first, ~v2.2) | α2 (build-first, ~v2.3) | Run 2 (full workflow, v2.3.1) |
|-----------|---------------------------|------------------------|-------------------------------|
| Brainstorming skill used | `superpowers:brainstorming` | None — skipped entirely | `superpowers:brainstorming` |
| Research intake | Used α2's docs as input | Created 3 domain audits (35KB) | Read all existing docs (same as α1) |
| Design doc length | 186 lines | N/A (no design phase) | 202 lines |
| Design doc quality | Rich domain engagement, specific architecture decisions | N/A | Adequate but more generic, less domain depth |
| Restarts needed | 0 | N/A | 2 — first attempt asked meta-scope questions ("do we need Python?"), second still too abstract |
| Checklist overhead | None (no dogfood checklist) | None | 735-line checklist maintained in real-time during brainstorming |
| Process enforcement active | 0 hooks, 0 auto-loaded rules | 3 hooks, partial rules | 18 hooks, 14 rule files, Superpowers skills |
| Time in brainstorming | Focused on domain | Skipped — jumped to coding | Split between domain work and process compliance |
| Planning → execution link | Weak (PRD → tasks existed but generic) | None (0 PRDs, 0 tasks) | Strong (PRD → complexity-guided tasks) |

**The paradox**: α1 had the best brainstorming output despite having the least template infrastructure. Run 2 had the most process enforcement and produced the worst brainstorming experience (2 restarts, meta-level questions, process-distracted output).

However, Run 2 produced the best **downstream artifacts** (PRD with dependency markers, complexity-guided task expansion, 41 targeted subtasks vs α1's flat 110 subtasks). The brainstorming degradation didn't cascade — it was contained to the brainstorming phase itself.

**α2's different creative contribution**: α2 was deliberately a build-focused test — it didn't skip brainstorming due to overhead, it was designed to test execution phases. But α2 did its own form of deep creative work: **3 comprehensive domain research docs (35KB total)** — online presence audit (16KB), Postiz technology assessment (11KB), and client context with branding rules (7KB). This research became the foundation that both α1 and Run 2 consumed during their brainstorming phases. α2 proves that the template supports high-quality creative research output (audits, assessments) — the degradation is specific to the brainstorming skill's interaction with process enforcement, not to creative work in general. The difference: α2's research was exploratory reading and synthesis (compatible with process overhead), while brainstorming is divergent ideation (degraded by process overhead).

**Root cause**: During brainstorming, Claude was simultaneously:
1. Exploring the user's intent and domain (the actual creative work)
2. Maintaining a TaskCreate checklist for brainstorming steps (Superpowers skill requirement)
3. Monitoring compliance with 14 auto-loaded rules in `.claude/rules/`
4. Tracking which dogfood checklist items to mark (dogfood-specific)
5. Managing context budget across all of the above
6. Processing 18 hooks firing on every tool call and prompt submission

The brainstorming skill itself worked fine in α1 (same skill, better output). The degradation came from the surrounding process infrastructure competing for the same context window and attention budget. α2 avoided this entirely by skipping the creative phase — but lost planning traceability.

**What went wrong specifically**:
- **Wrong-level questions**: First attempt asked "should this project include Python?" instead of domain-relevant questions like "how should the approval workflow work?" The process overhead pushed Claude toward meta-planning instead of domain engagement. α1 never exhibited this behavior.
- **2 restarts required**: User had to manually redirect Claude away from process-focused behavior and back to domain-focused brainstorming. α1 needed zero restarts with the same skill.
- **Checklist as cognitive drain**: The brainstorming skill creates a 6-item TaskCreate checklist. Combined with the dogfood checklist tracking, Claude was maintaining two parallel tracking systems while trying to think creatively. α1 had no checklist overhead.
- **Startup token overhead**: Run 2 loads ~40-50k tokens before any work begins (MCP tools, 14 rules, Superpowers skills, CLAUDE.md, hooks). α1 loaded ~10-15k. That's 25-35k fewer tokens available for creative reasoning.

**Implications for the template**:
1. The template's strength (structured workflow enforcement) becomes a weakness during creative/divergent phases — proven by direct α1 comparison
2. Rules are auto-loaded into every session — they consume context even when the current phase doesn't need them
3. The brainstorming skill's own checklist + template rules + dogfood tracking = triple overhead (α2 avoided all three)
4. Users who aren't dogfooding won't have the dogfood checklist, but they'll still have rules + skill checklist competing with creative work
5. α2's research phase (exploratory, convergent) handled process overhead fine; brainstorming (divergent ideation) did not. This suggests the degradation is specific to **divergent creative work**, not all creative work
6. The downstream benefits (PRD → complexity-guided tasks) are significant, but the brainstorming phase itself needs protection from the template's own machinery

**Proposed fixes** (for template team to evaluate):
1. **Phase-aware rule loading**: Only load rules relevant to the current phase. During IDEATION, skip implementation-focused rules (TDD, commit frequency, branch workflow). Currently all 14 rules load every session. α1's lighter context produced better brainstorming.
2. **Post-phase verification instead of real-time**: Verify checklist/compliance items AFTER each phase completes, not DURING creative work. The brainstorming skill should run unencumbered, then a verification pass checks that all steps were followed.
3. **Lighter brainstorming skill**: The 6-item TaskCreate checklist in the brainstorming skill may be counterproductive. Consider making it advisory (mental model) rather than tracked (TaskCreate items). α1 used the same skill without TaskCreate overhead.
4. **Context budget reservation**: During brainstorming, reserve more context for domain reasoning by deferring non-essential tool calls (project-index updates, observation logging, pre-compact state saves).
5. **"Creative mode" toggle**: A phase-specific setting that temporarily reduces process enforcement during brainstorming. Automatically re-enables full enforcement when transitioning to PLANNING or BUILDING.

**Key question for template design**: α1 proves brainstorming quality degrades under process load. α2 proves exploratory research handles the same load fine — so the issue is specific to divergent ideation, not all creative work. Run 2 proves brainstorming degradation doesn't cascade to downstream phases. So: **should the template protect divergent brainstorming from its own enforcement machinery, or accept the quality tradeoff knowing downstream phases compensate?**

**Key question for template design**: Is the quality loss during brainstorming acceptable as the cost of consistent process enforcement? Or should the template treat creative phases differently from execution phases?

### Finding #4-7 (Pattern): Claude Defaults to MCP Despite Documented CLI Guidance

**Severity**: Medium (all operations succeeded, but violated documented workflow)

**Summary**: Across 4 separate operations (get_tasks, parse_prd, analyze_project_complexity, expand_task), Claude used MCP tools instead of CLI commands despite explicit guidance in CLAUDE.md, DOGFOOD_CHECKLIST.md, and MEMORY.md saying to use CLI.

**Evidence**:
- CLAUDE.md line 73: `task-master list -c  # Compact one-line output (fewer tokens)` — Claude used MCP `get_tasks` instead (51KB vs ~200 tokens)
- DOGFOOD_CHECKLIST.md line 263-264: "Must use CLI, not MCP" for AI ops — Claude used MCP for parse-prd, analyze-complexity, and first 6 expand calls
- MEMORY.md: "CLI only for AI operations" — written in prior session, loaded into this session, still ignored

**Root cause analysis**:
1. **MCP tools are in the tool palette**: Claude sees MCP tools as first-class options alongside CLI. The MCP tool definitions are loaded at session start (~6.5k tokens for Task Master tools alone). CLI commands require remembering syntax and using the Bash tool.
2. **Path of least resistance**: MCP tools have structured parameters (fill in fields). CLI requires composing a command string with correct flags. MCP is cognitively easier even when CLI is documented as preferred.
3. **Documentation location matters**: The CLI-only guidance lives in:
   - CLAUDE.md (line 73, one line among many)
   - DOGFOOD_CHECKLIST.md (a test document, not an auto-loaded rule)
   - Cursor rules (`.cursor/rules/taskmaster/`) — NOT in `.claude/rules/` (auto-loaded)
   - MEMORY.md (auto-loaded, but as "memory" not "rule")

   None of these have the authority weight of `.claude/rules/*.md`. The guidance exists but isn't in the highest-authority location.

4. **User had to catch it**: Claude didn't self-correct on any of the 4 violations. The user noticed and flagged it. Even after being corrected on `get_tasks` (failure #7), Claude proceeded to use MCP for expand (failure #6) until caught again.

**Implications for the template**:
1. Documentation alone is insufficient — Claude will default to available tools over documented preferences
2. The MCP vs CLI guidance needs to be in `.claude/rules/` (auto-loaded, highest authority) not just in docs and Cursor rules
3. Consider whether the MCP tools for AI ops should even be exposed if CLI is always preferred
4. MEMORY.md guidance is treated as "advisory" even when explicitly stating "NEVER use MCP"

**Proposed fixes**:
1. **Add `.claude/rules/taskmaster-usage.md`**: Move the CLI vs MCP guidance into an auto-loaded rule file with examples
2. **Reduce MCP tool exposure**: Use `TASK_MASTER_TOOLS` env var to only expose non-AI MCP tools (get_task, set_task_status, next_task). Remove parse_prd, expand_task, analyze_project_complexity from MCP entirely.
3. **Add to CLAUDE.md commands section**: Make the CLI commands more prominent — currently one line, should be a subsection with "ALWAYS use these, NEVER use MCP equivalents"

### Finding #8: Tag Creation Ordering Constraint

**Severity**: Low (workaround exists)

**Summary**: `task-master tags add` requires `tasks.json` to exist. `parse-prd` creates `tasks.json`. You can't create a tag before parsing, so tasks always land in `master` first.

**Current workaround**: Parse into `master`, then create tag afterward. Or create an empty `tasks.json` during init.

**Proposed fix**: `init-project.sh` should create a minimal `tasks.json` skeleton (`{"tags": {"master": {"tasks": [], "metadata": {...}}}}`) so tags can be created at any time. Alternatively, `tags add` should create the file if it doesn't exist.

### Finding #9: TDD Not Applicable to Config/Infrastructure Tasks

**Severity**: Low (expected behavior)

**Summary**: Tasks 1-8 in our PRD are infrastructure verification, platform connection, and configuration tasks. None produce testable code. TDD (the template's core quality gate) doesn't activate until Task 10+.

**Not a failure**: The PRD correctly front-loads config tasks before code tasks (dependency ordering). The Superpowers TDD skill is designed for code implementation, not documentation or manual setup. Marking TDD checks as `[-] SKIPPED` with reason is the correct handling.

**Implication**: For projects where early tasks are infrastructure/config heavy, the dogfood checklist should note that TDD items are expected to be N/A until code tasks begin. The checklist could include a "TDD applicability" check: "Does this task produce testable code? If no, TDD is N/A."

### Finding #10 (Medium): Missing Technical Research Step Between Brainstorming and PRD

**Severity**: Medium (caused incorrect assumptions in PRD, required mid-implementation course correction)

**Summary**: During Phase 6 implementation, we discovered that the Postiz n8n custom node (`n8n-nodes-postiz`) has critical bugs (Instagram 400 errors, Issue #7), the API has a 30 req/hour rate limit, and the dominant n8n pattern uses HTTP Request nodes. These facts should have been discovered during IDEATION (Phase 2) and incorporated into the PRD.

**What happened**:
1. Brainstorming (Phase 2) explored high-level architecture decisions (Google Sheets, approval flow, platforms)
2. PRD (Phase 3) assumed the Postiz n8n custom node works and didn't specify HTTP Request as the integration method
3. During implementation (Phase 6), user asked good questions about API interaction methods
4. Research revealed: custom node is buggy, HTTP Request is preferred, rate limits exist, and 488 existing n8n templates could have informed our design

**What should have happened**:
1. After brainstorming produces a design doc, a **technical research step** validates key assumptions:
   - "Does the Postiz n8n node actually work?" → Check GitHub issues, npm downloads
   - "What are the API rate limits?" → Read Postiz docs
   - "What existing n8n templates cover our use case?" → Search n8n.io/workflows
   - "How do similar projects solve this?" → Research competitor patterns
2. Research findings inform the PRD (rate limits become constraints, HTTP Request becomes the specified method)
3. PRD → tasks reflect reality, not assumptions

**Template pipeline gap**:
```
Current:  brainstorm → PRD → parse-prd → implement
Missing:  brainstorm → TECHNICAL RESEARCH → PRD → parse-prd → implement
```

The brainstorming skill focuses on user intent, architecture, and design decisions. It does NOT validate technical feasibility of specific integration points (API capabilities, library bugs, rate limits, ecosystem patterns). That validation step is currently missing from the template pipeline.

**Proposed fixes**:
1. **Add a "Technical Validation" step** to the superpowers-integration pipeline between brainstorming and PRD: verify key technical assumptions (API docs, library health, rate limits, existing patterns)
2. **PRD template enhancement**: Add a "Technical Constraints" section requiring API rate limits, known library issues, and integration method choices to be documented
3. **Research skill invocation**: After brainstorming, automatically suggest `/research` for technical validation of integration points before PRD writing

**Comparison with α1**: α1's brainstorming also missed this — its PRD assumed the Postiz API works without checking rate limits or node bugs. The difference: α1 didn't reach implementation to discover the issue. The template pipeline has this gap regardless of process overhead.

---

## Summary

| Phase | Total Checks | Pass | Fail | Skip |
|-------|-------------|------|------|------|
| 0: Bootstrap | 19 | 19 | 0 | 0 |
| 1: Session Start | 13 | 8 | 2 | 3 |
| 2: Ideation | 13 | 11 | 1 | 0 |
| 3: Planning | 13 | 8 | 5 | 0 |
| 4: Complexity | 6 | 4 | 1 | 0 |
| 5: Expansion | 7 | 6 | 1 | 0 |
| 6: Implementation | 27 | 12 | 3 | 12 |
| 7: Review | | | | |
| 8: Branch Completion | | | | |
| 9: Session Lifecycle | | | | |
| C: Cross-Cutting | | | | |
| **TOTAL (so far)** | **98** | **68** | **13** | **15** |

**Phase 6 notes**: 12 items skipped because TDD (6.4-6.6) not applicable to infra/config tasks (Tasks 1, 8). 3 failures: #9 (TDD N/A — expected), #10 (missing technical research step — template gap), #11 (tasks blocked on external deps — real-world). Hook tests (6.8a) partially completed — protect-sensitive-files confirmed working.
