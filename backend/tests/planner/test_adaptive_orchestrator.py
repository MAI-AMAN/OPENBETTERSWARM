import asyncio
from backend.apps.planner.models import (
    ExecutionGraph, ExecutionNode, ContextStrategy, ExecutionStatus,
    MonitorSignal, ModelSelection, ActionType
)
from backend.apps.planner.adaptive_orchestrator import orchestrate

def create_mock_graph():
    node1 = ExecutionNode(
        node_id="node_1",
        agent_id="Agent1",
        model_id="model-1",
        tools=[],
        context_strategy=ContextStrategy()
    )
    node2 = ExecutionNode(
        node_id="node_2",
        agent_id="Agent2",
        model_id="model-1",
        tools=[],
        context_strategy=ContextStrategy()
    )
    return ExecutionGraph(
        entry_node_id="node_1",
        nodes={"node_1": node1, "node_2": node2},
        edges={"node_1": ["node_2"]}
    )

async def test_orchestrate_continue():
    graph = create_mock_graph()
    signal = MonitorSignal(status=ExecutionStatus.SUCCESS)
    model = ModelSelection(model_id="model-1")
    
    action = await orchestrate(graph, "node_1", signal, model)
    assert action.action_type == ActionType.CONTINUE
    assert action.next_node_id == "node_2"

async def test_orchestrate_finish():
    graph = create_mock_graph()
    signal = MonitorSignal(status=ExecutionStatus.SUCCESS)
    model = ModelSelection(model_id="model-1")
    
    action = await orchestrate(graph, "node_2", signal, model)
    assert action.action_type == ActionType.CONTINUE
    assert action.next_node_id is None

async def test_orchestrate_retry():
    graph = create_mock_graph()
    signal = MonitorSignal(status=ExecutionStatus.RETRYING)
    model = ModelSelection(model_id="model-1")
    
    action = await orchestrate(graph, "node_1", signal, model)
    assert action.action_type == ActionType.RETRY
    assert action.next_node_id == "node_1"

async def test_orchestrate_fallback():
    graph = create_mock_graph()
    signal = MonitorSignal(status=ExecutionStatus.FAILED, needs_fallback=True)
    model = ModelSelection(model_id="model-1", fallback_model_id="fallback-model")
    
    action = await orchestrate(graph, "node_1", signal, model)
    assert action.action_type == ActionType.FALLBACK
    assert action.next_node_id is not None
    assert action.next_node_id != "node_1"
    
    # Verify graph mutation
    assert action.next_node_id in action.updated_graph.nodes
    assert action.updated_graph.nodes[action.next_node_id].agent_id == "FallbackAgent"
    assert action.updated_graph.nodes[action.next_node_id].model_id == "fallback-model"
    # Edges rewired
    assert action.next_node_id in action.updated_graph.edges
    assert action.updated_graph.edges[action.next_node_id] == ["node_2"]

async def run_all():
    await test_orchestrate_continue()
    await test_orchestrate_finish()
    await test_orchestrate_retry()
    await test_orchestrate_fallback()
    print("ADAPTIVE ORCHESTRATOR TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
