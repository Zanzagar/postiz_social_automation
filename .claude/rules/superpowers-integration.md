<!-- template-version: 2.0.0 -->
<!-- template-file: .claude/rules/superpowers-integration.md -->
# Superpowers + Task Master Integration

This rule defines how Superpowers plugin skills integrate with the template's Task Master workflow. It OVERRIDES Superpowers skill routing where the two systems conflict.

## Authority

Per `authority-hierarchy.md`, rules take precedence over all other instruction sources. This includes Superpowers skill instructions that conflict with the template's workflow.

## The Correct Pipeline

Every non-trivial task follows this pipeline:

```
1. IDEATE    → superpowers:brainstorming (explore, clarify, propose approaches)
2. SPECIFY   → /prd-generate or manual PRD (create .taskmaster/docs/prd_*.txt)
3. DECOMPOSE → task-master parse-prd --num-tasks 0
4. ANALYZE   → task-master analyze-complexity (research task difficulty)
5. EXPAND    → task-master expand (guided by complexity analysis)
6. IMPLEMENT → superpowers:test-driven-development (RED-GREEN-REFACTOR per task)
7. REVIEW    → superpowers:requesting-code-review
8. SHIP      → superpowers:finishing-a-development-branch
```

## Critical Override: Brainstorming Exit

**The Superpowers brainstorming skill says:** "The terminal state is invoking writing-plans."

**This rule overrides that.** After brainstorming completes:

1. **Save the design doc** as the brainstorming skill instructs (`docs/plans/YYYY-MM-DD-<topic>-design.md`)
2. **Do NOT invoke `writing-plans`.** Instead:
3. **Create a PRD** from the brainstorming output using `/prd-generate` or manually write it to `.taskmaster/docs/prd_<slug>.txt`
4. **Parse the PRD** into Task Master: `task-master parse-prd <file> --num-tasks 0`
5. **Analyze complexity**: `task-master analyze-complexity`
6. **Expand tasks** guided by the complexity report: `task-master expand --id=<id>` for tasks flagged as complex
7. **Then implement** using Superpowers TDD per task

**Why:** The brainstorming design doc captures the *what* and *why*. The PRD structures it for Task Master consumption. Task Master provides dependency tracking, status management, and subtask decomposition that `writing-plans` does not.

## When writing-plans IS Appropriate

`writing-plans` is valid for **micro-planning within a single task** — breaking one Task Master task into 2-5 minute executable steps during implementation. It should NOT be used as a replacement for the PRD → Task Master pipeline.

| Scope | Use |
|-------|-----|
| Project-level planning (multiple features/tasks) | PRD → Task Master |
| Feature-level planning (new capability) | PRD → Task Master |
| Task-level micro-planning (one task, many steps) | writing-plans (optional) |
| Bug fix (clear, scoped) | Direct implementation with TDD |

## Task Decomposition: Complexity-First

**Do NOT blindly run `task-master expand --all`.** Follow this sequence:

1. `task-master parse-prd` → creates top-level tasks
2. `task-master analyze-complexity` → produces a complexity report
3. Review the report — it recommends which tasks need expansion and how deep
4. `task-master expand --id=<id>` for each task flagged as needing subtasks
5. Simple tasks (complexity < threshold) may not need subtasks at all

This prevents over-decomposition of simple tasks and under-decomposition of complex ones.

## Superpowers Skills: When to Use Each

| Skill | When | Replaces |
|-------|------|----------|
| `brainstorming` | Starting any non-trivial feature | Nothing — always use for ideation |
| `writing-plans` | Micro-planning a single task (optional) | NOT a replacement for PRD/Task Master |
| `executing-plans` | Only if writing-plans was used for micro-planning | NOT for project execution |
| `test-driven-development` | Every implementation task | Nothing — always use for TDD |
| `systematic-debugging` | Any bug or test failure | Nothing — always use for debugging |
| `requesting-code-review` | After completing a task/feature | Nothing — always use for review |
| `finishing-a-development-branch` | When ready to merge | Nothing — always use for completion |
| `verification-before-completion` | Before claiming done | Nothing — always verify |

## Quick Decision Tree

```
User requests work →
├─ Trivial fix (< 10 lines)? → TDD directly, no planning needed
├─ Single well-defined task? → TDD directly (maybe writing-plans for steps)
├─ New feature or multi-task work?
│   ├─ Requirements unclear? → brainstorming FIRST
│   └─ Requirements clear? → PRD directly
│   └─ After brainstorming OR clear requirements:
│       → PRD → parse-prd → analyze-complexity → expand → TDD per task
└─ Research/exploration? → No planning skills needed, just explore
```
