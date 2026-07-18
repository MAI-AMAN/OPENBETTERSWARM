import asyncio
from backend.apps.planner.models import TaskAnalysis, CapabilityMatch, AmbiguityLevel, DelegationStrategy
from backend.apps.planner.agent_planner import plan_agents

async def test_plan_agents_fallback():
    analysis = TaskAnalysis(primary_intent="creation", ambiguity_level=AmbiguityLevel.LOW)
    match = CapabilityMatch(feasibility_score=0.0)
    result = await plan_agents(analysis, match)
    assert result.primary_agent_id == "FallbackAgent"

async def test_plan_agents_creation():
    analysis = TaskAnalysis(primary_intent="creation", ambiguity_level=AmbiguityLevel.LOW)
    match = CapabilityMatch(feasibility_score=1.0)
    result = await plan_agents(analysis, match)
    assert result.primary_agent_id == "CreativeAgent"
    assert result.delegation_strategy == DelegationStrategy.SINGLE

async def test_plan_agents_execution():
    analysis = TaskAnalysis(primary_intent="execution", ambiguity_level=AmbiguityLevel.LOW)
    match = CapabilityMatch(feasibility_score=0.5)
    result = await plan_agents(analysis, match)
    assert result.primary_agent_id == "CodeExecutionAgent"

async def test_plan_agents_unknown():
    analysis = TaskAnalysis(primary_intent="unknown", ambiguity_level=AmbiguityLevel.HIGH)
    match = CapabilityMatch(feasibility_score=1.0)
    result = await plan_agents(analysis, match)
    assert result.primary_agent_id == "GeneralAgent"

async def run_all():
    await test_plan_agents_fallback()
    await test_plan_agents_creation()
    await test_plan_agents_execution()
    await test_plan_agents_unknown()
    print("AGENT PLANNER TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
