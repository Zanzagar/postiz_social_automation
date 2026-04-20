Safely identify and remove dead code with test verification at every step.

Usage: `/refactor-clean [scope]`

Arguments: $ARGUMENTS

## Scope Options

| Scope | Behavior |
|-------|----------|
| (default) | Entire project |
| `<path>` | Specific file or directory |

## Step 1: Detect Dead Code

Run analysis tools based on project type:

| Tool | What It Finds | Command |
|------|--------------|---------|
| knip | Unused exports, files, dependencies | `npx knip` |
| depcheck | Unused npm dependencies | `npx depcheck` |
| ts-prune | Unused TypeScript exports | `npx ts-prune` |
| vulture | Unused Python code | `vulture src/` |
| deadcode | Unused Go code | `deadcode ./...` |
| cargo-udeps | Unused Rust dependencies | `cargo +nightly udeps` |

If no tool is available, use Grep to find exports with zero imports.

## Step 2: Categorize Findings

| Tier | Examples | Action |
|------|----------|--------|
| **SAFE** | Unused utilities, test helpers, internal functions | Delete with confidence |
| **CAUTION** | Components, API routes, middleware | Verify no dynamic imports or external consumers |
| **DANGER** | Config files, entry points, type definitions | Investigate before touching |

## Step 3: Safe Deletion Loop

For each SAFE item:

1. **Run full test suite** - Establish baseline (all green)
2. **Delete the dead code** - Surgical removal
3. **Re-run test suite** - Verify nothing broke
4. **If tests fail** - Immediately revert with `git checkout -- <file>` and skip
5. **If tests pass** - Move to next item

## Step 4: Handle CAUTION Items

Before deleting:
- Search for dynamic imports: `import()`, `require()`, `__import__`
- Search for string references: route names, component names in configs
- Check if exported from a public package API
- Verify no external consumers

## Step 5: Consolidate Duplicates

After removing dead code, look for:
- Near-duplicate functions (>80% similar) - merge into one
- Redundant type definitions - consolidate
- Wrapper functions that add no value - inline
- Re-exports that serve no purpose - remove indirection

## Step 6: Summary

```
Dead Code Cleanup
------------------
Deleted:   12 unused functions
            3 unused files
            5 unused dependencies
Skipped:    2 items (tests failed)
Saved:     ~450 lines removed
------------------
All tests passing
```

## Rules

- **Never delete without running tests first**
- **One deletion at a time** - Atomic changes make rollback easy
- **Skip if uncertain** - Better to keep dead code than break production
- **Don't refactor while cleaning** - Separate concerns

## Integration

- Use after `/code-review` identifies dead code
- Part of `/orchestrate refactor` pipeline
- Follow with `/test` to verify everything still passes

## Agent

Invokes the **refactor-cleaner** agent (sonnet, write access).
