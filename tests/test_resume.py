from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from persistence import load_workflow, save_workflow
from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig
from schemas import PlanStep, ReplannerOutput
from registry import Tool, clear_registry, register_tool
from shared_types.completion_status import CompletionStatus
from shared_types.failure_reason import FailureReason
from shared_types.step_status import StepStatus


def test_resume_workflow_continues_persisted_workflow():
    workflow_id = "resume-integration-test"

    attempts = {
        1: 0,
        2: 0,
    }

    def fake_calculator(state):
        step_id = int(state["tool_input"])

        attempts[step_id] += 1

        return {
            "messages": [],
            "output": {
                "value": 5 if step_id == 1 else 30,
            },
            "success": True,
            "error": None,
        }
    clear_registry()

    register_tool(
        Tool(
            name="calculator",
            function=fake_calculator,
            description="Test calculator",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": workflow_id,
        "iteration": 0,
        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="1",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="2",
                depends_on=[1],
            ),
        ],
        "tool_results": {
            1: {
                "messages": [],
                "output": {"value": 5},
                "success": True,
                "status": StepStatus.SUCCESS,
                "error": None,
                "failure_reason": None,
            }
        },
        "execution_records": [],
        "messages": [
            HumanMessage(content="Continue this workflow.")
        ],
        "context": {
            "step_1": {"value": 5},
        },
        "output": {},
        "done": False,
        "error": None,
        "errors": [],
        "completion_status": None,
        "runtime_config": RuntimeConfig(),
    }
    try:
        save_workflow(workflow_id, state)
        from workflow.resume import resume_workflow

        result = resume_workflow(workflow_id)

        assert attempts[1] == 0
        assert attempts[2] == 1

        assert result["tool_results"][1]["success"] is True
        assert result["tool_results"][2]["success"] is True
    finally:
        Path(
            f"data/workflows/{workflow_id}.json"
        ).unlink()


def test_resume_completed_workflow_does_not_execute_again():
    workflow_id = "completed-resume-api-test"
    execution_count = 0

    def counting_tool(input_text):
        nonlocal execution_count

        execution_count += 1

        return {
            "messages": [],
            "output": {"value": 42},
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="completed_tool",
            function=counting_tool,
            description="Test tool for completed workflow resume.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": workflow_id,
        "iteration": 1,
        "steps": [
            PlanStep(
                id=1,
                tool="completed_tool",
                tool_input="run",
                depends_on=[],
            )
        ],
        "tool_results": {
            1: {
                "messages": [],
                "output": {"value": 42},
                "success": True,
                "status": StepStatus.SUCCESS,
                "error": None,
                "failure_reason": None,
            }
        },
        "execution_records": [],
        "messages": [],
        "context": {},
        "output": {},
        "done": False,
        "error": None,
        "errors": [],
        "completion_status": CompletionStatus.COMPLETE,
        "runtime_config": RuntimeConfig(),
    }

    try:
        save_workflow(workflow_id, state)

        from workflow.resume import resume_workflow

        result = resume_workflow(workflow_id)

        # The completed workflow must not execute its tool again.
        assert execution_count == 0

        # The completed status must be preserved.
        assert (
            result["completion_status"]
            == CompletionStatus.COMPLETE
        )

        # The existing successful result must remain intact.
        assert result["tool_results"][1]["success"] is True
        assert result["tool_results"][1]["output"]["value"] == 42

    finally:
        Path(
            f"data/workflows/{workflow_id}.json"
        ).unlink()


def test_resume_replan_workflow_enters_replanner():
    workflow_id = "replan-resume-api-test"
    original_execution_count = 0
    replacement_execution_count = 0

    def original_tool(input_text):
        nonlocal original_execution_count

        original_execution_count += 1

        return {
            "messages": [],
            "output": {"value": 10},
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    def replacement_tool(input_text):
        nonlocal replacement_execution_count

        replacement_execution_count += 1

        return {
            "messages": [],
            "output": {"value": 99},
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="temporary_tool",
            function=original_tool,
            description="Original tool that must not be re-executed.",
            outputs=["value"],
        )
    )

    register_tool(
        Tool(
            name="replacement_tool",
            function=replacement_tool,
            description="Test replacement tool.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": workflow_id,
        "iteration": 0,
        "steps": [
            PlanStep(
                id=1,
                tool="temporary_tool",
                tool_input="run",
                depends_on=[],
            )
        ],
        "tool_results": {
            1: {
                "messages": [],
                "output": {},
                "success": False,
                "status": StepStatus.FAILED,
                "error": "Request timed out",
                "failure_reason": FailureReason.TIMEOUT,
            }
        },
        "execution_records": [],
        "messages": [HumanMessage(content="Complete the task.")],
        "context": {},
        "output": {},
        "done": False,
        "error": None,
        "errors": [],
        "completion_status": CompletionStatus.REPLAN,
        "runtime_config": RuntimeConfig(),
    }

    replanner_output = ReplannerOutput(
        done=False,
        steps=[
            PlanStep(
                id=2,
                tool="replacement_tool",
                tool_input="run replacement",
                depends_on=[],
                replaces=1,
            )
        ],
    )

    try:
        save_workflow(workflow_id, state)

        with patch("replanner.llm") as mock_llm:
            mock_llm.with_structured_output.return_value.invoke.return_value = (
                replanner_output
            )

            from workflow.resume import resume_workflow

            result = resume_workflow(workflow_id)

        # The failed original step must not execute again.
        assert original_execution_count == 0
        assert replacement_execution_count == 1

        # The replanner must have created the replacement step.
        assert len(result["steps"]) == 2
        assert result["steps"][1].id == 2
        assert result["steps"][1].replaces == 1

        # The replacement step must succeed.
        assert result["tool_results"][2]["success"] is True
        assert result["tool_results"][2]["output"]["value"] == 99

    finally:
        Path(
            f"data/workflows/{workflow_id}.json"
        ).unlink()
