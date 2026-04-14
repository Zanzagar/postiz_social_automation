Auto-generate skills from git commit history and recurring patterns.

Usage: `/skill-create [--days N] [--min-pattern N]`

Arguments: $ARGUMENTS

## Process

### Step 1: Analyze Git History
```bash
# Default: last 30 days of commits
git log --since="30 days ago" --pretty=format:"%h %s" --name-only
```

Extract:
- Conventional commit types (feat, fix, refactor, test, etc.)
- Files frequently changed together (co-change clusters)
- Repeated fix patterns (same file/area fixed multiple times)
- Common commit message themes

### Step 2: Categorize Patterns

| Category | Signal | Example |
|----------|--------|---------|
| **Feature area** | Files co-changed 3+ times | `src/auth/` always changed together |
| **Fix hotspot** | Same area fixed repeatedly | `src/parser.py` fixed 5 times |
| **Test pattern** | Testing patterns repeated | Always mocking `requests` the same way |
| **Refactor theme** | Repeated refactoring | Extracting helpers from large functions |

### Step 3: Cluster Related Patterns

Group related patterns into potential skills:
```
Cluster: "API Testing"
- 8 commits touching test files with "api" in path
- Common pattern: pytest fixtures for API clients
- Repeated mock pattern for external services
- Confidence: HIGH (8 data points)

Cluster: "Database Migrations"
- 4 commits with migration files
- Pattern: always add index after column add
- Confidence: MEDIUM (4 data points)
```

### Step 4: Propose Skills

Present discovered clusters to user:

```markdown
# Discovered Skill Candidates

## 1. API Testing Patterns (HIGH confidence)
Based on 8 commits over 30 days
Would codify: fixture patterns, mock patterns, assertion helpers
**Create this skill?** [Y/n]

## 2. Database Migration Safety (MEDIUM confidence)
Based on 4 commits over 30 days
Would codify: index-after-column, rollback testing, migration ordering
**Create this skill?** [Y/n]

## 3. Error Handling Patterns (LOW confidence)
Based on 2 commits over 30 days
Would codify: custom exception hierarchy, error response format
**Create this skill?** [Y/n/wait for more data]
```

### Step 5: Generate SKILL.md

For each accepted skill, generate `.claude/skills/{name}/SKILL.md`:

```markdown
# Skill: {Name}

## When to Activate
{Trigger conditions based on detected patterns}

## Patterns
{Extracted patterns from git history}

## Examples
{Code examples from actual commits}

## Anti-Patterns
{Common mistakes found in fix commits}
```

### Step 6: User Review

**Important**: Always show the generated SKILL.md for user review before saving.
User can edit, approve, or reject each generated skill.

## Flags

| Flag | Default | Effect |
|------|---------|--------|
| `--days N` | 30 | Analysis window in days |
| `--min-pattern N` | 3 | Minimum occurrences to count as pattern |
| `--include-fixes` | true | Include fix commits in analysis |
| `--dry-run` | false | Show candidates without creating files |

## Confidence Levels

| Level | Threshold | Action |
|-------|-----------|--------|
| HIGH | 6+ occurrences | Recommend creating |
| MEDIUM | 3-5 occurrences | Suggest creating |
| LOW | 2 occurrences | Note but suggest waiting |

## When to Use

- After a sprint/milestone (codify what you learned)
- When onboarding to a new codebase (discover patterns)
- Monthly maintenance (evolve skills from real usage)
- Complements `/evolve` which creates skills from instincts
