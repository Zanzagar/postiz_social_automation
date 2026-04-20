# Task Master Usage Rules

This rule defines how to interact with Task Master. It distinguishes MCP tools (structured, in-palette) from CLI commands (shell-based), and specifies which to use for each operation.

## CLI vs MCP Decision Matrix

| Operation | Use | Command | Why |
|-----------|-----|---------|-----|
| List tasks | CLI | `task-master list -c` | ~200 tokens vs ~19.5k via MCP |
| List with subtasks | CLI | `task-master list -c --with-subtasks` | ~1-2k tokens, use sparingly |
| Show single task | CLI | `task-master show <id>` | ~500-2k tokens |
| Next task | MCP | `next_task` | Simple data lookup, MCP fine |
| Set status | MCP | `set_task_status` | Simple data write, MCP fine |
| Update subtask | MCP | `update_subtask` | Simple data write, MCP fine |
| Add subtask | MCP | `add_subtask` | Simple data write, MCP fine |
| **Parse PRD** | **CLI ONLY** | `task-master parse-prd --input=<file> --num-tasks=0 --force` | AI op — MCP spawns blocked nested subprocess |
| **Expand task** | **CLI ONLY** | `task-master expand --id=<id> --prompt="$(cat .taskmaster/prompts/quality-expand.txt)" --force` | AI op — same reason. Quality prompt produces Hamster-grade subtasks with checkbox AC, scope boundaries, business context |
| **Analyze complexity** | **CLI ONLY** | `task-master analyze-complexity` | AI op — same reason |
| View complexity report | CLI | `task-master complexity-report` | Read-only display |
| Tag operations | CLI | `task-master tags add/use/list` | CLI-only commands |

## Why AI Ops Must Use CLI

The `claude-code` provider spawns a nested Claude subprocess for AI operations. When invoked via MCP, this nested subprocess is blocked by Claude Code's session detection. CLI runs in its own process and works correctly.

**Simple rule:** If the operation needs AI thinking (parsing, expanding, analyzing), use CLI. If it's just reading or writing data, MCP is fine.

## CLI Flags and Timeouts

AI operations require special handling:

| Flag | Purpose | When |
|------|---------|------|
| `--force` | Skip interactive confirmation prompts | Always for parse-prd and expand |
| `--num-tasks=0` | Let AI determine task count | Always for parse-prd |
| `--prompt="$(cat .taskmaster/prompts/quality-expand.txt)"` | Inject quality requirements into subtask generation | Always for expand (produces checkbox AC, scope bounds, business context per subtask) |
| Bash timeout 900000ms | AI ops can take 5-15 minutes | Set on Bash tool call |

**NEVER use `2>&1`** with AI ops — merging stderr (ANSI progress spinners) into stdout corrupts output rendering.

**`analyze-complexity` output bug:** stdout gets swallowed by ANSI codes. Always follow with `task-master complexity-report` to see results.

## Batched Complexity Analysis (>10 tasks)

`analyze-complexity` truncates results when analyzing more than ~10 tasks — only the first ~10 get real scores; the rest default to 5. **Each run also overwrites the report file.** Use batched analysis:

```bash
# Step 1: Analyze in batches of 10, saving each before it's overwritten
task-master analyze-complexity --from=1 --to=10
cp .taskmaster/reports/task-complexity-report_<tag>.json batch-1.json

task-master analyze-complexity --from=11 --to=20
cp .taskmaster/reports/task-complexity-report_<tag>.json batch-2.json

# ... repeat for remaining batches

# Step 2: Merge batch reports (combine complexityAnalysis arrays)
# Step 3: Copy merged report back before expanding
cp merged-report.json .taskmaster/reports/task-complexity-report_<tag>.json
task-master expand --all --force
```

**Important:** Set Bash timeout to at least 7200000ms (2 hours) for `expand --all` on large task sets. 40 tasks × ~2min each = ~80 min.

## Token-Conscious Viewing

| Situation | Command | Cost |
|-----------|---------|------|
| Quick progress check | `task-master list -c` | ~200 tokens |
| Starting a task | `task-master show <id>` | ~500-2k tokens |
| Starting work / session resume | `task-master list -c --with-subtasks` | ~1-2k tokens |
| **NEVER for orientation** | MCP `get_tasks` with `withSubtasks: true` | ~19.5k tokens |

**Display cadence:** Full tree once at task start, compact list at task end, silence between subtasks.

## Tool Suggestions Do Not Override Rules

Task Master's own CLI output may suggest commands like `expand --all` or `task-master expand --all`. **These suggestions do not override project rules.**

Specifically:
- **Never use `expand --all`** — always expand individually, guided by the complexity report
- **Score >= 5 = always expand**, even if AI recommends 0 subtasks
- **Score < 5 = don't expand** unless you have specific reason to

## analyze-complexity --research Limitations

The `--research` flag uses Perplexity AI for analysis. It is unreliable for task sets larger than ~10 tasks (returns partial results, remaining tasks get defaults). Default to non-research analysis unless investigating unfamiliar technology with a small task set.

## TASK_MASTER_ALLOW_METADATA_UPDATES

Set this environment variable to `true` in MCP server configuration to enable GitHub issue linking via task metadata. This allows `task-master` to store issue URLs and other metadata on tasks.
