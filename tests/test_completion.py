from completion import completion_node

from shared_types.completion_status import CompletionStatus
from shared_types.failure_reason import FailureReason
from shared_types.step_status import StepStatus

def test_completion_when_workflow_complete():

    state = {
        "tool_results": {
            1: {
                "success": True,
                "status": StepStatus.SUCCESS,
            },
            2: {
                "success": True,
                "status": StepStatus.SUCCESS,
            },
        }
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.COMPLETE
    )

def test_completion_requests_replan():

    state = {
        "tool_results": {
            1: {
                "success": False,
                "status": StepStatus.FAILED,
                "failure_reason": FailureReason.TIMEOUT,
            }
        }
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.REPLAN
    )

def test_completion_continue_execution():

    state = {
        "tool_results": {
            1: {
                "success": True,
                "status": StepStatus.SUCCESS,
            }
        },
        "steps": [
            object(),
            object(),
        ],
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.CONTINUE
    )

def test_completion_failed_nonrecoverable():

    state = {
        "tool_results": {
            1: {
                "success": False,
                "status": StepStatus.FAILED,
                "failure_reason": FailureReason.INVALID_TOOL,
            }
        }
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.FAILED
    )