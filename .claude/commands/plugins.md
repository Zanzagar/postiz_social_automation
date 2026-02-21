# Plugin Selection Wizard

Help the user select and install appropriate plugins from the wshobson/agents repository based on their project needs.

## Instructions

1. First, read the plugin registry to understand available options:
   - Read `.claude/plugins/registry.json` for categories and plugins
   - Read `.claude/plugins/installed.json` if it exists to see current state

2. Ask the user about their project type using AskUserQuestion with these options:

**Question: "What type of project are you working on?"**
- Python Web Development (FastAPI, Django, Flask)
- JavaScript/TypeScript Full-Stack (React, Vue, Node.js)
- DevOps & Infrastructure (Kubernetes, CI/CD, Cloud)
- AI/ML Engineering (LLMs, MLOps, Data pipelines)
- Security-Focused Development
- Custom Selection (choose individual plugins)
- Minimal (just essentials)

3. Based on their selection:
   - Show the recommended preset from the registry
   - Display the plugins that will be installed with estimated token counts
   - Explain what each plugin provides (agents, skills)

4. Confirm installation and run:
   ```bash
   ./scripts/manage-plugins.sh install <plugin-id>
   ```
   for each selected plugin.

5. After installation, provide guidance on:
   - How to use the native Claude Code plugin system (`/plugin marketplace add wshobson/agents`)
   - Where plugin references are stored (`.claude/plugins/installed/`)
   - How to remove plugins if needed

## Token Budget Guidance

Explain to the user:
- Each plugin adds ~200-400 tokens to context
- More plugins = less room for conversation context
- Recommend starting minimal and adding as needed
- Presets are optimized combinations for common workflows

## Example Dialog

User: /plugins
Assistant: "I'll help you select plugins for your project. Let me first check what's currently installed..."
[Reads registry and installed.json]
"You currently have 2 plugins installed (~500 tokens).

What type of project are you working on?"
[Shows AskUserQuestion with options]

User selects: Python Web Development