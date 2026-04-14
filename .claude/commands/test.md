---
description: Run the project test suite and report results
allowed-tools: Bash, Read, Glob
---

# Test

Run the project's test suite. Detect which test framework is available and run it.

## Workflow

1. **Detect test framework** by checking project files:

```bash
# Check for test frameworks
command -v pytest &>/dev/null && echo "pytest: available" || echo "pytest: not found"
[ -f "package.json" ] && grep -q '"test"' package.json && echo "npm test: available"
command -v go &>/dev/null && [ -f "go.mod" ] && echo "go test: available"
```

2. **Detect test directories**:
```bash
ls -d tests/ test/ spec/ *_test.go 2>/dev/null
```

3. **Run tests** based on detected framework:

For Python:
```bash
pytest -q
```

For Python with verbose output (if `$ARGUMENTS` contains "verbose" or "-v"):
```bash
pytest -v
```

For Python with specific file/pattern (if `$ARGUMENTS` is a path or pattern):
```bash
pytest $ARGUMENTS
```

4. **Report results**:
   - **All passed**: Confirm pass count
   - **Failures**: Show each failing test with:
     - Test name and file location
     - Brief error description
     - Suggest investigation starting point
   - **No tests found**: Note this and suggest creating tests with `/generate-tests`
   - **Framework not installed**: Suggest installation command

## Arguments

- `/test` — Run full test suite (quiet mode)
- `/test verbose` — Run with verbose output
- `/test <path>` — Run specific test file or directory
- `/test <pattern>` — Run tests matching pattern (e.g., `/test test_auth`)
