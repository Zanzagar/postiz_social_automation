Export instincts as a shareable file.

Usage:
- `/instinct-export` — Export all instincts to stdout
- `/instinct-export --output=instincts-export.yaml` — Export to file
- `/instinct-export --domain=workflow` — Filter by domain
- `/instinct-export --min-confidence=0.7` — Only high-confidence instincts
- `/instinct-export --scope project --output project-instincts.yaml` — Project scope only

Arguments: $ARGUMENTS

## Instructions

Run the instinct CLI export command:

```bash
python3 scripts/instinct-cli.py export $ARGUMENTS
```

Display the output to the user.

If exporting to a file, suggest sharing instructions:

```
Share this file with team members. They can import with:
  /instinct-import <exported-file>
```

## What This Does

1. Detect current project context
2. Load instincts by selected scope:
   - `project`: current project only
   - `global`: global only
   - `all`: project + global merged (default)
3. Apply filters (`--domain`, `--min-confidence`)
4. Write YAML-style export to file (or stdout if no output path provided)

## Output Format

Creates a YAML file:

```yaml
# Instincts Export
# Generated: 2025-01-22
# Source: personal
# Count: 12 instincts

---
id: prefer-functional-style
trigger: "when writing new functions"
confidence: 0.8
domain: code-style
source: session-observation
scope: project
---

# Prefer Functional Style

## Action
Use functional patterns over classes.
```

## Flags

- `--domain <name>`: Export only specified domain
- `--min-confidence <n>`: Minimum confidence threshold
- `--output <file>`: Output file path (prints to stdout when omitted)
- `--scope <project|global|all>`: Export scope (default: `all`)

## Domains

code-style, testing, git, debugging, workflow, architecture
