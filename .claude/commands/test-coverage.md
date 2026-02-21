Analyze test coverage, identify gaps, and generate missing tests to reach 80%+ coverage.

Usage: `/test-coverage [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | Entire project |
| `<path>` | Specific file or directory |

## Step 1: Detect Test Framework

| Indicator | Coverage Command |
|-----------|-----------------|
| `jest.config.*` | `npx jest --coverage --coverageReporters=json-summary` |
| `vitest.config.*` | `npx vitest run --coverage` |
| `pytest` in deps | `pytest --cov=src --cov-report=json` |
| `Cargo.toml` | `cargo llvm-cov --json` |
| `pom.xml` with JaCoCo | `mvn test jacoco:report` |
| `go.mod` | `go test -coverprofile=coverage.out ./...` |

## Step 2: Analyze Coverage Report

1. Run the coverage command
2. Parse the output
3. List files **below 80% coverage**, sorted worst-first
4. For each under-covered file, identify:
   - Untested functions or methods
   - Missing branch coverage (if/else, switch, error paths)
   - Dead code inflating the denominator

## Step 3: Generate Missing Tests

Priority order for each under-covered file:

1. **Happy path** - Core functionality with valid inputs
2. **Error handling** - Invalid inputs, missing data, failures
3. **Edge cases** - Empty arrays, null/undefined, boundary values
4. **Branch coverage** - Each if/else, switch case, ternary

### Test Generation Rules

- Place tests adjacent to source (follow project convention)
- Use existing test patterns from the project
- Mock external dependencies (database, APIs, filesystem)
- Each test should be independent — no shared mutable state
- Descriptive names: `test_create_user_with_duplicate_email_returns_409`

## Step 4: Verify

1. Run full test suite — all tests must pass
2. Re-run coverage — verify improvement
3. If still below 80%, repeat for remaining gaps

## Step 5: Report

```
Coverage Report
------------------
File                        Before  After
src/services/auth.ts         45%     88%
src/utils/validation.ts      32%     82%
src/api/routes.py            58%     85%
------------------
Overall:                     67%     84%
```

## Focus Areas

- Functions with complex branching (high cyclomatic complexity)
- Error handlers and catch blocks
- Utility functions used across the codebase
- API endpoint handlers (request -> response flow)
- Edge cases: null, undefined, empty string, empty array, zero, negative

## Integration

- Use after `/tdd` to verify coverage targets
- Use before `/pr` to ensure quality gates
- Part of `/verify` pipeline
