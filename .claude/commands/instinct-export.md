Export instincts as a shareable file.

Usage:
- `/instinct-export` — Export all instincts to stdout
- `/instinct-export --output=instincts-export.yaml` — Export to file
- `/instinct-export --domain=workflow` — Filter by domain
- `/instinct-export --min-confidence=0.7` — Only high-confidence instincts

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

### Domains
code-style, testing, git, debugging, workflow, architecture
