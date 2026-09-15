import pytest

from agents import (
    AgentDefinition,
    clear_registry,
    get_agent,
    list_agents,
    register_agent,
)


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


def test_register_and_get_agent():
    agent = AgentDefinition(
        id="research",
        name="Research Agent",
        role="research",
        instructions="Research the assigned subject.",
    )

    register_agent(agent)

    assert get_agent("research") == agent


def test_list_agents():
    research = AgentDefinition(
        id="research",
        name="Research Agent",
        role="research",
        instructions="Research the assigned subject.",
    )

    analysis = AgentDefinition(
        id="analysis",
        name="Analysis Agent",
        role="analysis",
        instructions="Analyze the supplied information.",
    )

    register_agent(research)
    register_agent(analysis)

    agents = list_agents()

    assert agents == {
        "research": research,
        "analysis": analysis,
    }


def test_duplicate_agent_registration_fails():
    agent = AgentDefinition(
        id="research",
        name="Research Agent",
        role="research",
        instructions="Research the assigned subject.",
    )

    register_agent(agent)

    with pytest.raises(ValueError, match="already registered"):
        register_agent(agent)


def test_clear_registry():
    agent = AgentDefinition(
        id="research",
        name="Research Agent",
        role="research",
        instructions="Research the assigned subject.",
    )

    register_agent(agent)
    clear_registry()

    assert get_agent("research") is None
    assert list_agents() == {}