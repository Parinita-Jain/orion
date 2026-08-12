from persistence import (save_workflow,load_workflow,)
from models.plan import PlanStep
import json
from pathlib import Path

from shared_types.completion_status import CompletionStatus

def test_save_workflow_creates_json():

    state = {
        "workflow_id": "test-save",
        "iteration": 1,
        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            )
        ],
        "tool_results": {
            1: {
                "success": True,
                "output": {
                    "value": 42,
                },
            },
        },
        "completion_status": CompletionStatus.COMPLETE,
    }

   

    save_workflow(
        "test-save",
        state,
    )
    restored = load_workflow("test-save")

    path = Path("data/workflows/test-save.json")

    assert path.exists()

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["workflow_id"] == "test-save"
    assert data["iteration"] == 1

    assert (
        restored["completion_status"]
        == CompletionStatus.COMPLETE
    )

    path.unlink()

def test_load_workflow_restores_state():

    state = {
        "workflow_id": "test-save",
        "iteration": 3,
        "steps": [
            PlanStep(
                id=5,
                tool="llm",
                tool_input="summarize",
                depends_on=[],
            )
        ],
        "tool_results": {
            1: {
                "success": True,
                "output": {
                    "value": 42,
                },
            },
        },
        "completion_status": CompletionStatus.COMPLETE,
    }
    save_workflow("test-save", state)

    restored = load_workflow("test-save") 

    

    assert restored["workflow_id"] == state["workflow_id"]

    assert restored["iteration"] == state["iteration"]

    assert restored["steps"] == state["steps"]

    assert restored["tool_results"][1]["success"] is True

    assert (
        restored["completion_status"]
        == CompletionStatus.COMPLETE
    )

    Path("data/workflows/test-save.json").unlink()