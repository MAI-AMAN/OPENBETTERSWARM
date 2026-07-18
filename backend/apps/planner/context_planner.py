import json
import logging
from backend.apps.planner.models import TaskAnalysis, AgentSelection, ContextStrategy

logger = logging.getLogger(__name__)

async def plan_context(analysis: TaskAnalysis, agent: AgentSelection) -> ContextStrategy:
    """
    Determines what specific contextual information must be injected into the 
    agent's prompt to successfully execute the task.
    """
    if not analysis:
        return ContextStrategy(
            include_history=True,
            required_context_types=[],
            max_context_tokens=8000
        )

    try:
        from backend.apps.settings.settings import load_settings
        from backend.apps.settings.credentials import get_anthropic_client_for_model
        from backend.apps.agents.providers.registry import resolve_aux_model
        from backend.apps.agents.core.aux_llm import aux_max_tokens_for
        
        global_settings = load_settings()
        aux_models = await resolve_aux_model(
            global_settings,
            preferred_tier="haiku",
            primary_api=None,
        )
        if not aux_models:
            raise ValueError("No auxiliary model available for context planning")
            
        aux_model = aux_models[0]
        client = get_anthropic_client_for_model(global_settings, aux_model)
        
        system_prompt = (
            "You are an expert system orchestrator. Your job is to determine the necessary context "
            "and history needed for an AI agent to accomplish a given task based on its intent and constraints.\n"
            "You MUST return ONLY a valid JSON object matching the following schema. Do NOT wrap it in markdown block quotes. "
            "Do NOT include any explanations or other text.\n\n"
            "Schema:\n"
            "{\n"
            '  "include_history": true | false, // True if past conversation history is needed\n'
            '  "required_context_types": ["string", "string"], // Which types of context to load (e.g., "workspace_files", "user_preferences", "system_memory")\n'
            '  "max_context_tokens": 8000 // Maximum tokens to allow for context (default 8000, lower to 2000 if latency_sensitive)\n'
            "}\n\n"
            "Instructions:\n"
            "- If 'latency_sensitive' is in constraints, reduce 'max_context_tokens' to 2000.\n"
            "- For 'execution' or 'debugging' intents, include 'workspace_files'.\n"
            "- For 'creation' intent, include 'user_preferences' and 'system_memory'.\n"
        )
        
        user_content = (
            f"Intent: {analysis.primary_intent}\n"
            f"Constraints: {analysis.constraints}\n"
            f"Selected Agent ID: {agent.primary_agent_id}\n"
            "Determine the required context strategy."
        )
        
        response = await client.messages.create(
            model=aux_model,
            max_tokens=aux_max_tokens_for(aux_model, base=300),
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            timeout=2.0
        )
        
        raw_text = response.content[0].text
        
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        
        return ContextStrategy(
            include_history=data.get("include_history", True),
            required_context_types=data.get("required_context_types", []),
            max_context_tokens=data.get("max_context_tokens", 8000)
        )
        
    except Exception as e:
        logger.warning(f"[PLANNER] LLM ContextPlanner failed, falling back to heuristic: {e}")
        return _plan_context_heuristic(analysis, agent)


def _plan_context_heuristic(analysis: TaskAnalysis, agent: AgentSelection) -> ContextStrategy:
    include_history = True
    max_tokens = 8000
    context_types = []
    
    intent = analysis.primary_intent

    if intent in ["execution", "debugging"]:
        context_types.append("workspace_files")
        
    if intent == "creation":
        context_types.append("user_preferences")
        context_types.append("system_memory")

    # Adjust token limits based on constraints
    if "latency_sensitive" in analysis.constraints:
        max_tokens = 2000

    return ContextStrategy(
        include_history=include_history,
        required_context_types=context_types,
        max_context_tokens=max_tokens
    )
