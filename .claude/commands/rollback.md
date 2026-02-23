Guided rollback to a known-good state using git reflog and session summaries.

Usage:
- `/rollback` - Show recent states with session context, then choose
- `/rollback <commit-or-ref>` - Revert to a specific commit
- `/rollback --list` - List recovery points without reverting

Arguments: $ARGUMENTS

## Workflow

### Step 1: Gather Recovery Context

Run these in parallel to build a timeline:

```bash
# Recent git history (last 20 entries)
git reflog --format='%h %gd %gs (%cr)' -20

# Recent commits with conventional commit messages
git log --oneline --decorate -15

# Current branch and status
git status --short
```

Also check for session summaries:
```bash
ls -lt .claude/sessions/session-summary-*.md 2>/dev/null | head -5
```

### Step 2: Build Recovery Timeline

Present a **numbered timeline** combining git reflog entries with session summaries:

```markdown
## Recovery Points

| # | Commit  | Age     | Description                        | Session |
|---|---------|---------|------------------------------------|---------|
| 1 | abc1234 | 5m ago  | feat: Add user auth endpoint       | -       |
| 2 | def5678 | 15m ago | fix: Resolve null pointer in parser | -       |
| 3 | ghi9012 | 1h ago  | test: Add auth unit tests          | session-summary-20260222-1830.md |
| 4 | jkl3456 | 2h ago  | feat: Implement JWT tokens         | session-summary-20260222-1630.md |
```

For entries with matching session summaries, read the summary and note:
- What was accomplished in that session
- What state the project was in
- Any warnings or known issues

### Step 3: If specific target provided

If the user provided a commit hash or ref:
1. Show what will be lost: `git log --oneline <target>..HEAD`
2. Show file changes: `git diff --stat <target> HEAD`
3. **Ask for confirmation** before proceeding

### Step 4: Execute Rollback

**IMPORTANT: Never force-push or destroy history without explicit confirmation.**

Choose the safest method based on context:

#### Option A: Soft Reset (preserves changes as unstaged)
```bash
# Safest — moves HEAD but keeps all file changes
git reset --soft <target>
```
**Use when:** User wants to redo commits, not lose code.

#### Option B: Mixed Reset (default — unstages but keeps files)
```bash
# Moves HEAD and unstages, but files unchanged on disk
git reset <target>
```
**Use when:** User wants to start over from that point, keeping files for reference.

#### Option C: Revert (creates undo commit — safest for shared branches)
```bash
# Creates a new commit that undoes changes
git revert --no-commit <target>..HEAD
git commit -m "revert: Roll back to <target> (<description>)"
```
**Use when:** Changes were already pushed or branch is shared.

#### Option D: Hard Reset (destructive — loses all changes)
```bash
# DESTRUCTIVE: Discards all changes since target
git reset --hard <target>
```
**Use when:** User explicitly wants to discard everything. **Always confirm first.**

### Step 5: Verify

After rollback:
```bash
git status
git log --oneline -5
pytest --tb=short -q 2>/dev/null || echo "No tests to run"
```

Report the new state and suggest next steps.

## Safety Rules

1. **Default to Option A** (soft reset) unless user specifies otherwise
2. **Never hard reset without explicit confirmation** — show what will be lost first
3. **If changes were pushed**, use Option C (revert) not reset
4. **Create a backup branch** before destructive operations:
   ```bash
   git branch backup-before-rollback
   ```
5. **Check for uncommitted changes** first — stash them before any reset

## Integration with Session Summaries

Session summaries in `.claude/sessions/` contain:
- Timestamp and duration
- Files modified
- Commits made
- Key decisions and reasoning

When a session summary exists for a recovery point, display its "Actions" and "Decisions" sections to help the user understand what that state represents.

## When NOT to Use

- Simple undo of last commit → `git reset --soft HEAD~1` (no command needed)
- Merge conflict resolution → use `git-recovery` skill instead
- Lost stashed changes → use `git-recovery` skill instead
- This command is for **intentional rollback to a known state**, not emergency recovery
