Generate a plan using multiple AI models in parallel for diverse perspectives.

Usage: `/multi-plan <requirements>`

Arguments: $ARGUMENTS

## Model Roles

| Model | Role | Strengths |
|-------|------|-----------|
| **Claude** (primary) | Architecture, security, testing strategy | Deep reasoning, safety analysis |
| **Gemini** | Alternative perspectives, different approaches | Broad knowledge, catches different issues |
| **Codex/GPT** | Implementation focus, practical patterns | Code generation, API expertise |

## Process

### 1. Distribute Requirements
Send the same requirements to all available models.

### 2. Collect Perspectives
Each model analyzes independently:
- Claude: Architecture, risks, testing strategy, security considerations
- Gemini: Alternative approaches, scalability concerns, different trade-offs
- Codex: Implementation details, library recommendations, code patterns

### 3. Synthesize (Claude)
Claude aggregates all perspectives into a unified plan, noting:
- Where models agree (high confidence)
- Where models differ (decision point)
- Unique insights from each model

## Output Format

```markdown
# Multi-Model Plan: [Feature Name]

## Claude Analysis (Primary)
### Architecture
[Design decisions, component structure]
### Security Considerations
[Threats, mitigations]
### Testing Strategy
[What to test, approach]

## Gemini Perspective
### Alternative Approaches
[Different ways to solve this]
### Additional Concerns
[Issues Claude didn't flag]

## Codex Suggestions
### Implementation Patterns
[Specific code approaches, libraries]
### API Integration Details
[Practical implementation notes]

## Synthesis
### Unified Plan
[Merged plan incorporating best of all perspectives]

### Conflicts & Resolutions
| Topic | Claude | Gemini | Codex | Resolution |
|-------|--------|--------|-------|------------|
| [Area] | [View] | [View] | [View] | [Decision] |

### Confidence Assessment
- High confidence: [Areas where all models agree]
- Decision needed: [Areas of disagreement]
```

## API Configuration

Required environment variables (in `.env`):
```bash
GOOGLE_AI_KEY=your_google_ai_key    # Gemini
OPENAI_API_KEY=your_openai_key      # Codex/GPT
```

See `.claude/examples/multi-model-config.json` for setup details.

## Graceful Degradation

- **Missing GOOGLE_AI_KEY**: Skip Gemini, note in output
- **Missing OPENAI_API_KEY**: Skip Codex, note in output
- **Both missing**: Run Claude-only analysis with note
- **API error**: Retry once, then skip with note

```
Note: Gemini perspective unavailable (GOOGLE_AI_KEY not set).
Running with Claude + Codex only.
```
