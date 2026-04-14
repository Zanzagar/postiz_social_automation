<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/authority-hierarchy.md -->
# Authority Hierarchy

When guidance from different sources conflicts, follow this precedence order:

## Precedence Order

1. **Rules** (`.claude/rules/*.md`) — Highest authority. Project-defined requirements.
2. **Superpowers Enforcement** (when plugin installed) — Hard workflow enforcement. Deletes code without tests.
3. **Instincts** (`.claude/instincts/*.json`) — Learned patterns. Supplementary suggestions.
4. **Defaults** — Built-in Claude behavior. Baseline when nothing else applies.

## Key Principles

- Instincts **supplement** rules — they never **override** them
- If an instinct contradicts a rule, follow the rule without hesitation
- Instincts are suggestions; rules are requirements
- When referencing instincts, say "also consider" not "must follow"
- Allow user override of instincts without friction

## Superpowers Authority

When the Superpowers plugin is installed and active, its enforcement mechanisms are **hard constraints, subordinate only to explicit project rules**:

- **TDD enforcement** — deletes production code written without failing tests first
- **Debugging discipline** — systematic-debugging workflow required for bugs
- **Verification requirements** — evidence before completion claims

Superpowers is intentionally strict. Its enforcement exists to prevent quality shortcuts that feel productive in the moment but create problems later.

**When Superpowers is NOT installed:**
TDD becomes advisory (instinct-level), not enforced. The template will suggest TDD but cannot delete code or block implementation. All other normative rules from `workflow-enforcement.md` still apply.

## User Override Behavior

| Level | Override Behavior |
|-------|-------------------|
| Rules | Cannot be overridden. |
| Superpowers | Requires explicit acknowledgment: "I understand this skips TDD, proceed anyway." |
| Instincts | Can be overridden freely. |
| Defaults | Can be overridden freely. |

Overriding Superpowers is allowed but requires the user to consciously acknowledge they are bypassing quality gates. This prevents accidental skipping while preserving user agency.

## Examples

| Conflict | Resolution |
|----------|------------|
| Rule: "commit frequently" vs Instinct: "batch commits" | Follow rule: commit frequently |
| Instinct: "use pytest-asyncio for async tests" (no conflicting rule) | Follow instinct |
| Rule: ">80% confidence threshold for code review" vs Instinct: "report all findings" | Follow rule: filter by confidence |
| User says "skip tests this time" vs Instinct: "always run tests" | Follow user (instincts are suggestions) |
| Superpowers: "delete code without tests" vs User: "skip tests this once" | User must explicitly acknowledge the override |
| Superpowers not installed + Instinct: "use TDD" | Follow instinct (advisory, not enforced) |
| Rule: "commit frequently" vs Superpowers: "verify before commit" | Both apply: verify first, then commit |

## Integration with Continuous Learning

The continuous learning system (`.claude/instincts/`) automatically extracts patterns from your work. These instincts:

- Start as candidates (confidence 0.3–0.7)
- Become active when reinforced (confidence >0.7)
- Decay when unused (-0.05/week)
- Are always subordinate to explicit rules

See `.claude/instincts/README.md` for the full instinct system documentation.
