---
name: eval-harness
description: Eval-driven development (EDD) framework with pass@k capability and pass^k regression metrics, code-based and model-based graders, feature-level eval definitions
---
# Eval Harness Skill

## Eval-Driven Development (EDD)

EDD extends TDD with AI-specific evaluation patterns. While TDD verifies that code works correctly, EDD verifies that AI-assisted code meets quality thresholds across multiple attempts.

## Core Metrics

### pass@k (Capability)
"Can the system produce a correct solution in k attempts?"

```
pass@k = 1 - (C(n-c, k) / C(n, k))

Where:
  n = total attempts
  c = correct attempts
  k = number of attempts allowed
```

**Example:** Generate a kriging function 10 times, 7 produce correct output.
- pass@1 = 0.70 (70% chance of correct on first try)
- pass@3 = 0.97 (97% chance at least one of three is correct)
- pass@10 = 1.00 (guaranteed correct in 10 tries)

**Use for:** Measuring whether the template + model CAN solve a problem.

### pass^k (Regression)
"Does the system produce correct solutions consistently across k runs?"

```
pass^k = (c/n)^k

Where:
  c = correct attempts
  n = total attempts
  k = required consecutive successes
```

**Example:** Same 7/10 correct rate:
- pass^1 = 0.70 (70% on any single run)
- pass^3 = 0.34 (34% chance of 3 correct in a row)
- pass^5 = 0.17 (17% chance of 5 correct in a row)

**Use for:** Measuring reliability. High pass@k but low pass^k means the system is capable but inconsistent.

## Eval Definition Format

Each feature gets an eval definition:

```yaml
# evals/kriging_pipeline.yaml
name: kriging-pipeline-eval
description: Evaluate kriging pipeline quality
version: 1

cases:
  - id: basic_spherical
    input: "Generate ordinary kriging with spherical variogram"
    graders:
      - type: code
        check: "import ast; ast.parse(output)"  # Valid Python
      - type: code
        check: "'pykrige' in output or 'OrdinaryKriging' in output"
      - type: model
        prompt: "Does this code handle CRS validation before kriging?"
        threshold: 0.8

  - id: cross_validation
    input: "Add spatial cross-validation to the pipeline"
    graders:
      - type: code
        check: "'spatial' in output.lower() and 'cv' in output.lower()"
      - type: model
        prompt: "Does this use spatial CV (block or leave-one-out) rather than random k-fold?"
        threshold: 0.9

  - id: error_handling
    input: "Handle missing values and CRS mismatches"
    graders:
      - type: code
        check: "'try' in output and 'except' in output"
      - type: model
        prompt: "Does this properly handle NaN/NoData values before variogram fitting?"
        threshold: 0.7

metrics:
  pass_at_k: [1, 3, 5]
  pass_pow_k: [1, 3]
  threshold: 0.8  # Minimum pass@1 to consider the feature working
```

## Grader Types

### Code-Based Graders
Deterministic checks on the output:

```python
# Syntax check
def grade_syntax(output: str) -> bool:
    try:
        ast.parse(output)
        return True
    except SyntaxError:
        return False

# Contains check
def grade_contains(output: str, required: list[str]) -> bool:
    return all(term in output for term in required)

# Execution check
def grade_executes(output: str) -> bool:
    try:
        exec(output, {"__builtins__": {}})
        return True
    except Exception:
        return False

# Output match
def grade_output(output: str, expected: str, tolerance: float = 0.01) -> bool:
    actual = eval(output)
    return abs(actual - float(expected)) < tolerance
```

### Model-Based Graders
Use an LLM to evaluate subjective quality:

```python
def grade_with_model(output: str, prompt: str, threshold: float) -> bool:
    response = llm.evaluate(
        system="You are a code quality evaluator. Answer YES or NO.",
        prompt=f"{prompt}\n\nCode:\n{output}",
    )
    # Parse confidence from response
    confidence = parse_yes_no_confidence(response)
    return confidence >= threshold
```

**When to use each:**

| Grader | Use When | Pros | Cons |
|--------|----------|------|------|
| Code (syntax) | Checking valid code | Deterministic, fast | Only catches syntax |
| Code (contains) | Checking for patterns | Deterministic | Brittle to naming |
| Code (execution) | Checking runnable code | Proves it works | Needs safe sandbox |
| Model-based | Checking quality/style | Flexible, nuanced | Non-deterministic, costs tokens |

## Running Evals

```bash
# Run all evals for a feature
/eval kriging-pipeline

# Run specific case
/eval kriging-pipeline --case basic_spherical

# Run with multiple attempts (for pass@k)
/eval kriging-pipeline --attempts 10

# Save results for comparison
/eval kriging-pipeline --save

# Compare against previous baseline
/eval kriging-pipeline --compare baseline
```

## Interpreting Results

```
Feature: kriging-pipeline-eval
Cases: 3 | Attempts per case: 10

Results:
  basic_spherical:    pass@1=0.90  pass@3=1.00  pass^3=0.73
  cross_validation:   pass@1=0.60  pass@3=0.94  pass^3=0.22
  error_handling:     pass@1=0.80  pass@3=0.99  pass^3=0.51

Summary:
  Overall pass@1: 0.77 (threshold: 0.80) — BELOW TARGET
  Weakest case: cross_validation (pass@1=0.60)
  Action: Improve spatial CV guidance in prompts/skills
```

**Decision framework:**

| pass@1 | pass^3 | Interpretation | Action |
|--------|--------|---------------|--------|
| High | High | Reliable capability | Ship it |
| High | Low | Capable but inconsistent | Add constraints/examples |
| Low | Low | Capability gap | Add skill/improve prompt |
| Low | High | Unusual — check eval | Review graders |

## Integration with Template

The eval harness works with the template's existing components:

- **Skills** improve pass@1 by giving Claude domain knowledge
- **Rules** improve pass^k by enforcing consistent behavior
- **Instincts** track which patterns lead to higher eval scores
- **TDD** provides the test infrastructure that code-based graders use

Track eval scores over time to measure whether template changes improve AI output quality.
