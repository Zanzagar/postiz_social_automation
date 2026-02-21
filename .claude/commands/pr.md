Create a GitHub Pull Request for the current branch.

Usage:
- `/pr` - Create PR with auto-generated title and description
- `/pr "Add user authentication"` - Create PR with specified title

Arguments: $ARGUMENTS

## Workflow

1. **Verify branch state:**
   ```bash
   git status
   git branch --show-current
   ```

2. **Check for uncommitted changes:**
   - If uncommitted changes exist, ask: "Commit changes first?"
   - Use `/commit` workflow to commit them

3. **Ensure branch is pushed:**
   ```bash
   git push -u origin $(git branch --show-current)
   ```

4. **Analyze commits for PR:**
   ```bash
   git log main..HEAD --oneline
   git diff main..HEAD --stat
   ```

5. **Generate PR content:**

   **Title:** (from argument or first commit message)
   - Use conventional commit style if applicable
   - Keep under 72 characters

   **Description template:**
   ```markdown
   ## Summary
   [2-3 bullet points describing the changes]

   ## Changes
   - [List of specific changes]

   ## Testing
   - [ ] Tests pass locally (`pytest`)
   - [ ] Linting passes (`ruff check`)
   - [ ] Manual testing completed

   ## Related
   - Closes #[issue number] (if applicable)
   - Related to #[PR number] (if applicable)
   ```

6. **Create PR:**
   ```bash
   gh pr create --title "<title>" --body "<description>"
   ```

7. **Report result:**
   > Created PR #123: [title]
   > URL: https://github.com/owner/repo/pull/123

## PR Title Guidelines

Based on conventional commits:

| Change Type | PR Title Example |
|-------------|------------------|
| New feature | `feat: Add user registration flow` |
| Bug fix | `fix: Resolve payment timeout issue` |
| Multiple changes | `feat: Add auth with password reset` |
| Refactoring | `refactor: Restructure API routes` |

## Requirements Checklist

Before creating PR, verify:
- [ ] All tests pass
- [ ] No linting errors
- [ ] Meaningful commit messages
- [ ] Branch is up to date with main

If checks fail, report issues and suggest fixes.

## Draft PRs

To create a draft PR:
```
/pr --draft
```

Use drafts for:
- Work in progress
- Early feedback requests
- Incomplete implementations

## After Creating PR

Suggest next steps:
- "Request review from team members?"
- "Add labels or milestone?"
- "Link to related issues?"
