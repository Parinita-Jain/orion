from dataclasses import dataclass
from typing import Any


@dataclass
class AgentMessage:
    """
    Message exchanged between agents.
    """

    message_id: str
    sender: str
    recipient: str
    content: Any
    task_id: str | None = None
    correlation_id: str | None = None