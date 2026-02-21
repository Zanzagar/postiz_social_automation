Enforce test-driven development workflow: tests FIRST, then implementation.

Usage: `/tdd <feature or function description>`

Arguments: $ARGUMENTS

## What This Command Does

1. **Scaffold Interfaces** - Define types/interfaces first
2. **Generate Tests First** - Write failing tests (RED)
3. **Implement Minimal Code** - Write just enough to pass (GREEN)
4. **Refactor** - Improve code while keeping tests green
5. **Verify Coverage** - Ensure 80%+ test coverage

## TDD Cycle

```
RED     ->  Write a failing test
GREEN   ->  Write minimal code to pass
REFACTOR -> Improve code, keep tests passing
REPEAT  ->  Next feature/scenario
```

## How It Works

The tdd-guide agent will:

1. **Define interfaces** for inputs/outputs
2. **Write tests that FAIL** (code doesn't exist yet)
3. **Run tests** — verify they fail for the right reason
4. **Write minimal implementation** to make tests pass
5. **Run tests** — verify they pass
6. **Refactor** while keeping tests green
7. **Check coverage** — add tests if below 80%

## Coverage Requirements

| Code Type | Target |
|-----------|--------|
| Financial calculations | 100% |
| Authentication logic | 100% |
| Security-critical code | 100% |
| Core business logic | 100% |
| Public APIs | 90%+ |
| General code | 80%+ |
| Generated code | Exclude |

## Framework Detection

| Indicator | Test Framework |
|-----------|---------------|
| `pytest` in dependencies | pytest |
| `jest.config.*` | Jest |
| `vitest.config.*` | Vitest |
| `go.mod` | `go test` |
| `Cargo.toml` | `cargo test` |
| `pom.xml` | JUnit/Maven |

## TDD Best Practices

**DO:**
- Write the test FIRST, before any implementation
- Run tests after each change
- Test behavior, not implementation details
- Include edge cases and error scenarios
- One assert per test (when practical)
- Use descriptive test names

**DON'T:**
- Write implementation before tests
- Skip the RED phase
- Write too much code at once
- Mock everything (prefer integration tests)
- Ignore failing tests
- Test private internals

## Important Notes

**MANDATORY**: Tests must be written BEFORE implementation.

If Superpowers plugin is installed, it enforces the TDD cycle automatically and will delete production code written without failing tests first.

Without Superpowers, this command provides advisory guidance through the tdd-guide agent.

## Integration

- Use `/plan` first to understand what to build
- Use `/tdd` to implement with tests
- Use `/build-fix` if build errors occur
- Use `/code-review` to review implementation
- Use `/test-coverage` to verify coverage gaps

## Agent

Invokes the **tdd-guide** agent (sonnet, read-only). Advisory only — Superpowers enforces the cycle.
