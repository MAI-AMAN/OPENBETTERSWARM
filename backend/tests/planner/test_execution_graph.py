import asyncio
from backend.apps.planner.models import (
    TaskAnalysis, AgentSelection, ModelSelection, ContextStrategy, ToolStrategy,
    DelegationStrategy
)
from backend.apps.planner.execution_graph import build_execution_graph

async def test_build_execution_graph_single():
    analysis = TaskAnalysis(primary_intent="execution")
    agent = AgentSelection(primary_agent_id="CodeExecutionAgent", delegation_strategy=DelegationStrategy.SINGLE)
    model = ModelSelection(model_id="claude-3-haiku-20240307")
    context = ContextStrategy(include_history=True)
    tools = ToolStrategy(recommended_tool_ids=["run_command"])
    
    graph = await build_execution_graph(analysis, agent, model, context, tools)
    
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0
    
    node = graph.nodes[graph.entry_node_id]
    assert node.agent_id == "CodeExecutionAgent"
    assert node.model_id == "claude-3-haiku-20240307"
    assert "run_command" in node.tools

async def test_build_execution_graph_sequential():
    analysis = TaskAnalysis(primary_intent="execution")
    agent = AgentSelection(
        primary_agent_id="CodeExecutionAgent", 
        sub_agent_ids=["ReviewAgent", "TestAgent"],
        delegation_strategy=DelegationStrategy.SEQUENTIAL
    )
    model = ModelSelection(model_id="claude-3-5-sonnet-20241022")
    context = ContextStrategy()
    tools = ToolStrategy()
    
    graph = await build_execution_graph(analysis, agent, model, context, tools)
    
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    
    # Check edges
    entry_node = graph.entry_node_id
    assert entry_node in graph.edges
    
    second_node = graph.edges[entry_node][0]
    assert second_node in graph.edges
    
    third_node = graph.edges[second_node][0]
    assert third_node not in graph.edges
    
    # Check agents
    assert graph.nodes[entry_node].agent_id == "CodeExecutionAgent"
    assert graph.nodes[second_node].agent_id == "ReviewAgent"
    assert graph.nodes[third_node].agent_id == "TestAgent"


async def run_all():
    await test_build_execution_graph_single()
    await test_build_execution_graph_sequential()
    print("EXECUTION GRAPH TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
