from pathlib import Path

from langchain_core.messages import HumanMessage

from persistence import save_workflow
from runtime.runtime_config import RuntimeConfig
from schemas import PlanStep
from shared_types.step_status import StepStatus
from registry import Tool, clear_registry, register_tool


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