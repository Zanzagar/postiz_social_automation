# AGENTS.md — postiz_social_automation

Standing rules every session (Claude, Codex, human) loads. The harness standard is
`~/projects/claude-harness` (https://github.com/Zanzagar/claude-harness): `docs/git-hygiene.md` is the git
standard, `docs/adr/0001-verification-precedence.md` the workflow precedence, `docs/adoption-matrix.md`
this project's row. Adopted here 2026-09-28 from harness `main` 47c2303, rules and grilling gate together, on the
owner's decision of that day.

## Workflow precedence (harness ADR 0001)

1. **Pocock's skills are the default workflow**: grill / grill-with-docs before creative or scope-changing
   work, domain-modeling for `CONTEXT.md` and ADRs, tdd for code that must stay correct,
   verification-before-completion before any "done", handoff saved in-repo (`docs/handoffs/`). Invoked on
   judgment, except where a gate says otherwise.
2. **Codex adversarial review is the check on any diff that matters** (`/codex:adversarial-review`,
   `/code-review`): flag-only, on demand; findings are claims to verify, never auto-applied. The stop-time
   review gate stays disabled.
3. **A fan-out wave is the last resort**, for one job neither of the above can do: breaking a claim about a
   measurement, an artifact or an archive that no test pins and no diff review reaches.

## Multi-agent runs

- **One wave at a time, never concurrent.**
- **At most 6 questions and at most 6 verifiers per wave**; the entry-point / decision-critical claim is
  verified first; the tail is logged as unverified, not silently covered.
- **Say what the wave will spawn before launching it**, in the reply the owner reads.
- Run waves through `.claude/workflows/question-fanout-audit.js` (the hard-capped harness copy). An inline
  `Workflow` script that exceeds the caps is a rule violation, not a tooling gap.
- Ultracode ON does not reopen the caps (owner, 2026-09-02).
- Verifiers write nothing; premises in a brief are hypotheses (harness `docs/multi-agent-field-rules.md`).

## Git

- Follow claude-harness `docs/git-hygiene.md` (floor amended 2026-09-24): commit as work completes and push
  after every commit, `main` included. Take a `<track>/<subject>` branch when the work might be abandoned
  or a diff that matters wants its Codex review first, and merge it yourself; no human step. Never make
  published history unrecoverable: no force-push, no deleting `main`, no rewriting pushed commits; a goof
  is fixed with `git revert`. The one exception to merging your own PR (rule 14, "Changes to the gate
  itself"): a change to the grilling gate's own files lands in a PR by itself and merges only on the
  owner's explicit go. The checked-in `.claude/settings.json` carries the deny/ask rules.
- **Grilling gate:** placeholder, replaced by adopt.sh. <!-- grill-gate:pointer -->
