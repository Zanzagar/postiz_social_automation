#!/usr/bin/env node
/**
 * PostToolUse Hook: Warn about debug statements after edits
 *
 * Cross-platform (Windows, macOS, Linux)
 *
 * Runs after Edit tool use. Checks for debug statements across multiple
 * languages and warns with line numbers to help remove them before committing.
 *
 * Supported: JS/TS (console.log), Python (print), Go (fmt.Print*),
 * Java (System.out), Ruby (puts/p)
 */

const path = require('path');
const { readFile } = require('./lib/utils');

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
  // Delegate to quality-gate.js when available (consolidates debug statement checking)
  try { require.resolve('./quality-gate'); process.stdout.write(data); process.exit(0); } catch { /* fall through */ }

  try {
    const input = JSON.parse(data);
    const filePath = input.tool_input?.file_path;

    // Polyglot debug statement patterns (template addition)
    const debugPatterns = {
      '.js':   { pattern: /console\.log/, label: 'console.log' },
      '.jsx':  { pattern: /console\.log/, label: 'console.log' },
      '.ts':   { pattern: /console\.log/, label: 'console.log' },
      '.tsx':  { pattern: /console\.log/, label: 'console.log' },
      '.py':   { pattern: /\bprint\s*\(/, label: 'print()' },
      '.go':   { pattern: /fmt\.Print/, label: 'fmt.Print*' },
      '.java': { pattern: /System\.out\.print/, label: 'System.out' },
      '.rb':   { pattern: /\b(puts|p)\s/, label: 'puts/p' }
    };

    const ext = filePath ? path.extname(filePath) : '';
    const debugCheck = debugPatterns[ext];

    if (filePath && debugCheck) {
      const content = readFile(filePath);
      if (!content) { process.stdout.write(data); process.exit(0); }
      const lines = content.split('\n');
      const matches = [];

      lines.forEach((line, idx) => {
        if (debugCheck.pattern.test(line)) {
          matches.push((idx + 1) + ': ' + line.trim());
        }
      });

      if (matches.length > 0) {
        console.error('[Hook] WARNING: ' + debugCheck.label + ' found in ' + filePath);
        matches.slice(0, 5).forEach(m => console.error(m));
        console.error('[Hook] Remove debug statements before committing');
      }
    }
  } catch {
    // Invalid input — pass through
  }

  process.stdout.write(data);
  process.exit(0);
});
