import importlib
from unittest.mock import Mock

import pytest

import tools

from agents import (
    AgentDefinition,
    AgentTask,
    clear_registry as clear_agent_registry,
    register_agent,
)
from registry import clear_registry as clear_tool_registry
from agents.runtime import AgentRuntime
from models.plan import PlanStep
from planner.service import PlanningService
from registry import clear_registry as clear_tool_registry


@pytest.fixture(autouse=True)
def setup_tools():

    clear_tool_registry()
    importlib.reload(tools)

    clear_agent_registry()

    yield

    clear_tool_registry()
    clear_agent_registry()


def test_greeting_rule():

    service = PlanningService()

    steps = service.plan("Hello")

    assert len(steps) == 1
    assert steps[0].id == 1
    assert steps[0].tool == "direct"
    assert steps[0].tool_input == ""


def test_calculator_rule():

    service = PlanningService()

    steps = service.plan("25*7")

    assert len(steps) == 1
    assert steps[0].id == 1
    assert steps[0].tool == "calculator"
    assert steps[0].tool_input == "25*7"


def test_valid_llm_plan():

    fake_llm = Mock()

    fake_llm.invoke.return_value = type(
        "PlannerResult",
        (),
        {
            "steps": [
                type(
                    "PlannerStep",
                    (),
                    {
                        "id": 1,
                        "tool": "llm",
                        "tool_input": "Explain AI",
                        "depends_on": [],
                        "output": None,
                        "approval": None,
                        "condition": None,
                        "replaces": None,
                    },
                )()
            ]
        },
    )()

    service = PlanningService(
        get_structured_llm=lambda: fake_llm,
    )

    steps = service.plan("Explain AI")

    assert len(steps) == 1
    assert steps[0].tool == "llm"
    assert steps[0].tool_input == "Explain AI"


def test_llm_failure_raises_orion_error():

    fake_llm = Mock()

    fake_llm.invoke.side_effect = RuntimeError(
        "LLM called"
    )

    service = PlanningService(
        get_structured_llm=lambda: fake_llm,
    )

    with pytest.raises(
        Exception,
        match="LLM called",
    ):
        service.plan("Explain AI")


def test_repair_is_used_for_invalid_plan():

    invalid_step = type(
        "PlannerStep",
        (),
        {
            "id": 1,
            "tool": "unknown_tool",
            "tool_input": "Explain AI",
            "depends_on": [],
            "output": None,
            "approval": None,
            "condition": None,
            "replaces": None,
        },
    )()

    repaired_step = type(
        "PlannerStep",
        (),
        {
            "id": 1,
            "tool": "llm",
            "tool_input": "Explain AI",
            "depends_on": [],
            "output": None,
            "approval": None,
            "condition": None,
            "replaces": None,
        },
    )()

    fake_llm = Mock()

    fake_llm.invoke.return_value = type(
        "PlannerResult",
        (),
        {
            "steps": [invalid_step],
        },
    )()

    repaired_plan = type(
        "PlannerResult",
        (),
        {
            "steps": [repaired_step],
        },
    )()

    fake_repair = Mock(
        return_value=repaired_plan
    )

    service = PlanningService(
        get_structured_llm=lambda: fake_llm,
        repair_plan=fake_repair,
    )

    steps = service.plan("Explain AI")

    assert len(steps) == 1
    assert steps[0].tool == "llm"
    fake_repair.assert_called_once()


def test_runtime_uses_real_planning_service():

    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Research the assigned subject.",
        )
    )

    fake_service = Mock()

    fake_service.plan.return_value = [
        PlanStep(
            id=1,
            tool="rag",
            tool_input="Research hybrid cars.",
        )
    ]

    runtime = AgentRuntime(
        planning_service=fake_service
    )

    task = AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="research",
        request="Research hybrid cars.",
    )

    steps = runtime.plan_task(task)

    fake_service.plan.assert_called_once()

    assert len(steps) == 1
    assert steps[0].agent_task_id == "T1"