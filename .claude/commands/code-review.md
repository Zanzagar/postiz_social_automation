Comprehensive security and quality review of uncommitted changes.

Usage: `/code-review [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | All uncommitted changes (`git diff --name-only HEAD`) |
| `staged` | Only staged changes (`git diff --name-only --cached`) |
| `<path>` | Specific file or directory |

## Review Checklist

### Security Issues (CRITICAL - must block)

- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Missing input validation
- Insecure dependencies
- Path traversal risks
- Unsafe deserialization
- Command injection

### Code Quality (HIGH - should fix)

- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- `console.log` / `print()` debug statements
- TODO/FIXME comments without issue references
- Missing type hints on public APIs

### Best Practices (MEDIUM - consider)

- Mutation patterns (prefer immutable)
- Missing tests for new code
- Accessibility issues (a11y)
- Non-idiomatic patterns for the language
- Magic numbers without named constants

## Report Format

```
CODE REVIEW REPORT
==================
File: src/auth/tokens.py

[CRITICAL] Line 42: Hardcoded API key in source code
  Fix: Move to environment variable

[HIGH] Line 88-145: Function exceeds 50 lines (57 lines)
  Fix: Extract validation logic to helper

[MEDIUM] Line 12: Magic number 3600
  Fix: Use named constant TOKEN_EXPIRY_SECONDS = 3600
==================

Verdict: BLOCK (1 CRITICAL, 1 HIGH, 1 MEDIUM)
```

## Approval Criteria

| Status | Condition |
|--------|-----------|
| **APPROVE** | No CRITICAL or HIGH issues |
| **WARNING** | Only MEDIUM issues (merge with caution) |
| **BLOCK** | CRITICAL or HIGH issues found |

## Confidence Filtering

Only report findings with >80% confidence. Skip speculative issues.

## Integration

- Run after implementation, before `/commit`
- Part of `/orchestrate review` pipeline
- Complements `/security-audit` (which does deeper OWASP analysis)

## Agent

Invokes the **code-reviewer** agent (sonnet, read-only).
