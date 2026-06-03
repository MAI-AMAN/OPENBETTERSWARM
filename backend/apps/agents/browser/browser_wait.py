"""
Smart wait: return as soon as the page's network has SETTLED, instead of the
blind fixed sleep BrowserWait used to do.

The audit found blind `BrowserWait(2500)` sleeps eat ~42% of all run time, the
page is usually ready long before the fixed duration elapses (navigate already
waits for the main load, so the agent's extra wait is just for SPA XHR content
to finish). So we poll the page's actual network activity (the Performance
Resource Timing API, which records every fetch/XHR with timestamps) and return
the instant it's been quiet for a short window.

Reliability-preserving by construction, the whole point is to be FASTER without
being flakier:
- We wait for REAL network quiet, not a guess, so we don't read a half-loaded page.
- We NEVER return before the floor (skips a momentary gap between two requests).
- We NEVER wait longer than the caller asked (the requested ms is a hard cap).
- A page that keeps fetching (live feed) simply rides to the cap, same as before.

Backend-side + provider-free: the probe runs through the existing BrowserEvaluate
path, so there's no Electron/IPC change to packaged-build-test, and the decision
logic is a pure function we can hammer with tests.
"""

import asyncio
import json
import time

# One probe: is the document complete, and how long since the last network
# resource finished/started? Returns a JSON string (BrowserEvaluate hands back
# string results verbatim).
PROBE_JS = (
    "(()=>{const n=performance.now();"
    "const es=performance.getEntriesByType('resource');let last=0;"
    "for(const e of es){const t=Math.max(e.responseEnd||0,e.startTime||0);if(t>last)last=t;}"
    "return JSON.stringify({ready:document.readyState==='complete',quiet:Math.round(n-last)});})()"
)

_QUIET_WINDOW_MS = 400   # network must be silent this long to count as settled
_FLOOR_MS = 250          # never return before this (a momentary gap isn't 'settled')
_POLL_MS = 150


def decide_stop(ready, quiet_ms, elapsed_ms,
                floor_ms=_FLOOR_MS, quiet_window_ms=_QUIET_WINDOW_MS) -> bool:
    """Pure decision: stop waiting once we're past the floor AND the document is
    complete AND the network has been quiet for the settle window."""
    if elapsed_ms < floor_ms:
        return False
    return bool(ready) and (quiet_ms or 0) >= quiet_window_ms


async def smart_wait(execute_fn, browser_id, tab_id, max_ms, *,
                     poll_ms=_POLL_MS, floor_ms=_FLOOR_MS,
                     quiet_window_ms=_QUIET_WINDOW_MS) -> dict:
    """Wait up to `max_ms`, returning early once the page settles. `execute_fn`
    is an async (tool, params, browser_id, tab_id) -> result|None (None = the run
    was cancelled). Never raises into the caller."""
    max_ms = max(100, min(int(max_ms or 1000), 10000))
    start = time.monotonic()
    settled = False
    last_url = ""

    def _elapsed():
        return (time.monotonic() - start) * 1000

    while _elapsed() < max_ms:
        await asyncio.sleep(min(poll_ms, max(0, max_ms - _elapsed())) / 1000)
        if _elapsed() >= max_ms:
            break
        res = await execute_fn("BrowserEvaluate", {"expression": PROBE_JS}, browser_id, tab_id)
        if res is None:        # cancelled mid-wait
            break
        last_url = res.get("url") or last_url
        if "error" in res:     # page mid-navigation / not evaluable yet, keep waiting
            continue
        try:
            probe = json.loads(res.get("text") or "{}")
        except Exception:
            continue
        if decide_stop(probe.get("ready"), probe.get("quiet", 0), _elapsed(),
                       floor_ms=floor_ms, quiet_window_ms=quiet_window_ms):
            settled = True
            break

    waited = round(_elapsed())
    text = f"Waited {waited}ms ({'page settled' if settled else 'reached cap'})."
    if last_url:
        text += f" Current URL: {last_url}"
    return {"text": text, "url": last_url, "settled": settled, "waited_ms": waited}
