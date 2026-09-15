import pytest

from agents import (
    AgentDefinition,
    AgentTask,
    clear_registry,
    register_agent,
)
from agents.runtime import AgentRuntime
from models.plan import PlanStep


class FakePlanningService:

    def __init__(self, steps):
        self.steps = steps
        self.requests = []

    def plan(self, request):
        self.requests.append(request)
        return self.steps


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

    runtime = AgentRuntime(
        planning_service=FakePlanningService([])
    )

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

    runtime = AgentRuntime(
        planning_service=FakePlanningService([])
    )

    with pytest.raises(
        ValueError,
        match="Agent 'unknown' is not registered",
    ):
        runtime.build_planning_request(task)


def test_plan_task_uses_planning_service():

    register_research_agent()

    task = AgentTask(
        task_id="T2",
        parent_task_id=None,
        agent_id="research",
        request="Research hybrid cars.",
    )

    planned_steps = [
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

    planning_service = FakePlanningService(
        planned_steps
    )

    runtime = AgentRuntime(
        planning_service=planning_service
    )

    steps = runtime.plan_task(task)

    assert len(steps) == 2

    assert steps[0].agent_task_id == "T2"
    assert steps[1].agent_task_id == "T2"

    assert len(planning_service.requests) == 1
    assert "Research Agent" in planning_service.requests[0]
    assert "Research hybrid cars." in planning_service.requests[0]


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

    planning_service = FakePlanningService(
        [original_step]
    )

    runtime = AgentRuntime(
        planning_service=planning_service
    )

    steps = runtime.plan_task(task)

    assert steps[0] is not original_step
    assert steps[0].agent_task_id == "T3"
    assert original_step.agent_task_id is None