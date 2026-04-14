Show or parse a Product Requirements Document.

Usage:
- `/prd` - List available PRDs
- `/prd <name>` - Show specific PRD content

Available PRDs in `.taskmaster/docs/`:
- `prd_primary.txt` - Primary project requirements
- `prd_secondary.txt` - Secondary features
- `prd_tertiary.txt` - Tertiary/future features

Templates:
- `TEMPLATE_prd_rpg.txt` - RPG (Repository Planning Graph) method for complex multi-module projects. Separates functional/structural decomposition with explicit dependency graphs.

To generate tasks from a PRD:
```bash
task-master parse-prd --input=.taskmaster/docs/<prd_file> --num-tasks=0
```
