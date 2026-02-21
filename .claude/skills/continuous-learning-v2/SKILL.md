---
name: continuous-learning-v2
description: Instinct-based pattern extraction, confidence scoring, skill evolution
---
# Continuous Learning v2

## Overview

This skill enables Claude to learn from your working patterns over time. It extracts recurring behaviors into "instincts" — scored suggestions that improve with use.

**Authority**: Instincts never override rules. See `.claude/rules/authority-hierarchy.md`.

## Pattern Extraction

### When to Extract
After completing significant tasks, identify recurring patterns in:
- Tool usage (which tools you prefer, in what order)
- Coding style (naming, structure, documentation approach)
- Testing strategy (what you test, how you organize tests)
- Debugging approach (where you start, what you check)
- Architecture preferences (module layout, dependency patterns)

### Extraction Rules
- Require **2+ occurrences** before creating an instinct
- Pattern must be specific enough to be actionable
- Don't extract patterns that match existing rules (redundant)
- Don't extract one-time decisions (context-dependent, not a pattern)

### Extraction Prompt
After significant work, reflect:
```
Patterns observed this session:
1. [Pattern] — Confidence: [initial score] — Category: [category]
2. [Pattern] — Confidence: [initial score] — Category: [category]

New instincts to create: [list]
Existing instincts reinforced: [list]
```

## Instinct Format

```json
{
  "pattern": "Description of the learned behavior",
  "confidence": 0.0,
  "category": "coding-style|testing-strategy|debugging-approach|architecture-preference|tool-usage",
  "source_sessions": ["session-id-1", "session-id-2"],
  "last_reinforced": "2024-01-18T00:00:00Z",
  "active": true
}
```

### Fields
| Field | Type | Description |
|-------|------|-------------|
| `pattern` | string | Human-readable description of the behavior |
| `confidence` | float | 0.0–1.0 confidence score |
| `category` | string | One of the five categories |
| `source_sessions` | string[] | Session IDs where pattern was observed |
| `last_reinforced` | string | ISO date of last positive reinforcement |
| `active` | bool | Whether instinct is currently applied |

## Confidence Management

### Thresholds
| Range | Status | Action |
|-------|--------|--------|
| < 0.3 | Noise | Discard — too unreliable to keep |
| 0.3–0.7 | Candidate | Keep but don't auto-apply — needs reinforcement |
| > 0.7 | Active | Apply automatically as suggestion |

### Score Dynamics
| Event | Change | Example |
|-------|--------|---------|
| Pattern confirmed | +0.1 | User follows the suggested approach |
| Pattern reinforced | +0.1 | Same pattern observed in new context |
| Week unused | -0.05 | Natural decay of stale patterns |
| User rejects | -0.2 | Explicit contradiction by user |
| Rule conflict | Set to 0 | Instinct contradicts a rule — deactivate |

### Initial Confidence
- First observation: 0.4 (candidate)
- Second observation: 0.5 (candidate, strengthening)
- Third observation: 0.6 (approaching active)
- With explicit user confirmation: +0.2 bonus

## Skill Evolution

When 3+ related instincts cluster in the same category with confidence >0.7:

1. **Detection**: `/evolve` scans instincts for clusters
2. **Proposal**: Suggests a new SKILL.md combining the patterns
3. **Review**: User approves or rejects the proposed skill
4. **Creation**: Approved clusters become skills in `.claude/skills/`
5. **Cleanup**: Source instincts are archived (marked inactive)

### Clustering Criteria
- Same category
- Conceptually related (similar domain/context)
- All confidence >0.7
- At least 3 instincts in the cluster

## Storage

- Location: `.claude/instincts/*.json`
- One file per instinct (named by pattern slug)
- Personal by default (`.gitignore` excludes JSON files)
- Share via `/instinct-export` and `/instinct-import`
