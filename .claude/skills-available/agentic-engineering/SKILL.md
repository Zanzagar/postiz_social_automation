---
name: agentic-engineering
description: Eval-first development patterns for AI-assisted coding — task decomposition, model routing, cost discipline, and session strategy
---

# Agentic Engineering

Patterns for effective AI-assisted development. Apply these when working with Claude Code or dispatching sub-agents.

## Eval-First Loop

Every implementation should be driven by evaluable criteria:

1. **Define Criteria**: What does success look like? Measurable outcomes, not vibes.
2. **Baseline**: Run the current implementation against criteria (or note "no implementation yet")
3. **Implement**: Make changes
4. **Re-eval**: Run against the same criteria
5. **Compare**: Did we improve? Regress? Side-effect somewhere?

```
define_criteria() → baseline() → implement() → re_eval() → compare()
                                                    ↑           │
                                                    └───────────┘  (iterate until passing)
```

**Anti-pattern**: Implementing first, then writing criteria that match what you built.

## 15-Minute Task Decomposition

Every task should be completable in ~15 minutes. If not, decompose until each piece is:

- **Independently verifiable**: Can be tested in isolation
- **Single risk**: One thing that could go wrong, not five
- **Clear done condition**: Binary pass/fail, not "looks about right"

### Decomposition Heuristic

| Signal | Action |
|--------|--------|
| Task touches 3+ files | Split by file or module |
| Task has AND in description | Split at each AND |
| Task requires research + implementation | Split into research task + implementation task |
| Task is "build X" | Split into interface + implementation + integration |

## Model Routing by Tier

| Tier | Model | Use For | Cost |
|------|-------|---------|------|
| 1 | haiku | Deterministic ops, formatting, grep, status checks | ~$0.80/M in |
| 2 | sonnet | Implementation, refactoring, code review, moderate analysis | ~$3/M in |
| 3 | opus | Architecture, deep review, ambiguous problems, novel solutions | ~$15/M in |

### Escalation Rules

- Start with the lowest appropriate tier
- Escalate on: repeated failures, increasing complexity, user request
- Never downgrade mid-task (context loss outweighs savings)
- Sub-agents default to sonnet; override with `model: "haiku"` or `model: "opus"`

### Sub-Agent Model Selection

| Sub-Agent Task | Model | Rationale |
|----------------|-------|-----------|
| File search, grep, exploration | haiku | Mechanical, no judgment needed |
| Code implementation | sonnet | Balanced quality/cost |
| Code review, security review | sonnet or opus | Judgment-heavy |
| Architecture planning | opus | Highest reasoning needed |
| Documentation updates | haiku | Templated, low risk |

## Cost Discipline

Track per-task when optimizing:

- Model used and why
- Approximate tokens consumed (check `cost-log.jsonl`)
- Retry count (each retry = wasted tokens)
- Success/failure outcome

**The cheapest token is the one you don't send.** Reduce context by:
- Reading specific line ranges, not entire files
- Using project index instead of broad exploration
- Spawning sub-agents for isolated research (fresh context)

## Session Strategy

| Situation | Recommendation |
|-----------|---------------|
| Coupled units of work (same feature) | Continue session |
| Phase transition (planning → building) | Fresh session |
| After completing a milestone | Compact or fresh session |
| Context quality degrading | Fresh session immediately |
| Starting independent task | Fresh session |

See `.claude/rules/context-management.md` for detailed session management guidance.
