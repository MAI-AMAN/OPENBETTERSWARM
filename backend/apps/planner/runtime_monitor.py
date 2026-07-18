from backend.apps.planner.models import ExecutionNode, ExecutionStatus, MonitorSignal

async def evaluate_execution(node: ExecutionNode, simulated_result: dict) -> MonitorSignal:
    """
    Observes the result of an executed node and generates structured signals 
    (success, failure, retry, fallback) to guide the Adaptive Orchestrator.
    """
    if not isinstance(simulated_result, dict) or "status" not in simulated_result:
        return MonitorSignal(
            status=ExecutionStatus.FAILED,
            needs_fallback=True,
            error_context="Unparseable result or missing status key."
        )

    status = simulated_result.get("status")

    if status == "success":
        return MonitorSignal(
            status=ExecutionStatus.SUCCESS,
            needs_fallback=False,
            error_context=""
        )
    elif status == "error":
        error_type = simulated_result.get("error_type", "unknown")
        error_message = simulated_result.get("error_message", "An unknown error occurred.")
        
        if error_type in ["rate_limit", "timeout"]:
            return MonitorSignal(
                status=ExecutionStatus.RETRYING,
                needs_fallback=True,
                error_context=f"Systemic failure detected: {error_type}. {error_message}"
            )
        else:
            return MonitorSignal(
                status=ExecutionStatus.FAILED,
                needs_fallback=True,
                error_context=f"Logical failure detected: {error_type}. {error_message}"
            )

    return MonitorSignal(
        status=ExecutionStatus.FAILED,
        needs_fallback=True,
        error_context=f"Unknown status type: {status}"
    )
