"""Smart wait: return when the page's network settles, not on a blind timer.

The wait runs on EVERY browser task and the audit says it's 42% of all time, so
this is high-blast-radius. These pin down that it (1) returns early when settled,
(2) never returns before the floor (no half-loaded reads), (3) never exceeds the
cap, (4) keeps waiting through a still-loading SPA, (5) survives a cancel or a
mid-navigation probe error. Edge-case-complete on purpose.
"""

import json

import pytest

from backend.apps.agents.browser import browser_wait as bw


# --- the pure decision (hammer it) ------------------------------------------
def test_decide_stop_waits_until_past_the_floor():
    # even a fully-settled page must not return before the floor (a momentary gap
    # between two requests would otherwise look 'settled')
    assert bw.decide_stop(ready=True, quiet_ms=9999, elapsed_ms=100, floor_ms=250) is False
    assert bw.decide_stop(ready=True, quiet_ms=9999, elapsed_ms=300, floor_ms=250) is True


def test_decide_stop_needs_ready_and_quiet():
    # past floor, but document not complete -> keep waiting
    assert bw.decide_stop(ready=False, quiet_ms=9999, elapsed_ms=500) is False
    # past floor, ready, but network still active (quiet below the window) -> wait
    assert bw.decide_stop(ready=True, quiet_ms=100, elapsed_ms=500, quiet_window_ms=400) is False
    # past floor, ready, quiet long enough -> stop
    assert bw.decide_stop(ready=True, quiet_ms=400, elapsed_ms=500, quiet_window_ms=400) is True


def test_decide_stop_handles_missing_quiet():
    assert bw.decide_stop(ready=True, quiet_ms=None, elapsed_ms=500) is False


# --- the async loop with a scripted probe -----------------------------------
def _probe(ready, quiet):
    return {"text": json.dumps({"ready": ready, "quiet": quiet}), "url": "https://x.com"}


class FakeExec:
    """Returns scripted probe results in sequence (last one repeats)."""
    def __init__(self, results):
        self.results = results
        self.calls = 0

    async def __call__(self, tool, params, bid, tid):
        assert tool == "BrowserEvaluate"
        r = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return r


@pytest.mark.asyncio
async def test_returns_early_once_settled():
    # first probe: still loading; second: settled -> should stop well under the cap
    ex = FakeExec([_probe(False, 0), _probe(True, 999)])
    out = await bw.smart_wait(ex, "b", "", 5000, poll_ms=20, floor_ms=20, quiet_window_ms=50)
    assert out["settled"] is True
    assert out["waited_ms"] < 5000
    assert "page settled" in out["text"]


@pytest.mark.asyncio
async def test_rides_to_cap_when_page_never_settles():
    # an SPA that keeps fetching (quiet always small) -> never settles -> caps out
    ex = FakeExec([_probe(True, 10)])
    out = await bw.smart_wait(ex, "b", "", 200, poll_ms=20, floor_ms=20, quiet_window_ms=400)
    assert out["settled"] is False
    assert out["waited_ms"] >= 180  # ~the cap
    assert "reached cap" in out["text"]


@pytest.mark.asyncio
async def test_never_returns_before_the_floor():
    # settled from the very first probe, but the floor must still be respected
    ex = FakeExec([_probe(True, 9999)])
    out = await bw.smart_wait(ex, "b", "", 5000, poll_ms=10, floor_ms=200, quiet_window_ms=50)
    assert out["waited_ms"] >= 200, "must not read a page before the settle floor"
    assert out["settled"] is True


@pytest.mark.asyncio
async def test_cancel_mid_wait_stops_cleanly():
    async def _cancelled(tool, params, bid, tid):
        return None  # _cancellable returns None when the run is cancelled
    out = await bw.smart_wait(_cancelled, "b", "", 5000, poll_ms=10, floor_ms=10)
    assert out["settled"] is False and out["waited_ms"] < 5000


@pytest.mark.asyncio
async def test_probe_error_during_navigation_keeps_waiting_then_settles():
    # while the page is navigating, evaluate errors; we must keep polling, not bail
    ex = FakeExec([{"error": "Cannot evaluate, page navigating"},
                   {"error": "still navigating"},
                   _probe(True, 999)])
    out = await bw.smart_wait(ex, "b", "", 5000, poll_ms=15, floor_ms=15, quiet_window_ms=50)
    assert out["settled"] is True and ex.calls >= 3


@pytest.mark.asyncio
async def test_garbage_probe_text_does_not_crash():
    ex = FakeExec([{"text": "not json", "url": "u"}, _probe(True, 999)])
    out = await bw.smart_wait(ex, "b", "", 3000, poll_ms=15, floor_ms=15, quiet_window_ms=50)
    assert out["settled"] is True
