import tools
import json

import importlib


from registry import clear_registry

from persistence import (save_workflow,load_workflow,)
from models.plan import PlanStep

from pathlib import Path

from shared_types.completion_status import CompletionStatus

from models.execution_record import ExecutionRecord

from langchain_core.messages import HumanMessage, AIMessage

from unittest.mock import patch
from executor.node import executor_node
from runtime.runtime_config import RuntimeConfig
from models.plan import PlanStep

from shared_types.step_status import StepStatus

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
        "execution_records": [
            ExecutionRecord(
                step_id=5,
                tool="llm",
                success=True,
                retries=0,
                start_time=100.0,
                end_time=101.5,
                duration=1.5,
                error=None,
            )
        ],
    }

   

    save_workflow(
        "test-save",
        state,
    )
    restored = load_workflow("test-save")

    assert len(restored["execution_records"]) == 1

    record = restored["execution_records"][0]

    assert record.step_id == 5
    assert record.tool == "llm"
    assert record.success is True
    assert record.retries == 0
    assert record.duration == 1.5
    assert record.error is None

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
                    "value": 5,
                },
            },
        },
        "completion_status": CompletionStatus.COMPLETE,
        "messages": [
                HumanMessage(content="5+6"),
                AIMessage(content="The sum of 5 and 6 is 11."),
            ],
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

    assert restored["messages"][0].type == "human"
    assert restored["messages"][0].content == "5+6"

    assert restored["messages"][1].type == "ai"
    assert restored["messages"][1].content == "The sum of 5 and 6 is 11."

    Path("data/workflows/test-save.json").unlink()

def test_persisted_workflow_resumes_from_partial_progress():

    state = {
        "workflow_id": "resume-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[1],
            ),
        ],

        "context": {
            "step_1": {
                "value": 5
            }
        },
        "tool_results": {
            1: {
                "success": True,
                "output": {
                    "value": 5
                },
                "status": StepStatus.SUCCESS,
                "error": None,
            }
        },

        "execution_records": [],

        "completion_status": None,

        "messages": [],

        "runtime_config": RuntimeConfig(),
    }

    clear_registry()
    importlib.reload(tools)

    save_workflow("resume-test", state)

    restored = load_workflow("resume-test")

    # Runtime-only objects are reconstructed after loading.
    restored["runtime_config"] = RuntimeConfig()

    result = executor_node(restored)


    assert 1 in restored["tool_results"]
    assert 2 in result["tool_results"]

    # Step 1 was already complete.
    # Only Step 2 should have been executed.

    assert result["tool_results"][2]["success"] is True
    assert result["tool_results"][2]["output"]["value"] == 30

    assert len(result["execution_records"]) == 1
    assert result["execution_records"][0].step_id == 2
    assert len(result["execution_records"]) == 1

    assert result["execution_records"][0].step_id == 2

    Path("data/workflows/resume-test.json").unlink()

def test_persisted_workflow_resumes_after_multiple_completed_steps():

    state = {
        "workflow_id": "resume-multi-test",
        "iteration": 2,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[],
            ),
            PlanStep(
                id=3,
                tool="calculator",
                tool_input="100+200",
                depends_on=[1, 2],
            ),
        ],

        "context": {
            "step_1": {
                "value": 5,
            },
            "step_2": {
                "value": 30,
            },
        },

        "tool_results": {
            1: {
                "success": True,
                "output": {
                    "value": 5,
                },
                "status": StepStatus.SUCCESS,
                "error": None,
            },
            2: {
                "success": True,
                "output": {
                    "value": 30,
                },
                "status": StepStatus.SUCCESS,
                "error": None,
            },
        },

        "execution_records": [],

        "completion_status": None,

        "messages": [],

        "runtime_config": RuntimeConfig(),
    }

    clear_registry()
    importlib.reload(tools)

    save_workflow("resume-multi-test", state)

    restored = load_workflow("resume-multi-test")

    restored["runtime_config"] = RuntimeConfig()

    result = executor_node(restored)

    # Previously completed steps must remain intact.
    assert result["tool_results"][1]["success"] is True
    assert result["tool_results"][2]["success"] is True

    # Only the pending step should execute.
    assert result["tool_results"][3]["success"] is True
    assert result["tool_results"][3]["output"]["value"] == 300

    # Only Step 3 should have produced a new execution record.
    assert len(result["execution_records"]) == 1
    assert result["execution_records"][0].step_id == 3

    # Context from all three steps should be available.
    assert result["context"]["step_1"]["value"] == 5
    assert result["context"]["step_2"]["value"] == 30
    assert result["context"]["step_3"]["value"] == 300

    Path("data/workflows/resume-multi-test.json").unlink()

def test_checkpoint_preserves_completed_steps_before_later_failure():

    state = {
        "workflow_id": "checkpoint-failure-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[1],
            ),
            PlanStep(
                id=3,
                tool="does_not_exist",
                tool_input="anything",
                depends_on=[2],
            ),
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    clear_registry()
    importlib.reload(tools)

    save_workflow(
        "checkpoint-failure-test",
        state,
    )

    restored = load_workflow(
        "checkpoint-failure-test"
    )

    restored["runtime_config"] = RuntimeConfig()

    result = executor_node(restored)

    # Steps 1 and 2 should have completed.
    assert result["tool_results"][1]["success"] is True
    assert result["tool_results"][2]["success"] is True

    # Step 3 should have failed because the tool does not exist.
    assert result["tool_results"][3]["success"] is False

    # Now inspect the persisted checkpoint.
    persisted = load_workflow(
        "checkpoint-failure-test"
    )

    assert 1 in persisted["tool_results"]
    assert 2 in persisted["tool_results"]

    Path(
        "data/workflows/checkpoint-failure-test.json"
    ).unlink()

def test_step_checkpoint_survives_interruption():

    state = {
        "workflow_id": "step-interruption-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[1],
            ),
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    clear_registry()
    importlib.reload(tools)

    save_workflow(
        "step-interruption-test",
        state,
    )

    restored = load_workflow(
        "step-interruption-test"
    )

    restored["runtime_config"] = RuntimeConfig()

    real_checkpoint = __import__(
        "executor.node",
        fromlist=["checkpoint_state"],
    ).checkpoint_state

    checkpoint_count = 0

    def interrupted_checkpoint(state):
        nonlocal checkpoint_count

        checkpoint_count += 1

        if checkpoint_count == 1:
            real_checkpoint(state)
            return

        raise RuntimeError(
            "Simulated process interruption"
        )

    with patch(
        "executor.node.checkpoint_state",
        side_effect=interrupted_checkpoint,
    ):

        try:
            executor_node(restored)
        except RuntimeError:
            pass

    persisted = load_workflow(
        "step-interruption-test"
    )

    # Step 1 completed and was checkpointed.
    assert 1 in persisted["tool_results"]
    assert (
        persisted["tool_results"][1]["success"]
        is True
    )

    # Step 2 had not been checkpointed yet.
    assert 2 not in persisted["tool_results"]

    Path(
        "data/workflows/step-interruption-test.json"
    ).unlink()


def test_parallel_steps_are_checkpointed_correctly():

    state = {
        "workflow_id": "parallel-checkpoint-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[],
            ),
            PlanStep(
                id=3,
                tool="calculator",
                tool_input="100+200",
                depends_on=[1, 2],
            ),
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    clear_registry()
    importlib.reload(tools)

    save_workflow(
        "parallel-checkpoint-test",
        state,
    )

    restored = load_workflow(
        "parallel-checkpoint-test"
    )

    restored["runtime_config"] = RuntimeConfig()

    result = executor_node(restored)

    # Both independent steps must complete.
    assert result["tool_results"][1]["success"] is True
    assert result["tool_results"][2]["success"] is True

    # The dependent step must then complete.
    assert result["tool_results"][3]["success"] is True
    assert result["tool_results"][3]["output"]["value"] == 300

    # All three results must be present in the final checkpoint.
    persisted = load_workflow(
        "parallel-checkpoint-test"
    )

    assert 1 in persisted["tool_results"]
    assert 2 in persisted["tool_results"]
    assert 3 in persisted["tool_results"]

    assert persisted["tool_results"][1]["output"]["value"] == 5
    assert persisted["tool_results"][2]["output"]["value"] == 30
    assert persisted["tool_results"][3]["output"]["value"] == 300

    Path(
        "data/workflows/parallel-checkpoint-test.json"
    ).unlink() 