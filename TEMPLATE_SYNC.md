# Template Synchronization Guide

This document explains how to keep projects created from this template updated with new features and improvements.

## Quick Start

```bash
# Check what's outdated
./scripts/sync-template.sh --check-versions

# Preview changes
./scripts/sync-template.sh --dry-run

# Apply updates (interactive)
./scripts/sync-template.sh

# Apply all updates without prompts
./scripts/sync-template.sh --force
```

## Sync Script Options

The `scripts/sync-template.sh` script supports multiple sync methods:

### From Local Template (Default)
```bash
# Uses ~/projects/project-template by default
./scripts/sync-template.sh

# Or specify a path
./scripts/sync-template.sh --template /path/to/template
```

### From Git Remote (No Local Clone Needed)
```bash
# Sync directly from GitHub
./scripts/sync-template.sh --git https://github.com/YOUR_USERNAME/project-template.git
```

### All Options
```bash
./scripts/sync-template.sh [options]

Options:
  --dry-run         Preview changes without applying
  --template PATH   Use local template path
  --git URL         Clone and sync from git URL
  --commands        Also sync .claude/commands/ files
  --all             Sync everything (rules + commands)
  --force           Overwrite without prompting
  --check-versions  Show version info for all files
  --help            Show help
```

## What Gets Synced

### Stock Rules (Always Synced)
These files should generally match the template:

| File | Purpose |
|------|---------|
| `docs/rules/git-workflow.md` | Git commands and workflow |
| `docs/rules/python-standards.md` | Python coding standards (moved to `.claude/rules/python/coding-standards.md`) |
| `docs/rules/self-improve.md` | Rule improvement guidelines |
| `docs/rules/cursor-rules-format.md` | Rule formatting guide |

### Commands (Optional, use `--commands`)
```bash
./scripts/sync-template.sh --commands
```
Syncs `.claude/commands/*.md` slash command files.

### Never Synced (Project-Specific)
- `CLAUDE.md` - Your project context
- `docs/rules/project-*.md` - Project-specific rules
- Customized versions of stock files

## Version Tracking

Each template file includes version headers:
```markdown
<!-- template-version: 1.0.0 -->
<!-- template-file: docs/rules/git-workflow.md -->
```

Check versions across your project:
```bash
./scripts/sync-template.sh --check-versions
```

## Handling Customizations

If you've customized a stock file:

1. **Check what changed:**
   ```bash
   ./scripts/sync-template.sh --dry-run
   ```

2. **View full diff:**
   When prompted, press `d` to see the complete diff

3. **Manual merge:**
   ```bash
   code --diff docs/rules/python-standards.md ~/projects/project-template/docs/rules/python-standards.md
   ```

4. **Keep your version:**
   When prompted, press `n` to skip

## Alternative: Git Remote Method

For more control, add template as a git remote:

```bash
# One-time setup
git remote add template https://github.com/YOUR_USERNAME/project-template.git

# Fetch updates
git fetch template

# View changes
git log template/main --oneline -10

# Merge specific files
git checkout template/main -- docs/rules/git-workflow.md
```

## Changelog

### Version 1.0.0 (Initial)
- git-workflow.md - Git workflow and commands
- python-standards.md - Python coding standards
- self-improve.md - Rule improvement guidelines
- cursor-rules-format.md - Rule formatting guide
- CLAUDE.md - Project context template
- sync-template.sh - Sync script with git support
