Create a git commit with proper conventional commit format.

Usage:
- `/commit` - Analyze changes and create appropriate commit(s)
- `/commit feat: Add user authentication` - Commit with specified message
- `/commit --amend` - Amend the last commit (use sparingly)

Arguments: $ARGUMENTS

## Workflow

### If no message provided:

1. **Check current state:**
   ```bash
   git status
   git diff --staged
   git diff
   ```

2. **Analyze the changes:**
   - What files were modified?
   - What is the nature of the change? (feature, fix, refactor, etc.)
   - Are there multiple logical changes that should be separate commits?

3. **If multiple logical changes exist:**
   - Stage and commit each separately
   - Example: Don't combine a bug fix with a new feature
   - Ask user: "I see changes for X and Y. Should I commit these separately?"

4. **Generate conventional commit message:**
   - Determine the type: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `style`
   - Write concise description (50 chars or less)
   - Add body if change is complex

5. **Run pre-commit checks:**
   ```bash
   ruff check src/ tests/  # If Python
   pytest -q              # Quick test run
   ```

6. **Create the commit:**
   ```bash
   git add <appropriate files>
   git commit -m "<type>: <description>"
   ```

7. **Report to user:**
   > Created commit: `feat: Add user authentication endpoint`

### If message provided:

1. Validate message follows conventional format
2. If not, suggest correction:
   > "Message should start with type. Did you mean: `fix: Resolve login bug`?"
3. Stage all changes and commit with provided message

## Conventional Commit Types

| Type | When to Use | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: Add dark mode toggle` |
| `fix` | Bug fix | `fix: Resolve crash on empty input` |
| `docs` | Documentation | `docs: Update API reference` |
| `refactor` | Code restructure | `refactor: Extract validation logic` |
| `test` | Test changes | `test: Add auth integration tests` |
| `chore` | Maintenance | `chore: Update dependencies` |
| `perf` | Performance | `perf: Cache database queries` |
| `style` | Formatting | `style: Fix indentation` |
| `ci` | CI/CD | `ci: Add deploy workflow` |

## Message Guidelines

**Good:**
```
feat: Add user registration endpoint
fix: Resolve null pointer in payment processing
refactor: Extract email validation to utility
```

**Bad:**
```
update files          # No type, vague
fixed stuff           # No type, vague
WIP                   # Not descriptive
feat: Add feature     # Redundant
```

## Breaking Changes

For breaking changes, add `!` after type:
```
feat!: Change authentication to OAuth2
```

Or add footer:
```
feat: Migrate to new API format

BREAKING CHANGE: API responses now use camelCase
```

## After Committing

Suggest next steps:
- "Push to remote? `git push origin <branch>`"
- "Changes look ready for PR? Use `/pr` to create one"
