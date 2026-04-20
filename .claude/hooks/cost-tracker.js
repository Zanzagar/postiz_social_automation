#!/usr/bin/env node
/**
 * Stop Hook: Session cost telemetry
 *
 * Appends lightweight token/cost metrics to .claude/sessions/cost-log.jsonl.
 * Non-blocking — errors are silently ignored to prevent session disruption.
 *
 * Adapted from ECC (affaan-m/everything-claude-code) scripts/hooks/cost-tracker.js
 */

'use strict';

const path = require('path');
const { ensureDir, appendFile } = require('./lib/utils');

/**
 * Safely convert a value to a finite number, defaulting to 0.
 * @param {*} value
 * @returns {number}
 */
function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Estimate USD cost based on model and token counts.
 * Uses conservative blended rates per model family.
 *
 * @param {string} model - Model name/ID
 * @param {number} inputTokens
 * @param {number} outputTokens
 * @returns {number} Estimated cost in USD
 */
function estimateCost(model, inputTokens, outputTokens) {
  const table = {
    haiku:  { in: 0.8,  out: 4.0  },
    sonnet: { in: 3.0,  out: 15.0 },
    opus:   { in: 15.0, out: 75.0 },
  };

  const normalized = String(model || '').toLowerCase();
  let rates = table.sonnet; // default
  if (normalized.includes('haiku')) rates = table.haiku;
  if (normalized.includes('opus')) rates = table.opus;

  const cost = (inputTokens / 1_000_000) * rates.in
             + (outputTokens / 1_000_000) * rates.out;
  return Math.round(cost * 1e6) / 1e6;
}

/**
 * Get the project-local sessions directory.
 * Uses CLAUDE_PROJECT_DIR if set, otherwise walks up from __dirname.
 *
 * @returns {string}
 */
function getSessionsDir() {
  const projectDir = process.env.CLAUDE_PROJECT_DIR
    || path.resolve(__dirname, '..', '..');
  return path.join(projectDir, '.claude', 'sessions');
}

/**
 * Core logic — exported so run-with-flags.js can call directly.
 *
 * @param {string} rawInput - Raw JSON string from stdin
 * @returns {string} The original input (pass-through)
 */
function run(rawInput) {
  try {
    const input = rawInput.trim() ? JSON.parse(rawInput) : {};
    const usage = input.usage || input.token_usage || {};
    const inputTokens = toNumber(usage.input_tokens || usage.prompt_tokens || 0);
    const outputTokens = toNumber(usage.output_tokens || usage.completion_tokens || 0);

    const model = String(
      input.model || input._cursor?.model || process.env.CLAUDE_MODEL || 'unknown'
    );
    const sessionId = String(
      input.session_id || process.env.CLAUDE_SESSION_ID || 'default'
    );

    const sessionsDir = getSessionsDir();
    ensureDir(sessionsDir);

    const row = {
      timestamp: new Date().toISOString(),
      session_id: sessionId,
      model,
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      estimated_cost_usd: estimateCost(model, inputTokens, outputTokens),
    };

    appendFile(path.join(sessionsDir, 'cost-log.jsonl'), JSON.stringify(row) + '\n');
  } catch {
    // Non-blocking — never disrupt session exit
  }
  return rawInput;
}

// ── stdin entry point (backwards-compatible) ────────────────────
if (require.main === module) {
  const { isHookEnabled } = require('./lib/hook-flags');
  if (!isHookEnabled('cost-tracker')) process.exit(0);

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
