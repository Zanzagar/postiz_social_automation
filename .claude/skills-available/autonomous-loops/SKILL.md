---
name: autonomous-loops
description: Patterns for non-interactive agent work — sequential pipelines, de-sloppify, continuous PR loops, and safety defaults
---

# Autonomous Loops

Patterns for running Claude Code in non-interactive or semi-autonomous modes. Use when building automation scripts, CI integrations, or multi-step pipelines.

## Sequential Pipeline

Chain Claude calls with explicit failure handling:

```bash
set -e  # Fail on any error

# Each step reads the previous step's output
claude -p "Step 1: Research the API and document findings" > step1.md
claude -p "Step 2: Design the interface based on: $(cat step1.md)" > step2.md
claude -p "Step 3: Implement based on: $(cat step2.md)" --allowedTools Edit Write Bash
```

### Pipeline Best Practices

- Each step should produce a verifiable artifact (file, test result, commit)
- Use `--max-turns` to prevent infinite loops
- Pipe specific context, not entire conversation history
- Use `--model` to route each step to the appropriate tier

## De-Sloppify Pattern

After AI implementation, run a cleanup pass to remove common AI-generated noise:

1. **Remove defensive checks that "test the language"** — e.g., `if (typeof x === 'undefined')` in TypeScript where the type system already prevents this
2. **Remove redundant error handling for impossible states** — e.g., catching errors that can't occur given the input types
3. **Remove comments that restate the code** — e.g., `// increment counter` above `counter++`
4. **Remove unused imports/variables** — the linter catches these, but AI often adds "just in case"
5. **Simplify complex conditionals** — AI favors verbose chains over concise expressions

```bash
# Automated de-sloppify pass
claude -p "Review this file for AI-generated noise: unnecessary defensive checks, \
redundant comments, unused imports, over-engineering. Remove them. \
Do NOT add anything, only remove." --allowedTools Edit Read
```

**Key insight**: The same model that generates sloppy code will also generate sloppy cleanup. Use a fresh session or a different model for the review pass.

## Continuous PR Loop

For multi-day iterative projects:

```
1. Create feature branch
2. Implement in small commits
3. Push, trigger CI
4. If CI fails → fix, commit, push (loop to 3)
5. If CI passes → create PR, request review
6. Address review comments (loop to 2)
7. Merge when approved
```

### Automation Script Pattern

```bash
#!/bin/bash
# babysit-pr.sh — Watch a PR until it's mergeable
PR_NUMBER=$1
MAX_ITERATIONS=10

for i in $(seq 1 $MAX_ITERATIONS); do
    # Check CI status
    STATUS=$(gh pr checks "$PR_NUMBER" --json state --jq '.[].state' | sort -u)

    if echo "$STATUS" | grep -q "FAILURE"; then
        echo "Iteration $i: CI failed, fixing..."
        claude -p "Fix the CI failures on PR #$PR_NUMBER. Run gh run view --log-failed to diagnose." \
            --allowedTools Bash Edit Read Write
        git push
    elif echo "$STATUS" | grep -q "SUCCESS"; then
        echo "CI passed on iteration $i"
        break
    else
        echo "Waiting for CI..."
        sleep 60
    fi
done
```

## Model Routing in Loops

| Phase | Model | Rationale |
|-------|-------|-----------|
| Research | opus | Depth and accuracy matter |
| Implement | sonnet | Volume of code, cost-effective |
| Review | opus | Catch subtle issues |
| Fix known issues | sonnet/haiku | Known changes, lower risk |
| Formatting/cleanup | haiku | Mechanical, deterministic |

## Safety Defaults

When running autonomous loops, always:

- **Verify tests pass BEFORE the first iteration** — don't iterate on a broken baseline
- **Define an explicit stop condition** — max iterations, success criteria, or time limit
- **Never disable the hook profile during loops** — hooks are your safety net
- **Log each iteration** — timestamp, action taken, outcome, model used
- **Use `--max-turns`** — prevents runaway sessions (default: 10-20 for focused work)
- **Run in a git worktree** — isolates autonomous work from your main workspace

## The /loop Command

The template includes a `/loop` command for recurring tasks:

```bash
/loop 5m /health          # Run health check every 5 minutes
/loop 10m /check-upstream  # Check for upstream changes every 10 minutes
```

See the `loop` skill for configuration options.
