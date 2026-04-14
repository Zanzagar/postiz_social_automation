#!/usr/bin/env node

/**
 * Stop Hook: Check for debug statements in modified files
 *
 * Cross-platform (Windows, macOS, Linux)
 *
 * Runs after each response and checks if any modified files contain debug
 * statements. Supports JS/TS, Python, Go, Java, Ruby.
 *
 * Exclusions: test files, config files, scripts/ and hooks/ directories.
 */

const fs = require('fs');
const path = require('path');
const { isGitRepo, getGitModifiedFiles, readFile, log } = require('./lib/utils');

// Files where debug statements are expected and should not trigger warnings
const EXCLUDED_PATTERNS = [
  /\.test\.[jt]sx?$/,
  /\.spec\.[jt]sx?$/,
  /\.config\.[jt]s$/,
  /scripts\//,
  /\.claude\/hooks\//,
  /__tests__\//,
  /__mocks__\//,
  /test_.*\.py$/,
  /_test\.go$/,
];

// Polyglot debug patterns by extension (template addition)
const DEBUG_PATTERNS = {
  '.js': /console\.log/,
  '.jsx': /console\.log/,
  '.ts': /console\.log/,
  '.tsx': /console\.log/,
  '.py': /\bprint\s*\(/,
  '.go': /fmt\.Print/,
  '.java': /System\.out\.print/,
  '.rb': /\b(puts|p)\s/
};

const MAX_STDIN = 1024 * 1024; // 1MB limit
let data = '';
process.stdin.setEncoding('utf8');

process.stdin.on('data', chunk => {
  if (data.length < MAX_STDIN) {
    const remaining = MAX_STDIN - data.length;
    data += chunk.substring(0, remaining);
  }
});

process.stdin.on('end', () => {
  try {
    if (!isGitRepo()) {
      process.stdout.write(data);
      process.exit(0);
    }

    // Match all supported file types (template polyglot)
    const supportedExts = Object.keys(DEBUG_PATTERNS).map(e => e.replace('.', '\\.'));
    const extPattern = `(${supportedExts.join('|')})$`;
    const files = getGitModifiedFiles([extPattern])
      .filter(f => fs.existsSync(f))
      .filter(f => !EXCLUDED_PATTERNS.some(pattern => pattern.test(f)));

    let hasDebug = false;

    for (const file of files) {
      const ext = path.extname(file);
      const pattern = DEBUG_PATTERNS[ext];
      if (!pattern) continue;

      const content = readFile(file);
      if (content && pattern.test(content)) {
        log(`[Hook] WARNING: debug statement found in ${file}`);
        hasDebug = true;
      }
    }

    if (hasDebug) {
      log('[Hook] Remove debug statements before committing');
    }
  } catch (err) {
    log(`[Hook] check-console-log error: ${err.message}`);
  }

  // Always output the original data
  process.stdout.write(data);
  process.exit(0);
});
