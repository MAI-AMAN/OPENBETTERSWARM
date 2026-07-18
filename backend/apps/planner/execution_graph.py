import uuid
from backend.apps.planner.models import (
    TaskAnalysis, AgentSelection, ModelSelection, ContextStrategy, ToolStrategy,
    ExecutionNode, ExecutionGraph, DelegationStrategy
)

async def build_execution_graph(
    analysis: TaskAnalysis, 
    agent: AgentSelection, 
    model: ModelSelection, 
    context: ContextStrategy, 
    tools: ToolStrategy
) -> ExecutionGraph:
    """
    Synthesizes the Agent, Model, Context, and Tool strategies into a formalized, 
    topologically sorted execution graph (DAG) ready for the Runtime.
    """
    if not agent or not model or not context or not tools:
        # Failsafe fallback
        fallback_id = "node_fallback"
        return ExecutionGraph(
            entry_node_id=fallback_id,
            nodes={
                fallback_id: ExecutionNode(
                    node_id=fallback_id,
                    agent_id="FallbackAgent",
                    model_id="claude-3-haiku-20240307",
                    tools=[],
                    context_strategy=ContextStrategy()
                )
            },
            edges={}
        )

    nodes = {}
    edges = {}

    primary_node_id = f"node_{uuid.uuid4().hex[:8]}"
    
    primary_node = ExecutionNode(
        node_id=primary_node_id,
        agent_id=agent.primary_agent_id,
        model_id=model.model_id,
        tools=tools.recommended_tool_ids,
        context_strategy=context
    )
    nodes[primary_node_id] = primary_node

    entry_node_id = primary_node_id
    
    # If there's a sequential delegation strategy
    if agent.delegation_strategy == DelegationStrategy.SEQUENTIAL and agent.sub_agent_ids:
        previous_node_id = primary_node_id
        
        for sub_agent in agent.sub_agent_ids:
            sub_node_id = f"node_{uuid.uuid4().hex[:8]}"
            # For this simple prototype, sub-agents inherit the same model and context/tools
            sub_node = ExecutionNode(
                node_id=sub_node_id,
                agent_id=sub_agent,
                model_id=model.model_id,
                tools=tools.recommended_tool_ids,
                context_strategy=context
            )
            nodes[sub_node_id] = sub_node
            
            if previous_node_id not in edges:
                edges[previous_node_id] = []
            edges[previous_node_id].append(sub_node_id)
            
            previous_node_id = sub_node_id

    return ExecutionGraph(
        entry_node_id=entry_node_id,
        nodes=nodes,
        edges=edges
    )
