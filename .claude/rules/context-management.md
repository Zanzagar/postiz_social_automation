<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/context-management.md -->
# Context & Session Management

Effective context management is critical for Claude Code performance. Apply these patterns automatically.

## Thinking Modes

Claude Code supports different thinking depths via keywords. Use the appropriate mode for the task:

| Mode | Tokens | When to Use |
|------|--------|-------------|
| `think` | ~4,000 | Simple tasks, quick fixes, routine operations |
| `think hard` | ~8,000 | Moderate complexity, single-file changes |
| `think harder` | ~16,000 | Multi-file changes, architectural decisions |
| `ultrathink` | ~32,000 | Complex problems, deep analysis, novel solutions |

### Mode Selection Guidelines

**Use `think` (default) for:**
- Bug fixes with obvious solutions
- Adding simple functions
- Documentation updates
- Routine git operations

**Use `think hard` for:**
- Implementing defined features
- Code review of single files
- Debugging with clear symptoms
- Refactoring within a module

**Use `think harder` for:**
- Features touching multiple files
- Debugging with unclear root cause
- API design decisions
- Integration work

**Use `ultrathink` for:**
- Architectural planning
- Complex algorithm design
- Unfamiliar codebases (initial exploration)
- Multi-system integration
- Research synthesis

### Prompting for Thinking Modes

Include the mode in your prompt:
- "Think about how to fix this null check"
- "Think hard about the best data structure here"
- "Think harder about how these services should communicate"
- "Ultrathink about the overall architecture for this feature"

## Context Awareness and Session Management

### Understanding Your Context Budget

Claude Code's ~200k context window is NOT all available for work:

| Component | Tokens | Notes |
|-----------|--------|-------|
| MCP tool definitions | ~25-30k | Loaded at startup |
| Auto-loaded rules | ~5k | From `.claude/rules/` |
| Superpowers plugin | ~3-5k | Required for TDD |
| CLAUDE.md + base | ~5-10k | Project context |
| **Startup overhead** | **~40-50k** | Before any work |
| **Working context** | **~125-150k** | What's actually available |

### When Quality Degrades

Quality degradation is **gradual**, not a cliff. Watch for these symptoms:
- Forgetting earlier instructions
- Repeating previously rejected approaches
- Missing obvious connections between files
- Declining code quality
- Ignoring established patterns

### Fresh Session vs Auto-Compacting

Claude Code can auto-compact conversations when context fills up. Neither approach is universally better:

| Situation | Recommendation |
|-----------|----------------|
| Iterative refinement of same feature | Let it compact, continuity helps |
| Switching to unrelated task | Fresh session |
| Quality noticeably declining | Fresh session |
| Deep in complex debugging | Let it compact, context is valuable |
| After completing major milestone | Fresh session (clean slate) |
| Claude contradicting itself | Fresh session |

**The key principle:** Important context should live in files, not just conversation history.

If you've been writing decisions to CLAUDE.md, task notes to Task Master, and code to files, then a fresh session can reload what matters. If critical context only exists in conversation history, compacting or resetting will lose it.

### Prevention Strategies

1. **Persist important context**: Write decisions, architecture notes, and learnings to files
2. **Use Task Master**: Task descriptions survive sessions
3. **Spawn sub-agents**: Fresh context for isolated subtasks
4. **Monitor symptoms, not numbers**: Quality decline matters more than token counts
5. **Trust the tools**: Auto-compacting exists for a reason - don't preemptively reset

### When to Start Fresh

Start a fresh session when you observe **symptoms**, not arbitrary thresholds:

- Claude forgets or contradicts earlier decisions
- Quality of responses noticeably declines
- Switching to completely unrelated work
- After completing a major milestone (natural breakpoint)
- You've lost track of what Claude "knows"

**Don't reset preemptively** - if Claude is performing well, continue working regardless of token count.

## Token Optimization Settings

These settings reduce token consumption by 60-80%. Apply via `/settings optimized` or set individually as environment variables.

| Setting | Default | Optimized | Savings | Impact |
|---------|---------|-----------|---------|--------|
| `MAX_THINKING_TOKENS` | 31,999 | 10,000 | ~70% | Caps extended thinking — faster but shallower reasoning |
| `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE` | ~95% | 50% | N/A | Compacts earlier — preserves working room proactively |
| `CLAUDE_CODE_SUBAGENT_MODEL` | (inherits) | haiku | ~80% | Cheaper sub-agents for research/exploration tasks |
| Default model | opus | sonnet | ~60% | Maintains quality for typical development work |

### When to Compact (Decision Table)

Use this when deciding whether to trigger compaction or start fresh:

| Situation | Compact? | Rationale |
|-----------|----------|-----------|
| After research/exploration | YES | Exploration context no longer needed for implementation |
| Mid-implementation | NO | Preserves variable names, file paths, implementation state |
| After milestone completion | YES | Natural breakpoint, fresh slate for next feature |
| After debugging session | YES | Debug context is noise for the next task |
| Context usage >80% | CONSIDER | Preventive compaction before quality degrades |
| >50 tool calls + quality symptoms | CONSIDER | Proactive maintenance before degradation |

### What Survives Compaction

Understanding what persists helps you decide when compaction is safe.

**Always available (survives compaction):**
- CLAUDE.md, auto-loaded rules, and MCP tool definitions
- Git state and repository information
- Task Master tasks and current task context
- Files on disk (can be re-read)
- Session-persisted summaries (`.claude/sessions/`)

**Lost during compaction (must be re-established):**
- Intermediate reasoning and decision chains
- Previously read file contents (must re-read)
- Conversation flow and earlier exchanges
- In-progress variable names mentioned only in conversation
- Exploration findings not persisted to files

**Rule of thumb:** If context is important, persist it before compaction triggers. Use Task Master notes, `docs/decisions/`, code comments, or `.claude/work-log.md`.

### Monitoring Context Health

After approximately **50-75 tool invocations** in a single session, consider whether compaction would benefit your workflow. This is a rough heuristic, not a hard rule — quality symptoms matter more than counts.

If you notice symptoms from the quality degradation checklist (forgetting, contradicting, declining output) AND you're past 50 tool invocations, compaction or a fresh session is likely beneficial.

Setting `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE=50` makes automatic compaction proactive, reducing the need for manual monitoring. With this setting, context is compacted at 50% capacity instead of waiting until 95%.

## Session Management Best Practices

### Persist Context Appropriately

Don't rely on conversation history for important context—but don't bloat CLAUDE.md either.

**Where to persist different types of context:**

| Context Type | Location | Loaded |
|--------------|----------|--------|
| Project patterns, constraints | CLAUDE.md | Every session |
| Architectural decisions | `docs/decisions/*.md` | On demand |
| Current task learnings | Task Master subtask notes | When working task |
| Session discoveries | Update task description | With task |
| Session summaries | `.claude/sessions/` | Auto on SessionStart (via `session-init.sh`) |
| Pre-compaction state | `.claude/sessions/pre-compact-state.md` | Auto on SessionStart |
| Code rationale | Code comments | With file |

```
Good: Add stable project patterns to CLAUDE.md (sparingly)
Good: Create docs/decisions/YYYY-MM-DD-topic.md for ADRs
Good: Update Task Master task/subtask with learnings
Good: Put "why" comments in code

Bad: Dump session notes into CLAUDE.md (bloats startup)
Bad: Assume Claude remembers 30 messages ago
Bad: Reference "what we discussed earlier" without specifics
```

**CLAUDE.md should stay lean** - it's loaded every session. Use it for stable, long-term project context only.

### Use the Project Index

The project index hook (`.claude/hooks/project-index.sh`) maintains a lightweight JSON index of your codebase at `.claude/project-index.json`. This allows:

- Sub-agents to understand codebase structure without loading files
- Quick navigation to relevant code
- Reduced context consumption for exploration

Reference it when spawning sub-agents or exploring unfamiliar code.

### Sub-Agent Best Practices

Sub-agents (via Task tool) get fresh context windows. Use them for:

| Task Type | Use Sub-Agent? | Why |
|-----------|----------------|-----|
| Isolated research | Yes | Fresh context, focused scope |
| Code review | Yes | Independent perspective |
| Validation/testing | Yes (blind) | Unbiased verification |
| Multi-step implementation | Sometimes | Break at natural boundaries |
| Quick fixes | No | Overhead not worth it |

**Blind Validator Pattern**: For testing, spawn a separate agent that only sees test results, not the implementation. This prevents bias in verification.

## Token Budget Awareness

### What Consumes Context

| Source | Approximate Tokens | Notes |
|--------|-------------------|-------|
| MCP tool definitions | ~25-30k total | Loaded at session start |
| Auto-loaded rules | ~3-5k | From `.claude/rules/` |
| Superpowers plugin | ~3-5k | Required for TDD |
| CLAUDE.md | ~1-2k | Project instructions |
| Conversation history | Varies | Grows with each exchange |
| File reads | Varies | ~1 token per 4 characters |
| Context7 queries | 5-20k each | Use sparingly |

### Token-Conscious Habits

1. **Read selectively**: Use line limits when reading large files
2. **Summarize findings**: Don't paste entire files into responses
3. **Use project index**: Reference structure, not full content
4. **Tier documentation lookups**: Existing knowledge → WebFetch → Context7
5. **Clear completed context**: Start fresh after major milestones
6. **Follow the 10/80 rule**: Max 10 MCPs, 80 tools enabled (see `docs/MCP_SETUP.md`)

## Quick Reference

```
Context feeling sluggish?
├─► Quality actually declining? (forgetting, contradicting, poor output)
│   ├─ Yes, same task → Spawn sub-agent for fresh perspective
│   ├─ Yes, new task → Start fresh session
│   └─ No, just anxious → Continue, trust auto-compacting
│
├─► Switching task domains?
│   ├─ Related work → Continue
│   └─ Completely different → Fresh session (clean slate)
│
├─► Major milestone complete?
│   └─ Natural breakpoint → Good time for fresh session
│
└─► Complex task ahead?
    ├─ Well-defined? → think hard, proceed
    └─ Exploratory? → ultrathink, then decompose

Token optimization:
├─► Using default settings?
│   └─ Consider: /settings optimized for 60-80% cost reduction
│
├─► Should I compact now?
│   ├─ After research/debug/milestone → YES
│   ├─ Mid-implementation → NO
│   └─ >50 tool calls + quality symptoms → CONSIDER
│
└─► What survives compaction?
    ├─ Rules, CLAUDE.md, git state, Task Master → YES
    └─ Conversation history, read file contents → NO (re-read)

Key insight: If important context is in files (not just conversation),
fresh sessions can reload what matters. Use Task Master notes and
docs/decisions/ for session learnings—keep CLAUDE.md lean!
```
