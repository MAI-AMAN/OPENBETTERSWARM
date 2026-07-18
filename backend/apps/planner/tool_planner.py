import json
import logging
from backend.apps.planner.models import TaskAnalysis, CapabilityMatch, ToolStrategy

logger = logging.getLogger(__name__)

async def plan_tools(analysis: TaskAnalysis, match: CapabilityMatch) -> ToolStrategy:
    """
    Determines the minimal necessary set of tools to bind to the agent's prompt.
    """
    if not analysis or not match:
        return ToolStrategy(
            recommended_tool_ids=[],
            restricted_tool_ids=["*"],
            strict_mode=True
        )

    try:
        from backend.apps.settings.settings import load_settings
        from backend.apps.settings.credentials import get_anthropic_client_for_model
        from backend.apps.agents.providers.registry import resolve_aux_model
        from backend.apps.agents.core.aux_llm import aux_max_tokens_for
        from backend.apps.agents.manager.prompt.tool_catalog import get_all_tool_names
        
        global_settings = load_settings()
        aux_models = await resolve_aux_model(
            global_settings,
            preferred_tier="haiku",
            primary_api=None,
        )
        if not aux_models:
            raise ValueError("No auxiliary model available for tool planning")
            
        aux_model = aux_models[0]
        client = get_anthropic_client_for_model(global_settings, aux_model)
        
        all_tools = get_all_tool_names()
        
        system_prompt = (
            "You are an expert system orchestrator. Your job is to select the absolute minimum "
            "set of tools needed to accomplish a task based on its capabilities and constraints.\n"
            "You MUST return ONLY a valid JSON object matching the following schema. Do NOT wrap it in markdown block quotes. "
            "Do NOT include any explanations or other text.\n\n"
            "Schema:\n"
            "{\n"
            '  "recommended_tool_ids": ["string", "string"], // The specific tools needed\n'
            '  "restricted_tool_ids": ["string", "string"], // Tools explicitly forbidden by constraints\n'
            '  "strict_mode": true | false // True if ONLY recommended tools should be allowed, else False\n'
            "}\n\n"
            "Instructions:\n"
            "- 'strict_mode' should be true if constraints include 'safe_mode', 'read_only', etc.\n"
            "- 'restricted_tool_ids' should include 'Write', 'Edit', 'Bash', 'NotebookEdit', 'TodoWrite' if 'read_only' or 'safe_mode' is in constraints.\n"
            "- For 'code_execution', recommend 'Bash'. For 'web_search', recommend 'WebSearch'.\n"
            f"- You can only select tools from this list: {all_tools}\n"
        )
        
        user_content = (
            f"Intent: {analysis.primary_intent}\n"
            f"Constraints: {analysis.constraints}\n"
            f"Supported Capabilities: {match.supported_capabilities}\n"
            "Select the necessary tools."
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
        
        return ToolStrategy(
            recommended_tool_ids=data.get("recommended_tool_ids", []),
            restricted_tool_ids=data.get("restricted_tool_ids", []),
            strict_mode=data.get("strict_mode", False)
        )
        
    except Exception as e:
        logger.warning(f"[PLANNER] LLM ToolPlanner failed, falling back to heuristic: {e}")
        return _plan_tools_heuristic(analysis, match)


def _plan_tools_heuristic(analysis: TaskAnalysis, match: CapabilityMatch) -> ToolStrategy:
    recommended = []
    restricted = []
    strict_mode = False

    # Apply constraints
    if "safe_mode" in analysis.constraints or "read_only" in analysis.constraints:
        strict_mode = True
        restricted.extend(["Write", "Edit", "Bash", "NotebookEdit", "TodoWrite"])

    # Map capabilities to tools
    if "code_execution" in match.supported_capabilities:
        if "Bash" not in restricted:
            recommended.append("Bash")
        if "PythonExecution" not in restricted:
            recommended.append("PythonExecution")
            
    if "web_search" in match.supported_capabilities:
        if "WebSearch" not in restricted:
            recommended.append("WebSearch")
            
    if analysis.primary_intent == "creation":
        if "Write" not in restricted:
            recommended.append("Write")
        if "Edit" not in restricted:
            recommended.append("Edit")

    return ToolStrategy(
        recommended_tool_ids=recommended,
        restricted_tool_ids=restricted,
        strict_mode=strict_mode
    )
