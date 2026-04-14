#!/usr/bin/env node
/**
 * Validate hooks configuration in .claude/settings.json.
 * Adapted from ECC's validate-hooks.js — reads our settings.json format
 * instead of a standalone hooks.json file.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const SETTINGS_FILE = path.join(__dirname, '../../.claude/settings.json');

// Authoritative list of Claude Code hook events (from ECC hooks.schema.json)
const VALID_EVENTS = [
  'SessionStart',
  'UserPromptSubmit',
  'PreToolUse',
  'PermissionRequest',
  'PostToolUse',
  'PostToolUseFailure',
  'Notification',
  'SubagentStart',
  'Stop',
  'SubagentStop',
  'PreCompact',
  'InstructionsLoaded',
  'TeammateIdle',
  'TaskCompleted',
  'ConfigChange',
  'WorktreeCreate',
  'WorktreeRemove',
  'SessionEnd',
];

const VALID_HOOK_TYPES = ['command', 'http', 'prompt', 'agent'];

// Events that don't require a matcher field
const EVENTS_WITHOUT_MATCHER = new Set([
  'SessionStart',
  'UserPromptSubmit',
  'Notification',
  'Stop',
  'SubagentStop',
]);

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function isNonEmptyStringArray(value) {
  return Array.isArray(value) && value.length > 0 && value.every(item => isNonEmptyString(item));
}

/**
 * Extract script path from a hook command string.
 * Handles patterns like:
 *   bash $CLAUDE_PROJECT_DIR/.claude/hooks/lib/run-with-flags-shell.sh ... $CLAUDE_PROJECT_DIR/.claude/hooks/script.sh ...
 *   node $CLAUDE_PROJECT_DIR/.claude/hooks/lib/run-with-flags.js ... $CLAUDE_PROJECT_DIR/.claude/hooks/script.js ...
 */
function extractScriptPaths(command) {
  if (typeof command !== 'string') return [];
  const paths = [];
  // Match $CLAUDE_PROJECT_DIR/.claude/hooks/... patterns
  const matches = command.matchAll(/\$CLAUDE_PROJECT_DIR\/(\.claude\/hooks\/[^\s]+)/g);
  for (const m of matches) {
    paths.push(m[1]);
  }
  return paths;
}

/**
 * Validate a single hook entry has required fields and valid structure.
 */
function validateHookEntry(hook, label) {
  let hasErrors = false;

  if (!hook.type || typeof hook.type !== 'string') {
    console.error(`ERROR: ${label} missing or invalid 'type' field`);
    hasErrors = true;
  } else if (!VALID_HOOK_TYPES.includes(hook.type)) {
    console.error(`ERROR: ${label} has unsupported hook type '${hook.type}'`);
    hasErrors = true;
  }

  if ('timeout' in hook && (typeof hook.timeout !== 'number' || hook.timeout < 0)) {
    console.error(`ERROR: ${label} 'timeout' must be a non-negative number`);
    hasErrors = true;
  }

  if (hook.type === 'command') {
    if ('async' in hook && typeof hook.async !== 'boolean') {
      console.error(`ERROR: ${label} 'async' must be a boolean`);
      hasErrors = true;
    }

    if (!isNonEmptyString(hook.command) && !isNonEmptyStringArray(hook.command)) {
      console.error(`ERROR: ${label} missing or invalid 'command' field`);
      hasErrors = true;
    }

    return hasErrors;
  }

  if ('async' in hook) {
    console.error(`ERROR: ${label} 'async' is only supported for command hooks`);
    hasErrors = true;
  }

  if (hook.type === 'http') {
    if (!isNonEmptyString(hook.url)) {
      console.error(`ERROR: ${label} missing or invalid 'url' field`);
      hasErrors = true;
    }
    return hasErrors;
  }

  // prompt or agent type
  if (!isNonEmptyString(hook.prompt)) {
    console.error(`ERROR: ${label} missing or invalid 'prompt' field`);
    hasErrors = true;
  }

  if ('model' in hook && !isNonEmptyString(hook.model)) {
    console.error(`ERROR: ${label} 'model' must be a non-empty string`);
    hasErrors = true;
  }

  return hasErrors;
}

function validateHooks() {
  if (!fs.existsSync(SETTINGS_FILE)) {
    console.log('No .claude/settings.json found, skipping hook validation');
    process.exit(0);
  }

  let settings;
  try {
    settings = JSON.parse(fs.readFileSync(SETTINGS_FILE, 'utf-8'));
  } catch (e) {
    console.error(`ERROR: Invalid JSON in settings.json: ${e.message}`);
    process.exit(1);
  }

  const hooks = settings.hooks;
  if (!hooks || typeof hooks !== 'object') {
    console.log('No hooks configuration found in settings.json, skipping');
    process.exit(0);
  }

  let hasErrors = false;
  let totalMatchers = 0;
  let totalHookEntries = 0;
  const scriptPaths = [];
  const projectRoot = path.join(__dirname, '../..');

  for (const [eventType, matchers] of Object.entries(hooks)) {
    if (!VALID_EVENTS.includes(eventType)) {
      console.error(`ERROR: Invalid event type: '${eventType}' (valid: ${VALID_EVENTS.join(', ')})`);
      hasErrors = true;
      continue;
    }

    if (!Array.isArray(matchers)) {
      console.error(`ERROR: ${eventType} must be an array of matchers`);
      hasErrors = true;
      continue;
    }

    for (let i = 0; i < matchers.length; i++) {
      const matcher = matchers[i];
      if (typeof matcher !== 'object' || matcher === null) {
        console.error(`ERROR: ${eventType}[${i}] is not an object`);
        hasErrors = true;
        continue;
      }

      // Check matcher field (not required for some events)
      if (!('matcher' in matcher) && !EVENTS_WITHOUT_MATCHER.has(eventType)) {
        console.error(`ERROR: ${eventType}[${i}] missing 'matcher' field`);
        hasErrors = true;
      }

      if (!matcher.hooks || !Array.isArray(matcher.hooks)) {
        console.error(`ERROR: ${eventType}[${i}] missing 'hooks' array`);
        hasErrors = true;
      } else {
        for (let j = 0; j < matcher.hooks.length; j++) {
          const hookEntry = matcher.hooks[j];
          if (validateHookEntry(hookEntry, `${eventType}[${i}].hooks[${j}]`)) {
            hasErrors = true;
          }

          // Collect script paths for existence checking
          if (hookEntry.type === 'command' && typeof hookEntry.command === 'string') {
            const paths = extractScriptPaths(hookEntry.command);
            for (const p of paths) {
              scriptPaths.push({ path: p, label: `${eventType}[${i}].hooks[${j}]` });
            }
          }

          totalHookEntries++;
        }
      }
      totalMatchers++;
    }
  }

  // Verify referenced hook scripts exist
  let missingScripts = 0;
  for (const { path: scriptPath, label } of scriptPaths) {
    const fullPath = path.join(projectRoot, scriptPath);
    if (!fs.existsSync(fullPath)) {
      console.error(`WARN: ${label} references missing script: ${scriptPath}`);
      missingScripts++;
    }
  }

  if (hasErrors) {
    process.exit(1);
  }

  const parts = [`Validated ${totalMatchers} hook matchers (${totalHookEntries} hook entries)`];
  if (missingScripts > 0) {
    parts.push(`${missingScripts} missing script warning(s)`);
  }
  console.log(parts.join(', '));
}

validateHooks();
