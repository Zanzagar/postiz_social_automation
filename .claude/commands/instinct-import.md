Import instincts from a shared JSON file.

Usage: `/instinct-import <path-to-file>`

Arguments: $ARGUMENTS

## Instructions

1. Read the JSON file at the specified path
2. Validate each instinct has required fields: pattern, confidence, category
3. For each instinct:
   - If an instinct with the same pattern already exists: keep the one with higher confidence
   - If new: add to `.claude/instincts/` directory
4. Report results

### Validation Rules
- `pattern`: non-empty string
- `confidence`: number between 0.0 and 1.0
- `category`: one of: coding-style, testing-strategy, debugging-approach, architecture-preference, tool-usage
- `source_sessions`: array of strings (optional)
- `active`: boolean (optional, defaults to confidence > 0.7)

### Expected File Format

Single instinct:
```json
{
  "pattern": "...",
  "confidence": 0.8,
  "category": "coding-style"
}
```

Multiple instincts:
```json
[
  {"pattern": "...", "confidence": 0.8, "category": "coding-style"},
  {"pattern": "...", "confidence": 0.6, "category": "testing-strategy"}
]
```

### Output

```
Imported 3 instincts:
  + "Use type hints on all public functions" (0.85, coding-style) — NEW
  ↑ "Run tests before commits" (0.90 → kept, was 0.85) — UPDATED
  = "Prefer composition over inheritance" (0.72, skipped — existing 0.80 is higher)
```
