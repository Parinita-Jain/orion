from agents.models import AgentDefinition
from agents.registry import (
    clear_registry,
    register_agent,
)
from agents.runtime import AgentRuntime
from agents.task import AgentTask
from models.plan import PlanStep


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


def teardown_function():
    clear_registry()


class FakePlanningService:
    def plan(self, request, planning_context=None):
        return [
            PlanStep(
                id=1,
                tool="calculator",
                tool_input="calculate first step",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="formatter",
                tool_input="use result from #1.",
                depends_on=[1],
            ),
        ]


def test_plan_task_remaps_ids_and_dependencies():
    runtime = AgentRuntime(
        planning_service=FakePlanningService()
    )

    task = AgentTask(
        task_id="T2",
        parent_task_id="T1",
        agent_id="supervisor",
        request="Perform the delegated work.",
    )

    existing_steps = [
        PlanStep(
            id=1,
            tool="research",
            tool_input="research",
            depends_on=[],
            agent_task_id="T1",
        ),
        PlanStep(
            id=2,
            tool="calculator",
            tool_input="calculate",
            depends_on=[],
            agent_task_id="T1",
        ),
    ]

    steps = runtime.plan_task(
        task,
        existing_steps=existing_steps,
    )

    assert [step.id for step in steps] == [3, 4]

    assert steps[0].depends_on == []
    assert steps[1].depends_on == [3]

    assert steps[1].tool_input == "use result from #3."

    assert all(
        step.agent_task_id == "T2"
        for step in steps
    )


def test_plan_task_preserves_ids_for_initial_plan():
    runtime = AgentRuntime(
        planning_service=FakePlanningService()
    )

    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Perform the work.",
    )

    steps = runtime.plan_task(task)

    assert [step.id for step in steps] == [1, 2]

    assert steps[1].depends_on == [1]

    assert steps[1].tool_input == "use result from #1."

    assert all(
        step.agent_task_id == "T1"
        for step in steps
    )