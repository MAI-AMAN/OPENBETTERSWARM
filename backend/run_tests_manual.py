import asyncio
from backend.apps.planner.models import AmbiguityLevel
from backend.apps.planner.task_analyzer import analyze_task

async def test_analyze_task_creation():
    result = await analyze_task("Please create a simple react app", [])
    assert result.primary_intent == "creation", f"Got {result.primary_intent}"
    assert result.ambiguity_level == AmbiguityLevel.MEDIUM
    assert not result.required_capabilities

async def test_analyze_task_debugging():
    result = await analyze_task("fix the issue with the backend server", [])
    assert result.primary_intent == "debugging"

async def test_analyze_task_execution_and_capabilities():
    result = await analyze_task("run a web search script quickly", [])
    assert result.primary_intent == "execution"
    assert "web_search" in result.required_capabilities
    assert "code_execution" in result.required_capabilities
    assert "latency_sensitive" in result.constraints

async def test_analyze_task_empty():
    result = await analyze_task("", [])
    assert result.primary_intent == "unknown"
    assert result.ambiguity_level == AmbiguityLevel.HIGH

async def run_all():
    await test_analyze_task_creation()
    await test_analyze_task_debugging()
    await test_analyze_task_execution_and_capabilities()
    await test_analyze_task_empty()
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
