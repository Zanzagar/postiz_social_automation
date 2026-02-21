---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "src/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
---
<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/python/coding-standards.md -->
# Python Coding Standards

## Key Principles

- Write concise, technical code with accurate examples
- Prioritize clarity, efficiency, and best practices
- Use object-oriented programming for complex systems
- Use functional programming for data processing pipelines
- Use descriptive variable names that reflect their purpose
- Follow PEP 8 style guidelines

## Code Style

### Naming Conventions
```python
# Variables and functions: snake_case
user_count = 0
def calculate_total():
    pass

# Classes: PascalCase
class DataProcessor:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
```

### Type Hints
```python
# DO: Use type hints for function signatures
def process_data(items: list[str], limit: int = 10) -> dict[str, int]:
    pass

# DON'T: Skip type hints on public APIs
def process_data(items, limit=10):
    pass
```

### Docstrings
```python
def calculate_metrics(data: pd.DataFrame, threshold: float) -> dict:
    """Calculate performance metrics from input data.

    Args:
        data: Input DataFrame with required columns
        threshold: Minimum value for filtering

    Returns:
        Dictionary containing calculated metrics

    Raises:
        ValueError: If required columns are missing
    """
    pass
```

## Project Structure

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── core/           # Core functionality
│       ├── utils/          # Helper functions
│       └── config.py       # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_core.py
│   └── conftest.py
├── pyproject.toml
└── README.md
```

## Error Handling

### Basic Pattern
```python
# DO: Specific exceptions with context
try:
    result = process_file(filepath)
except FileNotFoundError:
    logger.error(f"File not found: {filepath}")
    raise
except PermissionError as e:
    logger.error(f"Permission denied: {filepath}")
    raise RuntimeError(f"Cannot access {filepath}") from e

# DON'T: Bare except or overly broad handling
try:
    result = process_file(filepath)
except:
    pass
```

### Custom Exception Hierarchies
```python
# Define domain-specific exceptions
class AppError(Exception):
    """Base exception for application errors."""
    pass

class ValidationError(AppError):
    """Raised when input validation fails."""
    pass

class ExternalServiceError(AppError):
    """Raised when external API calls fail."""
    def __init__(self, service: str, status_code: int, message: str):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} returned {status_code}: {message}")
```

### When to Raise vs Return
```python
# RAISE when: Operation cannot proceed, caller must handle
def get_user(user_id: int) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user

# RETURN None/Optional when: Missing data is expected/normal
def find_user(email: str) -> User | None:
    return db.query(User).filter_by(email=email).first()
```

### Retry Pattern for Transient Failures
```python
import time
from functools import wraps

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator for transient failures."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        sleep_time = delay * (backoff ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s")
                        time.sleep(sleep_time)
            raise last_exception
        return wrapper
    return decorator

@retry(max_attempts=3, delay=1.0)
def fetch_data(url: str) -> dict:
    return requests.get(url, timeout=10).json()
```

### Context Managers for Cleanup
```python
from contextlib import contextmanager

@contextmanager
def managed_resource(name: str):
    """Ensure cleanup even on exceptions."""
    resource = acquire_resource(name)
    try:
        yield resource
    finally:
        resource.cleanup()

# Usage
with managed_resource("database") as db:
    db.execute(query)  # cleanup happens even if this fails
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

# DO: Use appropriate log levels
logger.debug("Processing item %s", item_id)
logger.info("Completed processing %d items", count)
logger.warning("Retrying after failure: %s", error)
logger.error("Failed to process: %s", error, exc_info=True)

# DON'T: Use print for production code
print(f"Processing {item_id}")  # Use logger instead
```

## Testing

### Test Naming and Structure
```python
# DO: Descriptive test names following pattern: test_<function>_<scenario>_<expected>
def test_calculate_total_with_empty_list_returns_zero():
    result = calculate_total([])
    assert result == 0

def test_calculate_total_with_negative_values_raises_error():
    with pytest.raises(ValueError, match="negative"):
        calculate_total([-1, 2, 3])

# DON'T: Vague test names
def test_calculate():
    assert calculate_total([1,2,3]) == 6
```

### Test Organization
```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated tests
│   ├── test_models.py
│   └── test_utils.py
├── integration/         # Tests with real dependencies
│   ├── test_api.py
│   └── test_database.py
└── e2e/                 # End-to-end tests (optional)
    └── test_workflows.py
```

### Fixtures and conftest.py
```python
# conftest.py - Shared fixtures available to all tests
import pytest
from myapp.database import Database

@pytest.fixture
def sample_user():
    """Simple fixture returning test data."""
    return {"name": "Test User", "email": "test@example.com"}

@pytest.fixture
def db_session():
    """Fixture with setup and teardown."""
    db = Database(":memory:")
    db.create_tables()
    yield db  # Test runs here
    db.close()  # Cleanup after test

@pytest.fixture(scope="module")
def expensive_resource():
    """Module-scoped fixture (shared across tests in module)."""
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

### Mocking External Dependencies
```python
from unittest.mock import Mock, patch, MagicMock

# Mock a function
@patch("myapp.services.fetch_data")
def test_process_uses_fetched_data(mock_fetch):
    mock_fetch.return_value = {"key": "value"}
    result = process()
    mock_fetch.assert_called_once()
    assert result == "processed: value"

# Mock a class method
@patch.object(UserService, "get_user")
def test_handler_with_mocked_service(mock_get_user):
    mock_get_user.return_value = User(id=1, name="Test")
    response = handler(user_id=1)
    assert response.status == 200

# Mock context manager
def test_with_mocked_file():
    mock_file = MagicMock()
    mock_file.__enter__.return_value.read.return_value = "content"
    with patch("builtins.open", return_value=mock_file):
        result = read_config("config.json")
    assert result == "content"
```

### Parameterized Tests
```python
import pytest

@pytest.mark.parametrize("input_val,expected", [
    ([], 0),
    ([1], 1),
    ([1, 2, 3], 6),
    ([10, -5, 3], 8),
])
def test_calculate_total_various_inputs(input_val, expected):
    assert calculate_total(input_val) == expected

@pytest.mark.parametrize("invalid_input,error_msg", [
    (None, "cannot be None"),
    ("string", "must be a list"),
    ([1, "a"], "all elements must be numbers"),
])
def test_calculate_total_invalid_inputs(invalid_input, error_msg):
    with pytest.raises(ValueError, match=error_msg):
        calculate_total(invalid_input)
```

### Async Testing
```python
import pytest

@pytest.mark.asyncio
async def test_async_fetch():
    result = await fetch_data_async("https://api.example.com")
    assert result["status"] == "ok"

@pytest.fixture
async def async_client():
    async with AsyncClient(app) as client:
        yield client

@pytest.mark.asyncio
async def test_api_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Test Coverage Expectations
```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing

# Minimum expectations:
# - Unit tests: 80%+ coverage
# - Critical paths (auth, payments): 95%+ coverage
# - Happy path + error cases for all public APIs

```

### What Makes a Good Test
1. **Independent**: No test depends on another test's state
2. **Repeatable**: Same result every time, regardless of environment
3. **Fast**: Unit tests should run in milliseconds
4. **Focused**: Tests one behavior per test function
5. **Clear failure messages**: Easy to diagnose what broke

## File Architecture

### File Size Guidelines
- **Target**: 100-300 lines per file
- **Maximum**: 800 lines (hard limit - refactor if exceeded)
- **Rationale**: 2000-line files cost ~50x more tokens due to retry failures (35% success rate vs 85% for 200-line files)

### When to Split
- File has >3 classes
- File has >10 functions
- File responsibilities are unclear
- Imports section exceeds 30 lines

## Dependencies

### Core Python Tools
- `pytest` - Testing
- `black` - Code formatting
- `ruff` or `flake8` - Linting
- `mypy` - Type checking

### Common Libraries
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `requests` - HTTP client
- `pydantic` - Data validation

## Configuration

Use environment variables or config files:
```python
# config.py
import os
from pathlib import Path

class Config:
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
```

## Security Essentials

### Secrets — Never Hardcode
```python
# DO: Environment variables with python-dotenv
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ["API_KEY"]  # KeyError if missing = good

# DON'T: Hardcoded secrets, .get() with default for secrets
API_KEY = "sk-abc123"  # NEVER
API_KEY = os.getenv("API_KEY", "default")  # Silent failure
```

### Input Validation at Boundaries
```python
# Validate external input; trust internal code
from pathlib import Path

def read_user_file(user_path: str, allowed_dir: Path) -> str:
    resolved = Path(user_path).resolve()
    if not resolved.is_relative_to(allowed_dir):
        raise ValueError("Path traversal blocked")
    return resolved.read_text()
```

### SQL Safety
```python
# DO: Parameterized queries (ORM or raw)
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# DON'T: String interpolation in SQL
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # INJECTION
```

Run `bandit -r src/` for static security analysis. See `/security-audit` for comprehensive scanning.

## Modern Patterns (3.9+)

```python
# Protocol-based duck typing (structural subtyping)
from typing import Protocol

class Renderable(Protocol):
    def render(self) -> str: ...

def display(item: Renderable) -> None:  # Any object with .render() works
    print(item.render())

# Frozen dataclasses for immutable value objects
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Coordinate:
    lat: float
    lon: float
```

See `python-patterns` skill for comprehensive patterns reference.

## Key Conventions

1. Begin projects with clear problem definition
2. Create modular code with separation of concerns
3. Use configuration files for settings (not hardcoded values)
4. Implement proper logging and error handling
5. Write tests alongside implementation
6. Use version control with meaningful commits
