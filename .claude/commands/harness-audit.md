---
name: harness-audit
description: Run deterministic template health scoring across 7 categories
arguments:
  - name: scope
    description: "Audit scope: repo (default), hooks, skills, commands, agents, security"
    required: false
  - name: format
    description: "Output format: text (default), json"
    required: false
---

# Template Health Audit

Run the deterministic harness audit scoring engine to assess template configuration health.

## Steps

1. Run the audit engine:

```bash
node scripts/harness-audit.js $scope $format
```

2. Present the results to the user.

3. If any checks failed, explain:
   - What the failed check verifies
   - How to fix it (specific file to create/modify)
   - Priority (checks with higher weight are more impactful)

## Categories (10 points each, 70 max)

| Category | What It Checks |
|----------|---------------|
| **Tool Coverage** | MCP configs, hooks, agents, skills, commands |
| **Context Efficiency** | CLAUDE.md size, conditional rules, context modes |
| **Quality Gates** | Pre-commit, formatter, quality-gate, file-size-guard, protect hooks |
| **Memory & Persistence** | Session init/end, pre-compact, sessions dir, suggest-compact |
| **Eval & Testing** | Test/lint config, CI workflow, /verify and /eval commands |
| **Security Guardrails** | Protect hook, security rule, .gitignore, no secrets, doc blocker |
| **Cost Efficiency** | Cost tracker, /model-route, hook profiles, sub-agent routing |

## Score Interpretation

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 90-100% | Fully configured, production-ready template |
| B | 80-89% | Well configured, minor gaps |
| C | 70-79% | Functional but missing recommended features |
| D | 60-69% | Significant gaps, address top actions |
| F | <60% | Major configuration needed |

## Scoped Audits

- `/harness-audit security` — Check only security guardrails
- `/harness-audit hooks` — Check quality gates + memory persistence
- `/harness-audit` — Full 7-category audit (default)

## JSON Output

Use `--format json` for machine-readable output suitable for CI gates or trend tracking.
