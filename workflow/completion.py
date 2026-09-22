from shared_types.completion_status import CompletionStatus

from shared_types.step_status import StepStatus

from shared_types.failure_classifier import (
    is_recoverable_failure,
    is_nonrecoverable_failure,
)


def _active_execution(state):

    current_task_id = state.get(
        "current_agent_task_id"
    )

    steps = state.get(
        "steps",
        [],
    )

    tool_results = state.get(
        "tool_results",
        {},
    )

    if current_task_id is None:
        return steps, tool_results

    active_steps = [
        step
        for step in steps
        if step.agent_task_id == current_task_id
    ]

    active_step_ids = {
        step.id
        for step in active_steps
    }

    active_tool_results = {
        step_id: result
        for step_id, result in tool_results.items()
        if step_id in active_step_ids
    }

    return (
        active_steps,
        active_tool_results,
    )


def completion_node(state):

    steps, tool_results = _active_execution(
        state
    )

    # ---------------------------------
    # Recoverable failures → REPLAN
    # ---------------------------------

    for result in tool_results.values():

        status = result["status"]

        if (
            status == StepStatus.FAILED
            and is_recoverable_failure(
                result.get("failure_reason")
            )
        ):

            return {
                "completion_status":
                CompletionStatus.REPLAN
            }

    # ---------------------------------
    # Non-recoverable failures → FAILED
    # ---------------------------------

    for result in tool_results.values():

        status = result["status"]

        if (
            status == StepStatus.FAILED
            and is_nonrecoverable_failure(
                result.get("failure_reason")
            )
        ):

            return {
                "completion_status":
                CompletionStatus.FAILED
            }

    # ---------------------------------
    # Pending work → CONTINUE
    # ---------------------------------

    if len(tool_results) < len(steps):

        return {
            "completion_status":
            CompletionStatus.CONTINUE
        }

    # ---------------------------------
    # Current AgentTask execution complete
    # ---------------------------------

    return {
        "completion_status":
        CompletionStatus.COMPLETE
    }