Show the status of all learned instincts using the instinct CLI.

## Instructions

Run the instinct CLI status command:

```bash
python3 scripts/instinct-cli.py status
```

Display the output to the user.

If the CLI is not available or fails, fall back to manually reading instinct files:

1. Read YAML frontmatter `.md` files from `.claude/instincts/personal/` and `.claude/instincts/inherited/`
2. Read JSON candidates from `.claude/instincts/candidates/`
3. Check `.claude/instincts/observations.jsonl` for observation count
4. Group instincts by domain and sort by confidence

### Status Mapping
- Confidence > 0.7 = "Active" (auto-applied)
- Confidence 0.3-0.7 = "Candidate" (needs reinforcement)
- Confidence < 0.3 = "Fading" (will be discarded)

### If No Instincts Exist

```
No instincts found.

Instincts are learned automatically via observation hooks (PreToolUse/PostToolUse).
Use /learn to manually extract patterns from the current session.

See .claude/instincts/README.md for details.
```
