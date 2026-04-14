#!/usr/bin/env node
/**
 * PostToolUse Hook: Auto-format files after edits
 *
 * Cross-platform (Windows, macOS, Linux)
 *
 * Runs after Edit tool use. Handles multiple languages:
 * - JS/TS: auto-detects Biome or Prettier via resolve-formatter.js
 * - Python: ruff format
 * - Go: gofmt
 * - Rust: rustfmt
 * - Shell: shfmt
 *
 * For Biome, uses `check --write` (format + lint in one pass) to
 * avoid a redundant second invocation from quality-gate.js.
 *
 * Prefers the local node_modules/.bin binary over npx to skip
 * package-resolution overhead (~200-500ms savings per invocation).
 *
 * Fails silently if no formatter is found or installed.
 */

const { execFileSync, spawnSync } = require('child_process');
const path = require('path');

// Shell metacharacters that cmd.exe interprets as command separators/operators
const UNSAFE_PATH_CHARS = /[&|<>^%!]/;

const fs = require('fs');
const { findProjectRoot, detectFormatter, resolveFormatterBin } = require('./lib/resolve-formatter');
const { commandExists } = require('./lib/utils');

const MAX_STDIN = 1024 * 1024; // 1MB limit

/**
 * Core logic — exported so run-with-flags.js can call directly
 * without spawning a child process.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through)
 */
function run(rawInput) {
  // Delegate to quality-gate.js when available (consolidates formatting + linting + TS check)
  try { require.resolve('./quality-gate'); return rawInput; } catch { /* fall through */ }

  try {
    const input = JSON.parse(rawInput);
    const filePath = input.tool_input?.file_path;

    if (filePath && /\.(ts|tsx|js|jsx)$/.test(filePath)) {
      try {
        const resolvedFilePath = path.resolve(filePath);
        const projectRoot = findProjectRoot(path.dirname(resolvedFilePath));
        const formatter = detectFormatter(projectRoot);
        if (!formatter) return rawInput;

        const resolved = resolveFormatterBin(projectRoot, formatter);
        if (!resolved) return rawInput;

        // Biome: `check --write` = format + lint in one pass
        // Prettier: `--write` = format only
        const args = formatter === 'biome' ? [...resolved.prefix, 'check', '--write', resolvedFilePath] : [...resolved.prefix, '--write', resolvedFilePath];

        if (process.platform === 'win32' && resolved.bin.endsWith('.cmd')) {
          // Windows: .cmd files require shell to execute. Guard against
          // command injection by rejecting paths with shell metacharacters.
          if (UNSAFE_PATH_CHARS.test(resolvedFilePath)) {
            throw new Error('File path contains unsafe shell characters');
          }
          const result = spawnSync(resolved.bin, args, {
            cwd: projectRoot,
            shell: true,
            stdio: 'pipe',
            timeout: 15000
          });
          if (result.error) throw result.error;
          if (typeof result.status === 'number' && result.status !== 0) {
            throw new Error(result.stderr?.toString() || `Formatter exited with status ${result.status}`);
          }
        } else {
          execFileSync(resolved.bin, args, {
            cwd: projectRoot,
            stdio: ['pipe', 'pipe', 'pipe'],
            timeout: 15000
          });
        }
      } catch {
        // Formatter not installed, file missing, or failed — non-blocking
      }
    } else if (filePath) {
      // Polyglot formatter dispatch (template addition)
      try {
        const resolvedPath = path.resolve(filePath);
        if (!fs.existsSync(resolvedPath)) return rawInput;

        const formatters = {
          '.py': { cmd: 'ruff', args: ['format'] },
          '.go': { cmd: 'gofmt', args: ['-w'] },
          '.rs': { cmd: 'rustfmt', args: [] },
          '.sh': { cmd: 'shfmt', args: ['-w'] }
        };

        const ext = path.extname(filePath);
        const formatter = formatters[ext];
        if (formatter && commandExists(formatter.cmd)) {
          spawnSync(formatter.cmd, [...formatter.args, resolvedPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
            timeout: 15000
          });
        }
      } catch {
        // Formatter not installed or failed — non-blocking
      }
    }
  } catch {
    // Invalid input — pass through
  }

  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  let data = '';
  process.stdin.setEncoding('utf8');

  process.stdin.on('data', chunk => {
    if (data.length < MAX_STDIN) {
      const remaining = MAX_STDIN - data.length;
      data += chunk.substring(0, remaining);
    }
  });

  process.stdin.on('end', () => {
    data = run(data);
    process.stdout.write(data);
    process.exit(0);
  });
}

module.exports = { run };
