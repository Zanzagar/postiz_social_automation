<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/workflow-guide.md -->
# Project Workflow Guide

This rule helps orchestrate the right tools at the right time. Apply automatically based on context.

## Commitment Checkpoints

**Before starting significant work, explicitly state your assessment:**

```
PHASE: [IDEATION | PLANNING | BUILDING | REVIEW | SHIPPING]
CURRENT TASK: [Task ID or "none"]
APPROACH: [Brief description of intended approach]
```

This commitment mechanism improves follow-through. Once you write "PHASE: BUILDING", you're committed to following Building phase behaviors.

**When to use checkpoints:**
- Starting a new conversation
- User gives a new significant request
- Switching between tasks
- Before major implementation decisions

## Phase Detection

Detect the current phase from context clues:

| Phase | Signals | Primary Tools |
|-------|---------|---------------|
| **Ideation** | "I want to build...", "What if we...", no tasks exist | /brainstorm, /research, WebSearch |
| **Planning** | PRD exists, tasks being created, "how should we..." | Task Master parse-prd, expand |
| **Building** | Task in progress, writing code, "implement..." | Superpowers TDD, /test, /lint |
| **Review** | Code complete, "review this", PR prep | /code-review, /security-audit |
| **Shipping** | Ready to merge, "create PR", release prep | /pr, /changelog, /github-sync |

## Automatic Behavior by Phase

### When in IDEATION Phase

User is exploring ideas, not ready to code yet.

**Do:**
- Use /brainstorm for structured idea exploration
- Use /research for gathering information
- Ask clarifying questions liberally
- Use WebSearch for current information
- Summarize options before recommending

**Don't:**
- Jump to implementation
- Create tasks prematurely
- Use heavy tools like Context7 unless needed

### When in PLANNING Phase

User has decided what to build, needs structured plan.

**Do:**
- Check for existing PRD in `.taskmaster/docs/` or `.prd/`
- Use `task-master parse-prd` to generate tasks
- Use `task-master expand` to break down complex tasks
- Use `task-master next` to identify starting point
- Ask about priorities and dependencies

**Don't:**
- Start coding before tasks exist
- Skip the planning step for non-trivial work

### When in BUILDING Phase

Actively implementing features or fixes.

**Do:**
- Check current task with `task-master get-task`
- Follow Superpowers TDD workflow: RED → GREEN → REFACTOR
- Run /test and /lint before considering done
- Commit frequently (per claude-behavior.md rules)
- Update task status as you progress

**Don't:**
- Work on multiple tasks simultaneously
- Skip tests for "simple" changes
- Forget to commit working code

### When in REVIEW Phase

Code is written, needs quality check.

**Do:**
- Run /code-review on changed files
- Run /security-audit for security-sensitive code
- Run /optimize if performance matters
- Address all critical/high issues before PR

**Don't:**
- Create PR with failing tests
- Skip security review for auth/payment code

### When in SHIPPING Phase

Ready to share with team or deploy.

**Do:**
- Use /github-sync to update issues
- Use /pr to create pull request
- Use /changelog if releasing
- Update task status to done

**Don't:**
- Force push to main
- Skip PR for significant changes

## Human Input Triggers

**Before proceeding on ambiguous requests, state your decision:**

```
DECISION: [ASK USER | PROCEED]
REASON: [Why this choice]
```

**Always ask the user when:**
- Multiple valid approaches exist (use /brainstorm)
- Requirements are ambiguous (per reasoning-patterns.md)
- Making architectural decisions
- About to delete or significantly refactor code
- Choosing between trade-offs (performance vs readability)
- Task scope seems larger than expected

**Proceed without asking when:**
- Clear, unambiguous task
- Following established patterns in codebase
- Bug fix with obvious solution
- Routine operations (commit, test, lint)

## Tool Selection Decision Tree

```
START: What does the user need?
│
├─► Explore ideas? ──────────► /brainstorm
│
├─► Research something? ─────► /research (see below)
│   ├─ Known library? ───────► Tier 1-3 lookup (reasoning-patterns.md)
│   ├─ Current events? ──────► WebSearch
│   └─ PDF/paper? ───────────► Read tool + summarize
│
├─► Plan work? ──────────────► Task Master
│   ├─ Have PRD? ────────────► parse-prd
│   ├─ Task too big? ────────► expand
│   └─ What's next? ─────────► next
│
├─► Write code? ─────────────► Superpowers TDD flow
│   ├─ Write test first ─────► RED phase
│   ├─ Make test pass ───────► GREEN phase
│   └─ Clean up ─────────────► REFACTOR phase
│
├─► Review code? ────────────► /code-review, /security-audit
│
├─► Full feature cycle? ─────► /orchestrate feature
│   ├─ Just review? ─────────► /orchestrate review
│   └─ Just refactor? ───────► /orchestrate refactor
│
├─► Multi-model input? ──────► /multi-plan, /multi-execute
│
├─► Ship code? ──────────────► /pr, /github-sync, /changelog
│
└─► Something else? ─────────► Ask for clarification
```

## Continuous Background Behaviors

These should happen automatically throughout:

1. **Task awareness**: Know current task, update status
2. **Git discipline**: Commit frequently, meaningful messages
3. **Test awareness**: Run tests after changes
4. **Token consciousness**: Use lightweight options first

## Research Workflow

For research tasks (papers, documentation, exploration):

1. **Define the question clearly** - What specifically do we need to know?
2. **Check existing knowledge** - Do I already know this reliably?
3. **Search if needed** - WebSearch for current info, WebFetch for specific pages
4. **Read primary sources** - Use Read tool for PDFs, papers
5. **Summarize findings** - Distill to actionable insights
6. **Document if valuable** - Add to project docs or task notes

**For PDFs/Papers:**
```
1. Read the PDF using Read tool
2. Extract: Abstract, key findings, methodology, conclusions
3. Summarize in 200-500 words
4. Note relevance to current project/task
5. Ask user if deeper analysis needed
```
