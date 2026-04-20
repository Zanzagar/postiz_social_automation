<!-- template-version: 2.7.0 -->
<!-- template-file: .claude/rules/superpowers-integration.md -->
<!-- superpowers-compat: v5.0.0+ -->
# Superpowers + Task Master Integration

This rule defines how Superpowers plugin skills integrate with the template's Task Master workflow. It OVERRIDES Superpowers skill routing where the two systems conflict.

## Authority

Per `authority-hierarchy.md`, rules take precedence over all other instruction sources. This includes Superpowers skill instructions that conflict with the template's workflow.

## The Correct Pipeline

Every non-trivial task follows this pipeline:

```
1. IDEATE    → superpowers:brainstorming (explore, clarify, propose approaches)
2. VALIDATE  → /research (validate technical assumptions — APIs, libraries, constraints)
3. SPECIFY   → /prd-generate or manual PRD (create .taskmaster/docs/prd_*.txt)
4. DECOMPOSE → task-master parse-prd --input=<file> --num-tasks=0
5. ANALYZE   → task-master analyze-complexity (research task difficulty)
6. EXPAND    → task-master expand --prompt (guided by complexity analysis + quality prompt)
7. IMPLEMENT → superpowers:test-driven-development (RED-GREEN-REFACTOR per task)
8. REVIEW    → superpowers:requesting-code-review
9. SHIP      → superpowers:finishing-a-development-branch
```

## Critical Override: Brainstorming Exit

**The Superpowers brainstorming skill says:** "The terminal state is invoking writing-plans."

**This rule overrides that.** After brainstorming completes:

1. **Save the design doc** as the brainstorming skill instructs (`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`)
2. **Do NOT invoke `writing-plans`.** Instead:
3. **Validate technical assumptions** using `/research` — check API docs, library health, rate limits, known bugs, and integration patterns for any technologies referenced in the design doc. This prevents mid-implementation discovery of broken assumptions.
4. **Create a PRD** from the brainstorming output + validation findings using `/prd-generate` or manually write it to `.taskmaster/docs/prd_<slug>.txt`. Include a **Technical Constraints** section with validated API limits, library versions, known issues.
5. **Parse the PRD** into Task Master: `task-master parse-prd --input=<file> --num-tasks=0`
6. **Analyze complexity**: `task-master analyze-complexity`
7. **Expand tasks** guided by the complexity report: `task-master expand --id=<id> --prompt="$(cat .taskmaster/prompts/quality-expand.txt)" --force` for tasks flagged as complex. The quality prompt produces subtasks with checkbox acceptance criteria, scope boundaries, business context, code patterns, and technical constraints.
8. **Then implement** using Superpowers TDD per task

**Why:** The brainstorming design doc captures the *what* and *why*. Technical validation catches broken assumptions before they're baked into the PRD. The PRD structures both for Task Master consumption. Dogfood testing showed that skipping validation caused mid-implementation discovery of API bugs, rate limits, and preferred integration methods — all of which should have been known before writing the PRD.

**Important (Superpowers v5 alignment):**
- The brainstorming skill's **spec review loop** (step 7) fires BEFORE the override kicks in. Do NOT skip it — let the subagent reviewer validate the design doc for completeness before technical validation begins. The spec review checks document quality; our `/research` step checks technical feasibility. They are complementary.
- The brainstorming skill's **scope assessment** detects multi-subsystem requests early and flags them for decomposition. This complements Task Master's complexity analysis, which catches oversized tasks later.

## Document Locations

Three distinct artifact locations exist in this template:

| Artifact | Path | Purpose |
|----------|------|---------|
| Design docs (specs) | `docs/superpowers/specs/` | Brainstorming output — the *what* and *why* |
| Micro-plans | `docs/superpowers/plans/` | writing-plans output — optional per-task step breakdown |
| PRDs | `.taskmaster/docs/prd_*.txt` | Task Master input — structured for parse-prd consumption |

Design docs and PRDs are related but distinct: the design doc captures the validated design from brainstorming; the PRD restructures it with dependency graphs and technical constraints for Task Master's task decomposition.

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
4. `task-master expand --id=<id> --prompt="$(cat .taskmaster/prompts/quality-expand.txt)" --force` for each task flagged as needing subtasks
5. Simple tasks (complexity < 5) may not need subtasks at all

This prevents over-decomposition of simple tasks and under-decomposition of complex ones.

### Quality Expand Prompt

The file `.taskmaster/prompts/quality-expand.txt` injects structure requirements into subtask generation. Every subtask produced will include:

1. **Checkbox acceptance criteria** — measurable, with HTTP codes/field names/thresholds
2. **Scope boundaries** — explicit in-scope/out-of-scope per subtask
3. **Business context** — why the subtask matters to the product
4. **Code patterns** — existing implementations to follow as templates
5. **Technical constraints** — hard limits on implementation choices

This was validated against Hamster Studio's task quality (76/100 → TM with quality prompt matched or exceeded). The prompt file is the single highest-leverage improvement for task quality — always use it with expand.

**Without the prompt:** Generic subtasks with prose descriptions and vague test strategies.
**With the prompt:** Implementation-ready subtasks that an agent can execute with minimal clarification.

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
│   └─ Requirements clear? → technical validation → PRD directly
│   └─ After brainstorming:
│       → /research (validate tech assumptions) → PRD → parse-prd → analyze-complexity → expand → TDD per task
└─ Research/exploration? → No planning skills needed, just explore
```
