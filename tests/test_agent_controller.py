import pytest

from agents.controller import (
    build_decision_context,
    process_agent_decision,
)

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from agents.message import AgentMessage

from agents.models import AgentDefinition

from agents.registry import (
    clear_registry,
    register_agent,
)

from agents.task import (
    AgentTask,
    AgentTaskStatus,
)


@pytest.fixture(autouse=True)
def clean_registry():

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

    register_agent(
        AgentDefinition(
            id="calculation",
            name="Calculation Agent",
            role="calculation",
            instructions="Perform calculations.",
        )
    )

    yield

    clear_registry()


def make_root():
    return AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Complete the request.",
        status=AgentTaskStatus.RUNNING,
    )


def make_state(task_id="T1", steps=None, tool_results=None):

    return {
        "current_agent_task_id": task_id,
        "steps": steps or [],
        "tool_results": tool_results or {},
    }


def test_plan_decision_routes_to_planner():

    tasks = {
        "T1": make_root(),
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T1",
        state=make_state(),
        decision=AgentDecision(
            action=AgentAction.PLAN
        ),
    )

    assert result["agent_next_node"] == "planner"
    assert result["current_agent_task_id"] == "T1"


def test_delegate_creates_child_and_switches_current_task():

    tasks = {
        "T1": make_root(),
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T1",
        state=make_state(),
        decision=AgentDecision(
            action=AgentAction.DELEGATE,
            target_agent_id="research",
            request="Research the assigned subject.",
        ),
    )

    assert "T2" in tasks

    child = tasks["T2"]

    assert child.parent_task_id == "T1"
    assert child.agent_id == "research"
    assert child.status == AgentTaskStatus.RUNNING

    assert result["current_agent_task_id"] == "T2"
    assert result["agent_next_node"] == "agent"

    assert len(messages) == 1
    assert isinstance(
        messages[0],
        AgentMessage,
    )
    assert messages[0].sender == "supervisor"
    assert messages[0].recipient == "research"
    assert messages[0].task_id == "T2"


def test_child_complete_returns_to_parent():

    root = make_root()

    child = AgentTask(
        task_id="T2",
        parent_task_id="T1",
        agent_id="research",
        request="Research the subject.",
        status=AgentTaskStatus.RUNNING,
    )

    tasks = {
        "T1": root,
        "T2": child,
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T2",
        state=make_state(
            task_id="T2"
        ),
        decision=AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Research complete."
            },
        ),
    )

    assert (
        tasks["T2"].status
        == AgentTaskStatus.COMPLETED
    )

    assert (
        result["current_agent_task_id"]
        == "T1"
    )

    assert result["agent_next_node"] == "agent"

    assert len(messages) == 1

    assert (
        messages[0].sender
        == "research"
    )

    assert (
        messages[0].recipient
        == "supervisor"
    )


def test_root_complete_routes_to_synthesizer():

    tasks = {
        "T1": make_root(),
    }

    messages = []

    result = process_agent_decision(
        agent_tasks=tasks,
        agent_messages=messages,
        current_task_id="T1",
        state=make_state(),
        decision=AgentDecision(
            action=AgentAction.COMPLETE,
            result={
                "answer": "Complete."
            },
        ),
    )

    assert (
        tasks["T1"].status
        == AgentTaskStatus.COMPLETED
    )

    assert (
        result["agent_next_node"]
        == "synthesizer"
    )

    assert result[
        "current_agent_task_id"
    ] == "T1"


def test_delegation_is_rejected_after_task_steps_start():

    tasks = {
        "T1": make_root(),
    }

    messages = []

    from models.plan import PlanStep

    state = make_state(
        steps=[
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+2",
                depends_on=[],
                agent_task_id="T1",
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="cannot delegate",
    ):
        process_agent_decision(
            agent_tasks=tasks,
            agent_messages=messages,
            current_task_id="T1",
            state=state,
            decision=AgentDecision(
                action=AgentAction.DELEGATE,
                target_agent_id="research",
                request="Research something.",
            ),
        )


def test_decision_context_contains_execution_and_child_results():

    root = make_root()

    root.metadata["child_results"] = [
        {
            "task_id": "T2",
            "agent_id": "research",
            "request": "Research subject.",
            "result": {
                "answer": "Research result."
            },
        }
    ]

    from models.plan import PlanStep

    state = make_state(
        steps=[
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="2+2",
                depends_on=[],
                agent_task_id="T1",
            )
        ],
        tool_results={
            1: {
                "status": "success",
                "success": True,
                "output": {
                    "value": 4
                },
                "error": None,
                "failure_reason": None,
            }
        },
    )

    context = build_decision_context(
        root,
        state,
    )

    assert "calculator" in context
    assert "value" in context
    assert "T2" in context
    assert "Research result" in context


def test_planner_steps_are_scoped_to_agent_task():

    from agents.controller import get_task_steps

    from models.plan import PlanStep

    steps = [
        PlanStep(
            id=1,
            tool="calculator",
            tool_input="2+2",
            depends_on=[],
            agent_task_id="T1",
        ),
        PlanStep(
            id=2,
            tool="rag",
            tool_input="research",
            depends_on=[],
            agent_task_id="T2",
        ),
    ]

    state = {
        "steps": steps,
    }

    result = get_task_steps(
        state,
        "T2",
    )

    assert len(result) == 1
    assert result[0].id == 2