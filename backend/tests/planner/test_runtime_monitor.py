import asyncio
from backend.apps.planner.models import ExecutionNode, ContextStrategy, ExecutionStatus
from backend.apps.planner.runtime_monitor import evaluate_execution

def mock_node():
    return ExecutionNode(
        node_id="test_node",
        agent_id="TestAgent",
        model_id="test-model",
        tools=[],
        context_strategy=ContextStrategy()
    )

async def test_evaluate_success():
    node = mock_node()
    result = {"status": "success", "data": "all good"}
    
    signal = await evaluate_execution(node, result)
    assert signal.status == ExecutionStatus.SUCCESS
    assert signal.needs_fallback is False

async def test_evaluate_systemic_error():
    node = mock_node()
    result = {"status": "error", "error_type": "rate_limit", "error_message": "Too many requests"}
    
    signal = await evaluate_execution(node, result)
    assert signal.status == ExecutionStatus.RETRYING
    assert signal.needs_fallback is True
    assert "rate_limit" in signal.error_context

async def test_evaluate_logic_error():
    node = mock_node()
    result = {"status": "error", "error_type": "context_length_exceeded", "error_message": "Prompt too long"}
    
    signal = await evaluate_execution(node, result)
    assert signal.status == ExecutionStatus.FAILED
    assert signal.needs_fallback is True
    assert "context_length_exceeded" in signal.error_context

async def test_evaluate_malformed():
    node = mock_node()
    result = {"bad": "data"}
    
    signal = await evaluate_execution(node, result)
    assert signal.status == ExecutionStatus.FAILED
    assert signal.needs_fallback is True
    assert "Unparseable" in signal.error_context

async def run_all():
    await test_evaluate_success()
    await test_evaluate_systemic_error()
    await test_evaluate_logic_error()
    await test_evaluate_malformed()
    print("RUNTIME MONITOR TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
