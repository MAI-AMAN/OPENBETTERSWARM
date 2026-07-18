from backend.apps.planner.models import TaskAnalysis, AmbiguityLevel
import json
import logging

logger = logging.getLogger(__name__)

async def analyze_task(prompt: str, history: list) -> TaskAnalysis:
    """
    Parses the raw user input to determine the core intent, constraints, 
    requested outputs, and any implicit requirements.
    """
    if not prompt or not prompt.strip():
        return TaskAnalysis(
            primary_intent="unknown",
            constraints=[],
            required_capabilities=[],
            ambiguity_level=AmbiguityLevel.HIGH
        )

    try:
        from backend.apps.settings.settings import load_settings
        from backend.apps.settings.credentials import get_anthropic_client_for_model
        from backend.apps.agents.providers.registry import resolve_aux_model
        from backend.apps.agents.core.aux_llm import aux_max_tokens_for
        
        global_settings = load_settings()
        # Resolve to a fast auxiliary model (preferring haiku)
        aux_models = await resolve_aux_model(
            global_settings,
            preferred_tier="haiku",
            primary_api=None,
        )
        if not aux_models:
            raise ValueError("No auxiliary model available for task analysis")
        
        aux_model = aux_models[0]
        client = get_anthropic_client_for_model(global_settings, aux_model)
        
        system_prompt = (
            "You are an expert system orchestrator. Your job is to analyze the user's request and classify its intent. "
            "You MUST return ONLY a valid JSON object matching the following schema. Do NOT wrap it in markdown block quotes. "
            "Do NOT include any explanations or other text.\n\n"
            "Schema:\n"
            "{\n"
            '  "primary_intent": "string (e.g. informational, creation, debugging, execution)",\n'
            '  "constraints": ["string", "string"],\n'
            '  "required_capabilities": ["string", "string"],\n'
            '  "ambiguity_level": "LOW" | "MEDIUM" | "HIGH"\n'
            "}"
        )
        
        # We only pass the latest prompt and optionally recent history to keep it fast
        recent_history = history[-3:] if history else []
        history_context = ""
        if recent_history:
            history_context = "Recent Conversation History:\n"
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                history_context += f"{role.capitalize()}: {content}\n"
            history_context += "\n"

        user_content = (
            f"{history_context}"
            f"User Request to Analyze:\n{prompt[:2000]}"
        )
        
        response = await client.messages.create(
            model=aux_model,
            max_tokens=aux_max_tokens_for(aux_model, base=300),
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            timeout=2.0
        )
        
        raw_text = response.content[0].text
        
        # Try to clean up markdown if the LLM hallucinated it
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        
        # Normalize ambiguity level
        ambiguity_str = data.get("ambiguity_level", "HIGH").upper()
        if ambiguity_str not in [a.value for a in AmbiguityLevel]:
            ambiguity_str = "HIGH"
            
        return TaskAnalysis(
            primary_intent=data.get("primary_intent", "unknown"),
            constraints=data.get("constraints", []),
            required_capabilities=data.get("required_capabilities", []),
            ambiguity_level=AmbiguityLevel(ambiguity_str)
        )
        
    except Exception as e:
        logger.warning(f"[PLANNER] LLM TaskAnalyzer failed, falling back to heuristic: {e}")
        return _analyze_task_heuristic(prompt)

def _analyze_task_heuristic(prompt: str) -> TaskAnalysis:
    prompt_lower = prompt.lower()
    
    # 1. Extract Intent (Basic heuristic)
    primary_intent = "informational"
    if any(word in prompt_lower for word in ["create", "build", "make", "generate", "write"]):
        primary_intent = "creation"
    elif any(word in prompt_lower for word in ["fix", "debug", "error", "issue", "broken"]):
        primary_intent = "debugging"
    elif any(word in prompt_lower for word in ["run", "execute", "start"]):
        primary_intent = "execution"

    # 2. Extract Constraints
    constraints = []
    if "fast" in prompt_lower or "quickly" in prompt_lower:
        constraints.append("latency_sensitive")
    if "no" in prompt_lower and "code" in prompt_lower:
        constraints.append("no_code_changes")

    # 3. Required Capabilities
    capabilities = []
    if "search" in prompt_lower or "web" in prompt_lower:
        capabilities.append("web_search")
    if "run" in prompt_lower or "script" in prompt_lower or "command" in prompt_lower:
        capabilities.append("code_execution")
        
    # 4. Ambiguity Level
    words = prompt.split()
    if len(words) < 3 and not capabilities:
        ambiguity = AmbiguityLevel.HIGH
    elif len(words) > 15 and (constraints or capabilities):
        ambiguity = AmbiguityLevel.LOW
    else:
        ambiguity = AmbiguityLevel.MEDIUM

    return TaskAnalysis(
        primary_intent=primary_intent,
        constraints=constraints,
        required_capabilities=capabilities,
        ambiguity_level=ambiguity
    )
