---
name: python-patterns
description: Framework-agnostic Python idioms, type hints (3.9+ syntax), context managers, decorators, comprehensions, __slots__, async/await patterns, pyproject.toml configuration, dataclasses, pathlib
---
# Python Patterns Skill

## Type Hints (3.9+ Modern Syntax)

```python
# PREFER: Built-in generics (3.9+) — no imports needed
def process(items: list[str]) -> dict[str, int]: ...
def maybe(value: str | None) -> str: ...  # 3.10+ union syntax
def callback(fn: Callable[[int, str], bool]) -> None: ...

# AVOID: typing module imports (legacy)
# from typing import List, Dict, Optional, Union  # Don't do this in 3.9+
```

### Common Patterns
```python
from typing import TypeAlias, TypeVar, Protocol
from collections.abc import Iterator, Sequence

# Type alias for complex types
Coordinate: TypeAlias = tuple[float, float]
Grid: TypeAlias = list[list[float]]

# TypeVar for generics
T = TypeVar("T")
def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None

# Protocol for structural typing (duck typing with types)
class Predictor(Protocol):
    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...
    def predict(self, X: np.ndarray) -> np.ndarray: ...
```

## Dataclasses

```python
from dataclasses import dataclass, field

@dataclass
class VariogramResult:
    lags: list[float]
    semivariance: list[float]
    model: str = "spherical"
    parameters: dict[str, float] = field(default_factory=dict)

    @property
    def range(self) -> float:
        return self.parameters.get("range", 0.0)

# Frozen (immutable) dataclass
@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0

# Slots for memory efficiency (3.10+)
@dataclass(slots=True)
class SensorReading:
    timestamp: float
    value: float
    quality: int
```

## Context Managers

```python
from contextlib import contextmanager

# Class-based
class DatabaseConnection:
    def __enter__(self):
        self.conn = create_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        return False  # Don't suppress exceptions

# Generator-based (simpler)
@contextmanager
def temporary_crs(geodataframe, target_crs):
    """Temporarily reproject a GeoDataFrame, restore on exit."""
    original_crs = geodataframe.crs
    geodataframe = geodataframe.to_crs(target_crs)
    try:
        yield geodataframe
    finally:
        geodataframe = geodataframe.to_crs(original_crs)

# Usage
with temporary_crs(gdf, "EPSG:32617") as projected:
    distances = projected.geometry.distance(projected.geometry.iloc[0])
```

## Decorators

```python
import functools
import time

# Basic decorator with functools.wraps (ALWAYS use wraps)
def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper

# Decorator with arguments
def retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=3, delay=0.5)
def fetch_remote_data(url: str) -> dict: ...
```

## Comprehensions and Generators

```python
# List comprehension — when you need all results
squares = [x**2 for x in range(100)]

# Generator expression — when iterating once (memory efficient)
total = sum(x**2 for x in range(1_000_000))

# Dict comprehension
column_types = {col: df[col].dtype for col in df.columns}

# Set comprehension
unique_crs = {layer.crs for layer in layers if layer.crs is not None}

# Conditional comprehension
valid_points = [p for p in points if not np.isnan(p.value)]

# AVOID: Nested comprehensions beyond 2 levels — use a loop instead
# BAD: [[f(x,y) for x in xs] for y in ys if g(y)]
# GOOD: Use explicit loops for clarity
```

## Pathlib (Always Prefer Over os.path)

```python
from pathlib import Path

# Path construction
data_dir = Path("data") / "raw" / "boreholes"
output = Path.home() / "results" / "predictions.tif"

# Common operations
path.exists()
path.is_file()
path.is_dir()
path.suffix          # '.tif'
path.stem            # 'predictions'
path.parent          # Path('results')
path.mkdir(parents=True, exist_ok=True)

# Reading/writing
text = path.read_text(encoding="utf-8")
path.write_text(content, encoding="utf-8")
data = path.read_bytes()

# Globbing
csv_files = list(data_dir.glob("*.csv"))
all_tifs = list(data_dir.rglob("**/*.tif"))  # Recursive
```

## Async/Await Patterns

```python
import asyncio

# Basic async function
async def fetch_tile(session, url: str) -> bytes:
    async with session.get(url) as response:
        return await response.read()

# Concurrent execution
async def fetch_all_tiles(urls: list[str]) -> list[bytes]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_tile(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# Async context manager
class AsyncDatabasePool:
    async def __aenter__(self):
        self.pool = await asyncpg.create_pool(dsn)
        return self.pool

    async def __aexit__(self, *args):
        await self.pool.close()

# Async generator
async def stream_results(query):
    async with AsyncDatabasePool() as pool:
        async with pool.acquire() as conn:
            async for record in conn.cursor(query):
                yield record
```

## pyproject.toml Configuration

```toml
[project]
name = "my-geo-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24",
    "geopandas>=0.14",
    "rasterio>=1.3",
    "pykrige>=1.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
    "mypy",
]

[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "F", "I", "N", "UP", "B", "SIM"]

[tool.ruff.lint.isort]
known-first-party = ["my_geo_pipeline"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]
```

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Mutable default argument: `def f(x=[])` | Use `def f(x=None): x = x or []` |
| Bare `except:` | Catch specific: `except ValueError:` |
| `type(x) == str` | Use `isinstance(x, str)` |
| `if len(lst) == 0` | Use `if not lst` |
| String concatenation in loop | Use `"".join(parts)` |
| `import *` | Import specific names |
| Global mutable state | Pass as parameter or use dataclass |
| `os.path.join()` | Use `pathlib.Path` |
| Ignoring return values | Check or explicitly discard with `_ =` |

## __slots__ for Memory Optimization

```python
# Without __slots__: each instance has a __dict__ (~100+ bytes overhead)
class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# With __slots__: fixed attributes, no __dict__ (~40% less memory)
class Point:
    __slots__ = ("x", "y", "z")
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# Use when: creating many instances (1000+) of simple data objects
# Don't use when: need dynamic attributes or inheritance flexibility
```

## Enum for Constants

```python
from enum import Enum, auto

class VariogramModel(Enum):
    SPHERICAL = auto()
    EXPONENTIAL = auto()
    GAUSSIAN = auto()
    MATERN = auto()

# Usage
model = VariogramModel.SPHERICAL
if model == VariogramModel.SPHERICAL:
    ...

# String enum for serialization
class CRSType(str, Enum):
    GEOGRAPHIC = "geographic"
    PROJECTED = "projected"
    LOCAL = "local"
```
