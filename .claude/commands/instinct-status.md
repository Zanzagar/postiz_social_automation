Show the status of all learned instincts.

## Instructions

Read all JSON files in `.claude/instincts/` and display them grouped by category.

### Output Format

```
╔══════════════════════════════════════════════════════════╗
║                    INSTINCT STATUS                       ║
╠══════════════════════════════════════════════════════════╣

Category: coding-style
┌─────────────────────────────────────┬────────┬──────────┐
│ Pattern                             │ Score  │ Status   │
├─────────────────────────────────────┼────────┼──────────┤
│ Use snake_case for Python functions │ 0.85   │ Active   │
│ Prefer f-strings over .format()    │ 0.45   │ Candidate│
└─────────────────────────────────────┴────────┴──────────┘

Category: testing-strategy
┌─────────────────────────────────────┬────────┬──────────┐
│ Always test edge cases first        │ 0.72   │ Active   │
└─────────────────────────────────────┴────────┴──────────┘

Summary:
- Active (>0.7): 2 instincts
- Candidate (0.3-0.7): 1 instinct
- Total: 3 instincts across 2 categories
```

### Status Mapping
- Score > 0.7 → "Active" (auto-applied)
- Score 0.3–0.7 → "Candidate" (needs reinforcement)
- Score < 0.3 → "Fading" (will be discarded)

### If No Instincts Exist
```
No instincts found in .claude/instincts/

Instincts are learned automatically as you work. They capture recurring
patterns in your coding style, testing strategy, and tool usage.

See .claude/instincts/README.md for details.
```
