#!/usr/bin/env node
/**
 * claude-rate npx shim.
 *
 * Locates a Python 3 interpreter on the user's machine and runs rate.py
 * with all CLI args forwarded. The actual logic lives in rate.py (Python
 * stdlib only) so the same script is usable via npx, curl|sh, pip, or
 * direct invocation.
 *
 * Why a shim?
 *   npx is the most discoverable runner ("npx @sagargupta16/claude-rate"),
 *   but the rater is intentionally Python -- stdlib only, runs anywhere,
 *   no node_modules to download just to read a settings.json. This shim
 *   makes both audiences happy.
 */

'use strict';

const { spawnSync } = require('node:child_process');
const path = require('node:path');

const SCRIPT = path.join(__dirname, '..', 'rate.py');

const candidates = process.platform === 'win32'
  ? ['py', 'python3', 'python']
  : ['python3', 'python'];

function findPython() {
  for (const cmd of candidates) {
    // For "py", pass "-3" to force Python 3 on Windows.
    const probeArgs = cmd === 'py' ? ['-3', '--version'] : ['--version'];
    const probe = spawnSync(cmd, probeArgs, { stdio: 'ignore' });
    if (probe.status === 0) {
      return { cmd, prefix: cmd === 'py' ? ['-3'] : [] };
    }
  }
  return null;
}

const python = findPython();
if (!python) {
  console.error('claude-rate: no Python 3 interpreter found on PATH.');
  console.error('  Install Python 3.10+ from https://www.python.org/downloads/');
  console.error('  or use the curl|sh installer (see https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/tools/claude-rate).');
  process.exit(127);
}

const userArgs = process.argv.slice(2);
const result = spawnSync(
  python.cmd,
  [...python.prefix, SCRIPT, ...userArgs],
  { stdio: 'inherit' }
);

if (result.error) {
  console.error('claude-rate: failed to invoke Python:', result.error.message);
  process.exit(1);
}

process.exit(result.status === null ? 1 : result.status);
