---
name: python-testing
description: pytest patterns, fixtures, parametrize, mocking, async testing, coverage
---
# Python Testing Skill

## pytest Patterns

### Markers
```python
import pytest

@pytest.mark.slow          # Skip with: pytest -m "not slow"
@pytest.mark.integration   # Run with: pytest -m integration
@pytest.mark.parametrize("input,expected", [(1, 2), (3, 4)])
def test_example(input, expected):
    assert transform(input) == expected
```

### conftest.py Organization
- `tests/conftest.py` — Shared fixtures across all tests
- `tests/unit/conftest.py` — Unit-specific fixtures
- `tests/integration/conftest.py` — Integration fixtures (DB, API clients)
- Keep fixtures close to where they're used

## Fixture Strategies

### Scope
```python
@pytest.fixture(scope="session")    # Once per test session (DB setup)
@pytest.fixture(scope="module")     # Once per test file
@pytest.fixture(scope="class")      # Once per test class
@pytest.fixture(scope="function")   # Default: once per test function
```

### Factory Fixtures
```python
@pytest.fixture
def make_user():
    def _make_user(name="test", email=None):
        email = email or f"{name}@example.com"
        return User(name=name, email=email)
    return _make_user

def test_user_creation(make_user):
    user = make_user(name="alice")
    assert user.email == "alice@example.com"
```

### Database Fixtures
```python
@pytest.fixture
def db_session(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
```

## Parametrize Patterns

```python
# Basic parametrize
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_upper(input, expected):
    assert input.upper() == expected

# Multiple parameters with IDs
@pytest.mark.parametrize("x,y,expected", [
    pytest.param(1, 2, 3, id="positive"),
    pytest.param(-1, 1, 0, id="mixed"),
    pytest.param(0, 0, 0, id="zeros"),
])
def test_add(x, y, expected):
    assert add(x, y) == expected

# Stacked parametrize (cartesian product)
@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [10, 20])
def test_multiply(x, y):  # Runs 4 times
    assert isinstance(x * y, int)
```

## Mock Best Practices

### patch vs Dependency Injection
```python
# PREFER: Dependency injection (testable by design)
def fetch_data(client=None):
    client = client or HttpClient()
    return client.get("/data")

def test_fetch_data():
    mock_client = Mock()
    mock_client.get.return_value = {"key": "value"}
    result = fetch_data(client=mock_client)
    assert result == {"key": "value"}

# WHEN NEEDED: patch (for code you don't control)
from unittest.mock import patch

@patch("myapp.service.external_api.call")
def test_service(mock_call):
    mock_call.return_value = {"status": "ok"}
    result = my_service()
    mock_call.assert_called_once()
```

### Common Mock Patterns
```python
# Mock context manager
mock_file = mock_open(read_data="file contents")
with patch("builtins.open", mock_file):
    result = read_config()

# Mock async function
async_mock = AsyncMock(return_value={"data": 42})

# Side effects for sequential calls
mock.side_effect = [value1, value2, ValueError("boom")]
```

## Async Testing

```python
import pytest

# pytest-asyncio (recommended)
@pytest.mark.asyncio
async def test_async_function():
    result = await async_fetch()
    assert result is not None

# Async fixture
@pytest.fixture
async def async_client():
    async with AsyncClient(app=app) as client:
        yield client

@pytest.mark.asyncio
async def test_endpoint(async_client):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
```

## Coverage Targets

- **Realistic goals**: 80-90% line coverage for application code
- **Branch coverage**: Enable with `--cov-branch` (catches untested conditionals)
- **Don't chase 100%**: Diminishing returns after ~90%
- **Exclude from coverage**: `# pragma: no cover` for debug code, abstract methods
- **Config**: `pyproject.toml` `[tool.coverage.run]` section

```toml
[tool.coverage.run]
branch = true
source = ["src"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```
