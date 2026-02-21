<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/reasoning-patterns.md -->
# Reasoning & Quality Patterns

These patterns improve output quality through structured thinking. Apply them automatically.

## Clarification Before Assumption

**When requirements are vague, ASK rather than assume.**

Before starting work on ambiguous requests:
1. Identify what's unclear (scope, approach, constraints)
2. List 2-3 specific clarifying questions
3. Wait for answers before proceeding

**Trigger phrases requiring clarification:**
- "Make it better" → Better how? Performance? Readability? UX?
- "Fix the bug" → Which bug? What's the expected behavior?
- "Add a feature" → What exactly should it do? Who uses it?
- "Improve this" → What metric defines improvement?

**Format:**
> Before I proceed, I need to clarify:
> 1. [Specific question about scope/approach]
> 2. [Specific question about constraints/preferences]

## Brainstorming Before Building

**For non-trivial features, brainstorm approaches first.**

When facing implementation decisions:
1. Generate 2-3 distinct approaches
2. List pros/cons for each
3. Recommend one with reasoning
4. Get user confirmation before coding

**Apply when:**
- Multiple valid architectures exist
- Trade-offs between simplicity/flexibility
- New feature with unclear best practice
- Performance vs maintainability decisions

## Reflection Before Completion

**Review work before declaring done.**

After completing significant work, pause and verify:

```
## Pre-Completion Checklist
- [ ] Does this actually solve the stated problem?
- [ ] Did I miss any edge cases mentioned in requirements?
- [ ] Are there obvious improvements I should mention?
- [ ] Would I be comfortable if someone else reviewed this?
```

**Self-review questions:**
1. "If I were the user, would this answer satisfy me?"
2. "What's the weakest part of this solution?"
3. "What would a senior engineer critique?"

## Five Whys for Debugging

**Trace problems to root cause, not symptoms.**

When debugging:
1. **Why** did this fail? → [immediate cause]
2. **Why** did that happen? → [deeper cause]
3. **Why** was that possible? → [systemic cause]
4. **Why** wasn't this caught? → [process gap]
5. **Why** does this gap exist? → [root cause]

Stop when you reach something actionable. Fix the root cause, not just the symptom.

## First Principles for Complex Problems

**Break down complex problems to fundamentals.**

When stuck or facing novel challenges:

1. **What do we know for certain?** (facts, constraints)
2. **What are we assuming?** (challenge each assumption)
3. **What's the simplest version?** (minimum viable solution)
4. **What would we do differently with no legacy?** (ideal state)
5. **What's the path from here to there?** (incremental steps)

## Research Before Recommending

**Don't guess at library APIs or best practices.**

When recommending technologies or approaches:
1. Check if you confidently know the answer (common patterns, stable APIs)
2. For simple lookups, use WebFetch to official docs (lightweight)
3. For complex queries or code examples, use Context7 (heavy - use sparingly)
4. Cite sources for recommendations

### Documentation Lookup Tiers (Token-Conscious)

**Tier 1 - Use existing knowledge** (0 extra tokens):
- Standard library functions (Python, JS, etc.)
- Well-known frameworks with stable APIs
- Common patterns you're confident about

**Tier 2 - WebFetch** (lightweight, ~500-2k tokens):
```
Use for: Simple API questions, single function lookups
Example: WebFetch to docs.python.org for pathlib usage
```

**Tier 2.5 - llms.txt** (lightweight, ~1-5k tokens):
```
Use for: Comprehensive library docs when available
Check: WebFetch <docs-site>/llms.txt (many sites expose this)
Example: https://www.helius.dev/docs/llms.txt
Advantage: LLM-optimized format, more complete than single-page
           WebFetch, cheaper than Context7
```

**Tier 3 - Context7** (heavy, ~5-20k tokens per query):
```
Reserve for:
- Complex multi-part queries needing code examples
- Unfamiliar or rapidly-changing libraries
- When Tier 1-2.5 failed to answer
```

**Never say:** "I think the API works like..."
**Instead:** "According to the documentation..." or "Let me check the current docs."

### Why This Matters
Context7 queries inject 5-20k tokens into your context each time. Multiple queries compound quickly, eating into your working context. Use the lightest option that works.
