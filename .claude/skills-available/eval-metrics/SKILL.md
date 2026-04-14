---
name: eval-metrics
description: pass@k capability and pass^k regression evaluation frameworks for development and production
---

# Eval Metrics

Two complementary evaluation frameworks for AI-assisted development. Use pass@k during development (can we get it right?) and pass^k for production (is it reliably right?).

## pass@k (Development — Capability)

**Definition**: At least ONE of k attempts succeeds.

Measures whether a task is *achievable* with the current model/approach, even if it takes multiple tries.

### When to Use

- Feature implementation (can the model build this?)
- Bug fixes (can it find and fix the issue?)
- Refactoring (can it restructure without breaking?)
- Any task where retrying is acceptable

### Probability

| Metric | Formula | p=0.5 | p=0.7 | p=0.9 |
|--------|---------|-------|-------|-------|
| pass@1 | p | 50% | 70% | 90% |
| pass@3 | 1-(1-p)^3 | 87.5% | 97.3% | 99.9% |
| pass@5 | 1-(1-p)^5 | 96.9% | 99.8% | ~100% |

**Interpretation**: Even a 50% per-attempt success rate gives 97% success with 5 attempts. The cost of retrying is often lower than the cost of switching to a more capable (expensive) model.

### Practical Application

```
Task: "Implement JWT auth middleware"
pass@1 with sonnet: 70% (sometimes misses edge cases)
pass@3 with sonnet: 97% (retry catches edge cases)
pass@1 with opus: 92% (better first-try but 5x cost)

Decision: Use sonnet with up to 3 attempts — cheaper AND more reliable than opus@1
```

## pass^k (Production — Regression)

**Definition**: ALL k consecutive attempts must succeed.

Measures whether a behavior is *consistently reliable* — the standard for production code, CI gates, and security checks.

### When to Use

- API contract verification (must always return correct schema)
- Data integrity checks (must never corrupt data)
- Security validations (must always catch the vulnerability)
- CI pipeline gates (must pass every time, not just sometimes)

### Probability

| Metric | Formula | p=0.9 | p=0.95 | p=0.99 |
|--------|---------|-------|--------|--------|
| pass^1 | p | 90% | 95% | 99% |
| pass^3 | p^3 | 72.9% | 85.7% | 97.0% |
| pass^5 | p^5 | 59.0% | 77.4% | 95.1% |
| pass^10 | p^10 | 34.9% | 59.9% | 90.4% |

**Interpretation**: Even 90% per-run reliability drops to 35% over 10 consecutive runs. Production systems need pass^k > 95%, which requires per-run reliability of 99%+.

### Practical Application

```
Test: "Security audit catches SQL injection"
pass^1: 95% (catches it almost every time)
pass^5: 77% (misses it 1 in 4 five-run sequences)

Action: This is NOT production-ready. Add deterministic checks
(regex patterns, AST analysis) alongside AI review.
```

## Integration with /eval Command

The template's `/eval` command tracks both metrics:

```bash
/eval                    # Run current eval suite
/eval --save             # Save results for trend tracking
```

### Defining Feature-Level Evals

For each feature, define both capability and regression criteria:

```markdown
## Feature: User Authentication

### Capability (pass@k, development)
- [ ] Generates valid JWT tokens
- [ ] Handles refresh token rotation
- [ ] Rejects expired tokens

### Regression (pass^k, production)
- [ ] Token validation never accepts expired tokens (pass^10 required)
- [ ] Rate limiting always activates at threshold (pass^5 required)
- [ ] Password hashing always uses bcrypt (pass^10 required)
```

## Decision Framework

| Scenario | Metric | Threshold | Action if Below |
|----------|--------|-----------|-----------------|
| Can the model do this at all? | pass@3 | > 80% | Switch model or approach |
| Is this reliable enough for CI? | pass^5 | > 95% | Add deterministic checks |
| Is this safe for production? | pass^10 | > 90% | Don't rely solely on AI |
| Should we retry or escalate? | pass@1 | < 50% | Escalate model tier |
