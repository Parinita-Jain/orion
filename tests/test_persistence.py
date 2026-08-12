from persistence import (save_workflow,load_workflow,)
from models.plan import PlanStep
import json
from pathlib import Path


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
    }

    save_workflow(
        "test-save",
        state,
    )

    path = Path("data/workflows/test-save.json")

    assert path.exists()

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["workflow_id"] == "test-save"
    assert data["iteration"] == 1

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
    }
    save_workflow("test-save", state)

    restored = load_workflow("test-save")

    print("STATE:")
    print(state)

    print("\nRESTORED:")
    print(restored)

    print("\nSTATE STEP TYPE:")
    print(type(state["steps"][0]))

    print("\nRESTORED STEP TYPE:")
    print(type(restored["steps"][0]))

    print("\nSTATE STEP:")
    print(state["steps"][0])

    print("\nRESTORED STEP:")
    print(restored["steps"][0])

    assert len(restored["steps"]) == 1

    assert restored["steps"][0].tool == "llm"

    assert restored == state

    Path("data/workflows/test-save.json").unlink()