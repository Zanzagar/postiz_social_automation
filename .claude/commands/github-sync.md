---
name: github-sync
description: Sync Task Master tasks with GitHub Issues for team visibility
arguments:
  - name: action
    description: "Action: push (tasks→issues), pull (issues→tasks), status"
    required: false
---

# GitHub Task Sync

Sync Task Master tasks with GitHub Issues for team collaboration and visibility.

## Action: $ARGUMENTS.action

### If action is "push" or empty:

**Push tasks to GitHub Issues:**

1. Get current tasks from Task Master:
   ```
   Use mcp__task-master-ai__get_tasks to list all pending/in-progress tasks
   ```

2. For each task without a GitHub issue:
   - Create a GitHub issue using `gh issue create`
   - Format: `gh issue create --title "[Task ID] Task Title" --body "Task description and details"`
   - Add labels based on task type (feature, bug, chore)
   - Note the issue number in task details

3. For tasks with existing issues:
   - Update issue status via comments if task status changed
   - Close issues for completed tasks: `gh issue close <number>`

4. Report sync results

### If action is "pull":

**Pull GitHub Issues to Task Master:**

1. List open issues: `gh issue list --state open --json number,title,body,labels`

2. For each issue not in Task Master:
   - Use mcp__task-master-ai__add_task to create corresponding task
   - Include issue number in task details for linking

3. For existing linked tasks:
   - Update task status if issue was closed
   - Add any new comments as task notes

4. Report sync results

### If action is "status":

**Show sync status:**

1. Count tasks in Task Master
2. Count open issues in GitHub
3. Identify unlinked items (tasks without issues, issues without tasks)
4. Show last sync timestamp if available

## Sync Format

When creating issues from tasks:
```
Title: [TM-{id}] {task title}

Body:
## Task Details
{task description}

## Implementation Notes
{task details}

## Test Strategy
{test strategy if defined}

---
*Synced from Task Master task #{id}*
```

When creating tasks from issues:
```
Title: {issue title}
Description: {issue body}
Details: GitHub Issue #{number} - {issue url}
```

## Labels Mapping

| Task Type | GitHub Label |
|-----------|--------------|
| Feature task | `enhancement` |
| Bug fix | `bug` |
| Documentation | `documentation` |
| Refactor | `refactor` |
| Test | `testing` |

## Usage Examples

```bash
# Push all tasks to GitHub Issues
/github-sync push

# Pull new issues into Task Master
/github-sync pull

# Check sync status
/github-sync status

# Default (no args) = push
/github-sync
```

## Notes

- Requires `gh` CLI to be authenticated (`gh auth status`)
- Tasks and issues are linked by including references in descriptions
- Sync is additive - won't delete tasks or close issues automatically unless status changed
- Run `/github-sync status` first to see what will be synced
