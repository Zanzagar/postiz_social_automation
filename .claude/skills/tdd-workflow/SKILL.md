---
name: tdd-workflow
description: Complete RED-GREEN-REFACTOR TDD cycle patterns, coverage thresholds by code type, mocking strategies, Arrange-Act-Assert templates for pytest, Jest, and Go test
---
# TDD Workflow Skill

## The RED-GREEN-REFACTOR Cycle

### RED Phase — Write a Failing Test
Define the desired behavior before writing any implementation.

```python
# pytest example
def test_calculate_variogram_returns_semivariance():
    """RED: This test defines what we want — it should FAIL."""
    data = [(0, 0, 1.0), (1, 0, 2.0), (0, 1, 1.5)]
    result = calculate_variogram(data, n_lags=5)
    assert len(result.lags) == 5
    assert all(sv >= 0 for sv in result.semivariance)
```

**Rules:**
- Test MUST fail before writing implementation
- Test should fail for the RIGHT reason (import error or assertion, not syntax error)
- One behavior per test — don't test multiple things

### GREEN Phase — Minimum Code to Pass
Write the simplest implementation that makes the test pass.

```python
# Minimum implementation — NOT the final version
def calculate_variogram(data, n_lags=10):
    lags = [i * max_dist / n_lags for i in range(1, n_lags + 1)]
    semivariance = [0.0] * n_lags  # Placeholder
    # TODO: actual semivariance calculation
    return VariogramResult(lags=lags, semivariance=semivariance)
```

**Rules:**
- Do NOT add features not required by tests
- Do NOT optimize yet
- Do NOT handle edge cases not tested
- If the test passes, STOP writing code

### REFACTOR Phase — Improve While Green
Clean up code while all tests remain passing.

**Safe refactors:**
- Extract helper functions
- Rename variables for clarity
- Remove duplication
- Improve performance (with benchmark tests)

**Rules:**
- Run tests after EVERY change
- If a test fails, revert the refactor
- Don't add new behavior (that requires new RED phase)

## Arrange-Act-Assert (AAA) Pattern

Every test should have three distinct sections:

```python
def test_kriging_prediction():
    # ARRANGE — Set up test data and expected state
    known_points = np.array([[0, 0], [1, 0], [0, 1]])
    known_values = np.array([10.0, 20.0, 15.0])
    prediction_point = np.array([[0.5, 0.5]])

    # ACT — Execute the behavior under test
    kriging = OrdinaryKriging(known_points, known_values)
    result = kriging.predict(prediction_point)

    # ASSERT — Verify the outcome
    assert result.shape == (1,)
    assert 10.0 <= result[0] <= 20.0  # Within data range
```

```javascript
// Jest example
test('spatial join matches points to polygons', () => {
    // Arrange
    const points = [{ lat: 40.7, lon: -74.0 }];
    const polygons = [{ name: 'NYC', geometry: nycBoundary }];

    // Act
    const result = spatialJoin(points, polygons);

    // Assert
    expect(result[0].polygon).toBe('NYC');
});
```

```go
// Go example — table-driven
func TestDistanceMeters(t *testing.T) {
    tests := []struct {
        name     string
        lat1, lon1, lat2, lon2 float64
        wantMin, wantMax       float64
    }{
        {"same point", 0, 0, 0, 0, 0, 0},
        {"known distance", 40.7128, -74.0060, 40.7580, -73.9855, 5000, 6000},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := DistanceMeters(tt.lat1, tt.lon1, tt.lat2, tt.lon2)
            if got < tt.wantMin || got > tt.wantMax {
                t.Errorf("DistanceMeters() = %v, want [%v, %v]", got, tt.wantMin, tt.wantMax)
            }
        })
    }
}
```

## Coverage Thresholds by Code Type

| Code Type | Target | Rationale |
|-----------|--------|-----------|
| Business logic / algorithms | 90%+ | Core value — must be well tested |
| API endpoints / routes | 80%+ | Integration points need coverage |
| Data transformations / ETL | 85%+ | Silent failures are expensive |
| Configuration / setup | 60%+ | Mostly boilerplate, test happy path |
| CLI / UI glue code | 50%+ | Hard to unit test, use E2E instead |
| Generated code / migrations | Skip | Don't test generated code |

## Mocking Strategy Decision Tree

```
Need to isolate a dependency?
│
├─ Can you inject it? ──────────► Dependency injection (PREFERRED)
│   def process(client=None):
│       client = client or RealClient()
│
├─ External service? ───────────► Mock at boundary
│   @patch("myapp.api.requests.get")
│
├─ Database? ───────────────────► Use test database or fixture
│   @pytest.fixture
│   def db(): ...
│
├─ File system? ────────────────► Use tmp_path (pytest) or tempfile
│   def test_export(tmp_path): ...
│
├─ Time-dependent? ─────────────► freeze_gun or manual injection
│   @freeze_time("2026-01-15")
│
└─ Random/stochastic? ─────────► Set seed + tolerance
    np.random.seed(42)
    assert abs(result - expected) < tolerance
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Test after implementation | Tests written to pass, not to verify behavior | Write test FIRST, see it fail |
| Testing implementation details | Tests break on refactor | Test behavior and outputs, not internals |
| Shared mutable state between tests | Order-dependent failures | Fresh fixtures per test |
| Catching all exceptions in tests | Hides real failures | Let unexpected exceptions propagate |
| `assert True` or no assertions | Test always passes | Every test needs meaningful assertions |
| Giant test functions | Hard to debug failures | One behavior per test, descriptive names |

## When NOT to TDD

TDD is not always the right approach:
- **Exploratory prototyping** — spike first, then write tests for the keeper code
- **UI layout** — visual verification is more appropriate
- **One-off scripts** — if truly disposable, tests add overhead
- **Generated code** — test the generator, not the output

For these cases, write tests AFTER if the code will be maintained.
