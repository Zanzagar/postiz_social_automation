<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/authority-hierarchy.md -->
# Authority Hierarchy

When guidance from different sources conflicts, follow this precedence order:

## Precedence Order

1. **Rules** (`.claude/rules/*.md`) — Highest authority. Project-defined requirements.
2. **Instincts** (`.claude/instincts/*.json`) — Learned patterns. Supplementary suggestions.
3. **Defaults** — Built-in Claude behavior. Baseline when nothing else applies.

## Key Principles

- Instincts **supplement** rules — they never **override** them
- If an instinct contradicts a rule, follow the rule without hesitation
- Instincts are suggestions; rules are requirements
- When referencing instincts, say "also consider" not "must follow"
- Allow user override of instincts without friction

## Examples

| Conflict | Resolution |
|----------|------------|
| Rule: "commit frequently" vs Instinct: "batch commits" | Follow rule: commit frequently |
| Instinct: "use pytest-asyncio for async tests" (no conflicting rule) | Follow instinct |
| Rule: ">80% confidence threshold for code review" vs Instinct: "report all findings" | Follow rule: filter by confidence |
| User says "skip tests this time" vs Instinct: "always run tests" | Follow user (instincts are suggestions) |

## Integration with Continuous Learning

The continuous learning system (`.claude/instincts/`) automatically extracts patterns from your work. These instincts:

- Start as candidates (confidence 0.3–0.7)
- Become active when reinforced (confidence >0.7)
- Decay when unused (-0.05/week)
- Are always subordinate to explicit rules

See `.claude/instincts/README.md` for the full instinct system documentation.
