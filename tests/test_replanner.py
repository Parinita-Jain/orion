from replanner import replanner_node
from shared_types.step_status import StepStatus

def test_replanner_max_iterations():

    state = {
        "iteration": 3,
    }

    result = replanner_node(state)

    assert result["error"] is not None

from unittest.mock import patch

from langchain_core.messages import HumanMessage

from replanner import replanner_node

from schemas import (
    ReplannerOutput,
    PlanStep,
)


@patch("replanner.llm")
def test_replanner_adds_new_steps(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            return ReplannerOutput(
                done=False,
                steps=[
                    PlanStep(
                        id=2,
                        tool="llm",
                        tool_input="Summarize the answer",
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
            )
        ],
        "tool_results": {
            1: {
                "success": True,
                "status": StepStatus.SUCCESS,
                "output": "RAG explanation",
                "error": None,
                "failure_reason": None,
            }
        },
    }

    result = replanner_node(state)

    assert result["done"] is False
    assert result["iteration"] == 1
    assert result["error"] is None
    assert len(result["steps"]) == 2
    assert result["steps"][1].tool == "llm"

# Test 3
@patch("replanner.llm")
def test_replanner_returns_done_when_work_is_complete(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            return ReplannerOutput(
                done=True,
                steps=[],
            )

    mock_llm.with_structured_output.return_value = FakeLLM()

    state = {
        "iteration": 0,
        "messages": [
            HumanMessage(
                content="Explain RAG."
            )
        ],
        "steps": [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="Explain RAG",
                depends_on=[],
            )
        ],
        "tool_results": {
            1: {
                "success": True,
                "status": StepStatus.SUCCESS,
                "output": "RAG explanation",
                "error": None,
                "failure_reason": None,
            }
        },
    }

    result = replanner_node(state)

    assert result["done"] is True
    assert result["iteration"] == 1
    assert result["error"] is None
    assert len(result["steps"]) == 1

#Test 4
from unittest.mock import patch

from langchain_core.messages import HumanMessage


@patch("replanner.llm")
def test_replanner_handles_llm_failure(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            raise Exception("API Error")

    mock_llm.with_structured_output.return_value = FakeLLM()

    state = {
        "iteration": 0,
        "messages": [
            HumanMessage(
                content="Explain RAG."
            )
        ],
        "steps": [],
        "tool_results": {},
    }

    result = replanner_node(state)

    assert result["error"] is not None
    assert result["done"] is True
    assert result["iteration"] == 0