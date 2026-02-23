Fix Go build errors, `go vet` warnings, and linter issues incrementally.

Usage: `/go-build`

Arguments: $ARGUMENTS

## Diagnostic Commands

```bash
go build ./...           # Primary build check
go vet ./...             # Static analysis
staticcheck ./...        # Extended linting
golangci-lint run        # Comprehensive linting
go mod verify            # Module integrity
go mod tidy -v           # Dependency cleanup
```

## Common Errors Fixed

| Error | Typical Fix |
|-------|-------------|
| `undefined: X` | Add import or fix typo |
| `cannot use X as Y` | Type conversion or fix assignment |
| `missing return` | Add return statement |
| `X does not implement Y` | Add missing interface method |
| `import cycle` | Restructure packages |
| `declared but not used` | Remove or use variable |
| `cannot find package` | `go get` or `go mod tidy` |

## Fix Strategy

1. **Build errors first** - Code must compile
2. **Vet warnings second** - Fix suspicious constructs
3. **Lint warnings third** - Style and best practices
4. **One fix at a time** - Verify each change
5. **Minimal changes** - Don't refactor, just fix

## Stop Conditions

The agent will stop and report if:
- Same error persists after 3 attempts
- Fix introduces more errors
- Requires architectural changes
- Missing external dependencies

## Integration

- Use `/go-test` after build succeeds
- Use `/go-review` for code quality review
- Use `/verify` for full verification pipeline

## Agent

Invokes the **go-build-resolver** agent (sonnet, all tools).
