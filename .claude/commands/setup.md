# Project Setup Wizard

Guided setup for new projects or integrating the template into existing projects.

## Instructions

Run this command when starting a new project or adopting the template into an existing codebase.

### Preset Mode (Fast Path)

If the user runs `/setup preset <name>`, skip the interactive wizard and apply a project-type preset directly.

**Available presets:** `python-fastapi`, `node-nextjs`, `go-api`, `java-spring`, `python-data-science`

#### If `/setup preset` (no name):
List available presets by running:
```bash
./scripts/setup-preset.sh --list
```

#### If `/setup preset <name>`:
1. Ask the user for a **project name** (default: current directory name)
2. Show a preview of what will be created:
   ```bash
   ./scripts/setup-preset.sh <name> --dry-run
   ```
3. After user confirms, apply the preset:
   ```bash
   ./scripts/setup-preset.sh <name> --name "<project-name>"
   ```
4. Initialize Taskmaster if not already done:
   ```bash
   task-master init
   ```
5. Show the summary and suggest next steps (create PRD, generate tasks)

**Note:** Presets are also available directly from the CLI:
```bash
./scripts/setup-preset.sh <preset-name> [--dry-run] [--force] [--name <name>]
```

---

### Step 0: Initialize Local `.claude/` Structure

Before anything else, ensure the project has locally-registered commands and skills. Claude Code only registers commands and skills from LOCAL `.claude/` directories — parent-directory inheritance works for rules and CLAUDE.md, but NOT for commands or skills. Without this step, all slash commands will fail with "Unknown skill".

```bash
# Check for local commands dir (directory or symlink)
test -d .claude/commands -o -L .claude/commands && echo "commands: OK" || echo "commands: MISSING"
test -d .claude/skills -o -L .claude/skills && echo "skills: OK" || echo "skills: MISSING"
```

If either is missing:

1. **If `scripts/init-project.sh` exists** (project is within or has the template scripts):
   ```bash
   ./scripts/init-project.sh
   ```
   This auto-detects whether to create symlinks (nested project) or copies (standalone).

2. **If `scripts/init-project.sh` doesn't exist** (standalone project without scripts):
   - Ask the user: "Where is the project-template? (local path or git URL)"
   - If local path: `TEMPLATE_PATH=/path/to/template ./scripts/init-project.sh`
   - If git URL: Clone the template to a temp dir and copy `.claude/` subdirectories (commands, skills, agents, contexts, hooks)

If both are already present, skip to Step 1.

---

### Step 1: Detect Project State

Check what already exists:

```bash
# Check for existing code
ls -la src/ tests/ 2>/dev/null || echo "No src/tests directories"

# Check for Taskmaster
ls -la .taskmaster/ 2>/dev/null || echo "Taskmaster not initialized"

# Check CLAUDE.md status
grep -q "\[PROJECT_NAME\]" CLAUDE.md && echo "CLAUDE.md needs customization" || echo "CLAUDE.md customized"

# Check git status
git status --short 2>/dev/null || echo "Not a git repository"
```

### Step 2: Determine Scenario

Based on detection, identify the scenario:

| Scenario | Indicators | Action |
|----------|------------|--------|
| **New Project** | No src/, no .taskmaster/, placeholder CLAUDE.md | Full setup |
| **Adopting Template** | Has src/ or code, no .taskmaster/ | Careful integration |
| **Already Setup** | Has .taskmaster/, customized CLAUDE.md | Health check only |

### Step 3: Gather Project Information (for New/Adopting)

Use AskUserQuestion to gather:

1. **Project name** - What is this project called?
2. **Project description** - One-line description
3. **Tech stack** - Python/JavaScript/Go/Rust/Other
4. **Project type** - Backend API / Frontend / Full-stack / CLI / Library / Data/ML
5. **Database needs** - PostgreSQL / MongoDB / SQLite / None

**Preset suggestion:** After gathering project type and tech stack, check if a preset matches:

| Project Type + Stack | Suggested Preset |
|---------------------|------------------|
| Backend API + Python + FastAPI | `python-fastapi` |
| Full-stack + JavaScript/TypeScript + Next.js | `node-nextjs` |
| Backend API + Go | `go-api` |
| Backend API + Java + Spring | `java-spring` |
| Data/ML + Python | `python-data-science` |

If a preset matches, suggest: "A preset is available for this stack. Run `/setup preset <name>` for one-command setup, or continue with manual configuration?"

### Step 4: Execute Setup

#### For New Projects:

1. **Update CLAUDE.md**:
   - Replace `[PROJECT_NAME]` with actual name
   - Fill in tech stack section
   - Add project-specific patterns

2. **Initialize Taskmaster**:
   ```bash
   task-master init
   ```

3. **Create project structure** (if needed):
   ```bash
   mkdir -p src tests docs
   ```

4. **Initialize git** (if not already):
   ```bash
   git init
   git add .
   git commit -m "chore: Initial project setup"
   ```

5. **Configure MCPs**:
   - Run `/mcps` with recommended preset based on project type

6. **Create initial PRD placeholder**:
   - Create `.taskmaster/docs/prd.txt` with project description

#### For Adopting Template:

1. **Preserve existing work** - DO NOT modify existing code

1.5. **Initialize `.claude/` structure** (if not already done by Step 0):
   ```bash
   ./scripts/init-project.sh
   ```
   Creates symlinks (nested) or copies (standalone) for commands, skills, agents, contexts, and hooks.

2. **Update CLAUDE.md**:
   - Customize with existing project details
   - Document existing patterns found in codebase

3. **Initialize Taskmaster**:
   ```bash
   task-master init
   ```

4. **Analyze existing codebase**:
   - Identify main modules/packages
   - Note existing testing patterns
   - Document current git workflow

5. **Create catch-up tasks** in Taskmaster:
   - "Document existing architecture"
   - "Add missing tests for core modules"
   - "Set up CI/CD if not present"

6. **Configure MCPs** based on detected tech stack

### Step 5: Create Project State File

After setup, create `.claude/project-state.json`:

```json
{
  "initialized_at": "2024-01-15T10:30:00Z",
  "scenario": "new|adopting|existing",
  "project_name": "My Project",
  "tech_stack": ["python", "fastapi", "postgresql"],
  "project_type": "backend",
  "setup_complete": true,
  "onboarding_steps_completed": [
    "claude_md_customized",
    "taskmaster_initialized",
    "mcps_configured",
    "git_initialized"
  ]
}
```

### Step 6: Final Checklist

Present a summary:

```
✅ Setup Complete!

Project: {name}
Type: {type}
Tech Stack: {stack}

Completed:
  ✓ CLAUDE.md customized
  ✓ Taskmaster initialized
  ✓ MCPs configured ({preset})
  ✓ Git repository ready

Next Steps:
  1. Create your PRD: .taskmaster/docs/prd.txt
  2. Generate tasks: task-master parse-prd
  3. Start coding: task-master next
```

## For Research Groups

When setting up for a research group:

1. **Standardize CLAUDE.md sections** for the group
2. **Pre-configure MCPs** commonly used by the group
3. **Create shared PRD templates** for common project types
4. **Document group-specific conventions** in CLAUDE.md

## Re-running Setup

If user runs `/setup` on an already-configured project:

1. Show current configuration
2. Offer to reconfigure specific aspects:
   - "Update CLAUDE.md?"
   - "Reconfigure MCPs?"
   - "Reset Taskmaster?" (with warning)
