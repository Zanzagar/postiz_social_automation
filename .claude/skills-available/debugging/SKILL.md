---
name: debugging
description: Systematic debugging workflow for Python applications. Use when user reports bugs, errors, unexpected behavior, or needs help troubleshooting.
---

# Debugging Skill

## When to Use
- User reports a bug or error
- Something "isn't working"
- Unexpected behavior
- Test failures
- Performance issues

## Debugging Workflow

### Step 1: Reproduce
- Get exact steps to reproduce
- Get the full error message/traceback
- Identify: Does it happen every time? Only with certain inputs?

### Step 2: Isolate
- Find the smallest code that reproduces the issue
- Check recent changes (`git diff`, `git log`)
- Binary search: comment out code to narrow down

### Step 3: Understand
- Read the error message carefully (line numbers, exception type)
- Check the values of variables at the failure point
- Trace the data flow

### Step 4: Fix
- Make ONE change at a time
- Verify the fix actually works
- Check for similar issues elsewhere
- Add a test to prevent regression

## Python Debugging Tools

### Quick Debug
```python
# Print debugging (simple but effective)
print(f"DEBUG: {variable=}")

# Breakpoint (Python 3.7+)
breakpoint()  # Drops into pdb
```

### Using pdb
```python
import pdb; pdb.set_trace()

# Commands:
# n - next line
# s - step into function
# c - continue
# p variable - print variable
# l - show code context
# q - quit
```

### Logging (Better than print)
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Processing {item}")
logger.error(f"Failed: {error}", exc_info=True)
```

## Common Python Issues

### Import Errors
- Check PYTHONPATH
- Check virtual environment is activated
- Check for circular imports

### Type Errors
- Check `None` values
- Check data types (str vs int vs bytes)
- Use `type()` and `isinstance()` to verify

### Attribute Errors
- Object might be `None`
- Check spelling
- Check if attribute exists with `hasattr()`

### Index/Key Errors
- Check bounds and lengths
- Check if key exists with `.get()` or `in`
- Off-by-one errors

## Questions to Ask
1. What did you expect to happen?
2. What actually happened?
3. What's the full error message?
4. What changed recently?
5. Does it work in a simpler case?
