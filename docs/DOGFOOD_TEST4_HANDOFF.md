# Dogfood Test 4 — Handoff for Template Fixes

**Date**: 2026-02-23
**Test project**: `~/projects/ISKCON-GN/postiz_social_automation`
**Template version**: v2.3.1 (copy mode — different parent directories)
**Phases completed**: 0.1–1.4 (7 failures logged, 4 in previous session + 3 in this session)
**Full results**: See `docs/DOGFOOD_TEST4_RESULTS.md`

## Failures Requiring Template Fixes

### Failure #1 (Medium): `settings.json` not copied
- **File**: `scripts/init-project.sh`
- **Problem**: Copies 6 subdirectories from `.claude/` (rules/, commands/, skills/, agents/, contexts/, hooks/) but NOT the root-level `.claude/settings.json`. Without it, zero hooks fire on first session.
- **Fix**: Add `cp "$TEMPLATE_DIR/.claude/settings.json" "$PROJECT_DIR/.claude/settings.json"` after the directory copies.
- **Test**: After init, verify `.claude/settings.json` exists in target project.

### Failure #2 (Low): No `var/` directory created
- **File**: `scripts/init-project.sh`
- **Problem**: Doesn't create `var/` directory. Some projects need it for SQLite DBs, logs, etc.
- **Fix**: Consider adding `mkdir -p "$PROJECT_DIR/var"` if the template expects it. Or remove this expectation. Low priority — cosmetic.

### Failure #3 (High): Task Master config overwritten by init
- **File**: `scripts/init-project.sh`
- **Problem**: Template has correct `.taskmaster/config.json` (provider: `claude-code`, models: `opus`/`sonnet`, maxTokens: 200000), but both `task-master init` CLI and MCP `initialize_project` overwrite it with their own defaults (wrong provider, wrong models, wrong maxTokens).
- **Fix**: In `init-project.sh`, AFTER running `task-master init`, overwrite `.taskmaster/config.json` with the template's version (replacing `__PROJECT_NAME__` placeholder with actual project name).
- **Sequence must be**: `task-master init` → then copy template's `config.json` over the generated one.
- **Test**: After init, verify `.taskmaster/config.json` has `provider: "claude-code"` and `model: "opus"`.

### Failure #4 (Low): Success message doesn't list all copied files
- **File**: `scripts/init-project.sh`
- **Problem**: Final success message doesn't mention `.claude/settings.json` or `.taskmaster/config.json`.
- **Fix**: Update the success message to list all files copied/configured. Low priority.

### Failure #5 (High): Local `.mcp.json` overrides global MCP config
- **File**: Not directly an `init-project.sh` issue — this is a Claude Code behavior issue during session restart.
- **Problem**: When Claude Code starts a session, it may prompt the user to "enable Task Master AI as a local MCP", creating a `.mcp.json` in the project root with:
  - Placeholder API keys (`YOUR_ANTHROPIC_API_KEY_HERE`)
  - `core` tier (7 tools instead of `all` 44+)
  - No `@latest` version pin

  This local `.mcp.json` **overrides** the user's working global config in `~/.claude.json` for servers with the same name. Result: AI operations (parse_prd, expand_task, analyze_complexity) fail silently because of placeholder keys.
- **Fix options** (template-level):
  1. Add `.mcp.json` to `.gitignore` in the template's default gitignore
  2. Add a note in CLAUDE.md or onboarding docs: "Do NOT accept local MCP creation if you already have global MCP config"
  3. Consider: should `init-project.sh` check for existing global MCP config and warn?
- **Fix applied in test project**: Deleted `.mcp.json`, added to `.gitignore`.
- **Test**: After init + session restart, verify no `.mcp.json` exists in project root. Verify Task Master AI ops work (test: `parse_prd` with a dummy PRD).

### Failure #6 (Low): No project phase or template version displayed
- **File**: `hooks/session-init.sh`
- **Problem**: On session start, hook outputs just "Success" instead of showing:
  - Current project phase (IDEATION for new project)
  - Template version (v2.3.1)

  Root cause: `.template/version` file doesn't exist. In copy mode, `init-project.sh` doesn't create this file.
- **Fix**: In `init-project.sh`, create `.template/version` with the current template version:
  ```bash
  echo "2.3.1" > "$PROJECT_DIR/.template/version"
  ```
  Then verify `session-init.sh` reads this file for phase/version display.
- **Test**: After init + session start, verify system message shows "v2.3.1" and "IDEATION".

### Failure #7 (Medium): Project index not generated
- **File**: `hooks/project-index.sh`
- **Problem**: Hook detects "PROTO-TEMPLATE" (template-like structure but not officially synced) and shows a sync recommendation instead of generating `.claude/project-index.json`. Missing components: `mcp-registry.json`, `sync-template.sh`.
- **Root cause**: Copy-mode projects don't have `sync-template.sh` or `mcp-registry.json`, so the hook's template detection logic flags them as "proto-templates" and skips indexing.
- **Fix**: `project-index.sh` should generate the project index REGARDLESS of template sync status. The proto-template detection can remain as an advisory message, but it shouldn't skip the core indexing functionality.
- **Alternative**: In `init-project.sh`, create stub/placeholder files for `sync-template.sh` and `mcp-registry.json` so copy-mode projects pass the template detection check.
- **Test**: After init + session start, verify `.claude/project-index.json` exists and contains file tree.

## Fix Priority Order

1. **#3 (config.json)** + **#1 (settings.json)** — both in `init-project.sh`, both block core functionality
2. **#5 (.mcp.json)** — add to default `.gitignore`, add warning to docs
3. **#6 (.template/version)** — add to `init-project.sh`
4. **#7 (project-index.sh)** — fix indexing for copy-mode projects
5. **#2 and #4** — cosmetic, fix while you're in the files

## Re-Test Protocol

After fixes are applied:
1. In `~/projects/ISKCON-GN/postiz_social_automation`:
   - Delete `.claude/` and `.taskmaster/` directories
   - Archive current `docs/DOGFOOD_CHECKLIST.md` → `docs/DOGFOOD_CHECKLIST_run1.md`
   - Keep: `docker-compose.yaml`, `.env`, `dynamicconfig/`, `docs/` (research docs), `CLAUDE.md`
2. Re-run `init-project.sh` from the fixed template
3. Start fresh Claude Code session
4. Walk through fresh dogfood checklist from Phase 0.1
5. **No manual interventions** — if something fails, log it and stop

## PC Crash Note

The user's PC crashed with "system thread exception not handled" during this dogfood session. This is a hardware/OS-level issue (WSL2 on Windows), not template-related. Worth noting in case it recurs — may affect session persistence or file integrity.
