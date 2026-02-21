---
name: golang-patterns
description: Go idioms, error handling, concurrency patterns, interface design, testing
---
# Go Patterns Skill

## Go Idioms

### Accept Interfaces, Return Structs
```go
// GOOD: Accept interface (flexible for callers)
func ProcessData(r io.Reader) (*Result, error) {
    data, err := io.ReadAll(r)
    // ...
    return &Result{Data: data}, nil  // Return concrete struct
}

// Caller can pass any io.Reader: file, buffer, HTTP body, etc.
```

### Zero Values are Useful
```go
var buf bytes.Buffer    // Ready to use, no initialization needed
var mu sync.Mutex       // Ready to use
var wg sync.WaitGroup   // Ready to use
```

### Functional Options
```go
type Option func(*Server)

func WithPort(port int) Option { return func(s *Server) { s.port = port } }
func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }

func NewServer(opts ...Option) *Server {
    s := &Server{port: 8080, timeout: 30 * time.Second} // defaults
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// Usage: srv := NewServer(WithPort(9090), WithTimeout(time.Minute))
```

## Error Handling

### Wrapping with Context
```go
if err != nil {
    return fmt.Errorf("reading config %s: %w", path, err)
}
```

### Sentinel Errors
```go
var ErrNotFound = errors.New("not found")
var ErrPermission = errors.New("permission denied")

// Check with errors.Is (works through wrapping)
if errors.Is(err, ErrNotFound) {
    // handle not found
}
```

### Custom Error Types
```go
type ValidationError struct {
    Field   string
    Message string
}
func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation: %s - %s", e.Field, e.Message)
}

// Check with errors.As
var ve *ValidationError
if errors.As(err, &ve) {
    log.Printf("Invalid field: %s", ve.Field)
}
```

## Concurrency Patterns

### Worker Pool
```go
func processItems(items []Item, workers int) []Result {
    jobs := make(chan Item, len(items))
    results := make(chan Result, len(items))

    for w := 0; w < workers; w++ {
        go func() {
            for item := range jobs {
                results <- process(item)
            }
        }()
    }

    for _, item := range items {
        jobs <- item
    }
    close(jobs)

    var out []Result
    for range items {
        out = append(out, <-results)
    }
    return out
}
```

### Context for Cancellation
```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

select {
case result := <-doWork(ctx):
    return result, nil
case <-ctx.Done():
    return nil, ctx.Err()
}
```

### Fan-Out / Fan-In
```go
func fanOut(ctx context.Context, input <-chan int, workers int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)

    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for n := range input {
                select {
                case out <- process(n):
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    go func() { wg.Wait(); close(out) }()
    return out
}
```

## Interface Design

- **Small interfaces**: 1-3 methods (`io.Reader`, `fmt.Stringer`)
- **Define at use site**: Not where implemented
- **Composition**: Embed interfaces to combine them
- **Don't export single-implementation interfaces**

```go
// GOOD: Small, defined where needed
type Validator interface {
    Validate() error
}
```

## Table-Driven Tests

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"mixed", -1, 1, 0},
        {"zeros", 0, 0, 0},
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
