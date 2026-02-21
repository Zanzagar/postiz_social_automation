---
name: iterative-retrieval
description: Progressive context refinement for large codebases - breadth-first exploration, then depth-first analysis
---

# Iterative Retrieval

A structured approach to understanding unfamiliar code without overwhelming the context window. Instead of reading everything at once, progressively refine your understanding.

## The Problem

Large codebases (100+ files) can't be loaded into context entirely. Naive approaches either:
- Read too many files → context overflow, quality degradation
- Read too few files → miss critical connections, wrong assumptions

## The Solution: Three-Phase Retrieval

### Phase 1: Survey (Breadth-First)

**Goal:** Understand the landscape without reading file contents.

```
Tools: Glob, project-index.json, directory listings
Token cost: ~500-1,000 tokens
Time: 30 seconds
```

**Actions:**
1. Read project structure (Glob for `**/*.py`, `**/*.ts`, etc.)
2. Check project-index.json if available
3. Identify entry points (`main.py`, `app.py`, `index.ts`, `cmd/`)
4. Note test locations (`tests/`, `*_test.go`, `*.spec.ts`)
5. Check configuration files (`pyproject.toml`, `package.json`, `go.mod`)

**Output:** Mental map of module boundaries and entry points.

### Phase 2: Reconnaissance (Targeted Grep)

**Goal:** Find specific patterns, connections, and hot spots.

```
Tools: Grep (files_with_matches mode), targeted Reads (first 30 lines)
Token cost: ~1,000-3,000 tokens
Time: 1-2 minutes
```

**Actions:**
1. Grep for the specific feature/pattern you're investigating
2. Read file headers (imports, class definitions) — not full files
3. Trace the call chain: entry point → handler → service → repository
4. Identify shared dependencies and cross-cutting concerns
5. Note files that appear in multiple grep results (high-connectivity nodes)

**Techniques:**
```
# Find where a function is defined
Grep: "def process_payment" or "func ProcessPayment"

# Find where it's called
Grep: "process_payment(" or "ProcessPayment("

# Find related tests
Grep: "test.*process_payment" or "TestProcessPayment"

# Find configuration
Grep: "PAYMENT" in config files
```

**Output:** Shortlist of 3-7 files that are actually relevant.

### Phase 3: Deep Read (Depth-First)

**Goal:** Fully understand the relevant code.

```
Tools: Read (full files), targeted line ranges
Token cost: ~2,000-10,000 tokens (controlled)
Time: 2-5 minutes
```

**Actions:**
1. Read the shortlisted files fully (from Phase 2)
2. Understand data flow and transformations
3. Identify edge cases, error handling, and invariants
4. Check tests for expected behavior and documented assumptions
5. Note TODO comments, known limitations, tech debt

**Output:** Deep understanding of the specific area, ready to implement.

## Decision Framework

### When to Use Each Phase

| Situation | Start At | Depth Needed |
|-----------|----------|--------------|
| "Fix bug in module X" | Phase 2 (you know where) | Phase 3 on 2-3 files |
| "Add feature to existing system" | Phase 1 (understand boundaries) | Phase 3 on relevant module |
| "Onboard to new codebase" | Phase 1 (full survey) | Phase 2 across modules |
| "Review PR with 5 files" | Phase 3 (files are known) | Deep read all 5 |
| "Investigate performance issue" | Phase 2 (grep for hot paths) | Phase 3 + profiling |

### When to Stop Retrieving

Stop reading more files when:
- You can explain the data flow end-to-end
- You know where your change needs to go
- You've seen the test patterns for this area
- Further reading returns diminishing information

**Rule of thumb:** If you've read 10+ files and still don't understand the flow, you're probably missing an architectural pattern — grep for it rather than reading more files.

## Context Budget Management

### Token Cost by Action

| Action | Tokens | When to Use |
|--------|--------|-------------|
| `Glob **/*.py` | ~50-200 | Always (Phase 1) |
| `Grep pattern` (files_with_matches) | ~50-100 | Always (Phase 2) |
| `Grep pattern` (content, 3 lines context) | ~200-1,000 | When you need surrounding code |
| `Read file` (full, 200-line file) | ~1,000-2,000 | Phase 3, confirmed relevant files |
| `Read file` (full, 500-line file) | ~3,000-5,000 | Only if critical path |
| Sub-agent exploration | ~5,000-15,000 | Large codebases, isolated research |

### Budget Allocation

For a typical investigation with ~15,000 token budget:

```
Phase 1: Survey          ~1,000 tokens  (7%)
Phase 2: Reconnaissance  ~3,000 tokens  (20%)
Phase 3: Deep Read       ~8,000 tokens  (53%)
Buffer for iteration     ~3,000 tokens  (20%)
```

### When to Spawn Sub-Agents

Use a sub-agent (Task tool) when:
- You need to explore a module unrelated to your main task
- The exploration might consume >5,000 tokens
- You want the findings summarized, not the raw content
- You're comparing multiple approaches across the codebase

```
Main context: keeps working on implementation
Sub-agent: explores module X, returns 500-token summary
Net savings: ~4,500 tokens vs reading directly
```

## Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| Reading every file in a directory | Grep first, read only matching files |
| Reading 1,000-line files fully | Read specific line ranges or use Grep with context |
| Starting with Phase 3 on unknown code | Always survey first (Phase 1) |
| Re-reading files already in context | Reference earlier reads, don't re-read |
| Loading entire test suites | Read only tests for the specific feature |
| Ignoring project-index.json | Check it first — it's a pre-computed map |

## Integration with Project Index

If `project-index.sh` hook is enabled, `.claude/project-index.json` provides:
- File listing with modification times
- Module structure
- Entry points

**Use this as your Phase 1 accelerator** — skip manual Glob when the index exists.

## Example Workflow

```
Task: "Fix the authentication timeout bug"

Phase 1 (30s):
  Glob: **/*auth*.py → found src/auth/, src/middleware/auth.py, tests/test_auth.py
  Read: project-index.json → auth module has 4 files

Phase 2 (1 min):
  Grep: "timeout" in src/auth/ → found in token_validator.py:42, session.py:88
  Grep: "TOKEN_EXPIRY" → found in config.py:15, token_validator.py:10
  Read: token_validator.py first 50 lines → see the timeout logic

Phase 3 (3 min):
  Read: token_validator.py fully (180 lines) → found the bug at line 42
  Read: test_auth.py → no test for timeout edge case
  Read: config.py lines 10-20 → confirm default timeout value

Total tokens used: ~4,000
Files read fully: 2 (not 15)
```
