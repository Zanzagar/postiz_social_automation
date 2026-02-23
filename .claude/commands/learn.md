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

Save to `.claude/instincts/personal/<pattern-id>.md` using YAML frontmatter markdown:

```markdown
---
id: descriptive-pattern-id
trigger: "When [specific condition]"
confidence: 0.5
domain: "workflow"
source: "manual-learn"
---

# Descriptive Pattern Name

## Action
[What to do when the trigger condition is met]

## Evidence
- Extracted from session on [date]
- Context: [what was happening when the pattern was observed]
```

### Domains
`code-style`, `testing`, `debugging`, `workflow`, `architecture`, `git`

### Confidence
Instincts start at 0.5 (candidate), grow to >0.7 (active) when reinforced, decay when unused (-0.02/week).

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
- Use `/instinct-status` to view all learned patterns and their confidence
- Use `/evolve` to cluster related instincts into skills/commands/agents
- Use `/instinct-export` to share instincts with teammates
- Use `/skill-create` for git-history-based extraction

## How /learn Fits Into the Learning System

```
Automatic paths (no user action needed):
  observe.sh hooks → observations.jsonl → observer daemon → instincts/personal/
  pattern-extraction.sh → candidates/ (from git commit history)

Manual path (this command):
  /learn → user reviews session → creates instinct in personal/
```

`/learn` is for capturing insights the automatic paths might miss — especially
debugging discoveries, workarounds, and project-specific conventions that aren't
visible in tool usage patterns alone.
