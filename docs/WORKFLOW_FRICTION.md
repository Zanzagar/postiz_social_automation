# Workflow Friction Log

| ID | Phase | Severity | Issue | Resolution |
|----|-------|----------|-------|------------|
| F1 | 1.1   | MEDIUM   | Test plan expected "8 core + 5 language rules" but only 8 core rules exist. No language-specific rule files in template. | Adjust test plan expectation — template provides 8 core rules only. Language-specific guidance lives in skills, not rules. |
| F2 | 1.1   | INFO     | No instincts directory created at bootstrap — `.claude/instincts/` is empty | Expected behavior — instincts are generated over time by continuous-learning skill. |
| F3 | 1.8   | INFO     | MCP count exceeds expectation — 4 MCPs loaded (task-master-ai, context7, playwright, ide) vs expected 2 | Extra MCPs from Claude Code IDE integration. Not a problem but adds ~15-20k tool definition tokens. |
| F4 | health | LOW      | sync-template.sh not available — /health check tries to run it | Template bootstrap via init-project.sh (copy mode) doesn't include sync-template.sh. Health check should handle missing script gracefully. |
| F5 | 1.7   | LOW      | tasks.json lives at `.taskmaster/tasks.json`, not `.taskmaster/tasks/tasks.json`. But `task-master list` creates/reads from `.taskmaster/tasks/tasks.json` path. Two files. | Task Master CLI creates its own path structure on first use. The `.taskmaster/tasks.json` from init is the seed; CLI creates `.taskmaster/tasks/` on first operation. |
