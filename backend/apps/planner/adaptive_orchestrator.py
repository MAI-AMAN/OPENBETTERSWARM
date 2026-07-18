import uuid
from backend.apps.planner.models import (
    ExecutionGraph, ExecutionNode, MonitorSignal, ModelSelection,
    ExecutionStatus, ActionType, OrchestrationAction
)

async def orchestrate(
    graph: ExecutionGraph,
    current_node_id: str,
    signal: MonitorSignal,
    model_plan: ModelSelection
) -> OrchestrationAction:
    """
    Adjusts the execution plan dynamically while the task is running by processing 
    signals from the Runtime Monitor.
    """
    if not graph or current_node_id not in graph.nodes:
        return OrchestrationAction(
            action_type=ActionType.HALT,
            updated_graph=graph,
            next_node_id=None
        )

    if signal.status == ExecutionStatus.SUCCESS:
        # Find next node if any
        next_nodes = graph.edges.get(current_node_id, [])
        if next_nodes:
            return OrchestrationAction(
                action_type=ActionType.CONTINUE,
                updated_graph=graph,
                next_node_id=next_nodes[0]
            )
        else:
            return OrchestrationAction(
                action_type=ActionType.CONTINUE,
                updated_graph=graph,
                next_node_id=None # Execution finished
            )
            
    elif signal.status == ExecutionStatus.RETRYING:
        return OrchestrationAction(
            action_type=ActionType.RETRY,
            updated_graph=graph,
            next_node_id=current_node_id
        )
        
    elif signal.status == ExecutionStatus.FAILED and signal.needs_fallback:
        current_node = graph.nodes[current_node_id]
        
        # If the failed node was ALREADY a fallback, HALT to prevent infinite fallback loops
        if current_node.agent_id == "FallbackAgent":
            return OrchestrationAction(
                action_type=ActionType.HALT,
                updated_graph=graph,
                next_node_id=None
            )

        fallback_node_id = f"node_{uuid.uuid4().hex[:8]}"
        
        fallback_node = ExecutionNode(
            node_id=fallback_node_id,
            agent_id="FallbackAgent",
            model_id=model_plan.fallback_model_id,
            tools=current_node.tools,
            context_strategy=current_node.context_strategy
        )
        
        # Mutate the graph
        graph.nodes[fallback_node_id] = fallback_node
        
        # Re-wire edges
        next_nodes = graph.edges.get(current_node_id, [])
        if next_nodes:
            graph.edges[fallback_node_id] = next_nodes
            
        # Optional: remove old edges/nodes to keep it clean, but preserving history is fine.
        
        return OrchestrationAction(
            action_type=ActionType.FALLBACK,
            updated_graph=graph,
            next_node_id=fallback_node_id
        )
        
    return OrchestrationAction(
        action_type=ActionType.HALT,
        updated_graph=graph,
        next_node_id=None
    )
