from dataclasses import dataclass


@dataclass
class AgentDefinition:
    """
    Definition of an available Orion agent.
    """

    id: str
    name: str
    role: str
    instructions: str