from agents.models import AgentDefinition


AGENT_REGISTRY = {}


def register_agent(agent: AgentDefinition):
    """
    Register an agent definition.
    """

    if agent.id in AGENT_REGISTRY:
        raise ValueError(
            f"Agent '{agent.id}' is already registered."
        )

    AGENT_REGISTRY[agent.id] = agent


def clear_registry():
    """
    Remove all registered agents.
    """

    AGENT_REGISTRY.clear()


def get_agent(agent_id: str):
    """
    Return a registered agent definition by ID.
    """

    return AGENT_REGISTRY.get(agent_id)


def list_agents():
    """
    Return all registered agent definitions.
    """

    return AGENT_REGISTRY