import pytest

import importlib

import tools

from langchain_core.messages import HumanMessage

from planner import planner_node, MAX_REPAIR_ATTEMPTS

from unittest.mock import patch

from schemas import PlannerOutput, PlanStep, ApprovalConfig

from registry import clear_registry
from runtime.approval_request import ApprovalRequest

@pytest.fixture(autouse=True)
def setup_tools():

    clear_registry()

    importlib.reload(tools)

    yield

    clear_registry()

def test_greeting_rule():

    state = {
        "messages": [
            HumanMessage(content="Hello")
        ]
    }

    result = planner_node(state)

    assert len(result["steps"]) == 1
    assert result["steps"][0].tool == "direct"
    assert result["steps"][0].id == 1
    assert result["error"] is None


def test_calculator_rule():

    state = {
        "messages": [
            HumanMessage(content="25*7")
        ]
    }

    result = planner_node(state)

    assert len(result["steps"]) == 1
    assert result["steps"][0].tool == "calculator"
    assert result["steps"][0].tool_input == "25*7"
    assert result["error"] is None


def test_calculator_rule_with_spaces():

    state = {
        "messages": [
            HumanMessage(content="20 + 30")
        ]
    }

    result = planner_node(state)

    assert result["steps"][0].tool == "calculator"


def test_non_greeting_goes_to_llm():

    class FakeStructuredLLM:

        def invoke(self, prompt):
            raise RuntimeError("LLM called")

    with patch(
        "planner.node.get_structured_llm",
        return_value=FakeStructuredLLM(),
    ):

        state = {
            "messages": [
                HumanMessage(content="Explain RAG")
            ]
        }

        result = planner_node(state)

    assert result["steps"] == []
    assert result["error"] is not None
    assert result["error"].source == "planner"
    assert result["error"].recoverable is True
    assert result["error"].message == "LLM called"


def test_valid_llm_plan():

    planner_output = PlannerOutput(
        steps=[
            PlanStep(
                id=1,
                tool="llm",
                tool_input="Explain AI",
                depends_on=[]
            )
        ]
    )

    class FakeStructuredLLM:

        def invoke(self, prompt):
            return planner_output

    with patch(
        "planner.node.get_structured_llm",
        return_value=FakeStructuredLLM(),
    ):

        state = {
            "messages": [
                HumanMessage(content="Explain AI")
            ]
        }

        result = planner_node(state)

    assert len(result["steps"]) == 1
    assert result["steps"][0].tool == "llm"
    assert result["steps"][0].tool_input == "Explain AI"
    assert result["error"] is None

def test_planner_repairs_invalid_plan():

    invalid_plan = PlannerOutput(
        steps=[
            PlanStep(
                id=1,
                tool="unknown_tool",
                tool_input="Explain AI",
                depends_on=[]
            )
        ]
    )

    repaired_plan = PlannerOutput(
        steps=[
            PlanStep(
                id=1,
                tool="llm",
                tool_input="Explain AI",
                depends_on=[]
            )
        ]
    )

    class FakeStructuredLLM:

        def invoke(self, prompt):
            return invalid_plan

    with (
        patch(
            "planner.node.get_structured_llm",
            return_value=FakeStructuredLLM(),
        ),
        patch(
            "planner.node.repair_plan",
            return_value=repaired_plan,
        ) as mock_repair,
    ):

        state = {
            "messages": [
                HumanMessage(content="Explain AI")
            ]
        }

        result = planner_node(state)

    mock_repair.assert_called_once()

    assert len(result["steps"]) == 1
    assert result["steps"][0].tool == "llm"
    assert result["error"] is None

    args = mock_repair.call_args.args
    
    assert args[0] == "Explain AI"    
    assert args[1][0].tool == "unknown_tool"    
    assert "Unknown tool" in args[2][0]

def test_planner_repair_failure():

    invalid_plan = PlannerOutput(
        steps=[
            PlanStep(
                id=1,
                tool="unknown_tool",
                tool_input="Explain AI",
                depends_on=[]
            )
        ]
    )

    class FakeStructuredLLM:

        def invoke(self, prompt):
            return invalid_plan

    with (
        patch(
            "planner.node.get_structured_llm",
            return_value=FakeStructuredLLM(),
        ),
        patch(
            "planner.node.repair_plan",
            return_value=invalid_plan,
        ) as mock_repair,
    ):

        state = {
            "messages": [
                HumanMessage(content="Explain AI")
            ]
        }

        with pytest.raises(ValueError) as exc:
            planner_node(state)

    assert mock_repair.call_count == MAX_REPAIR_ATTEMPTS

    assert "Planner could not repair the plan" in str(exc.value)

def test_valid_multistep_llm_plan():

    planner_output = PlannerOutput(
        steps=[
            PlanStep(
                id=1,
                tool="rag",
                tool_input="Explain RAG",
                depends_on=[]
            ),
            PlanStep(
                id=2,
                tool="llm",
                tool_input="Summarize #1.answer",
                depends_on=[1]
            ),
        ]
    )

    class FakeStructuredLLM:

        def invoke(self, prompt):
            return planner_output

    with patch(
        "planner.node.get_structured_llm",
        return_value=FakeStructuredLLM(),
    ):

        state = {
            "messages": [
                HumanMessage(
                    content="Explain RAG and summarize it."
                )
            ]
        }

        result = planner_node(state)

    assert len(result["steps"]) == 2

    assert result["steps"][0].tool == "rag"
    assert result["steps"][1].tool == "llm"

    assert result["steps"][0].depends_on == []
    assert result["steps"][1].depends_on == [1]

    assert result["steps"][1].tool_input == "Summarize #1.answer"

    assert result["error"] is None

@patch("planner.node.get_structured_llm")
def test_planner_creates_approval_request(mock_llm):

    class FakeLLMApproval:

        def invoke(self, prompt):

            return PlannerOutput(
                steps=[
                    PlanStep(
                        id=1,
                        tool="llm",
                        tool_input="Hello",
                        depends_on=[],
                        approval=ApprovalConfig(
                            required=True,
                            reason="Planner requested approval.",
                        ),
                    )
                ]
            )

    mock_llm.return_value = FakeLLMApproval()

    state = {
        "messages": [
            HumanMessage(content="What is RAG?")
        ]
    }

    result = planner_node(state)

    step = result["steps"][0]
    
    assert step.approval is not None

    assert (
        step.approval.step_id == 1
    )

    assert (
        step.approval.tool == "llm"
    )

    assert (
        step.approval.reason
        == "Planner requested approval."
    )

@patch("planner.node.get_structured_llm")
def test_planner_without_approval(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            return PlannerOutput(
                steps=[
                    PlanStep(
                        id=1,
                        tool="llm",
                        tool_input="Hello",
                        depends_on=[],
                        approval=None,
                    )
                ]
            )

    mock_llm.return_value = FakeLLM()

    state = {
        "messages": [
            HumanMessage(content="Explain RAG")
        ]
    }

    result = planner_node(state)

    step = result["steps"][0]

    assert step.approval is None

@patch("planner.node.get_structured_llm")
def test_planner_supports_branching(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            return PlannerOutput(
                steps=[
                    PlanStep(
                        id=1,
                        tool="llm",
                        tool_input="Check eligibility",
                        depends_on=[],
                    ),
                    PlanStep(
                        id=2,
                        tool="llm",
                        tool_input="Approve loan",
                        depends_on=[1],
                        condition="#1.answer == 'yes'",
                    ),
                    PlanStep(
                        id=3,
                        tool="llm",
                        tool_input="Reject loan",
                        depends_on=[1],
                        condition="#1.answer != 'yes'",
                    ),
                ]
            )

    mock_llm.return_value = FakeLLM()

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "If eligible approve the loan "
                    "otherwise reject it."
                )
            )
        ]
    }

    result = planner_node(state)

    assert (
        result["steps"][1].condition
        == "#1.answer == 'yes'"
    )

    assert (
        result["steps"][2].condition
        == "#1.answer != 'yes'"
    )

@patch("planner.node.get_structured_llm")
def test_planner_generates_mutually_exclusive_branches(mock_llm):

    class FakeLLM:

        def invoke(self, prompt):

            return PlannerOutput(
                steps=[
                    PlanStep(
                        id=1,
                        tool="llm",
                        tool_input="Check loan eligibility",
                        depends_on=[],
                    ),
                    PlanStep(
                        id=2,
                        tool="llm",
                        tool_input="Approve loan",
                        depends_on=[1],
                        condition="#1.answer == 'eligible'",
                    ),
                    PlanStep(
                        id=3,
                        tool="llm",
                        tool_input="Reject loan",
                        depends_on=[1],
                        condition="#1.answer != 'eligible'",
                    ),
                ]
            )

    mock_llm.return_value = FakeLLM()

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "If the customer is eligible, "
                    "approve the loan, otherwise reject it."
                )
            )
        ]
    }

    result = planner_node(state)

    assert len(result["steps"]) == 3

    assert result["steps"][1].depends_on == [1]
    assert result["steps"][2].depends_on == [1]

    assert (
        result["steps"][1].condition
        == "#1.answer == 'eligible'"
    )

    assert (
        result["steps"][2].condition
        == "#1.answer != 'eligible'"
    )