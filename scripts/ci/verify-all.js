#!/usr/bin/env node
// Runs every deterministic packaged-app verifier in sequence and aggregates the
// result. This is the single entry point CI calls after building the artifact.
// Each verifier cold-launches the app itself for clean isolation, so this is
// slower than one shared launch but far less flaky.
//
//   node scripts/ci/verify-all.js [--app <path>] [--require-signed] [--strict]
//
//   --require-signed   make the signature check a hard gate (release CI, post-sign)
//   --strict           make external-network reachability a hard gate
//
// Exit 0 only if every verifier passed.

'use strict';
const path = require('path');
const { spawnSync } = require('child_process');

function parseArgs(argv) {
  const out = { app: null, requireSigned: false, strict: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--app') out.app = argv[++i];
    else if (argv[i] === '--require-signed') out.requireSigned = true;
    else if (argv[i] === '--strict') out.strict = true;
  }
  return out;
}

function run(label, script, extra) {
  process.stdout.write(`\n${'='.repeat(64)}\n== ${label}\n${'='.repeat(64)}\n`);
  const r = spawnSync(process.execPath, [path.join(__dirname, script), ...extra], { stdio: 'inherit' });
  return r.status === 0;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const appArg = args.app ? ['--app', args.app] : [];

  const steps = [
    ['boot / paint / serve / provenance', 'verify-packaged-app.js', appArg],
    ['code-signing state', 'verify-signature.js', [...(args.app ? ['--target', args.app] : []), ...(args.requireSigned ? ['--require-signed'] : [])]],
    ['resilience (locked-port + multi-instance)', 'verify-resilience.js', appArg],
    ['network / auth / 9router', 'verify-network.js', [...appArg, ...(args.strict ? ['--strict'] : [])]],
  ];

  const results = steps.map(([label, script, extra]) => [label, run(label, script, extra)]);

  process.stdout.write(`\n${'='.repeat(64)}\n== SUMMARY\n${'='.repeat(64)}\n`);
  let allOk = true;
  for (const [label, ok] of results) { process.stdout.write(`  ${ok ? 'PASS' : 'FAIL'}  ${label}\n`); if (!ok) allOk = false; }
  process.stdout.write('\n');
  process.exit(allOk ? 0 : 1);
}

main();
