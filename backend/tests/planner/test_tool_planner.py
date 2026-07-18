import pytest
import asyncio
from backend.apps.planner.models import TaskAnalysis, CapabilityMatch
from backend.apps.planner.tool_planner import plan_tools

@pytest.mark.asyncio
async def test_plan_tools_execution():
    analysis = TaskAnalysis(primary_intent="execution")
    match = CapabilityMatch(supported_capabilities=["code_execution", "web_search"])
    result = await plan_tools(analysis, match)
    assert "Bash" in result.recommended_tool_ids
    assert "WebSearch" in result.recommended_tool_ids
    assert result.strict_mode is False
    assert len(result.restricted_tool_ids) == 0

@pytest.mark.asyncio
async def test_plan_tools_read_only():
    analysis = TaskAnalysis(primary_intent="execution", constraints=["read_only"])
    match = CapabilityMatch(supported_capabilities=["code_execution"])
    result = await plan_tools(analysis, match)
    assert "Bash" not in result.recommended_tool_ids
    assert result.strict_mode is True
    assert "Write" in result.restricted_tool_ids
    assert "Bash" in result.restricted_tool_ids

async def run_all():
    await test_plan_tools_execution()
    await test_plan_tools_read_only()
    print("TOOL PLANNER TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
