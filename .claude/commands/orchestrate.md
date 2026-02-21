Execute a multi-agent pipeline for comprehensive task handling.

Usage:
- `/orchestrate feature` — Full feature pipeline
- `/orchestrate review` — Comprehensive review pipeline
- `/orchestrate refactor` — Safe refactoring pipeline
- `/orchestrate agent1 agent2 agent3` — Custom pipeline

Arguments: $ARGUMENTS

## Default Pipelines

### feature
```
planner → tdd-guide → [implement] → code-reviewer → security-reviewer
```
Full feature cycle: plan it, write tests, implement, review.

### bugfix
```
planner → tdd-guide → [implement fix] → code-reviewer
```
Bug investigation and fix: understand the problem, write regression test, fix, review.

### review
```
code-reviewer → security-reviewer → database-reviewer (if SQL detected)
```
Comprehensive review: code quality, security, then database if relevant.

### refactor
```
architect → refactor-cleaner → code-reviewer → [run tests]
```
Safe refactoring: design the target, refactor, verify with review and tests.

### security
```
security-reviewer → code-reviewer → architect
```
Security-focused: find vulnerabilities, assess code quality, evaluate architecture.

## Custom Pipelines

Specify agent names in order:
```
/orchestrate architect planner code-reviewer
```

Available agents: planner, architect, tdd-guide, code-reviewer, security-reviewer, database-reviewer, doc-updater, refactor-cleaner, e2e-runner, go-reviewer, go-build-resolver, python-reviewer

## Execution Flow

### Setup

Before invoking the first agent, create the output directory:
```bash
mkdir -p .claude/orchestrate/<pipeline-name>/
```

### Per-Agent Cycle

For each agent in the pipeline:

1. **Compose prompt** with objective context (see Objective Context below)
2. **Invoke** the agent as a sub-agent (Task tool)
3. **Evaluate** the agent's output for completeness (see Iterative Evaluation below)
4. **Persist** the agent's report to `.claude/orchestrate/<pipeline>/<N>-<agent-name>.md`
5. **Pass** the file path and key findings to the next agent

### Objective Context

Every agent prompt MUST include the pipeline objective, not just the immediate query. Sub-agents lack the orchestrator's semantic context — they only know the literal query, not the PURPOSE behind the request.

```markdown
## Objective
[What the overall pipeline is trying to achieve — the user's original request]

## Your Role in This Pipeline
[Which phase this agent is in, what came before, what comes after]

## Input from Previous Agent
[Key findings from the previous agent's persisted report]

## Your Task
[The specific work this agent should do]
```

### Iterative Evaluation

After each agent returns, evaluate the output before accepting it:

1. **Check completeness** — Did the agent address all aspects of its task?
2. **Check actionability** — Are findings specific enough for the next agent to act on?
3. **Check consistency** — Does the output contradict earlier agent findings?

If the output is **insufficient**, re-invoke the agent with a follow-up prompt specifying what's missing. **Maximum 3 cycles per agent** — after 3 attempts, accept the best result and note gaps in the handoff.

```
Cycle 1: Initial invocation → evaluate
Cycle 2 (if needed): "Your report is missing X. Please also address Y." → evaluate
Cycle 3 (if needed): "Still need specifics on Z." → evaluate → accept regardless
```

### Handoff Document Format

Each agent produces a report that is **written to disk** at `.claude/orchestrate/<pipeline>/<N>-<agent-name>.md`:

```markdown
## [Agent Name] Report

### Objective
[The pipeline's overall goal — carried through every handoff]

### Summary
[Brief summary of findings/work]

### Findings
[Ordered by severity: CRITICAL → HIGH → MEDIUM → LOW]

### Recommendations
[Actionable next steps]

### Context for Next Agent
[Specific information the next agent needs, including file paths and line numbers]

### Evaluation
[Cycles needed: 1/2/3 | Gaps remaining: none / list]
```

### Persistence

All intermediate outputs survive context compaction and enable:
- **Human review** between phases (check `.claude/orchestrate/` at any time)
- **Pipeline resumption** after interruption (re-read last persisted report)
- **Audit trail** for decisions made during orchestration

After the pipeline completes, the orchestrate directory contains the full record:
```
.claude/orchestrate/feature/
  1-planner.md
  2-tdd-guide.md
  3-code-reviewer.md
  4-security-reviewer.md
  REPORT.md
```

## Final Report

After all agents complete, produce an aggregated report and **persist it** to `.claude/orchestrate/<pipeline>/REPORT.md`:

```
╔══════════════════════════════════════════════════════════╗
║                  ORCHESTRATION REPORT                     ║
╠══════════════════════════════════════════════════════════╣

Pipeline: feature (4 agents)
Duration: ~X minutes

Agent Results:
  [1] planner ............... ✓ Complete (3 findings)
  [2] tdd-guide ............. ✓ Complete (5 test suggestions)
  [3] code-reviewer ......... ✓ Complete (2 HIGH, 4 MEDIUM)
  [4] security-reviewer ..... ✓ Complete (1 CRITICAL)

Aggregated Findings (by severity):
  CRITICAL: 1
  HIGH: 2
  MEDIUM: 4
  LOW: 3

Top Issues:
1. [CRITICAL] security-reviewer: SQL injection in user input handler
2. [HIGH] code-reviewer: Missing error handling in API client
3. [HIGH] code-reviewer: Race condition in cache invalidation

Conflicts Between Agents:
  (none — or list where agents disagreed)
╚══════════════════════════════════════════════════════════╝
```

## Parallel Execution

For independent checks, run agents in parallel rather than sequentially:

```
### Sequential (default)
planner → tdd-guide → code-reviewer → security-reviewer

### Parallel phase (when agents don't depend on each other)
planner → tdd-guide → [implement] → ┬─ code-reviewer    ──┐
                                     └─ security-reviewer ──┤→ Merge Results
                                                            │
                                        database-reviewer ──┘
```

Use parallel execution when agents are doing independent reviews of the same code. The final report merges all parallel outputs.

## Notes

- Each agent runs in a fresh sub-agent context (isolated — stronger than manual `/clear`)
- Agent outputs are persisted to `.claude/orchestrate/<pipeline>/` for auditability and resumption
- Each agent is evaluated before acceptance; re-invoked up to 3 times if output is insufficient
- Pipeline stops on CRITICAL findings (unless `--continue` flag)
- Implement steps (marked with `[]`) are manual — you write the code
- Use `/orchestrate --dry-run` to preview pipeline without executing
- Clean up old orchestration outputs: `rm -rf .claude/orchestrate/` between unrelated runs
