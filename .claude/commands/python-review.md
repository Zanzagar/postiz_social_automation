---
description: Comprehensive Python code review for PEP 8 compliance, type hints, security, and Pythonic idioms. Invokes the python-reviewer agent.
---

# Python Code Review

This command invokes the **python-reviewer** agent for comprehensive Python-specific code review.

## What This Command Does

1. **Identify Python Changes**: Find modified `.py` files via `git diff`
2. **Run Static Analysis**: Execute `ruff`, `mypy`, `pylint`, `black --check`
3. **Security Scan**: Check for SQL injection, command injection, unsafe deserialization
4. **Type Safety Review**: Analyze type hints and mypy errors
5. **Pythonic Code Check**: Verify code follows PEP 8 and Python best practices
6. **Generate Report**: Categorize issues by severity

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | All uncommitted `.py` file changes |
| `staged` | Only staged `.py` changes |
| `<path>` | Specific file or directory |

## When to Use

Use `/python-review` when:
- After writing or modifying Python code
- Before committing Python changes
- Reviewing pull requests with Python code
- Onboarding to a new Python codebase
- Learning Pythonic patterns and idioms

## Review Categories

### CRITICAL (Must Fix)
- SQL/Command injection vulnerabilities
- Unsafe `eval()` / `exec()` usage
- `pickle` unsafe deserialization
- Hardcoded credentials
- `yaml.load()` without `Loader=SafeLoader`
- Bare `except:` clauses hiding errors

### HIGH (Should Fix)
- Missing type hints on public functions
- Mutable default arguments (`def f(x=[])`)
- Swallowing exceptions silently (`except: pass`)
- Not using context managers for resources
- C-style looping instead of comprehensions
- Using `type()` instead of `isinstance()`
- Race conditions without locks

### MEDIUM (Consider)
- PEP 8 formatting violations
- Missing docstrings on public functions
- `print()` statements instead of `logging`
- Inefficient string operations
- Magic numbers without named constants
- Not using f-strings for formatting
- Unnecessary list creation (use generators)

## Automated Checks Run

```bash
# Type checking
mypy .

# Linting and formatting
ruff check .
black --check .
isort --check-only .

# Security scanning
bandit -r .

# Dependency audit
pip-audit
safety check

# Testing
pytest --cov=app --cov-report=term-missing
```

## Example Usage

```text
User: /python-review

Agent:
# Python Code Review Report

## Files Reviewed
- app/routes/user.py (modified)
- app/services/auth.py (modified)

## Static Analysis Results
✓ ruff: No issues
✓ mypy: No errors
⚠️ black: 2 files need reformatting
✓ bandit: No security issues

## Issues Found

[CRITICAL] SQL Injection vulnerability
File: app/routes/user.py:42
Issue: User input directly interpolated into SQL query
```python
query = f"SELECT * FROM users WHERE id = {user_id}"  # Bad
```
Fix: Use parameterized query
```python
query = "SELECT * FROM users WHERE id = %s"  # Good
cursor.execute(query, (user_id,))
```

[HIGH] Mutable default argument
File: app/services/auth.py:18
Issue: Mutable default argument causes shared state
```python
def process_items(items=[]):  # Bad
    items.append("new")
    return items
```
Fix: Use None as default
```python
def process_items(items=None):  # Good
    if items is None:
        items = []
    items.append("new")
    return items
```

[MEDIUM] Missing type hints
File: app/services/auth.py:25
Issue: Public function without type annotations
```python
def get_user(user_id):  # Bad
    return db.find(user_id)
```
Fix: Add type hints
```python
def get_user(user_id: str) -> Optional[User]:  # Good
    return db.find(user_id)
```

## Summary
- CRITICAL: 1
- HIGH: 1
- MEDIUM: 2

Recommendation: Block merge until CRITICAL issue is fixed
```

## Approval Criteria

| Status | Condition |
|--------|-----------|
| **APPROVE** | No CRITICAL or HIGH issues |
| **WARNING** | Only MEDIUM issues (merge with caution) |
| **BLOCK** | CRITICAL or HIGH issues found |

## Framework-Specific Reviews

### Django Projects
- N+1 query issues (use `select_related` / `prefetch_related`)
- Missing migrations for model changes
- Raw SQL when ORM would work
- Missing `transaction.atomic()` for multi-step operations

### FastAPI Projects
- CORS misconfiguration
- Pydantic models for request validation
- Response models correctness
- Proper async/await usage
- Dependency injection patterns

### Flask Projects
- Context management (app context, request context)
- Proper error handling
- Blueprint organization
- Configuration management

## Common Fixes

### Add Type Hints
```python
# Before
def calculate(x, y):
    return x + y

# After
from typing import Union

def calculate(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    return x + y
```

### Use Context Managers
```python
# Before
f = open("file.txt")
data = f.read()
f.close()

# After
with open("file.txt") as f:
    data = f.read()
```

### Fix Mutable Defaults
```python
# Before
def append(value, items=[]):
    items.append(value)
    return items

# After
def append(value, items=None):
    if items is None:
        items = []
    items.append(value)
    return items
```

### Use List Comprehensions
```python
# Before
result = []
for item in items:
    if item.is_valid():
        result.append(item.value)

# After
result = [item.value for item in items if item.is_valid()]
```

### Use f-strings (Python 3.6+)
```python
# Before
greeting = "Hello, " + name + "!"

# After
greeting = f"Hello, {name}!"
```

### Fix String Concatenation in Loops
```python
# Before
result = ""
for word in words:
    result += word + " "

# After
result = " ".join(words)
```

## Python Version Compatibility

| Feature | Minimum Python |
|---------|----------------|
| Type hints | 3.5+ |
| f-strings | 3.6+ |
| Walrus operator (`:=`) | 3.8+ |
| Position-only parameters | 3.8+ |
| Match statements | 3.10+ |
| Type unions (`x | None`) | 3.10+ |

## Integration

- Use `/tdd` first to ensure tests pass
- Use `/python-review` before committing
- Use `/code-review` for language-agnostic concerns
- Use `/build-fix` if static analysis tools fail

## Agent

Invokes the **python-reviewer** agent (sonnet, read-only).
