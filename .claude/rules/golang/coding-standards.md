---
paths: ["**/*.go"]
---
<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/golang/coding-standards.md -->
# Go Coding Standards

Auto-loaded for `.go` files. These conventions follow Go idioms and community best practices.

## Error Handling

### Always Check Errors
```go
// GOOD: Always handle errors explicitly
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// BAD: Never ignore errors
result, _ := doSomething()  // Don't do this
```

### Wrap with Context
```go
// Use %w for wrappable errors (allows errors.Is/As)
if err != nil {
    return fmt.Errorf("fetching user %d: %w", userID, err)
}

// Define sentinel errors for expected conditions
var ErrNotFound = errors.New("not found")
var ErrPermission = errors.New("permission denied")
```

### Error Type Strategy
```go
// Custom error types for complex error info
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation: %s — %s", e.Field, e.Message)
}
```

## Naming Conventions

### General
- **MixedCaps** (not snake_case): `userID`, `httpClient`, `maxRetries`
- **Acronyms** all caps: `URL`, `HTTP`, `ID` (not `Url`, `Http`, `Id`)
- **Short receivers**: `func (s *Server) Start()` — 1-2 letter abbreviation of type
- **Unexported by default**: Only export what the package contract requires

### Package Design
```go
// Package names: short, lowercase, no underscores
package user     // GOOD
package userAuth // BAD — use package auth instead

// Avoid stutter: user.User is fine, user.UserService is not
type Service struct { ... }  // user.Service — clean
```

## Interface Design

### Accept Interfaces, Return Structs
```go
// GOOD: Accept the narrowest interface you need
func ProcessData(r io.Reader) error {
    // works with files, buffers, HTTP bodies, etc.
}

// GOOD: Return concrete types
func NewServer(cfg Config) *Server {
    return &Server{cfg: cfg}
}
```

### Keep Interfaces Small
```go
// GOOD: Single-method interfaces are powerful
type Validator interface {
    Validate() error
}

// BAD: Kitchen-sink interfaces
type UserManager interface {
    Create(u User) error
    Update(u User) error
    Delete(id int) error
    Find(id int) (User, error)
    List() ([]User, error)
    // ... too many methods
}
```

### Define Interfaces at Consumer Site
```go
// The CONSUMER defines the interface, not the producer
// This keeps packages decoupled

// In package handler:
type UserStore interface {
    GetUser(id int) (User, error)
}

func NewHandler(store UserStore) *Handler { ... }
```

## Goroutines and Concurrency

### Always Have Exit Conditions
```go
// GOOD: Context-based cancellation
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case <-ctx.Done():
            return
        case job, ok := <-jobs:
            if !ok {
                return
            }
            process(job)
        }
    }
}
```

### Use Context for Cancellation
```go
// Pass context as first parameter
func (s *Service) FetchUser(ctx context.Context, id int) (*User, error) {
    // Respect cancellation
    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
    }
    // ... fetch user
}
```

### Protect Shared State
```go
// Prefer channels for communication
results := make(chan Result, 10)

// Use sync.Mutex only for simple shared state
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

## Testing

### Table-Driven Tests
```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

### Test Helpers
```go
// Use t.Helper() for test helper functions
func assertNoError(t *testing.T, err error) {
    t.Helper()
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}
```

## Struct Patterns

```go
// Use functional options for complex constructors
type Option func(*Server)

func WithPort(port int) Option {
    return func(s *Server) { s.port = port }
}

func NewServer(opts ...Option) *Server {
    s := &Server{port: 8080}  // defaults
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

## Security Essentials

### Secrets — Never Hardcode
```go
// DO: Validate env vars at startup, fail fast
func requireEnv(key string) string {
    val := os.Getenv(key)
    if val == "" {
        log.Fatalf("required env var %s not set", key)
    }
    return val
}

var dbURL = requireEnv("DATABASE_URL")
```

### Context Timeouts — Always Bound External Calls
```go
// Every HTTP call, DB query, or external RPC needs a timeout
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel() // ALWAYS defer cancel to avoid goroutine/memory leaks

resp, err := client.Do(req.WithContext(ctx))
```

Run `gosec ./...` for static security analysis. See `/security-audit` for comprehensive scanning.

## Tooling

- `gofmt` / `goimports` — **mandatory**, no style debates
- `go vet` — run after every edit (catches subtle bugs)
- `staticcheck` — extended static analysis beyond `go vet`

### Testing with Race Detection
```bash
# ALWAYS use -race in development — catches data races at runtime
go test -race -cover ./...
```

## Avoid

- `init()` functions — prefer explicit initialization
- `panic()` in library code — return errors instead
- Global mutable state — pass dependencies explicitly
- Deep package nesting — prefer flat, focused packages
- `interface{}` / `any` without type assertions — use generics where possible (Go 1.18+)

See `golang-patterns` skill for comprehensive patterns reference.
