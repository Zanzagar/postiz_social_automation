#!/usr/bin/env node
/**
 * CLI bridge for bash scripts to query hook enable/disable status.
 * Adapted from ECC (affaan-m/everything-claude-code) scripts/hooks/check-hook-enabled.js
 *
 * Usage: node check-hook-enabled.js <hookId> [profilesCsv]
 * Outputs: "yes" or "no"
 */
'use strict';

const { isHookEnabled } = require('./hook-flags');

const [, , hookId, profilesCsv] = process.argv;
if (!hookId) {
  process.stdout.write('yes');
  process.exit(0);
}

process.stdout.write(isHookEnabled(hookId, { profiles: profilesCsv }) ? 'yes' : 'no');
