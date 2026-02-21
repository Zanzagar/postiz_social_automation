Enforce TDD workflow for Go with table-driven tests and 80%+ coverage.

Usage: `/go-test <feature or function description>`

Arguments: $ARGUMENTS

## TDD Cycle

```
RED     ->  Write failing table-driven test
GREEN   ->  Implement minimal code to pass
REFACTOR -> Improve code, tests stay green
REPEAT  ->  Next test case
```

## Test Patterns

### Table-Driven Tests
```go
tests := []struct {
    name    string
    input   InputType
    want    OutputType
    wantErr bool
}{
    {"valid input", validInput, expectedOutput, false},
    {"empty input", emptyInput, zeroValue, true},
    {"boundary", maxInput, maxOutput, false},
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got, err := Function(tt.input)
        if (err != nil) != tt.wantErr {
            t.Errorf("error = %v, wantErr %v", err, tt.wantErr)
        }
        if got != tt.want {
            t.Errorf("got %v, want %v", got, tt.want)
        }
    })
}
```

### Parallel Tests
```go
for _, tt := range tests {
    tt := tt // capture range variable
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // test body
    })
}
```

### Test Helpers
```go
func setupTestDB(t *testing.T) *sql.DB {
    t.Helper()
    db := createDB()
    t.Cleanup(func() { db.Close() })
    return db
}
```

## Coverage Commands

```bash
go test -cover ./...                        # Basic coverage
go test -coverprofile=coverage.out ./...    # Profile
go tool cover -html=coverage.out            # View in browser
go tool cover -func=coverage.out            # By function
go test -race -cover ./...                  # With race detection
```

## Coverage Targets

| Code Type | Target |
|-----------|--------|
| Critical business logic | 100% |
| Public APIs | 90%+ |
| General code | 80%+ |
| Generated code | Exclude |

## Best Practices

**DO:** Write test FIRST, use table-driven tests, test behavior not internals, include edge cases (nil, empty, max)

**DON'T:** Write code before tests, skip RED phase, test private functions directly, use `time.Sleep` in tests

## Integration

- Use `/go-build` if build errors occur
- Use `/go-review` for code quality review
- Use `/verify` for full verification pipeline

## Skills Referenced

- `golang-testing` - Table-driven tests, benchmarks, fuzzing
- `golang-patterns` - Go idioms and patterns
