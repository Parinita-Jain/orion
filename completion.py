from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus
from shared_types.failure_classifier import (
    is_recoverable_failure,
    is_nonrecoverable_failure,
)


def completion_node(state):

    tool_results = state.get("tool_results", {})
    steps = state.get("steps", [])

    # ---------------------------------
    # Recoverable failures → REPLAN
    # ---------------------------------

    for result in tool_results.values():

        if (
            result["status"] == StepStatus.FAILED
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

        if (
            result["status"] == StepStatus.FAILED
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
    # Workflow complete
    # ---------------------------------

    return {
        "completion_status":
        CompletionStatus.COMPLETE
    }