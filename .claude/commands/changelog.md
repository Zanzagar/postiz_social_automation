Generate or update the CHANGELOG based on git history.

Usage:
- `/changelog` - Generate changelog since last tag
- `/changelog v1.0.0` - Generate changelog since specific tag
- `/changelog v1.0.0..v1.1.0` - Generate changelog between two tags
- `/changelog --init` - Create new CHANGELOG.md file

Arguments: $ARGUMENTS

## Changelog Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes
```

## Actions

### If `--init` argument:
1. Create `CHANGELOG.md` with template above
2. Add `[Unreleased]` section
3. Report success

### If version range provided (e.g., `v1.0.0..v1.1.0`):
1. Run: `git log v1.0.0..v1.1.0 --oneline --no-merges`
2. Categorize commits by type (see Commit Categorization below)
3. Generate formatted changelog section
4. Show output (don't modify file unless asked)

### If single version/tag provided:
1. Run: `git log <tag>..HEAD --oneline --no-merges`
2. Categorize and format commits
3. Show output

### If no arguments:
1. Find latest tag: `git describe --tags --abbrev=0 2>/dev/null || echo ""`
2. If no tags, use all commits: `git log --oneline --no-merges`
3. Generate `[Unreleased]` section
4. Show output

## Commit Categorization

Categorize commits based on conventional commit prefixes:

| Category | Commit Types |
|----------|--------------|
| Added | `feat:`, `feat(scope):` |
| Changed | `refactor:`, `perf:`, `style:` |
| Deprecated | `deprecate:` (rare) |
| Removed | Commits mentioning "remove", "delete" |
| Fixed | `fix:`, `fix(scope):` |
| Security | `security:`, commits mentioning "CVE", "vulnerability" |

**Other types mapping:**
- `docs:` → Documentation section (or skip if minor)
- `test:` → Usually skip unless user-facing
- `chore:` → Usually skip (internal maintenance)
- `ci:` → Usually skip (CI/CD changes)

Commits without conventional prefixes: Try to categorize by keywords, otherwise put in "Changed".

## Output Format

```markdown
## [Unreleased] - YYYY-MM-DD

### Added
- Implement user authentication (#123)
- Add dark mode toggle

### Fixed
- Fix memory leak in data processor
- Resolve race condition in queue handler

### Changed
- Update dependencies to latest versions
- Refactor database connection pooling
```

## After Generating

Ask user:
1. "Would you like me to prepend this to CHANGELOG.md?"
2. "Should I create a git tag for this release?"

## Tips

- Group related commits together
- Remove noise commits (typo fixes, merge commits)
- Link to issues/PRs when referenced (e.g., `#123`)
- Include breaking changes prominently with `**BREAKING:**` prefix
