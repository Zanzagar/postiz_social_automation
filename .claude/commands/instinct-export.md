Export instincts as a shareable JSON file.

Usage:
- `/instinct-export` — Export all instincts (candidates and active)
- `/instinct-export --active` — Export only active instincts (confidence > 0.7)
- `/instinct-export --category=coding-style` — Filter by category
- `/instinct-export --min-confidence=0.5` — Filter by minimum confidence

Arguments: $ARGUMENTS

## Instructions

1. Read all JSON files in `.claude/instincts/` (exclude `candidates/` subdirectory — those are raw auto-extractions, not curated instincts)
2. Apply filters if specified:
   - `--active`: only confidence > 0.7
   - `--category=X`: only matching category
   - `--min-confidence=N`: only confidence >= N
3. Combine into a single JSON array
4. Write to `.claude/instincts/export-YYYY-MM-DD.json`
5. Report results (include count per category and confidence range)

### Default Behavior (No Filters)
- Export **all curated** instincts (confidence > 0.3, which excludes noise)
- Strip `source_sessions` (personal context, not shareable)
- Include candidates (0.3-0.7) AND active (>0.7) instincts — the importer can filter further

### Output Format

```json
[
  {
    "pattern": "Use type hints on all public functions",
    "confidence": 0.85,
    "category": "coding-style",
    "last_reinforced": "2024-01-18"
  },
  {
    "pattern": "Run tests before commits",
    "confidence": 0.90,
    "category": "tool-usage",
    "last_reinforced": "2024-01-20"
  }
]
```

### Report

```
Exported 5 instincts to .claude/instincts/export-2024-01-20.json

Categories:
  coding-style: 2
  testing-strategy: 1
  tool-usage: 2

Share this file with team members. They can import with:
  /instinct-import .claude/instincts/export-2024-01-20.json
```
