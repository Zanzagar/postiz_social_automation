---
name: model-route
description: Get model tier recommendation for a task based on complexity and risk
arguments:
  - name: task
    description: Task description
    required: true
---

# Model Route

Analyze the task "$task" and recommend the appropriate model tier based on **capability requirements**, not cost.

## Routing Heuristics

| Model | Use For | Capability | Speed |
|-------|---------|------------|-------|
| **haiku** | Deterministic ops, formatting, simple transforms, status checks | Sufficient for mechanical tasks | Fastest |
| **sonnet** | Implementation, refactoring, code generation, moderate review | Strong for scoped work | Fast |
| **opus** | Architecture, deep review, ambiguous problems, complex debugging | Maximum reasoning depth | Slower |

## Decision Factors

Evaluate each factor and weight toward the appropriate tier:

1. **Complexity**: How many files/concepts are involved?
   - 1-2 files, single concept → haiku
   - 3-10 files, moderate logic → sonnet
   - 10+ files, architectural → opus

2. **Risk**: What happens if it goes wrong?
   - Easily reversible, no data impact → haiku
   - Moderate impact, tests catch issues → sonnet
   - Production risk, security-sensitive → opus

3. **Ambiguity**: How clear are the requirements?
   - Crystal clear, well-defined → haiku
   - Mostly clear, some design decisions → sonnet
   - Exploratory, open-ended, novel → opus

**Default to the highest-capability model when in doubt.** Never sacrifice reasoning depth for speed.

## Output Format

Provide your recommendation as:

```
Recommendation: [haiku | sonnet | opus]
Confidence: [high | medium | low]
Rationale: [1-2 sentence explanation]
Fallback: [next tier up if recommendation struggles]
```

## Sub-Agent Routing

When dispatching sub-agents via the Agent tool, match model to task complexity:

| Sub-Agent Task | Model | Why |
|----------------|-------|-----|
| Architecture planning, security review | opus | High-stakes, deep reasoning required |
| Code review, implementation, complex research | sonnet | Strong analysis for scoped work |
| File search, simple exploration, status checks | haiku | Sufficient for mechanical/deterministic tasks |
| Doc updates, formatting, simple transforms | haiku | Well-defined output, no ambiguity |
