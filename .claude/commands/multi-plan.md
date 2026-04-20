Generate a plan using multiple AI models in parallel for diverse perspectives.

Usage: `/multi-plan <requirements>`

Arguments: $ARGUMENTS

## How It Works

This command queries Gemini and OpenAI in addition to Claude for genuinely different perspectives on your planning problem. If API keys are missing, those models are skipped and Claude provides all perspectives (with a note).

## Step 1: Check Available Models

Run this first:
```bash
python3 scripts/multi-model-query.py --check
```

## Step 2: Generate Your Analysis (Claude)

Analyze the requirements yourself first. Cover:
- Architecture and component design
- Security considerations and threat model
- Testing strategy
- Risk assessment

## Step 3: Query External Models (in parallel)

Run both queries in parallel using the Bash tool. Use the requirements from $ARGUMENTS as the prompt context.

**Gemini** — ask for alternative perspectives:
```bash
python3 scripts/multi-model-query.py --model gemini \
  --role "You are a senior software architect reviewing a design proposal. Focus on: alternative approaches the team may not have considered, scalability concerns, and different trade-offs. Be concise and specific." \
  --prompt "Review this proposal and suggest alternatives:\n\n$ARGUMENTS"
```

**OpenAI (GPT)** — ask for implementation patterns:
```bash
python3 scripts/multi-model-query.py --model openai \
  --role "You are a pragmatic senior engineer focused on implementation. Focus on: specific libraries and APIs to use, concrete code patterns, practical gotchas, and boilerplate that will be needed. Be concise and specific." \
  --prompt "Suggest implementation details for:\n\n$ARGUMENTS"
```

If a model returns `"available": false`, skip it and note in the output.

## Step 4: Synthesize

Combine all perspectives into the output format below. For each model that responded, use their ACTUAL response — do not simulate or rephrase. For models that were unavailable, note this clearly.

## Output Format

```markdown
# Multi-Model Plan: [Feature Name]

## Claude Analysis (Primary)
### Architecture
[Your own analysis]
### Security Considerations
[Your own analysis]
### Testing Strategy
[Your own analysis]

## Gemini Perspective
[ACTUAL Gemini response, or "Gemini unavailable (GOOGLE_AI_KEY not set)"]

## GPT Perspective
[ACTUAL GPT response, or "GPT unavailable (OPENAI_API_KEY not set)"]

## Synthesis
### Unified Plan
[Merged plan incorporating best of all available perspectives]

### Conflicts & Resolutions
| Topic | Claude | Gemini | GPT | Resolution |
|-------|--------|--------|-----|------------|
| [Area] | [View] | [View] | [View] | [Decision] |

### Confidence Assessment
- High confidence: [Areas where available models agree]
- Decision needed: [Areas of disagreement]
- Models consulted: [list which were available]
```

## API Configuration

Required environment variables (in `.env`):
```bash
GOOGLE_AI_KEY=your_google_ai_key    # Gemini
OPENAI_API_KEY=your_openai_key      # GPT
```

See `.claude/examples/multi-model-config.json` for setup details.

## Graceful Degradation

- **Missing GOOGLE_AI_KEY**: Skip Gemini, note in output
- **Missing OPENAI_API_KEY**: Skip GPT, note in output
- **Both missing**: Run Claude-only analysis with note that this is single-model
- **API error**: Note the error, continue with available models
