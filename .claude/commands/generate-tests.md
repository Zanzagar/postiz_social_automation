Generate tests for the specified file, function, or module.

Usage:
- `/generate-tests src/module.py` - Generate tests for entire module
- `/generate-tests src/module.py::function_name` - Generate tests for specific function
- `/generate-tests src/api/` - Generate tests for directory

Arguments: $ARGUMENTS

Instructions:
1. Read the specified file(s) to understand the code
2. Identify functions, classes, and methods that need tests
3. Generate comprehensive pytest tests covering:
   - Happy path scenarios
   - Edge cases (empty inputs, None, boundaries)
   - Error conditions and exceptions
   - Type variations if applicable

Test file naming:
- For `src/module.py` → create `tests/test_module.py`
- For `src/api/routes.py` → create `tests/api/test_routes.py`

Test patterns to follow:
- Use `pytest` fixtures for setup/teardown
- Use `@pytest.mark.parametrize` for multiple inputs
- Mock external dependencies (databases, APIs, file system)
- Include docstrings explaining what each test verifies

Before writing tests:
1. Check if tests already exist for this code
2. If yes, add new tests to existing file
3. Follow existing test patterns in the project

After generating tests:
- Run `pytest <test_file> -v` to verify they pass
- Report coverage if `pytest-cov` is available
