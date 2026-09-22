from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from agents import (
    AgentDefinition,
    AgentMessage,
    AgentTask,
    AgentTaskStatus,
    clear_registry,
    register_agent,
)

from agent import agent_node

from unittest.mock import patch

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from models.execution_record import ExecutionRecord
from models.plan import PlanStep

from persistence.serializer import (
    serialize_state,
    deserialize_state,
)

from planner.node import planner_node

from registry import (
    Tool,
    clear_registry as clear_tool_registry,
    register_tool,
)

from runtime.event_bus import EventBus
from runtime.runtime_config import RuntimeConfig

from executor.node import executor_node

from shared_types.step_status import StepStatus


def setup_function():
    clear_registry()
    clear_tool_registry()


def teardown_function():
    clear_registry()
    clear_tool_registry()


def test_agent_node_creates_root_supervisor_task():

    state = {
        "messages": [
            HumanMessage(
                content="25*7"
            )
        ],
        "agent_tasks": {},
        "agent_messages": [],
        "current_agent_task_id": None,
    }

    with patch("agents.runtime.AgentRuntime") as mock_runtime:
        mock_runtime.return_value.decide_task.return_value = (
            AgentDecision(
                action=AgentAction.PLAN,
            )
        )

        result = agent_node(state)

    assert result["current_agent_task_id"] == "T1"

    task = result["agent_tasks"]["T1"]

    assert task.parent_task_id is None
    assert task.agent_id == "supervisor"
    assert task.request == "25*7"
    assert task.status == AgentTaskStatus.RUNNING

    assert result["agent_next_node"] == "planner"


def test_agent_node_reuses_existing_root_task():

    existing_task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="25*7",
        status=AgentTaskStatus.ASSIGNED,
    )

    state = {
        "messages": [
            HumanMessage(
                content="25*7"
            )
        ],
        "agent_tasks": {
            "T1": existing_task,
        },
        "agent_messages": [],
        "current_agent_task_id": "T1",
    }

    result = agent_node(state)

    assert result["current_agent_task_id"] == "T1"
    assert list(result["agent_tasks"].keys()) == ["T1"]
    assert result["agent_tasks"]["T1"].status == (
        AgentTaskStatus.RUNNING
    )


def test_planner_node_uses_current_agent_task():

    task = AgentTask(
        task_id="T2",
        parent_task_id="T1",
        agent_id="research",
        request="Research RAG.",
        status=AgentTaskStatus.RUNNING,
    )

    state = {
        "messages": [
            HumanMessage(
                content="Original user request."
            )
        ],
        "agent_tasks": {
            "T1": AgentTask(
                task_id="T1",
                parent_task_id=None,
                agent_id="supervisor",
                request="Original user request.",
            ),
            "T2": task,
        },
        "current_agent_task_id": "T2",
    }

    planned_step = PlanStep(
        id=1,
        tool="rag",
        tool_input="Research RAG.",
        agent_task_id="T2",
    )

    class FakeAgentRuntime:

        def plan_task(self, received_task, existing_steps=None):
            assert received_task is task
            return [planned_step]

    with patch(
        "agents.runtime.AgentRuntime",
        return_value=FakeAgentRuntime(),
    ):

        result = planner_node(state)

    assert result["error"] is None
    assert len(result["steps"]) == 1
    assert result["steps"][0].agent_task_id == "T2"


def test_executor_records_agent_task_id():

    workflow_id = "agent-executor-association-test"

    def fake_tool(state):

        return {
            "messages": [],
            "output": {
                "value": 42
            },
            "success": True,
            "error": None,
        }

    register_tool(
        Tool(
            name="agent_test_tool",
            function=fake_tool,
            description="Agent integration test tool.",
            outputs=["value"],
        )
    )

    state = {
        "workflow_id": workflow_id,
        "steps": [
            PlanStep(
                id=1,
                tool="agent_test_tool",
                tool_input="run",
                depends_on=[],
                agent_task_id="T2",
            )
        ],
        "tool_results": {},
        "execution_records": [],
        "context": {},
        "runtime_config": RuntimeConfig(),
        "event_bus": EventBus(),
    }

    try:

        with patch(
            "executor.node.save_workflow"
        ):

            result = executor_node(state)

        records = result["execution_records"]

        assert len(records) == 1
        assert records[0].step_id == 1
        assert records[0].agent_task_id == "T2"

    finally:

        path = Path(
            f"data/workflows/{workflow_id}.json"
        )

        if path.exists():
            path.unlink()


def test_agent_state_persistence_round_trip():

    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Research RAG.",
        status=AgentTaskStatus.RUNNING,
        metadata={
            "priority": "normal"
        },
    )

    message = AgentMessage(
        message_id="M1",
        sender="supervisor",
        recipient="research",
        content="Research RAG.",
        task_id="T2",
        correlation_id="C1",
    )

    state = {
        "workflow_id": "agent-persistence-test",
        "iteration": 1,
        "done": False,
        "error": None,
        "steps": [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="Research RAG.",
                agent_task_id="T1",
            )
        ],
        "tool_results": {},
        "execution_records": [],
        "messages": [
            HumanMessage(
                content="Research RAG."
            )
        ],
        "context": {},
        "output": {},
        "agent_tasks": {
            "T1": task,
        },
        "agent_messages": [
            message,
        ],
        "current_agent_task_id": "T1",
    }

    serialized = serialize_state(state)

    restored = deserialize_state(
        serialized
    )

    assert restored["current_agent_task_id"] == "T1"

    restored_task = restored["agent_tasks"]["T1"]

    assert restored_task.agent_id == "supervisor"
    assert restored_task.request == "Research RAG."
    assert restored_task.status == AgentTaskStatus.RUNNING
    assert restored_task.metadata == {
        "priority": "normal"
    }

    restored_message = restored["agent_messages"][0]

    assert restored_message.message_id == "M1"
    assert restored_message.sender == "supervisor"
    assert restored_message.recipient == "research"
    assert restored_message.task_id == "T2"
    assert restored_message.correlation_id == "C1"

    assert (
        restored["steps"][0].agent_task_id
        == "T1"
    )