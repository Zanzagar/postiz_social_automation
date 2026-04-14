---
name: git-recovery
description: Git emergency recovery and troubleshooting. Use when user has git problems, lost commits, merge conflicts, or needs to undo changes.
---

# Git Recovery Skill

## When to Use
- User says they "messed up" git or made a mistake
- Lost commits or changes
- Merge conflicts
- Need to undo commits or changes
- Detached HEAD state
- Branch problems

## Diagnosis First

Before suggesting recovery commands, understand the situation:
1. Run `git status` to see current state
2. Run `git log --oneline -10` to see recent history
3. Ask clarifying questions if unclear

## Recovery Scenarios

### Lost Uncommitted Changes
```bash
# If changes were staged
git fsck --lost-found
# Look in .git/lost-found/

# If you ran git stash
git stash list
git stash pop
```

### Undo Last Commit (Not Pushed)
```bash
# Keep changes staged
git reset --soft HEAD~1

# Keep changes unstaged
git reset HEAD~1

# Discard changes completely (DESTRUCTIVE)
git reset --hard HEAD~1
```

### Undo Pushed Commit (Safe)
```bash
# Create a new commit that undoes the previous one
git revert HEAD
git push
```

### Recover Deleted Branch
```bash
# Find the commit
git reflog

# Recreate branch at that commit
git checkout -b branch-name abc1234
```

### Fix Detached HEAD
```bash
# Create a branch to save your work
git checkout -b temp-branch

# Or return to a branch
git checkout main
```

### Merge Conflict Resolution
```bash
# See conflicted files
git status

# After manually fixing conflicts
git add <fixed-files>
git commit
```

### Nuclear Options (Last Resort)
```bash
# See ALL recent git actions
git reflog

# Go back to any previous state
git reset --hard <commit-hash>
```

## Safety Warnings
- Always confirm before running `--hard` commands
- Check if commits are pushed before resetting
- Use `git stash` to save work before risky operations
- `git reflog` is your friend - commits aren't truly lost for ~30 days
