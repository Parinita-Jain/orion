from unittest.mock import patch

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)

from registry import register_tool
from registry import Tool

from executor import executor_node
from replanner import replanner_node
from completion import completion_node

from runtime.runtime_config import RuntimeConfig
from runtime.event_bus import EventBus

from schemas import (
    PlanStep,
    ReplannerOutput,
)

from shared_types.step_status import StepStatus
from shared_types.failure_reason import FailureReason
from shared_types.completion_status import CompletionStatus


def dummy_tool(state):

    return {
        "messages": [
            AIMessage(content="Done")
        ],
        "output": {
            "answer": "Orion Test Response",
        },
        "success": True,
        "error": None,
    }


def make_state(**overrides):

    state = {
        "steps": [],
        "messages": [],
        "context": {},
        "tool_results": {},
        "execution_records": [],
        "runtime_config": RuntimeConfig(),
        "event_bus": EventBus(),
    }

    state.update(overrides)

    return state


@patch("replanner.llm")
def test_step_supersession(mock_llm):

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    class FakeLLM:

        def invoke(self, prompt):

            return ReplannerOutput(
                done=False,
                steps=[
                    PlanStep(
                        id=3,
                        tool="dummy",
                        tool_input="Retry",
                        depends_on=[],
                        replaces=2,
                    )
                ],
            )

    mock_llm.with_structured_output.return_value = FakeLLM()

    state = make_state(
        iteration=0,
        messages=[
            HumanMessage(
                content="Explain RAG and summarize it."
            )
        ],
        steps=[
            PlanStep(
                id=1,
                tool="dummy",
                tool_input="Explain RAG",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="dummy",
                tool_input="Summarize",
                depends_on=[1],
            ),
        ],
    )

    # -------------------------
    # Step 1 succeeded
    # -------------------------

    state["tool_results"][1] = {
        "messages": [],
        "output": {
            "answer": "RAG explanation"
        },
        "success": True,
        "status": StepStatus.SUCCESS,
        "error": None,
        "failure_reason": None,
    }

    # -------------------------
    # Step 2 failed
    # -------------------------

    state["tool_results"][2] = {
        "messages": [],
        "output": {},
        "success": False,
        "status": StepStatus.FAILED,
        "error": "Timeout",
        "failure_reason": FailureReason.TIMEOUT,
    }

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.REPLAN
    )

    replanner_result = replanner_node(state)

    assert replanner_result["error"] is None

    state["steps"] = replanner_result["steps"]

    # Execute replacement step

    state["steps"] = [
        replanner_result["steps"][-1]
    ]

    executor_result = executor_node(state)

    assert (
        executor_result["tool_results"][2]["status"]
        == StepStatus.SUPERSEDED
    )

    assert (
        executor_result["tool_results"][3]["status"]
        == StepStatus.SUCCESS
    )

    state["tool_results"] = executor_result["tool_results"]

    state["steps"] = replanner_result["steps"]

    result = completion_node(state)

    assert (
        result["completion_status"]
        == CompletionStatus.COMPLETE
    )