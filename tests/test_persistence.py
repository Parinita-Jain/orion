from persistence import (save_workflow,load_workflow,)
import json
from pathlib import Path


def test_save_workflow_creates_json():

    state = {
        "workflow_id": "test-workflow",
        "iteration": 1,
    }

    save_workflow(
        "test-workflow",
        state,
    )

    path = Path("data/workflows/test-workflow.json")

    assert path.exists()

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["workflow_id"] == "test-workflow"
    assert data["iteration"] == 1

    path.unlink()

def test_load_workflow_restores_state():

    state = {
        "workflow_id": "test-workflow",
        "iteration": 3,
    }

    save_workflow("test-workflow", state)

    restored = load_workflow("test-workflow")

    assert restored == state

    Path("data/workflows/test-workflow.json").unlink()