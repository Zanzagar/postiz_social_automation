Execute implementation tasks using multiple AI models in parallel.

Usage: `/multi-execute <task-description>`

Arguments: $ARGUMENTS

## Division of Work

| Model | Responsibility | Best For |
|-------|---------------|----------|
| **Claude** | Core logic, complex algorithms, integration | Reasoning-heavy code |
| **Gemini** | Alternative implementations, edge cases | Different perspectives |
| **Codex/GPT** | Boilerplate, API integrations, scaffolding | Fast code generation |

## Process

### 1. Task Decomposition
Break the task into components suitable for parallel execution:
- Core logic components (Claude)
- Boilerplate/scaffolding (Codex)
- Alternative approaches for comparison (Gemini)

### 2. Parallel Execution
Each model works on its assigned components independently.

### 3. Merge (Claude)
Claude reviews all outputs and synthesizes:
- Select best approach per component
- Ensure consistency across merged code
- Resolve conflicts between implementations
- Run tests on merged result

## Output Format

```markdown
# Multi-Model Execution: [Task]

## Component Implementations

### Core Logic (Claude)
```[language]
[implementation]
```

### Alternative Approach (Gemini)
[If different/better than Claude's version]

### Scaffolding (Codex)
```[language]
[boilerplate, types, interfaces]
```

## Merged Implementation
```[language]
[final synthesized code]
```

## Selection Rationale
- Core: Used Claude's approach because [reason]
- Types: Used Codex's scaffolding because [reason]
- Edge case from Gemini incorporated: [what and why]

## Verification
- [ ] Tests pass
- [ ] No merge conflicts
- [ ] Consistent style
```

## API Configuration

Same as `/multi-plan` — requires `GOOGLE_AI_KEY` and/or `OPENAI_API_KEY` in `.env`.

## Graceful Degradation

Same as `/multi-plan`:
- Missing API keys → skip that model, Claude handles everything
- API errors → retry once, then skip with note
- Single-model fallback is always Claude

## When to Use

- **Use `/multi-execute`**: Complex features with multiple components
- **Use regular implementation**: Simple features, bug fixes, refactoring
- **Use after `/multi-plan`**: Plan approved, ready to implement with multiple perspectives
