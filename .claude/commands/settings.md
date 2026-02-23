Configure Claude Code settings for this project.

Usage:
- `/settings` - Show current settings and available presets
- `/settings fast` - Apply fast mode preset
- `/settings thorough` - Apply thorough mode preset
- `/settings safe` - Apply safe mode preset
- `/settings autoformat` - Apply auto-format mode preset
- `/settings optimized` - Apply optimized mode preset (token-efficient)

Arguments: $ARGUMENTS

## Available Presets

| Preset | Auto-Accept | Output Style | Hooks | Best For |
|--------|-------------|--------------|-------|----------|
| `fast` | Yes | Concise | None | Quick fixes, familiar code |
| `thorough` | No | Explanatory | Pre-commit | Learning, complex changes |
| `safe` | No | Explanatory | File protection + Pre-commit | Production, unfamiliar code |
| `autoformat` | Yes | Concise | Post-edit formatting | Strict style enforcement |
| `optimized` | Yes | Concise | None | Token-efficient, long sessions |

## Actions

If preset argument provided:
1. Read `.claude/settings-presets.json` for preset configuration
2. Show the user what changes will be made
3. Ask for confirmation before applying
4. Update `.claude/settings.local.json` with the preset settings
5. Inform user to restart Claude Code for changes to take effect

If no argument:
1. Read current `.claude/settings.local.json` (or report defaults)
2. Show current configuration
3. List available presets with descriptions
4. Suggest: "Use `/settings <preset>` to apply a preset"

## Token Optimization (Optimized Preset)

The `optimized` preset sets environment variables that reduce token consumption by 60-80%:

| Variable | Default | Optimized | Effect |
|----------|---------|-----------|--------|
| `MAX_THINKING_TOKENS` | 31,999 | 10,000 | Caps extended thinking budget — faster but shallower reasoning |
| `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE` | ~95% | 50% | Compacts context earlier — preserves working room but loses older context sooner |
| `CLAUDE_CODE_SUBAGENT_MODEL` | (inherits) | haiku | Uses cheaper model for sub-agents — faster exploration, slightly less capable |

**Trade-offs to consider:**
- Reduced thinking depth may miss subtle bugs in complex code
- Earlier compaction means older conversation context is summarized sooner
- Haiku sub-agents work well for search/exploration but may struggle with nuanced analysis

**When to use:** Long coding sessions, cost-conscious work, routine tasks on familiar codebases.
**When to avoid:** Complex debugging, architectural planning, unfamiliar codebases (use `thorough` instead).

Note: Environment variables take effect on the next Claude Code session. The `/settings` command will update `settings.local.json` but env vars may require a restart.

## Manual Settings

Users can also manually edit `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": ["Bash(npm:*)"],
    "deny": []
  },
  "autoAcceptEdits": true,
  "outputStyle": "Concise",
  "hooks": {
    // See .claude/hooks/README.md
  }
}
```

Note: `.claude/settings.local.json` is gitignored for personal preferences.
