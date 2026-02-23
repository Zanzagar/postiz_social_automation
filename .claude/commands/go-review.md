Comprehensive Go code review for idiomatic patterns, concurrency safety, and security.

Usage: `/go-review [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | All uncommitted `.go` file changes |
| `staged` | Only staged `.go` changes |
| `<path>` | Specific file or directory |

## Review Categories

### CRITICAL (Must Fix)
- SQL/Command injection vulnerabilities
- Race conditions without synchronization
- Goroutine leaks (missing context cancellation)
- Hardcoded credentials
- Unsafe pointer usage
- Ignored errors in critical paths

### HIGH (Should Fix)
- Missing error wrapping with context (`fmt.Errorf("...: %w", err)`)
- `panic()` instead of error returns
- Context not propagated through call chain
- Unbuffered channels causing deadlocks
- Interface not satisfied errors
- Missing mutex protection on shared state

### MEDIUM (Consider)
- Non-idiomatic patterns (e.g., getter methods, stuttering names)
- Missing godoc comments on exported symbols
- Inefficient string concatenation (use `strings.Builder`)
- Slice not preallocated when size is known
- Table-driven tests not used

## Automated Checks

```bash
go vet ./...                   # Static analysis
staticcheck ./...              # Advanced checks
golangci-lint run              # Comprehensive linting
go build -race ./...           # Race detection
govulncheck ./...              # Known vulnerabilities
```

## Approval Criteria

| Status | Condition |
|--------|-----------|
| **APPROVE** | No CRITICAL or HIGH issues |
| **WARNING** | Only MEDIUM issues |
| **BLOCK** | CRITICAL or HIGH issues found |

## Integration

- Use `/go-test` first to ensure tests pass
- Use `/go-build` if build errors occur
- Use `/go-review` before committing
- Use `/code-review` for language-agnostic concerns

## Agent

Invokes the **go-reviewer** agent (sonnet, read-only).
