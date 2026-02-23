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

1. Read the source file (YAML frontmatter markdown format or JSON)
2. Parse instincts with fields: id, trigger, confidence, domain
3. Check for duplicates against `.claude/instincts/personal/` and `.claude/instincts/inherited/`
4. Write new instincts to `.claude/instincts/inherited/`
5. Report results

### Expected Instinct Format (YAML Frontmatter)

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
