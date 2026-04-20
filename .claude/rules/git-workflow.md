<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/git-workflow.md -->
# Git Workflow Rules & Commands Reference

## Daily Workflow Rules

### Rule 1: Always Start Fresh
```bash
git checkout main
git pull origin main
git checkout -b feature/descriptive-name
```
**When:** Beginning of every work session

### Rule 2: Commit Frequently
```bash
git add filename.py              # Specific files
git add .                        # All files
git commit -m "Descriptive message about what you did"
```

**When to Commit:**
- Feature/function completed and working
- Bug fixed and tested
- Before breaks (lunch, end of day)
- Before risky experiments
- Before switching tasks

**When NOT to Commit:**
- Code doesn't run/compile
- Broken functionality
- Incomplete features

### Rule 3: Push for Backup
```bash
git push -u origin feature/branch-name    # First time
git push origin feature/branch-name       # Subsequent pushes
```

## Branch Naming Conventions

```bash
feature/add-user-auth       # New features
bugfix/fix-login-error      # Bug fixes
hotfix/critical-security    # Urgent fixes
docs/update-readme          # Documentation
refactor/cleanup-database   # Code improvements
```

## Commit Message Rules

### Conventional Commits Format

All commits MUST follow the conventional commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types (Required)

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: Add user login endpoint` |
| `fix` | Bug fix | `fix: Resolve null pointer in parser` |
| `docs` | Documentation | `docs: Update API reference` |
| `style` | Formatting (no code change) | `style: Fix indentation` |
| `refactor` | Code restructure | `refactor: Extract helper function` |
| `test` | Adding tests | `test: Add auth unit tests` |
| `chore` | Maintenance | `chore: Update dependencies` |
| `perf` | Performance | `perf: Optimize database query` |
| `ci` | CI/CD changes | `ci: Add GitHub Actions workflow` |

### Scope (Optional)

Indicates the area affected:
```bash
feat(auth): Add password reset flow
fix(api): Handle timeout errors
docs(readme): Add installation steps
```

### Good Messages:
```bash
git commit -m "feat: Add user authentication with JWT tokens"
git commit -m "fix: Resolve memory leak in image processing"
git commit -m "docs: Update README with installation instructions"
git commit -m "refactor: Optimize database queries for performance"
git commit -m "test(auth): Add integration tests for login flow"
```

### Bad Messages:
```bash
git commit -m "fix"           # Too vague
git commit -m "updates"       # Meaningless
git commit -m "stuff"         # Useless
git commit -m "WIP"           # Not descriptive
git commit -m "Fixed bug"     # Missing type prefix
```

### Why Conventional Commits?

1. **Automated changelogs** - `/changelog` command categorizes by type
2. **Clear history** - Easy to understand what changed
3. **Semantic versioning** - `feat` = minor, `fix` = patch
4. **Searchable** - `git log --grep="feat:"` finds all features

## Recovery Commands

### Uncommitted Changes
```bash
git status                    # See what changed
git checkout -- filename.py   # Restore single file
git reset --hard HEAD         # Restore all (NUCLEAR)
```

### Committed But Not Pushed
```bash
git reset --soft HEAD~1       # Undo commit, keep changes staged
git reset HEAD~1              # Undo commit, unstage changes
git reset --hard HEAD~1       # Undo commit, delete changes (NUCLEAR)
```

### Already Pushed (Safe)
```bash
git revert HEAD               # Create undo commit
git push origin main
```

### Emergency Recovery
```bash
git reflog                    # See all your actions
git checkout abc1234          # Go back to specific state
git stash                     # Temporarily save work
git stash pop                 # Restore saved work
```

## Team Collaboration Rules

1. **Never commit to main directly** - Always use feature branches
2. **Always pull before push** - `git pull origin main` first
3. **Use meaningful branch names** - Not `test`, `mywork`, `temp`
4. **Merge via Pull Requests** - For code review and history

## Quick Reference

| Command | When to Use | Effect |
|---------|-------------|--------|
| `git add .` | Before committing | Stages all changes |
| `git commit -m "msg"` | Save working code | Creates checkpoint |
| `git push origin branch` | Backup/share work | Uploads to GitHub |
| `git pull origin main` | Start of day | Gets latest changes |
| `git checkout -b feature/name` | New work | Creates new branch |
| `git status` | Check state | Shows what changed |
| `git log --oneline` | See history | Shows commits |
| `git revert HEAD` | Undo safely | Creates undo commit |

## Danger Commands (Use with Caution)

```bash
git reset --hard HEAD       # Deletes all uncommitted work
git reset --hard HEAD~5     # Deletes last 5 commits locally
git push --force            # Overwrites history (AVOID)
git branch -D branch-name   # Force delete branch
```
