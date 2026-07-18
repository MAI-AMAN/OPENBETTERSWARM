from backend.apps.planner.models import TaskAnalysis, CapabilityMatch, AgentSelection, DelegationStrategy

async def plan_agents(analysis: TaskAnalysis, match: CapabilityMatch) -> AgentSelection:
    """
    Determines the optimal agent or combination of agents to execute a given task.
    """
    if not match or match.feasibility_score == 0:
        return AgentSelection(
            primary_agent_id="FallbackAgent",
            sub_agent_ids=[],
            delegation_strategy=DelegationStrategy.SINGLE
        )

    intent = analysis.primary_intent if analysis else "unknown"

    if intent == "creation":
        primary = "CreativeAgent"
    elif intent == "execution":
        primary = "CodeExecutionAgent"
    elif intent == "debugging":
        primary = "DebugAgent"
    else:
        primary = "GeneralAgent"
        
    sub_agents = []
    strategy = DelegationStrategy.SINGLE
    
    # In the future, if capabilities require specialized sub-agents, we would 
    # append them to sub_agents and set strategy to PARALLEL or SEQUENTIAL.

    return AgentSelection(
        primary_agent_id=primary,
        sub_agent_ids=sub_agents,
        delegation_strategy=strategy
    )
