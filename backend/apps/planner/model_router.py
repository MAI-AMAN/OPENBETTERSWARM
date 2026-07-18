from backend.apps.planner.models import TaskAnalysis, AgentSelection, ModelSelection, ReasoningEffort, AmbiguityLevel

async def route_model(analysis: TaskAnalysis, agent: AgentSelection) -> ModelSelection:
    """
    Selects the most appropriate foundational LLM for the task based on latency constraints, 
    ambiguity, and the chosen agent's capabilities.
    """
    # Defaults
    model_id = "claude-3-5-sonnet-20241022"
    fallback_id = "claude-3-haiku-20240307"
    effort = ReasoningEffort.MEDIUM
    
    if not analysis:
        return ModelSelection(
            model_id=model_id,
            fallback_model_id=fallback_id,
            reasoning_effort=effort
        )

    is_latency_sensitive = "latency_sensitive" in analysis.constraints

    if is_latency_sensitive:
        model_id = "claude-3-haiku-20240307"
        effort = ReasoningEffort.LOW
    else:
        if analysis.ambiguity_level == AmbiguityLevel.HIGH:
            model_id = "claude-3-5-sonnet-20241022"
            effort = ReasoningEffort.HIGH
        elif analysis.ambiguity_level == AmbiguityLevel.LOW:
            model_id = "claude-3-haiku-20240307"
            effort = ReasoningEffort.LOW
            
    # Some specific agents might enforce model requirements (mock implementation)
    if agent and agent.primary_agent_id == "CodeExecutionAgent" and not is_latency_sensitive:
        model_id = "claude-3-5-sonnet-20241022"
        effort = ReasoningEffort.HIGH

    return ModelSelection(
        model_id=model_id,
        fallback_model_id=fallback_id,
        reasoning_effort=effort
    )
