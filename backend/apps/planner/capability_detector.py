from backend.apps.planner.models import TaskAnalysis, CapabilityMatch

async def detect_capabilities(analysis: TaskAnalysis, registry: dict) -> CapabilityMatch:
    """
    Verifies which required capabilities are supported by the system's 
    current registered tools, models, and agents.
    """
    if not analysis or not isinstance(analysis, TaskAnalysis):
        return CapabilityMatch(
            supported_capabilities=[],
            missing_capabilities=[],
            feasibility_score=0.0
        )

    required = set(analysis.required_capabilities)
    
    # If nothing is required, it's fully feasible
    if not required:
        return CapabilityMatch(
            supported_capabilities=[],
            missing_capabilities=[],
            feasibility_score=1.0
        )

    # Convert the registry values to a flat set of provided capabilities
    # We assume the mock registry looks like: {"tool_name": ["capability1", "capability2"]}
    provided = set()
    for caps in registry.values():
        if isinstance(caps, list):
            provided.update(caps)
            
    supported = required.intersection(provided)
    missing = required.difference(provided)
    
    score = len(supported) / len(required)

    return CapabilityMatch(
        supported_capabilities=list(supported),
        missing_capabilities=list(missing),
        feasibility_score=score
    )
