# MCP Selection Wizard

Help the user enable/disable MCP servers based on their project needs to optimize context token usage.

## Instructions

1. First, get the current MCP status:
   ```bash
   claude mcp list
   ```

2. Read the MCP registry to understand available options:
   - Read `.claude/mcp-registry.json` for server details, categories, and presets

3. Ask the user about their project type using AskUserQuestion:

**Question: "What type of project are you working on?"**
- Python Backend (APIs, databases, services)
- Frontend Development (React, Vue, browser testing)
- Full-Stack Web Application
- E-Commerce / Payment Processing
- WordPress / Content Management
- Testing & QA Automation
- Minimal (just task management + docs)
- Custom Selection (choose individual MCPs)

4. Based on their selection, show:
   - Which MCPs will be enabled/disabled
   - Estimated token savings
   - Any MCPs that need to be installed first

5. Apply the configuration using:
   ```bash
   claude mcp disable <server> --scope project  # For servers to disable
   claude mcp enable <server> --scope project   # For servers to enable
   ```

6. **Save the project configuration** by creating `.claude/mcp-project.json`:
   ```json
   {
     "preset": "python-backend",
     "enabled": ["task-master-ai", "context7", "github", "postgres"],
     "disabled": ["paypal", "wpcom-mcp", "canva-dev"],
     "configured_at": "2024-01-15T10:30:00Z"
   }
   ```
   This file prevents the session-init hook from prompting again.

7. Remind the user to **restart Claude Code** for changes to take effect.

## Token Guidance

Explain to the user:
- Each MCP adds tools that consume context tokens
- Disabling unused MCPs frees up context for conversation
- Changes are project-scoped by default (won't affect other projects)
- They can re-enable any MCP at any time

## Presets Reference

| Preset | MCPs | Est. Tokens |
|--------|------|-------------|
| minimal | task-master-ai, context7 | ~4,300 |
| python-backend | + github, postgres | ~7,500 |
| frontend | + github, playwright, magic | ~9,600 |
| fullstack | + github, playwright, postgres | ~10,800 |
| e-commerce | + github, paypal, postgres | ~11,500 |
| content | + github, wpcom-mcp | ~8,800 |
| testing | + playwright | ~6,800 |

## Example Dialog

User: /mcps
Assistant: "Let me check your current MCP configuration..."
[Runs claude mcp list]
"You have 7 MCPs enabled, using approximately 14,800 tokens of context.

What type of project are you working on?"
[Shows AskUserQuestion with project types]

User selects: Python Backend
Assistant: "For Python Backend, I recommend:
- Keep: task-master-ai, context7, github, postgres
- Disable: paypal, wpcom-mcp, canva-dev, magic, playwright

This will save ~7,300 tokens. Shall I apply this configuration?"