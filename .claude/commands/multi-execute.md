Execute implementation tasks using multiple AI models in parallel.

Usage: `/multi-execute <task-description>`

Arguments: $ARGUMENTS

## How It Works

This command queries Gemini and OpenAI for alternative implementation approaches, then Claude synthesizes the best solution. If API keys are missing, those models are skipped and Claude handles everything (with a note).

## Step 1: Check Available Models

```bash
python3 scripts/multi-model-query.py --check
```

## Step 2: Decompose the Task

Break the task ($ARGUMENTS) into components:
- Core logic (Claude handles directly)
- Areas where alternative approaches would be valuable (query external models)

## Step 3: Query External Models (in parallel)

Run both queries in parallel using the Bash tool.

**Gemini** — alternative implementation:
```bash
python3 scripts/multi-model-query.py --model gemini \
  --role "You are a senior engineer providing an alternative implementation approach. Write actual code, not pseudocode. Focus on: different design patterns, edge case handling, and approaches the primary developer might not consider." \
  --prompt "Provide an alternative implementation for:\n\n$ARGUMENTS"
```

**OpenAI (GPT)** — scaffolding and boilerplate:
```bash
python3 scripts/multi-model-query.py --model openai \
  --role "You are a pragmatic engineer focused on scaffolding and integration. Write actual code. Focus on: type definitions, interfaces, API integration boilerplate, configuration, and error handling patterns." \
  --prompt "Generate scaffolding and boilerplate code for:\n\n$ARGUMENTS"
```

If a model returns `"available": false`, skip it and note in the output.

## Step 4: Implement and Merge

1. Write your own implementation (core logic)
2. Review external model responses for useful patterns
3. Incorporate the best ideas from each model
4. Ensure consistency across merged code
5. Write tests for the final implementation

## Output Format

```markdown
# Multi-Model Execution: [Task]

## Component Implementations

### Core Logic (Claude)
[Your implementation]

### Alternative Approach (Gemini)
[ACTUAL Gemini response, or "Gemini unavailable"]

### Scaffolding (GPT)
[ACTUAL GPT response, or "GPT unavailable"]

## Merged Implementation
[Final synthesized code incorporating best of all approaches]

## Selection Rationale
- [What was used from each model and why]
- Models consulted: [list which were available]

## Verification
- [ ] Tests pass
- [ ] No merge conflicts
- [ ] Consistent style
```

## API Configuration

Same as `/multi-plan` — requires `GOOGLE_AI_KEY` and/or `OPENAI_API_KEY` in `.env`.

## Graceful Degradation

- Missing API keys → skip that model, Claude handles everything
- API errors → note error, continue with available models
- Single-model fallback is always Claude

## When to Use

- **Use `/multi-execute`**: Complex features where alternative perspectives add value
- **Use regular implementation**: Simple features, bug fixes, refactoring
- **Use after `/multi-plan`**: Plan approved, ready to implement with diverse input
