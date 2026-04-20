Import instincts from a file or URL.

Usage: `/instinct-import <path-or-url>`

Arguments: $ARGUMENTS

## Instructions

Run the instinct CLI import command:

```bash
python3 scripts/instinct-cli.py import "$ARGUMENTS" --force
```

Display the output to the user.

If the CLI is not available, fall back to manual import:

1. Fetch the instinct file (local path or URL)
2. Parse and validate the format
3. Check for duplicates against `.claude/instincts/personal/` and `.claude/instincts/inherited/`
4. Write new instincts to `.claude/instincts/inherited/`
5. Report results

## Import Process

```
Importing instincts from: team-instincts.yaml
================================================

Found 12 instincts to import.

Analyzing conflicts...

## New Instincts (8)
These will be added:
  ✓ use-zod-validation (confidence: 0.7)
  ✓ prefer-named-exports (confidence: 0.65)
  ✓ test-async-functions (confidence: 0.8)
  ...

## Duplicate Instincts (3)
Already have similar instincts:
  ⚠️ prefer-functional-style
     Local: 0.8 confidence, 12 observations
     Import: 0.7 confidence
     → Keep local (higher confidence)

  ⚠️ test-first-workflow
     Local: 0.75 confidence
     Import: 0.9 confidence
     → Update to import (higher confidence)

Import 8 new, update 1?
```

## Merge Behavior

When importing an instinct with an existing ID:
- Higher-confidence import becomes an update candidate
- Equal/lower-confidence import is skipped
- User confirms unless `--force` is used

## Source Tracking

Imported instincts are marked with:
```yaml
source: inherited
scope: project
imported_from: "team-instincts.yaml"
```

## Flags

- `--dry-run`: Preview without importing
- `--force`: Skip confirmation prompt
- `--min-confidence <n>`: Only import instincts above threshold
- `--scope <project|global>`: Select target scope (default: `project`)

## Expected Instinct Format (YAML Frontmatter)

```markdown
---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.7
domain: "code-style"
source: "session-observation"
---

# Prefer Functional Style

## Action
Use functional patterns over classes when appropriate.

## Evidence
- Observed in multiple sessions
```

### Domains
code-style, testing, git, debugging, workflow, architecture
