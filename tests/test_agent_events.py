from langchain_core.messages import HumanMessage

from agents.controller import (
    ensure_active_task,
    process_agent_decision,
    start_agent_task,
)

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from agents.models import AgentDefinition

from agents.registry import (
    clear_registry,
    register_agent,
)

from agents.task import (
    AgentTask,
    AgentTaskStatus,
)

from agents.controller import (
    complete_agent_task,
    fail_agent_task,
)

from runtime.event import WorkflowEvent
from runtime.event_bus import EventBus

from shared_types.workflow_event_type import WorkflowEventType


class FakeListener:
    def __init__(self):
        self.events = []

    def __call__(self, event):
        self.events.append(event)


def setup_function():
    clear_registry()

    register_agent(
        AgentDefinition(
            id="supervisor",
            name="Supervisor Agent",
            role="supervisor",
            instructions="Coordinate work.",
        )
    )

    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Perform research.",
        )
    )


def teardown_function():
    clear_registry()


def test_root_task_creation_and_start_emit_events():

    listener = FakeListener()
    bus = EventBus()
    bus.subscribe(listener)

    tasks = {}
    messages = []

    task = ensure_active_task(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id=None,
        messages=[
            HumanMessage(
                content="Research something."
            )
        ],
        event_bus=bus,
    )

    start_agent_task(
        tasks,
        task.task_id,
        event_bus=bus,
    )

    assert [
        event.type
        for event in listener.events
    ] == [
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
    ]

    created = listener.events[0]

    assert created.agent_task_id == "T1"
    assert created.agent_id == "supervisor"
    assert created.payload["parent_task_id"] is None
    assert created.payload["request"] == "Research something."

    started = listener.events[1]

    assert started.agent_task_id == "T1"
    assert started.agent_id == "supervisor"
    assert started.payload["status"] == "running"


def test_delegation_emits_created_started_and_message_events():

    listener = FakeListener()
    bus = EventBus()
    bus.subscribe(listener)

    tasks = {
        "T1": AgentTask(
            task_id="T1",
            parent_task_id=None,
            agent_id="supervisor",
            request="Coordinate work.",
            status=AgentTaskStatus.RUNNING,
        )
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T1",
        state={
            "current_agent_task_id": "T1",
            "steps": [],
            "tool_results": {},
        },
        decision=AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="research",
            request="Research the subject.",
        ),
        event_bus=bus,
    )

    assert result["current_agent_task_id"] == "T2"

    assert [
        event.type
        for event in listener.events
    ] == [
        WorkflowEventType.AGENT_TASK_CREATED,
        WorkflowEventType.AGENT_TASK_STARTED,
        WorkflowEventType.AGENT_MESSAGE,
    ]

    created = listener.events[0]

    assert created.agent_task_id == "T2"
    assert created.agent_id == "research"
    assert created.payload["parent_task_id"] == "T1"

    message = listener.events[2]

    assert message.agent_task_id == "T2"
    assert message.agent_id == "supervisor"
    assert message.payload["sender"] == "supervisor"
    assert message.payload["recipient"] == "research"
    assert message.payload["content"] == "Research the subject."


def test_child_completion_emits_completion_and_result_message():

    listener = FakeListener()
    bus = EventBus()
    bus.subscribe(listener)

    tasks = {
        "T1": AgentTask(
            task_id="T1",
            parent_task_id=None,
            agent_id="supervisor",
            request="Coordinate work.",
            status=AgentTaskStatus.RUNNING,
        ),
        "T2": AgentTask(
            task_id="T2",
            parent_task_id="T1",
            agent_id="research",
            request="Research the subject.",
            status=AgentTaskStatus.RUNNING,
        ),
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T2",
        state={
            "current_agent_task_id": "T2",
            "steps": [],
            "tool_results": {},
        },
        decision=AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Research complete."
            },
        ),
        event_bus=bus,
    )

    assert result["current_agent_task_id"] == "T1"

    assert [
        event.type
        for event in listener.events
    ] == [
        WorkflowEventType.AGENT_TASK_COMPLETED,
        WorkflowEventType.AGENT_MESSAGE,
    ]

    completed = listener.events[0]

    assert completed.agent_task_id == "T2"
    assert completed.agent_id == "research"
    assert completed.payload["result"] == {
        "answer": "Research complete."
    }

    message = listener.events[1]

    assert message.agent_task_id == "T2"
    assert message.agent_id == "research"
    assert message.payload["recipient"] == "supervisor"
    assert message.payload["content"] == {
        "answer": "Research complete."
    }


def test_task_failure_emits_failure_event():

    listener = FakeListener()
    bus = EventBus()
    bus.subscribe(listener)

    tasks = {
        "T1": AgentTask(
            task_id="T1",
            parent_task_id=None,
            agent_id="supervisor",
            request="Coordinate work.",
            status=AgentTaskStatus.RUNNING,
        )
    }

    fail_agent_task(
        agent_tasks=tasks,
        task_id="T1",
        error="Agent execution failed.",
        result={
            "reason": "test"
        },
        event_bus=bus,
    )

    assert tasks["T1"].status == AgentTaskStatus.FAILED

    assert [
        event.type
        for event in listener.events
    ] == [
        WorkflowEventType.AGENT_TASK_FAILED,
    ]

    event = listener.events[0]

    assert event.agent_task_id == "T1"
    assert event.agent_id == "supervisor"
    assert event.payload["error"] == "Agent execution failed."
    assert event.payload["result"] == {
        "reason": "test"
    }


def test_existing_workflow_event_is_backward_compatible():

    event = WorkflowEvent(
        WorkflowEventType.WORKFLOW_STARTED,
        123.0,
        7,
        "calculator",
        {"value": 4},
    )

    assert event.type == WorkflowEventType.WORKFLOW_STARTED
    assert event.timestamp == 123.0
    assert event.step_id == 7
    assert event.tool == "calculator"
    assert event.payload == {
        "value": 4
    }
    assert event.agent_task_id is None
    assert event.agent_id is None


def test_existing_event_types_remain_available():

    assert WorkflowEventType.WORKFLOW_STARTED.value == "workflow_started"
    assert WorkflowEventType.WORKFLOW_COMPLETED.value == "workflow_completed"
    assert WorkflowEventType.STEP_STARTED.value == "step_started"
    assert WorkflowEventType.STEP_COMPLETED.value == "step_completed"
    assert WorkflowEventType.STEP_FAILED.value == "step_failed"
    assert WorkflowEventType.STEP_SKIPPED.value == "step_skipped"