from backend.apps.planner.models import (
    FinalResult, ActionType, ExecutionStatus, MonitorSignal
)
from backend.apps.planner.task_analyzer import analyze_task
from backend.apps.planner.capability_detector import detect_capabilities
from backend.apps.planner.agent_planner import plan_agents
from backend.apps.planner.model_router import route_model
from backend.apps.planner.context_planner import plan_context
from backend.apps.planner.tool_planner import plan_tools
from backend.apps.planner.execution_graph import build_execution_graph
from backend.apps.planner.runtime_monitor import evaluate_execution
from backend.apps.planner.adaptive_orchestrator import orchestrate
from backend.apps.planner.result_aggregator import aggregate_results

class PlannerPipeline:
    def __init__(self, mock_runtime_executor=None):
        """
        Initializes the planner pipeline.
        `mock_runtime_executor` is an optional async function that simulates
        the OpenSwarm runtime executing a node.
        """
        self.mock_runtime_executor = mock_runtime_executor

    async def _default_runtime_executor(self, node):
        """A simple mock execution to fall back on if none provided."""
        return {"status": "success", "data": f"Output from {node.agent_id} using {node.model_id}"}

    async def plan_and_execute(self, user_prompt: str, history: list[dict], session_id: str = None, emit_status=None) -> FinalResult:
        async def _emit(step: str, message: str):
            if emit_status:
                await emit_status(step, message)

        # Phase 1: Planning
        await _emit("TASK_ANALYZER", "Analyzing task intent...")
        task_analysis = await analyze_task(user_prompt, history)
        
        await _emit("CAPABILITY_DETECTOR", "Detecting required capabilities...")
        # In a real system, the registry would be fetched from the actual OpenSwarm tools
        mock_registry = {
            "web_search": ["web_search"],
            "code_execution": ["python_execution"],
            "creative_writing": ["creative_writing"]
        }
        capability_match = await detect_capabilities(task_analysis, mock_registry)
        
        await _emit("AGENT_PLANNER", "Selecting optimal agents...")
        agent_selection = await plan_agents(task_analysis, capability_match)
        
        await _emit("MODEL_ROUTER", "Routing to foundation model...")
        model_selection = await route_model(task_analysis, agent_selection)
        
        await _emit("CONTEXT_PLANNER", "Optimizing context window...")
        context_strategy = await plan_context(task_analysis, history)
        
        await _emit("TOOL_PLANNER", "Binding required tools...")
        tool_strategy = await plan_tools(task_analysis, capability_match)
        
        await _emit("EXECUTION_GRAPH", "Building execution DAG...")
        graph = await build_execution_graph(
            analysis=task_analysis,
            agent=agent_selection,
            model=model_selection,
            context=context_strategy,
            tools=tool_strategy
        )

        # Phase 2: Execution & Orchestration
        current_node_id = graph.entry_node_id
        execution_results = {}
        executor = self.mock_runtime_executor or self._default_runtime_executor

        max_steps = 10 # Circuit breaker
        steps = 0

        while current_node_id and steps < max_steps:
            steps += 1
            node = graph.nodes.get(current_node_id)
            if not node:
                break

            # 1. Execute
            await _emit("RUNTIME_MONITOR", f"Executing node {current_node_id}...")
            raw_result = await executor(node)

            # 2. Monitor
            await _emit("RUNTIME_MONITOR", f"Evaluating execution result...")
            signal = await evaluate_execution(node, raw_result)

            # 3. Store result if successful
            if signal.status == ExecutionStatus.SUCCESS:
                # We extract whatever string data we can from the mock result for aggregation
                output_str = raw_result.get("data", raw_result.get("error_message", str(raw_result)))
                execution_results[current_node_id] = output_str

            # 4. Orchestrate
            await _emit("ADAPTIVE_ORCHESTRATOR", f"Orchestrating next steps...")
            action = await orchestrate(graph, current_node_id, signal, model_selection)
            
            graph = action.updated_graph
            
            if action.action_type == ActionType.HALT:
                break
            elif action.action_type == ActionType.RETRY:
                # Add simple logic to avoid infinite retries
                if raw_result.get("_retried"):
                    # Force a halt or fallback next time if we retry too much
                    break
                # Simulating a retry by passing the same node ID back
                current_node_id = action.next_node_id
            else:
                # CONTINUE or FALLBACK
                current_node_id = action.next_node_id

        # Phase 3: Aggregation
        await _emit("RESULT_AGGREGATOR", "Aggregating final results...")
        final_result = await aggregate_results(execution_results, graph)
        
        await _emit("COMPLETE", "Planning pipeline complete.")
        return final_result
