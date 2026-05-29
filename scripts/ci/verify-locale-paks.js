#!/usr/bin/env node
// Guards the empty-locale renderer crash. A packaged build MUST ship Chromium's
// locale .pak files (locales/en-US.pak + the full ~50). If they are missing,
// Electron launches the renderer with an EMPTY --lang, and Blink's
// LCIDFromLocaleInternal (third_party/blink/.../text/locale_win.cc) null-derefs
// (STATUS_ACCESS_VIOLATION 0xC0000005, read of 0x8) the instant a text/agent/
// webview surface mounts - a hard crash on the first real interaction, with no
// JS error to localize it. electron-builder has been observed to drop these on a
// --dir repack, so we assert them explicitly rather than trust the packager.

'use strict';
const fs = require('fs');
const path = require('path');
const h = require('./lib/app-harness');

// The build intentionally trims locales to en-US via electronLanguages, so the
// count is small by design - the only thing that matters is that the locale the
// renderer resolves to (en-US.pak) is actually present. Zero paks / a missing
// en-US.pak is the crash condition.
const REQUIRED = 'en-US.pak';

function parseArgs(argv) {
  const out = { app: null };
  for (let i = 0; i < argv.length; i++) if (argv[i] === '--app') out.app = argv[++i];
  return out;
}

function pakCount(dir) {
  try { return fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.pak')); }
  catch { return null; }
}

function checkWinLinux(exe) {
  const dir = path.join(path.dirname(exe), 'locales');
  const paks = pakCount(dir);
  if (paks === null) return { ok: false, msg: `locales/ dir missing at ${dir}` };
  const hasReq = paks.some((p) => p.toLowerCase() === REQUIRED.toLowerCase());
  process.stdout.write(`  ${dir}: ${paks.length} paks, en-US.pak=${hasReq}\n`);
  if (!hasReq) return { ok: false, msg: `${REQUIRED} missing from ${dir} (${paks.length} paks present)` };
  return { ok: true, msg: `${paks.length} paks incl ${REQUIRED}` };
}

function checkMac(exe) {
  // mac stores locale paks inside the Electron Framework; layout varies by version,
  // and this crash is Windows-specific, so be informational rather than blocking.
  const appRoot = exe.slice(0, exe.indexOf('.app') + 4);
  const found = [];
  (function walk(d, depth) {
    if (depth > 6) return;
    let ents = [];
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full, depth + 1);
      else if (e.isFile() && e.name.toLowerCase().endsWith('.pak')) found.push(full);
    }
  })(appRoot, 0);
  process.stdout.write(`  mac: found ${found.length} .pak file(s) under the app bundle\n`);
  return { ok: found.length > 0, msg: `${found.length} paks (mac is informational)` , soft: true };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const exe = h.packagedAppPath(args.app);
  const res = process.platform === 'darwin' ? checkMac(exe) : checkWinLinux(exe);
  if (res.ok) { process.stdout.write(`PASS  locale paks present (${res.msg})\n`); process.exit(0); }
  if (res.soft) { process.stdout.write(`WARN  ${res.msg} - could not confirm mac paks; not blocking\n`); process.exit(0); }
  process.stderr.write(
    `FAIL  packaged build is MISSING Chromium locale paks: ${res.msg}\n` +
    `      The renderer would launch with an empty --lang and crash in Blink's\n` +
    `      LCIDFromLocaleInternal (0xC0000005) on the first text/agent/webview mount.\n` +
    `      Fix: ensure electron-builder copies node_modules/electron/dist/locales/*.pak\n` +
    `      into the packaged output (this regressed on --dir repacks of the v42 build).\n`);
  process.exit(1);
}

main();
