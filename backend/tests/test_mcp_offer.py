"""Gate-safety invariants for the Phase 2 in-task connect offer (offer_for_gated_server).

The whole point of the offer is that it can ONLY ever suggest, never grant: it must surface a
vetted, inactive, not-dismissed MCP for the user to one-click-connect, and it must never carry
anything that could widen the MCP surface on its own. These tests make a bad offer state fail
loudly instead of shipping a silent gate bypass.
"""

from types import SimpleNamespace

import backend.apps.agents.core.mcp_preflight as pf
from backend.apps.agents.core.mcp_preflight import (
    CURATED_SHORTLIST,
    offer_for_gated_server,
)

VETTED = {e["id"] for e in CURATED_SHORTLIST}
OFFER_SHAPE = {"id", "title", "description", "reason"}


def _settings(dismissed=None):
    return SimpleNamespace(dismissed_mcp_suggestions=dismissed or {})


def test_offer_only_returns_vetted_inactive(monkeypatch):
    monkeypatch.setattr(pf, "load_all_tools", lambda: [])  # nothing enabled
    s = _settings()
    o = offer_for_gated_server("Google Workspace", s)
    assert o is not None
    assert o["id"] == "Google Workspace"
    assert o["id"] in VETTED


def test_offer_rejects_unvetted_and_empty(monkeypatch):
    monkeypatch.setattr(pf, "load_all_tools", lambda: [])
    s = _settings()
    assert offer_for_gated_server("NotAVettedServer", s) is None
    assert offer_for_gated_server("", s) is None
    assert offer_for_gated_server(None, s) is None  # type: ignore[arg-type]


def test_offer_suppressed_when_dismissed(monkeypatch):
    monkeypatch.setattr(pf, "load_all_tools", lambda: [])
    s = _settings({"Google Workspace": "2026-01-01T00:00:00Z"})
    assert offer_for_gated_server("Google Workspace", s) is None


def test_offer_suppressed_when_already_active(monkeypatch):
    monkeypatch.setattr(
        pf, "load_all_tools",
        lambda: [SimpleNamespace(name="Google Workspace", enabled=True)],
    )
    s = _settings()
    assert offer_for_gated_server("Google Workspace", s) is None


def test_offer_carries_no_activate_capability(monkeypatch):
    # The security invariant: an offer is data to display, never an action that grants access.
    monkeypatch.setattr(pf, "load_all_tools", lambda: [])
    s = _settings()
    for entry in CURATED_SHORTLIST:
        o = offer_for_gated_server(entry["id"], s)
        assert o is not None
        assert set(o.keys()) == OFFER_SHAPE, f"offer for {entry['id']} grew an unexpected field"
