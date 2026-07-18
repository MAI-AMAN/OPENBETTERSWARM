import asyncio
import pytest
from backend.apps.planner.models import TaskAnalysis, AgentSelection
from backend.apps.planner.context_planner import plan_context

@pytest.mark.asyncio
async def test_plan_context_execution():
    analysis = TaskAnalysis(primary_intent="execution")
    agent = AgentSelection(primary_agent_id="code_agent")
    result = await plan_context(analysis, agent)
    assert "workspace_files" in result.required_context_types
    assert result.include_history is True
    assert result.max_context_tokens >= 8000

@pytest.mark.asyncio
async def test_plan_context_creation():
    analysis = TaskAnalysis(primary_intent="creation")
    agent = AgentSelection(primary_agent_id="creative_agent")
    result = await plan_context(analysis, agent)
    assert "user_preferences" in result.required_context_types
    assert "system_memory" in result.required_context_types

@pytest.mark.asyncio
async def test_plan_context_latency():
    analysis = TaskAnalysis(primary_intent="execution", constraints=["latency_sensitive"])
    agent = AgentSelection(primary_agent_id="fast_agent")
    result = await plan_context(analysis, agent)
    assert result.max_context_tokens <= 2000

@pytest.mark.asyncio
async def test_plan_context_empty():
    analysis = TaskAnalysis(primary_intent="unknown")
    agent = AgentSelection(primary_agent_id="GeneralAgent")
    result = await plan_context(analysis, agent)
    assert isinstance(result.required_context_types, list)
    assert result.max_context_tokens >= 2000

async def run_all():
    await test_plan_context_execution()
    await test_plan_context_creation()
    await test_plan_context_latency()
    await test_plan_context_empty()
    print("CONTEXT PLANNER TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
