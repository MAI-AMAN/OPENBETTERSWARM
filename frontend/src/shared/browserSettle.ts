// Renderer-side mirror of the backend's smart-wait (browser_wait.py): a `wait`
// that returns the instant the page's network goes quiet instead of blind-sleeping
// the full duration. A top-level BrowserWait already gets this on the backend, but
// a `wait` INSIDE a BrowserBatch runs entirely here in the renderer, so without
// this it would fall back to a dumb sleep and make batching slower than not batching.

export const SETTLE_FLOOR_MS = 250; // never settle before this (a momentary gap isn't 'settled')
export const SETTLE_QUIET_MS = 400; // network must be silent this long to count as settled
export const SETTLE_POLL_MS = 150;

// One probe: is the document complete, and how long since the last network resource
// finished/started? Returns a JSON string. No interpolation, so it's injection-safe.
export const SETTLE_PROBE_JS =
  "(()=>{const n=performance.now();" +
  "const es=performance.getEntriesByType('resource');let last=0;" +
  "for(const e of es){const t=Math.max(e.responseEnd||0,e.startTime||0);if(t>last)last=t;}" +
  "return JSON.stringify({ready:document.readyState==='complete',quiet:Math.round(n-last)});})()";

// Pure decision: stop waiting once we're past the floor AND the document is complete
// AND the network has been quiet for the settle window.
export function shouldStopWaiting(
  ready: boolean,
  quietMs: number,
  elapsedMs: number,
  floorMs = SETTLE_FLOOR_MS,
  quietWindowMs = SETTLE_QUIET_MS,
): boolean {
  if (elapsedMs < floorMs) return false;
  return !!ready && (quietMs || 0) >= quietWindowMs;
}
