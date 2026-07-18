import pytest
import asyncio
from backend.apps.planner.planner_pipeline import PlannerPipeline

async def mock_successful_executor(node):
    return {"status": "success", "data": f"Success from {node.agent_id}!"}

async def mock_failing_executor(node):
    if node.agent_id == "FallbackAgent":
        return {"status": "success", "data": "Fallback agent saved the day!"}
    return {"status": "error", "error_type": "logic_error"}

@pytest.mark.asyncio
async def test_successful_pipeline():
    pipeline = PlannerPipeline(mock_runtime_executor=mock_successful_executor)
    
    # We pass a simple prompt that should route to CreativeAgent or CodeExecutionAgent
    prompt = "Can you write a python script to reverse a string?"
    history = []
    
    result = await pipeline.plan_and_execute(prompt, history)
    
    assert result.status == "completed"
    assert result.node_count > 0
    assert "Success from" in result.aggregated_output
    assert "### Output from" in result.aggregated_output

@pytest.mark.asyncio
async def test_fallback_pipeline():
    pipeline = PlannerPipeline(mock_runtime_executor=mock_failing_executor)
    
    prompt = "Do some task that will fail"
    history = []
    
    result = await pipeline.plan_and_execute(prompt, history)
    
    assert result.status == "completed"
    assert result.node_count > 0
    assert "### Output from FallbackAgent" in result.aggregated_output
    assert "Fallback agent saved the day!" in result.aggregated_output

async def run_all():
    await test_successful_pipeline()
    await test_fallback_pipeline()
    print("PLANNER PIPELINE TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
