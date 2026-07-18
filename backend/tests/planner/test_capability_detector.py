import asyncio
from backend.apps.planner.models import TaskAnalysis, AmbiguityLevel
from backend.apps.planner.capability_detector import detect_capabilities

async def test_detect_capabilities_all_supported():
    analysis = TaskAnalysis(
        primary_intent="execution",
        required_capabilities=["code_execution", "web_search"],
        ambiguity_level=AmbiguityLevel.LOW
    )
    registry = {
        "python_repl": ["code_execution", "data_analysis"],
        "google_search": ["web_search"]
    }
    result = await detect_capabilities(analysis, registry)
    assert result.feasibility_score == 1.0
    assert "code_execution" in result.supported_capabilities
    assert "web_search" in result.supported_capabilities
    assert len(result.missing_capabilities) == 0

async def test_detect_capabilities_partially_supported():
    analysis = TaskAnalysis(
        primary_intent="execution",
        required_capabilities=["code_execution", "image_generation"],
        ambiguity_level=AmbiguityLevel.LOW
    )
    registry = {
        "python_repl": ["code_execution"]
    }
    result = await detect_capabilities(analysis, registry)
    assert result.feasibility_score == 0.5
    assert "code_execution" in result.supported_capabilities
    assert "image_generation" in result.missing_capabilities

async def test_detect_capabilities_empty():
    analysis = TaskAnalysis(
        primary_intent="creation",
        required_capabilities=[],
        ambiguity_level=AmbiguityLevel.HIGH
    )
    registry = {}
    result = await detect_capabilities(analysis, registry)
    assert result.feasibility_score == 1.0
    assert len(result.supported_capabilities) == 0
    assert len(result.missing_capabilities) == 0

async def run_all():
    await test_detect_capabilities_all_supported()
    await test_detect_capabilities_partially_supported()
    await test_detect_capabilities_empty()
    print("CAPABILITY DETECTOR TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
