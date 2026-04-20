List Taskmaster tasks for the current or specified tag.

Usage:
- `/tasks` — list tasks for current tag
- `/tasks <tag-name>` — list tasks for a specific tag
- `/tasks ready` — show only actionable tasks (dependencies satisfied)
- `/tasks blocking` — show tasks on the critical path
- `/tasks compact` — minimal one-line output (fewer tokens)
- `/tasks all` — include subtasks in output

If no tag specified, uses current tag from `.taskmaster/state.json`.

Execute based on arguments:

If `$ARGUMENTS` is "ready":
```bash
task-master list --ready
```

If `$ARGUMENTS` is "blocking":
```bash
task-master list --blocking
```

If `$ARGUMENTS` is "compact":
```bash
task-master list -c
```

If `$ARGUMENTS` is "all":
```bash
task-master list --with-subtasks
```

If `$ARGUMENTS` is empty (no arguments provided):
```bash
task-master list
```

Otherwise (treat as tag name):
```bash
task-master list --tag $ARGUMENTS --with-subtasks
```
