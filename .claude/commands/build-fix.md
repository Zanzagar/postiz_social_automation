Incrementally fix build and type errors with minimal, safe changes.

Usage: `/build-fix`

Arguments: $ARGUMENTS

## Step 1: Detect Build System

| Indicator | Build Command |
|-----------|---------------|
| `package.json` with `build` script | `npm run build` or `pnpm build` |
| `tsconfig.json` | `npx tsc --noEmit` |
| `Cargo.toml` | `cargo build 2>&1` |
| `pom.xml` | `mvn compile` |
| `build.gradle` | `./gradlew compileJava` |
| `go.mod` | `go build ./...` |
| `pyproject.toml` | `python -m py_compile` or `mypy .` |
| `Makefile` | `make` |

## Step 2: Parse and Group Errors

1. Run the build command and capture stderr
2. Group errors by file path
3. Sort by dependency order (fix imports/types before logic errors)
4. Count total errors for progress tracking

## Step 3: Fix Loop (One Error at a Time)

For each error:

1. **Read the file** - See error context (10 lines around the error)
2. **Diagnose** - Identify root cause (missing import, wrong type, syntax error)
3. **Fix minimally** - Smallest change that resolves the error
4. **Re-run build** - Verify error is gone, no new errors introduced
5. **Move to next** - Continue with remaining errors

## Step 4: Guardrails

Stop and ask the user if:
- A fix introduces **more errors than it resolves**
- The **same error persists after 3 attempts**
- The fix requires **architectural changes**
- Build errors stem from **missing dependencies** (need install command)

## Step 5: Summary

```
Build Fix Summary
------------------
Errors fixed:     8
Errors remaining: 0
New errors:       0 (should always be zero)
------------------
Build: PASSING
```

## Recovery Strategies

| Situation | Action |
|-----------|--------|
| Missing module/import | Check if package is installed; suggest install command |
| Type mismatch | Read both type definitions; fix the narrower type |
| Circular dependency | Identify cycle with import graph; suggest extraction |
| Version conflict | Check package manifest for version constraints |
| Build tool misconfiguration | Read config file; compare with working defaults |

## Rules

- Fix **one error at a time** for safety
- Prefer **minimal diffs** over refactoring
- **Never refactor** while fixing builds — separate concerns
- Re-run build after **every** change

## Integration

- Use `/build-fix` when `go build`, `tsc`, `cargo build` etc. fail
- Follow with `/test` to verify tests still pass
- Follow with `/code-review` to review the fixes

## Agent

Invokes the **build-resolver** agent (sonnet, all tools).
