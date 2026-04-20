#!/usr/bin/env node
/**
 * Prevent shipping user-specific absolute paths in template files.
 * Adapted from ECC's validate-no-personal-paths.js — auto-detects username
 * and scans .claude/ prefixed directories.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.join(__dirname, '../..');

// Directories to scan for personal path leaks
const TARGETS = [
  'README.md',
  'CLAUDE.md',
  '.claude/skills',
  '.claude/commands',
  '.claude/agents',
  '.claude/rules',
  'docs',
];

// File extensions to check
const SCANNABLE_EXTENSIONS = /\.(md|json|js|ts|sh|toml|yml|yaml|py)$/i;

// Build block patterns from detected usernames
function buildBlockPatterns() {
  const patterns = [];
  const usernames = new Set();

  // Detect current username from environment
  const envUser = process.env.USER || process.env.USERNAME;
  if (envUser) {
    usernames.add(envUser);
  }

  // Detect from HOME
  const home = process.env.HOME || process.env.USERPROFILE;
  if (home) {
    const homeUser = path.basename(home);
    if (homeUser && homeUser !== '/' && homeUser !== '\\') {
      usernames.add(homeUser);
    }
  }

  // Detect from git config
  try {
    const gitUser = execSync('git config user.name', { encoding: 'utf-8' }).trim();
    // Git user.name can contain spaces — extract potential username-like parts
    if (gitUser && !gitUser.includes(' ')) {
      usernames.add(gitUser);
    }
  } catch {
    // git config not available, skip
  }

  // Build patterns for each detected username
  for (const username of usernames) {
    if (username.length < 3) continue; // Skip very short names to avoid false positives
    // Unix-style paths
    patterns.push(new RegExp(`/home/${username}\\b`, 'g'));
    patterns.push(new RegExp(`/Users/${username}\\b`, 'g'));
    // Windows-style paths
    patterns.push(new RegExp(`C:\\\\Users\\\\${username}\\b`, 'gi'));
  }

  // Always block ECC's author path (template may have residual references)
  patterns.push(/\/Users\/affoon\b/g);
  patterns.push(/C:\\Users\\affoon\b/gi);

  return patterns;
}

function collectFiles(targetPath, out) {
  if (!fs.existsSync(targetPath)) return;
  const stat = fs.statSync(targetPath);
  if (stat.isFile()) {
    out.push(targetPath);
    return;
  }

  for (const entry of fs.readdirSync(targetPath)) {
    if (entry === 'node_modules' || entry === '.git') continue;
    collectFiles(path.join(targetPath, entry), out);
  }
}

const blockPatterns = buildBlockPatterns();
const files = [];
for (const target of TARGETS) {
  collectFiles(path.join(ROOT, target), files);
}

let failures = 0;
for (const file of files) {
  if (!SCANNABLE_EXTENSIONS.test(file)) continue;
  const content = fs.readFileSync(file, 'utf8');
  for (const pattern of blockPatterns) {
    // Reset regex lastIndex for global patterns
    pattern.lastIndex = 0;
    const match = content.match(pattern);
    if (match) {
      const relPath = path.relative(ROOT, file);
      console.error(`ERROR: personal path detected in ${relPath}: ${match[0]}`);
      failures += match.length;
      break;
    }
  }
}

if (failures > 0) {
  console.error(`\nFound ${failures} personal path occurrence(s)`);
  process.exit(1);
}

console.log(`Validated ${files.length} files: no personal paths in shipped content`);
