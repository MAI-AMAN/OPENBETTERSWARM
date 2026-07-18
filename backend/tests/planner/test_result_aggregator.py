import asyncio
from backend.apps.planner.models import ExecutionGraph, ExecutionNode, ContextStrategy
from backend.apps.planner.result_aggregator import aggregate_results

def create_mock_graph():
    node1 = ExecutionNode(
        node_id="node_1",
        agent_id="WebSearchAgent",
        model_id="test",
        tools=[],
        context_strategy=ContextStrategy()
    )
    node2 = ExecutionNode(
        node_id="node_2",
        agent_id="CodeExecutionAgent",
        model_id="test",
        tools=[],
        context_strategy=ContextStrategy()
    )
    return ExecutionGraph(
        entry_node_id="node_1",
        nodes={"node_1": node1, "node_2": node2},
        edges={}
    )

async def test_aggregate_empty():
    graph = create_mock_graph()
    results = {}
    
    final = await aggregate_results(results, graph)
    assert final.status == "failed"
    assert "No execution results" in final.aggregated_output
    assert final.node_count == 0

async def test_aggregate_no_real_output():
    graph = create_mock_graph()
    results = {"node_1": "   ", "node_2": None}
    
    final = await aggregate_results(results, graph)
    assert final.status == "completed"
    assert "no output was generated" in final.aggregated_output
    assert final.node_count == 0

async def test_aggregate_success():
    graph = create_mock_graph()
    results = {
        "node_1": "Found 10 results for Python web scraping.",
        "node_2": "Code executed successfully. Output: [1, 2, 3]"
    }
    
    final = await aggregate_results(results, graph)
    assert final.status == "completed"
    assert final.node_count == 2
    
    out = final.aggregated_output
    assert "### Output from WebSearchAgent" in out
    assert "Found 10 results for Python web scraping." in out
    assert "### Output from CodeExecutionAgent" in out
    assert "Code executed successfully." in out

async def run_all():
    await test_aggregate_empty()
    await test_aggregate_no_real_output()
    await test_aggregate_success()
    print("RESULT AGGREGATOR TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(run_all())
