from enum import Enum
from pydantic import BaseModel, Field

class AmbiguityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TaskAnalysis(BaseModel):
    primary_intent: str = Field(..., description="The main intent of the user request")
    constraints: list[str] = Field(default_factory=list, description="Explicit constraints in the request")
    required_capabilities: list[str] = Field(default_factory=list, description="Capabilities needed to fulfill the request")
    ambiguity_level: AmbiguityLevel = Field(default=AmbiguityLevel.HIGH, description="The ambiguity level of the request")

class CapabilityMatch(BaseModel):
    supported_capabilities: list[str] = Field(default_factory=list, description="Capabilities supported by the system")
    missing_capabilities: list[str] = Field(default_factory=list, description="Capabilities requested but not supported")
    feasibility_score: float = Field(default=0.0, description="Score from 0.0 to 1.0 indicating if request is feasible")

class DelegationStrategy(str, Enum):
    SINGLE = "SINGLE"
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"

class AgentSelection(BaseModel):
    primary_agent_id: str = Field(..., description="The main agent assigned to the task")
    sub_agent_ids: list[str] = Field(default_factory=list, description="Optional sub-agents to delegate to")
    delegation_strategy: DelegationStrategy = Field(default=DelegationStrategy.SINGLE, description="How multiple agents will coordinate")

class ReasoningEffort(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ModelSelection(BaseModel):
    model_id: str = Field(..., description="The primary model selected for the task")
    fallback_model_id: str = Field(default="claude-3-haiku-20240307", description="Fallback model if primary fails")
    reasoning_effort: ReasoningEffort = Field(default=ReasoningEffort.MEDIUM, description="Reasoning effort requested from the model")

class ContextStrategy(BaseModel):
    include_history: bool = Field(default=True, description="Whether to inject past conversation turns")
    required_context_types: list[str] = Field(default_factory=list, description="Specific context domains to load (e.g. workspace_files, system_memory)")
    max_context_tokens: int = Field(default=8000, description="Token limit for the context payload")

class ToolStrategy(BaseModel):
    recommended_tool_ids: list[str] = Field(default_factory=list, description="Tools that should be attached to the agent")
    restricted_tool_ids: list[str] = Field(default_factory=list, description="Tools explicitly blocked from being used")
    strict_mode: bool = Field(default=False, description="If true, only recommended_tool_ids can be used")

class ExecutionNode(BaseModel):
    node_id: str = Field(..., description="Unique identifier for this node")
    agent_id: str = Field(..., description="The agent to execute this step")
    model_id: str = Field(..., description="The model to use")
    tools: list[str] = Field(default_factory=list, description="Tools available for this node")
    context_strategy: ContextStrategy = Field(..., description="Context strategy for this node")

class ExecutionGraph(BaseModel):
    entry_node_id: str = Field(..., description="The ID of the first node to execute")
    nodes: dict[str, ExecutionNode] = Field(default_factory=dict, description="Map of node ID to ExecutionNode")
    edges: dict[str, list[str]] = Field(default_factory=dict, description="Map of node ID to a list of subsequent node IDs")

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class MonitorSignal(BaseModel):
    status: ExecutionStatus = Field(..., description="The evaluated status of the execution")
    needs_fallback: bool = Field(default=False, description="Whether the orchestrator should invoke a fallback strategy")
    error_context: str = Field(default="", description="Contextual information about the failure, if any")

class ActionType(str, Enum):
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    HALT = "HALT"

class OrchestrationAction(BaseModel):
    action_type: ActionType = Field(..., description="The action the runtime should take next")
    updated_graph: ExecutionGraph = Field(..., description="The (potentially mutated) graph state")
    next_node_id: str | None = Field(default=None, description="The ID of the next node to execute")

class FinalResult(BaseModel):
    status: str = Field(..., description="Status of the final payload, e.g. 'completed', 'failed'")
    aggregated_output: str = Field(..., description="The unified response string")
    node_count: int = Field(default=0, description="The number of nodes that successfully contributed to the output")
