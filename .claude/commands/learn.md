Extract reusable patterns from the current session and save as skills or instincts.

Usage: `/learn`

Arguments: $ARGUMENTS

## What to Extract

Look for patterns worth saving from the current session:

### 1. Error Resolution Patterns
- What error occurred?
- What was the root cause?
- What fixed it?
- Is this reusable for similar errors?

### 2. Debugging Techniques
- Non-obvious debugging steps
- Tool combinations that worked
- Diagnostic patterns

### 3. Workarounds
- Library quirks
- API limitations
- Version-specific fixes

### 4. Project-Specific Patterns
- Codebase conventions discovered
- Architecture decisions made
- Integration patterns

## Process

1. Review the current session for extractable patterns
2. Identify the most valuable/reusable insight
3. Decide: **instinct** (lightweight, auto-decays) or **skill** (permanent reference)
4. Draft the content
5. Ask user to confirm before saving

## Output: Instinct (Lightweight Pattern)

Save to `.claude/instincts/`:

```json
{
  "pattern": "descriptive-name",
  "trigger": "When [specific condition]",
  "action": "Do [specific action]",
  "confidence": 0.5,
  "source": "session",
  "created": "2026-02-13"
}
```

Instincts start at confidence 0.5 (candidate), grow to >0.7 (active) when reinforced, decay when unused.

## Output: Skill (Permanent Reference)

Save to `.claude/skills/learned/<pattern-name>/SKILL.md`:

```markdown
---
name: <pattern-name>
description: <when to activate this skill>
---

# [Descriptive Pattern Name]

**Extracted:** [Date]
**Context:** [When this applies]

## Problem
[What problem this solves]

## Solution
[The pattern/technique/workaround]

## Example
[Code example if applicable]

## When to Use
[Trigger conditions]
```

## What NOT to Extract

- Trivial fixes (typos, simple syntax errors)
- One-time issues (specific API outages)
- Session-specific context
- Patterns already captured in existing skills or rules

## Integration

- Extracted instincts participate in authority hierarchy (Rules > Instincts > Defaults)
- Use `/instinct-status` to view learned patterns
- Use `/evolve` to cluster instincts into skills
- Use `/skill-create` for git-history-based extraction
