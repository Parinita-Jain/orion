import pytest

from agents import (
    AgentDefinition,
    AgentTask,
    clear_registry,
    register_agent,
)
from agents.runtime import AgentRuntime
from models.plan import PlanStep


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


def register_research_agent():
    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Research the assigned subject.",
        )
    )


def test_build_planning_request():
    register_research_agent()

    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="research",
        request="Research hybrid cars.",
    )

    runtime = AgentRuntime()

    request = runtime.build_planning_request(task)

    assert "Research Agent" in request
    assert "research" in request
    assert "Research the assigned subject." in request
    assert "Research hybrid cars." in request


def test_build_planning_request_requires_registered_agent():
    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="unknown",
        request="Do something.",
    )

    runtime = AgentRuntime()

    with pytest.raises(
        ValueError,
        match="Agent 'unknown' is not registered",
    ):
        runtime.build_planning_request(task)


def test_plan_task_attaches_agent_task_id():
    register_research_agent()

    task = AgentTask(
        task_id="T2",
        parent_task_id=None,
        agent_id="research",
        request="Research hybrid cars.",
    )

    planner_request = {}

    def fake_planner(request):
        planner_request["value"] = request

        return [
            PlanStep(
                id=1,
                tool="rag",
                tool_input="Research hybrid cars.",
            ),
            PlanStep(
                id=2,
                tool="llm",
                tool_input="Summarize the research.",
                depends_on=[1],
            ),
        ]

    runtime = AgentRuntime()

    steps = runtime.plan_task(
        task,
        fake_planner,
    )

    assert len(steps) == 2
    assert steps[0].agent_task_id == "T2"
    assert steps[1].agent_task_id == "T2"

    assert planner_request["value"]
    assert "Research Agent" in planner_request["value"]


def test_plan_task_does_not_mutate_planner_steps():
    register_research_agent()

    task = AgentTask(
        task_id="T3",
        parent_task_id=None,
        agent_id="research",
        request="Research something.",
    )

    original_step = PlanStep(
        id=1,
        tool="rag",
        tool_input="Research something.",
    )

    def fake_planner(request):
        return [original_step]

    runtime = AgentRuntime()

    steps = runtime.plan_task(
        task,
        fake_planner,
    )

    assert steps[0] is not original_step
    assert steps[0].agent_task_id == "T3"
    assert original_step.agent_task_id is None


def test_plan_task_rejects_invalid_planner_result():
    register_research_agent()

    task = AgentTask(
        task_id="T4",
        parent_task_id=None,
        agent_id="research",
        request="Research something.",
    )

    runtime = AgentRuntime()

    def bad_planner(request):
        return "not a list"

    with pytest.raises(
        TypeError,
        match="Planner must return a list of PlanStep objects.",
    ):
        runtime.plan_task(
            task,
            bad_planner,
        )


def test_plan_task_rejects_non_plan_step():
    register_research_agent()

    task = AgentTask(
        task_id="T5",
        parent_task_id=None,
        agent_id="research",
        request="Research something.",
    )

    runtime = AgentRuntime()

    def bad_planner(request):
        return ["not a PlanStep"]

    with pytest.raises(
        TypeError,
        match="non-PlanStep",
    ):
        runtime.plan_task(
            task,
            bad_planner,
        )