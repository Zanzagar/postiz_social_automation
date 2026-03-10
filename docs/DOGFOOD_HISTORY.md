# Dogfood Test History & Comparative Analysis

This document tracks every dogfood test of the project template, comparing the **quality of outputs** across template versions to demonstrate that added complexity actually improves outcomes. Use alongside `DOGFOOD_CHECKLIST.md`.

---

## Test Registry

| # | Project | Date | Template Version | Focus | Key Discovery |
|---|---------|------|-----------------|-------|---------------|
| 1 | rideshare-rescue | 2025-12-01–03 | pre-v1 | Build only, no workflow | Code gets written regardless of template |
| 2 | analog_image_generator (test-projects/) | ~2025-12 | early | Planning only, no execution | Complexity analysis + --research flag |
| α1 | **postiz (test-projects/)** | 2026-02-19–20 | ~v2.2 | Planning + 1 TDD task | 18 friction items, MCP/CLI split |
| α2 | **ISKCON-GN/postiz_social_automation** | 2026-02-18–20 | ~v2.3 | Build + hooks + review | TDD works, orchestration works, instincts work |
| 4 | **postiz-social-automation (NEW)** | 2026-02-23+ | **v2.3.1** | **Full workflow** | TBD |

Tests 1 and 2 were early explorations on different projects. **α1 and α2 are the primary comparison baselines** — both test the same domain (postiz social automation) with earlier template versions.

---

## Alpha Test α1: postiz (test-projects/) — Planning-Focused

**Template version**: ~v2.2 (pre-guardrails, pre-enforcement rules)
**What it was**: 3-session friction audit. Ideation → planning → 1 TDD implementation task.

### What Was Produced

| Artifact | Detail |
|----------|--------|
| **PRD** | 200-line PRD with 4 phases in `.taskmaster/docs/prd.txt` |
| **Tasks** | 22 tasks generated via `parse-prd`, tag `postiz-mvp` |
| **Subtasks** | 110 subtasks (flat 5 per task — no complexity analysis) |
| **Code** | 36 LOC (branding checker) + 95 LOC tests (14 tests, 100% pass) |
| **Commits** | 7 conventional commits |
| **Docs** | Design doc, assessment, context docs, friction log (1,148 lines total) |

### Quality of Outputs

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| **Task decomposition** | Poor | `expand --all` used blindly → simple tasks got 5 subtasks, complex tasks got 5 subtasks. No differentiation. |
| **Task quality** | Medium | Titles meaningful, but dependencies and test strategies thin. IDs non-sequential (28-49 not 1-22). |
| **Code quality** | High | Branding checker is clean, 100% test coverage. But only 1 of 22 tasks completed. |
| **TDD compliance** | High (1 task) | RED → GREEN → REFACTOR properly followed for task #41. |
| **Git discipline** | Medium | Conventional commits ✅, but no feature branches, commits to main. |
| **Planning → execution link** | Weak | PRD → tasks existed, but planning artifacts didn't inform implementation approach. Tasks were too generic. |
| **Hooks/enforcement** | None | Zero hooks enabled. No pre-commit validation. No context monitoring. Hit 94% context with no warning. |
| **Session continuity** | None | No session artifacts, handoff docs, or instincts. |

### Friction Found (18 items)

| Category | Count | Impact on Output Quality |
|----------|-------|------------------------|
| Tool failures (MCP/CLI, ANSI corruption, timeouts) | 5 | Blocked task creation, lost time to debugging infra |
| Workflow gaps (brainstorm exit, expand without analysis) | 5 | Wrong routing, over-decomposition, wasted subtasks |
| Missing enforcement (no hooks, no context monitoring) | 4 | Silent degradation, no guard rails |
| Ergonomic issues (task IDs, subtask overhead) | 4 | Confusion, ceremony overhead |

---

## Alpha Test α2: ISKCON-GN/postiz — Build-Focused

**Template version**: ~v2.3 (hooks existed, but planning skipped)
**What it was**: 2-day sprint building a Postiz health monitoring system. Jumped straight to coding.

### What Was Produced

| Artifact | Detail |
|----------|--------|
| **Research/audits** | 3 domain audit docs (~35KB total): online presence audit, technology assessment, client context |
| **PRD** | None — tasks.json empty, Task Master never populated |
| **Tasks** | 0 (Task Master initialized but unused) |
| **Code** | ~500 LOC across 5 feature modules (health monitor, alerter, checker, storage, orchestrator) |
| **Tests** | 66+ tests (health_alerter alone), tests precede feat commits in git log |
| **Commits** | 19 conventional commits over 2 days |
| **Review** | `/orchestrate review` run → REPORT.md generated |
| **Instincts** | 5 instinct candidates extracted + persisted |
| **Session artifacts** | 1 session summary, eval harness configured |

### Quality of Outputs

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| **Research/audit depth** | High | 3 comprehensive domain docs: platform-by-platform rebrand audit (16KB), Postiz vs SaaS technology assessment (11KB), client context with branding rules (7KB). These informed all subsequent work. |
| **Task decomposition** | None | No tasks created. Work was ad-hoc, driven by developer intuition, not structured decomposition. |
| **Task quality** | N/A | Task Master unused entirely. |
| **Code quality** | High | 5 modules with comprehensive test suites. 66+ tests in alerter. |
| **TDD compliance** | High | Git log shows `test:` commits preceding `feat:` commits — genuine RED → GREEN signal. |
| **Git discipline** | Medium | Conventional commits ✅ (19 total), but all to main, no feature branches. |
| **Planning → execution link** | None | No planning phase at all. Zero PRDs, zero tasks. |
| **Hooks/enforcement** | Partial | observe.sh, session-end.sh, pattern-extraction.sh produced artifacts. 15 of 18 hooks unverified. |
| **Session continuity** | Partial | 1 session artifact + 5 instincts. Eval harness configured. |

---

## Direct Quality Comparison: α1 vs α2 vs Expected (Test 4)

This is the core question: **does the full v2.3.1 workflow produce better outcomes than either alpha approach?**

### Output Quality by Dimension

| Dimension | α1 (Planning-first) | α2 (Build-first) | Test 4 (Full workflow) | What v2.3.1 adds |
|-----------|:-------------------:|:-----------------:|:---------------------:|-----------------|
| **Research/audit depth** | Used α2's docs as input | High (3 domain audits, 35KB) | Expected: High | Brainstorming skill step 1 + checklist verification |
| **PRD dependency structure** | None (flat phases only) | N/A (no PRD) | Expected: High | `/prd-generate` now includes Phase 3.5 (Dependency Graph) with explicit `Depends on [X, Y]` markers |
| **Task decomposition** | Poor (default 5 subtasks — no complexity analysis run) | None (no tasks) | Expected: High | Complexity-first expansion, threshold rule (≥5 = expand) |
| **Task quality** | Medium (generic) | N/A | Expected: High | PRD dependency graph → parse → complexity scoring → guided expansion |
| **Code quality** | High (1 task) | High (5 modules) | Expected: High | TDD enforced via Superpowers, not just advisory |
| **TDD compliance** | 1 task only | Yes (advisory) | Expected: Full | Superpowers enforcement (deletes code without tests) |
| **Git discipline** | No branches | No branches | Expected: Full | pre-commit-check.sh blocks main commits + validates format |
| **Planning → execution** | Weak link | No link | Expected: Strong | Same tag, same task IDs, status tracking through full cycle |
| **Hooks/enforcement** | 0/18 hooks | 3/18 hooks | Expected: 18/18 | All hooks enabled in settings.json by default |
| **Context management** | Hit 94% blind | Unknown | Expected: Monitored | suggest-compact.sh + execution readiness rule |
| **Session continuity** | None | Partial | Expected: Full | session-init/end hooks + pre-compact + handoff docs |
| **Review quality** | None | Orchestrate run | Expected: Full | /code-review + /security-audit before PR |
| **Branch completion** | Never reached | Never reached | Expected: Full | Prescribed: push → PR → CI → squash merge → cleanup |

### The Key Gaps Each Alpha Exposed

**α1 showed**: The planning pipeline works (PRD → tasks → subtasks) but produces **mediocre task decomposition** without complexity analysis. And planning without hooks means **zero safety nets** during execution.

**α2 showed**: TDD and code quality work well when the developer follows discipline, but **planning gets skipped under time pressure** because it's normative-only. The code produced was good, but there's no traceability back to requirements.

### What v2.3.1 Should Prove

The full workflow should demonstrate that **combining α1's planning with α2's execution discipline** produces better outcomes than either alone:

1. **Better task decomposition than α1**: Complexity-first expansion should produce variable subtask counts (simple tasks: 0-2, complex tasks: 4-6) instead of flat 5-per-task.

2. **Planning traceability that α2 lacked**: Every piece of code should trace back to a Task Master task, which traces back to a PRD requirement.

3. **Enforcement that neither alpha had**: Hooks should catch mistakes (bad commit messages, main-branch commits, context pressure) that both alphas missed.

4. **Complete lifecycle coverage**: Both alphas stopped before review/shipping. Test 4 should complete the full cycle: brainstorm → PRD → tasks → TDD → review → PR → merge.

### Success Criteria for Test 4

To demonstrate improvement over both alphas, Test 4 must show:

| Criterion | α1 Baseline | α2 Baseline | Test 4 Target |
|-----------|:-----------:|:-----------:|:-------------:|
| Tasks with variable subtask counts | No (flat 5) | N/A | Yes |
| TDD on every code task | 1 of 22 | ~5 of 5 | All code tasks |
| Feature branches used | No | No | Yes, every feature |
| pre-commit-check.sh fires | No | Unknown | Yes, every commit |
| Branch completion (PR + merge) | No | No | At least 1 full cycle |
| Code review before merge | No | Yes (1 orchestrate) | Yes, for every PR |
| Session artifacts produced | No | Partial (1) | Yes, every session |
| Context monitored (no blind 94%) | No | Unknown | Yes, suggest-compact.sh active |
| Planning → execution traceability | Weak | None | Task IDs in commits or PR |

---

## Comparative Coverage Matrix

### Phase Coverage (Postiz tests only)

| Phase | α1 (test-projects/) | α2 (ISKCON-GN/) | Test 4 (NEW) |
|-------|:-------------------:|:----------------:|:------------:|
| 0: Bootstrap | Yes | Yes | **Expected: Full** |
| 1: Session Start (hooks) | No | Partial | **Expected: Full** |
| 2: Ideation (brainstorm) | Yes | Yes | **Expected: Full** |
| 3: Planning (PRD → tasks) | Yes | **No** | **Expected: Full** |
| 4: Complexity Analysis | Partial (skipped initially) | No | **Expected: Full** |
| 5: Task Expansion | Partial (blind expand) | No | **Expected: Full** |
| 6: Implementation (TDD) | 1 task | **Yes (5 modules)** | **Expected: Full** |
| 7: Review | No | **Yes** | **Expected: Full** |
| 8: Branch Completion | No | No | **Expected: Full** |
| 9: Session Lifecycle | No | Partial | **Expected: Full** |

**The split**: α1 covered phases 0-5 (planning). α2 covered phases 0, 6-7, 9 (execution). Neither covered phase 8 (branch completion). Test 4 must cover all.

### Hook Coverage (Postiz tests only)

| Hook | α1 | α2 | Test 4 (NEW) |
|------|:--:|:--:|:------------:|
| session-init.sh | — | ? | **Expected** |
| project-index.sh | — | ? | **Expected** |
| pre-compact.sh | — | ? | **Expected** |
| suggest-compact.sh | — | ? | **Expected** |
| pre-commit-check.sh | — | ? | **Expected** |
| protect-sensitive-files.sh | — | ? | **Expected** |
| doc-file-blocker.sh | — | ? | **Expected** |
| post-edit-format.sh | — | ? | **Expected** |
| console-log-audit.sh | — | ? | **Expected** |
| typescript-check.sh | — | ? | **Expected** |
| dev-server-blocker.sh | — | ? | **Expected** |
| long-running-tmux-hint.sh | — | ? | **Expected** |
| build-analysis.sh | — | ? | **Expected** |
| pr-url-extract.sh | — | ? | **Expected** |
| observe.sh | — | ✅ | **Expected** |
| session-end.sh | — | ✅ | **Expected** |
| session-summary.sh | — | ? | **Expected** |
| pattern-extraction.sh | — | ✅ | **Expected** |

### Enforcement Coverage (Postiz tests only)

| Rule | α1 | α2 | Test 4 (NEW) |
|------|:--:|:--:|:------------:|
| Conventional commits | Yes | Yes | **Expected** |
| Branch discipline | No | No | **Expected** |
| TDD enforcement (Superpowers) | 1 task | Advisory | **Expected (enforced)** |
| PRD-first | Yes | **No** | **Expected** |
| Tag per phase | Yes | No | **Expected** |
| One task in-progress | ? | ? | **Expected** |
| Commit frequency | Partial (7) | Yes (19) | **Expected** |
| Execution readiness check | N/A | N/A | **Expected (new in v2.3.1)** |
| Brainstorm exit override | **Broken** | ? | **Expected (fixed v2.3.0)** |
| Complexity-first expand | **No** | N/A | **Expected** |
| Orchestrate review | No | **Yes** | **Expected** |
| Continuous learning | No | **Yes** | **Expected** |

---

## Feature Discovery Timeline

| Discovery | Source | Template Fix | Version |
|-----------|--------|-------------|---------|
| MCP vs CLI split for AI ops | α1 | Documented in MEMORY.md | — |
| Brainstorm → writing-plans override | α1 | `superpowers-integration.md` rule | v2.3.0 |
| Context monitoring needs hooks enabled | α1 | Hooks enabled by default in settings.json | v2.3.0 |
| TDD mismatches infra tasks | α1 | Noted (not yet addressed) | — |
| `parse-prd` needs `--force` + timeout | α1 | Documented in MEMORY.md | — |
| `analyze-complexity` output rendering bug | α1 | Workaround: use `complexity-report` | — |
| `expand --all` over-decomposes | α1 | Threshold rule (≥5) documented | v2.3.0 |
| TDD works well for code-centric projects | α2 | Validates template design | — |
| Orchestrate review pipeline works e2e | α2 | Validates orchestration | — |
| Continuous learning hooks produce instincts | α2 | Validates CL system | — |
| Planning gets skipped under time pressure | α2 | Normative-only gap identified | — |
| Local squash merge needs `-D` | Prep | Docs clarified | v2.3.1 |
| Execution readiness check needed | Prep | Rule added to context-management.md | v2.3.1 |
| PRD lacks dependency structure for parse-prd | α1 analysis | `/prd-generate` Phase 3.5 (Dependency Graph) added | v2.3.1+ |
| Research docs not verified during brainstorming | α2 analysis | Checklist Phase 2.2 (Research & Context Intake) added | v2.3.1+ |

---

## How to Use This Document

### After Each Dogfood Test

1. Add a row to the **Test Registry**
2. Create a **What Was Produced** + **Quality of Outputs** section (follow α1/α2 format)
3. Update the **Direct Quality Comparison** table with actual results
4. Fill in the **Success Criteria** pass/fail
5. Add any new discoveries to the **Feature Discovery Timeline**

### When Evaluating a Template Change

Ask: **"Does this change improve an area where α1 or α2 scored poorly?"**

| If the change targets... | Evidence it's needed |
|--------------------------|---------------------|
| Task decomposition | α1: flat 5-per-task, no differentiation |
| Planning enforcement | α2: skipped planning entirely |
| Branch discipline | Both: all commits to main |
| Hook coverage | α1: 0/18, α2: 3/18 |
| Context monitoring | α1: hit 94% blind |
| Session continuity | α1: none, α2: partial |

If the change doesn't address a known gap from α1 or α2, it's speculative — validate in the next test before shipping.

### Regression Detection

These features passed in prior tests and must continue to pass:

| Feature | Passing Since | Regression = |
|---------|--------------|-------------|
| Conventional commits format | α1 | Commit without type: prefix accepted |
| PRD → task generation | α1 | parse-prd fails or produces garbage |
| TDD RED → GREEN cycle | α1 (1 task) | Tests pass before implementation |
| Orchestrate review pipeline | α2 | /orchestrate review fails or produces empty report |
| Instinct extraction | α2 | pattern-extraction.sh produces no candidates |
| Brainstorm exit override | v2.3.0 fix | Brainstorm routes to writing-plans instead of PRD |

---

## Metrics Over Time

| Metric | α1 (test-projects/) | α2 (ISKCON-GN/) | Test 4 (NEW) |
|--------|:-------------------:|:----------------:|:------------:|
| Template version | ~v2.2 | ~v2.3 | v2.3.1 |
| Phase coverage (of 10) | 4/10 | 5/10 | ?/10 |
| Hook coverage (of 18) | 0/18 | 3/18 | ?/18 |
| Enforcement rules tested | 5 | 5 | ? |
| Friction items found | 18 | 0* | ? |
| Code LOC produced | 131 | ~500 | ? |
| Test LOC produced | 95 | 66+ tests | ? |
| Git commits | 7 | 19 | ? |
| Instincts extracted | 0 | 5 | ? |
| Tasks completed | 1/22 | ~5 (ad-hoc) | ? |
| Branch completion cycles | 0 | 0 | ? |

*No formal friction logging in α2.

### The Core Trend

α1 and α2 represent two halves of the same workflow:

```
α1:  [Brainstorm] → [PRD] → [Tasks] → [Expand] → [1 TDD task] → STOP
α2:  [Skip all planning] ──────────────────────── → [TDD] → [Review] → STOP
Test 4: [Brainstorm] → [PRD] → [Tasks] → [Expand] → [TDD] → [Review] → [PR] → [Merge]
```

Test 4's job is to close the loop — prove that combining structured planning with disciplined execution produces outcomes better than either half alone.
