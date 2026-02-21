Analyze instincts for clustering opportunities and suggest new skills.

Usage: `/evolve`

## Instructions

1. Read all instincts from `.claude/instincts/`
2. Group by category
3. Within each category, identify clusters of 3+ related instincts with confidence > 0.7
4. For each cluster, propose a new skill

### Clustering Algorithm

1. **Group**: Organize instincts by category
2. **Filter**: Keep only active instincts (confidence > 0.7)
3. **Cluster**: Within each category, find patterns that share a common theme
   - Look for overlapping keywords
   - Look for patterns that apply to the same domain
   - Look for patterns that form a workflow sequence
4. **Propose**: For each cluster of 3+, draft a SKILL.md

### Output Format

```
╔══════════════════════════════════════════════════════════╗
║                    INSTINCT EVOLUTION                     ║
╠══════════════════════════════════════════════════════════╣

Cluster 1: "API Error Handling" (debugging-approach, 4 instincts)
  - "Check HTTP status codes before parsing response" (0.85)
  - "Log request/response on 4xx/5xx errors" (0.78)
  - "Retry with exponential backoff on 429/503" (0.82)
  - "Include correlation ID in error context" (0.71)

  Proposed skill: .claude/skills/api-error-handling/SKILL.md
  Accept? [Y/n]

Cluster 2: "Test Organization" (testing-strategy, 3 instincts)
  - "Group tests by feature, not by file" (0.80)
  - "Use factory fixtures instead of raw data" (0.75)
  - "Mark slow tests with @pytest.mark.slow" (0.73)

  Proposed skill: .claude/skills/test-organization/SKILL.md
  Accept? [Y/n]

No clusters found: coding-style (only 2 active instincts)
No clusters found: tool-usage (instincts not related enough)
```

### On Accept
1. Create the skill directory and SKILL.md with the clustered patterns
2. Mark source instincts as `"active": false` (archived into skill)
3. Report: "Created skill 'api-error-handling' from 4 instincts"

### On Reject
- Skip the cluster, instincts remain active
- Report: "Skipped cluster 'API Error Handling'"

### No Clusters Found
```
No evolution opportunities found.

To evolve instincts into skills, you need:
  - 3+ instincts in the same category
  - All with confidence > 0.7
  - Conceptually related patterns

Current instinct counts:
  coding-style: 2 active (need 1 more)
  testing-strategy: 1 active (need 2 more)
  tool-usage: 0 active
```
