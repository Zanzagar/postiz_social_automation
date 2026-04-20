#!/usr/bin/env node
/**
 * PostToolUse Hook: Consolidated quality gate
 *
 * Matcher: Edit|Write
 *
 * Combines three concerns into a single smart hook:
 *   1. Auto-formatting (replaces post-edit-format for Node.js path)
 *   2. Debug statement detection (replaces console-log-audit)
 *   3. TypeScript error checking (replaces typescript-check)
 *
 * Adapted from ECC (affaan-m/everything-claude-code) scripts/hooks/quality-gate.js
 * with debug statement and TypeScript checking added from template hooks.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const { findProjectRoot, detectFormatter, resolveFormatterBin } = require('./lib/resolve-formatter');

const MAX_STDIN = 1024 * 1024;

// ── Debug statement patterns (from console-log-audit.js) ────────
const DEBUG_PATTERNS = {
  '.js':   { pattern: /console\.log/, label: 'console.log' },
  '.jsx':  { pattern: /console\.log/, label: 'console.log' },
  '.ts':   { pattern: /console\.log/, label: 'console.log' },
  '.tsx':  { pattern: /console\.log/, label: 'console.log' },
  '.py':   { pattern: /\bprint\s*\(/, label: 'print()' },
  '.go':   { pattern: /fmt\.Print/, label: 'fmt.Print*' },
  '.java': { pattern: /System\.out\.print/, label: 'System.out' },
  '.rb':   { pattern: /\b(puts|p)\s/, label: 'puts/p' },
};

// ── Helpers ─────────────────────────────────────────────────────

/**
 * Execute a command synchronously with timeout.
 */
function exec(command, args, cwd = process.cwd()) {
  return spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: process.env,
    timeout: 15000,
  });
}

function log(msg) {
  process.stderr.write(`${msg}\n`);
}

// ── 1. Formatting ───────────────────────────────────────────────

/**
 * Run formatter on a file based on extension and project config.
 * For JS/TS with Biome, skips (post-edit-format already handles it).
 */
function maybeFormat(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const fix = String(process.env.TEMPLATE_QUALITY_GATE_FIX || 'true').toLowerCase() === 'true';

  // JS/TS/JSON/MD — use project formatter (Biome or Prettier)
  if (['.ts', '.tsx', '.js', '.jsx', '.json', '.md'].includes(ext)) {
    const projectRoot = findProjectRoot(path.dirname(filePath));
    const formatter = detectFormatter(projectRoot);

    if (formatter === 'biome') {
      // JS/TS formatting handled by post-edit-format — only run for JSON/MD
      if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) return;

      const resolved = resolveFormatterBin(projectRoot, 'biome');
      if (!resolved) return;
      const args = [...resolved.prefix, 'check', filePath];
      if (fix) args.push('--write');
      const result = exec(resolved.bin, args, projectRoot);
      if (result.status === 0 && fix) {
        log(`[QualityGate] Formatted: ${path.basename(filePath)} (biome)`);
      }
      return;
    }

    if (formatter === 'prettier') {
      const resolved = resolveFormatterBin(projectRoot, 'prettier');
      if (!resolved) return;
      const args = [...resolved.prefix, fix ? '--write' : '--check', filePath];
      const result = exec(resolved.bin, args, projectRoot);
      if (result.status === 0 && fix) {
        log(`[QualityGate] Formatted: ${path.basename(filePath)} (prettier)`);
      }
      return;
    }
    return;
  }

  // Go
  if (ext === '.go') {
    if (fix) {
      const r = exec('gofmt', ['-w', filePath]);
      if (r.status === 0) log(`[QualityGate] Formatted: ${path.basename(filePath)} (gofmt)`);
    }
    return;
  }

  // Python
  if (ext === '.py') {
    const args = fix ? ['format', filePath] : ['format', '--check', filePath];
    const r = exec('ruff', args);
    if (r.status === 0 && fix) log(`[QualityGate] Formatted: ${path.basename(filePath)} (ruff)`);
  }
}

// ── 2. Debug statement detection ────────────────────────────────

/**
 * Check for debug statements and warn (advisory, does not block).
 */
function checkDebugStatements(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const check = DEBUG_PATTERNS[ext];
  if (!check) return;

  // Skip hook files themselves — they reference debug patterns as grep targets
  if (filePath.includes('.claude/hooks/')) return;

  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return;
  }

  const lines = content.split('\n');
  const matches = [];
  for (let i = 0; i < lines.length; i++) {
    if (check.pattern.test(lines[i])) {
      matches.push(`  ${i + 1}: ${lines[i].trim()}`);
    }
  }

  if (matches.length > 0) {
    log(`[QualityGate] WARNING: ${check.label} found in ${path.basename(filePath)}`);
    matches.slice(0, 5).forEach(m => log(m));
    if (matches.length > 5) log(`  ... and ${matches.length - 5} more`);
    log('[QualityGate] Remove debug statements before committing');
  }
}

// ── 3. TypeScript error checking ────────────────────────────────

/**
 * Run tsc --noEmit and report errors relevant to the edited file.
 */
function maybeTypeCheck(filePath) {
  if (!/\.(ts|tsx)$/.test(filePath)) return;

  const resolvedPath = path.resolve(filePath);
  if (!fs.existsSync(resolvedPath)) return;

  // Find nearest tsconfig.json
  let dir = path.dirname(resolvedPath);
  const root = path.parse(dir).root;
  let depth = 0;

  while (dir !== root && depth < 20) {
    if (fs.existsSync(path.join(dir, 'tsconfig.json'))) break;
    dir = path.dirname(dir);
    depth++;
  }

  if (!fs.existsSync(path.join(dir, 'tsconfig.json'))) return;

  try {
    const npxBin = process.platform === 'win32' ? 'npx.cmd' : 'npx';
    spawnSync(npxBin, ['tsc', '--noEmit', '--pretty', 'false'], {
      cwd: dir,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 30000,
    });
  } catch (err) {
    // tsc exits non-zero when there are errors — filter to edited file
    const output = (err.stdout || '') + (err.stderr || '');
    const relPath = path.relative(dir, resolvedPath);
    const candidates = new Set([filePath, resolvedPath, relPath]);
    const relevantLines = output
      .split('\n')
      .filter(line => {
        for (const candidate of candidates) {
          if (line.includes(candidate)) return true;
        }
        return false;
      })
      .slice(0, 10);

    if (relevantLines.length > 0) {
      log(`[QualityGate] TypeScript errors in ${path.basename(filePath)}:`);
      relevantLines.forEach(line => log(`  ${line}`));
    }
  }
}

// ── Main ────────────────────────────────────────────────────────

/**
 * Core logic — exported so run-with-flags.js can call directly.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through)
 */
function run(rawInput) {
  try {
    const input = JSON.parse(rawInput);
    const filePath = String(input.tool_input?.file_path || input.tool_input?.path || '');

    if (!filePath || !fs.existsSync(filePath)) return rawInput;

    // Resolve to absolute for consistent path comparisons
    const absPath = path.resolve(filePath);

    // 1. Format
    maybeFormat(absPath);

    // 2. Debug statement check
    checkDebugStatements(absPath);

    // 3. TypeScript check (if applicable)
    maybeTypeCheck(absPath);
  } catch {
    // Ignore errors — quality gate must not disrupt workflow
  }
  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  const { isHookEnabled } = require('./lib/hook-flags');
  if (!isHookEnabled('quality-gate')) process.exit(0);

  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {
    if (raw.length < MAX_STDIN) {
      raw += chunk.substring(0, MAX_STDIN - raw.length);
    }
  });
  process.stdin.on('end', () => {
    const result = run(raw);
    if (result !== null && result !== undefined) process.stdout.write(result);
  });
}

module.exports = { run };
