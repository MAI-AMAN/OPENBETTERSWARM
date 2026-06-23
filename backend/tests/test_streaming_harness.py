"""Streaming harness: drive the real _run_agent_loop with a MOCKED claude_agent_sdk.query
that yields a controlled SDK message sequence, and assert the session state + emitted WS
events. This is the safety net for restructuring the streaming loop (it had no isolated
coverage), so it pins the observable contract: streamed text lands as an assistant message,
tool calls are recorded, and the turn completes."""

import asyncio

import claude_agent_sdk
from claude_agent_sdk import AssistantMessage, ResultMessage
from claude_agent_sdk.types import TextBlock, ToolUseBlock, ThinkingBlock

from backend.apps.agents.agent_manager import AgentManager
import backend.apps.agents.core.ws_manager as ws_mod


def _mock_query_yielding(*messages):
    async def _q(*args, **kwargs):
        for m in messages:
            yield m
    return _q


def _drive(monkeypatch, messages, prompt="hi"):
    """Run one _run_agent_loop turn against a mocked SDK message stream; return (session, ws_events)."""
    events = []

    async def fake_send(session_id, event, data):
        events.append((event, data))

    monkeypatch.setattr(ws_mod.ws_manager, "send_to_session", fake_send, raising=True)
    monkeypatch.setattr(claude_agent_sdk, "query", _mock_query_yielding(*messages), raising=True)

    mgr = AgentManager()
    from backend.apps.agents.core.models import AgentSession
    session = AgentSession(name="t", model="sonnet", dashboard_id="d")
    mgr.sessions[session.id] = session
    asyncio.run(mgr._run_agent_loop(session.id, prompt))
    return session, events


def _result(**kw):
    base = dict(subtype="success", duration_ms=100, duration_api_ms=80, is_error=False,
                num_turns=1, session_id="sdk-1", usage={"input_tokens": 10, "output_tokens": 5})
    base.update(kw)
    return ResultMessage(**base)


def _assistant(blocks, **kw):
    base = dict(content=blocks, model="sonnet", message_id="m1", stop_reason="end_turn",
                session_id="sdk-1", usage={"input_tokens": 10, "output_tokens": 5})
    base.update(kw)
    return AssistantMessage(**base)


def test_streamed_text_lands_as_assistant_message(monkeypatch):
    session, events = _drive(monkeypatch, [
        _assistant([TextBlock(text="Hello there")]),
        _result(),
    ])
    assert any(m.role == "assistant" and "Hello there" in str(m.content) for m in session.messages)
    assert session.status == "completed"
    # the assistant reply + the token meter are broadcast to the UI
    assert any(e == "agent:message" for e, _ in events)
    assert any(e == "agent:context_update" for e, _ in events)


def test_tool_use_is_recorded(monkeypatch):
    session, events = _drive(monkeypatch, [
        _assistant([ToolUseBlock(id="tu1", name="Read", input={"file_path": "/x.py"})]),
        _result(),
    ])
    assert any(m.role == "tool_call" for m in session.messages)
    # the tool name survives onto the recorded call
    assert any("Read" in str(m.content) for m in session.messages if m.role == "tool_call")
    assert session.status == "completed"


def test_text_then_tool_in_one_turn(monkeypatch):
    session, events = _drive(monkeypatch, [
        _assistant([TextBlock(text="Let me read it."), ToolUseBlock(id="tu1", name="Read", input={"file_path": "/x.py"})]),
        _result(),
    ])
    roles = [m.role for m in session.messages]
    assert "assistant" in roles and "tool_call" in roles
    assert session.status == "completed"


def test_completes_even_with_no_content(monkeypatch):
    # an empty assistant turn (e.g. a pure stop) must still finish cleanly, not hang
    session, events = _drive(monkeypatch, [_assistant([]), _result()])
    assert session.status == "completed"


def test_thinking_block_before_text_is_handled(monkeypatch):
    # a ThinkingBlock mutates the separate thinking-state cluster; the turn must still
    # surface the final answer and complete (pins the thinking path for the restructuring)
    session, events = _drive(monkeypatch, [
        _assistant([ThinkingBlock(thinking="let me reason about this", signature="sig-1"),
                    TextBlock(text="the answer is 42")]),
        _result(),
    ])
    assert any(m.role == "assistant" and "the answer is 42" in str(m.content) for m in session.messages)
    assert session.status == "completed"


def test_transient_capacity_error_is_retried_then_succeeds(monkeypatch):
    # the capacity-retry while-loop: first query() raises a transient error, the loop
    # backs off (sleep mocked to no-op) and re-queries, which succeeds. This is the exact
    # behavior the streaming restructuring must preserve.
    real_sleep = asyncio.sleep  # capture before patching to avoid self-recursion

    async def _fast_sleep(*a, **k):
        await real_sleep(0)  # still yields to the loop, but no real backoff delay

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)

    state = {"n": 0}

    async def flaky_query(*args, **kwargs):
        state["n"] += 1
        if state["n"] == 1:
            raise Exception("No pool capacity available. Try again shortly.")
        yield _assistant([TextBlock(text="Recovered after backoff")])
        yield _result()

    events = []

    async def fake_send(session_id, event, data):
        events.append((event, data))

    monkeypatch.setattr(ws_mod.ws_manager, "send_to_session", fake_send, raising=True)
    monkeypatch.setattr(claude_agent_sdk, "query", flaky_query, raising=True)

    mgr = AgentManager()
    from backend.apps.agents.core.models import AgentSession
    session = AgentSession(name="t", model="sonnet", dashboard_id="d")
    mgr.sessions[session.id] = session
    asyncio.run(mgr._run_agent_loop(session.id, "hi"))

    assert state["n"] == 2  # retried exactly once
    assert any(m.role == "assistant" and "Recovered" in str(m.content) for m in session.messages)
    assert session.status == "completed"
