from agents import AgentDefinition


def test_agent_definition():
    agent = AgentDefinition(
        id="research",
        name="Research Agent",
        role="research",
        instructions="Research the assigned subject.",
    )

    assert agent.id == "research"
    assert agent.name == "Research Agent"
    assert agent.role == "research"
    assert agent.instructions == "Research the assigned subject."