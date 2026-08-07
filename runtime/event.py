import time
from dataclasses import dataclass, field
from typing import Any

from shared_types.workflow_event_type import WorkflowEventType


@dataclass
class WorkflowEvent:
    type: WorkflowEventType
    timestamp: float = field(default_factory=time.time)
    step_id: int | None = None
    tool: str | None = None

    payload: dict[str, Any] = field(default_factory=dict)