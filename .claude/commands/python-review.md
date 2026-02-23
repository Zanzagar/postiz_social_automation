Comprehensive Python code review for PEP 8, type hints, security, and Pythonic idioms.

Usage: `/python-review [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | All uncommitted `.py` file changes |
| `staged` | Only staged `.py` changes |
| `<path>` | Specific file or directory |

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
- Using `type()` instead of `isinstance()`
- Race conditions without locks

### MEDIUM (Consider)
- PEP 8 formatting violations
- Missing docstrings on public functions
- `print()` statements instead of `logging`
- Magic numbers without named constants
- Not using f-strings for formatting
- Unnecessary list creation (use generators)

## Automated Checks

```bash
ruff check .                   # Linting
mypy .                         # Type checking
black --check .                # Formatting
bandit -r .                    # Security scanning
pip-audit                      # Dependency vulnerabilities
pytest --cov=src               # Test coverage
```

## Framework-Specific Reviews

### Django Projects
- N+1 query issues (use `select_related` / `prefetch_related`)
- Missing migrations for model changes
- Raw SQL when ORM would work
- Missing `transaction.atomic()` for multi-step operations

### FastAPI Projects
- CORS misconfiguration
- Pydantic models for request validation
- Proper async/await usage
- Dependency injection patterns

## Approval Criteria

| Status | Condition |
|--------|-----------|
| **APPROVE** | No CRITICAL or HIGH issues |
| **WARNING** | Only MEDIUM issues |
| **BLOCK** | CRITICAL or HIGH issues found |

## Integration

- Use `/tdd` first to ensure tests pass
- Use `/python-review` before committing
- Use `/code-review` for language-agnostic concerns

## Agent

Invokes the **python-reviewer** agent (sonnet, read-only).
