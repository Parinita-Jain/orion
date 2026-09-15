from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentTaskStatus(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """
    Work delegated to an agent.
    """

    task_id: str
    parent_task_id: str | None
    agent_id: str
    request: str
    status: AgentTaskStatus = AgentTaskStatus.CREATED
    result: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)