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
- [ ] Directory exists at `~/projects/postiz-social-automation`
- [ ] Git repo initialized with at least one commit (required for hooks)
- **Enforcement**: PREREQUISITE — hooks and Task Master require a git repo
- **Gotcha**: Some hooks call `git log` or `git diff` and fail on repos with zero commits

### 0.2 Run init-project.sh

- **Trigger**: Manual — run from inside the postiz project directory
- **Command**: `~/projects/project-template/scripts/init-project.sh`
- [ ] Auto-detects template at `~/projects/project-template` (parent walk or script-path detection)
- [ ] Mode reported: `symlink` (projects are siblings, so should be copy mode — verify which!)
- [ ] `.claude/` directory created
- [ ] Symlinks OR copies created for: `rules/`, `commands/`, `skills/`, `agents/`, `contexts/`, `hooks/`
- [ ] Each directory has files (not empty)
- [ ] Summary shows `Created: 6` (or appropriate count)
- [ ] No errors or warnings about missing directories
- **Enforcement**: PREREQUISITE — without this, no commands/skills/hooks work
- **Gotchas**:
  - Script uses `python3` for `calc_relative_path` — must be installed
  - If projects are siblings (not nested), auto-detect may fall back to copy mode via `DEFAULT_TEMPLATE_PATH`
  - Previous bug: hardcoded path `~/projects/project-template` — fixed in v2.3.1 (now auto-detects from script location)

### 0.3 Verify settings.json Copied/Created

- **Trigger**: Part of init-project.sh (hooks/ directory includes settings.json reference)
- [ ] `.claude/settings.json` exists in the project
- [ ] Contains all hook definitions (SessionStart, PreToolUse, PostToolUse, UserPromptSubmit, Stop)
- [ ] Hook paths use `$CLAUDE_PROJECT_DIR` prefix (portable across machines)
- **Enforcement**: PREREQUISITE — without settings.json, zero hooks fire
- **Gotcha**: settings.json is in `.claude/hooks/` in the template but Claude Code reads from `.claude/settings.json`. Verify init-project.sh handles this correctly OR document that settings.json must be manually copied/symlinked to `.claude/settings.json`.

### 0.4 Create CLAUDE.md

- **Trigger**: Manual — copy template CLAUDE.md and customize for postiz project
- [ ] `CLAUDE.md` exists at project root
- [ ] Project name, tech stack, and structure sections filled in
- [ ] Taskmaster workflow section preserved (PRD first, new tag per phase, etc.)
- **Enforcement**: NORMATIVE — Claude reads CLAUDE.md every session
- **Gotcha**: CLAUDE.md is project-specific and should NOT be symlinked from template

### 0.5 Initialize Task Master

- **Trigger**: Manual — `task-master init` in the project
- **Command**: `task-master init`
- [ ] `.taskmaster/` directory created with `tasks/`, `reports/`, `docs/` subdirectories
- [ ] `.taskmaster/config.json` created
- [ ] Config has correct `projectName` (not template default)
- [ ] Config has `maxTokens: 200000` (not the `task-master init` default of 32000)
- **Enforcement**: PREREQUISITE — Task Master CLI won't work without init
- **Gotchas**:
  - `task-master init` creates config with its own defaults (32k tokens, wrong project name) — MUST manually edit
  - If `.taskmaster/tasks/` doesn't exist, `task-master tags add` fails silently
  - init-project.sh creates `.taskmaster/{tasks,reports,docs}/` IF `.taskmaster/` already exists — so run `task-master init` FIRST, then re-run init-project.sh, OR manually mkdir

### 0.6 Install Superpowers Plugin

- **Trigger**: Manual — follow CLAUDE.md instructions
- **Commands**:
  ```
  /plugin marketplace add obra/superpowers-marketplace
  /plugin install superpowers@superpowers-marketplace
  ```
- [ ] Superpowers skills appear in skill list (brainstorming, test-driven-development, etc.)
- [ ] `superpowers:brainstorming` is invocable
- [ ] `superpowers:test-driven-development` is invocable
- **Enforcement**: PREREQUISITE — without Superpowers, TDD is advisory-only (not enforced)
- **Gotcha**: Superpowers detection in session-init.sh checks `find` + skills directory — improved in v2.3.1

### 0.7 Verify MCP Servers Connected

- **Trigger**: Start a Claude Code session in the project
- [ ] Task Master MCP responds (test: `task-master list`)
- [ ] Context7 MCP responds (test: resolve a library ID)
- **Enforcement**: PREREQUISITE — Task Master MCP needed for data ops
- **Gotcha**: MCP servers are user-level config (`~/.claude/settings.json`), not project-level

---

## Phase 1: Session Start

### 1.1 session-init.sh Fires

- **Trigger**: `SessionStart` hook — fires when Claude Code session begins
- [ ] Hook runs without errors (check for `SessionStart:startup hook success` in system message)
- [ ] Project phase detected and displayed (IDEATION for new project)
- [ ] Template version shown: `v2.3.1`
- [ ] No stale session summaries loaded (fresh project)
- [ ] Update banner NOT shown (installed version should match current)
- **Enforcement**: HOOK — fires automatically
- **Gotchas**:
  - If `.template/version` file doesn't exist, version comparison may error
  - Hook assumes `jq` is installed for some operations

### 1.2 project-index.sh Fires

- **Trigger**: `SessionStart` hook — runs after session-init.sh
- [ ] `Project index updated` message appears in system reminders
- [ ] `.claude/project-index.json` created/updated
- [ ] Index contains file tree of the project
- **Enforcement**: HOOK — fires automatically
- **Gotcha**: On empty projects, index will be minimal (just CLAUDE.md, .claude/, .taskmaster/)

### 1.3 pre-compact.sh Fires

- **Trigger**: `UserPromptSubmit` hook — fires on EVERY user message
- [ ] `Pre-compaction state saved` message appears
- [ ] `.claude/sessions/pre-compact-state.md` created
- **Enforcement**: HOOK — fires every prompt
- **Gotcha**: This fires on every single user message, not just before compaction — it's preemptive

### 1.4 suggest-compact.sh Fires

- **Trigger**: `UserPromptSubmit` hook — fires on every user message
- [ ] Silent on early messages (no output until 50+ tool calls)
- [ ] At 50 tool calls: advisory suggestion appears
- [ ] At 75 tool calls: stronger suggestion
- [ ] At 100 tool calls: urgent suggestion
- **Enforcement**: ADVISORY — suggestions only, no blocking
- **Gotcha**: Counter resets on session restart. Token-based, not message-based.

---

## Phase 2: Ideation (Brainstorming)

### 2.1 Skill Detection

- **Trigger**: User describes a feature to build (e.g., "I want to build a social media automation tool")
- [ ] Claude detects that brainstorming skill applies
- [ ] `superpowers:brainstorming` skill is invoked BEFORE any code or planning
- **Enforcement**: NORMATIVE (Superpowers) — skill should be invoked for any creative/feature work
- **Gotcha**: If Superpowers not installed, brainstorming is advisory only

### 2.2 Research & Context Intake

- **Trigger**: Brainstorming skill's first step: "Explore project context — check files, docs, recent commits"
- [ ] Claude reads ALL existing research docs in `docs/` (non-dogfood files)
  - `gita-valley-context.md` — Client profile, social accounts, content strategy
  - `gita-valley-online-presence-audit-v2.md` — Platform audit, rebranding gaps
  - `social-media-automation-assessment.md` — Postiz vs SaaS comparison
  - `N8N_INTEGRATION.md` — n8n ↔ Postiz connection setup
- [ ] Claude reads/analyzes existing infrastructure (Docker Compose, service config) if present
- [ ] Research findings are explicitly referenced when proposing approaches (not generic suggestions)
- [ ] Technology constraints from research are acknowledged (Postiz API beta limits, n8n capabilities, platform app approvals)
- **Enforcement**: NORMATIVE (Superpowers brainstorming skill step 1 + startup prompt)
- **Context**: In α2, comprehensive domain audits (online presence audit, tech assessment) were created as part of the workflow and informed all subsequent design. These docs already exist in the project — the brainstorming must incorporate them, not ignore them.
- **Gotcha**: The brainstorming skill says "check files, docs, recent commits" but doesn't enforce it. If Claude skips this step, the design doc and PRD will be generic rather than domain-informed.

### 2.3 Brainstorming Process

- **Trigger**: `superpowers:brainstorming` skill loaded, research intake complete
- [ ] Claude explores user intent before jumping to solutions
- [ ] Multiple approaches considered (at least 2-3)
- [ ] Approaches reference specific findings from research docs (e.g., API rate limits, platform rebrand status, content pillar weights)
- [ ] Trade-offs discussed with domain-specific context (not abstract pros/cons)
- [ ] User confirms direction before proceeding
- **Enforcement**: NORMATIVE (Superpowers skill instructions)

### 2.4 Design Doc Quality Check

- **Trigger**: Brainstorming produces design doc
- [ ] Design doc references specific data from research docs (follower counts, API limits, platform statuses)
- [ ] Architecture decisions are grounded in the technology assessment (not reinvented from scratch)
- [ ] Content strategy alignment: design doc reflects the 40/25/15/10/5/5 pillar weights and 70/20/10 mix
- [ ] Infrastructure constraints captured: Docker stack, Postiz API beta limits, separate hosts for n8n/Postiz
- **Enforcement**: NORMATIVE (quality verification)
- **Context**: α1's design doc was 185 lines with detailed architecture, data flow, and phased rollout — all informed by the research docs. This is the quality bar.

### 2.5 Brainstorming Exit — CRITICAL OVERRIDE

- **Trigger**: Brainstorming skill completes
- [ ] Design doc saved to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- [ ] **Does NOT route to `writing-plans`** — this is the rule override from `superpowers-integration.md`
- [ ] Instead routes to PRD creation (Phase 3)
- **Enforcement**: NORMATIVE (rule override in `.claude/rules/superpowers-integration.md`)
- **Gotcha**: **This was broken TWICE in prior sessions.** The Superpowers brainstorming skill explicitly says to invoke `writing-plans` as terminal state. Our rule overrides this. Verify Claude follows the rule, not the skill's default exit.

---

## Phase 3: Planning (PRD & Task Generation)

### 3.1 PRD Creation

- **Trigger**: After brainstorming completes (or if requirements are already clear)
- [ ] PRD written to `.taskmaster/docs/prd_<slug>.txt`
- [ ] PRD contains: overview, architecture, technology stack, requirements, success criteria
- [ ] PRD contains a **Dependency Graph** section with layered dependencies
  - [ ] Foundation layer modules have NO dependencies
  - [ ] Each non-foundation module has explicit `Depends on [X, Y]` markers
  - [ ] Dependencies form a DAG (no circular references)
  - [ ] Modules within the same layer that don't depend on each other are identifiable as parallelizable
- [ ] PRD is NOT in random location (should be in `.taskmaster/docs/`)
- **Enforcement**: NORMATIVE (CLAUDE.md: "ALWAYS create a PRD before generating tasks")
- **Context**: The dependency graph is the most valuable section for `task-master parse-prd`. Without it, the parser must infer dependencies from prose — often incorrectly. `/prd-generate` now includes Phase 3.5 (Dependency Analysis) that produces this structure automatically.
- **Gotcha**: doc-file-blocker.sh may block `.md` files outside `docs/` — PRD uses `.txt` extension intentionally
- **Gotcha**: α1's PRD lacked explicit dependency chains. Combined with skipping `analyze-complexity` (which caused the default 5 subtasks per task), this produced poorly-ordered, flat task decomposition.

### 3.2 Create Tag for This Phase

- **Trigger**: Before parsing PRD into tasks
- **Command**: `task-master tags add <tag-name>` then `task-master tags use <tag-name>`
- [ ] New tag created (e.g., `postiz-mvp` or `feature-automation`)
- [ ] Tag is active (verified with `task-master tags list`)
- [ ] Tasks are NOT being added to `master` tag
- **Enforcement**: NORMATIVE (CLAUDE.md: "Each workflow phase gets its own tag")
- **Gotcha**: Tag ID spaces are independent — each tag starts at ID 1

### 3.3 Parse PRD into Tasks

- **Trigger**: PRD exists, tag is active
- **Command**: `task-master parse-prd --input=.taskmaster/docs/prd_<slug>.txt --num-tasks=0 --force`
- [ ] Command executes WITHOUT hanging (no interactive prompt)
- [ ] Output visible in terminal (not swallowed by ANSI codes)
- [ ] Tasks created in the active tag
- [ ] Task count is AI-determined (not hardcoded)
- [ ] `task-master list` shows the new tasks
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
- [ ] Tasks listed with IDs, titles, and statuses
- [ ] All tasks are `pending` status
- [ ] Task titles are meaningful (not generic)
- [ ] Dependencies are reasonable (if set)
- **Enforcement**: NORMATIVE (verification step)
- **Gotcha**: Use `task-master list -c` for token efficiency — NEVER `get_tasks` with `withSubtasks: true` for orientation (dumps ~19.5k tokens)

---

## Phase 4: Complexity Analysis

### 4.1 Analyze Complexity

- **Trigger**: After tasks are parsed from PRD
- **Command**: `task-master analyze-complexity`
- [ ] Command runs without error
- [ ] Output may be empty/garbled (known rendering bug)
- **Enforcement**: NORMATIVE (workflow rule: always analyze before expanding)
- **Gotcha**: **`analyze-complexity` has stdout rendering bug** — ANSI progress codes swallow output. This is expected. Always follow with `complexity-report`.

### 4.2 View Complexity Report

- **Trigger**: After analyze-complexity completes
- **Command**: `task-master complexity-report`
- [ ] Report displays with per-task complexity scores (1-10)
- [ ] Each task has an expansion recommendation (number of subtasks)
- [ ] Tasks scored >= 5 flagged for expansion
- [ ] Report is readable (not garbled by ANSI)
- **Enforcement**: NORMATIVE (this is the workaround for 4.1's rendering bug)
- **Gotcha**: Pipeline must be: `parse-prd → analyze-complexity → complexity-report → expand`

---

## Phase 5: Task Expansion

### 5.1 Expand Complex Tasks

- **Trigger**: Complexity report shows tasks with score >= 5
- **Command**: `task-master expand --id=<id> --force` (per complex task)
- [ ] Expansion runs for each task scoring >= 5
- [ ] Subtasks created with meaningful titles
- [ ] Simple tasks (score < 5) NOT expanded (unless user requests)
- [ ] Output visible in terminal
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
- [ ] Full task tree visible with parent tasks and subtasks
- [ ] Subtask IDs use dot notation (e.g., `1.1`, `1.2`)
- [ ] Dependencies between subtasks are reasonable
- **Enforcement**: NORMATIVE (verification step)
- **Gotcha**: Only use `--with-subtasks` once at this point and once on session resume — it's heavier than compact list

---

## Phase 6: Implementation (TDD per Task)

### 6.1 Pick Next Task

- **Trigger**: Ready to implement
- **Command**: `task-master next` or `task-master list --ready --blocking`
- [ ] Returns a task/subtask with all dependencies satisfied
- [ ] Task is the highest-impact starting point
- **Enforcement**: NORMATIVE (workflow rule)

### 6.2 Set Task In-Progress

- **Trigger**: Starting work on a task
- **Command**: `task-master set-status <id> in-progress`
- [ ] Status updated successfully
- [ ] Only ONE task is in-progress at a time
- **Enforcement**: NORMATIVE (one task in-progress rule from workflow-enforcement.md)

### 6.3 Create Feature Branch

- **Trigger**: Starting implementation work
- **Command**: `git checkout -b feature/<descriptive-name>`
- [ ] Branch created from main
- [ ] Branch name follows convention: `feature/`, `bugfix/`, `hotfix/`
- [ ] NOT working directly on main
- **Enforcement**: HOOK (pre-commit-check.sh blocks commits to main)

### 6.4 Superpowers TDD — RED Phase

- **Trigger**: `superpowers:test-driven-development` skill invoked
- [ ] Skill is invoked BEFORE writing any production code
- [ ] Failing test written FIRST
- [ ] Test describes the expected behavior
- [ ] Test actually FAILS when run (not a false pass)
- **Enforcement**: NORMATIVE (Superpowers TDD) — if installed, Superpowers may delete code written without tests
- **Gotcha**: Superpowers TDD is strict — it deletes production code written without failing tests first

### 6.5 Superpowers TDD — GREEN Phase

- **Trigger**: Failing test exists
- [ ] Minimal production code written to make test pass
- [ ] Test now PASSES
- [ ] No other tests broken
- **Enforcement**: NORMATIVE (Superpowers TDD)

### 6.6 Superpowers TDD — REFACTOR Phase

- **Trigger**: Test passes
- [ ] Code cleaned up (if needed)
- [ ] All tests still pass after refactor
- [ ] No behavior changes
- **Enforcement**: NORMATIVE (Superpowers TDD)

### 6.7 Commit After TDD Cycle

- **Trigger**: TDD cycle complete (RED-GREEN-REFACTOR)
- [ ] `git add <specific-files>` (not `git add .`)
- [ ] Commit message uses conventional format: `feat:`, `fix:`, `test:`, etc.
- [ ] pre-commit-check.sh validates commit message format
- [ ] pre-commit-check.sh blocks if committing to main branch
- [ ] Commit succeeds
- **Enforcement**: HOOK (pre-commit-check.sh)
- **Gotcha**: Hook checks conventional commit format — "Fixed bug" will be rejected, must be "fix: ..."

### 6.8 Hook Triggers During Implementation

These hooks fire during normal coding work:

#### 6.8a protect-sensitive-files.sh
- **Trigger**: PreToolUse on `Edit` or `Write`
- [ ] Blocks edits to `.env`, `credentials.json`, `secrets.json`, `*.pem`, `*.key`
- [ ] Blocks edits to files in `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, `venv/`
- [ ] Allows `.env.sample`, `.env.example`
- [ ] Allows normal source files
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
- [ ] Status updated
- [ ] Claude suggests next task or milestone check-in
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
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

---

## Summary

| Phase | Total Checks | Pass | Fail | Skip |
|-------|-------------|------|------|------|
| 0: Bootstrap | | | | |
| 1: Session Start | | | | |
| 2: Ideation | | | | |
| 3: Planning | | | | |
| 4: Complexity | | | | |
| 5: Expansion | | | | |
| 6: Implementation | | | | |
| 7: Review | | | | |
| 8: Branch Completion | | | | |
| 9: Session Lifecycle | | | | |
| C: Cross-Cutting | | | | |
| **TOTAL** | | | | |
