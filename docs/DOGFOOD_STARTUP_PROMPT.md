# Dogfood Startup Prompt

Copy everything below the `---` line and paste it as your first message in a new Claude Code session started from `/home/cjh5690/projects/ISKCON-GN/postiz_social_automation/`.

---

## Context

You are dogfood-testing the project template v2.3.1 on a real project. This is the first test to cover the **full workflow** from bootstrap through shipping.

**Project**: Postiz Social Media Automation — Docker-based social media scheduling for Gita Valley (ISKCON community). The infrastructure (Docker Compose with Postiz, PostgreSQL, Redis, Temporal) is already set up. Your job is to build the automation layer on top of it.

**Template source**: `~/projects/project-template` (v2.3.1)

## Dogfood Protocol (MANDATORY)

This session is a controlled test of the project template workflow. You MUST follow the dogfood protocol:

1. **Read `docs/DOGFOOD_CHECKLIST.md` NOW** before doing anything else. This is your verification checklist with 100+ items across 9 phases.

2. **At every phase transition** (starting Phase 0, moving to Phase 1, etc.), read the relevant checklist section and verify each item. Mark items as `[x]` pass, `[!]` fail (note details in the Failure Log), or `[-]` skipped.

3. **Update the checklist file directly** as you complete items — this creates a live audit trail.

4. **If a checklist item fails**, log it in the Failure Log table at the bottom of the checklist with: phase, check name, expected output, actual output, severity, and notes. Then continue — don't stop the workflow for non-blocking failures.

5. **Read `docs/DOGFOOD_HISTORY.md`** to understand what the two alpha tests (α1 and α2) covered. The "Success Criteria for Test 4" section lists 9 specific outcomes this test must demonstrate.

6. **Compare output quality** as you go. When you complete a planning step, note whether the output is better than α1's (which used blind `expand --all` with flat 5 subtasks). When you complete a build step, note whether the discipline matches α2's (which had good TDD but no planning traceability).

## Research Context

Read these docs for domain understanding (already in `docs/`):
- `gita-valley-context.md` — Client profile, social accounts, content strategy
- `gita-valley-online-presence-audit-v2.md` — Platform audit, rebranding gaps
- `social-media-automation-assessment.md` — Postiz vs SaaS comparison

## Start Here

Begin with **Phase 0: Project Bootstrap** from the checklist. This includes:
- Running `init-project.sh` from the template
- Creating and customizing CLAUDE.md
- Initializing Task Master
- Installing Superpowers plugin
- Verifying MCP servers

After Phase 0 is complete with all checklist items verified, proceed to Phase 1 (Session Start verification), then Phase 2 (Ideation/Brainstorming).

Follow the template's prescribed workflow exactly as documented in the rules — this IS the test.
