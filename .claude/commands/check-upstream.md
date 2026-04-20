# Check Upstream

Check template components against upstream sources for available updates.

## Usage

- `/check-upstream` — Quick summary of upstream changes (repo-level)
- `/check-upstream --manifest` — Per-file change detection using upstream-manifest.json
- `/check-upstream --manifest --diff` — Show actual upstream diffs for changed files
- `/check-upstream --verbose` — Show recent commit messages
- `/check-upstream --since YYYY-MM-DD` — Check changes since specific date

## Instructions

1. Run the check-upstream script with any arguments passed via `$ARGS`:

```bash
./scripts/check-upstream.sh $ARGS
```

2. Interpret the results:

**Repo-level mode (default):**
- "All upstreams up to date" — No action needed
- "X upstream(s) have changes" — Review the flagged upstreams

**Manifest mode (`--manifest`):**
- "All N files up to date" — No upstream changes to our adopted files
- "N file(s) changed upstream" — Review and decide: update our copy or skip

3. For changed files, follow the audit verdict framework:
   - **Adopt**: Our copy is a direct port — update to latest upstream version, re-apply documented adaptations
   - **Adapt**: Our copy has template-specific additions — review upstream diff, merge relevant changes
   - **Content merge**: Our rule has sections from upstream — check if the upstream section changed

4. After updating adopted files:
   - Update `adaptedFromSha` in `.claude/upstream-manifest.json`
   - Run CI validators: `node scripts/ci/validate-*.js`
   - Commit with: `chore: sync <component> with upstream <sha>`
