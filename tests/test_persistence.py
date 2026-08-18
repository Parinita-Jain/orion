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
from shared_types.failure_reason import FailureReason

from registry import Tool, register_tool, clear_registry

from runtime.approval_request import ApprovalRequest

from workflow.completion import completion_node

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

def test_restart_reconstructs_runtime_state():

    state = {
        "workflow_id": "restart-runtime-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+3",
                depends_on=[],
            )
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
        "restart-runtime-test",
        state,
    )

    # Simulate a new Python process.
    restored = load_workflow(
        "restart-runtime-test",
    )

    # Runtime objects are reconstructed after restart.
    restored["runtime_config"] = RuntimeConfig()

    assert restored["workflow_id"] == "restart-runtime-test"

    assert restored["iteration"] == 1

    assert len(restored["steps"]) == 1

    assert restored["steps"][0].tool == "calculator"

    assert isinstance(
        restored["runtime_config"],
        RuntimeConfig,
    )

    # The persisted state should not contain a live
    # runtime EventBus.
    assert "event_bus" not in restored

    Path(
        "data/workflows/restart-runtime-test.json"
    ).unlink()

def test_restart_resumes_from_persisted_progress():

    state = {
        "workflow_id": "restart-resume-test",
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
                "value": 5,
            }
        },

        "tool_results": {
            1: {
                "success": True,
                "output": {
                    "value": 5,
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

    # Process 1: save the partial workflow.
    save_workflow(
        "restart-resume-test",
        state,
    )

    # Process 2: load the persisted workflow.
    restored = load_workflow(
        "restart-resume-test",
    )

    # Reconstruct runtime-only state.
    restored["runtime_config"] = RuntimeConfig()

    # Resume execution.
    result = executor_node(restored)

    # Step 1 was already completed before restart.
    assert result["tool_results"][1]["success"] is True

    # Step 2 must execute after restart.
    assert result["tool_results"][2]["success"] is True

    assert (
        result["tool_results"][2]["output"]["value"]
        == 30
    )

    Path(
        "data/workflows/restart-resume-test.json"
    ).unlink()

def test_completed_step_is_not_executed_again_after_restart():

    execution_count = 0

    def counting_tool(input_text):
        nonlocal execution_count

        execution_count += 1

        return {
            "messages": [
                AIMessage(content="Executed")
            ],
            "output": {
                "value": 42
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="counting_tool",
            function=counting_tool,
            description="Test tool that counts executions.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": "idempotency-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="counting_tool",
                tool_input="run",
                depends_on=[],
            )
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    # First execution.
    result = executor_node(state)

    assert result["tool_results"][1]["success"] is True
    assert execution_count == 1

    # Persist the completed workflow.
    save_workflow(
        "idempotency-test",
        state,
    )

    # Simulate restart.
    restored = load_workflow(
        "idempotency-test",
    )

    restored["runtime_config"] = RuntimeConfig()

    # Execute the workflow again.
    result = executor_node(restored)

    # Step 1 was already completed.
    # It must NOT execute again.
    assert execution_count == 1

    assert result["tool_results"][1]["success"] is True

    Path(
        "data/workflows/idempotency-test.json"
    ).unlink()

def test_failed_step_is_retried_after_restart():

    execution_count = 0

    def retryable_tool(input_text):
        nonlocal execution_count

        execution_count += 1

        if execution_count == 1:
            return {
                "messages": [
                    AIMessage(content="First attempt failed")
                ],
                "output": {},
                "success": False,
                "status": StepStatus.FAILED,
                "error": "Temporary failure",
            }

        return {
            "messages": [
                AIMessage(content="Second attempt succeeded")
            ],
            "output": {
                "value": 42,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="retryable_tool",
            function=retryable_tool,
            description="Fails once and succeeds on retry.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": "retry-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="retryable_tool",
                tool_input="run",
                depends_on=[],
            )
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    # First execution.
    first_result = executor_node(state)

    assert execution_count == 1
    assert first_result["tool_results"][1]["success"] is False

    # Persist the failed workflow.
    save_workflow(
        "retry-test",
        state,
    )

    # Simulate restart.
    restored = load_workflow(
        "retry-test",
    )

    restored["runtime_config"] = RuntimeConfig()

    # Execute again.
    second_result = executor_node(restored)

    # The failed step must be retried.
    assert execution_count == 2

    # The retry should succeed.
    assert second_result["tool_results"][1]["success"] is True

    assert (
        second_result["tool_results"][1]["output"]["value"]
        == 42
    )

    Path(
        "data/workflows/retry-test.json"
    ).unlink()

def test_approval_state_survives_restart():

    approval = ApprovalRequest(
        step_id=2,
        tool="calculator",
        reason="This step requires human approval.",
    )

    state = {
        "workflow_id": "approval-restart-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=2,
                tool="calculator",
                tool_input="10+20",
                depends_on=[],
                approval=approval,
            )
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    save_workflow(
        "approval-restart-test",
        state,
    )

    restored = load_workflow(
        "approval-restart-test",
    )

    restored_approval = restored["steps"][0].approval

    assert restored_approval is not None

    assert restored_approval.step_id == 2

    assert restored_approval.tool == "calculator"

    assert (
        restored_approval.reason
        == "This step requires human approval."
    )

    Path(
        "data/workflows/approval-restart-test.json"
    ).unlink()

def test_pending_approval_does_not_execute_after_restart():

    execution_count = 0

    def approval_tool(input_text):
        nonlocal execution_count
        execution_count += 1

        return {
            "messages": [
                AIMessage(content="Executed")
            ],
            "output": {
                "value": 42
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="approval_tool",
            function=approval_tool,
            description="Tool requiring approval.",
            outputs=["value"],
        )
    )

    approval = ApprovalRequest(
        step_id=1,
        tool="approval_tool",
        reason="Human approval required.",
    )

    state = {
        "workflow_id": "approval-resume-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="approval_tool",
                tool_input="run",
                depends_on=[],
                approval=approval,
            )
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    # First execution: approval should be required.
    result = executor_node(state)

    assert execution_count == 0

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.WAITING_FOR_APPROVAL
    )

    # Persist the pending-approval workflow.
    save_workflow(
        "approval-resume-test",
        state,
    )

    # Simulate restart.
    restored = load_workflow(
        "approval-resume-test",
    )

    restored["runtime_config"] = RuntimeConfig()

    # Resume without providing an approval decision.
    result = executor_node(restored)

    # Tool must still NOT execute.
    assert execution_count == 0

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.WAITING_FOR_APPROVAL
    )

    Path(
        "data/workflows/approval-resume-test.json"
    ).unlink()


def test_completed_workflow_does_not_execute_again_after_restart():

    execution_count = 0

    def counting_tool(input_text):
        nonlocal execution_count

        execution_count += 1

        return {
            "messages": [
                AIMessage(content="Executed")
            ],
            "output": {
                "value": 42,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="completed_tool",
            function=counting_tool,
            description="Tool used to test completed workflow restart.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": "completed-restart-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="completed_tool",
                tool_input="run",
                depends_on=[],
            )
        ],

        "context": {},
        "tool_results": {},
        "execution_records": [],
        "completion_status": None,
        "messages": [],
        "runtime_config": RuntimeConfig(),
    }

    # First execution.
    result = executor_node(state)

    completion = completion_node(state)
    
    state.update(completion)

    assert execution_count == 1
    assert result["tool_results"][1]["success"] is True

    

    # The workflow should now be complete.
    save_workflow(
        "completed-restart-test",
        state,
    )

    # Simulate restart.
    restored = load_workflow(
        "completed-restart-test",
    )

    assert (
        restored["completion_status"]
        == CompletionStatus.COMPLETE
    )
        

    restored["runtime_config"] = RuntimeConfig()

    # Restart the already-completed workflow.
    result = executor_node(restored)

    
    # Tool must not execute again.
    assert execution_count == 1

    # Existing successful result must remain.
    assert result["tool_results"][1]["success"] is True

    Path(
        "data/workflows/completed-restart-test.json"
    ).unlink()

def test_restart_executes_only_remaining_dependent_steps():

    execution_counts = {
        "step_1": 0,
        "step_2": 0,
    }

    def first_tool(input_text):
        execution_counts["step_1"] += 1

        return {
            "messages": [
                AIMessage(content="Step 1 executed")
            ],
            "output": {
                "value": 5,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    def second_tool(input_text):
        execution_counts["step_2"] += 1

        return {
            "messages": [
                AIMessage(content="Step 2 executed")
            ],
            "output": {
                "value": 30,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="first_tool",
            function=first_tool,
            description="First dependency step.",
            outputs=["value"],
        )
    )

    register_tool(
        Tool(
            name="second_tool",
            function=second_tool,
            description="Second dependent step.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": "dependency-restart-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="first_tool",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="second_tool",
                tool_input="use step 1",
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

    save_workflow(
        "dependency-restart-test",
        state,
    )

    restored = load_workflow(
        "dependency-restart-test"
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

    # First execution:
    # Step 1 succeeds and is persisted.
    # Step 2 succeeds in memory but its checkpoint is interrupted.
    with patch(
        "executor.node.checkpoint_state",
        side_effect=interrupted_checkpoint,
    ):

        try:
            executor_node(restored)
        except RuntimeError:
            pass

    # Step 1 and Step 2 both executed once.
    assert execution_counts["step_1"] == 1
    assert execution_counts["step_2"] == 1

    # Only Step 1 should have survived the interruption.
    persisted = load_workflow(
        "dependency-restart-test"
    )

    assert 1 in persisted["tool_results"]
    assert (
        persisted["tool_results"][1]["success"]
        is True
    )

    assert 2 not in persisted["tool_results"]

    # Step 1's context must also have survived.
    assert (
        persisted["context"]["step_1"]["value"]
        == 5
    )

    # Simulate restart.
    persisted["runtime_config"] = RuntimeConfig()

    result = executor_node(persisted)

    # Step 1 must NOT execute again.
    assert execution_counts["step_1"] == 1

    # Step 2 must execute now.
    assert execution_counts["step_2"] == 2

    assert (
        result["tool_results"][1]["success"]
        is True
    )

    assert (
        result["tool_results"][2]["success"]
        is True
    )

    Path(
        "data/workflows/dependency-restart-test.json"
    ).unlink()

def test_successful_step_is_not_reexecuted_when_later_step_retries_after_restart():

    execution_counts = {
        "step_1": 0,
        "step_2": 0,
    }

    def first_tool(input_text):
        execution_counts["step_1"] += 1

        return {
            "messages": [
                AIMessage(content="Step 1 executed")
            ],
            "output": {
                "value": 5,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    def second_tool(input_text):
        execution_counts["step_2"] += 1

        if execution_counts["step_2"] == 1:
            return {
                "messages": [
                    AIMessage(content="Temporary failure")
                ],
                "output": {},
                "success": False,
                "status": StepStatus.FAILED,
                "failure_reason": FailureReason.EXCEPTION,
                "error": "Temporary failure",
            }

        return {
            "messages": [
                AIMessage(content="Step 2 succeeded")
            ],
            "output": {
                "value": 30,
            },
            "success": True,
            "status": StepStatus.SUCCESS,
            "error": None,
        }

    clear_registry()

    register_tool(
        Tool(
            name="first_tool",
            function=first_tool,
            description="First successful step.",
            outputs=["value"],
        )
    )

    register_tool(
        Tool(
            name="second_tool",
            function=second_tool,
            description="Retryable second step.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": "failed-dependent-restart-test",
        "iteration": 1,

        "steps": [
            PlanStep(
                id=1,
                tool="first_tool",
                tool_input="2+3",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="second_tool",
                tool_input="use step 1",
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

    result = executor_node(state)

    # Step 1 succeeds once.
    assert execution_counts["step_1"] == 1

    # Step 2 runs once and fails.
    assert execution_counts["step_2"] == 1
    assert (
        result["tool_results"][2]["status"]
        == StepStatus.FAILED
    )

    # Step 1's successful result must remain available.
    assert (
        state["tool_results"][1]["status"]
        == StepStatus.SUCCESS
    )

    save_workflow(
        "failed-dependent-restart-test",
        state,
    )

    restored = load_workflow(
        "failed-dependent-restart-test"
    )

    restored["runtime_config"] = RuntimeConfig()

    # Restart.
    result = executor_node(restored)

    # Successful Step 1 must NOT execute again.
    assert execution_counts["step_1"] == 1

    # Failed Step 2 must retry.
    assert execution_counts["step_2"] == 2

    assert (
        result["tool_results"][2]["success"]
        is True
    )

    Path(
        "data/workflows/failed-dependent-restart-test.json"
    ).unlink()