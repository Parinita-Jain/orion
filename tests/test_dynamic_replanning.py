from completion import completion_node
from replanner import replanner_node

from langchain_core.messages import HumanMessage
from unittest.mock import patch

from schemas import (
    PlanStep,
    ReplannerOutput,
)

from shared_types.completion_status import CompletionStatus
from shared_types.failure_reason import FailureReason
from shared_types.step_status import StepStatus

@patch("replanner.llm")
def test_dynamic_replanning_workflow(mock_llm):
    class FakeLLM:

        def invoke(self, prompt):

            return ReplannerOutput(
                done=False,
                steps=[
                    PlanStep(
                        id=3,
                        tool="llm",
                        tool_input="Summarize the final answer",
                        depends_on=[1],
                    )
                ],
            )

    mock_llm.with_structured_output.return_value = FakeLLM()

    state = {
        "iteration": 0,
        "messages": [
            HumanMessage(
                content="Explain RAG and summarize it."
            )
        ],
        "steps": [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="Explain RAG",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="llm",
                tool_input="Summarize #1.answer",
                depends_on=[1],
            ),
        ],
    }

    state["tool_results"] = {
        1: {
            "success": True,
            "status": StepStatus.SUCCESS,
            "output": "RAG explanation",
            "error": None,
            "failure_reason": None,
        }
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.CONTINUE
    )

    # ---------------------------------
    # Simulate Step 2 timeout
    # ---------------------------------

    state["tool_results"][2] = {
        "success": False,
        "status": StepStatus.FAILED,
        "output": None,
        "error": "Request timed out",
        "failure_reason": FailureReason.TIMEOUT,
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.REPLAN
    )

    # ---------------------------------
    # Replanner generates a new step
    # ---------------------------------

    replanner_result = replanner_node(state)

    assert replanner_result["done"] is False

    assert replanner_result["error"] is None

    assert replanner_result["iteration"] == 1

    assert len(replanner_result["steps"]) == 3

    assert replanner_result["steps"][-1].tool == "llm"

    # NOTE:
    # The current replanner appends new steps but does not
    # replace or supersede failed steps.
    #
    # Completion therefore continues to return REPLAN
    # until step replacement support is implemented.
    #
    # This behavior is documented in ADR-007.

    # ---------------------------------
    # Execute replanned step
    # ---------------------------------

    """

    state["steps"] = replanner_result["steps"]

    state["tool_results"][3] = {
        "success": True,
        "status": StepStatus.SUCCESS,
        "output": "Summary",
        "error": None,
        "failure_reason": None,
    }


    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.COMPLETE
    )

    """


        