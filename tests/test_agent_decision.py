from unittest.mock import patch

import pytest

from agents.decision import (
    AgentAction,
    AgentDecision,
)

from agents.models import AgentDefinition
from agents.registry import (
    clear_registry,
    register_agent,
)

from agents.runtime import AgentRuntime
from agents.task import AgentTask


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


def make_task():
    return AgentTask(
        task_id="T1",
        parent_task_id=None,
        agent_id="supervisor",
        request="Complete the assigned task.",
    )


def register_supervisor():
    register_agent(
        AgentDefinition(
            id="supervisor",
            name="Supervisor Agent",
            role="supervisor",
            instructions="Coordinate the task.",
        )
    )


def test_agent_decision_plan():
    register_supervisor()

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.PLAN
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        result = runtime.decide_task(
            make_task()
        )

    assert result.action == AgentAction.PLAN


def test_agent_decision_complete():
    register_supervisor()

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.COMPLETE,
        result={"answer": "completed"},
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        result = runtime.decide_task(
            make_task()
        )

    assert result.action == AgentAction.COMPLETE
    assert result.result == {
        "answer": "completed"
    }


def test_agent_decision_delegate():
    register_supervisor()

    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Perform research.",
        )
    )

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.DELEGATE,
        target_agent_id="research",
        request="Research the assigned subject.",
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        result = runtime.decide_task(
            make_task()
        )

    assert result.action == AgentAction.DELEGATE
    assert result.target_agent_id == "research"
    assert result.request == (
        "Research the assigned subject."
    )


def test_agent_decision_rejects_unknown_agent():
    register_supervisor()

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.DELEGATE,
        target_agent_id="does-not-exist",
        request="Do some work.",
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        with pytest.raises(
            ValueError,
            match="is not registered",
        ):
            runtime.decide_task(
                make_task()
            )


def test_agent_decision_requires_delegation_target():
    register_supervisor()

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.DELEGATE,
        request="Do some work.",
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        with pytest.raises(
            ValueError,
            match="target_agent_id",
        ):
            runtime.decide_task(
                make_task()
            )


def test_agent_decision_requires_delegation_request():
    register_supervisor()

    register_agent(
        AgentDefinition(
            id="research",
            name="Research Agent",
            role="research",
            instructions="Perform research.",
        )
    )

    runtime = AgentRuntime()

    decision = AgentDecision(
        action=AgentAction.DELEGATE,
        target_agent_id="research",
    )

    with patch(
        "agents.runtime.llm"
    ) as mock_llm:

        mock_llm.with_structured_output.return_value.invoke.return_value = (
            decision
        )

        with pytest.raises(
            ValueError,
            match="non-empty request",
        ):
            runtime.decide_task(
                make_task()
            )