<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/workflow-enforcement.md -->
# Workflow Enforcement

This rule is **normative** — it defines the correct workflow for every common scenario. Hooks (pre-commit-check.sh, pre-compact.sh) provide **enforcement** for the most critical rules, but not every normative rule has hard enforcement. Some rely on Claude's discipline.

This complements but does not duplicate:
- **workflow-guide.md** — phase detection, tool selection, background behaviors
- **superpowers-integration.md** — Superpowers plugin routing, pipeline definition
- **proactive-steering.md** — steering patterns, auto-invoke table

This rule provides **explicit decision thresholds** so there is no ambiguity about which workflow applies.

## Workflows by Task Type

### Feature Implementation

**MANDATORY for multi-task work.** Single-task features may use a simplified flow.

```
brainstorm → PRD → parse-prd → analyze-complexity → expand → TDD per task
```

| Step | Command | Required? |
|------|---------|-----------|
| Brainstorm | `superpowers:brainstorming` | Yes, for non-trivial features |
| PRD | Write to `.taskmaster/docs/prd_<slug>.txt` | Yes |
| Parse | `task-master parse-prd --input=<file> --num-tasks=0` | Yes |
| Analyze | `task-master analyze-complexity` | Yes |
| Expand | `task-master expand --id=<id>` (guided by report) | For tasks scoring >= 5 |
| Implement | `superpowers:test-driven-development` per task | Yes |

See `superpowers-integration.md` for full pipeline details and the brainstorming exit override.

**Single well-defined task:** Skip brainstorm/PRD. Use TDD directly, optionally with `writing-plans` for micro-planning steps.

### Bug Fixes

Choose workflow based on size and clarity:

| Size | Threshold | Workflow |
|------|-----------|----------|
| Trivial | < 10 lines, obvious cause | Direct TDD. No task needed. |
| Scoped | 10–50 lines, clear cause | Create task, then TDD. |
| Complex | > 50 lines or unclear root cause | `superpowers:systematic-debugging` first, then create task + TDD. |

**All bug fixes require at least one test** proving the fix. The test should fail before the fix and pass after.

### Refactoring

Choose workflow based on scope:

| Size | Threshold | Workflow |
|------|-----------|----------|
| Small | < 50 lines | Direct with tests. Verify existing tests still pass. |
| Medium | 50–200 lines | Create task + TDD. Run full test suite. |
| Large | 200+ lines | Full workflow: PRD, parse-prd, expand, TDD per subtask. |

**Refactoring must not change behavior.** All existing tests must continue to pass. If existing test coverage is insufficient, add tests *before* refactoring.

### Documentation

Documentation changes do **not** require TDD (prose is not testable).

| Change | Workflow |
|--------|----------|
| Small (README fix, comment update) | Direct edit. Commit with `docs:` prefix. No task needed. |
| Medium (new section, API docs) | Direct edit. Commit with `docs:` prefix. Task optional. |
| Major (documentation system, full rewrite) | Create task. Commit with `docs:` prefix. |

### Dependency Updates

| Change | Workflow |
|--------|----------|
| Patch/minor bump | Update, run full test suite, commit as `chore:`. No task needed. |
| Major version bump | Create task. Review changelog for breaking changes. Update, run full test suite, commit as `chore:`. |

**Always run the full test suite after any dependency update** to catch breaking changes.

### Emergency Hotfixes

For production-critical issues requiring immediate resolution:

1. Create `hotfix/` branch (e.g., `hotfix/fix-auth-crash`)
2. **TDD still applies** but minimal: write a single assertion test proving the fix
3. Skip PRD/task overhead — speed matters
4. Fix the issue, verify test passes
5. Commit with `fix:` prefix
6. Document in CHANGELOG with date and issue reference
7. Merge via expedited PR (or direct if truly critical)

Hotfixes are the **only** scenario where the full planning pipeline is skipped, but TDD is never skipped entirely.

### Branch Completion (Post-Implementation)

After all tasks on a branch are done, follow this sequence:

1. **Review**: Run `/code-review` on changed files. Address critical/high findings.
2. **Push**: `git push -u origin <branch>`
3. **Create PR**: `/pr` — squash merge is the default (one feature = one commit on main).
4. **Verify CI**: `gh run list --branch <branch> --limit 1` → `gh run watch <run-id>`. Fix failures before merging.
5. **Merge**: Squash merge via GitHub (or `gh pr merge --squash`).
6. **Sync local**: `git checkout main && git pull origin main`
7. **Clean up branch**: `git branch -d <branch>` (local). GitHub auto-deletes remote if configured.
8. **Update tasks**: `task-master set-status <id> done` for all completed tasks.
9. **Tag if release-worthy**: `git tag -a v<version> -m "description"` → `git push origin v<version>`

**Why this sequence matters (squash merge + branch safety):**

Squash merges rewrite commits into a single new commit, which breaks git's ability to verify branch ancestry. The order above ensures `git branch -d` (lowercase, safe) always works:

| Approach | `branch -d` works? | Why |
|----------|-------------------|-----|
| Squash via GitHub PR → pull → delete | Yes | GitHub tracks provenance; pulled commit matches |
| Local `git merge --squash` → delete | No — requires `-D` | New commit has no parent link to branch |
| Local `git merge --no-ff` → delete | Yes | Merge commit preserves ancestry |

**Always merge via GitHub PR** (steps 2-5 above). This is the default. Local `merge --squash` + `branch -D` is a shortcut that bypasses git's safety check — avoid it unless working solo with no remote.

**Merge strategy by branch type:**

| Branch Type | Strategy | Rationale |
|-------------|----------|-----------|
| Feature (`feature/`) | Squash merge | Clean main history — one feature = one commit |
| Bugfix (`bugfix/`) | Squash merge | Single fix = single commit |
| Hotfix (`hotfix/`) | Squash merge | Urgent fix, minimal history |
| Release (`release/`) | Merge commit | Preserve release branch history |

**When to tag a release:**

| Change | Tag? | Version Bump |
|--------|------|-------------|
| New `feat:` merged | Yes, minor (`v2.3.0`) | New functionality added |
| Only `fix:`/`docs:`/`chore:` | Optional, patch (`v2.3.1`) | Maintenance only |
| Breaking change | Yes, major (`v3.0.0`) | API or behavior change |
| Multiple features accumulated | Yes, minor | Batch release at natural milestone |

**Do not present merge strategy as a choice.** Use the default from the table above. Only deviate if the user explicitly requests a different strategy.

## Session Management

### Multi-Feature Sessions

**One task in-progress at a time.** This prevents context fragmentation and ensures focused work.

- Before switching tasks: `task-master set-status <current-id> <status>` (done, blocked, or pending)
- Then claim the new task: `task-master set-status <new-id> in-progress`
- If the user requests a different task mid-work, use the Redirect pattern from `proactive-steering.md`

### Session Resume Priority

When resuming work in a new session, check sources in this order:

| Priority | Source | What It Provides |
|----------|--------|-----------------|
| 1 | Handoff doc (`.claude/sessions/handoff-*.md`) | Explicit continuation state from previous session |
| 2 | MEMORY.md | Stable patterns, project conventions, learned context |
| 3 | Session summary (`.claude/sessions/session-summary-*.md`) | Recent activity log |
| 4 | `git log` + `task-master next` | Ground truth: what changed, what's next |

If a handoff doc exists and is recent (< 24h), it takes absolute priority — it was written specifically for this continuation.

## Tag Management

- **One tag per workflow phase** (e.g., `feature-auth`, `bugfix-api`). Never pollute the `master` tag with phase-specific work.
- **Switch tags before status operations**: `task-master tags use <name>` before `set-status`, `show`, or `list`.
- **Document tag purpose** when creating: include the feature/phase name so future sessions understand the context.
- **Clean up completed tags**: After all tasks in a tag are done and merged, the tag can be archived or ignored.

## Enforcement Note

| Term | Meaning |
|------|---------|
| **Normative** | Defines correct behavior. This document. |
| **Enforcement** | Prevents violations. Hooks (`pre-commit-check.sh`, `pre-compact.sh`). |

Not all normative rules have hard enforcement. Some rely on Claude following the rules faithfully. When a violation is noticed (by Claude or the user), it should be corrected — even if no hook caught it.

**Enforced by hooks:**
- Conventional commit format (pre-commit-check.sh)
- Main branch protection (pre-commit-check.sh)
- Pre-compaction state preservation (pre-compact.sh)

**Normative only (no hook enforcement):**
- Feature workflow pipeline (brainstorm → PRD → tasks → TDD)
- Branch completion sequence (review → PR → merge → cleanup)
- Bug fix size thresholds
- Refactoring scope thresholds
- One task in-progress at a time
- Tag management discipline
- Session resume priority order
