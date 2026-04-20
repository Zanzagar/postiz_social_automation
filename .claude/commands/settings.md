Configure Claude Code settings for this project.

Usage:
- `/settings` - Show current settings and available presets
- `/settings fast` - Apply fast mode preset
- `/settings thorough` - Apply thorough mode preset
- `/settings safe` - Apply safe mode preset
- `/settings autoformat` - Apply auto-format mode preset
- `/settings minimal` - Apply minimal mode preset (lightweight hooks only)

Arguments: $ARGUMENTS

## Available Presets

| Preset | Auto-Accept | Output Style | Hooks | Best For |
|--------|-------------|--------------|-------|----------|
| `fast` | Yes | Concise | None | Quick fixes, familiar code |
| `thorough` | No | Explanatory | Pre-commit | Learning, complex changes |
| `safe` | No | Explanatory | File protection + Pre-commit | Production, unfamiliar code |
| `autoformat` | Yes | Concise | Post-edit formatting | Strict style enforcement |
| `minimal` | — | — | Minimal profile | Fast debugging, exploration |

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
