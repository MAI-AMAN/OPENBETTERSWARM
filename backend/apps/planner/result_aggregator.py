from backend.apps.planner.models import ExecutionGraph, FinalResult

async def aggregate_results(execution_results: dict[str, str], graph: ExecutionGraph) -> FinalResult:
    """
    Collects and formats the execution results from all nodes in the DAG 
    into a single, cohesive response payload to be returned to the frontend/user.
    """
    if not execution_results:
        return FinalResult(
            status="failed",
            aggregated_output="No execution results provided.",
            node_count=0
        )

    aggregated = []
    node_count = 0

    # Ensure we iterate in some predictable order, e.g. nodes present in the graph
    # or just iterate through the keys if not in graph.
    for node_id, output in execution_results.items():
        # Clean up empty strings or None
        if not output or not str(output).strip():
            continue

        agent_id = "UnknownAgent"
        if graph and node_id in graph.nodes:
            agent_id = graph.nodes[node_id].agent_id
            
        header = f"### Output from {agent_id}"
        aggregated.append(header)
        aggregated.append(str(output).strip())
        aggregated.append("") # blank line for spacing
        
        node_count += 1

    if node_count == 0:
        return FinalResult(
            status="completed",
            aggregated_output="Execution finished, but no output was generated.",
            node_count=0
        )

    return FinalResult(
        status="completed",
        aggregated_output="\n".join(aggregated).strip(),
        node_count=node_count
    )
