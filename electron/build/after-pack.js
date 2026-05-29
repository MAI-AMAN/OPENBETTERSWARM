'use strict';
// electron-builder 26 special-excludes node_modules from extraResources (25 did
// not), so the bundled 9Router - a Next.js standalone whose server.js does
// require('next') - ships WITHOUT its deps. The result: 9Router dies with
// "Cannot find module 'next'", never binds :20128, and the Models tab spins on
// "Starting subscription service..." forever. We copy router/node_modules into
// the packed app HERE rather than after electron-builder finishes, because
// afterPack runs BEFORE code-signing: on macOS the whole .app is sealed by the
// signature, so injecting files post-sign would invalidate it. The .next dotdir
// is handled by the package.json extraResources filter; only node_modules needs
// this rescue.
const fs = require('fs');
const path = require('path');

exports.default = async function afterPack(context) {
  const { appOutDir, electronPlatformName, packager } = context;
  const src = path.join(__dirname, '..', 'build-staging', 'router', 'node_modules');
  if (!fs.existsSync(src)) return; // dev/no-router build; nothing to do

  let routerDir;
  if (electronPlatformName === 'darwin') {
    const appName = packager.appInfo.productFilename; // "OpenSwarm"
    routerDir = path.join(appOutDir, `${appName}.app`, 'Contents', 'Resources', 'router');
  } else {
    routerDir = path.join(appOutDir, 'resources', 'router');
  }
  if (!fs.existsSync(routerDir)) return; // router not staged into this target

  const dest = path.join(routerDir, 'node_modules');
  if (!fs.existsSync(dest)) {
    fs.cpSync(src, dest, { recursive: true });
  }
  if (!fs.existsSync(path.join(dest, 'next'))) {
    throw new Error(`afterPack: 9Router node_modules/next missing in ${routerDir} after copy`);
  }
  console.log(`[afterPack] staged 9Router node_modules into ${routerDir}`);
};
