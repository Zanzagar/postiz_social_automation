Invoke the planner agent to create a comprehensive implementation plan before writing any code.

Usage: `/plan <requirements>`

Arguments: $ARGUMENTS

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## How It Works

The planner agent will:

1. **Analyze the request** and restate requirements in clear terms
2. **Break down into phases** with specific, actionable steps
3. **Identify dependencies** between components
4. **Assess risks** and potential blockers
5. **Estimate complexity** (High/Medium/Low)
6. **Present the plan** and WAIT for explicit confirmation

**CRITICAL**: The planner agent will **NOT** write any code until you explicitly confirm the plan.

If you want changes, respond with:
- "modify: [your changes]"
- "different approach: [alternative]"
- "skip phase 2 and do phase 3 first"

## When to Use

- Starting a new feature
- Making significant architectural changes
- Complex refactoring across multiple files
- Requirements are unclear or ambiguous
- Multiple valid approaches exist

## Output Format

```
# Implementation Plan: [Title]

## Requirements Restatement
[Clear restatement of what needs to be built]

## Implementation Phases
### Phase 1: [Name]
- [Step 1]
- [Step 2]

### Phase 2: [Name]
...

## Dependencies
- [Dependency 1]
- [Dependency 2]

## Risks
- HIGH: [Risk description]
- MEDIUM: [Risk description]
- LOW: [Risk description]

## Estimated Complexity: [HIGH/MEDIUM/LOW]

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Integration with Other Commands

After planning:
- Use `/tdd` to implement with test-driven development
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed implementation
- Use `/orchestrate feature` for the full pipeline

## Agent

Invokes the **planner** agent (opus, read-only).
