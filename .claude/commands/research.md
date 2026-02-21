---
name: research
description: Structured research workflow for papers, documentation, or exploration
arguments:
  - name: topic
    description: What to research (can be a question, topic, or path to PDF)
    required: true
---

# Research: $ARGUMENTS.topic

## Step 1: Classify Research Type

Determine what kind of research this is:

**If topic is a file path (PDF, paper):**
→ Go to "PDF/Paper Analysis" section

**If topic is a technical question:**
→ Go to "Technical Research" section

**If topic is exploratory/open-ended:**
→ Go to "Exploratory Research" section

---

## PDF/Paper Analysis

For research papers, technical documents, or PDFs:

### 1. Read and Extract
```
Use Read tool on the PDF file
Extract key sections:
- Abstract/Summary
- Methodology/Approach
- Key Findings/Results
- Conclusions
- Relevant figures/tables (describe)
```

### 2. Structured Summary

**Paper:** [Title]
**Authors:** [If available]
**Date:** [Publication date]

**Core Question:** What problem does this address?

**Key Findings:**
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

**Methodology:** [Brief description of approach]

**Relevance to Project:** [How this applies to current work]

**Limitations:** [Any caveats or constraints]

### 3. Actionable Insights
- What can we apply from this?
- What questions remain?
- Should we research further?

---

## Technical Research

For library docs, API questions, implementation approaches:

### 1. Apply Token-Conscious Tiers

**Tier 1 - Check existing knowledge:**
- Do I know this reliably from training?
- Is this a stable, well-documented API?
→ If yes, provide answer with confidence level

**Tier 2 - Lightweight lookup:**
- Use WebFetch to official documentation
- Target specific pages, not entire sites
→ Summarize relevant section only

**Tier 3 - Deep documentation (use sparingly):**
- Use Context7 for complex, multi-part queries
- Only when Tier 1-2 insufficient
→ Note: This adds 5-20k tokens to context

### 2. Document Findings

**Question:** [Original question]

**Answer:** [Direct answer]

**Source:** [Where this came from]

**Confidence:** [High/Medium/Low]

**Code Example:** (if applicable)
```
[Relevant code snippet]
```

---

## Exploratory Research

For open-ended exploration, market research, or broad topics:

### 1. Define Scope
- What specifically do we need to learn?
- What decisions will this inform?
- What's the time/depth budget?

### 2. Search Strategy
```
Use WebSearch for:
- Current state of the field
- Recent developments (2024-2026)
- Comparisons and alternatives
```

### 3. Synthesize Findings

**Research Question:** [What we set out to learn]

**Key Discoveries:**
1. [Discovery 1 with source]
2. [Discovery 2 with source]
3. [Discovery 3 with source]

**Emerging Patterns:** [What themes emerged]

**Recommendations:** [Based on research]

**Gaps:** [What we still don't know]

**Sources:**
- [Source 1](url)
- [Source 2](url)

---

## Research Output

After completing research, ask user:

1. **Is this sufficient?** Or do you need deeper investigation?
2. **Should I document this?** Add to project docs for future reference?
3. **What's the next step?** Apply findings to a task?

---

## Token-Conscious Research Tips

- Start with existing knowledge before searching
- Use WebFetch for targeted lookups (500-2k tokens)
- Reserve Context7 for complex library questions (5-20k tokens)
- Summarize PDFs rather than quoting extensively
- For large documents, read in sections if needed
