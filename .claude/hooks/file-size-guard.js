#!/usr/bin/env node
/**
 * PreToolUse Hook: Block creation of files exceeding 800 lines
 *
 * Matcher: Write
 * Exit 2 to block the tool use, Exit 0 to allow.
 *
 * Exempt: lockfiles, generated files, vendor directories, documentation files.
 * Adapted for template from claude-behavior.md (<800 lines rule).
 * The 800-line rule targets source code modularity — documentation, skills,
 * PRDs, and data files are legitimately long and should not be constrained.
 */

'use strict';

const path = require('path');

const MAX_LINES = 800;

const EXEMPT_FILES = new Set([
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  'Cargo.lock',
  'go.sum',
  'poetry.lock',
  'Gemfile.lock',
  'composer.lock',
  'pnpm-workspace.yaml',
]);

// Documentation and data files — length means thoroughness, not poor design
const EXEMPT_EXTENSIONS = new Set([
  '.md', '.mdx', '.txt', '.rst', '.adoc',  // documentation
  '.csv', '.tsv', '.jsonl', '.log',         // data/logs
  '.sql',                                    // migrations, seeds
]);

const EXEMPT_PATH_SEGMENTS = [
  '/generated/',
  '.generated.',
  '.min.',
  '/vendor/',
  '/dist/',
  '/node_modules/',
  '/build/',
  '/__pycache__/',
];

/**
 * Core logic — exported so run-with-flags.js can call directly.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through) or calls process.exit(2) to block
 */
function run(rawInput) {
  try {
    const data = JSON.parse(rawInput);
    const filePath = data.tool_input?.file_path;
    const content = data.tool_input?.content;

    if (!filePath || typeof content !== 'string') return rawInput;

    // Check exempt filenames
    const filename = path.basename(filePath);
    if (EXEMPT_FILES.has(filename)) return rawInput;

    // Check exempt extensions (documentation, data, logs)
    const ext = path.extname(filePath).toLowerCase();
    if (EXEMPT_EXTENSIONS.has(ext)) return rawInput;

    // Check exempt path segments
    if (EXEMPT_PATH_SEGMENTS.some(seg => filePath.includes(seg))) return rawInput;

    // Count lines
    const lineCount = content.split('\n').length;

    if (lineCount > MAX_LINES) {
      process.stderr.write(
        `[Hook] BLOCKED: File would be ${lineCount} lines (limit: ${MAX_LINES}).\n` +
        `[Hook] Split into smaller, focused modules for better maintainability.\n` +
        `[Hook] File: ${filename}\n`
      );
      process.exit(2);
    }
  } catch {
    // Don't block on parse errors
  }
  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  const { isHookEnabled } = require('./lib/hook-flags');
  if (!isHookEnabled('file-size-guard')) process.exit(0);

  const MAX_STDIN = 1024 * 1024;
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
