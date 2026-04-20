# Security Guide

This project has two complementary security layers:

| Layer | Scope | Command |
|-------|-------|---------|
| **AgentShield** | Config-level risks (CLAUDE.md, MCPs, hooks, agents) | `npx ecc-agentshield scan` |
| **/security-audit** | Code-level vulnerabilities (OWASP Top 10, secrets, deps) | `/security-audit` |

Both should be used together for comprehensive coverage.

## AgentShield

AgentShield scans your Claude Code configuration for security risks that traditional code scanners miss.

### What It Scans

- **CLAUDE.md secrets** — Hardcoded API keys, tokens, or credentials in project instructions
- **MCP permissions** — Overly permissive MCP server configurations
- **Hook injection vectors** — Shell scripts in `.claude/hooks/` that could be exploited
- **Agent misconfigurations** — Agent definitions with excessive tool access or unsafe patterns
- **Sensitive file exposure** — Configuration files that should be protected

### Scan Modes

#### Quick Scan (Default)
```bash
npx ecc-agentshield scan
```
Fast scan of common risk patterns. Run this frequently.

#### Auto-Fix
```bash
npx ecc-agentshield scan --fix
```
Automatically remediates common issues (e.g., removing hardcoded secrets, tightening permissions). Review changes before committing.

#### Deep Scan
```bash
npx ecc-agentshield scan --opus
```
Uses 3 adversarial Claude agents to probe your configuration from different attack angles. More thorough but slower and uses API credits. Reserve for pre-release or after major config changes.

### When to Run

| Trigger | Scan Type | Why |
|---------|-----------|-----|
| Before committing `.claude/` changes | Quick | Catch misconfigs before they reach git |
| After adding new MCP servers | Quick | Verify MCP permissions are minimal |
| After modifying hooks | Quick | Check for injection vectors |
| Before PR reviews touching config | Quick | Reviewer confidence |
| In CI pipeline | Quick | Automated gate |
| Before release / major milestone | Deep | Comprehensive adversarial check |
| After importing external agents or skills | Quick | Verify third-party content is safe |

### CI Integration

Add AgentShield to your CI pipeline as a security gate:

```yaml
# .github/workflows/security.yml
name: Security Checks

on:
  push:
    paths:
      - '.claude/**'
      - 'CLAUDE.md'
  pull_request:
    paths:
      - '.claude/**'
      - 'CLAUDE.md'

jobs:
  agentshield:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Run AgentShield scan
        run: npx ecc-agentshield scan

  code-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install security tools
        run: pip install bandit safety
      - name: Run bandit
        run: bandit -r src/ -f json -o bandit-report.json || true
      - name: Check dependencies
        run: safety check --json || true
```

This triggers AgentShield only when Claude Code config files change, keeping CI fast.

### Common Findings

| Finding | Severity | Fix |
|---------|----------|-----|
| API key in CLAUDE.md | Critical | Move to `.env`, reference via environment variable |
| MCP server with write access to `/` | High | Restrict to project directory |
| Hook script without input validation | Medium | Add input sanitization |
| Agent with unrestricted Bash access | Medium | Limit to specific commands |
| Sensitive file not in protect list | Low | Add to `protect-sensitive-files.sh` |

## /security-audit (Code-Level)

The `/security-audit` command handles traditional code security:

- **OWASP Top 10** — SQL injection, XSS, command injection, path traversal
- **Secrets detection** — Hardcoded credentials in source code
- **Dependency vulnerabilities** — Known CVEs in packages
- **Authentication/authorization** — Password hashing, session management, RBAC
- **Data protection** — Encryption, cookie flags, HTTPS, PII handling

Run `/security-audit` (or `/security-audit src/api/` for targeted scans) as part of your review workflow.

See `.claude/commands/security-audit.md` for the full checklist.

## Combined Security Workflow

For comprehensive security coverage:

```
1. During development:
   ├── /security-audit on changed files (code-level)
   └── npx ecc-agentshield scan (if .claude/ changed)

2. Before PR:
   ├── /security-audit (full project)
   ├── npx ecc-agentshield scan
   └── Fix all Critical/High findings

3. In CI:
   ├── AgentShield on .claude/ path changes
   └── bandit + safety on code changes

4. Before release:
   └── npx ecc-agentshield scan --opus (deep scan)
```

## Sensitive File Protection

The `protect-sensitive-files.sh` hook blocks edits to sensitive files:

- `.env`, `.env.*` — Environment variables and secrets
- `*credentials*`, `*secret*` — Credential files
- `*.pem`, `*.key` — Private keys and certificates

Enable via `/settings safe` or add to `.claude/settings.local.json`. See `docs/HOOKS.md` for configuration.

## Agentic Security Patterns

Modern AI coding assistants introduce security considerations beyond traditional application security. The agent has filesystem access, can execute shell commands, and processes external content — all of which create unique attack surfaces.

### OWASP Agentic Top 10 Mapping

| Risk | Description | Template Mitigation |
|------|-------------|---------------------|
| A01: Excessive Agency | Agent has more permissions than needed | Hook profile system limits scope; `allowedTools` in settings |
| A02: Data Leakage | Sensitive data exposed through agent actions | Secret scrubbing in `observe.sh`; `protect-sensitive-files.sh` |
| A03: Tool Misuse | Agent tools used for unintended purposes | `protect-sensitive-files.sh` blocking; `file-size-guard.js` |
| A04: Prompt Injection | External content manipulates agent behavior | Guardrails in `security-hardening.md` rule |
| A05: Insecure Output | Agent generates unsafe outputs | `/code-review` and `/security-audit` commands |
| A06: Autonomy Abuse | Agent runs unchecked for too long | SIGUSR1 throttling; `cost-tracker.js`; `suggest-compact.js` |
| A07: System Prompt Leak | Agent instructions exposed | N/A (Claude Code runs locally, no API exposure) |
| A08: Data Integrity | Configuration files tampered with | Config tamper guard in `protect-sensitive-files.sh` |
| A09: Insecure Plugin | Third-party plugins introduce risk | MCP audit (`manage-mcps.sh audit`); 10/80 rule |
| A10: Supply Chain | Upstream dependencies compromised | AgentShield CI; upstream manifest tracking |

### PR Audit Checklist for Agent Config

For any PR touching `.claude/` or `CLAUDE.md`, verify:

- [ ] No broadened `allowedTools` scope without justification
- [ ] No hooks modified without security review
- [ ] No external links added to skills or rules (transitive injection vectors)
- [ ] No new MCP servers added without explicit approval
- [ ] No secrets or API keys hardcoded
- [ ] No `--dangerously-skip-permissions` added without documented reason
- [ ] AgentShield scan passes: `npx ecc-agentshield scan`

### Deny List Recommendations

Add these to your Claude Code settings `permissions.deny`:

```json
{
  "permissions": {
    "deny": [
      "Read(~/.ssh/*)",
      "Read(~/.aws/*)",
      "Read(~/.env)",
      "Read(**/credentials*)",
      "Read(**/.env*)",
      "Read(**/*.pem)",
      "Read(**/*.key)",
      "Write(~/.ssh/*)",
      "Write(~/.aws/*)",
      "Write(**/.env*)"
    ]
  }
}
```

These complement the `protect-sensitive-files.sh` hook (runtime enforcement) and `security-hardening.md` rule (behavioral guidance).

See `.claude/rules/security-hardening.md` for the full set of hardening recommendations.
