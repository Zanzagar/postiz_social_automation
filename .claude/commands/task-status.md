Update the status of a Taskmaster task.

Usage: `/task-status <id> <status> [tag]`

Example: `/task-status 3 done master`

Valid statuses: `pending`, `in-progress`, `done`, `blocked`, `review`, `deferred`, `cancelled`

Execute:
```bash
task-master set-status $ARGUMENTS
```
