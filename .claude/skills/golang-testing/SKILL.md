---
name: golang-testing
description: Go test patterns, benchmarks, fuzzing, testify, httptest, integration tests
---
# Go Testing Skill

## Table-Driven Tests

The standard Go pattern for comprehensive test coverage:

```go
func TestParse(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    *Config
        wantErr bool
    }{
        {name: "valid", input: `{"port": 8080}`, want: &Config{Port: 8080}},
        {name: "empty", input: `{}`, want: &Config{}},
        {name: "invalid JSON", input: `{bad}`, wantErr: true},
        {name: "empty string", input: "", wantErr: true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Parse(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("Parse() error = %v, wantErr %v", err, tt.wantErr)
            }
            if !tt.wantErr && !reflect.DeepEqual(got, tt.want) {
                t.Errorf("Parse() = %v, want %v", got, tt.want)
            }
        })
    }
}
```

## Benchmarks

```go
func BenchmarkSort(b *testing.B) {
    data := generateTestData(10000)
    b.ResetTimer() // Exclude setup time

    for i := 0; i < b.N; i++ {
        input := make([]int, len(data))
        copy(input, data)
        sort.Ints(input)
    }
}

// Memory benchmarks
func BenchmarkAlloc(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        _ = make([]byte, 1024)
    }
}
```

Run: `go test -bench=. -benchmem ./...`

## Fuzzing

```go
func FuzzParse(f *testing.F) {
    // Seed corpus
    f.Add(`{"port": 8080}`)
    f.Add(`{}`)
    f.Add("")

    f.Fuzz(func(t *testing.T, input string) {
        result, err := Parse(input)
        if err != nil {
            return // Invalid input is expected
        }
        // If it parses, it should round-trip
        output, err := Marshal(result)
        if err != nil {
            t.Fatalf("Marshal failed on valid parse result: %v", err)
        }
        reparsed, err := Parse(output)
        if err != nil {
            t.Fatalf("Round-trip failed: %v", err)
        }
        if !reflect.DeepEqual(result, reparsed) {
            t.Errorf("Round-trip mismatch")
        }
    })
}
```

Run: `go test -fuzz=FuzzParse -fuzztime=30s`

## testify Assertions

```go
import (
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestUser(t *testing.T) {
    user, err := GetUser(1)

    // require: stops test on failure (for preconditions)
    require.NoError(t, err)
    require.NotNil(t, user)

    // assert: continues test on failure (for assertions)
    assert.Equal(t, "alice", user.Name)
    assert.True(t, user.IsActive)
    assert.Contains(t, user.Email, "@")
    assert.Len(t, user.Roles, 2)
    assert.ElementsMatch(t, []string{"admin", "user"}, user.Roles)
}
```

## httptest for HTTP Testing

```go
func TestHandler(t *testing.T) {
    // Create handler
    handler := NewAPIHandler(mockDB)

    // Create test request
    req := httptest.NewRequest("GET", "/api/users/1", nil)
    req.Header.Set("Authorization", "Bearer test-token")

    // Record response
    w := httptest.NewRecorder()
    handler.ServeHTTP(w, req)

    // Assert
    assert.Equal(t, http.StatusOK, w.Code)

    var user User
    err := json.NewDecoder(w.Body).Decode(&user)
    require.NoError(t, err)
    assert.Equal(t, "alice", user.Name)
}

// Test server for integration tests
func TestClientIntegration(t *testing.T) {
    srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
    }))
    defer srv.Close()

    client := NewClient(srv.URL)
    status, err := client.HealthCheck()
    require.NoError(t, err)
    assert.Equal(t, "ok", status)
}
```

## Integration Test Organization

```go
//go:build integration

package myapp_test

// Only runs with: go test -tags=integration ./...

func TestDatabaseIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test in short mode")
    }
    // ... test with real database
}
```

### TestMain for Setup/Teardown
```go
func TestMain(m *testing.M) {
    // Setup: start containers, seed DB, etc.
    db := setupTestDB()

    code := m.Run()

    // Teardown
    db.Close()
    os.Exit(code)
}
```
