import asyncio
from backend.apps.planner.models import TaskAnalysis, AgentSelection, AmbiguityLevel, ReasoningEffort
from backend.apps.planner.model_router import route_model

async def test_route_model_latency_sensitive():
    analysis = TaskAnalysis(primary_intent="execution", constraints=["latency_sensitive"])
    agent = AgentSelection(primary_agent_id="CodeExecutionAgent")
    result = await route_model(analysis, agent)
    assert result.model_id == "claude-3-haiku-20240307"
    assert result.reasoning_effort == ReasoningEffort.LOW

async def test_route_model_high_ambiguity():
    analysis = TaskAnalysis(primary_intent="creation", ambiguity_level=AmbiguityLevel.HIGH)
    agent = AgentSelection(primary_agent_id="CreativeAgent")
    result = await route_model(analysis, agent)
    assert result.model_id == "claude-3-5-sonnet-20241022"
    assert result.reasoning_effort == ReasoningEffort.HIGH

async def test_route_model_low_ambiguity():
    analysis = TaskAnalysis(primary_intent="execution", ambiguity_level=AmbiguityLevel.LOW)
    agent = AgentSelection(primary_agent_id="GeneralAgent")
    result = await route_model(analysis, agent)
    assert result.model_id == "claude-3-haiku-20240307"
    assert result.reasoning_effort == ReasoningEffort.LOW

async def test_route_model_agent_override():
    analysis = TaskAnalysis(primary_intent="execution", ambiguity_level=AmbiguityLevel.MEDIUM)
    agent = AgentSelection(primary_agent_id="CodeExecutionAgent")
    result = await route_model(analysis, agent)
    assert result.model_id == "claude-3-5-sonnet-20241022"
    assert result.reasoning_effort == ReasoningEffort.HIGH

async def run_all():
    await test_route_model_latency_sensitive()
    await test_route_model_high_ambiguity()
    await test_route_model_low_ambiguity()
    await test_route_model_agent_override()
    print("MODEL ROUTER TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
