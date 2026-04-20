---
name: code-review
description: Systematic code review for quality, security, and maintainability. Use when reviewing PRs, analyzing code quality, or providing feedback on implementations.
---

# Code Review Skill

## When to Use
- User asks to review code or a PR
- User asks "is this code good?" or similar
- After implementing a significant feature
- When user asks about code quality

## Review Checklist

### 1. Correctness
- Does the code do what it's supposed to do?
- Are edge cases handled?
- Are there off-by-one errors, null checks, or boundary conditions?

### 2. Security
- Input validation present?
- SQL injection, XSS, command injection risks?
- Secrets or credentials exposed?
- Proper authentication/authorization?

### 3. Performance
- Unnecessary loops or redundant operations?
- N+1 query problems?
- Large data structures in memory?
- Missing indexes for database queries?

### 4. Maintainability
- Is the code readable without extensive comments?
- Are functions focused (single responsibility)?
- Is there code duplication that should be extracted?
- Are names descriptive?

### 5. Error Handling
- Are errors caught and handled appropriately?
- Are error messages helpful for debugging?
- Is there proper logging?

### 6. Testing
- Are there tests for the new code?
- Do tests cover edge cases?
- Are tests readable and maintainable?

## Confidence Filtering

**Only report issues at >80% confidence.**

Before reporting an issue, ask:
- Am I confident this is actually a problem? (not just a different style)
- Could there be context I'm missing that makes this intentional?
- Is this worth the author's time to address?

If <80% confident, don't report. If borderline, add "(verify)" prefix.

## Severity Classification

| Severity | Criteria | Examples |
|----------|----------|----------|
| CRITICAL | Security vulnerability, data loss, production crash | SQL injection, credential exposure, null deref in hot path |
| HIGH | Likely bug, performance issue, maintenance debt | Race condition, N+1 query, missing error handling |
| MEDIUM | Code quality concern, minor bug risk | Missing type hints, unclear naming, code duplication |
| LOW | Style preference, minor improvement | Comment clarity, import ordering (defer to linter) |

## Finding Consolidation

Group similar issues instead of repeating:
- Instead of 5 separate "missing type hint" issues, report once with count
- Format: "Found 5 functions missing return type hints: `func_a`, `func_b`, ..."
- Consolidate when: same issue type, same severity, related files
- Report separately when: different root causes or different severities

## Python-Specific Patterns

Always check for these common anti-patterns:
- Mutable default arguments: `def foo(items=[])` — use `items=None` instead
- Bare except clauses: `except:` should be `except Exception:`
- Type hint gaps on public APIs
- Missing `if __name__ == "__main__":` guard in scripts
- Hardcoded credentials or file paths

## Review Format

Structure output by severity:

1. **Summary**: One-line assessment with overall verdict (approve/request changes)
2. **Findings** (grouped by severity):
   - CRITICAL — must fix before merge
   - HIGH — should fix before merge
   - MEDIUM — consider fixing
   - LOW — optional improvements
3. **Praise**: What's done well (reinforces good patterns)

Each finding: `[SEVERITY] file:line — Description. Suggestion: how to fix.`

## Tone
Be constructive and specific. Instead of "this is bad", say "consider X because Y".
