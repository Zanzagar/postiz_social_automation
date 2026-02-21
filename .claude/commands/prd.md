Show or parse a Product Requirements Document.

Usage:
- `/prd` - List available PRDs
- `/prd <name>` - Show specific PRD content

Available PRDs in `.taskmaster/docs/`:
- `prd_primary.txt` - Primary project requirements
- `prd_secondary.txt` - Secondary features
- `prd_tertiary.txt` - Tertiary/future features

To generate tasks from a PRD:
```bash
task-master parse-prd --file .taskmaster/docs/<prd_file>
```
