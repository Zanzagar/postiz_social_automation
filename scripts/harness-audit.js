#!/usr/bin/env node
/**
 * harness-audit.js — Deterministic template health scoring
 *
 * 7 categories, 0-10 each, 70 max total.
 * All checks are file-existence or content-based — reproducible for same commit.
 *
 * Usage:
 *   node scripts/harness-audit.js [scope] [--format json|text]
 *
 * Scopes: repo (default), hooks, skills, commands, agents, security
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ── Helpers ─────────────────────────────────────────────────────

function exists(projectDir, relPath) {
  return fs.existsSync(path.join(projectDir, relPath));
}

function dirCount(projectDir, relPath) {
  const dir = path.join(projectDir, relPath);
  if (!fs.existsSync(dir)) return 0;
  try {
    return fs.readdirSync(dir).filter(f => !f.startsWith('.')).length;
  } catch { return 0; }
}

function fileContains(projectDir, relPath, pattern) {
  const filePath = path.join(projectDir, relPath);
  if (!fs.existsSync(filePath)) return false;
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return typeof pattern === 'string' ? content.includes(pattern) : pattern.test(content);
  } catch { return false; }
}

function fileSize(projectDir, relPath) {
  const filePath = path.join(projectDir, relPath);
  try { return fs.statSync(filePath).size; } catch { return 0; }
}

// ── Check definitions ───────────────────────────────────────────

function defineChecks() {
  return {
    toolCoverage: {
      label: 'Tool Coverage',
      checks: [
        { id: 'hooks-configured', label: 'Hooks configured in settings.json', weight: 2,
          test: (d) => exists(d, '.claude/settings.json') && fileContains(d, '.claude/settings.json', '"hooks"') },
        { id: 'mcp-servers', label: 'MCP servers configured', weight: 2,
          test: (d) => exists(d, '.taskmaster/tasks/tasks.json') },
        { id: 'agents-defined', label: 'Agents defined (3+)', weight: 2,
          test: (d) => dirCount(d, '.claude/agents') >= 3 },
        { id: 'skills-defined', label: 'Skills defined (10+)', weight: 2,
          test: (d) => dirCount(d, '.claude/skills') >= 10 },
        { id: 'commands-defined', label: 'Commands defined (10+)', weight: 2,
          test: (d) => dirCount(d, '.claude/commands') >= 10 },
      ]
    },
    contextEfficiency: {
      label: 'Context Efficiency',
      checks: [
        { id: 'claude-md-exists', label: 'CLAUDE.md exists', weight: 2,
          test: (d) => exists(d, 'CLAUDE.md') },
        { id: 'claude-md-lean', label: 'CLAUDE.md under 20KB', weight: 2,
          test: (d) => fileSize(d, 'CLAUDE.md') > 0 && fileSize(d, 'CLAUDE.md') < 20480 },
        { id: 'conditional-rules', label: 'Language rules use paths: frontmatter', weight: 2,
          test: (d) => {
            const rulesDir = path.join(d, '.claude/rules');
            if (!fs.existsSync(rulesDir)) return false;
            const langDirs = ['python', 'typescript', 'golang', 'java', 'frontend'];
            return langDirs.some(lang => exists(d, `.claude/rules/${lang}`));
          }},
        { id: 'context-modes', label: 'Context modes defined', weight: 2,
          test: (d) => exists(d, '.claude/contexts') && dirCount(d, '.claude/contexts') >= 1 },
        { id: 'context-management', label: 'Context management documented', weight: 2,
          test: (d) => fileContains(d, 'CLAUDE.md', 'Context') || fileContains(d, 'CLAUDE.md', 'Status Line') },
      ]
    },
    qualityGates: {
      label: 'Quality Gates',
      checks: [
        { id: 'pre-commit-hook', label: 'Pre-commit check hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/pre-commit-check.sh') },
        { id: 'post-edit-format', label: 'Post-edit formatter hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/post-edit-format.js') || exists(d, '.claude/hooks/post-edit-format.sh') },
        { id: 'quality-gate', label: 'Quality gate hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/quality-gate.js') },
        { id: 'file-size-guard', label: 'File size guard hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/file-size-guard.js') },
        { id: 'protect-sensitive', label: 'Sensitive file protection hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/protect-sensitive-files.sh') },
      ]
    },
    memoryPersistence: {
      label: 'Memory & Persistence',
      checks: [
        { id: 'session-init', label: 'Session init hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/session-init.sh') },
        { id: 'session-end', label: 'Session end hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/session-end.js') },
        { id: 'pre-compact', label: 'Pre-compact state preservation', weight: 2,
          test: (d) => exists(d, '.claude/hooks/pre-compact.sh') },
        { id: 'sessions-dir', label: 'Sessions directory exists', weight: 2,
          test: (d) => exists(d, '.claude/sessions') },
        { id: 'suggest-compact', label: 'Compaction advisor hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/suggest-compact.js') },
      ]
    },
    evalCoverage: {
      label: 'Eval & Testing',
      checks: [
        { id: 'test-command', label: 'Test command configured', weight: 2,
          test: (d) => fileContains(d, 'CLAUDE.md', 'pytest') || fileContains(d, 'CLAUDE.md', 'jest') || fileContains(d, 'CLAUDE.md', 'go test') },
        { id: 'linter-configured', label: 'Linter configured', weight: 2,
          test: (d) => fileContains(d, 'CLAUDE.md', 'ruff') || fileContains(d, 'CLAUDE.md', 'eslint') || fileContains(d, 'CLAUDE.md', 'golangci') },
        { id: 'ci-workflow', label: 'CI workflow exists', weight: 2,
          test: (d) => exists(d, '.github/workflows') && dirCount(d, '.github/workflows') >= 1 },
        { id: 'verify-command', label: '/verify command exists', weight: 2,
          test: (d) => exists(d, '.claude/commands/verify.md') },
        { id: 'eval-command', label: '/eval command exists', weight: 2,
          test: (d) => exists(d, '.claude/commands/eval.md') },
      ]
    },
    securityGuardrails: {
      label: 'Security Guardrails',
      checks: [
        { id: 'protect-hook', label: 'Sensitive file protection', weight: 2,
          test: (d) => exists(d, '.claude/hooks/protect-sensitive-files.sh') },
        { id: 'security-rule', label: 'Security hardening rule', weight: 2,
          test: (d) => exists(d, '.claude/rules/security-hardening.md') },
        { id: 'gitignore-env', label: '.gitignore blocks .env files', weight: 2,
          test: (d) => fileContains(d, '.gitignore', '.env') },
        { id: 'no-secrets-claude-md', label: 'No hardcoded secrets in CLAUDE.md', weight: 2,
          test: (d) => {
            if (!exists(d, 'CLAUDE.md')) return true;
            const content = fs.readFileSync(path.join(d, 'CLAUDE.md'), 'utf8');
            return !/\b(sk-|pk_live_|AKIA|ghp_|gho_)[A-Za-z0-9]{10,}/.test(content);
          }},
        { id: 'doc-file-blocker', label: 'Doc file blocker hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/doc-file-blocker.sh') },
      ]
    },
    costEfficiency: {
      label: 'Resource Management',
      checks: [
        { id: 'cost-tracker', label: 'Cost tracker hook', weight: 2,
          test: (d) => exists(d, '.claude/hooks/cost-tracker.js') },
        { id: 'model-route', label: '/model-route command exists', weight: 2,
          test: (d) => exists(d, '.claude/commands/model-route.md') },
        { id: 'hook-profiles', label: 'Hook profile system', weight: 2,
          test: (d) => exists(d, '.claude/hooks/lib/hook-flags.js') },
        { id: 'subagent-docs', label: 'Sub-agent model routing documented', weight: 2,
          test: (d) => fileContains(d, 'CLAUDE.md', 'haiku') && fileContains(d, 'CLAUDE.md', 'Agent') },
        { id: 'settings-presets', label: 'Settings presets available', weight: 2,
          test: (d) => exists(d, '.claude/commands/settings.md') },
      ]
    },
  };
}

// ── Scoring ─────────────────────────────────────────────────────

function runAudit(projectDir, scope = 'repo') {
  const allCategories = defineChecks();
  const results = {
    overall: 0,
    maxScore: 0,
    categories: {},
    failedChecks: [],
    passedChecks: [],
    topActions: [],
  };

  // Filter categories by scope
  const scopeMap = {
    repo: Object.keys(allCategories),
    hooks: ['qualityGates', 'memoryPersistence'],
    skills: ['toolCoverage'],
    commands: ['toolCoverage'],
    agents: ['toolCoverage'],
    security: ['securityGuardrails'],
  };

  const activeCategories = scopeMap[scope] || scopeMap.repo;

  for (const [key, category] of Object.entries(allCategories)) {
    if (!activeCategories.includes(key)) continue;

    let score = 0;
    let maxScore = 0;
    const checks = [];

    for (const check of category.checks) {
      maxScore += check.weight;
      const passed = check.test(projectDir);
      checks.push({ ...check, passed, test: undefined });

      if (passed) {
        score += check.weight;
        results.passedChecks.push({ category: key, ...check, test: undefined });
      } else {
        results.failedChecks.push({ category: key, ...check, test: undefined });
      }
    }

    results.categories[key] = { label: category.label, score, maxScore, checks };
    results.overall += score;
    results.maxScore += maxScore;
  }

  // Generate top 3 improvement actions from failed checks
  results.topActions = results.failedChecks
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 3)
    .map(c => ({ action: `Fix: ${c.label}`, category: c.category, id: c.id }));

  return results;
}

// ── Output formatters ───────────────────────────────────────────

function printTextReport(results) {
  const pct = results.maxScore > 0
    ? Math.round((results.overall / results.maxScore) * 100)
    : 0;

  const grade = pct >= 90 ? 'A' : pct >= 80 ? 'B' : pct >= 70 ? 'C' : pct >= 60 ? 'D' : 'F';
  const bar = makeBar(pct);

  console.log('');
  console.log(`  Template Health: ${results.overall}/${results.maxScore} (${pct}%) ${grade}`);
  console.log(`  ${bar}`);
  console.log('');

  for (const [, cat] of Object.entries(results.categories)) {
    const catPct = cat.maxScore > 0 ? Math.round((cat.score / cat.maxScore) * 100) : 0;
    const icon = catPct === 100 ? '[OK]' : catPct >= 60 ? '[--]' : '[!!]';
    console.log(`  ${icon} ${cat.label}: ${cat.score}/${cat.maxScore}`);

    for (const check of cat.checks) {
      const mark = check.passed ? '+' : '-';
      console.log(`      ${mark} ${check.label}`);
    }
    console.log('');
  }

  if (results.topActions.length > 0) {
    console.log('  Top Actions:');
    results.topActions.forEach((a, i) => {
      console.log(`    ${i + 1}. ${a.action}`);
    });
    console.log('');
  }
}

function makeBar(pct) {
  const width = 30;
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;
  return '[' + '#'.repeat(filled) + '-'.repeat(empty) + ']';
}

// ── CLI entry point ─────────────────────────────────────────────

if (require.main === module) {
  const args = process.argv.slice(2);
  const formatIdx = args.indexOf('--format');
  const format = formatIdx >= 0 ? args[formatIdx + 1] : 'text';
  const scope = args.find(a => !a.startsWith('--') && a !== format) || 'repo';
  const projectDir = process.env.CLAUDE_PROJECT_DIR || process.cwd();

  const results = runAudit(projectDir, scope);

  if (format === 'json') {
    console.log(JSON.stringify(results, null, 2));
  } else {
    printTextReport(results);
  }

  // Exit with non-zero if score is below 50%
  const pct = results.maxScore > 0 ? (results.overall / results.maxScore) * 100 : 0;
  process.exit(pct < 50 ? 1 : 0);
}

module.exports = { runAudit, defineChecks };
