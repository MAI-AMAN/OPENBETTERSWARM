import { _electron as electron, ElectronApplication, Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Repo root is two levels up from this file (e2e/helpers/).
const REPO_ROOT = path.resolve(__dirname, '..', '..');

// Resolve the PACKAGED Electron binary for the current OS. Override with
// E2E_APP_PATH to point at any built artifact. We deliberately drive the packaged
// build (asar, bundled python-env, real paths) — not `electron .` on source —
// because that is what ships and what the plan requires us to verify.
export function packagedAppPath(): string {
  if (process.env.E2E_APP_PATH) return process.env.E2E_APP_PATH;
  const dist = path.join(REPO_ROOT, 'electron', 'dist');
  const candidates =
    process.platform === 'win32'
      ? [path.join(dist, 'win-unpacked', 'OpenSwarm.exe')]
      : process.platform === 'darwin'
        ? [
            path.join(dist, 'mac-arm64', 'OpenSwarm.app', 'Contents', 'MacOS', 'OpenSwarm'),
            path.join(dist, 'mac', 'OpenSwarm.app', 'Contents', 'MacOS', 'OpenSwarm'),
            path.join(dist, 'mac-universal', 'OpenSwarm.app', 'Contents', 'MacOS', 'OpenSwarm'),
          ]
        : [path.join(dist, 'linux-unpacked', 'openswarm')];
  const found = candidates.find((c) => { try { return fs.statSync(c).isFile(); } catch { return false; } });
  if (!found) throw new Error(`Packaged app not found. Build first or set E2E_APP_PATH. Looked in:\n  ${candidates.join('\n  ')}`);
  return found;
}

export async function launchApp(): Promise<ElectronApplication> {
  return electron.launch({ executablePath: packagedAppPath(), args: [] });
}

// The app opens a splash window first, then the main window that loads the React
// frontend and exposes window.openswarm. Poll all windows until one has the
// bridge AND the React root has mounted (first meaningful paint), then return it.
export async function waitForMainWindow(app: ElectronApplication, timeoutMs = 120_000): Promise<Page> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const w of app.windows()) {
      try {
        const ready = await w.evaluate(() => {
          const hasBridge = typeof (window as any).openswarm?.getBackendPort === 'function';
          const root = document.getElementById('root');
          return hasBridge && !!root && root.childElementCount > 0;
        });
        if (ready) return w;
      } catch { /* window navigating or not ready; keep polling */ }
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error('main window with mounted React root never appeared');
}

// Read the build-info.json the build stamped, so tests can assert the running
// app's provenance matches the artifact on disk.
export function readBuildInfo(): { sha: string; shortSha: string; channel: string; version: string } {
  return JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'electron', 'build-info.json'), 'utf8'));
}
