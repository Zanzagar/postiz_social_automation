Perform a security audit on the specified scope.

Usage:
- `/security-audit` - Audit entire project
- `/security-audit src/api/` - Audit specific directory
- `/security-audit src/auth.py` - Audit specific file

Arguments: $ARGUMENTS

## Audit Checklist

### 1. Secrets & Credentials
- [ ] Hardcoded passwords, API keys, tokens
- [ ] Secrets in configuration files
- [ ] Credentials in git history
- [ ] Proper use of environment variables

### 2. Input Validation (OWASP Top 10)
- [ ] SQL Injection vulnerabilities
- [ ] Command Injection (subprocess, os.system)
- [ ] Path Traversal (../../../etc/passwd)
- [ ] XSS in templates/responses
- [ ] XML External Entity (XXE)
- [ ] Unsafe deserialization (pickle, yaml.load)

### 3. Authentication & Authorization
- [ ] Password hashing (bcrypt, argon2)
- [ ] Session management
- [ ] JWT validation and expiry
- [ ] Role-based access control
- [ ] Rate limiting on auth endpoints

### 4. Data Protection
- [ ] Sensitive data encryption
- [ ] Secure cookie flags (HttpOnly, Secure, SameSite)
- [ ] HTTPS enforcement
- [ ] PII handling and logging

### 5. Dependencies
- [ ] Known vulnerabilities in packages
- [ ] Outdated dependencies
- [ ] Suspicious packages

## Output Format

Report findings as:

```
## Security Audit Report

**Scope:** [files/directories audited]
**Date:** [timestamp]

### Critical Issues
1. [Description] - [File:Line] - [Remediation]

### High Priority
1. ...

### Medium Priority
1. ...

### Low Priority / Recommendations
1. ...

### Summary
- Critical: X
- High: X
- Medium: X
- Low: X
```

## Tools to Use

If available in the project:
- `bandit` - Python security linter
- `safety` - Dependency vulnerability check
- `semgrep` - Pattern-based analysis

Run if installed:
```bash
bandit -r src/ -f json
safety check --json
```

## Config-Level Security

This audit covers **code-level** vulnerabilities. For **config-level** security (CLAUDE.md secrets, MCP permissions, hook injection vectors, agent misconfigs), run AgentShield:

```bash
npx ecc-agentshield scan
```

See `docs/SECURITY.md` for full details on AgentShield scan modes and CI integration.
