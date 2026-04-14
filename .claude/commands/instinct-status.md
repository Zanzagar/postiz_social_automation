Show the status of all learned instincts using the instinct CLI.

## Instructions

Run the instinct CLI status command:

```bash
python3 scripts/instinct-cli.py status
```

Display the output to the user.

## What This Does

1. Detect current project context
2. Read project instincts from `.claude/instincts/personal/` and `.claude/instincts/inherited/`
3. Read global instincts (if any)
4. Merge with precedence rules (project overrides global when IDs collide)
5. Display grouped by domain with confidence bars and observation stats

## Output Format

```
============================================================
  INSTINCT STATUS - 12 total
============================================================

  Project instincts: 8
  Inherited instincts: 4

## WORKFLOW (3)
  ███████░░░  70%  grep-before-edit [project]
            trigger: when modifying code

## TESTING (2)
  █████████░  85%  validate-user-input [project]
            trigger: when handling user input

## SECURITY (2)
  ██████░░░░  60%  check-env-vars [inherited]
            trigger: when writing configuration
```

## Status Mapping

- Confidence > 0.7 = "Active" (auto-applied)
- Confidence 0.3-0.7 = "Candidate" (needs reinforcement)
- Confidence < 0.3 = "Fading" (will be discarded)

## If the CLI Is Not Available

Fall back to manually reading instinct files:

1. Read YAML frontmatter `.md` files from `.claude/instincts/personal/` and `.claude/instincts/inherited/`
2. Read JSON candidates from `.claude/instincts/candidates/`
3. Check `.claude/instincts/observations.jsonl` for observation count
4. Group instincts by domain and sort by confidence

## If No Instincts Exist

```
No instincts found.

Instincts are learned automatically via observation hooks (PreToolUse/PostToolUse).
Use /learn to manually extract patterns from the current session.

See .claude/instincts/README.md for details.
```
