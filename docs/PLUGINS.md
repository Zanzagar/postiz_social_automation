# Claude Code Plugins

This project template supports plugins from multiple sources:

- **[wshobson/agents](https://github.com/wshobson/agents)** — 65+ specialized agents, commands, and skills for development domains
- **[anthropics/skills](https://github.com/anthropics/skills)** — Official Anthropic skills including document processing (PDF, DOCX, PPTX, XLSX)

## Why Plugins?

Plugins provide domain-specific expertise without bloating every conversation with unused context. The system is designed with **token efficiency** in mind:

- **Isolated Loading**: Each plugin loads only its own agents/skills (~200-400 tokens)
- **On-Demand**: Install only what you need for your project
- **Presets**: Curated combinations for common project types

## Quick Start

### Interactive Selection (Recommended)

Use the slash command to interactively select plugins:

```
/plugins
```

Or run the shell script:

```bash
./scripts/manage-plugins.sh select
```

### Using Presets

Install a preset for your project type:

```bash
# List available presets
./scripts/manage-plugins.sh list

# Install via interactive preset selection
./scripts/manage-plugins.sh install-preset
```

Available presets:

| Preset | Description | Est. Tokens |
|--------|-------------|-------------|
| `python-web` | Full Python web stack | ~1,360 |
| `fullstack-js` | Complete JS/TS stack | ~1,480 |
| `devops-sre` | Infrastructure & reliability | ~1,500 |
| `security-focused` | Security scanning & compliance | ~1,100 |
| `ai-ml-engineer` | LLM apps, MLOps, data | ~1,270 |
| `minimal` | Just the essentials | ~540 |

### Individual Plugin Installation

```bash
# Install a specific plugin
./scripts/manage-plugins.sh install python-development

# Get plugin info before installing
./scripts/manage-plugins.sh info kubernetes-operations
```

## Available Plugin Categories

### Python Development
- `python-development` - Python 3.12+ with uv, ruff, pytest, async patterns

### JavaScript/TypeScript
- `javascript-typescript` - Modern JS/TS, React, Vue, Node.js

### Backend Development
- `backend-development` - API design, authentication, caching
- `database-design` - Schema design, query optimization
- `database-migrations` - Safe migrations, rollback patterns

### Frontend & Mobile
- `frontend-mobile-development` - React Native, Flutter, responsive design
- `multi-platform-apps` - Electron, Tauri cross-platform

### DevOps & Infrastructure
- `cicd-automation` - GitHub Actions, GitLab CI, pipelines
- `kubernetes-operations` - K8s deployment, scaling, troubleshooting
- `cloud-infrastructure` - AWS, GCP, Azure, Terraform
- `observability-monitoring` - Logging, metrics, tracing

### Code Quality & Testing
- `code-review-ai` - Automated code review
- `unit-testing` - Testing strategies, mocking
- `tdd-workflows` - Test-driven development
- `debugging-toolkit` - Advanced debugging tools

### Security & Compliance
- `security-scanning` - SAST, DAST, dependency scanning
- `security-compliance` - SOC2, GDPR, HIPAA patterns
- `incident-response` - Security incident handling

### AI/ML & Data
- `llm-application-dev` - LLM apps, RAG, prompt engineering
- `machine-learning-ops` - Model deployment, MLOps
- `data-engineering` - Data pipelines, ETL

### Documentation & APIs
- `api-scaffolding` - OpenAPI, GraphQL design
- `documentation-generation` - Automated docs
- `c4-architecture` - Architecture diagrams

### Specialized Domains
- `blockchain-web3` - Smart contracts, DeFi
- `game-development` - Unity, Unreal, game architecture
- `quantitative-trading` - Algorithmic trading
- `systems-programming` - Rust, C/C++, low-level systems

## Managing Installed Plugins

```bash
# List installed plugins
./scripts/manage-plugins.sh list-installed

# Remove a plugin
./scripts/manage-plugins.sh remove python-development
```

## Using Claude Code's Native Plugin System

Claude Code has a built-in `/plugin` command that provides official plugin management:

### Official /plugin Commands

```bash
# List installed plugins
/plugin list

# Search marketplace
/plugin search <query>

# Install from marketplace
/plugin install <plugin-name>

# Install from GitHub repository
/plugin install github:wshobson/agents/python-development

# Remove a plugin
/plugin remove <plugin-name>

# View plugin details
/plugin info <plugin-name>

# Add a marketplace source
/plugin marketplace add wshobson/agents
```

### Official vs Template Plugin Management

| Feature | Official `/plugin` | Template Scripts |
|---------|-------------------|------------------|
| Plugin installation | Yes | Yes |
| Marketplace search | Yes | No |
| Token tracking | No | Yes |
| Interactive presets | No | Yes |
| Project-type recommendations | No | Yes |
| Installed plugin metrics | No | Yes |

**Recommendation**: Use the official `/plugin` command for individual installs, and the template's `/plugins` wizard when setting up new projects or managing token budgets.

### wshobson/agents Integration

The wshobson/agents repository works with both systems:

```bash
# Official method
/plugin marketplace add wshobson/agents
/plugin install python-development

# Template method (with token tracking)
./scripts/manage-plugins.sh install python-development
```

This project's plugin management script provides an additional layer for:
- Tracking installed plugins and token estimates
- Interactive selection based on project type
- Preset-based installation

## Token Budget Considerations

Claude Code has a context window that's shared between:
- System prompts and instructions
- Plugin agents, commands, and skills
- Your conversation history
- Code being analyzed

**Recommendations:**
1. Start with the `minimal` preset and add as needed
2. Keep total plugin tokens under 2,000 for most projects
3. Remove unused plugins with `./scripts/manage-plugins.sh remove`
4. Check current usage with `./scripts/manage-plugins.sh list-installed`

## File Structure

```
.claude/plugins/
├── registry.json        # Available plugins catalog
├── installed.json       # Tracking installed plugins
└── installed/           # Plugin reference files
    └── <plugin-id>/
        └── SOURCE.md    # Link to source repository
```

## Contributing

To add new plugins or presets to this template:

1. Update `.claude/plugins/registry.json`
2. Add the plugin to appropriate category
3. Include token estimates (check source repo)
4. Test with `./scripts/manage-plugins.sh install <plugin>`

## Anthropic Document Skills (Optional)

[Anthropic's official document processing skills](https://github.com/anthropics/skills) provide production-grade PDF, Word, PowerPoint, and Excel capabilities.

### What's Included

| Skill | Capabilities | Key Dependencies |
|-------|-------------|-----------------|
| **pdf** | Read, extract tables, fill forms, merge/split, OCR | pypdf, pdfplumber, reportlab, pdftotext |
| **docx** | Create & edit Word docs, tracked changes, comments | docx (npm), LibreOffice |
| **pptx** | Slide decks, layouts, charts, speaker notes | pptxgenjs (npm), LibreOffice |
| **xlsx** | Formulas, analysis, charts via plain English | openpyxl, pandas, LibreOffice |

### Installation

```bash
# Step 1: Add the Anthropic skills marketplace
/plugin marketplace add anthropics/skills

# Step 2: Install the document-skills package (all 4 skills)
/plugin install document-skills@anthropic-agent-skills

# Step 3: Check system dependencies
./scripts/check-doc-deps.sh --install
```

### System Dependencies

These skills require system-level software beyond Python/Node packages:

**LibreOffice** (required by DOCX, PPTX, XLSX):
```bash
# Ubuntu/Debian
sudo apt install -y libreoffice-calc libreoffice-writer libreoffice-impress

# macOS
brew install --cask libreoffice
```

**PDF tools** (required by PDF skill):
```bash
# Ubuntu/Debian
sudo apt install -y poppler-utils qpdf

# macOS
brew install poppler qpdf
```

Run `./scripts/check-doc-deps.sh --install` for a complete dependency report with install commands tailored to your system.

### Token Overhead

~800-1600 tokens (4 skills × ~200-400 tokens metadata each). Skills load on-demand — zero overhead when not triggered.

### License

These skills are **proprietary** (source-available reference implementations). Use is governed by Anthropic's Terms of Service. Do not copy skill files into other repositories — install via the official plugin mechanism only.

### Conflict Note

The `anthropic-agent-skills` marketplace also offers a `claude-api` plugin. This template already includes a `claude-api` skill (from ECC). Install only `document-skills`, not `claude-api@anthropic-agent-skills`, to avoid conflicts.

## Superpowers Plugin (Required)

[Superpowers](https://github.com/obra/superpowers) is a required component of this template. It provides workflow enforcement that complements Task Master.

### Installation

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### How It Works With Task Master

| Layer | Tool | Purpose |
|-------|------|---------|
| Task Tracking | Task Master (MCP) | WHAT to work on - tasks, dependencies, status |
| Workflow | Superpowers (Plugin) | HOW to work - TDD, debugging, code review |

**Example workflow:**
1. `task-master next` → Get next task from Task Master
2. Superpowers activates → Enforces TDD for that task
3. Write failing test (RED) → Superpowers validates
4. Write minimal code (GREEN) → Superpowers validates
5. Refactor → Superpowers validates tests still pass
6. `task-master set-status --id X --status=done` → Mark complete

### Superpowers Skills

| Skill | Purpose |
|-------|---------|
| `test-driven-development` | Strict RED-GREEN-REFACTOR enforcement |
| `systematic-debugging` | 4-phase root cause analysis |
| `brainstorming` | Structured ideation before coding |
| `writing-plans` | Break work into 2-5 minute tasks |
| `executing-plans` | Subagent dispatch per task |
| `using-git-worktrees` | Branch isolation for features |
| `requesting-code-review` | Initiate peer review |
| `receiving-code-review` | Process and address feedback |
| `finishing-a-development-branch` | Verify and merge workflow |
| `verification-before-completion` | Evidence-based completion checks |
| `subagent-driven-development` | Parallel agent task dispatch |
| `dispatching-parallel-agents` | Independent task parallelization |
| `using-superpowers` | Skill discovery and routing |
| `writing-skills` | Skill creation and verification |

### Key Enforcement Rules

**TDD (Non-negotiable):**
- Code written before failing test exists → DELETED
- Test passes immediately → Restart with proper failing test
- No "just this once" exceptions

**Debugging:**
- No fixes until root cause identified
- One variable changed at a time
- 3 failed fixes → Stop and question architecture

**Code Review:**
- Two-stage review: spec compliance, then quality
- Critical issues block progress

### Token Overhead

Estimated: ~3-5k tokens (14 skills × ~200-400 tokens each)

### Why Superpowers is Required

This template enforces a rigorous, structured workflow. Superpowers provides the enforcement mechanism:

- **Task Master** tells you WHAT to work on
- **Superpowers** ensures you work on it correctly (TDD, debugging discipline)

Without Superpowers, the template's workflow guidance becomes suggestions rather than enforcement. The ~3-5k token overhead is included in the template's token budget.

**Note**: For quick prototyping outside the main project workflow, you can temporarily disable Superpowers, but it should be re-enabled for any production code.

## Resources

- [wshobson/agents Repository](https://github.com/wshobson/agents)
- [anthropics/skills Repository](https://github.com/anthropics/skills)
- [Superpowers Repository](https://github.com/obra/superpowers)
- [Claude Code Plugin Documentation](https://docs.anthropic.com/claude-code/plugins)
