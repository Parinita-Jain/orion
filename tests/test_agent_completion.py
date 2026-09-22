from models.plan import PlanStep

from shared_types.completion_status import CompletionStatus
from shared_types.step_status import StepStatus

from workflow.completion import completion_node


def test_completion_checks_only_current_agent_task():

    state = {
        "current_agent_task_id": "T1",

        "steps": [
            PlanStep(
                id=1,
                tool="research",
                tool_input="research",
                depends_on=[],
                agent_task_id="T2",
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="2+2",
                depends_on=[],
                agent_task_id="T1",
            ),
        ],

        "tool_results": {
            1: {
                "status": StepStatus.SUCCESS,
                "success": True,
                "output": {
                    "research": "done"
                },
                "error": None,
                "failure_reason": None,
            },
        },
    }

    result = completion_node(
        state
    )

    assert (
        result["completion_status"]
        == CompletionStatus.CONTINUE
    )