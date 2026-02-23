Analyze instincts for clustering opportunities and suggest new skills.

Usage: `/evolve`

## Instructions

Run the instinct CLI evolve command:

```bash
python3 scripts/instinct-cli.py evolve
```

Display the output. If the user wants to generate the evolved structures, run:

```bash
python3 scripts/instinct-cli.py evolve --generate
```

### What Evolution Does

1. Groups instincts by domain
2. Finds clusters of 2+ related instincts (similar triggers)
3. Proposes new skills, commands, or agents from clusters
4. On `--generate`: writes evolved structures to `.claude/instincts/evolved/`

### Evolution Targets

| Source | Target | Criteria |
|--------|--------|----------|
| 2+ related instincts | Skill | Similar triggers, any confidence |
| Workflow instinct (>=70%) | Command | High-confidence workflow patterns |
| 3+ instincts (>=75% avg) | Agent | Complex multi-step patterns |

### If Not Enough Instincts

```
Need at least 3 instincts to analyze patterns.
Currently have: N

To build up instincts:
  - Use /learn to extract patterns from sessions
  - The observer agent creates instincts automatically
  - Import shared instincts with /instinct-import
```
