Analyze and optimize code for performance.

Usage:
- `/optimize` - Analyze entire project for optimization opportunities
- `/optimize src/processing.py` - Optimize specific file
- `/optimize src/api/` - Optimize directory
- `/optimize --memory` - Focus on memory optimization
- `/optimize --speed` - Focus on execution speed

Arguments: $ARGUMENTS

## Analysis Areas

### 1. Algorithm Complexity
- Identify O(n²) or worse operations
- Suggest more efficient data structures
- Find unnecessary nested loops
- Recommend standard library alternatives

### 2. Database & I/O
- N+1 query patterns
- Missing indexes (from query patterns)
- Unoptimized bulk operations
- Synchronous I/O that could be async
- Missing caching opportunities

### 3. Memory Usage
- Large object allocations in loops
- Missing generators for large datasets
- Object retention preventing GC
- Unnecessary data copying

### 4. Python-Specific
- List comprehensions vs loops
- `__slots__` for data classes
- `lru_cache` for expensive pure functions
- `dataclasses` vs regular classes
- `collections` module usage (defaultdict, Counter)

### 5. Concurrency
- CPU-bound vs I/O-bound identification
- Threading vs multiprocessing recommendations
- Async/await opportunities
- Connection pooling

## Output Format

```
## Performance Analysis

**Scope:** [files analyzed]
**Focus:** [speed/memory/general]

### High Impact Opportunities

1. **[Location]** - [Current issue]
   - Impact: [High/Medium/Low]
   - Current: [code snippet]
   - Recommended: [optimized code]
   - Expected improvement: [estimate]

### Quick Wins

1. [Simple changes with measurable benefit]

### Long-term Recommendations

1. [Architectural changes for significant gains]

### Benchmarking Suggestions

To measure improvements:
```python
# Suggested profiling code
```
```

## Profiling Tools

If available, suggest running:
```bash
# CPU profiling
python -m cProfile -s cumtime src/main.py

# Memory profiling
python -m memory_profiler src/main.py

# Line-by-line profiling
kernprof -l -v src/main.py
```

## Important Notes

- Don't optimize prematurely - profile first
- Prefer readability for non-critical paths
- Benchmark before and after changes
- Consider maintainability tradeoffs
